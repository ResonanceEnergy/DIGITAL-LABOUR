"""Delivery module — exports completed outputs to clients.

Supports: file export (JSON/CSV/Markdown), email via SMTP, webhook POST.

Usage:
    from delivery.sender import deliver, send_email, check_smtp
    deliver(task_id="abc", outputs={...}, method="file")
    send_email("user@example.com", "Subject", "<h1>Body</h1>")
    ok, msg = check_smtp()
"""

import csv
import hashlib
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

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("delivery.sender")

OUTPUT_DIR = PROJECT_ROOT / "output" / "deliveries"
DELIVERY_LOG = PROJECT_ROOT / "kpi" / "delivery_log.jsonl"
RECEIPTS_DIR = PROJECT_ROOT / "data" / "delivery_receipts"

_WEBHOOK_RETRY_DELAYS = (1, 5, 30)  # seconds between attempts
_DELIVERY_LOG_RETENTION_DAYS = 90


def _compute_checksum(data: dict) -> str:
    """SHA-256 checksum of the output payload for integrity verification."""
    raw = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _write_delivery_receipt(receipt: dict) -> None:
    """Write delivery receipt to both append-only JSONL log and individual receipt file."""
    # Immutable JSONL log (P4.2)
    DELIVERY_LOG.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(DELIVERY_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(receipt) + "\n")
    except Exception as exc:
        logger.error("Failed to write delivery log: %s", exc)

    # Individual receipt file (P4.1)
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        receipt_id = receipt.get("task_id", "unknown")[:8]
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        receipt_path = RECEIPTS_DIR / f"receipt_{receipt_id}_{ts}.json"
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.error("Failed to write receipt file: %s", exc)


def prune_delivery_log(retention_days: int = _DELIVERY_LOG_RETENTION_DAYS) -> int:
    """P4.2: Remove delivery log entries older than retention_days. Returns lines pruned."""
    if not DELIVERY_LOG.exists():
        return 0
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()
    lines = DELIVERY_LOG.read_text(encoding="utf-8").strip().splitlines()
    kept = []
    pruned = 0
    for line in lines:
        try:
            entry = json.loads(line)
            if entry.get("delivered_at", "") >= cutoff:
                kept.append(line)
            else:
                pruned += 1
        except Exception:
            kept.append(line)  # preserve unparseable lines
    if pruned > 0:
        DELIVERY_LOG.write_text("\n".join(kept) + "\n" if kept else "", encoding="utf-8")
        logger.info("Pruned %d delivery log entries older than %d days", pruned, retention_days)
    return pruned


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
    lineage_id: str = "",
    email_fallback: str = "",
) -> dict:
    """Deliver task outputs to the client.

    Args:
        task_id: Unique task identifier
        task_type: Type of task (sales_outreach, support_ticket, etc.)
        outputs: The completed output data
        client: Client identifier
        method: "file" | "email" | "webhook"
        destination: Email address or webhook URL
        lineage_id: Task lineage ID for traceability
        email_fallback: Fallback email address for webhook failures (P4.3)

    Returns:
        Delivery receipt dict with status and path/response.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    checksum = _compute_checksum(outputs)

    if method == "file":
        return _deliver_file(task_id, task_type, outputs, client, timestamp, lineage_id, checksum)
    elif method == "email":
        return _deliver_email(task_id, task_type, outputs, client, destination, timestamp, lineage_id, checksum)
    elif method == "webhook":
        result = _deliver_webhook(task_id, task_type, outputs, client, destination, timestamp, lineage_id, checksum)
        # P4.3: Fallback to email after 3 webhook failures
        if result.get("delivery_status") == "failed" and email_fallback:
            logger.info("[FALLBACK] Webhook failed for %s — falling back to email %s", task_id, email_fallback)
            email_result = _deliver_email(
                task_id, task_type, outputs, client, email_fallback, timestamp, lineage_id, checksum
            )
            email_result["fallback_from"] = "webhook"
            email_result["original_webhook_url"] = destination
            return email_result
        return result
    else:
        return {"status": "error", "message": f"Unknown delivery method: {method}"}


def _deliver_file(
    task_id: str, task_type: str, outputs: dict, client: str,
    timestamp: str, lineage_id: str = "", checksum: str = "",
) -> dict:
    """Save outputs as JSON file."""
    client_dir = OUTPUT_DIR / (client or "unknown")
    client_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{task_type}_{task_id[:8]}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    filepath = client_dir / filename

    payload = {
        "task_id": task_id,
        "lineage_id": lineage_id,
        "task_type": task_type,
        "client": client,
        "delivered_at": timestamp,
        "checksum": checksum,
        "outputs": outputs,
    }
    filepath.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    receipt = {
        "job_id": task_id, "lineage_id": lineage_id,
        "task_type": task_type, "client": client,
        "channel": "file", "delivery_status": "complete",
        "checksum": checksum, "path": str(filepath),
        "delivered_at": timestamp,
    }
    _write_delivery_receipt(receipt)
    return {"delivery_status": "complete", "method": "file", "path": str(filepath), "checksum": checksum}


def _deliver_email(
    task_id: str, task_type: str, outputs: dict, client: str, email_to: str,
    timestamp: str, lineage_id: str = "", checksum: str = "",
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
        receipt = {
            "job_id": task_id, "lineage_id": lineage_id,
            "task_type": task_type, "client": client,
            "channel": "email", "delivery_status": "complete",
            "checksum": checksum, "to": email_to,
            "delivered_at": timestamp,
        }
        _write_delivery_receipt(receipt)
        return {"delivery_status": "complete", "method": "email", "to": email_to, "checksum": checksum}
    receipt = {
        "job_id": task_id, "lineage_id": lineage_id,
        "task_type": task_type, "client": client,
        "channel": "email", "delivery_status": "failed",
        "checksum": checksum, "to": email_to,
        "error": result["error"], "delivered_at": timestamp,
    }
    _write_delivery_receipt(receipt)
    return {"delivery_status": "failed", "method": "email", "error": result["error"]}


def _deliver_webhook(
    task_id: str, task_type: str, outputs: dict, client: str, webhook_url: str,
    timestamp: str, lineage_id: str = "", checksum: str = "",
) -> dict:
    """POST outputs to a webhook URL with 3× retry + exponential backoff."""
    if not webhook_url:
        return {"status": "skipped", "method": "webhook", "reason": "No webhook URL provided"}

    payload = {
        "task_id": task_id,
        "lineage_id": lineage_id,
        "task_type": task_type,
        "client": client,
        "delivered_at": timestamp,
        "checksum": checksum,
        "outputs": outputs,
    }

    last_error = ""
    for attempt, delay in enumerate(_WEBHOOK_RETRY_DELAYS, start=1):
        try:
            resp = httpx.post(webhook_url, json=payload, timeout=30.0)
            resp.raise_for_status()
            receipt = {
                "job_id": task_id, "lineage_id": lineage_id,
                "task_type": task_type, "client": client,
                "channel": "webhook", "delivery_status": "complete",
                "checksum": checksum, "url": webhook_url,
                "http_status": resp.status_code,
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
        "job_id": task_id, "lineage_id": lineage_id,
        "task_type": task_type, "client": client,
        "channel": "webhook", "delivery_status": "failed",
        "checksum": checksum, "url": webhook_url, "error": last_error,
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
