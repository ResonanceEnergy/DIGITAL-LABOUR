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
import time
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("delivery.sender")

OUTPUT_DIR = PROJECT_ROOT / "output" / "deliveries"
DELIVERY_LOG = PROJECT_ROOT / "kpi" / "delivery_log.jsonl"

_WEBHOOK_RETRY_DELAYS = (1, 5, 30)  # seconds between attempts


def _write_delivery_receipt(receipt: dict) -> None:
    """Append an immutable delivery receipt to kpi/delivery_log.jsonl."""
    DELIVERY_LOG.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(DELIVERY_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(receipt) + "\n")
    except Exception as exc:
        logger.error("Failed to write delivery receipt: %s", exc)


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

    receipt = {
        "task_id": task_id, "task_type": task_type, "client": client,
        "method": "file", "delivery_status": "complete",
        "path": str(filepath), "delivered_at": timestamp,
    }
    _write_delivery_receipt(receipt)
    return {"delivery_status": "complete", "method": "file", "path": str(filepath)}


def _deliver_email(
    task_id: str, task_type: str, outputs: dict, client: str, email_to: str, timestamp: str
) -> dict:
    """Send task outputs via SMTP email."""
    subject = f"[Bit Rage Labour] {task_type} complete — {task_id[:8]}"
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
        receipt = {
            "task_id": task_id, "task_type": task_type, "client": client,
            "method": "email", "delivery_status": "complete",
            "to": email_to, "delivered_at": timestamp,
        }
        _write_delivery_receipt(receipt)
        return {"delivery_status": "complete", "method": "email", "to": email_to}
    receipt = {
        "task_id": task_id, "task_type": task_type, "client": client,
        "method": "email", "delivery_status": "failed",
        "to": email_to, "error": result["error"], "delivered_at": timestamp,
    }
    _write_delivery_receipt(receipt)
    return {"delivery_status": "failed", "method": "email", "error": result["error"]}


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

    last_error = ""
    for attempt, delay in enumerate(_WEBHOOK_RETRY_DELAYS, start=1):
        try:
            resp = httpx.post(webhook_url, json=payload, timeout=30.0)
            resp.raise_for_status()
            receipt = {
                "task_id": task_id, "task_type": task_type, "client": client,
                "method": "webhook", "delivery_status": "complete",
                "url": webhook_url, "http_status": resp.status_code,
                "attempt": attempt, "delivered_at": timestamp,
            }
            _write_delivery_receipt(receipt)
            return {
                "delivery_status": "complete", "method": "webhook",
                "url": webhook_url, "http_status": resp.status_code, "attempt": attempt,
            }
        except Exception as exc:
            last_error = str(exc)
            logger.warning("Webhook attempt %d/%d failed: %s", attempt, len(_WEBHOOK_RETRY_DELAYS), exc)
            if attempt < len(_WEBHOOK_RETRY_DELAYS):
                time.sleep(delay)

    receipt = {
        "task_id": task_id, "task_type": task_type, "client": client,
        "method": "webhook", "delivery_status": "failed",
        "url": webhook_url, "error": last_error,
        "attempts": len(_WEBHOOK_RETRY_DELAYS), "delivered_at": timestamp,
    }
    _write_delivery_receipt(receipt)
    return {"delivery_status": "failed", "method": "webhook", "error": last_error}


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
