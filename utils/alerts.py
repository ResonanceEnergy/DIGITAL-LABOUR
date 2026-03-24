"""Task alert system — polls for new completed tasks and sends notifications.

Supports: Desktop toast (Windows), Telegram bot, Discord webhook.
Configure in .env:
    ALERT_TELEGRAM_BOT_TOKEN=...
    ALERT_TELEGRAM_CHAT_ID=...
    ALERT_DISCORD_WEBHOOK=...

Usage:
    python utils/alerts.py                # one-shot: report any new outputs
    python utils/alerts.py --watch        # continuous: poll every 60s
    python utils/alerts.py --test         # send a test alert
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

# ── State tracking ──────────────────────────────────────────────────────────

STATE_FILE = PROJECT_ROOT / "output" / ".alert_state.json"


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"last_check": None, "seen_files": []}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── Notification channels ──────────────────────────────────────────────────

def send_telegram(message: str) -> bool:
    token = os.getenv("ALERT_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("ALERT_TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    try:
        import httpx
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = httpx.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"[ALERT] Telegram failed: {e}")
        return False


def send_discord(message: str) -> bool:
    webhook = os.getenv("ALERT_DISCORD_WEBHOOK")
    if not webhook:
        return False
    try:
        import httpx
        resp = httpx.post(webhook, json={"content": message}, timeout=10)
        return resp.status_code in (200, 204)
    except Exception as e:
        print(f"[ALERT] Discord failed: {e}")
        return False


def send_desktop(title: str, message: str) -> bool:
    """Windows toast notification via PowerShell."""
    try:
        import subprocess
        ps_script = f"""
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
        $template = @"
        <toast>
            <visual>
                <binding template="ToastText02">
                    <text id="1">{title}</text>
                    <text id="2">{message}</text>
                </binding>
            </visual>
        </toast>
