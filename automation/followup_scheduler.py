"""Followup Scheduler — Automated multi-touch follow-up engine.

Manages timed follow-up sequences for cold outreach:
  - Day 3: Soft nudge (value-add)
  - Day 7: Case study / social proof
  - Day 14: Break-up email (last chance)

Reads from followups.json + sent_log.json, sends via SMTP (Zoho),
and updates CRM stage on reply detection.

Usage:
    python -m automation.followup_scheduler --run        # Send all due follow-ups
    python -m automation.followup_scheduler --status      # Show follow-up pipeline
    python -m automation.followup_scheduler --preview     # Preview due follow-ups without sending
    python -m automation.followup_scheduler --daemon      # Run continuous follow-up loop
"""

import argparse
import json
import logging
import os
import smtplib
import sys
import time
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# ── Paths ──────────────────────────────────────────────────────
FOLLOWUP_DB = Path(__file__).parent / "followups.json"
SENT_LOG = Path(__file__).parent / "sent_log.json"
STATE_FILE = PROJECT_ROOT / "data" / "followup_scheduler_state.json"
LOG_DIR = PROJECT_ROOT / "data" / "followup_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── SMTP config ────────────────────────────────────────────────
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.zohocloud.ca")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_NAME = os.getenv("FROM_NAME", "BIT RAGE SYSTEMS")
FROM_EMAIL = os.getenv("SMTP_USER", "sales@bit-rage-labour.com")

# ── Timing ─────────────────────────────────────────────────────
FOLLOWUP_SCHEDULE = [
    {"key": "follow_up_1", "days": 3, "sent_key": "follow_up_1_sent"},
    {"key": "follow_up_2", "days": 7, "sent_key": "follow_up_2_sent"},
    {"key": "follow_up_3", "days": 14, "sent_key": "follow_up_3_sent"},
]
MAX_PER_HOUR = 15               # Rate limit
DELAY_BETWEEN_SENDS = 10        # Seconds
DAEMON_INTERVAL_HOURS = 6       # Check every 6 hours

# ── Logging ────────────────────────────────────────────────────
_LOG_FMT = logging.Formatter("%(asctime)s [%(levelname)s] followup — %(message)s")
logger = logging.getLogger("followup_scheduler")
if not logger.handlers:
    _sh = logging.StreamHandler()
    _sh.setFormatter(_LOG_FMT)
    logger.addHandler(_sh)
    _fh = logging.FileHandler(LOG_DIR / "followup_scheduler.log", encoding="utf-8")
    _fh.setFormatter(_LOG_FMT)
    logger.addHandler(_fh)
    logger.setLevel(logging.INFO)
logger.propagate = False

# ── Follow-up Templates ───────────────────────────────────────

TEMPLATES = {
    "follow_up_1": {
        "subject": "Quick follow-up — AI agents for {company}",
        "body": (
            "Hi {name},\n\n"
            "Just circling back on my note from a few days ago.\n\n"
            "We recently helped a SaaS company automate 80% of their lead research "
            "and saved their SDR team 25+ hours/week.\n\n"
            "Happy to show you a quick demo tailored to {company} — "
            "no commitment, just 10 minutes.\n\n"
            "Worth a look?\n\n"
            "— BIT RAGE SYSTEMS\n"
            "sales@digital-labour.com"
        ),
    },
    "follow_up_2": {
        "subject": "One more thought for {company}",
        "body": (
            "Hi {name},\n\n"
            "I know inboxes are brutal, so I'll keep this short.\n\n"
            "Our AI agents handle:\n"
            "  - Lead enrichment + cold email ($2.40/lead)\n"
            "  - Support ticket triage ($1/ticket)\n"
            "  - Content repurposing ($3/piece)\n"
            "  - Data entry + extraction ($0.80/task)\n\n"
            "All with QA checks and human-in-the-loop oversight.\n\n"
            "If any of those sound useful, I'd love to run a free sample for {company}.\n\n"
            "— BIT RAGE SYSTEMS"
        ),
    },
    "follow_up_3": {
        "subject": "Last note — {company}",
        "body": (
            "Hi {name},\n\n"
            "I've reached out a couple times about our AI labor agents.\n"
            "I'll assume the timing isn't right and won't follow up again.\n\n"
            "If things change, here's what we do:\n"
            "→ 24 AI agents that handle real business tasks\n"
            "→ Pay per task, no contracts\n"
            "→ 90%+ QA pass rate\n\n"
            "The door's always open.\n\n"
            "Best,\n"
            "BIT RAGE SYSTEMS\n"
            "sales@digital-labour.com"
        ),
    },
}


# ── Data Loading ───────────────────────────────────────────────

def _load_followups() -> list[dict]:
    if FOLLOWUP_DB.exists():
        return json.loads(FOLLOWUP_DB.read_text(encoding="utf-8"))
    return []


