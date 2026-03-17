"""Email Tracker — Tracks outreach email responses, open rates, and reply chains.

Consolidates sent_log.json, followups.json, and inbox_reader results into a
unified view of the outreach funnel: Sent → Opened → Replied → Converted.

Usage:
    python -m automation.email_tracker --funnel         # Show full funnel
    python -m automation.email_tracker --replies         # Show all replies
    python -m automation.email_tracker --stale           # Find stale (no response) leads
    python -m automation.email_tracker --sync            # Sync inbox replies into tracking
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SENT_LOG = Path(__file__).parent / "sent_log.json"
FOLLOWUP_DB = Path(__file__).parent / "followups.json"
INBOX_DIR = PROJECT_ROOT / "data" / "inbox"
TRACKER_FILE = PROJECT_ROOT / "data" / "email_tracker.json"


# ── Data Loading ───────────────────────────────────────────────

def _load_sent_log() -> list[dict]:
    if SENT_LOG.exists():
        return json.loads(SENT_LOG.read_text(encoding="utf-8"))
    return []


def _load_followups() -> list[dict]:
    if FOLLOWUP_DB.exists():
        return json.loads(FOLLOWUP_DB.read_text(encoding="utf-8"))
    return []


def _load_inbox_leads() -> list[dict]:
    """Load lead files from inbox directory."""
    leads = []
    if not INBOX_DIR.exists():
        return leads
    for f in INBOX_DIR.glob("lead_*.json"):
        try:
            leads.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return leads


# ── Tracking Engine ────────────────────────────────────────────

def build_tracking_report() -> dict:
    """Build a comprehensive email tracking report."""
    sent_log = _load_sent_log()
    followups = _load_followups()
    inbox_leads = _load_inbox_leads()

    now = datetime.now(timezone.utc)

    # Build per-company tracking
    companies = {}
    for entry in sent_log:
        company = entry.get("company", "unknown").lower()
        if company not in companies:
            companies[company] = {
                "company": entry.get("company", "unknown"),
                "contact_email": entry.get("contact_email", ""),
                "contact_name": entry.get("contact_name", ""),
                "role": entry.get("role", ""),
                "first_sent": entry.get("sent_at", ""),
                "emails_sent": 0,
                "followups_sent": 0,
                "replied": False,
                "reply_at": None,
                "status": "sent",
                "days_since_first": 0,
            }
        companies[company]["emails_sent"] += 1
        if entry.get("replied"):
            companies[company]["replied"] = True
            companies[company]["reply_at"] = entry.get("reply_at")
            companies[company]["status"] = "replied"

    # Match followups
    for fu in followups:
        company = fu.get("company", "").lower()
        if company in companies:
            sent_count = 0
            if fu.get("follow_up_1_sent"):
                sent_count += 1
            if fu.get("follow_up_2_sent"):
                sent_count += 1
            companies[company]["followups_sent"] = sent_count

    # Match inbox replies
    reply_emails = {lead.get("from_email", "").lower() for lead in inbox_leads}
    for company, data in companies.items():
        contact = data.get("contact_email", "").lower()
        if contact and contact in reply_emails:
            data["replied"] = True
            data["status"] = "replied"

    # Calculate ages
    for data in companies.values():
        first = data.get("first_sent")
        if first:
            try:
                first_dt = datetime.fromisoformat(first)
                data["days_since_first"] = (now - first_dt).days
            except Exception:
                pass

        # Classify status
        if data["replied"]:
            data["status"] = "replied"
        elif data["days_since_first"] > 14 and data["followups_sent"] >= 2:
            data["status"] = "dead"
        elif data["days_since_first"] > 7 and data["followups_sent"] < 2:
            data["status"] = "stale"
        elif data["followups_sent"] > 0:
            data["status"] = "following_up"

    # Funnel metrics
    total_sent = len(sent_log)
    unique_companies = len(companies)
    total_replied = sum(1 for c in companies.values() if c["replied"])
    total_stale = sum(1 for c in companies.values() if c["status"] == "stale")
    total_dead = sum(1 for c in companies.values() if c["status"] == "dead")
    total_following = sum(1 for c in companies.values() if c["status"] == "following_up")
    total_fu_sent = sum(c["followups_sent"] for c in companies.values())

    reply_rate = (total_replied / unique_companies * 100) if unique_companies else 0

    report = {
        "generated_at": now.isoformat(),
        "funnel": {
            "total_emails_sent": total_sent,
            "unique_companies": unique_companies,
            "followups_sent": total_fu_sent,
            "replies_received": total_replied,
            "reply_rate_pct": round(reply_rate, 1),
            "stale_leads": total_stale,
            "dead_leads": total_dead,
            "active_followups": total_following,
        },
        "companies": list(companies.values()),
    }

    # Save report
    TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


def sync_inbox_replies():
    """Scan inbox for replies and update sent_log with reply status."""
    inbox_leads = _load_inbox_leads()
    if not inbox_leads:
        print("[EMAIL TRACKER] No inbox leads to sync.")
        return 0

    sent_log = _load_sent_log()
    reply_map = {}
    for lead in inbox_leads:
        email = lead.get("from_email", "").lower()
        if email:
            reply_map[email] = lead

    matches = 0
    for entry in sent_log:
        contact = entry.get("contact_email", "").lower()
        if contact in reply_map and not entry.get("replied"):
            entry["replied"] = True
            entry["reply_at"] = reply_map[contact].get("received_at")
            entry["reply_subject"] = reply_map[contact].get("subject", "")
            matches += 1
            print(f"  [MATCH] {contact} replied to {entry.get('company', '?')}")

    if matches > 0:
        SENT_LOG.write_text(json.dumps(sent_log, indent=2), encoding="utf-8")
        print(f"[EMAIL TRACKER] Synced {matches} replies into sent_log.")

    return matches


def get_stale_leads(days: int = 7) -> list[dict]:
    """Find leads with no response after N days and fewer than 2 follow-ups."""
    report = build_tracking_report()
    stale = [
        c for c in report["companies"]
        if c["status"] in ("stale", "sent")
        and c["days_since_first"] >= days
        and c["followups_sent"] < 2
    ]
    return stale


def get_replied_leads() -> list[dict]:
    """Get all leads that have replied."""
    report = build_tracking_report()
    return [c for c in report["companies"] if c["replied"]]


# ── Display ────────────────────────────────────────────────────

def show_funnel():
    """Display the full email funnel."""
    report = build_tracking_report()
    f = report["funnel"]

    print(f"\n{'='*60}")
    print(f"  EMAIL TRACKING FUNNEL")
    print(f"  {report['generated_at'][:16]} UTC")
    print(f"{'='*60}")
    print(f"""
  SENT ─────────────── {f['total_emails_sent']} emails to {f['unique_companies']} companies
    │
  FOLLOWED UP ──────── {f['followups_sent']} follow-ups sent
    │
  REPLIED ──────────── {f['replies_received']} replies ({f['reply_rate_pct']}% rate)
    │
  STALE ────────────── {f['stale_leads']} (>7 days, no reply, <2 follow-ups)
    │
  DEAD ─────────────── {f['dead_leads']} (>14 days, 2+ follow-ups, no reply)
    │
  ACTIVE ───────────── {f['active_followups']} in follow-up sequence
