"""Reference Request — Send emails to past employers/clients requesting testimonials.

Sends a professional reference request email via Zoho SMTP asking past employers
or clients to write a short testimonial for freelance platform profiles
(Freelancer.com, Upwork, Fiverr, PeoplePerHour, Guru).

Usage:
    # Send to one person
    python -m automation.reference_request --to "boss@company.com" --name "John Smith" --company "Acme Corp"

    # Send to multiple people from a CSV
    python -m automation.reference_request --csv refs.csv

    # Preview email without sending
    python -m automation.reference_request --to "boss@company.com" --name "John" --company "Acme" --dry-run

    # Custom platform link
    python -m automation.reference_request --to "boss@company.com" --name "John" --company "Acme" --platform freelancer

CSV format (refs.csv):
    name,email,company,relationship
    John Smith,john@acme.com,Acme Corp,Former Manager
    Jane Doe,jane@startup.io,StartupIO,Client
"""

import argparse
import csv
import json
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

LOG_FILE = PROJECT_ROOT / "data" / "reference_requests.json"

# ── Platform review/recommendation links ───────────────────────

PLATFORM_LINKS = {
    "freelancer": "https://www.freelancer.com/u/BitRageLabour",
    "upwork": "https://www.upwork.com/freelancers/BitRageLabour",
    "fiverr": "https://www.fiverr.com/BitRageLabour",
    "pph": "https://www.peopleperhour.com/freelancer/BitRageLabour",
    "guru": "https://www.guru.com/freelancers/BitRageLabour",
}

# ── Email Template ─────────────────────────────────────────────


def build_email(
    recipient_name: str,
    recipient_company: str,
    relationship: str = "",
    platform: str = "",
) -> tuple[str, str, str]:
    """Return (subject, plain_body, html_body) for the reference request."""

    subject = "Quick favour — would you write a short reference for me?"

    platform_note = ""
    if platform and platform in PLATFORM_LINKS:
        platform_note = (
            f"\n\nMy profile: {PLATFORM_LINKS[platform]}\n"
            f"You can leave the recommendation directly on the platform, "
            f"or just reply to this email and I'll post it myself."
        )
    else:
        platform_note = (
            "\n\nYou can simply reply to this email with your testimonial "
            "and I'll add it to my profiles. Or if you prefer, I can send "
            "you a direct link to leave it on a specific platform."
        )

    relationship_line = ""
    if relationship:
        relationship_line = f" ({relationship})"

    plain_body = f"""Hi {recipient_name},

I hope you're doing well. I'm reaching out because I'm expanding my freelance presence and setting up profiles on platforms like Freelancer.com, Upwork, and Fiverr.

Having worked together at {recipient_company}{relationship_line}, I was wondering if you'd be willing to write a brief reference or testimonial about your experience working with me. Even 2-3 sentences would be incredibly helpful.

Here are a few things you might mention (whatever feels natural):
  - The type of work we did together
  - Skills or qualities you noticed
  - Whether you'd recommend working with me

No pressure at all — I completely understand if you're too busy.{platform_note}

Thank you for considering it. I really appreciate the time we spent working together.

Best regards,
BIT RAGE LABOUR SYSTEMS
sales@bit-rage-labour.com
https://bit-rage-labour.com
"""

    html_body = f"""<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: 0 auto;">

<p>Hi {recipient_name},</p>

<p>I hope you're doing well. I'm reaching out because I'm expanding my freelance presence
and setting up profiles on platforms like Freelancer.com, Upwork, and Fiverr.</p>

<p>Having worked together at <strong>{recipient_company}</strong>{relationship_line},
I was wondering if you'd be willing to write a brief reference or testimonial about your
experience working with me. Even 2–3 sentences would be incredibly helpful.</p>

<p>Here are a few things you might mention (whatever feels natural):</p>
<ul>
  <li>The type of work we did together</li>
  <li>Skills or qualities you noticed</li>
  <li>Whether you'd recommend working with me</li>
</ul>

<p>No pressure at all — I completely understand if you're too busy.</p>

{f'<p><strong>My profile:</strong> <a href="{PLATFORM_LINKS.get(platform, "")}">{PLATFORM_LINKS.get(platform, "")}</a><br>'
 f'You can leave the recommendation directly on the platform, or just reply to this email and I will post it myself.</p>'
 if platform and platform in PLATFORM_LINKS else
 '<p>You can simply reply to this email with your testimonial and I will add it to my profiles. '
 'Or if you prefer, I can send you a direct link to leave it on a specific platform.</p>'}

<p>Thank you for considering it. I really appreciate the time we spent working together.</p>

<p>Best regards,<br>
<strong>BIT RAGE LABOUR SYSTEMS</strong><br>
<a href="mailto:sales@bit-rage-labour.com">sales@bit-rage-labour.com</a><br>
<a href="https://bit-rage-labour.com">bit-rage-labour.com</a></p>

</body>
</html>"""

    return subject, plain_body, html_body


