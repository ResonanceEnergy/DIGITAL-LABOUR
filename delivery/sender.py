"""Delivery module — exports completed outputs to clients.

Supports: file export (JSON/CSV/Markdown), email via SMTP, webhook POST.

Usage:
    from delivery.sender import deliver, send_email, check_smtp
    deliver(task_id="abc", outputs={...}, method="file")
    send_email("user@example.com", "Subject", "<h1>Body</h1>")
    ok, msg = check_smtp()
"""

import csv
import json
import logging
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("delivery.sender")

OUTPUT_DIR = PROJECT_ROOT / "output" / "deliveries"


# ── SMTP helpers ────────────────────────────────────────────────

def _smtp_config() -> dict:
    """Return SMTP config from env vars."""
    return {
        "host": os.getenv("SMTP_HOST", ""),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASS", ""),
        "from_addr": os.getenv("SMTP_FROM", "") or os.getenv("SMTP_USER", ""),
    }


def check_smtp() -> tuple[bool, str]:
    """Test SMTP connectivity + auth. Returns (ok, message)."""
    cfg = _smtp_config()
    if not all([cfg["host"], cfg["user"], cfg["password"]]):
        return False, "SMTP not configured (missing SMTP_HOST/SMTP_USER/SMTP_PASS)"
    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(cfg["user"], cfg["password"])
        return True, "SMTP OK"
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed — check SMTP_PASS (needs Zoho App Password)"
    except Exception as e:
        return False, f"SMTP connection error: {e}"


def send_email(to: str, subject: str, body_html: str, body_text: str = "") -> dict:
    """Send a single email. Returns {"ok": bool, "error": str|None}.

    Args:
        to: Recipient email address
        subject: Email subject line
        body_html: HTML body content
        body_text: Optional plain-text fallback (auto-generated from HTML if empty)
    """
    cfg = _smtp_config()
    if not all([cfg["host"], cfg["user"], cfg["password"]]):
        logger.error("SMTP not configured — cannot send email to %s", to)
        return {"ok": False, "error": "SMTP not configured"}
    if not to:
        return {"ok": False, "error": "No recipient address"}

    msg = MIMEMultipart("alternative")
    msg["From"] = cfg["from_addr"]
    msg["To"] = to
    msg["Subject"] = subject

    # Plain-text fallback
    if not body_text:
        import re
        body_text = re.sub(r"<[^>]+>", "", body_html)
    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(cfg["user"], cfg["password"])
            server.send_message(msg)
        logger.info("Email sent to %s — %s", to, subject)
        return {"ok": True, "error": None}
    except Exception as e:
        logger.error("Email to %s failed: %s", to, e)
        return {"ok": False, "error": str(e)}


def deliver(
    task_id: str,
    task_type: str,
    outputs: dict,
    client: str = "",
    method: str = "file",
    destination: str = "",
) -> dict:
    """Deliver task outputs to the client.

    Args:
        task_id: Unique task identifier
        task_type: Type of task (sales_outreach, support_ticket, etc.)
        outputs: The completed output data
        client: Client identifier
        method: "file" | "email" | "webhook"
        destination: Email address or webhook URL

    Returns:
        Delivery receipt dict with status and path/response.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    if method == "file":
        return _deliver_file(task_id, task_type, outputs, client, timestamp)
    elif method == "email":
        return _deliver_email(task_id, task_type, outputs, client, destination, timestamp)
    elif method == "webhook":
        return _deliver_webhook(task_id, task_type, outputs, client, destination, timestamp)
    else:
        return {"status": "error", "message": f"Unknown delivery method: {method}"}


def _deliver_file(task_id: str, task_type: str, outputs: dict, client: str, timestamp: str) -> dict:
    """Save outputs as JSON file."""
    client_dir = OUTPUT_DIR / (client or "unknown")
    client_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{task_type}_{task_id[:8]}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    filepath = client_dir / filename

    payload = {
        "task_id": task_id,
        "task_type": task_type,
        "client": client,
        "delivered_at": timestamp,
        "outputs": outputs,
    }
    filepath.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {"status": "delivered", "method": "file", "path": str(filepath)}


def _deliver_email(
    task_id: str, task_type: str, outputs: dict, client: str, email_to: str, timestamp: str
) -> dict:
    """Send task outputs via SMTP email."""
    subject = f"[Digital Labour] {task_type} complete — {task_id[:8]}"
    body_html = f"""<h2>Task Delivered</h2>
<table>
<tr><td><strong>Task ID</strong></td><td>{task_id}</td></tr>
<tr><td><strong>Type</strong></td><td>{task_type}</td></tr>
<tr><td><strong>Client</strong></td><td>{client}</td></tr>
<tr><td><strong>Delivered</strong></td><td>{timestamp}</td></tr>
</table>
<h3>Output</h3>
<pre>{json.dumps(outputs, indent=2)}</pre>
"""
    result = send_email(email_to, subject, body_html)
    if result["ok"]:
        return {"status": "delivered", "method": "email", "to": email_to}
    return {"status": "error", "method": "email", "error": result["error"]}


def _deliver_webhook(
    task_id: str, task_type: str, outputs: dict, client: str, webhook_url: str, timestamp: str
) -> dict:
    """POST outputs to a webhook URL."""
    if not webhook_url:
        return {"status": "skipped", "method": "webhook", "reason": "No webhook URL provided"}

    payload = {
        "task_id": task_id,
        "task_type": task_type,
        "client": client,
        "delivered_at": timestamp,
        "outputs": outputs,
    }

    try:
        resp = httpx.post(webhook_url, json=payload, timeout=30.0)
        resp.raise_for_status()
        return {"status": "delivered", "method": "webhook", "url": webhook_url, "http_status": resp.status_code}
    except Exception as e:
        return {"status": "error", "method": "webhook", "error": str(e)}


def export_csv(tasks: list[dict], filepath: Path | str) -> str:
    """Export a list of task result dicts to CSV."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    if not tasks:
        return str(filepath)

    fieldnames = list(tasks[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for task in tasks:
            row = {}
            for k in fieldnames:
                v = task.get(k, "")
                row[k] = json.dumps(v) if isinstance(v, (dict, list)) else v
            writer.writerow(row)

    return str(filepath)
