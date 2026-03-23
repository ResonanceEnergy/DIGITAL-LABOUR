"""SQLite-backed task queue for Digital Labour dispatcher.

Usage:
    from dispatcher.queue import TaskQueue

    q = TaskQueue()
    task_id = q.enqueue("sales_outreach", {"company": "Acme"}, client="client-1")
    task = q.dequeue()
    q.complete(task_id, outputs={...}, qa_status="PASS")
"""

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "task_queue.db"


class TaskQueue:
    """Thread-safe SQLite task queue."""

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path))
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA busy_timeout=5000")
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id      TEXT PRIMARY KEY,
                task_type    TEXT NOT NULL,
                client       TEXT DEFAULT '',
                provider     TEXT DEFAULT '',
                status       TEXT DEFAULT 'queued',
                priority     INTEGER DEFAULT 0,
                inputs       TEXT DEFAULT '{}',
                outputs      TEXT DEFAULT '{}',
                qa_status    TEXT DEFAULT '',
                error        TEXT DEFAULT '',
                created_at   TEXT NOT NULL,
                started_at   TEXT DEFAULT '',
                completed_at TEXT DEFAULT '',
                cost_usd     REAL DEFAULT 0.0
            );

            CREATE INDEX IF NOT EXISTS idx_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_client ON tasks(client);
            CREATE INDEX IF NOT EXISTS idx_created ON tasks(created_at);

            CREATE TABLE IF NOT EXISTS daily_budget (
                date         TEXT NOT NULL,
                client       TEXT NOT NULL,
                task_type    TEXT NOT NULL,
                count        INTEGER DEFAULT 0,
                PRIMARY KEY (date, client, task_type)
            );
        """)
        conn.commit()

    def enqueue(
        self,
        task_type: str,
        inputs: dict,
        client: str = "",
        provider: str = "",
        priority: int = 0,
    ) -> str:
        """Add a task to the queue. Returns task_id."""
        task_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO tasks (task_id, task_type, client, provider, status, priority, inputs, created_at)
               VALUES (?, ?, ?, ?, 'queued', ?, ?, ?)""",
            (task_id, task_type, client, provider, priority, json.dumps(inputs), now),
        )
        conn.commit()
        return task_id

    def dequeue(self) -> dict | None:
        """Claim the next queued task (FIFO, priority-weighted). Returns task dict or None."""
        conn = self._get_conn()
        cursor = conn.execute(
            """SELECT * FROM tasks WHERE status = 'queued'
               ORDER BY priority DESC, created_at ASC LIMIT 1"""
        )
        row = cursor.fetchone()
        if not row:
            return None

        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE tasks SET status = 'running', started_at = ? WHERE task_id = ?",
            (now, row["task_id"]),
        )
        conn.commit()
        return dict(row)

    def complete(self, task_id: str, outputs: dict | None = None, qa_status: str = "", cost_usd: float = 0.0):
        """Mark a task as completed."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        conn.execute(
            """UPDATE tasks SET status = 'completed', outputs = ?, qa_status = ?,
               completed_at = ?, cost_usd = ? WHERE task_id = ?""",
            (json.dumps(outputs or {}), qa_status, now, cost_usd, task_id),
        )
        conn.commit()

    def fail(self, task_id: str, error: str = ""):
        """Mark a task as failed."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        conn.execute(
            "UPDATE tasks SET status = 'failed', error = ?, completed_at = ? WHERE task_id = ?",
            (error, now, task_id),
        )
        conn.commit()

    def get(self, task_id: str) -> dict | None:
        """Get a task by ID."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        return dict(row) if row else None

    def list_tasks(self, status: str | None = None, client: str | None = None, limit: int = 50) -> list[dict]:
        """List tasks with optional filters."""
        conn = self._get_conn()
        query = "SELECT * FROM tasks WHERE 1=1"
        params: list = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if client:
            query += " AND client = ?"
            params.append(client)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in conn.execute(query, params).fetchall()]

    def stats(self, client: str | None = None) -> dict:
        """Get queue statistics."""
        conn = self._get_conn()
        base = " WHERE client = ?" if client else ""
        params = [client] if client else []

        result = {}
        for status in ("queued", "running", "completed", "failed"):
            row = conn.execute(
                f"SELECT COUNT(*) as cnt FROM tasks{base} AND status = ?" if client
                else f"SELECT COUNT(*) as cnt FROM tasks WHERE status = ?",
                params + [status],
            ).fetchone()
            result[status] = row["cnt"]
        result["total"] = sum(result.values())
        return result

    # ── Budget enforcement ──────────────────────────────────────────────

    def check_budget(self, client: str, task_type: str, daily_limit: int) -> bool:
        """Return True if client is within daily budget for this task type."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        conn = self._get_conn()
        row = conn.execute(
            "SELECT count FROM daily_budget WHERE date = ? AND client = ? AND task_type = ?",
            (today, client, task_type),
        ).fetchone()
        current = row["count"] if row else 0
        return current < daily_limit

    def increment_budget(self, client: str, task_type: str):
        """Increment the daily count for a client/task type."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO daily_budget (date, client, task_type, count)
               VALUES (?, ?, ?, 1)
               ON CONFLICT(date, client, task_type)
               DO UPDATE SET count = count + 1""",
            (today, client, task_type),
        )
        conn.commit()

    def get_daily_usage(self, client: str) -> list[dict]:
        """Get today's usage for a client."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT task_type, count FROM daily_budget WHERE date = ? AND client = ?",
            (today, client),
        ).fetchall()
        return [dict(r) for r in rows]


if __name__ == "__main__":
    q = TaskQueue()
    # Quick test
    tid = q.enqueue("sales_outreach", {"company": "TestCo"}, client="demo")
    print(f"Enqueued: {tid}")
    task = q.dequeue()
    print(f"Dequeued: {task['task_id'] if task else 'None'}")
    if task:
        q.complete(task["task_id"], outputs={"test": True}, qa_status="PASS")
    print(f"Stats: {q.stats()}")