""")

    # Show replied leads
    replied = [c for c in report["companies"] if c["replied"]]
    if replied:
        print(f"  ── LEADS THAT REPLIED ──")
        for r in replied:
            print(f"    {r['company']:30s} {r['contact_email']:40s} replied {r.get('reply_at', '?')[:10]}")

    # Show stale leads
    stale = [c for c in report["companies"] if c["status"] == "stale"]
    if stale:
        print(f"\n  ── STALE LEADS (need follow-up) ──")
        for s in stale[:10]:
            print(f"    {s['company']:30s} {s['contact_email']:40s} {s['days_since_first']}d ago, {s['followups_sent']} FU")


def show_replies():
    """Show all reply details."""
    replied = get_replied_leads()
    print(f"\n{'='*60}")
    print(f"  REPLIES RECEIVED: {len(replied)}")
    print(f"{'='*60}")
    for r in replied:
        print(f"\n  {r['company']} — {r['contact_name']}")
        print(f"  Email: {r['contact_email']}")
        print(f"  First sent: {r.get('first_sent', '?')[:10]}")
        print(f"  Replied at: {r.get('reply_at', '?')[:10]}")


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Email Tracker — Outreach funnel analytics")
    parser.add_argument("--funnel", action="store_true", help="Show full funnel")
    parser.add_argument("--replies", action="store_true", help="Show all replies")
    parser.add_argument("--stale", action="store_true", help="Show stale leads")
    parser.add_argument("--sync", action="store_true", help="Sync inbox replies")
    args = parser.parse_args()

    if args.sync:
        sync_inbox_replies()
        show_funnel()
    elif args.replies:
        show_replies()
    elif args.stale:
        stale = get_stale_leads()
        print(f"\n[STALE LEADS] {len(stale)} leads need follow-up:")
        for s in stale:
            print(f"  {s['company']:30s} {s['days_since_first']}d ago, {s['followups_sent']} follow-ups sent")
    else:
        show_funnel()
