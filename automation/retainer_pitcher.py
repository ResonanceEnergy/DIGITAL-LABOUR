"""Retainer Pitcher — Convert marketplace buyers into monthly retainer clients.

Identifies high-value marketplace clients (repeat buyers, high spend) and
generates personalized retainer pitches with tiered pricing.

Integrates with:
- billing/tracker.py for client spend history
- automation/crm_tracker.py for pipeline stage updates
- automation/email_tracker.py for engagement signals

Usage:
    python -m automation.retainer_pitcher --candidates    # Show retainer candidates
    python -m automation.retainer_pitcher --pitch "Acme"  # Generate pitch for company
    python -m automation.retainer_pitcher --auto          # Auto-pitch all qualified leads
    python -m automation.retainer_pitcher --status        # Show retainer pipeline
"""

import argparse
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

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# ── Paths ──────────────────────────────────────────────────────
BILLING_DB = PROJECT_ROOT / "data" / "billing.db"
CRM_DB = PROJECT_ROOT / "data" / "crm.db"
STATE_FILE = PROJECT_ROOT / "data" / "retainer_pitcher_state.json"
LOG_DIR = PROJECT_ROOT / "data" / "retainer_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── SMTP config ────────────────────────────────────────────────
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.zohocloud.ca")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_NAME = os.getenv("FROM_NAME", "DIGITAL LABOUR")
FROM_EMAIL = os.getenv("SMTP_USER", "sales@bit-rage-labour.com")

# ── Retainer Tiers ─────────────────────────────────────────────
RETAINER_TIERS = {
    "starter": {
        "name": "Starter",
        "price_usd": 299,
        "tasks_per_month": 100,
        "agents": 2,
        "description": "2 AI agents, 100 tasks/month, email support",
    },
    "core": {
        "name": "Core",
        "price_usd": 999,
        "tasks_per_month": 500,
        "agents": 5,
        "description": "5 AI agents, 500 tasks/month, priority support, weekly reports",
    },
    "pro": {
        "name": "Pro",
        "price_usd": 2499,
        "tasks_per_month": 2000,
        "agents": 10,
        "description": "10 AI agents, 2000 tasks/month, dedicated account manager, custom workflows",
    },
    "enterprise": {
        "name": "Enterprise",
        "price_usd": 4999,
        "tasks_per_month": -1,  # Unlimited
        "agents": 24,
        "description": "All 24 agents, unlimited tasks, SLA, API access, custom integrations",
    },
}

# ── Qualification Thresholds ───────────────────────────────────
MIN_TASKS_FOR_PITCH = 3          # At least 3 completed tasks
MIN_SPEND_FOR_PITCH = 15.0       # At least $15 in per-task spend
MIN_DAYS_SINCE_FIRST = 3         # Wait 3 days after first task
REPEAT_BUYER_THRESHOLD = 5       # 5+ tasks = strong signal

# ── Logging ────────────────────────────────────────────────────
logger = logging.getLogger("retainer_pitcher")
if not logger.handlers:
    _sh = logging.StreamHandler()
    _sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] retainer — %(message)s"))
    logger.addHandler(_sh)
    _fh = logging.FileHandler(LOG_DIR / "retainer_pitcher.log", encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] retainer — %(message)s"))
    logger.addHandler(_fh)
    logger.setLevel(logging.INFO)
logger.propagate = False


# ── Data Loading ───────────────────────────────────────────────

def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"pitched": {}, "converted": {}, "total_pitched": 0, "total_converted": 0}


def _save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _get_client_spend() -> list[dict]:
    """Query billing.db for client task history."""
    import sqlite3
    if not BILLING_DB.exists():
        return []

    conn = sqlite3.connect(str(BILLING_DB))
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute("""
            SELECT
                client_id,
                COUNT(*) as task_count,
                SUM(amount) as total_spend,
                MIN(created_at) as first_task,
                MAX(created_at) as last_task,
                GROUP_CONCAT(DISTINCT task_type) as task_types
            FROM usage
            WHERE status = 'billed'
            GROUP BY client_id
            HAVING COUNT(*) >= ?
            ORDER BY total_spend DESC
        """, (MIN_TASKS_FOR_PITCH,)).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def _get_client_email(client_id: str) -> str:
    """Look up client email from CRM."""
    import sqlite3
    if not CRM_DB.exists():
        return ""
    try:
        conn = sqlite3.connect(str(CRM_DB))
        row = conn.execute(
            "SELECT email FROM contacts WHERE contact_id = ? OR company = ? LIMIT 1",
            (client_id, client_id)
        ).fetchone()
        conn.close()
        return row[0] if row else ""
    except Exception:
        return ""


