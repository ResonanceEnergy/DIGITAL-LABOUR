"""OpenClaw Inbox Agent — autonomous inbox sales responder for sales@bit-rage-labour.com.

Reads new inbound leads from data/inbox/, generates contextual AI replies,
sends them via Zoho SMTP, and marks each lead as responded.

Called from NERVE every cycle as Phase 13: Inbox Sales Response.

Handled lead categories:
    lead          → Full pitch reply with service overview + call-to-action
    demo_request  → Trial confirmation + onboarding next steps
    reply         → Warm contextual follow-up matching their concern
    support       → Acknowledge + ETA + escalate to support agent

Usage (standalone):
    python -m openclaw.inbox_agent --check     # List new unresponded leads
    python -m openclaw.inbox_agent --process   # Draft + send responses
    python -m openclaw.inbox_agent --dry-run   # Draft but do NOT send
"""

import argparse
import json
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

INBOX_DIR = PROJECT_ROOT / "data" / "inbox"
RESPONDED_LOG = PROJECT_ROOT / "data" / "inbox_responses.json"
FROM_EMAIL = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "sales@bit-rage-labour.com"))
FROM_NAME = "Bit Rage Labour AI"

# ── SMTP Config ───────────────────────────────────────────────

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.zohocloud.ca")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")


# ── Response Templates (LLM fallback) ────────────────────────

_PROMPTS = {
    "lead": """You are the AI sales assistant for Bit Rage Labour, an autonomous AI agency.
Reply to this inbound lead with a short, confident, personalized email.

Lead email:
From: {from_name} <{from_email}>
Subject: {subject}
Body: {body}

Instructions:
- 3–4 short paragraphs max
- Acknowledge their specific situation
- Briefly explain what Bit Rage Labour does: 24 AI agents handling sales outreach, content, research, proposals, CRM, bookkeeping, and more
- Suggest a 15-min discovery call via Calendly (use placeholder [CALENDLY_LINK])
- Sign off as: The Bit Rage Labour Team | sales@bit-rage-labour.com
- Plain text only, no markdown
- Do NOT include a subject line in the output""",

    "demo_request": """You are the AI sales assistant for Bit Rage Labour, an autonomous AI agency.
Reply to this demo/trial request with a warm, action-oriented email.

Request email:
From: {from_name} <{from_email}>
Subject: {subject}
Body: {body}

Instructions:
- 3 short paragraphs max
- Confirm their request and express enthusiasm
- Tell them their free trial is being set up and they will receive API credentials within 24 hours
- Ask them to reply with: their company name, primary use case, and preferred LLM (OpenAI/Anthropic/Gemini)
- Sign off as: The Bit Rage Labour Team | sales@bit-rage-labour.com
- Plain text only, no markdown
- Do NOT include a subject line""",

    "reply": """You are the AI sales assistant for Bit Rage Labour, an autonomous AI agency.
Reply to this response to our cold outreach email.

Their reply:
From: {from_name} <{from_email}>
Subject: {subject}
Body: {body}

Instructions:
- Keep it short (2–3 paragraphs)
- If they expressed interest: confirm next steps, offer a quick call, include [CALENDLY_LINK]
- If they asked a question: answer it concisely and invite them to continue the conversation
- If they asked to be removed (unsubscribe): politely acknowledge, confirm removal, stop following up
- Sign off as: The Bit Rage Labour Team | sales@bit-rage-labour.com
- Plain text only, no markdown
- Do NOT include a subject line""",

    "support": """You are the customer support AI for Bit Rage Labour.
Reply to this support request professionally.

Support request:
From: {from_name} <{from_email}>
Subject: {subject}
Body: {body}

Instructions:
- Acknowledge the issue within 2 sentences
- Tell them a support specialist will follow up within 4 hours during business hours
- If it looks like a billing issue, mention they can also reach us at sales@bit-rage-labour.com
- Sign off as: Bit Rage Labour Support | sales@bit-rage-labour.com
- Plain text only, no markdown
- Do NOT include a subject line""",
}

_DEFAULT_SUBJECTS = {
    "lead": "Re: {original_subject}",
    "demo_request": "Re: {original_subject} — Trial Setup Confirmed",
    "reply": "Re: {original_subject}",
    "support": "Re: {original_subject} — Support Request Received",
}


