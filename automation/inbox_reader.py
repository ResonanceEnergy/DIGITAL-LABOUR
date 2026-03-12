"""Inbox Reader — IMAP monitor for sales@bit-rage-labour.com.

Reads incoming emails, classifies them (lead, reply, demo request, spam),
and routes them into the outreach pipeline or flags for human review.

Usage:
    python -m automation.inbox_reader --check          # Check new unread emails
    python -m automation.inbox_reader --status          # Show inbox stats
    python -m automation.inbox_reader --process         # Check + auto-classify + route
    python -m automation.inbox_reader --watch           # Poll every 5 min (daemon)
    python -m automation.inbox_reader --watch --interval 120  # Custom poll interval
"""

import argparse
import email
import imaplib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

INBOX_LOG = Path(__file__).parent / "inbox_log.json"
INBOX_DIR = PROJECT_ROOT / "data" / "inbox"

# ── IMAP Config ────────────────────────────────────────────────

IMAP_HOST = os.getenv("IMAP_HOST", "imappro.zohocloud.ca")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
IMAP_USER = os.getenv("SMTP_USER", "")  # Same creds as SMTP
IMAP_PASS = os.getenv("SMTP_PASS", "")  # Same creds as SMTP

# ── Email Categories ───────────────────────────────────────────

CATEGORIES = {
    "lead": "New inbound lead — someone wants to buy / try our agents",
    "demo_request": "Demo or trial request from the website",
    "reply": "Reply to an outreach email we sent",
    "support": "Customer support request or issue",
    "subscription": "Billing / subscription inquiry",
    "spam": "Spam, marketing, or irrelevant",
    "internal": "System notification, Stripe alert, etc.",
    "unknown": "Could not classify",
}

# Subject patterns for fast classification (before LLM fallback)
SUBJECT_PATTERNS = [
    (r"free\s*(trial|leads?|demo|sample|extract)", "demo_request"),
    (r"sales\s*ops.*(?:free|trial|started)", "demo_request"),
    (r"support\s*resolver.*(?:free|trial|started)", "demo_request"),
    (r"content\s*repurpos.*(?:free|sample|started)", "demo_request"),
    (r"document\s*extract.*(?:free|extract|started)", "demo_request"),
    (r"custom\s*agent\s*(?:inquiry|build|quote)", "lead"),
    (r"retainer\s*(?:inquiry|pricing)", "lead"),
    (r"custom\s*demo\s*request", "demo_request"),
    (r"get\s*started", "demo_request"),
    (r"re:\s*", "reply"),  # replies start with Re:
    (r"(?:stripe|invoice|payment|subscription)", "internal"),
    (r"(?:unsubscribe|opt.out|remove.*list)", "spam"),
    (r"(?:viagra|casino|lottery|nigerian|prince|crypto.*airdrop)", "spam"),
]


# ── Data Persistence ───────────────────────────────────────────

def _load_inbox_log() -> list[dict]:
    if INBOX_LOG.exists():
        return json.loads(INBOX_LOG.read_text(encoding="utf-8"))
    return []


def _save_inbox_log(log: list[dict]):
    INBOX_LOG.write_text(json.dumps(log, indent=2), encoding="utf-8")


def _seen_message_ids() -> set:
    return {m["message_id"] for m in _load_inbox_log() if "message_id" in m}


# ── IMAP Connection ───────────────────────────────────────────

def connect_imap() -> imaplib.IMAP4_SSL:
    """Connect to Zoho IMAP and authenticate."""
    if not IMAP_USER or not IMAP_PASS:
        print("[INBOX] ERROR: SMTP_USER / SMTP_PASS not configured in .env")
        sys.exit(1)

    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    conn.login(IMAP_USER, IMAP_PASS)
    return conn


def _decode_header_value(raw) -> str:
    """Decode an email header that may be encoded."""
    if raw is None:
        return ""
    parts = decode_header(raw)
    decoded = []
    for data, charset in parts:
        if isinstance(data, bytes):
            decoded.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(data)
    return " ".join(decoded)


