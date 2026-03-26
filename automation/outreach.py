"""Outreach automation — generates leads, sends emails, tracks follow-ups.

Chains meta/self_sell.py → delivery/sender.py → follow-up scheduler.
Handles the full outreach lifecycle: generate → review → send → follow-up.

Usage:
    python -m automation.outreach --generate 10        # Generate 10 leads from prospects.csv
    python -m automation.outreach --send-approved       # Send all approved outreach via email
    python -m automation.outreach --follow-up            # Send due follow-ups
    python -m automation.outreach --status               # Show pipeline status
    python -m automation.outreach --auto-approve         # Auto-approve PASS leads + send
"""

import argparse
import csv
import io
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── UTF-8 stdout fix for Windows (prevents charmap crashes) ────
if sys.stdout and hasattr(sys.stdout, 'encoding') and sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

PROSPECTS_FILE = Path(__file__).parent / "prospects.csv"
OUTREACH_DIR = PROJECT_ROOT / "output" / "meta_outreach"
SENT_LOG = Path(__file__).parent / "sent_log.json"
FOLLOWUP_DB = Path(__file__).parent / "followups.json"


# ── Prospect Management ────────────────────────────────────────

def load_prospects() -> list[dict]:
    """Load prospects from CSV, skip already-contacted ones."""
    if not PROSPECTS_FILE.exists():
        return []
    sent = _load_sent_log()
    contacted = {s["company"].lower() for s in sent}

    prospects = []
    with open(PROSPECTS_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["company"].lower() not in contacted:
                prospects.append(row)
    return prospects


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


# ── Generate Outreach ──────────────────────────────────────────

def generate_batch(count: int = 10, priority: str = "all") -> list[dict]:
    """Generate outreach for N prospects using self-sell pipeline."""
    from meta.self_sell import run_self_sell

    prospects = load_prospects()
    if priority != "all":
        prospects = [p for p in prospects if p.get("priority") == priority]

    batch = prospects[:count]
    if not batch:
        print("[OUTREACH] No remaining prospects to contact.")
        return []

    print(f"[OUTREACH] Generating {len(batch)} leads...")
    results = []

    for i, prospect in enumerate(batch, 1):
        print(f"\n[{i}/{len(batch)}] {prospect['company']} — {prospect['role']}")
        try:
            result = run_self_sell(
                company=prospect["company"],
                role=prospect["role"],
                service="full_suite",
            )
            results.append({
                "company": prospect["company"],
                "role": prospect["role"],
                "vertical": prospect.get("vertical", ""),
                "qa_status": result.get("qa_status", "UNKNOWN"),
                "file": result.get("file", ""),
            })
        except Exception as e:
            print(f"  [ERROR] {e}")
            results.append({
                "company": prospect["company"],
                "role": prospect["role"],
                "qa_status": "ERROR",
                "error": str(e),
            })

        if i < len(batch):
            time.sleep(3)  # Rate limit between leads

    passed = sum(1 for r in results if r.get("qa_status") == "PASS")
    print(f"\n[OUTREACH] Batch complete: {passed}/{len(results)} passed QA")
    return results


# ── Send Approved Outreach ─────────────────────────────────────

def send_approved(auto_approve: bool = False) -> list[dict]:
    """Send all approved (or auto-approve PASS) outreach via email."""
    import os
    import smtplib
    from email.mime.text import MIMEText

    if not OUTREACH_DIR.exists():
        print("[OUTREACH] No outreach directory found.")
        return []

    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    if not smtp_pass:
        print("[OUTREACH] SMTP_PASS not configured. Saving to file instead.")
        file_mode = True
    else:
        file_mode = False

    sent_log = _load_sent_log()
    followups = _load_followups()
    already_sent = {s["company"].lower() for s in sent_log}
    results = []

    for f in sorted(OUTREACH_DIR.glob("meta_*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        company = data["target"]["company"]

        if company.lower() in already_sent:
            continue

        # Check approval status
        if auto_approve and data.get("qa_status") == "PASS":
            data["send_status"] = "approved"
            f.write_text(json.dumps(data, indent=2), encoding="utf-8")
        elif data.get("send_status") != "approved":
            continue

        # Extract email content
        emails = data.get("emails", {})
        primary = emails.get("primary_email", {})
        subject = primary.get("subject", f"Quick note for {company}")
        body = primary.get("body", "")

        if not body:
            continue

        # Get contact email — auto-discover if missing
        enrichment = data.get("enrichment", {})
        contact_email = enrichment.get("contact_email_guess", "")
        contact_name = enrichment.get("contact_name", "")

        if not contact_email or "@" not in contact_email or any(
            x in contact_email.lower() for x in ["head_of", "vp.", "director_", "ceo@", "cfo@"]
        ):
            try:
                from automation.email_discovery import discover_email
                result = discover_email(company, data["target"]["role"])
                contact_email = result.get("contact_email", "")
                contact_name = result.get("contact_name", "") or contact_name
                # Persist back to file
                enrichment["contact_email_guess"] = contact_email
                enrichment["contact_name"] = contact_name
                enrichment["email_confidence"] = result.get("email_confidence", 0)
                data["enrichment"] = enrichment
                f.write_text(json.dumps(data, indent=2), encoding="utf-8")
            except Exception as e:
                print(f"  [WARN] Email discovery failed for {company}: {e}")
        role = data["target"]["role"]

        record = {
            "company": company,
            "role": role,
            "contact_name": contact_name,
            "contact_email": contact_email,
            "subject": subject,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "method": "file" if file_mode else "email",
            "source_file": f.name,
        }

        if file_mode:
            # Save as ready-to-send file
            send_dir = PROJECT_ROOT / "output" / "ready_to_send"
            send_dir.mkdir(parents=True, exist_ok=True)
            outfile = send_dir / f"email_{_sanitize_filename(company)}.json"
            outfile.write_text(json.dumps({
                "to": contact_email or f"[FIND EMAIL for {role} at {company}]",
                "from": smtp_from or "sales@bit-rage-labour.com",
                "subject": subject,
                "body": body,
                "follow_up_1": emails.get("follow_up_1", {}),
                "follow_up_2": emails.get("follow_up_2", {}),
            }, indent=2), encoding="utf-8")
            print(f"  [FILE] {company} -> {outfile.name}")
        else:
            # Actually send via SMTP
            if not contact_email:
                record["method"] = "file"
                print(f"  [SKIP] {company} — no email address found. Saved for manual send.")
                send_dir = PROJECT_ROOT / "output" / "ready_to_send"
                send_dir.mkdir(parents=True, exist_ok=True)
                outfile = send_dir / f"email_{_sanitize_filename(company)}.json"
                outfile.write_text(json.dumps({
                    "to": f"[FIND EMAIL for {role} at {company}]",
                    "subject": subject,
                    "body": body,
                    "follow_up_1": emails.get("follow_up_1", {}),
                    "follow_up_2": emails.get("follow_up_2", {}),
                }, indent=2), encoding="utf-8")
            else:
                try:
                    msg = MIMEText(body, "plain", "utf-8")
                    msg["Subject"] = subject
                    msg["From"] = smtp_from
                    msg["To"] = contact_email

                    with smtplib.SMTP(smtp_host, int(os.getenv("SMTP_PORT", "587"))) as server:
                        server.starttls()
                        server.login(smtp_user, smtp_pass)
                        server.sendmail(smtp_from, [contact_email], msg.as_string())

                    print(f"  [SENT] {company} -> {contact_email}")
                except Exception as e:
                    record["method"] = "failed"
                    record["error"] = str(e)
                    print(f"  [FAIL] {company}: {e}")

        # Mark as sent in source file
        data["send_status"] = "sent"
        data["sent_at"] = record["sent_at"]
        f.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Schedule follow-ups
        sent_time = datetime.now(timezone.utc)
        followups.append({
            "company": company,
            "role": role,
            "contact_email": contact_email,
            "follow_up_1_due": (sent_time + timedelta(days=3)).isoformat(),
            "follow_up_1_sent": False,
            "follow_up_2_due": (sent_time + timedelta(days=7)).isoformat(),
            "follow_up_2_sent": False,
            "source_file": f.name,
        })

        sent_log.append(record)
        results.append(record)

    _save_sent_log(sent_log)
    _save_followups(followups)

    print(f"\n[OUTREACH] Processed {len(results)} emails")
    return results


# ── Follow-up Sender ───────────────────────────────────────────

def send_followups() -> list[dict]:
    """Send due follow-up emails."""
    import os

    followups = _load_followups()
    now = datetime.now(timezone.utc)
    results = []

    for fu in followups:
        source_file = OUTREACH_DIR / fu["source_file"]
        if not source_file.exists():
            continue

        data = json.loads(source_file.read_text(encoding="utf-8"))
        emails = data.get("emails", {})

        # Check follow-up 1
        if not fu["follow_up_1_sent"]:
            due = datetime.fromisoformat(fu["follow_up_1_due"])
            if now >= due:
                fu1 = emails.get("follow_up_1", {})
                if fu1:
                    _queue_followup(fu, fu1, "follow_up_1")
                    fu["follow_up_1_sent"] = True
                    results.append({"company": fu["company"], "type": "follow_up_1"})

        # Check follow-up 2
        if not fu["follow_up_2_sent"]:
            due = datetime.fromisoformat(fu["follow_up_2_due"])
            if now >= due:
                fu2 = emails.get("follow_up_2", {})
                if fu2:
                    _queue_followup(fu, fu2, "follow_up_2")
                    fu["follow_up_2_sent"] = True
                    results.append({"company": fu["company"], "type": "follow_up_2"})

        # Check follow-up 3 (break-up email, day 14)
        if not fu.get("follow_up_3_sent", False):
            fu3_due = fu.get("follow_up_3_due")
            if fu3_due:
                due = datetime.fromisoformat(fu3_due)
                if now >= due:
                    fu3 = emails.get("follow_up_3", {})
                    if fu3:
                        _queue_followup(fu, fu3, "follow_up_3")
                        fu["follow_up_3_sent"] = True
                        results.append({"company": fu["company"], "type": "follow_up_3"})

    _save_followups(followups)
    if results:
        print(f"[FOLLOWUP] Sent {len(results)} follow-ups")
    else:
        print("[FOLLOWUP] No follow-ups due")
    return results


def _sanitize_filename(name: str) -> str:
    """Make a string safe for use as a filename."""
    import re
    safe = name.replace(" ", "_")
    safe = re.sub(r'[\\/:*?"<>|]', '_', safe)
    return safe


def _queue_followup(fu: dict, email_data: dict, fu_type: str):
    """Save follow-up email to ready_to_send."""
    send_dir = PROJECT_ROOT / "output" / "ready_to_send"
    send_dir.mkdir(parents=True, exist_ok=True)
    company = _sanitize_filename(fu["company"])
    outfile = send_dir / f"{fu_type}_{company}.json"
    outfile.write_text(json.dumps({
        "to": fu.get("contact_email") or f"[FIND EMAIL for {fu['role']} at {fu['company']}]",
        "from": "sales@digital-labour.com",
        "subject": email_data.get("subject", f"Following up — {fu['company']}"),
        "body": email_data.get("body", ""),
        "type": fu_type,
    }, indent=2), encoding="utf-8")
    print(f"  [{fu_type.upper()}] {fu['company']} -> queued")


# ── Flush Ready-to-Send Emails via SMTP ────────────────────────

def flush_ready_to_send(dry_run: bool = False) -> dict:
    """Send all emails in output/ready_to_send/ that have real email addresses.

    Moves sent files to output/sent/, failed to output/failed/.
    Returns summary dict with counts.
    """
    import os
    import smtplib
    from email.mime.text import MIMEText

    send_dir = PROJECT_ROOT / "output" / "ready_to_send"
    sent_dir = PROJECT_ROOT / "output" / "sent"
    failed_dir = PROJECT_ROOT / "output" / "failed"

    if not send_dir.exists():
        print("[FLUSH] No ready_to_send directory.")
        return {"sent": 0, "failed": 0, "skipped": 0}

    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    if not smtp_pass:
        print("[FLUSH] SMTP_PASS not set — cannot send.")
        return {"sent": 0, "failed": 0, "skipped": 0, "error": "no SMTP_PASS"}

    sent_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(send_dir.glob("*.json"))
    sent_count = 0
    fail_count = 0
    skip_count = 0

    # Open one SMTP connection for the whole batch
    try:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
        server.starttls()
        server.login(smtp_user, smtp_pass)
    except Exception as e:
        print(f"[FLUSH] SMTP connection failed: {e}")
        return {"sent": 0, "failed": 0, "skipped": 0, "error": str(e)}

    try:
        for f in files:
            data = json.loads(f.read_text(encoding="utf-8"))
            to_addr = data.get("to", "")
            subject = data.get("subject", "")
            body = data.get("body", "")

            if not to_addr or "@" not in to_addr or "FIND EMAIL" in to_addr:
                skip_count += 1
                continue

            if not body:
                skip_count += 1
                continue

            if dry_run:
                print(f"  [DRY] Would send to {to_addr}: {subject[:60]}")
                sent_count += 1
                continue

            try:
                msg = MIMEText(body, "plain", "utf-8")
                msg["Subject"] = subject
                msg["From"] = smtp_from
                msg["To"] = to_addr

                server.sendmail(smtp_from, [to_addr], msg.as_string())

                data["sent_at"] = datetime.now(timezone.utc).isoformat()
                data["sent_by"] = "flush"
                dest = sent_dir / f.name
                dest.write_text(json.dumps(data, indent=2), encoding="utf-8")
                f.unlink()
                sent_count += 1
                print(f"  [SENT] {to_addr}")

                time.sleep(2)  # Rate limit: ~30/min to avoid Zoho throttle
            except Exception as e:
                data["error"] = str(e)
                data["failed_at"] = datetime.now(timezone.utc).isoformat()
                dest = failed_dir / f.name
                dest.write_text(json.dumps(data, indent=2), encoding="utf-8")
                f.unlink()
                fail_count += 1
                print(f"  [FAIL] {to_addr}: {e}")
    finally:
        try:
            server.quit()
        except Exception:
            pass

    summary = {"sent": sent_count, "failed": fail_count, "skipped": skip_count}
    print(f"\n[FLUSH] Done: {sent_count} sent, {fail_count} failed, {skip_count} skipped")
    return summary


# ── Pipeline Status ────────────────────────────────────────────

def show_status():
    """Show the full outreach pipeline status."""
    prospects = load_prospects()
    sent_log = _load_sent_log()
    followups = _load_followups()

    # Count outreach files by status
    pending = 0
    approved = 0
    sent = 0
    failed = 0
    if OUTREACH_DIR.exists():
        for f in OUTREACH_DIR.glob("meta_*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            status = data.get("send_status", "unknown")
            if status == "pending_review":
                pending += 1
            elif status == "approved":
                approved += 1
            elif status == "sent":
                sent += 1
            else:
                failed += 1

    # Count due follow-ups
    now = datetime.now(timezone.utc)
    due_fu = sum(
        1 for fu in followups
        if (not fu["follow_up_1_sent"] and datetime.fromisoformat(fu["follow_up_1_due"]) <= now)
        or (not fu["follow_up_2_sent"] and datetime.fromisoformat(fu["follow_up_2_due"]) <= now)
    )

    print(f"""
{'='*60}
  OUTREACH PIPELINE STATUS
{'='*60}
  Prospects remaining:     {len(prospects)}
  Outreach generated:      {pending + approved + sent + failed}
    ├─ Pending review:     {pending}
    ├─ Approved (unsent):  {approved}
    ├─ Sent:               {sent}
    └─ Failed/Other:       {failed}
  Total emails sent:       {len(sent_log)}
  Follow-ups scheduled:    {len(followups)}
  Follow-ups due now:      {due_fu}
{'='*60}
""")


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Outreach Automation Pipeline")
    parser.add_argument("--generate", type=int, metavar="N", help="Generate N leads from prospects.csv")
    parser.add_argument("--priority", default="all", help="Filter by priority: high|medium|all")
    parser.add_argument("--send-approved", action="store_true", help="Send all approved outreach")
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve QA-PASS leads and send")
    parser.add_argument("--follow-up", action="store_true", help="Send due follow-up emails")
    parser.add_argument("--flush", action="store_true", help="Flush ready_to_send/ emails via SMTP")
    parser.add_argument("--flush-dry", action="store_true", help="Dry-run flush (show what would send)")
    parser.add_argument("--status", action="store_true", help="Show pipeline status")
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.generate:
        generate_batch(count=args.generate, priority=args.priority)
    elif args.send_approved:
        send_approved(auto_approve=False)
    elif args.auto_approve:
        send_approved(auto_approve=True)
    elif args.follow_up:
        send_followups()
    elif args.flush:
        flush_ready_to_send(dry_run=False)
    elif args.flush_dry:
        flush_ready_to_send(dry_run=True)
    else:
        parser.print_help()
