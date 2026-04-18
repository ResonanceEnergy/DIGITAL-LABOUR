"""SQLite-backed task store for the BRL Task Management System.

Extends the pattern from dispatcher/queue.py with richer schema:
  - Human vs AI task ownership
  - Categories: client_work, internal, biz_dev, outreach
  - NCL intelligence linkage
  - C-Suite directive tracking
  - Due dates, recurrence, dependencies
  - Tags and notes for context
"""

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "brl_tasks.db"


class TaskStore:
    """Thread-safe SQLite store for BRL task management."""

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
            CREATE TABLE IF NOT EXISTS brl_tasks (
                task_id         TEXT PRIMARY KEY,
                title           TEXT NOT NULL,
                description     TEXT DEFAULT '',
                category        TEXT NOT NULL DEFAULT 'internal',
                subcategory     TEXT DEFAULT '',
                status          TEXT DEFAULT 'pending',
                priority        INTEGER DEFAULT 0,
                owner_type      TEXT DEFAULT 'human',
                owner_name      TEXT DEFAULT '',
                assigned_agent  TEXT DEFAULT '',
                client          TEXT DEFAULT '',
                source          TEXT DEFAULT 'manual',
                source_ref      TEXT DEFAULT '',
                ncl_event_id    TEXT DEFAULT '',
                directive_id    TEXT DEFAULT '',
                nerve_cycle_id  TEXT DEFAULT '',
                due_date        TEXT DEFAULT '',
                recurrence      TEXT DEFAULT '',
                depends_on      TEXT DEFAULT '[]',
                tags            TEXT DEFAULT '[]',
                notes           TEXT DEFAULT '[]',
                inputs          TEXT DEFAULT '{}',
                outputs         TEXT DEFAULT '{}',
                progress_pct    INTEGER DEFAULT 0,
                estimated_hours REAL DEFAULT 0.0,
                actual_hours    REAL DEFAULT 0.0,
                cost_usd        REAL DEFAULT 0.0,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                started_at      TEXT DEFAULT '',
                completed_at    TEXT DEFAULT '',
                archived        INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_brl_status ON brl_tasks(status);
            CREATE INDEX IF NOT EXISTS idx_brl_category ON brl_tasks(category);
            CREATE INDEX IF NOT EXISTS idx_brl_owner_type ON brl_tasks(owner_type);
            CREATE INDEX IF NOT EXISTS idx_brl_client ON brl_tasks(client);
            CREATE INDEX IF NOT EXISTS idx_brl_priority ON brl_tasks(priority DESC);
            CREATE INDEX IF NOT EXISTS idx_brl_due_date ON brl_tasks(due_date);
            CREATE INDEX IF NOT EXISTS idx_brl_source ON brl_tasks(source);
            CREATE INDEX IF NOT EXISTS idx_brl_directive ON brl_tasks(directive_id);
            CREATE INDEX IF NOT EXISTS idx_brl_archived ON brl_tasks(archived);

            CREATE TABLE IF NOT EXISTS task_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id     TEXT NOT NULL,
                action      TEXT NOT NULL,
                old_value   TEXT DEFAULT '',
                new_value   TEXT DEFAULT '',
                actor       TEXT DEFAULT '',
                timestamp   TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES brl_tasks(task_id)
            );

            CREATE INDEX IF NOT EXISTS idx_history_task ON task_history(task_id);
        """)
        conn.commit()

    # ── Create ─────────────────────────────────────────────────────

    def create(
        self,
        title: str,
        description: str = "",
        category: str = "internal",
        subcategory: str = "",
        priority: int = 0,
        owner_type: str = "human",
        owner_name: str = "",
        assigned_agent: str = "",
        client: str = "",
        source: str = "manual",
        source_ref: str = "",
        ncl_event_id: str = "",
        directive_id: str = "",
        nerve_cycle_id: str = "",
        due_date: str = "",
        recurrence: str = "",
        depends_on: list[str] | None = None,
        tags: list[str] | None = None,
        inputs: dict | None = None,
        estimated_hours: float = 0.0,
    ) -> str:
        """Create a new task. Returns task_id."""
        task_id = f"BRL-{uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO brl_tasks (
                task_id, title, description, category, subcategory, status, priority,
                owner_type, owner_name, assigned_agent, client, source, source_ref,
                ncl_event_id, directive_id, nerve_cycle_id, due_date, recurrence,
                depends_on, tags, inputs, estimated_hours, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task_id, title, description, category, subcategory, priority,
                owner_type, owner_name, assigned_agent, client, source, source_ref,
                ncl_event_id, directive_id, nerve_cycle_id, due_date, recurrence,
                json.dumps(depends_on or []), json.dumps(tags or []),
                json.dumps(inputs or {}), estimated_hours, now, now,
            ),
        )
        self._log_history(conn, task_id, "created", "", title, source)
        conn.commit()
        return task_id

    # ── Read ───────────────────────────────────────────────────────

    def get(self, task_id: str) -> dict | None:
        """Get a task by ID."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM brl_tasks WHERE task_id = ?", (task_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def list_tasks(
        self,
        status: str | None = None,
        category: str | None = None,
        owner_type: str | None = None,
        client: str | None = None,
        source: str | None = None,
        tag: str | None = None,
        include_archived: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """List tasks with flexible filtering."""
        conn = self._get_conn()
        query = "SELECT * FROM brl_tasks WHERE 1=1"
        params: list = []

        if not include_archived:
            query += " AND archived = 0"
        if status:
            query += " AND status = ?"
            params.append(status)
        if category:
            query += " AND category = ?"
            params.append(category)
        if owner_type:
            query += " AND owner_type = ?"
            params.append(owner_type)
        if client:
            query += " AND client = ?"
            params.append(client)
        if source:
            query += " AND source = ?"
            params.append(source)
        if tag:
            query += " AND tags LIKE ?"
            params.append(f"%{tag}%")

        query += " ORDER BY priority DESC, due_date ASC, created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        return [self._row_to_dict(r) for r in conn.execute(query, params).fetchall()]

    def search(self, query_text: str, limit: int = 50) -> list[dict]:
        """Full-text search across title, description, notes, tags."""
        conn = self._get_conn()
        pattern = f"%{query_text}%"
        rows = conn.execute(
            """SELECT * FROM brl_tasks
               WHERE (title LIKE ? OR description LIKE ? OR notes LIKE ? OR tags LIKE ?)
                 AND archived = 0
               ORDER BY priority DESC, created_at DESC LIMIT ?""",
            (pattern, pattern, pattern, pattern, limit),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    # ── Update ─────────────────────────────────────────────────────

    def update(self, task_id: str, actor: str = "system", **fields) -> bool:
        """Update task fields. Logs changes to history."""
        task = self.get(task_id)
        if not task:
            return False

        conn = self._get_conn()
        now = datetime.now(timezone.utc).isoformat()

        # JSON-encoded fields
        json_fields = {"depends_on", "tags", "notes", "inputs", "outputs"}

        set_clauses = ["updated_at = ?"]
        params = [now]

        for key, value in fields.items():
            if key in ("task_id", "created_at"):
                continue  # immutable
            old_val = task.get(key, "")
            if key in json_fields:
                new_val = json.dumps(value) if not isinstance(value, str) else value
            else:
                new_val = value

            set_clauses.append(f"{key} = ?")
            params.append(new_val)

            # Log the change
            self._log_history(
                conn, task_id, f"updated.{key}",
                str(old_val) if not isinstance(old_val, str) else old_val,
                str(new_val) if not isinstance(new_val, str) else new_val,
                actor,
            )

        # Auto-set timestamps
        if "status" in fields:
            new_status = fields["status"]
            if new_status == "in_progress" and not task.get("started_at"):
                set_clauses.append("started_at = ?")
                params.append(now)
            elif new_status in ("completed", "cancelled"):
                set_clauses.append("completed_at = ?")
                params.append(now)

        params.append(task_id)
        conn.execute(
            f"UPDATE brl_tasks SET {', '.join(set_clauses)} WHERE task_id = ?",
            params,
        )
        conn.commit()
        return True

    def add_note(self, task_id: str, note: str, author: str = "system") -> bool:
        """Append a timestamped note to a task."""
        task = self.get(task_id)
        if not task:
            return False
        notes = task.get("notes", [])
        if isinstance(notes, str):
            notes = json.loads(notes) if notes else []
        notes.append({
            "text": note,
            "author": author,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return self.update(task_id, actor=author, notes=notes)

    def archive(self, task_id: str) -> bool:
        """Archive a completed/cancelled task."""
        return self.update(task_id, actor="system", archived=1)

    # ── Stats & Dashboards ─────────────────────────────────────────

    def stats(self) -> dict:
        """Dashboard-ready statistics."""
        conn = self._get_conn()
        result = {"by_status": {}, "by_category": {}, "by_owner_type": {}, "by_source": {}}

        for status in ("pending", "in_progress", "completed", "blocked", "cancelled"):
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM brl_tasks WHERE status = ? AND archived = 0",
                (status,),
            ).fetchone()
            result["by_status"][status] = row["cnt"]

        for cat in ("client_work", "internal", "biz_dev", "outreach"):
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM brl_tasks WHERE category = ? AND archived = 0",
                (cat,),
            ).fetchone()
            result["by_category"][cat] = row["cnt"]

        for otype in ("human", "ai", "hybrid"):
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM brl_tasks WHERE owner_type = ? AND archived = 0",
                (otype,),
            ).fetchone()
            result["by_owner_type"][otype] = row["cnt"]

        for src in ("manual", "ncl", "c_suite", "nerve", "paperclip", "scheduler"):
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM brl_tasks WHERE source = ? AND archived = 0",
                (src,),
            ).fetchone()
            result["by_source"][src] = row["cnt"]

        total = conn.execute(
            "SELECT COUNT(*) as cnt FROM brl_tasks WHERE archived = 0"
        ).fetchone()
        result["total_active"] = total["cnt"]

        overdue = conn.execute(
            """SELECT COUNT(*) as cnt FROM brl_tasks
               WHERE due_date != '' AND due_date < ? AND status NOT IN ('completed', 'cancelled')
                 AND archived = 0""",
            (datetime.now(timezone.utc).strftime("%Y-%m-%d"),),
        ).fetchone()
        result["overdue"] = overdue["cnt"]

        # Human responsibility load
        human_active = conn.execute(
            """SELECT COUNT(*) as cnt FROM brl_tasks
               WHERE owner_type = 'human' AND status IN ('pending', 'in_progress')
                 AND archived = 0"""
        ).fetchone()
        result["human_active_tasks"] = human_active["cnt"]

        return result

    def overdue_tasks(self) -> list[dict]:
        """Get all overdue, non-completed tasks."""
        conn = self._get_conn()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rows = conn.execute(
            """SELECT * FROM brl_tasks
               WHERE due_date != '' AND due_date < ? AND status NOT IN ('completed', 'cancelled')
                 AND archived = 0
               ORDER BY due_date ASC""",
            (today,),
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def human_responsibilities(self) -> list[dict]:
        """Get all active human-owned tasks."""
        return self.list_tasks(owner_type="human", status=None)

    def ai_workload(self) -> list[dict]:
        """Get all active AI-assigned tasks."""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT * FROM brl_tasks
               WHERE owner_type IN ('ai', 'hybrid') AND status IN ('pending', 'in_progress')
                 AND archived = 0
               ORDER BY priority DESC, created_at ASC"""
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def task_history(self, task_id: str) -> list[dict]:
        """Get the full audit trail for a task."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM task_history WHERE task_id = ? ORDER BY timestamp ASC",
            (task_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Helpers ────────────────────────────────────────────────────

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """Convert a Row to dict, deserializing JSON fields."""
        d = dict(row)
        for key in ("depends_on", "tags", "notes", "inputs", "outputs"):
            if key in d and isinstance(d[key], str):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d

    def _log_history(self, conn, task_id, action, old_value, new_value, actor="system"):
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO task_history (task_id, action, old_value, new_value, actor, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (task_id, action, str(old_value)[:500], str(new_value)[:500], actor, now),
        )
