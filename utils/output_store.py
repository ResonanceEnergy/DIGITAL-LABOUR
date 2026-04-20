"""Persistent output store for completed Bit Rage task outputs.

SQLite-backed store that captures every completed output with metadata,
providing query/search/retrieval capabilities. Replaces the pattern of
writing JSON files to output/ directories that are never referenced again.

Usage:
    from utils.output_store import store_output, get_output, list_outputs, search_outputs
"""

import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("data.output_store")

_DB_PATH = Path(__file__).resolve().parent / "outputs.db"

# Thread-local connections for SQLite thread safety
_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Return a thread-local SQLite connection, creating tables if needed."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(_DB_PATH), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        _local.conn = conn
        _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection):
    """Create tables and indexes if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS outputs (
            id TEXT PRIMARY KEY,
            task_type TEXT NOT NULL,
            division TEXT DEFAULT '',
            client TEXT DEFAULT '',
            provider TEXT DEFAULT '',
            qa_status TEXT DEFAULT 'UNKNOWN',
            qa_score INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            duration_s REAL DEFAULT 0,
            cost_usd REAL DEFAULT 0,
            title TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            outputs_json TEXT DEFAULT '{}',
            tags TEXT DEFAULT '',
            category TEXT DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_outputs_task_type ON outputs(task_type);
        CREATE INDEX IF NOT EXISTS idx_outputs_division ON outputs(division);
        CREATE INDEX IF NOT EXISTS idx_outputs_created ON outputs(created_at);
        CREATE INDEX IF NOT EXISTS idx_outputs_category ON outputs(category);
    """)


# ── Category mapping ──────────────────────────────────────────────────────

_TASK_CATEGORY = {
    # Company building
    "business_plan": "company_building",
    "proposal_writer": "company_building",
    # Market research
    "market_research": "market_research",
    "lead_gen": "market_research",
    "web_scraper": "market_research",
    # Content
    "content_repurpose": "content",
    "seo_content": "content",
    "social_media": "content",
    "email_marketing": "content",
    "ad_copy": "content",
    "press_release": "content",
    "product_desc": "content",
    "tech_docs": "content",
    "resume_writer": "content",
    # Compliance
    "compliance_docs": "compliance",
    "insurance_appeals": "compliance",
    "insurance_qa": "compliance",
    "insurance_compliance": "compliance",
    "grant_writer": "compliance",
    "grant_qa": "compliance",
    "grant_compliance": "compliance",
    "contractor_compliance": "compliance",
    "municipal_compliance": "compliance",
    # Operations
    "sales_outreach": "operations",
    "support_ticket": "operations",
    "doc_extract": "operations",
    "data_entry": "operations",
    "crm_ops": "operations",
    "bookkeeping": "operations",
    "context_manager": "operations",
    "qa_manager": "operations",
    "production_manager": "operations",
    "automation_manager": "operations",
    "data_reporter": "operations",
    # Platform work
    "freelancer_work": "operations",
    "upwork_work": "operations",
    "fiverr_work": "operations",
    "pph_work": "operations",
    "guru_work": "operations",
    # Division docs
    "contractor_doc_writer": "content",
    "contractor_qa": "compliance",
    "municipal_doc_writer": "content",
    "municipal_qa": "compliance",
}


def _infer_category(task_type: str) -> str:
    """Infer category from task type."""
    return _TASK_CATEGORY.get(task_type, "operations")


# ── Smart extraction helpers ──────────────────────────────────────────────

def _extract_title(outputs_dict: dict, task_type: str) -> str:
    """Extract a human-readable title from the output JSON."""
    if not isinstance(outputs_dict, dict):
        return task_type.replace("_", " ").title()

    # Try common title-bearing keys in priority order
    for key in ("title", "project_name", "subject", "headline",
                "letter_type", "doc_type", "report_type", "plan_type",
                "proposal_type", "release_type", "content_type",
                "name", "topic"):
        val = outputs_dict.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()[:200]

    # Try nested structures (e.g., outputs.qa.title, outputs.metadata.title)
    for sub_key in ("metadata", "qa", "result", "output"):
        sub = outputs_dict.get(sub_key)
        if isinstance(sub, dict):
            for key in ("title", "subject", "name"):
                val = sub.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()[:200]

    return task_type.replace("_", " ").title()


def _extract_summary(outputs_dict: dict, task_type: str) -> str:
    """Extract the first meaningful content block (up to 500 chars)."""
    if not isinstance(outputs_dict, dict):
        text = str(outputs_dict)
        return text[:500]

    # Try common content keys
    for key in ("full_markdown", "document_body", "letter_body", "body",
                "content", "text", "article", "email_body", "summary",
                "executive_summary", "description", "proposal_body",
                "blog_post", "output"):
        val = outputs_dict.get(key)
        if isinstance(val, str) and len(val.strip()) > 20:
            return val.strip()[:500]

    # Try nested content
    for sub_key in ("result", "output", "deliverable"):
        sub = outputs_dict.get(sub_key)
        if isinstance(sub, dict):
            for key in ("full_markdown", "body", "content", "text"):
                val = sub.get(key)
                if isinstance(val, str) and len(val.strip()) > 20:
                    return val.strip()[:500]
        elif isinstance(sub, str) and len(sub.strip()) > 20:
            return sub.strip()[:500]

    # Fallback: serialize first 500 chars of JSON
    text = json.dumps(outputs_dict, default=str)
    return text[:500]


