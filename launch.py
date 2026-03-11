"""Master Launch Script — Starts ALL Digital Labour automation in one shot.

Activates every daemon, checks follow-ups, fires revenue checks, opens platforms.
One command to rule them all.

Usage:
    python launch.py                    # Full launch: all daemons + checks
    python launch.py --daemons          # Start background daemons only
    python launch.py --checks           # Run one-shot checks only (follow-ups, revenue, status)
    python launch.py --platforms        # Open platform registration URLs
    python launch.py --status           # Show status of all systems
    python launch.py --kill             # Stop all running daemons
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

DAEMON_PID_FILE = PROJECT_ROOT / "data" / "daemon_pids.json"


# ── Daemon Management ──────────────────────────────────────────

def _save_pids(pids: dict):
    DAEMON_PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    DAEMON_PID_FILE.write_text(json.dumps(pids, indent=2), encoding="utf-8")


def _load_pids() -> dict:
    if DAEMON_PID_FILE.exists():
        return json.loads(DAEMON_PID_FILE.read_text(encoding="utf-8"))
    return {}


def _is_running(pid: int) -> bool:
    """Check if PID is alive (Windows & Unix)."""
    try:
        if sys.platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except (OSError, PermissionError):
        return False


def start_daemons():
    """Start all background daemons: NERVE, C-Suite, Task Scheduler."""
    pids = _load_pids()
    python = sys.executable
    daemons = [
        {
            "name": "NERVE",
            "cmd": [python, "-m", "automation.nerve", "--daemon"],
            "desc": "Nexus Engine — 24/7 autonomous cycles (outreach, healing, C-Suite)",
        },
        {
            "name": "C-Suite Scheduler",
            "cmd": [python, "c_suite/scheduler.py", "--daemon"],
            "desc": "Executive cadence — standup, CFO cash, COO ops",
        },
        {
            "name": "Task Scheduler",
            "cmd": [python, "scheduler/runner.py", "--daemon"],
            "desc": "Retainer client task runner — 5 min checks",
        },
        {
            "name": "Revenue Daemon",
            "cmd": [python, "-m", "automation.revenue_daemon", "--daemon"],
            "desc": "Revenue monitoring — Stripe polling + income updates",
        },
    ]

    print(f"\n{'='*70}")
    print(f"  DIGITAL LABOUR — DAEMON LAUNCH")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*70}\n")

    for d in daemons:
        name = d["name"]

        # Check if already running
        existing_pid = pids.get(name, {}).get("pid")
        if existing_pid and _is_running(existing_pid):
            print(f"  [SKIP] {name} already running (PID {existing_pid})")
            continue

        print(f"  [START] {name} — {d['desc']}")
        try:
            proc = subprocess.Popen(
                d["cmd"],
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            )
            pids[name] = {
                "pid": proc.pid,
                "started": datetime.now(timezone.utc).isoformat(),
                "cmd": " ".join(d["cmd"]),
            }
            print(f"          PID {proc.pid} ✓")
        except Exception as e:
            print(f"          FAILED: {e}")

    _save_pids(pids)
    print(f"\n  All daemons launched. PIDs saved to data/daemon_pids.json")


def stop_daemons():
    """Stop all known daemon processes."""
    pids = _load_pids()
    if not pids:
        print("  No tracked daemons.")
        return

    print(f"\n{'='*70}")
    print(f"  STOPPING ALL DAEMONS")
    print(f"{'='*70}\n")

    for name, info in list(pids.items()):
        pid = info.get("pid")
        if pid and _is_running(pid):
            try:
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                                   capture_output=True, check=False)
                else:
                    os.kill(pid, 15)  # SIGTERM
                print(f"  [STOP] {name} (PID {pid}) — killed")
            except Exception as e:
                print(f"  [WARN] {name} (PID {pid}) — {e}")
        else:
            print(f"  [SKIP] {name} — not running")
        del pids[name]

    _save_pids(pids)
    print(f"\n  All daemons stopped.")


# ── One-Shot Checks ────────────────────────────────────────────

def run_checks():
    """Run all one-shot checks: follow-ups, revenue, reprocess fails."""
    print(f"\n{'='*70}")
    print(f"  DIGITAL LABOUR — SYSTEM CHECKS")
    print(f"{'='*70}")

    # 1. Follow-up check
    print(f"\n── Follow-Up Check ──")
    try:
        from automation.outreach import send_followups
        followups = send_followups()
        if followups:
            print(f"  Sent {len(followups)} follow-up(s)")
        else:
            print(f"  No follow-ups due right now")
    except Exception as e:
        print(f"  [ERROR] {e}")

    # 2. Revenue check
    print(f"\n── Revenue Check ──")
    try:
        from automation.revenue_daemon import check_stripe_revenue
        rev = check_stripe_revenue()
        print(f"  Stripe revenue: ${rev.get('total', 0):.2f}")
    except Exception as e:
        print(f"  [ERROR] {e}")

    # 3. Outreach status
    print(f"\n── Outreach Status ──")
    try:
        from automation.outreach import show_status as outreach_status
        outreach_status()
    except Exception as e:
        print(f"  [ERROR] {e}")

    # 4. Income tracker summary
    print(f"\n── Income Sources ──")
    try:
        from income.tracker import print_summary
        print_summary()
    except Exception as e:
        print(f"  [ERROR] {e}")

    # 5. NERVE status
    print(f"\n── NERVE Status ──")
    try:
        from automation.nerve import show_status
        show_status()
    except Exception as e:
        print(f"  [ERROR] {e}")


# ── Platform Opener ────────────────────────────────────────────

def open_platforms():
    """Open all platform registration URLs in browser."""
    import webbrowser
    platforms = [
        ("Stripe Dashboard", "https://dashboard.stripe.com/settings/account"),
        ("Freelancer.com", "https://www.freelancer.com/signup"),
        ("Fiverr", "https://www.fiverr.com/join"),
        ("Upwork", "https://www.upwork.com/nx/signup/"),
        ("RapidAPI", "https://rapidapi.com/auth/sign-up"),
        ("Chatbase", "https://www.chatbase.co/"),
        ("Botpress", "https://app.botpress.cloud/"),
        ("Relevance AI", "https://app.relevanceai.com/signup"),
    ]

    print(f"\n{'='*70}")
    print(f"  OPENING PLATFORM REGISTRATION PAGES")
    print(f"{'='*70}\n")

    for name, url in platforms:
        print(f"  [{name}] {url}")
        webbrowser.open(url)
        time.sleep(1)  # Stagger to avoid browser overload

    print(f"\n  Opened {len(platforms)} tabs. Register on each, then:")
    print(f"  → python -m income.tracker --update <source> registered")


# ── Status Display ─────────────────────────────────────────────

def show_status():
    """Show status of all Digital Labour systems."""
    print(f"\n{'='*70}")
    print(f"  DIGITAL LABOUR — FULL STATUS")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*70}")

    # Daemon status
    pids = _load_pids()
    print(f"\n── Daemons ──")
    if pids:
        for name, info in pids.items():
            pid = info.get("pid")
            alive = _is_running(pid) if pid else False
            status = "RUNNING" if alive else "DEAD"
            started = info.get("started", "?")[:16]
            print(f"  {name:25s} PID {pid:>6}  {status:8s}  since {started}")
    else:
        print(f"  No daemons tracked. Run: python launch.py --daemons")

    # Run subsystem status checks
    run_checks()


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Digital Labour Master Launch")
    parser.add_argument("--daemons", action="store_true", help="Start all background daemons")
    parser.add_argument("--checks", action="store_true", help="Run one-shot system checks")
    parser.add_argument("--platforms", action="store_true", help="Open platform registration URLs")
    parser.add_argument("--status", action="store_true", help="Full status report")
    parser.add_argument("--kill", action="store_true", help="Stop all daemons")
    args = parser.parse_args()

    if args.kill:
        stop_daemons()
    elif args.daemons:
        start_daemons()
    elif args.checks:
        run_checks()
    elif args.platforms:
        open_platforms()
    elif args.status:
        show_status()
    else:
        # Full launch: daemons + checks
        start_daemons()
        time.sleep(2)
        run_checks()
        print(f"\n{'='*70}")
        print(f"  ALL SYSTEMS GO")
        print(f"  Daemons running in background. Use --status to check anytime.")
        print(f"  Use --kill to stop all daemons.")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