# ── Qualification Engine ───────────────────────────────────────

def find_candidates() -> list[dict]:
    """Find clients qualified for retainer pitch."""
    clients = _get_client_spend()
    state = _load_state()
    now = datetime.now(timezone.utc)

    candidates = []
    for client in clients:
        client_id = client["client_id"]

        # Skip already pitched (within 30 days)
        if client_id in state.get("pitched", {}):
            pitched_at = state["pitched"][client_id].get("pitched_at", "")
            if pitched_at:
                try:
                    pitch_date = datetime.fromisoformat(pitched_at)
                    if (now - pitch_date).days < 30:
                        continue
                except (ValueError, TypeError):
                    pass

        # Skip already converted
        if client_id in state.get("converted", {}):
            continue

        task_count = client.get("task_count", 0)
        total_spend = client.get("total_spend", 0) or 0
        first_task = client.get("first_task", "")

        # Check minimum spend
        if total_spend < MIN_SPEND_FOR_PITCH:
            continue

        # Check tenure
        if first_task:
            try:
                first_date = datetime.fromisoformat(first_task)
                if (now - first_date).days < MIN_DAYS_SINCE_FIRST:
                    continue
            except (ValueError, TypeError):
                pass

        # Calculate recommended tier
        if total_spend > 500 or task_count > 100:
            recommended_tier = "pro"
        elif total_spend > 100 or task_count > 20:
            recommended_tier = "core"
        else:
            recommended_tier = "starter"

        # Score the candidate
        score = 0
        score += min(task_count * 2, 40)       # Up to 40 pts for tasks
        score += min(total_spend / 5, 30)       # Up to 30 pts for spend
        if task_count >= REPEAT_BUYER_THRESHOLD:
            score += 20                          # Repeat buyer bonus
        score += min((now - datetime.fromisoformat(first_task)).days * 0.5, 10) if first_task else 0

        email = _get_client_email(client_id)

        candidates.append({
            "client_id": client_id,
            "task_count": task_count,
            "total_spend": round(total_spend, 2),
            "first_task": first_task,
            "last_task": client.get("last_task", ""),
            "task_types": client.get("task_types", ""),
            "email": email,
            "recommended_tier": recommended_tier,
            "score": round(score, 1),
        })

    # Sort by score descending
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates


# ── Pitch Generation ───────────────────────────────────────────

def generate_pitch(client: dict) -> dict:
    """Generate a personalized retainer pitch for a client."""
    tier = RETAINER_TIERS[client["recommended_tier"]]
    task_types = client.get("task_types", "").split(",") if client.get("task_types") else []

    # Calculate savings
    current_per_task = client["total_spend"] / max(client["task_count"], 1)
    retainer_per_task = tier["price_usd"] / tier["tasks_per_month"] if tier["tasks_per_month"] > 0 else 0
    monthly_savings = (current_per_task * tier["tasks_per_month"]) - tier["price_usd"]

    subject = f"A better way to work together — {tier['name']} plan for you"
    body = (
        f"Hi there,\n\n"
        f"I noticed you've used our AI agents {client['task_count']} times "
        f"(${client['total_spend']:.2f} total) — thank you for trusting us.\n\n"
        f"I wanted to share something that could save you money and give you "
        f"more capacity:\n\n"
        f"**{tier['name']} Retainer — ${tier['price_usd']}/month**\n"
        f"  - {tier['description']}\n"
        f"  - Your current rate: ~${current_per_task:.2f}/task\n"
        f"  - Retainer rate: ~${retainer_per_task:.2f}/task\n"
    )

    if monthly_savings > 0:
        body += f"  - Estimated monthly savings: ${monthly_savings:.0f}\n"

    body += (
        f"\nNo long-term commitment — cancel anytime.\n\n"
        f"Want to set it up? Just reply and I'll get you started.\n\n"
        f"— DIGITAL LABOUR\n"
        f"sales@digital-labour.com"
    )

    return {
        "subject": subject,
        "body": body,
        "tier": client["recommended_tier"],
        "tier_price": tier["price_usd"],
        "monthly_savings": round(max(monthly_savings, 0), 2),
    }


