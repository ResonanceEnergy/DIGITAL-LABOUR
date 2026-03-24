"""NERVE Watchdog — RETIRED.

The Python watchdog layer has been removed. NERVE is now supervised directly by
Windows Task Scheduler, eliminating:
  - Wrong-Python fallback (Python 3.14 breaks aiohttp)
  - Duplicate NERVE instances (adoption via daemon_pids.json never worked)
  - Stale-threshold killing a healthy NERVE mid-22-phase-cycle
  - Three-layer supervisor stack (health_check.ps1 → watchdog.py → nerve.py)

NEW SETUP — run once as Administrator:
    powershell -ExecutionPolicy Bypass -File scripts\\nerve_service.ps1 -Install

NERVE control:
    python -m automation.nerve --daemon    # start daemon
    python -m automation.nerve --stop      # graceful stop
    python -m automation.nerve --status    # status

This module is kept for backwards-compatibility with bitrage_monitor.py C2 commands.
The watchdog_start / watchdog_stop / watchdog_status commands now control NERVE
directly without spawning this watchdog as an intermediary.
"""

import json
import os
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

_VENV_PYTHONW = PROJECT_ROOT / ".venv" / "Scripts" / "pythonw.exe"
_VENV_PYTHON  = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
PYTHON_EXE    = str(_VENV_PYTHONW) if _VENV_PYTHONW.exists() else str(_VENV_PYTHON)
STATE_FILE    = PROJECT_ROOT / "data" / "nerve_state.json"
PID_FILE      = PROJECT_ROOT / "data" / "nerve.pid"
NERVE_STOP    = PROJECT_ROOT / "data" / "nerve_stop.flag"

def _nerve_alive_pid() -> int | None:
    """Return NERVE daemon PID if it is actually running, else None."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, 0)
            return pid
        except (OSError, ValueError):
            PID_FILE.unlink(missing_ok=True)
    return None


def run_watchdog():
    """RETIRED — watchdog is no longer used. Prints guidance and exits."""
    print()
    print("  NERVE Watchdog is RETIRED.")
    print()
    print("  NERVE is now supervised directly by Windows Task Scheduler,")
    print("  which eliminates the duplicate-instance and wrong-Python bugs.")
    print()
    print("  To register the Task Scheduler entry (run once as Administrator):")
    print(r"    powershell -ExecutionPolicy Bypass -File scripts\nerve_service.ps1 -Install")
    print()
    print("  Manual control:")
    print("    python -m automation.nerve --daemon   # start")
    print("    python -m automation.nerve --stop     # stop")
    print("    python -m automation.nerve --status   # status")
    print()


def show_status():
    """Show NERVE status (reads nerve_state.json + PID file)."""
    pid = _nerve_alive_pid()
    if STATE_FILE.exists():
        nerve = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        nerve["nerve_pid"]   = pid
        nerve["nerve_alive"] = pid is not None
        nerve["supervisor"]  = "Windows Task Scheduler (direct)"
        print(json.dumps(nerve, indent=2))
    else:
        print(json.dumps({
            "nerve_pid":   pid,
            "nerve_alive": pid is not None,
            "supervisor":  "Windows Task Scheduler (direct)",
            "note":        "nerve_state.json not found — NERVE has not run a full cycle yet",
        }, indent=2))


def stop_watchdog():
    """Signal NERVE daemon to stop gracefully."""
    import signal as _sig
    NERVE_STOP.parent.mkdir(parents=True, exist_ok=True)
    NERVE_STOP.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
    pid = _nerve_alive_pid()
    if pid:
        try:
            os.kill(pid, _sig.SIGTERM)
            print(f"SIGTERM sent to NERVE PID {pid}. Daemon will stop after current phase.")
        except OSError as e:
            print(f"Could not signal PID {pid}: {e}")
    else:
        print("NERVE does not appear to be running (no valid PID file).")
    print(f"Stop flag written to {NERVE_STOP}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NERVE Watchdog (retired — use nerve_service.ps1)")
    parser.add_argument("--status", action="store_true", help="Show NERVE status")
    parser.add_argument("--stop",   action="store_true", help="Stop the NERVE daemon")
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.stop:
        stop_watchdog()
    else:
        run_watchdog()