# ── Persistence ───────────────────────────────────────────────

def _load_response_log() -> list[dict]:
    if RESPONDED_LOG.exists():
        return json.loads(RESPONDED_LOG.read_text(encoding="utf-8"))
    return []


def _save_response_log(log: list[dict]):
    RESPONDED_LOG.parent.mkdir(parents=True, exist_ok=True)
    RESPONDED_LOG.write_text(json.dumps(log, indent=2), encoding="utf-8")


def _already_responded(from_email: str) -> bool:
    log = _load_response_log()
    responded_emails = {r["to_email"].lower() for r in log}
    return from_email.lower() in responded_emails


# ── Lead Loading ──────────────────────────────────────────────

def load_new_leads() -> list[tuple[Path, dict]]:
    """Return all lead files with status == 'new' that haven't been responded to."""
    if not INBOX_DIR.exists():
        return []

    leads = []
    for f in sorted(INBOX_DIR.glob("lead_*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("status") != "new":
                continue
            from_email = data.get("from_email", "")
            if not from_email or _already_responded(from_email):
                continue
            leads.append((f, data))
        except Exception:
            continue

    return leads


# ── LLM Draft ─────────────────────────────────────────────────

def draft_response(lead: dict) -> Optional[str]:
    """Use LLM to draft a response for the given lead."""
    category = lead.get("type", "lead")
    prompt_template = _PROMPTS.get(category, _PROMPTS["lead"])

    prompt = prompt_template.format(
        from_name=lead.get("from_name", ""),
        from_email=lead.get("from_email", ""),
        subject=lead.get("subject", "(no subject)"),
        body=(lead.get("body_preview", ""))[:800],
    )

    try:
        from utils.llm_client import call_llm
        response = call_llm(
            system_prompt=prompt,
            user_message="Write the response email body now.",
            provider="openai",
            json_mode=False,
            temperature=0.6,
            fallback=True,
        )
        return response.strip()
    except Exception as e:
        # Fallback: generic template
        return (
            f"Hi {lead.get('from_name', 'there')},\n\n"
            "Thank you for reaching out to Bit Rage Labour.\n\n"
            "We'd love to learn more about your needs. Could you share a bit more about "
            "your company and what you're trying to automate or improve?\n\n"
            "You can also book a quick 15-minute call here: [CALENDLY_LINK]\n\n"
            "Looking forward to connecting.\n\n"
            "The Bit Rage Labour Team\nsales@bit-rage-labour.com"
        )


# ── Send Reply ────────────────────────────────────────────────

def send_reply(to_email: str, to_name: str, subject: str, body: str) -> bool:
    """Send a reply email via Zoho SMTP. Returns True on success."""
    if not SMTP_PASS:
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg["To"] = f"{to_name} <{to_email}>" if to_name else to_email
        msg["Subject"] = subject
        msg["Reply-To"] = FROM_EMAIL
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(FROM_EMAIL, [to_email], msg.as_string())

        return True
    except Exception as e:
        print(f"[INBOX_AGENT] SMTP error sending to {to_email}: {e}")
        return False


# ── Mark Lead Responded ───────────────────────────────────────

def _mark_responded(lead_file: Path, lead: dict, sent: bool, body: str):
    """Update the lead file status and append to response log."""
    lead["status"] = "replied" if sent else "draft_ready"
    lead["responded_at"] = datetime.now(timezone.utc).isoformat()
    lead["response_sent"] = sent
    lead_file.write_text(json.dumps(lead, indent=2), encoding="utf-8")

    log = _load_response_log()
    log.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "to_email": lead.get("from_email", ""),
        "to_name": lead.get("from_name", ""),
        "subject": lead.get("subject", ""),
        "category": lead.get("type", "lead"),
        "sent": sent,
        "response_preview": body[:300] if body else "",
        "lead_file": str(lead_file.name),
    })
    _save_response_log(log)


# ── Main Processing Loop ──────────────────────────────────────

