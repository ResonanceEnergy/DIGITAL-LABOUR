"""Delivery module — exports completed outputs to clients.

Supports: file export (JSON/CSV/Markdown), email via SMTP, webhook POST.

Usage:
    from delivery.sender import deliver
    deliver(task_id="abc", outputs={...}, method="file")
"""

import csv
import json
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

OUTPUT_DIR = PROJECT_ROOT / "output" / "deliveries"


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
    """Send outputs via SMTP email."""
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    if not all([smtp_host, smtp_user, smtp_pass, email_to]):
        return {"status": "skipped", "method": "email", "reason": "SMTP not configured or no recipient"}

    subject = f"[Digital Labour] {task_type} complete — {task_id[:8]}"
    body = f"""Task ID: {task_id}
Type: {task_type}
Client: {client}
Delivered: {timestamp}

--- Output ---
{json.dumps(outputs, indent=2)}
"""

    msg = MIMEMultipart()
    msg["From"] = smtp_from
    msg["To"] = email_to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return {"status": "delivered", "method": "email", "to": email_to}
    except Exception as e:
        return {"status": "error", "method": "email", "error": str(e)}


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