def _auto_tag(task_type: str, division: str, outputs_dict: dict) -> str:
    """Generate comma-separated tags from task type, division, and content."""
    tags = set()

    # Task type as tag
    tags.add(task_type)

    # Division as tag
    if division:
        tags.add(division.lower())

    # Category as tag
    cat = _infer_category(task_type)
    if cat:
        tags.add(cat)

    # Extract keywords from outputs
    if isinstance(outputs_dict, dict):
        # Add doc_type, letter_type, etc. as tags
        for key in ("doc_type", "letter_type", "grant_type", "report_type",
                     "plan_type", "platform", "industry"):
            val = outputs_dict.get(key)
            if isinstance(val, str) and val.strip():
                tags.add(val.strip().lower())

    return ",".join(sorted(tags))


# ── Public API ────────────────────────────────────────────────────────────

def store_output(
    task_id: str,
    task_type: str,
    division: str = "",
    client: str = "",
    provider: str = "",
    qa_status: str = "PASS",
    qa_score: int = 0,
    duration_s: float = 0,
    cost_usd: float = 0,
    outputs: dict | None = None,
    category: str = "",
) -> str:
    """Save a completed output to the store. Returns the task_id."""
    outputs = outputs or {}
    now = datetime.now(timezone.utc).isoformat()

    title = _extract_title(outputs, task_type)
    summary = _extract_summary(outputs, task_type)
    tags = _auto_tag(task_type, division, outputs)
    if not category:
        category = _infer_category(task_type)

    outputs_json = json.dumps(outputs, default=str)

    conn = _get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO outputs
           (id, task_type, division, client, provider, qa_status, qa_score,
            created_at, completed_at, duration_s, cost_usd,
            title, summary, outputs_json, tags, category)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            task_id, task_type, division or "", client or "", provider or "",
            qa_status, qa_score,
            now, now, duration_s, cost_usd,
            title, summary, outputs_json, tags, category,
        ),
    )
    conn.commit()
    logger.info("[OUTPUT_STORE] Stored %s (%s) — %s", task_id[:12], task_type, title[:60])
    return task_id


def get_output(task_id: str) -> dict | None:
    """Retrieve a single output by task_id, including full outputs_json."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM outputs WHERE id = ?", (task_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    # Parse outputs_json back to dict
    try:
        d["outputs"] = json.loads(d.pop("outputs_json", "{}"))
    except (json.JSONDecodeError, TypeError):
        d["outputs"] = {}
    return d


def list_outputs(
    division: str | None = None,
    task_type: str | None = None,
    category: str | None = None,
    qa_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List outputs with optional filters. Does NOT include full outputs_json."""
    conn = _get_conn()
    clauses = []
    params: list = []

    if division:
        clauses.append("division = ?")
        params.append(division)
    if task_type:
        clauses.append("task_type = ?")
        params.append(task_type)
    if category:
        clauses.append("category = ?")
        params.append(category)
    if qa_status:
        clauses.append("qa_status = ?")
        params.append(qa_status)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    query = (
        f"SELECT id, task_type, division, client, provider, qa_status, qa_score, "
        f"created_at, completed_at, duration_s, cost_usd, title, summary, tags, category "
        f"FROM outputs{where} ORDER BY created_at DESC LIMIT ? OFFSET ?"
    )
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def search_outputs(query: str, limit: int = 20) -> list[dict]:
    """Full-text search across title, summary, and tags."""
    conn = _get_conn()
    pattern = f"%{query}%"
    rows = conn.execute(
        """SELECT id, task_type, division, client, provider, qa_status, qa_score,
                  created_at, completed_at, duration_s, cost_usd, title, summary, tags, category
           FROM outputs
           WHERE title LIKE ? OR summary LIKE ? OR tags LIKE ?
           ORDER BY created_at DESC LIMIT ?""",
        (pattern, pattern, pattern, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    """Return aggregate statistics about the output store."""
    conn = _get_conn()

    total = conn.execute("SELECT COUNT(*) FROM outputs").fetchone()[0]

    by_division = {}
    for row in conn.execute(
        "SELECT division, COUNT(*) as cnt FROM outputs GROUP BY division ORDER BY cnt DESC"
    ).fetchall():
        by_division[row["division"] or "(none)"] = row["cnt"]

    by_task_type = {}
    for row in conn.execute(
        "SELECT task_type, COUNT(*) as cnt FROM outputs GROUP BY task_type ORDER BY cnt DESC"
    ).fetchall():
        by_task_type[row["task_type"]] = row["cnt"]

    by_category = {}
    for row in conn.execute(
        "SELECT category, COUNT(*) as cnt FROM outputs GROUP BY category ORDER BY cnt DESC"
    ).fetchall():
        by_category[row["category"] or "(none)"] = row["cnt"]

    by_qa_status = {}
    for row in conn.execute(
        "SELECT qa_status, COUNT(*) as cnt FROM outputs GROUP BY qa_status ORDER BY cnt DESC"
    ).fetchall():
        by_qa_status[row["qa_status"]] = row["cnt"]

    return {
        "total": total,
        "by_division": by_division,
        "by_task_type": by_task_type,
        "by_category": by_category,
        "by_qa_status": by_qa_status,
    }


def get_latest(
    division: str | None = None,
    task_type: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Return the most recent outputs, optionally filtered."""
    return list_outputs(division=division, task_type=task_type, limit=limit, offset=0)