"@
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("BIT RAGE SYSTEMS").Show($toast)
        """
        subprocess.run(["powershell", "-Command", ps_script], capture_output=True, timeout=10)
        return True
    except Exception as e:
        print(f"[ALERT] Desktop notification failed: {e}")
        return False


def send_alert(title: str, message: str):
    """Send alert through all configured channels."""
    full = f"*{title}*\n{message}"
    sent = []

    if send_telegram(full):
        sent.append("Telegram")
    if send_discord(full):
        sent.append("Discord")
    if send_desktop(title, message):
        sent.append("Desktop")

    if not sent:
        # Fallback: just print to console
        print(f"\n{'='*50}")
        print(f"  {title}")
        print(f"  {message}")
        print(f"{'='*50}\n")
        sent.append("Console")

    return sent


# ── File scanning ───────────────────────────────────────────────────────────

OUTPUT_DIRS = [
    PROJECT_ROOT / "output" / "sales_ops",
    PROJECT_ROOT / "output" / "support",
    PROJECT_ROOT / "output" / "content_repurpose",
    PROJECT_ROOT / "output" / "doc_extract",
]


def scan_new_outputs(state: dict) -> list[dict]:
    """Find new output files since last check."""
    seen = set(state.get("seen_files", []))
    new_files = []

    for d in OUTPUT_DIRS:
        if not d.exists():
            continue
        for f in d.glob("*.json"):
            rel = str(f.relative_to(PROJECT_ROOT))
            if rel not in seen:
                # Parse the output for summary info
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    agent_type = d.name  # directory name = agent type
                    summary = _summarize(data, agent_type)
                except Exception:
                    summary = f"New output: {f.name}"
                new_files.append({"path": rel, "file": f.name, "summary": summary})
                seen.add(rel)

    state["seen_files"] = list(seen)
    state["last_check"] = datetime.now().isoformat()
    return new_files


def _summarize(data: dict, agent_type: str) -> str:
    if agent_type == "sales_ops":
        enrich = data.get("lead_enrichment", {})
        company = enrich.get("company_name", "Unknown")
        role = enrich.get("contact_role", "Unknown")
        return f"Sales Ops: {company} / {role}"
    elif agent_type == "content_repurpose":
        analysis = data.get("analysis", {})
        title = analysis.get("title", "Untitled")[:50]
        qa = data.get("qa_status", "?")
        return f"Content: {title} (QA: {qa})"
    elif agent_type == "doc_extract":
        extraction = data.get("extraction", {})
        doc_type = extraction.get("doc_type", "unknown")
        qa = data.get("qa_status", "?")
        return f"Doc Extract: {doc_type} (QA: {qa})"
    else:
        cat = data.get("category", "Unknown")
        sev = data.get("severity", "?")
        return f"Support: {cat} (severity: {sev})"


# ── Task-level alert (called from dispatcher) ──────────────────────────────

def alert_task_complete(task_id: str, task_type: str, qa_status: str, client: str = "", duration_s: float = 0):
    """Fire alert on task completion — especially on QA failures."""
    if qa_status == "FAIL":
        send_alert(
            f"⚠ QA FAILURE: {task_type}",
            f"Task {task_id} for client '{client}' FAILED QA.\nDuration: {duration_s:.1f}s\nReview and re-run."
        )
    elif qa_status == "PASS" and client:
        # Only alert for client tasks, not internal
        send_alert(
            f"✓ Task Complete: {task_type}",
            f"Task {task_id} for '{client}' PASSED QA in {duration_s:.1f}s."
        )


# ── Revenue tracking alerts ────────────────────────────────────────────────

def check_revenue_milestone():
    """Check KPI logs for revenue milestones and alert."""
    kpi_file = PROJECT_ROOT / "kpi" / "events.jsonl"
    if not kpi_file.exists():
        return

    total_revenue = 0.0
    milestones_hit = set()
    milestones = [1, 10, 50, 100, 500, 1000, 5000]

    for line in kpi_file.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            total_revenue += event.get("revenue", 0.0)
        except Exception:
            continue

    for m in milestones:
        if total_revenue >= m:
            milestones_hit.add(m)

    milestone_file = PROJECT_ROOT / "output" / ".milestones_alerted.json"
    already_alerted = set()
    if milestone_file.exists():
        already_alerted = set(json.loads(milestone_file.read_text(encoding="utf-8")))

    new_milestones = milestones_hit - already_alerted
    for m in sorted(new_milestones):
        send_alert(
            f"Revenue Milestone: ${m}",
            f"Total revenue has reached ${total_revenue:.2f}. Milestone: ${m}."
        )

    if new_milestones:
        all_alerted = already_alerted | milestones_hit
        milestone_file.write_text(json.dumps(sorted(all_alerted)), encoding="utf-8")


# ── Main ────────────────────────────────────────────────────────────────────

def run_once():
    state = load_state()
    new_files = scan_new_outputs(state)
    check_revenue_milestone()

    if new_files:
        count = len(new_files)
        summaries = "\n".join(f"  • {f['summary']}" for f in new_files[:5])
        if count > 5:
            summaries += f"\n  ... and {count - 5} more"
        channels = send_alert(
            f"BIT RAGE SYSTEMS: {count} new output(s)",
            summaries
        )
        print(f"[ALERT] {count} new outputs → sent via {', '.join(channels)}")
    else:
        print("[ALERT] No new outputs since last check.")

    save_state(state)


def watch(interval: int = 60):
    print(f"[ALERT] Watching for new outputs every {interval}s... (Ctrl+C to stop)")
    while True:
        run_once()
        time.sleep(interval)


def test_alert():
    channels = send_alert(
        "BIT RAGE SYSTEMS — Test Alert",
        "Alert system is working. Channels configured and active."
    )
    print(f"[TEST] Alert sent via: {', '.join(channels)}")


def main():
    parser = argparse.ArgumentParser(description="BIT RAGE SYSTEMS Alert System")
    parser.add_argument("--watch", action="store_true", help="Continuously poll for new outputs")
    parser.add_argument("--interval", type=int, default=60, help="Poll interval in seconds (default: 60)")
    parser.add_argument("--test", action="store_true", help="Send a test alert")
    args = parser.parse_args()

    if args.test:
        test_alert()
    elif args.watch:
        watch(args.interval)
    else:
        run_once()


if __name__ == "__main__":
    main()