# ── Send Pitch ─────────────────────────────────────────────────

def _send_pitch_email(to_email: str, pitch: dict) -> dict:
    """Send retainer pitch email."""
    if not SMTP_USER or not SMTP_PASS:
        return {"status": "skipped", "reason": "SMTP not configured"}

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = pitch["subject"]
    msg.attach(MIMEText(pitch["body"], "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return {"status": "sent"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}


def pitch_client(client_id: str, dry_run: bool = False) -> dict:
    """Generate and send retainer pitch to a specific client."""
    candidates = find_candidates()
    client = next((c for c in candidates if c["client_id"] == client_id), None)

    if not client:
        # Try with partial match
        client = next((c for c in candidates if client_id.lower() in c["client_id"].lower()), None)

    if not client:
        return {"status": "not_found", "message": f"No candidate found for '{client_id}'"}

    pitch = generate_pitch(client)

    if dry_run or not client.get("email"):
        return {"status": "preview", "pitch": pitch, "client": client}

    result = _send_pitch_email(client["email"], pitch)

    if result["status"] == "sent":
        state = _load_state()
        state["pitched"][client["client_id"]] = {
            "pitched_at": datetime.now(timezone.utc).isoformat(),
            "tier": pitch["tier"],
            "email": client["email"],
        }
        state["total_pitched"] += 1
        _save_state(state)

    return {"status": result["status"], "pitch": pitch, "client": client}


def auto_pitch(dry_run: bool = False) -> list[dict]:
    """Auto-pitch all qualified candidates."""
    candidates = find_candidates()
    results = []

    for client in candidates:
        if not client.get("email"):
            logger.info(f"Skipping {client['client_id']} — no email")
            continue

        result = pitch_client(client["client_id"], dry_run=dry_run)
        results.append(result)
        logger.info(f"  {client['client_id']}: {result['status']}")

        if not dry_run and result.get("status") == "sent":
            time.sleep(10)  # Rate limit

    return results


# ── Status Report ──────────────────────────────────────────────

def show_status() -> dict:
    """Show retainer pipeline status."""
    state = _load_state()
    candidates = find_candidates()

    report = {
        "candidates": len(candidates),
        "total_pitched": state.get("total_pitched", 0),
        "total_converted": state.get("total_converted", 0),
        "top_candidates": candidates[:5],
    }

    print(f"\n{'='*50}")
    print(f"  RETAINER PITCHER STATUS")
    print(f"{'='*50}")
    print(f"  Qualified candidates:  {len(candidates)}")
    print(f"  Total pitched:         {state.get('total_pitched', 0)}")
    print(f"  Total converted:       {state.get('total_converted', 0)}")

    if candidates:
        print(f"\n  Top Candidates:")
        for c in candidates[:5]:
            print(f"    {c['client_id']}: {c['task_count']} tasks, "
                  f"${c['total_spend']:.2f} spent, "
                  f"rec: {c['recommended_tier']} (score: {c['score']})")

    print(f"{'='*50}\n")
    return report


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Retainer Pitcher")
    parser.add_argument("--candidates", action="store_true", help="Show retainer candidates")
    parser.add_argument("--pitch", type=str, help="Generate pitch for a specific company")
    parser.add_argument("--auto", action="store_true", help="Auto-pitch all qualified leads")
    parser.add_argument("--status", action="store_true", help="Show retainer pipeline status")
    parser.add_argument("--dry-run", action="store_true", help="Preview without sending")
    args = parser.parse_args()

    if args.candidates:
        candidates = find_candidates()
        for c in candidates:
            print(f"  {c['client_id']}: {c['task_count']} tasks, ${c['total_spend']:.2f}, "
                  f"tier={c['recommended_tier']}, score={c['score']}")
        print(f"\nTotal: {len(candidates)} candidates")
    elif args.pitch:
        result = pitch_client(args.pitch, dry_run=args.dry_run)
        print(json.dumps(result, indent=2, default=str))
    elif args.auto:
        results = auto_pitch(dry_run=args.dry_run)
        sent = sum(1 for r in results if r.get("status") == "sent")
        print(f"\nPitched: {sent}, Total processed: {len(results)}")
    elif args.status:
        show_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