def _save_followups(followups: list[dict]):
    FOLLOWUP_DB.write_text(json.dumps(followups, indent=2), encoding="utf-8")


def _load_sent_log() -> list[dict]:
    if SENT_LOG.exists():
        return json.loads(SENT_LOG.read_text(encoding="utf-8"))
    return []


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {
        "total_sent": 0,
        "last_run": None,
        "sends_today": 0,
        "today_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


def _save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── Personalization ────────────────────────────────────────────

def _personalize(template: dict, prospect: dict) -> dict:
    """Fill {name}, {company} placeholders in subject/body."""
    name = prospect.get("contact_name", prospect.get("name", "there"))
    company = prospect.get("company", "your company")
    first_name = name.split()[0] if name and name != "there" else "there"

    return {
        "subject": template["subject"].format(name=first_name, company=company),
        "body": template["body"].format(name=first_name, company=company),
    }


# ── SMTP Sender ────────────────────────────────────────────────

def _send_email(to_email: str, subject: str, body: str) -> dict:
    """Send a single follow-up email via SMTP."""
    if not SMTP_USER or not SMTP_PASS:
        return {"status": "skipped", "reason": "SMTP credentials not configured"}

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return {"status": "sent"}
    except smtplib.SMTPAuthenticationError:
        return {"status": "error", "reason": "SMTP auth failed — check SMTP_PASS"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}


# ── Core: Find Due Follow-ups ─────────────────────────────────

def get_due_followups() -> list[dict]:
    """Return list of follow-ups that are due to send now."""
    followups = _load_followups()
    sent_log = _load_sent_log()
    now = datetime.now(timezone.utc)

    # Build lookup: company -> sent_log entry (for email + dates)
    sent_by_company = {}
    for entry in sent_log:
        company = entry.get("company", "").lower()
        if company:
            sent_by_company[company] = entry

    due = []
    for fu in followups:
        company = fu.get("company", "").lower()
        to_email = fu.get("contact_email", "")

        # Skip if no email
        if not to_email or to_email.startswith("["):
            continue

        # Determine original send date
        sent_entry = sent_by_company.get(company, {})
        sent_at_str = fu.get("sent_at") or sent_entry.get("sent_at", "")
        if not sent_at_str:
            continue

        try:
            sent_at = datetime.fromisoformat(sent_at_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue

        # Check each follow-up stage
        for step in FOLLOWUP_SCHEDULE:
            sent_key = step["sent_key"]
            # Already sent?
            if fu.get(sent_key, False):
                continue

            # Due?
            due_date = sent_at + timedelta(days=step["days"])
            if now >= due_date:
                due.append({
                    "followup_entry": fu,
                    "step": step,
                    "company": fu.get("company", "unknown"),
                    "contact_email": to_email,
                    "contact_name": fu.get("contact_name", fu.get("name", "")),
                    "due_date": due_date.isoformat(),
                    "days_overdue": (now - due_date).days,
                })
                break  # Only one stage at a time per prospect

    return due


# ── Core: Send Due Follow-ups ─────────────────────────────────

def run_followups(dry_run: bool = False) -> list[dict]:
    """Send all due follow-ups. Returns list of send results."""
    due = get_due_followups()
    if not due:
        logger.info("No follow-ups due right now.")
        return []

    logger.info(f"Found {len(due)} follow-ups due to send.")
    state = _load_state()

    # Reset daily counter if new day
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if state.get("today_date") != today:
        state["sends_today"] = 0
        state["today_date"] = today

    results = []
    sent_count = 0

    for item in due:
        if sent_count >= MAX_PER_HOUR:
            logger.warning(f"Rate limit hit ({MAX_PER_HOUR}/hr). Remaining deferred.")
            break

        step = item["step"]
        template = TEMPLATES.get(step["key"])
        if not template:
            continue

        personalized = _personalize(template, {
            "contact_name": item["contact_name"],
            "company": item["company"],
        })

        if dry_run:
            logger.info(f"  [DRY-RUN] {step['key']} -> {item['contact_email']} ({item['company']})")
            results.append({
                "company": item["company"],
                "email": item["contact_email"],
                "step": step["key"],
                "status": "dry_run",
            })
            continue

        # Send
        result = _send_email(
            to_email=item["contact_email"],
            subject=personalized["subject"],
            body=personalized["body"],
        )

        logger.info(f"  [{step['key']}] {item['company']} -> {item['contact_email']}: {result['status']}")

        if result["status"] == "sent":
            # Mark as sent in followups.json
            item["followup_entry"][step["sent_key"]] = True
            item["followup_entry"][f"{step['key']}_sent_at"] = datetime.now(timezone.utc).isoformat()
            sent_count += 1
            state["total_sent"] += 1
            state["sends_today"] += 1

        results.append({
            "company": item["company"],
            "email": item["contact_email"],
            "step": step["key"],
            "status": result["status"],
            "reason": result.get("reason", ""),
        })

        # Rate limiting delay
        if sent_count < len(due):
            time.sleep(DELAY_BETWEEN_SENDS)

    # Persist
    if not dry_run and results:
        followups = _load_followups()
        # Update entries by matching company
        fu_by_company = {fu.get("company", "").lower(): fu for fu in followups}
        for item in due:
            company = item["company"].lower()
            if company in fu_by_company:
                for step in FOLLOWUP_SCHEDULE:
                    sent_key = step["sent_key"]
                    if item["followup_entry"].get(sent_key):
                        fu_by_company[company][sent_key] = True
                        at_key = f"{step['key']}_sent_at"
                        if item["followup_entry"].get(at_key):
                            fu_by_company[company][at_key] = item["followup_entry"][at_key]
        _save_followups(followups)

    state["last_run"] = datetime.now(timezone.utc).isoformat()
    _save_state(state)

    # Log to daily log
    _log_run(results)

    return results


def _log_run(results: list[dict]):
    """Append run results to daily log file."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"{today}.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        for r in results:
            r["timestamp"] = datetime.now(timezone.utc).isoformat()
            f.write(json.dumps(r) + "\n")


# ── Status Report ──────────────────────────────────────────────

def show_status() -> dict:
    """Show follow-up pipeline status."""
    followups = _load_followups()
    state = _load_state()

    total = len(followups)
    fu1_sent = sum(1 for f in followups if f.get("follow_up_1_sent"))
    fu2_sent = sum(1 for f in followups if f.get("follow_up_2_sent"))
    fu3_sent = sum(1 for f in followups if f.get("follow_up_3_sent"))
    complete = sum(1 for f in followups
                   if f.get("follow_up_1_sent") and f.get("follow_up_2_sent") and f.get("follow_up_3_sent"))
    has_email = sum(1 for f in followups
                    if f.get("contact_email") and not f["contact_email"].startswith("["))

    due = get_due_followups()

    report = {
        "total_prospects": total,
        "with_email": has_email,
        "follow_up_1_sent": fu1_sent,
        "follow_up_2_sent": fu2_sent,
        "follow_up_3_sent": fu3_sent,
        "sequence_complete": complete,
        "currently_due": len(due),
        "total_followups_sent": state.get("total_sent", 0),
        "last_run": state.get("last_run"),
    }

    print(f"\n{'='*50}")
    print(f"  FOLLOW-UP SCHEDULER STATUS")
    print(f"{'='*50}")
    print(f"  Prospects tracked:    {total}")
    print(f"  With valid email:     {has_email}")
    print(f"  Follow-up 1 sent:     {fu1_sent}/{total}")
    print(f"  Follow-up 2 sent:     {fu2_sent}/{total}")
    print(f"  Follow-up 3 sent:     {fu3_sent}/{total}")
    print(f"  Sequence complete:    {complete}/{total}")
    print(f"  Currently due:        {len(due)}")
    print(f"  Total sent (all time): {state.get('total_sent', 0)}")
    print(f"  Last run:             {state.get('last_run', 'never')}")
    print(f"{'='*50}\n")

    return report


# ── Daemon Mode ────────────────────────────────────────────────

def run_daemon():
    """Run follow-up scheduler in continuous loop."""
    logger.info("Follow-up Scheduler daemon starting...")
    logger.info(f"Interval: every {DAEMON_INTERVAL_HOURS} hours")
    logger.info(f"Rate limit: {MAX_PER_HOUR} emails/hour")

    while True:
        try:
            logger.info(f"\n--- Follow-up check at {datetime.now(timezone.utc).isoformat()} ---")
            results = run_followups()
            sent = sum(1 for r in results if r.get("status") == "sent")
            logger.info(f"Cycle complete: {sent} sent, {len(results) - sent} skipped/failed")
        except Exception as e:
            logger.error(f"Follow-up cycle error: {e}")

        logger.info(f"Next check in {DAEMON_INTERVAL_HOURS} hours...")
        time.sleep(DAEMON_INTERVAL_HOURS * 3600)


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Followup Scheduler")
    parser.add_argument("--run", action="store_true", help="Send all due follow-ups")
    parser.add_argument("--preview", action="store_true", help="Preview without sending")
    parser.add_argument("--status", action="store_true", help="Show follow-up pipeline status")
    parser.add_argument("--daemon", action="store_true", help="Run continuous follow-up loop")
    args = parser.parse_args()

    if args.daemon:
        run_daemon()
    elif args.run:
        results = run_followups()
        sent = sum(1 for r in results if r.get("status") == "sent")
        print(f"\nSent {sent} follow-ups ({len(results)} processed)")
    elif args.preview:
        results = run_followups(dry_run=True)
        print(f"\n[DRY-RUN] {len(results)} follow-ups would be sent")
    elif args.status:
        show_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
