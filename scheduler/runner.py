"""Task scheduler — runs recurring tasks for retainer clients.

Reads client profiles from /clients/*.json and dispatches tasks on schedule.
For sales_outreach, pulls real prospect data from automation/prospects.csv.
Designed to be run as a background process or via cron/Task Scheduler.

Usage:
    python scheduler/runner.py                    # One-shot: process due tasks
    python scheduler/runner.py --daemon           # Run continuously (check every 5 min)
    python scheduler/runner.py --check            # Dry run: show what would run
"""

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CLIENTS_DIR = PROJECT_ROOT / "clients"
SCHEDULE_DB = PROJECT_ROOT / "data" / "schedule_state.json"
PROSPECTS_CSV = PROJECT_ROOT / "automation" / "prospects.csv"
PROSPECT_STATE = PROJECT_ROOT / "data" / "prospect_queue_state.json"


def _load_prospects() -> list[dict]:
    """Load prospects from CSV. Returns list of dicts with company/role/contact data."""
    if not PROSPECTS_CSV.exists():
        return []
    with open(PROSPECTS_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _get_next_prospects(count: int) -> list[dict]:
    """Get the next N un-queued prospects, tracking position."""
    prospects = _load_prospects()
    if not prospects:
        return []

    # Load position state
    state = {}
    if PROSPECT_STATE.exists():
        state = json.loads(PROSPECT_STATE.read_text(encoding="utf-8"))
    offset = state.get("offset", 0)

    # Get next batch (wrap around if we exhaust the list)
    batch = []
    for i in range(count):
        idx = (offset + i) % len(prospects)
        batch.append(prospects[idx])

    # Save new offset
    state["offset"] = (offset + count) % len(prospects)
    state["last_queued"] = datetime.now(timezone.utc).isoformat()
    PROSPECT_STATE.parent.mkdir(parents=True, exist_ok=True)
    PROSPECT_STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")

    return batch


def _load_state() -> dict:
    """Load the schedule state (last run times per client)."""
    if SCHEDULE_DB.exists():
        return json.loads(SCHEDULE_DB.read_text(encoding="utf-8"))
    return {}


def _save_state(state: dict):
    """Save the schedule state."""
    SCHEDULE_DB.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_DB.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _load_clients() -> list[dict]:
    """Load all active client profiles."""
    clients = []
    if not CLIENTS_DIR.exists():
        return clients
    for f in CLIENTS_DIR.glob("*.json"):
        try:
            profile = json.loads(f.read_text(encoding="utf-8"))
            if profile.get("status") == "active":
                clients.append(profile)
        except Exception:
            continue
    return clients


def get_due_tasks(dry_run: bool = False) -> list[dict]:
    """Determine which retainer tasks are due for processing."""
    from billing.tracker import RETAINER_TIERS

    state = _load_state()
    clients = _load_clients()
    now = datetime.now(timezone.utc)
    due = []

    for client in clients:
        cid = client["client_id"]
        tier_name = client.get("retainer_tier", "")
        if not tier_name or tier_name not in RETAINER_TIERS:
            continue

        tier = RETAINER_TIERS[tier_name]
        tasks_per_month = tier["tasks"]
        task_type = tier["type"]

        # Calculate daily target (spread evenly across 30 days)
        daily_target = max(1, tasks_per_month // 30)

        # Check last run
        last_run = state.get(cid, {}).get("last_run", "")
        if last_run:
            last_dt = datetime.fromisoformat(last_run)
            hours_since = (now - last_dt).total_seconds() / 3600
            if hours_since < 20:  # Don't run more than once per ~day
                continue

        # Check monthly progress
        month_count = state.get(cid, {}).get("month_count", 0)
        month_key = now.strftime("%Y-%m")
        if state.get(cid, {}).get("month", "") != month_key:
            month_count = 0  # Reset for new month

        if month_count >= tasks_per_month:
            continue  # Already hit monthly cap

        due.append({
            "client_id": cid,
            "task_type": task_type,
            "daily_target": daily_target,
            "month_count": month_count,
            "month_limit": tasks_per_month,
            "provider": client.get("provider", ""),
            "delivery_method": client.get("delivery_method", "file"),
            "delivery_destination": client.get("delivery_destination", ""),
        })

    return due


def process_due_tasks(dry_run: bool = False) -> list[dict]:
    """Process all due retainer tasks."""
    due = get_due_tasks()
    results = []
    state = _load_state()
    now = datetime.now(timezone.utc)

    if not due:
        print("[SCHEDULER] No tasks due.")
        return results

    for task_info in due:
        cid = task_info["client_id"]
        print(f"[SCHEDULER] Processing {task_info['daily_target']} {task_info['task_type']} "
              f"for {cid} ({task_info['month_count']}/{task_info['month_limit']} this month)")

        if dry_run:
            results.append({"client": cid, "status": "dry_run", **task_info})
            continue

        # Import dispatcher
        from dispatcher.queue import TaskQueue

        queue = TaskQueue()
        queued = 0
        daily_target = task_info["daily_target"]

        # For sales_outreach, pull real prospect data
        if task_info["task_type"] == "sales_outreach":
            prospects = _get_next_prospects(daily_target)
            for prospect in prospects:
                task_id = queue.enqueue(
                    task_type=task_info["task_type"],
                    inputs={
                        "company": prospect.get("company", ""),
                        "role": prospect.get("role", ""),
                        "contact_name": prospect.get("contact_name", ""),
                        "contact_email": prospect.get("contact_email", ""),
                        "vertical": prospect.get("vertical", ""),
                        "provider": task_info["provider"] or "openai",
                    },
                    client=cid,
                    provider=task_info["provider"] or "openai",
                )
                queued += 1
        else:
            for _ in range(daily_target):
                task_id = queue.enqueue(
                    task_type=task_info["task_type"],
                    inputs={"provider": task_info["provider"] or "openai"},
                    client=cid,
                    provider=task_info["provider"] or "openai",
                )
                queued += 1

        # Update state
        month_key = now.strftime("%Y-%m")
        if cid not in state:
            state[cid] = {}
        state[cid]["last_run"] = now.isoformat()
        state[cid]["month"] = month_key
        state[cid]["month_count"] = task_info["month_count"] + queued

        results.append({"client": cid, "queued": queued, "status": "scheduled"})
        print(f"  → Queued {queued} tasks")

    _save_state(state)
    return results


def _maybe_run_daily_burn():
    """Run the daily burn report once per day (after 23:50)."""
    now = datetime.now(timezone.utc)
    if now.hour < 23 or now.minute < 50:
        return
    state = _load_state()
    last_burn = state.get("_daily_burn", {}).get("last_date", "")
    today = now.strftime("%Y-%m-%d")
    if last_burn == today:
        return
    try:
        from kpi.daily_burn import run_burn_check
        report = run_burn_check(write_report=True)
        print(f"[SCHEDULER] Daily burn report: status={report.get('status')}, "
              f"cost=${report.get('total_cost_usd', 0):.4f}")
        state["_daily_burn"] = {"last_date": today, "status": report.get("status")}
        _save_state(state)
    except Exception as e:
        print(f"[SCHEDULER] Burn report error: {e}")


# Quarterly doctrine review dates (first day of Q2, Q3, Q4, Q1+1)
_QUARTERLY_REVIEW_MONTHS = {4, 7, 10, 1}


def _maybe_quarterly_review_reminder():
    """Log a doctrine review reminder on the first day of each quarter."""
    now = datetime.now(timezone.utc)
    if now.month not in _QUARTERLY_REVIEW_MONTHS or now.day != 1:
        return
    state = _load_state()
    quarter_key = f"{now.year}-Q{(now.month - 1) // 3 + 1}"
    last_review = state.get("_doctrine_review", {}).get("last_quarter", "")
    if last_review == quarter_key:
        return
    print(f"[SCHEDULER] *** DOCTRINE REVIEW DUE *** Quarter {quarter_key}")
    print(f"  Review agenda: failed insights vs reality, new patterns, sunset candidates")
    print(f"  Output: updated BRS_2_0_FRAMEWORK.md + DOCTRINE_CHANGELOG.md entry")
    state["_doctrine_review"] = {"last_quarter": quarter_key, "reminded": now.isoformat()}
    _save_state(state)


def _maybe_nightly_secret_scan():
    """Run nightly secret scan of log files (after 23:50, same window as burn)."""
    now = datetime.now(timezone.utc)
    if now.hour < 23 or now.minute < 50:
        return
    state = _load_state()
    last_scan = state.get("_secret_scan", {}).get("last_date", "")
    today = now.strftime("%Y-%m-%d")
    if last_scan == today:
        return
    try:
        from utils.secret_scanner import scan_log_files
        report = scan_log_files()
        print(f"[SCHEDULER] Secret scan: {report['scanned']} files, {report['total_findings']} findings")
        state["_secret_scan"] = {"last_date": today, "findings": report["total_findings"]}
        _save_state(state)
    except Exception as e:
        print(f"[SCHEDULER] Secret scan error: {e}")


def daemon_loop(interval_minutes: int = 5):
    """Run the scheduler continuously."""
    print(f"[SCHEDULER] Daemon started. Checking every {interval_minutes} min. Ctrl+C to stop.")
    while True:
        try:
            results = process_due_tasks()
            if results:
                print(f"[SCHEDULER] Processed {len(results)} clients at {datetime.now(timezone.utc).isoformat()}")
            _maybe_run_daily_burn()
            _maybe_nightly_secret_scan()
            _maybe_quarterly_review_reminder()
        except Exception as e:
            print(f"[SCHEDULER] Error: {e}")
        time.sleep(interval_minutes * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BIT RAGE SYSTEMS Task Scheduler")
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    parser.add_argument("--check", action="store_true", help="Dry run — show due tasks")
    parser.add_argument("--interval", type=int, default=5, help="Check interval in minutes (daemon mode)")
    args = parser.parse_args()

    if args.daemon:
        daemon_loop(args.interval)
    elif args.check:
        due = get_due_tasks(dry_run=True)
        if due:
            print(f"\n{len(due)} client(s) have due tasks:")
            for t in due:
                print(f"  {t['client_id']}: {t['daily_target']} {t['task_type']} "
                      f"({t['month_count']}/{t['month_limit']} this month)")
        else:
            print("No tasks currently due.")
    else:
        process_due_tasks()
