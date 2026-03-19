"""Structured KPI event logger — logs every task event to JSONL and SQLite.

Usage:
    from kpi.logger import log_task_event

    log_task_event(
        task_id="abc-123",
        task_type="sales_outreach",
        client="acme",
        provider="openai",
        status="completed",
        qa_status="PASS",
        duration_s=13.4,
        cost_usd=0.012,
    )
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

LOGS_DIR = PROJECT_ROOT / "kpi" / "logs"
DB_PATH = PROJECT_ROOT / "data" / "kpi.db"
DOCTRINE_VERSION = "2.0"


def _ensure_dirs():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _get_db() -> sqlite3.Connection:
    _ensure_dirs()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id         TEXT NOT NULL,
            lineage_id      TEXT DEFAULT '',
            task_type       TEXT NOT NULL,
            client          TEXT DEFAULT '',
            provider        TEXT DEFAULT '',
            status          TEXT NOT NULL,
            qa_status       TEXT DEFAULT '',
            failure_reason  TEXT DEFAULT '',
            duration_s      REAL DEFAULT 0.0,
            cost_usd        REAL DEFAULT 0.0,
            tokens_in       INTEGER DEFAULT 0,
            tokens_out      INTEGER DEFAULT 0,
            error           TEXT DEFAULT '',
            doctrine_version TEXT DEFAULT '2.0',
            metadata        TEXT DEFAULT '{}',
            timestamp       TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_events_lineage ON events(lineage_id);
        CREATE INDEX IF NOT EXISTS idx_events_time ON events(timestamp);
        CREATE INDEX IF NOT EXISTS idx_events_client ON events(client);
        CREATE INDEX IF NOT EXISTS idx_events_type ON events(task_type);
    """)
    conn.commit()
    return conn


def log_task_event(
    task_id: str,
    task_type: str,
    status: str,
    client: str = "",
    provider: str = "",
    qa_status: str = "",
    failure_reason: str = "",
    lineage_id: str = "",
    duration_s: float = 0.0,
    cost_usd: float = 0.0,
    tokens_in: int = 0,
    tokens_out: int = 0,
    error: str = "",
    metadata: dict | None = None,
) -> dict:
    """Log a task event to both JSONL and SQLite. Returns the event dict."""
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()

    event = {
        "task_id": task_id,
        "lineage_id": lineage_id,
        "task_type": task_type,
        "client": client,
        "provider": provider,
        "status": status,
        "qa_status": qa_status,
        "failure_reason": failure_reason,
        "duration_s": round(duration_s, 3),
        "cost_usd": round(cost_usd, 6),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "error": error,
        "doctrine_version": DOCTRINE_VERSION,
        "metadata": metadata or {},
        "timestamp": timestamp,
    }

    # JSONL (daily file)
    _ensure_dirs()
    daily_file = LOGS_DIR / f"{now.strftime('%Y-%m-%d')}.jsonl"
    with open(daily_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

    # SQLite
    conn = _get_db()
    conn.execute(
        """INSERT INTO events
           (task_id, lineage_id, task_type, client, provider, status, qa_status,
            failure_reason, duration_s, cost_usd, tokens_in, tokens_out, error,
            doctrine_version, metadata, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            task_id, lineage_id, task_type, client, provider, status, qa_status,
            failure_reason, duration_s, cost_usd, tokens_in, tokens_out, error,
            DOCTRINE_VERSION, json.dumps(metadata or {}), timestamp,
        ),
    )
    conn.commit()
    conn.close()

    return event


def get_events(
    start: str | None = None,
    end: str | None = None,
    task_type: str | None = None,
    client: str | None = None,
    status: str | None = None,
    limit: int = 500,
) -> list[dict]:
    """Query events from SQLite with optional filters."""
    conn = _get_db()
    query = "SELECT * FROM events WHERE 1=1"
    params: list = []

    if start:
        query += " AND timestamp >= ?"
        params.append(start)
    if end:
        query += " AND timestamp <= ?"
        params.append(end)
    if task_type:
        query += " AND task_type = ?"
        params.append(task_type)
    if client:
        query += " AND client = ?"
        params.append(client)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def summary(days: int = 7, client: str | None = None) -> dict:
    """Generate a summary of recent activity."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    events = get_events(start=cutoff, client=client, limit=10000)

    total = len(events)
    completed = [e for e in events if e["status"] == "completed"]
    failed = [e for e in events if e["status"] == "failed"]

    total_revenue = sum(e.get("cost_usd", 0) for e in completed)
    avg_duration = sum(e.get("duration_s", 0) for e in completed) / len(completed) if completed else 0

    by_type: dict[str, int] = {}
    by_provider: dict[str, int] = {}
    for e in events:
        by_type[e["task_type"]] = by_type.get(e["task_type"], 0) + 1
        if e.get("provider"):
            by_provider[e["provider"]] = by_provider.get(e["provider"], 0) + 1

    return {
        "period_days": days,
        "total_tasks": total,
        "completed": len(completed),
        "failed": len(failed),
        "pass_rate": f"{len(completed)/total*100:.1f}%" if total else "N/A",
        "total_cost_usd": round(total_revenue, 4),
        "avg_duration_s": round(avg_duration, 2),
        "by_type": by_type,
        "by_provider": by_provider,
    }
