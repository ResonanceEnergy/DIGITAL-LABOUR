"""Task scheduler — runs recurring tasks for retainer clients.

Reads client profiles from /clients/*.json and dispatches tasks on schedule.
Designed to be run as a background process or via cron/Task Scheduler.

Usage:
    python scheduler/runner.py                    # One-shot: process due tasks
    python scheduler/runner.py --daemon           # Run continuously (check every 5 min)
    python scheduler/runner.py --check            # Dry run: show what would run
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CLIENTS_DIR = PROJECT_ROOT / "clients"
SCHEDULE_DB = PROJECT_ROOT / "data" / "schedule_state.json"


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

        for _ in range(task_info["daily_target"]):
            task_id = queue.enqueue(
                task_type=task_info["task_type"],
                inputs={"provider": task_info["provider"]},
                client=cid,
                provider=task_info["provider"],
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


def daemon_loop(interval_minutes: int = 5):
    """Run the scheduler continuously."""
    print(f"[SCHEDULER] Daemon started. Checking every {interval_minutes} min. Ctrl+C to stop.")
    while True:
        try:
            results = process_due_tasks()
            if results:
                print(f"[SCHEDULER] Processed {len(results)} clients at {datetime.now(timezone.utc).isoformat()}")
        except Exception as e:
            print(f"[SCHEDULER] Error: {e}")
        time.sleep(interval_minutes * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Digital Labour Task Scheduler")
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
