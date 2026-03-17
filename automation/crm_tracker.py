"""CRM Tracker — SQLite-backed client relationship management.

Tracks the full lifecycle: prospect → lead → opportunity → client → retained.
Integrates with sent_log, email_tracker, lead_scorer, and billing.

Usage:
    python -m automation.crm_tracker --pipeline         # Show deal pipeline
    python -m automation.crm_tracker --clients          # List active clients
    python -m automation.crm_tracker --add-lead "Acme" "ceo@acme.com"
    python -m automation.crm_tracker --status           # CRM health stats
    python -m automation.crm_tracker --sync             # Sync from sent_log + billing
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "data" / "crm.db"
SENT_LOG = Path(__file__).parent / "sent_log.json"
SCORES_FILE = PROJECT_ROOT / "data" / "lead_scores.json"
BILLING_DB = PROJECT_ROOT / "data" / "billing.db"

# Pipeline stages (in order)
STAGES = ["prospect", "contacted", "replied", "opportunity", "proposal", "client", "retained", "churned"]


# ── Database ───────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db():
    """Create CRM tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS contacts (
            contact_id   TEXT PRIMARY KEY,
            company      TEXT NOT NULL,
            name         TEXT DEFAULT '',
            email        TEXT DEFAULT '',
            role         TEXT DEFAULT '',
            stage        TEXT DEFAULT 'prospect',
            lead_score   INTEGER DEFAULT 50,
            source       TEXT DEFAULT 'manual',
            notes        TEXT DEFAULT '',
            deal_value   REAL DEFAULT 0.0,
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL,
            last_contact TEXT DEFAULT '',
            next_action  TEXT DEFAULT '',
            tags         TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS interactions (
            interaction_id TEXT PRIMARY KEY,
            contact_id     TEXT NOT NULL,
            type           TEXT NOT NULL,
            direction      TEXT DEFAULT 'outbound',
            subject        TEXT DEFAULT '',
            summary        TEXT DEFAULT '',
            created_at     TEXT NOT NULL,
            FOREIGN KEY (contact_id) REFERENCES contacts(contact_id)
        );

        CREATE TABLE IF NOT EXISTS deals (
            deal_id     TEXT PRIMARY KEY,
            contact_id  TEXT NOT NULL,
            title       TEXT NOT NULL,
            value       REAL DEFAULT 0.0,
            stage       TEXT DEFAULT 'opportunity',
            platform    TEXT DEFAULT '',
            created_at  TEXT NOT NULL,
            closed_at   TEXT DEFAULT '',
            status      TEXT DEFAULT 'open',
            FOREIGN KEY (contact_id) REFERENCES contacts(contact_id)
        );

        CREATE INDEX IF NOT EXISTS idx_contact_stage ON contacts(stage);
        CREATE INDEX IF NOT EXISTS idx_contact_company ON contacts(company);
        CREATE INDEX IF NOT EXISTS idx_deal_status ON deals(status);
    """)
    conn.commit()
    conn.close()


# ── Contact Operations ─────────────────────────────────────────

def add_contact(
    company: str,
    email: str = "",
    name: str = "",
    role: str = "",
    stage: str = "prospect",
    source: str = "manual",
    lead_score: int = 50,
    notes: str = "",
) -> str:
    """Add a new contact. Returns contact_id."""
    init_db()
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    contact_id = str(uuid4())[:8]

    # Check for existing contact by company+email
    existing = conn.execute(
        "SELECT contact_id FROM contacts WHERE lower(company) = ? AND lower(email) = ?",
        (company.lower(), email.lower()),
    ).fetchone()
    if existing:
        conn.close()
        return existing["contact_id"]

    conn.execute(
        """INSERT INTO contacts
           (contact_id, company, name, email, role, stage, lead_score, source, notes, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (contact_id, company, name, email, role, stage, lead_score, source, notes, now, now),
    )
    conn.commit()
    conn.close()
    return contact_id


def update_stage(contact_id: str, new_stage: str):
    """Move a contact to a new pipeline stage."""
    if new_stage not in STAGES:
        return
    init_db()
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE contacts SET stage = ?, updated_at = ? WHERE contact_id = ?",
        (new_stage, now, contact_id),
    )
    conn.commit()
    conn.close()


def log_interaction(
    contact_id: str,
    interaction_type: str,
    direction: str = "outbound",
    subject: str = "",
    summary: str = "",
):
    """Log an interaction with a contact."""
    init_db()
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO interactions (interaction_id, contact_id, type, direction, subject, summary, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid4())[:8], contact_id, interaction_type, direction, subject, summary, now),
    )
    conn.execute(
        "UPDATE contacts SET last_contact = ?, updated_at = ? WHERE contact_id = ?",
        (now, now, contact_id),
    )
    conn.commit()
    conn.close()