def process_new_leads(dry_run: bool = False) -> dict:
    """Process all new inbound leads — draft + send responses.

    Args:
        dry_run: If True, draft responses but do not send emails.

    Returns:
        Summary dict with counts.
    """
    leads = load_new_leads()
    if not leads:
        return {"processed": 0, "sent": 0, "errors": 0, "skipped": 0}

    results = {"processed": 0, "sent": 0, "errors": 0, "skipped": 0, "dry_run": dry_run}

    for lead_file, lead in leads:
        from_email = lead.get("from_email", "")
        from_name = lead.get("from_name", "")
        category = lead.get("type", "lead")
        original_subject = lead.get("subject", "(no subject)")

        # Build reply subject
        subject_template = _DEFAULT_SUBJECTS.get(category, "Re: {original_subject}")
        subject = subject_template.format(original_subject=original_subject)
        if not subject.startswith("Re:"):
            subject = f"Re: {original_subject}"

        print(f"  [INBOX AGENT] Processing: {from_email} ({category})")

        # Draft
        body = draft_response(lead)
        if not body:
            print(f"    → Draft failed, skipping.")
            results["skipped"] += 1
            continue

        results["processed"] += 1

        if dry_run:
            print(f"    → [DRY RUN] Draft ready ({len(body)} chars)")
            _mark_responded(lead_file, lead, sent=False, body=body)
            results["sent"] += 0
            continue

        # Send
        sent = send_reply(to_email=from_email, to_name=from_name, subject=subject, body=body)
        if sent:
            print(f"    → Sent to {from_email}")
            results["sent"] += 1
        else:
            print(f"    → Send failed (SMTP). Draft saved.")
            results["errors"] += 1

        _mark_responded(lead_file, lead, sent=sent, body=body)

    return results


# ── Inbox Check Summary ───────────────────────────────────────

def inbox_check() -> dict:
    """Check and print inbox status without processing."""
    leads = load_new_leads()
    response_log = _load_response_log()

    # Category breakdown of all leads
    all_leads = []
    if INBOX_DIR.exists():
        for f in INBOX_DIR.glob("lead_*.json"):
            try:
                all_leads.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                pass

    cats: dict[str, int] = {}
    statuses: dict[str, int] = {}
    for lead in all_leads:
        cats[lead.get("type", "unknown")] = cats.get(lead.get("type", "unknown"), 0) + 1
        statuses[lead.get("status", "unknown")] = statuses.get(lead.get("status", "unknown"), 0) + 1

    print(f"\n{'='*60}")
    print(f"  OPENCLAW INBOX AGENT — sales@bit-rage-labour.com")
    print(f"{'='*60}")
    print(f"  Total inbound leads: {len(all_leads)}")
    print(f"  Awaiting response:   {len(leads)}")
    print(f"  Responses sent:      {len([r for r in response_log if r.get('sent')])}")
    if cats:
        print(f"\n  By category:")
        for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
            print(f"    {cat:15s}: {count}")
    if statuses:
        print(f"\n  By status:")
        for status, count in sorted(statuses.items(), key=lambda x: -x[1]):
            print(f"    {status:15s}: {count}")

    if leads:
        print(f"\n  Pending responses:")
        for _, lead in leads[:10]:
            print(f"    [{lead.get('type', '?'):12s}] {lead.get('from_email', '?'):30s} — {lead.get('subject', '')[:40]}")

    return {"new": len(leads), "total": len(all_leads), "sent": len(response_log)}


# ── CLI ───────────────────────────────────────────────────────

def _main():
    parser = argparse.ArgumentParser(description="OpenClaw Inbox Agent")
    parser.add_argument("--check", action="store_true", help="Show inbox status")
    parser.add_argument("--process", action="store_true", help="Draft and send responses")
    parser.add_argument("--dry-run", action="store_true", help="Draft but do not send")
    args = parser.parse_args()

    if args.check:
        inbox_check()
    elif args.process:
        print("[INBOX AGENT] Processing new inbound leads...\n")
        result = process_new_leads(dry_run=False)
        print(f"\n  Processed: {result['processed']}")
        print(f"  Sent:      {result['sent']}")
        print(f"  Errors:    {result['errors']}")
    elif args.dry_run:
        print("[INBOX AGENT] Dry run — drafting without sending...\n")
        result = process_new_leads(dry_run=True)
        print(f"\n  Drafted: {result['processed']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    _main()
