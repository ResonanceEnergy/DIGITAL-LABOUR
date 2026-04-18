"""Cold Email Spray — Bulk outreach engine for targeted prospect campaigns.

Loads prospects from prospects.csv (optionally filtered by lead score),
generates personalized cold emails using LLM + templates from
campaign/COLD_EMAIL_SEQUENCES.md, and sends via SMTP (Zoho).

Tracks sends in sent_log.json and schedules follow-ups in followups.json.

Usage:
    python -m automation.cold_email_spray --campaign saas_founders --limit 50
    python -m automation.cold_email_spray --preview 5       # Preview without sending
    python -m automation.cold_email_spray --status           # Campaign stats
    python -m automation.cold_email_spray --followups        # Send due follow-ups
"""

import argparse
import csv
import json
import os
import re
import smtplib
import sys
import time
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Zoho CRM integration — sync prospects as Leads
try:
    from utils.zoho_client import sync_cold_email_prospect
    ZOHO_AVAILABLE = True
except ImportError:
    ZOHO_AVAILABLE = False

PROSPECTS_FILE = Path(__file__).parent / "prospects.csv"
SENT_LOG = Path(__file__).parent / "sent_log.json"
FOLLOWUP_DB = Path(__file__).parent / "followups.json"
SCORES_FILE = PROJECT_ROOT / "data" / "lead_scores.json"
SEQUENCES_FILE = PROJECT_ROOT / "campaign" / "COLD_EMAIL_SEQUENCES.md"
CAMPAIGN_STATE_FILE = PROJECT_ROOT / "data" / "cold_email_state.json"

# SMTP config (Zoho)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.zohocloud.ca")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_NAME = os.getenv("FROM_NAME", "DIGITAL LABOUR")
FROM_EMAIL = os.getenv("SMTP_USER", "sales@bit-rage-labour.com")

# Safety limits
MAX_PER_HOUR = 20          # Zoho rate limit safety
MAX_PER_DAY = 100          # Hard daily cap
DELAY_BETWEEN_SENDS = 8    # Seconds between emails (avoid spam triggers)
FOLLOWUP_DAY_3 = 3         # First follow-up after N days
FOLLOWUP_DAY_7 = 7         # Second follow-up


# ── Data Loading ───────────────────────────────────────────────