def create_deal(contact_id: str, title: str, value: float = 0.0, platform: str = "") -> str:
    """Create a deal/opportunity for a contact."""
    init_db()
    conn = _get_conn()
    deal_id = str(uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO deals (deal_id, contact_id, title, value, platform, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (deal_id, contact_id, title, value, platform, now),
    )
    conn.commit()
    conn.close()
    return deal_id


# ── Sync from Outreach Data ───────────────────────────────────

def sync_from_sent_log():
    """Import contacts from sent_log.json into CRM."""
    if not SENT_LOG.exists():
        return 0

    sent = json.loads(SENT_LOG.read_text(encoding="utf-8"))
    scores = {}
    if SCORES_FILE.exists():
        score_data = json.loads(SCORES_FILE.read_text(encoding="utf-8"))
        scores = {s.get("company", "").lower(): s for s in score_data if isinstance(s, dict)}

    imported = 0
    for entry in sent:
        company = entry.get("company", "")
        email = entry.get("contact_email", "")
        if not company:
            continue

        score_info = scores.get(company.lower(), {})
        lead_score = score_info.get("total_score", 50)

        contact_id = add_contact(
            company=company,
            email=email,
            name=entry.get("contact_name", ""),
            role=entry.get("role", ""),
            stage="contacted",
            source="cold_email",
            lead_score=lead_score,
        )
        log_interaction(
            contact_id=contact_id,
            interaction_type="email",
            direction="outbound",
            subject=entry.get("subject", ""),
            summary=f"Cold email sent via {entry.get('campaign', 'outreach')}",
        )
        imported += 1

    return imported


def sync_from_billing():
    """Check billing.db for paying contacts and update CRM stage to 'client'."""
    if not BILLING_DB.exists():
        return 0

    try:
        bconn = sqlite3.connect(str(BILLING_DB))
        bconn.row_factory = sqlite3.Row
        rows = bconn.execute(
            "SELECT DISTINCT client FROM invoices WHERE status = 'paid'"
        ).fetchall()
        bconn.close()
    except Exception:
        return 0

    init_db()
    conn = _get_conn()
    updated = 0
    now = datetime.now(timezone.utc).isoformat()

    for row in rows:
        client_name = row["client"]
        contact = conn.execute(
            "SELECT contact_id FROM contacts WHERE lower(company) = ?",
            (client_name.lower(),),
        ).fetchone()
        if contact:
            conn.execute(
                "UPDATE contacts SET stage = 'client', updated_at = ? WHERE contact_id = ? AND stage != 'client' AND stage != 'retained'",
                (now, contact["contact_id"]),
            )
            updated += 1

    conn.commit()
    conn.close()
    return updated


# ── Pipeline View ──────────────────────────────────────────────

def get_pipeline() -> dict:
    """Get the deal pipeline grouped by stage."""
    init_db()
    conn = _get_conn()
    pipeline = {}
    for stage in STAGES:
        rows = conn.execute(
            "SELECT * FROM contacts WHERE stage = ? ORDER BY lead_score DESC",
            (stage,),
        ).fetchall()
        pipeline[stage] = [dict(r) for r in rows]
    conn.close()
    return pipeline


def get_stats() -> dict:
    """Get CRM statistics."""
    init_db()
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) as c FROM contacts").fetchone()["c"]
    by_stage = {}
    for stage in STAGES:
        count = conn.execute("SELECT COUNT(*) as c FROM contacts WHERE stage = ?", (stage,)).fetchone()["c"]
        if count > 0:
            by_stage[stage] = count

    deals_open = conn.execute("SELECT COUNT(*) as c FROM deals WHERE status = 'open'").fetchone()["c"]
    deals_value = conn.execute("SELECT COALESCE(SUM(value), 0) as v FROM deals WHERE status = 'open'").fetchone()["v"]
    interactions = conn.execute("SELECT COUNT(*) as c FROM interactions").fetchone()["c"]
    conn.close()

    return {
        "total_contacts": total,
        "by_stage": by_stage,
        "open_deals": deals_open,
        "pipeline_value": deals_value,
        "total_interactions": interactions,
    }


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="CRM Tracker")
    parser.add_argument("--pipeline", action="store_true", help="Show deal pipeline")
    parser.add_argument("--clients", action="store_true", help="List active clients")
    parser.add_argument("--add-lead", nargs=2, metavar=("COMPANY", "EMAIL"), help="Add a lead")
    parser.add_argument("--status", action="store_true", help="CRM health stats")
    parser.add_argument("--sync", action="store_true", help="Sync from sent_log + billing")
    args = parser.parse_args()

    if args.sync:
        imported = sync_from_sent_log()
        billing_updated = sync_from_billing()
        print(f"  Synced: {imported} contacts from sent_log, {billing_updated} stage updates from billing")
    elif args.status:
        stats = get_stats()
        print(f"\n  Total contacts: {stats['total_contacts']}")
        for stage, count in stats["by_stage"].items():
            print(f"    {stage:15s}: {count}")
        print(f"  Open deals: {stats['open_deals']} (${stats['pipeline_value']:.0f})")
        print(f"  Total interactions: {stats['total_interactions']}")
    elif args.pipeline:
        pipeline = get_pipeline()
        for stage, contacts in pipeline.items():
            if contacts:
                print(f"\n  [{stage.upper()}] ({len(contacts)})")
                for c in contacts[:10]:
                    print(f"    {c['company']:30s} | {c['email']:35s} | score={c['lead_score']}")
    elif args.clients:
        pipeline = get_pipeline()
        for stage in ["client", "retained"]:
            for c in pipeline.get(stage, []):
                print(f"  [{stage}] {c['company']:30s} | {c['email']}")
    elif args.add_lead:
        cid = add_contact(company=args.add_lead[0], email=args.add_lead[1], stage="prospect", source="manual")
        print(f"  Added lead: {args.add_lead[0]} → {cid}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
