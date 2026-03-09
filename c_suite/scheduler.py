"""C-Suite Scheduler — Automated executive cadence runner.

Runs the C-Suite on schedule: morning briefs, ops checks, full board meetings.
Designed to run as a background process or via system scheduler.

Usage:
    python c_suite/scheduler.py                  # One-shot: run any due executive actions
    python c_suite/scheduler.py --daemon         # Run continuously (checks every 30 min)
    python c_suite/scheduler.py --force-board    # Force a board meeting now
    python c_suite/scheduler.py --force-standup  # Force a quick standup now
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

STATE_FILE = PROJECT_ROOT / "data" / "csuite_schedule.json"


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def _save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _hours_since(iso_ts: str) -> float:
    if not iso_ts:
        return 999
    then = datetime.fromisoformat(iso_ts)
    now = datetime.now(timezone.utc)
    return (now - then).total_seconds() / 3600


def run_due_actions() -> list[str]:
    """Check schedule and run any due executive actions."""
    state = _load_state()
    actions_run = []
    now = datetime.now(timezone.utc)
    hour = now.hour

    # Morning standup (run once per day, between 6-10 AM UTC)
    last_standup = state.get("last_standup", "")
    if 6 <= hour <= 10 and _hours_since(last_standup) > 20:
        try:
            from c_suite.boardroom import BoardRoom
            print("[C-SUITE SCHED] Running morning standup...")
            board = BoardRoom()
            board.convene(quick=True)
            state["last_standup"] = now.isoformat()
            actions_run.append("morning_standup")
        except Exception as e:
            print(f"[C-SUITE SCHED] Standup error: {e}")

    # CFO cash check (run once per day, between 14-18 UTC)
    last_cash = state.get("last_cash_check", "")
    if 14 <= hour <= 18 and _hours_since(last_cash) > 20:
        try:
            from c_suite.ledgr import LedgrCFO
            print("[C-SUITE SCHED] Running CFO cash check...")
            LedgrCFO().cash_check()
            state["last_cash_check"] = now.isoformat()
            actions_run.append("cash_check")
        except Exception as e:
            print(f"[C-SUITE SCHED] Cash check error: {e}")

    # COO ops check (every 8 hours)
    last_ops = state.get("last_ops_check", "")
    if _hours_since(last_ops) > 8:
        try:
            from c_suite.vectis import VectisCOO
            print("[C-SUITE SCHED] Running COO ops check...")
            VectisCOO().ops_check()
            state["last_ops_check"] = now.isoformat()
            actions_run.append("ops_check")
        except Exception as e:
            print(f"[C-SUITE SCHED] Ops check error: {e}")

    # Full board meeting (weekly — every 168 hours)
    last_board = state.get("last_full_board", "")
    if _hours_since(last_board) > 168:
        try:
            from c_suite.boardroom import BoardRoom
            print("[C-SUITE SCHED] Running weekly board meeting...")
            board = BoardRoom()
            board.convene(quick=False)
            state["last_full_board"] = now.isoformat()
            actions_run.append("full_board")
        except Exception as e:
            print(f"[C-SUITE SCHED] Board meeting error: {e}")

    _save_state(state)
    return actions_run


def daemon_loop(interval_minutes: int = 30):
    """Run the C-Suite scheduler continuously."""
    print(f"[C-SUITE SCHED] Daemon started. Checking every {interval_minutes} min.")
    while True:
        try:
            actions = run_due_actions()
            if actions:
                print(f"[C-SUITE SCHED] Completed: {', '.join(actions)}")
            else:
                print(f"[C-SUITE SCHED] No actions due at {datetime.now(timezone.utc).strftime('%H:%M UTC')}")
        except Exception as e:
            print(f"[C-SUITE SCHED] Error: {e}")
        time.sleep(interval_minutes * 60)


def main():
    parser = argparse.ArgumentParser(description="C-Suite Executive Scheduler")
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    parser.add_argument("--force-board", action="store_true", help="Force full board meeting now")
    parser.add_argument("--force-standup", action="store_true", help="Force quick standup now")
    parser.add_argument("--interval", type=int, default=30, help="Check interval in minutes (daemon mode)")
    parser.add_argument("--provider", help="Force LLM provider")
    args = parser.parse_args()

    if args.force_board:
        from c_suite.boardroom import BoardRoom
        BoardRoom(provider=args.provider).convene(quick=False)
    elif args.force_standup:
        from c_suite.boardroom import BoardRoom
        BoardRoom(provider=args.provider).convene(quick=True)
    elif args.daemon:
        daemon_loop(args.interval)
    else:
        actions = run_due_actions()
        if actions:
            print(f"Actions executed: {', '.join(actions)}")
        else:
            print("No executive actions due right now.")


if __name__ == "__main__":
    main()