def _get_body(msg: email.message.Message) -> str:
    """Extract plain-text body from an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in disp:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        # Fallback to HTML if no plain text
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    raw_html = payload.decode(charset, errors="replace")
                    # Strip HTML tags for classification
                    return re.sub(r"<[^>]+>", " ", raw_html).strip()
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return ""


# ── Fetch Emails ───────────────────────────────────────────────

def fetch_unread(conn: imaplib.IMAP4_SSL, folder: str = "INBOX", limit: int = 50) -> list[dict]:
    """Fetch unread emails from the specified folder."""
    conn.select(folder, readonly=True)
    _, data = conn.search(None, "UNSEEN")

    if not data or not data[0]:
        return []

    msg_ids = data[0].split()
    if limit:
        msg_ids = msg_ids[-limit:]  # Most recent first

    seen = _seen_message_ids()
    emails = []

    for mid in msg_ids:
        _, msg_data = conn.fetch(mid, "(RFC822)")
        if not msg_data or not msg_data[0]:
            continue

        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        message_id = msg.get("Message-ID", "")
        if message_id in seen:
            continue

        subject = _decode_header_value(msg.get("Subject", ""))
        from_name, from_email = parseaddr(msg.get("From", ""))
        from_name = _decode_header_value(from_name) if from_name else ""
        to_addr = parseaddr(msg.get("To", ""))[1]
        date_str = msg.get("Date", "")
        body = _get_body(msg)

        try:
            received_at = parsedate_to_datetime(date_str).isoformat()
        except Exception:
            received_at = datetime.now(timezone.utc).isoformat()

        # Check for In-Reply-To (indicates a reply to our outreach)
        in_reply_to = msg.get("In-Reply-To", "")
        references = msg.get("References", "")

        emails.append({
            "imap_id": mid.decode() if isinstance(mid, bytes) else str(mid),
            "message_id": message_id,
            "from_name": from_name,
            "from_email": from_email,
            "to": to_addr,
            "subject": subject,
            "body": body[:3000],  # Cap body for classification
            "received_at": received_at,
            "in_reply_to": in_reply_to,
            "references": references,
        })

    return emails


def fetch_all_folders(conn: imaplib.IMAP4_SSL) -> dict:
    """List all IMAP folders."""
    _, folders = conn.list()
    result = []
    if folders:
        for f in folders:
            if isinstance(f, bytes):
                # Parse folder name from IMAP response
                match = re.search(rb'"([^"]*)"$|(\S+)$', f)
                if match:
                    name = (match.group(1) or match.group(2)).decode("utf-8", errors="replace")
                    result.append(name)
    return result


# ── Classification ─────────────────────────────────────────────

def classify_email(email_data: dict) -> str:
    """Classify an email into a category using pattern matching + LLM fallback."""
    subject = email_data.get("subject", "").lower()
    from_email = email_data.get("from_email", "").lower()
    body = email_data.get("body", "").lower()

    # Check if it's a reply to our outreach
    if email_data.get("in_reply_to") or email_data.get("references"):
        return "reply"

    # Pattern match on subject
    for pattern, category in SUBJECT_PATTERNS:
        if re.search(pattern, subject, re.IGNORECASE):
            # "Re:" alone isn't enough — check if it matches something more specific first
            if category == "reply" and not email_data.get("in_reply_to"):
                continue
            return category

    # Check for common service/notification senders
    system_senders = ["noreply@", "no-reply@", "notifications@", "mailer-daemon@",
                      "postmaster@", "stripe.com", "zoho.com"]
    if any(s in from_email for s in system_senders):
        return "internal"

    # Check body for buying signals
    buy_signals = ["interested in", "looking for", "need help with", "want to try",
                   "pricing", "how much", "quote", "proposal", "can you",
                   "our company", "we need", "budget"]
    if any(sig in body for sig in buy_signals):
        return "lead"

    # LLM classification for ambiguous emails
    try:
        from utils.llm_client import call_llm
        prompt = f"""Classify this inbound email to a B2B AI labor company (sales@bit-rage-labour.com).

From: {email_data.get('from_name', '')} <{email_data.get('from_email', '')}>
Subject: {email_data.get('subject', '')}
Body (first 500 chars): {body[:500]}