def _load_prospects() -> list[dict]:
    if not PROSPECTS_FILE.exists():
        return []
    rows = []
    with open(PROSPECTS_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def _load_sent_log() -> list[dict]:
    if SENT_LOG.exists():
        return json.loads(SENT_LOG.read_text(encoding="utf-8"))
    return []


def _save_sent_log(log: list[dict]):
    SENT_LOG.write_text(json.dumps(log, indent=2), encoding="utf-8")


def _load_followups() -> list[dict]:
    if FOLLOWUP_DB.exists():
        return json.loads(FOLLOWUP_DB.read_text(encoding="utf-8"))
    return []


def _save_followups(followups: list[dict]):
    FOLLOWUP_DB.write_text(json.dumps(followups, indent=2), encoding="utf-8")


def _load_scores() -> dict:
    if SCORES_FILE.exists():
        data = json.loads(SCORES_FILE.read_text(encoding="utf-8"))
        return {s.get("company", "").lower(): s for s in data if isinstance(s, dict)}
    return {}


def _load_campaign_state() -> dict:
    if CAMPAIGN_STATE_FILE.exists():
        return json.loads(CAMPAIGN_STATE_FILE.read_text(encoding="utf-8"))
    return {"campaigns": {}, "total_sent": 0, "last_spray_at": None}


def _save_campaign_state(state: dict):
    CAMPAIGN_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CAMPAIGN_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── Email Sequences ────────────────────────────────────────────

def _load_sequences() -> dict[str, list[dict]]:
    """Parse email sequences from COLD_EMAIL_SEQUENCES.md."""
    if not SEQUENCES_FILE.exists():
        return {"default": [_default_template()]}

    content = SEQUENCES_FILE.read_text(encoding="utf-8")

    sequences = {}
    current_seq = "default"
    current_emails = []

    for section in re.split(r"\n## ", content):
        header_match = re.match(r"(Sequence \d+|[\w\s]+)\n", section)
        if header_match:
            if current_emails:
                sequences[current_seq] = current_emails
            current_seq = header_match.group(1).strip().lower().replace(" ", "_")
            current_emails = []

        # Extract subject/body pairs from code blocks
        blocks = re.findall(r"Subject:\s*(.+?)\n(.*?)(?=Subject:|$)", section, re.DOTALL)
        for subject, body in blocks:
            current_emails.append({
                "subject": subject.strip(),
                "body": body.strip(),
            })

    if current_emails:
        sequences[current_seq] = current_emails

    if not sequences:
        sequences["default"] = [_default_template()]

    return sequences


def _default_template() -> dict:
    return {
        "subject": "AI agents that do your busy work — {company}",
        "body": (
            "Hi {name},\n\n"
            "I noticed {company} is scaling fast — congrats.\n\n"
            "We built 24 AI agents that handle lead gen, data entry, "
            "email outreach, content creation, and more. Clients save "
            "20-40 hours/week.\n\n"
            "Would a quick 10-min demo be worth your time this week?\n\n"
            "— DIGITAL LABOUR\n"
            "sales@bit-rage-labour.com"
        ),
    }


def _personalize(template: dict, prospect: dict) -> dict:
    """Substitute {name}, {company}, {role} placeholders."""
    name = prospect.get("contact_name", prospect.get("name", "there"))
    company = prospect.get("company", "your company")
    role = prospect.get("role", "")

    first_name = name.split()[0] if name and name != "there" else "there"

    subject = template["subject"].format(
        name=first_name, company=company, role=role
    )
    body = template["body"].format(
        name=first_name, company=company, role=role
    )
    return {"subject": subject, "body": body}


# ── SMTP Sender ────────────────────────────────────────────────

def _send_email(to_email: str, subject: str, body: str) -> dict:
    """Send a single email via SMTP. Returns result dict."""
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
        return {"status": "error", "reason": "SMTP auth failed"}
    except smtplib.SMTPRecipientsRefused:
        return {"status": "error", "reason": f"Recipient refused: {to_email}"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}


# ── Campaign Engine ────────────────────────────────────────────

def run_spray(
    campaign_name: str = "default",
    limit: int = 50,
    min_score: int = 0,
    dry_run: bool = False,
) -> dict:
    """Execute a cold email spray campaign.

    Args:
        campaign_name: Which sequence from COLD_EMAIL_SEQUENCES.md to use
        limit: Max prospects to email in this run
        min_score: Only email prospects with lead score >= this value
        dry_run: Preview without sending

    Returns:
        Campaign result dict with sent/skipped/failed counts
    """
    prospects = _load_prospects()
    sent_log = _load_sent_log()
    followups = _load_followups()
    scores = _load_scores()
    sequences = _load_sequences()
    state = _load_campaign_state()

    contacted = {s.get("company", "").lower() for s in sent_log}
    template_list = sequences.get(campaign_name, sequences.get("default", [_default_template()]))
    template = template_list[0] if template_list else _default_template()

    # Filter prospects
    eligible = []
    for p in prospects:
        company_key = p.get("company", "").lower()
        if company_key in contacted:
            continue
        email_addr = p.get("contact_email", p.get("email", ""))
        if not email_addr or "@" not in email_addr:
            continue
        score_data = scores.get(company_key, {})
        prospect_score = score_data.get("total_score", 50)
        if prospect_score < min_score:
            continue
        p["_score"] = prospect_score
        eligible.append(p)

    # Sort by score descending (best prospects first)
    eligible.sort(key=lambda x: x.get("_score", 0), reverse=True)
    batch = eligible[:limit]

    results = {"sent": 0, "skipped": 0, "failed": 0, "previewed": 0, "details": []}
    now = datetime.now(timezone.utc)

    # Check daily cap
    today_str = now.strftime("%Y-%m-%d")
    today_count = sum(
        1 for s in sent_log
        if s.get("sent_at", "").startswith(today_str)
    )
    remaining_today = MAX_PER_DAY - today_count

    print(f"\n{'=' * 60}")
    print(f"  COLD EMAIL SPRAY: {campaign_name}")
    print(f"  Eligible: {len(eligible)} | Batch: {len(batch)} | Daily remaining: {remaining_today}")
    print(f"{'=' * 60}\n")

    for i, prospect in enumerate(batch):
        if results["sent"] >= remaining_today:
            print(f"  [CAP] Daily limit reached ({MAX_PER_DAY})")
            break

        email_addr = prospect.get("contact_email", prospect.get("email", ""))
        company = prospect.get("company", "unknown")
        personalized = _personalize(template, prospect)

        if dry_run:
            print(f"  [PREVIEW] {company:30s} → {email_addr}")
            print(f"            Subject: {personalized['subject']}")
            results["previewed"] += 1
            continue

        result = _send_email(email_addr, personalized["subject"], personalized["body"])

        if result["status"] == "sent":
            results["sent"] += 1
            entry = {
                "id": str(uuid4())[:8],
                "company": company,
                "contact_email": email_addr,
                "contact_name": prospect.get("contact_name", prospect.get("name", "")),
                "role": prospect.get("role", ""),
                "subject": personalized["subject"],
                "campaign": campaign_name,
                "sent_at": now.isoformat(),
                "status": "sent",
                "lead_score": prospect.get("_score", 50),
            }
            sent_log.append(entry)

            # Schedule follow-ups
            followups.append({
                "id": entry["id"],
                "company": company,
                "contact_email": email_addr,
                "followup_number": 1,
                "due_at": (now + timedelta(days=FOLLOWUP_DAY_3)).isoformat(),
                "status": "pending",
            })
            followups.append({
                "id": entry["id"],
                "company": company,
                "contact_email": email_addr,
                "followup_number": 2,
                "due_at": (now + timedelta(days=FOLLOWUP_DAY_7)).isoformat(),
                "status": "pending",
            })

            print(f"  [SENT] {company:30s} → {email_addr} (score={prospect.get('_score', '?')})")

            # Sync prospect to Zoho CRM as a Lead
            if ZOHO_AVAILABLE:
                try:
                    sync_cold_email_prospect({
                        "first_name": prospect.get("contact_name", prospect.get("name", "")).split()[0] if prospect.get("contact_name", prospect.get("name", "")) else "",
                        "last_name": prospect.get("contact_name", prospect.get("name", "Unknown")).split()[-1] if prospect.get("contact_name", prospect.get("name", "")) else "Unknown",
                        "company": company,
                        "email": email_addr,
                        "phone": prospect.get("phone", ""),
                        "score": prospect.get("_score", 50),
                        "industry": prospect.get("industry", ""),
                        "source": "cold_email_spray",
                    })
                except Exception:
                    pass  # CRM sync is non-blocking
        else:
            results["failed"] += 1
            print(f"  [FAIL] {company:30s} → {result.get('reason', 'unknown')}")

        results["details"].append({"company": company, "email": email_addr, **result})

        if i < len(batch) - 1 and not dry_run:
            time.sleep(DELAY_BETWEEN_SENDS)

    if not dry_run:
        _save_sent_log(sent_log)
        _save_followups(followups)
        state["total_sent"] = len(sent_log)
        state["last_spray_at"] = now.isoformat()
        if campaign_name not in state["campaigns"]:
            state["campaigns"][campaign_name] = {"runs": 0, "total_sent": 0}
        state["campaigns"][campaign_name]["runs"] += 1
        state["campaigns"][campaign_name]["total_sent"] += results["sent"]
        _save_campaign_state(state)

    print(f"\n  RESULT: {results['sent']} sent | {results['failed']} failed | {results['previewed']} previewed")
    return results


def send_due_followups(dry_run: bool = False) -> dict:
    """Send all follow-up emails that are due."""
    sent_log = _load_sent_log()
    followups = _load_followups()
    sequences = _load_sequences()
    now = datetime.now(timezone.utc)

    sent_by_id = {s["id"]: s for s in sent_log if "id" in s}
    results = {"sent": 0, "skipped": 0, "not_due": 0}

    for fu in followups:
        if fu.get("status") != "pending":
            continue
        due_at = fu.get("due_at", "")
        if due_at > now.isoformat():
            results["not_due"] += 1
            continue

        original = sent_by_id.get(fu.get("id", ""))
        if not original:
            fu["status"] = "skipped"
            results["skipped"] += 1
            continue

        fu_num = fu.get("followup_number", 1)
        subject = f"Re: {original.get('subject', 'Following up')}"
        body = (
            f"Hi {original.get('contact_name', 'there').split()[0] if original.get('contact_name') else 'there'},\n\n"
            f"Just following up on my previous email about AI automation for {original.get('company', 'your team')}.\n\n"
            f"Our 24 AI agents handle everything from lead gen to data entry — "
            f"saving teams 20-40 hours/week.\n\n"
            f"Worth a quick chat?\n\n"
            f"— DIGITAL LABOUR"
        )

        if dry_run:
            print(f"  [PREVIEW FOLLOWUP #{fu_num}] {original.get('company', '?')} → {fu.get('contact_email', '?')}")
            continue

        result = _send_email(fu["contact_email"], subject, body)
        if result["status"] == "sent":
            fu["status"] = "sent"
            fu["sent_at"] = now.isoformat()
            results["sent"] += 1
            print(f"  [FOLLOWUP #{fu_num}] {original.get('company', '?')} → sent")
            time.sleep(DELAY_BETWEEN_SENDS)
        else:
            fu["status"] = "failed"
            results["skipped"] += 1

    if not dry_run:
        _save_followups(followups)

    return results


def get_campaign_status() -> dict:
    """Return campaign stats."""
    state = _load_campaign_state()
    sent_log = _load_sent_log()
    followups = _load_followups()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_sent = sum(1 for s in sent_log if s.get("sent_at", "").startswith(today))
    pending_followups = sum(1 for f in followups if f.get("status") == "pending")
    due_followups = sum(
        1 for f in followups
        if f.get("status") == "pending" and f.get("due_at", "Z") <= datetime.now(timezone.utc).isoformat()
    )

    return {
        "total_sent": len(sent_log),
        "sent_today": today_sent,
        "daily_remaining": MAX_PER_DAY - today_sent,
        "pending_followups": pending_followups,
        "due_followups": due_followups,
        "campaigns": state.get("campaigns", {}),
        "last_spray": state.get("last_spray_at"),
    }


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Cold Email Spray")
    parser.add_argument("--campaign", default="default", help="Campaign/sequence name")
    parser.add_argument("--limit", type=int, default=50, help="Max emails to send")
    parser.add_argument("--min-score", type=int, default=0, help="Min lead score")
    parser.add_argument("--preview", type=int, nargs="?", const=5, help="Preview N emails")
    parser.add_argument("--followups", action="store_true", help="Send due follow-ups")
    parser.add_argument("--status", action="store_true", help="Show campaign stats")
    args = parser.parse_args()

    if args.status:
        status = get_campaign_status()
        print(f"\n  Total sent: {status['total_sent']}")
        print(f"  Sent today: {status['sent_today']} / {MAX_PER_DAY}")
        print(f"  Pending follow-ups: {status['pending_followups']}")
        print(f"  Due follow-ups: {status['due_followups']}")
        print(f"  Last spray: {status['last_spray']}")
        for name, data in status.get("campaigns", {}).items():
            print(f"  Campaign '{name}': {data['total_sent']} sent in {data['runs']} runs")
    elif args.followups:
        send_due_followups()
    elif args.preview is not None:
        run_spray(args.campaign, limit=args.preview, min_score=args.min_score, dry_run=True)
    else:
        run_spray(args.campaign, limit=args.limit, min_score=args.min_score)


if __name__ == "__main__":
    main()