# ── Send ───────────────────────────────────────────────────────


def send_reference_request(
    to_email: str,
    recipient_name: str,
    recipient_company: str,
    relationship: str = "",
    platform: str = "",
    dry_run: bool = False,
) -> dict:
    """Send (or preview) one reference request email."""
    subject, plain_body, html_body = build_email(
        recipient_name, recipient_company, relationship, platform
    )

    if dry_run:
        print(f"\n{'='*60}")
        print(f"  DRY RUN — Would send to: {to_email}")
        print(f"{'='*60}")
        print(f"Subject: {subject}")
        print(f"\n{plain_body}")
        return {"status": "dry_run", "to": to_email}

    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    if not all([smtp_host, smtp_user, smtp_pass]):
        print(f"[REF] SMTP not configured. Saving email to file instead.")
        save_dir = PROJECT_ROOT / "output" / "reference_emails"
        save_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = recipient_name.replace(" ", "_").lower()
        filepath = save_dir / f"ref_request_{safe_name}_{ts}.txt"
        filepath.write_text(
            f"TO: {to_email}\nSUBJECT: {subject}\n\n{plain_body}",
            encoding="utf-8",
        )
        print(f"  Saved to {filepath}")
        return {"status": "saved_to_file", "path": str(filepath)}

    msg = MIMEMultipart("alternative")
    msg["From"] = f"Bit Rage Labour <{smtp_from}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Reply-To"] = smtp_from
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print(f"  [OK] Sent reference request to {recipient_name} <{to_email}>")
        _log_request(to_email, recipient_name, recipient_company, relationship, platform, "sent")
        return {"status": "sent", "to": to_email}
    except Exception as e:
        print(f"  [ERROR] Failed to send to {to_email}: {e}")
        _log_request(to_email, recipient_name, recipient_company, relationship, platform, f"error: {e}")
        return {"status": "error", "to": to_email, "error": str(e)}


# ── Batch from CSV ─────────────────────────────────────────────


def send_from_csv(csv_path: str, platform: str = "", dry_run: bool = False) -> list[dict]:
    """Send reference requests to everyone in a CSV file.

    CSV columns: name, email, company, relationship (optional)
    """
    results = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name", "").strip()
            email = row.get("email", "").strip()
            company = row.get("company", "").strip()
            rel = row.get("relationship", "").strip()

            if not email or not name:
                print(f"  [SKIP] Missing name or email in row: {row}")
                continue

            result = send_reference_request(
                to_email=email,
                recipient_name=name,
                recipient_company=company,
                relationship=rel,
                platform=platform,
                dry_run=dry_run,
            )
            results.append(result)

    print(f"\n  Total: {len(results)} reference requests {'previewed' if dry_run else 'processed'}")
    return results


# ── Log ────────────────────────────────────────────────────────


def _log_request(email: str, name: str, company: str, relationship: str, platform: str, status: str):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    log = []
    if LOG_FILE.exists():
        log = json.loads(LOG_FILE.read_text(encoding="utf-8"))
    log.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "email": email,
        "name": name,
        "company": company,
        "relationship": relationship,
        "platform": platform,
        "status": status,
    })
    LOG_FILE.write_text(json.dumps(log, indent=2), encoding="utf-8")


# ── CLI ────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Send reference request emails for freelance profiles")
    parser.add_argument("--to", help="Recipient email address")
    parser.add_argument("--name", help="Recipient name")
    parser.add_argument("--company", help="Company you worked at together")
    parser.add_argument("--relationship", default="", help="Relationship (e.g. 'Former Manager', 'Client')")
    parser.add_argument("--platform", default="", choices=["freelancer", "upwork", "fiverr", "pph", "guru", ""],
                        help="Platform to link to for the recommendation")
    parser.add_argument("--csv", help="Path to CSV file with columns: name, email, company, relationship")
    parser.add_argument("--dry-run", action="store_true", help="Preview emails without sending")
    args = parser.parse_args()

    if args.csv:
        send_from_csv(args.csv, platform=args.platform, dry_run=args.dry_run)
    elif args.to and args.name and args.company:
        send_reference_request(
            to_email=args.to,
            recipient_name=args.name,
            recipient_company=args.company,
            relationship=args.relationship,
            platform=args.platform,
            dry_run=args.dry_run,
        )
    else:
        parser.print_help()
        print("\nExamples:")
        print('  python -m automation.reference_request --to "boss@acme.com" --name "John" --company "Acme" --dry-run')
        print('  python -m automation.reference_request --csv data/references.csv --platform freelancer')


if __name__ == "__main__":
    main()