Categories: lead, demo_request, reply, support, subscription, spam, internal, unknown.
Respond with ONLY the category name, nothing else."""

        result = call_llm(prompt, provider="openai", max_tokens=20)
        category = result.strip().lower().replace('"', '').replace("'", "")
        if category in CATEGORIES:
            return category
    except Exception:
        pass

    return "unknown"


def extract_contact_info(email_data: dict) -> dict:
    """Extract structured contact info from an email."""
    body = email_data.get("body", "")

    # Try to extract company name from email domain
    from_email = email_data.get("from_email", "")
    domain = from_email.split("@")[1] if "@" in from_email else ""
    # Skip generic providers
    generic = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
               "aol.com", "icloud.com", "protonmail.com", "mail.com"]
    company_domain = domain if domain and domain not in generic else ""

    # Try to find company name in body
    company_match = re.search(
        r"(?:company|organization|we are|from)\s*:?\s*([A-Z][A-Za-z0-9 &]{2,30})",
        body
    )

    return {
        "name": email_data.get("from_name", ""),
        "email": from_email,
        "company_domain": company_domain,
        "company_name": company_match.group(1).strip() if company_match else "",
        "subject": email_data.get("subject", ""),
    }


# ── Processing Pipeline ───────────────────────────────────────

def process_email(email_data: dict) -> dict:
    """Classify and route a single email."""
    category = classify_email(email_data)
    contact = extract_contact_info(email_data)

    result = {
        **email_data,
        "category": category,
        "category_desc": CATEGORIES.get(category, ""),
        "contact": contact,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "actioned": False,
    }

    return result


def route_processed(processed: list[dict]) -> dict:
    """Route processed emails to appropriate handlers."""
    routed = {"leads": [], "demos": [], "replies": [], "support": [], "spam": [], "other": []}

    for p in processed:
        cat = p["category"]
        if cat == "lead":
            routed["leads"].append(p)
            _save_lead(p)
        elif cat == "demo_request":
            routed["demos"].append(p)
            _save_lead(p)
        elif cat == "reply":
            routed["replies"].append(p)
            _match_reply(p)
        elif cat == "support":
            routed["support"].append(p)
        elif cat == "spam":
            routed["spam"].append(p)
        else:
            routed["other"].append(p)

    return routed


def _save_lead(processed_email: dict):
    """Save an inbound lead to the inbox directory for follow-up."""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    contact = processed_email["contact"]
    safe_email = contact["email"].replace("@", "_at_").replace(".", "_")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    lead_file = INBOX_DIR / f"lead_{ts}_{safe_email}.json"
    lead_data = {
        "type": processed_email["category"],
        "from_name": contact["name"],
        "from_email": contact["email"],
        "company": contact["company_name"] or contact["company_domain"],
        "subject": processed_email["subject"],
        "body_preview": processed_email["body"][:500],
        "received_at": processed_email["received_at"],
        "processed_at": processed_email["processed_at"],
        "status": "new",
        "notes": "",
    }
    lead_file.write_text(json.dumps(lead_data, indent=2), encoding="utf-8")
    print(f"  [LEAD] Saved: {contact['email']} — {processed_email['subject'][:60]}")


def _match_reply(processed_email: dict):
    """Match a reply to an existing outreach in sent_log."""
    from_email = processed_email["from_email"].lower()
    sent_log_path = Path(__file__).parent / "sent_log.json"

    if not sent_log_path.exists():
        return

    sent_log = json.loads(sent_log_path.read_text(encoding="utf-8"))
    for entry in sent_log:
        if entry.get("contact_email", "").lower() == from_email:
            entry["replied"] = True
            entry["reply_at"] = processed_email["received_at"]
            entry["reply_subject"] = processed_email["subject"]
            print(f"  [REPLY] Matched: {from_email} replied to outreach for {entry.get('company', '?')}")
            break

    sent_log_path.write_text(json.dumps(sent_log, indent=2), encoding="utf-8")

    # Also save as lead since a reply = warm lead
    _save_lead(processed_email)


# ── CLI Commands ───────────────────────────────────────────────

def check_inbox(verbose: bool = True) -> list[dict]:
    """Check for new unread emails."""
    print(f"\n[INBOX] Connecting to {IMAP_HOST}...")
    conn = connect_imap()

    emails = fetch_unread(conn)
    conn.logout()

    if not emails:
        if verbose:
            print("[INBOX] No new unread emails.")
        return []

    if verbose:
        print(f"[INBOX] Found {len(emails)} new email(s):\n")
        for i, e in enumerate(emails, 1):
            print(f"  {i}. From: {e['from_name']} <{e['from_email']}>")
            print(f"     Subject: {e['subject']}")
            print(f"     Date: {e['received_at']}")
            print(f"     Preview: {e['body'][:120].replace(chr(10), ' ')}...")
            print()

    return emails


def process_inbox() -> dict:
    """Check inbox, classify, route, and log all new emails."""
    emails = check_inbox(verbose=False)
    if not emails:
        print("[INBOX] No new emails to process.")
        return {"processed": 0}

    print(f"[INBOX] Processing {len(emails)} email(s)...\n")

    processed = []
    for e in emails:
        result = process_email(e)
        processed.append(result)

        icon = {
            "lead": "💰", "demo_request": "🎯", "reply": "↩️",
            "support": "🔧", "spam": "🗑️", "internal": "⚙️", "unknown": "❓",
            "subscription": "💳",
        }.get(result["category"], "📧")

        print(f"  {icon} [{result['category'].upper():12s}] {result['from_email']:30s} — {result['subject'][:50]}")

    # Route to handlers
    routed = route_processed(processed)

    # Log everything
    inbox_log = _load_inbox_log()
    inbox_log.extend(processed)
    _save_inbox_log(inbox_log)

    # Summary
    print(f"\n{'─'*50}")
    print(f"  Processed: {len(processed)}")
    for key, items in routed.items():
        if items:
            print(f"  {key.title():10s}: {len(items)}")

    leads_count = len(routed["leads"]) + len(routed["demos"])
    if leads_count:
        print(f"\n  🔥 {leads_count} new lead(s) saved to data/inbox/")

    return {
        "processed": len(processed),
        "leads": len(routed["leads"]),
        "demos": len(routed["demos"]),
        "replies": len(routed["replies"]),
        "spam": len(routed["spam"]),
    }


def inbox_status():
    """Show inbox processing stats."""
    log = _load_inbox_log()

    print(f"\n{'='*50}")
    print("  INBOX STATUS — sales@bit-rage-labour.com")
    print(f"{'='*50}")

    if not log:
        print("  No emails processed yet.")
        print(f"  Run: python -m automation.inbox_reader --check")
        return

    # Category breakdown
    cats = {}
    for entry in log:
        cat = entry.get("category", "unknown")
        cats[cat] = cats.get(cat, 0) + 1

    print(f"\n  Total processed: {len(log)}")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        desc = CATEGORIES.get(cat, "")
        print(f"  {cat:15s}: {count:3d}  — {desc}")

    # Recent leads
    leads_dir = INBOX_DIR
    if leads_dir.exists():
        lead_files = sorted(leads_dir.glob("lead_*.json"), reverse=True)
        if lead_files:
            print(f"\n  Recent leads ({len(lead_files)} total):")
            for lf in lead_files[:5]:
                data = json.loads(lf.read_text(encoding="utf-8"))
                status = data.get("status", "new")
                print(f"    [{status:8s}] {data.get('from_email', '?'):30s} — {data.get('subject', '')[:40]}")

    # Connection test
    try:
        conn = connect_imap()
        conn.select("INBOX", readonly=True)
        _, data = conn.search(None, "UNSEEN")
        unread = len(data[0].split()) if data and data[0] else 0
        _, data = conn.search(None, "ALL")
        total = len(data[0].split()) if data and data[0] else 0
        conn.logout()
        print(f"\n  Mailbox: {unread} unread / {total} total")
        print(f"  IMAP: CONNECTED ✓")
    except Exception as e:
        print(f"\n  IMAP: FAILED — {e}")


def watch_inbox(interval: int = 300):
    """Poll inbox at a regular interval."""
    print(f"[INBOX] Watching sales@bit-rage-labour.com (every {interval}s)")
    print(f"[INBOX] Press Ctrl+C to stop\n")

    while True:
        try:
            result = process_inbox()
            if result["processed"]:
                print(f"[INBOX] Cycle complete. Next check in {interval}s\n")
            else:
                now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
                print(f"[INBOX] {now} — no new mail. Next check in {interval}s")
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[INBOX] Watcher stopped.")
            break
        except Exception as e:
            print(f"[INBOX] Error: {e}. Retrying in {interval}s")
            time.sleep(interval)


# ── Entry Point ────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Inbox Reader — IMAP email monitor")
    parser.add_argument("--check", action="store_true", help="Check for new unread emails")
    parser.add_argument("--process", action="store_true", help="Check + classify + route emails")
    parser.add_argument("--status", action="store_true", help="Show inbox stats")
    parser.add_argument("--watch", action="store_true", help="Poll inbox continuously")
    parser.add_argument("--interval", type=int, default=300, help="Poll interval in seconds (default: 300)")
    parser.add_argument("--folders", action="store_true", help="List all IMAP folders")
    args = parser.parse_args()

    if args.status:
        inbox_status()
    elif args.folders:
        conn = connect_imap()
        folders = fetch_all_folders(conn)
        conn.logout()
        print(f"\n  IMAP Folders ({len(folders)}):")
        for f in folders:
            print(f"    {f}")
    elif args.watch:
        watch_inbox(args.interval)
    elif args.process:
        process_inbox()
    elif args.check:
        check_inbox()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
