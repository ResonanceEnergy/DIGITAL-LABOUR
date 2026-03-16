#!/usr/bin/env python3
"""
REPO DEPOT AUTONOMOUS SCHEDULER
================================
Persistent daemon that drives the FlywheelController continuously.
Manages API keys, logging to file, PID tracking, and graceful shutdown.

Usage:
  python3 autonomous_scheduler.py start         # Start daemon (foreground)
  python3 autonomous_scheduler.py start --bg    # Start daemon (background via nohup)
  python3 autonomous_scheduler.py stop          # Stop running daemon
  python3 autonomous_scheduler.py status        # Show status
  python3 autonomous_scheduler.py scan          # Show repo staleness
  python3 autonomous_scheduler.py once          # Run one cycle and exit

Configuration is loaded from state/flywheel/scheduler_config.json if it exists,
otherwise uses sensible defaults. API keys are read from environment variables.
"""

import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# ===========================================================================
# PATHS
# ===========================================================================

WORKSPACE = Path(
    os.environ.get(
        "REPODEPOT_WORKSPACE",
        str(Path(__file__).parent.parent),
    )
)
STATE_DIR = WORKSPACE / "state" / "flywheel"
PID_FILE = STATE_DIR / "scheduler.pid"
LOG_FILE = STATE_DIR / "scheduler.log"
CONFIG_FILE = STATE_DIR / "scheduler_config.json"

# ===========================================================================
# DEFAULT CONFIG
# ===========================================================================

DEFAULT_CONFIG = {
    "cycle_interval_seconds": 300,  # 5 minutes between cycles
    "max_repos_per_cycle": 3,  # process 3 repos each cycle
    "cooldown_hours": 24,  # skip repos touched in last 24h
    "agent_type": "both",  # run OPTIMUS + GASKET
}


# ===========================================================================
# HELPERS
# ===========================================================================


def load_config() -> Dict[str, Any]:
    """Load config from file or return defaults"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                user_cfg = json.load(f)
            cfg = DEFAULT_CONFIG.copy()
            cfg.update(user_cfg)
            return cfg
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_default_config():
    """Write default config if none exists"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)


def setup_logging():
    """Configure logging to file + console"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    # Root logger
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # File handler (append mode, rotates implicitly by size check)
    fh = logging.FileHandler(LOG_FILE, mode="a")
    fh.setLevel(logging.INFO)
    fh.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(name)s] %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
    )
    root.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(
        logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s", datefmt="%H:%M:%S")
    )
    root.addHandler(ch)

    # Truncate log if too large (> 10MB)
    if LOG_FILE.exists() and LOG_FILE.stat().st_size > 10 * 1024 * 1024:
        lines = LOG_FILE.read_text().splitlines()
        LOG_FILE.write_text("\n".join(lines[-5000:]) + "\n")


def check_api_keys() -> Dict[str, bool]:
    """Check which API keys are available"""
    keys = {
        "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
        "XAI_API_KEY": bool(os.environ.get("XAI_API_KEY")),
        "GEMINI_API_KEY": bool(os.environ.get("GEMINI_API_KEY")),
    }
    return keys


def write_pid():
    """Write current PID to file"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))


def read_pid() -> Optional[int]:
    """Read PID from file"""
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except Exception:
            pass
    return None


def clear_pid():
    """Remove PID file"""
    if PID_FILE.exists():
        PID_FILE.unlink()


def is_running() -> bool:
    """Check if scheduler is currently running"""
    pid = read_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, 0)  # signal 0 = check existence
        return True
    except ProcessLookupError:
        clear_pid()
        return False
    except PermissionError:
        return True  # process exists but we can't signal it


# ===========================================================================
# COMMANDS
# ===========================================================================


def cmd_start(background: bool = False):
    """Start the flywheel scheduler"""
    if is_running():
        pid = read_pid()
        print(f"Scheduler already running (PID {pid}). Use 'stop' first.")
        return

    # Check API keys
    keys = check_api_keys()
    available = [k for k, v in keys.items() if v]
    missing = [k for k, v in keys.items() if not v]

    if not available:
        print("ERROR: No API keys found in environment!")
        print("Set at least one of: ANTHROPIC_API_KEY, OPENAI_API_KEY, XAI_API_KEY")
        print("\nExample:")
        print('  export ANTHROPIC_API_KEY="sk-ant-..."')
        print("  python3 autonomous_scheduler.py start")
        return

    if background:
        # Launch self in background via nohup
        env = os.environ.copy()
        cmd = [sys.executable, __file__, "_run_daemon"]
        proc = subprocess.Popen(
            cmd,
            env=env,
            stdout=open(LOG_FILE, "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        print(f"Scheduler started in background (PID {proc.pid})")
        print(f"Log: {LOG_FILE}")
        print(f"Stop: python3 {__file__} stop")
        return

    # Foreground start
    _run_daemon()


def _run_daemon():
    """Internal: actually run the flywheel loop"""
    setup_logging()
    logger = logging.getLogger("scheduler")

    # Write PID
    write_pid()

    # Signal handlers for graceful shutdown
    controller = [None]  # mutable reference for signal handler

    def shutdown_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        if controller[0]:
            controller[0].stop()
        clear_pid()

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    # Load config
    config = load_config()
    save_default_config()

    # Check API keys
    keys = check_api_keys()
    logger.info("=" * 60)
    logger.info("REPO DEPOT AUTONOMOUS SCHEDULER")
    logger.info("=" * 60)
    logger.info(f"  PID:       {os.getpid()}")
    logger.info(f"  Workspace: {WORKSPACE}")
    logger.info(f"  Interval:  {config['cycle_interval_seconds']}s")
    logger.info(f"  Max repos: {config['max_repos_per_cycle']}")
    logger.info(f"  Cooldown:  {config['cooldown_hours']}h")
    logger.info(f"  Agents:    {config['agent_type']}")
    for k, v in keys.items():
        logger.info(f"  {k}: {'SET' if v else 'MISSING'}")
    logger.info("=" * 60)

    if not any(keys.values()):
        logger.error("No API keys available. Cannot run agents. Exiting.")
        clear_pid()
        return

    # Import and initialize flywheel
    sys.path.insert(0, str(WORKSPACE))
    from repo_depot.flywheel.flywheel_controller import FlywheelController

    ctrl = FlywheelController(WORKSPACE, config)
    controller[0] = ctrl

    try:
        ctrl.start()
    except Exception as e:
        logger.error(f"FATAL: {e}")
    finally:
        clear_pid()
        logger.info("Scheduler exited cleanly")


def cmd_stop():
    """Stop the running scheduler"""
    pid = read_pid()
    if pid is None:
        print("No scheduler is running.")
        return

    if not is_running():
        print("Scheduler is not running (stale PID file). Cleaning up.")
        clear_pid()
        return

    print(f"Stopping scheduler (PID {pid})...")
    try:
        os.kill(pid, signal.SIGTERM)
        # Wait for it to die
        for _ in range(30):
            time.sleep(1)
            if not is_running():
                print("Scheduler stopped.")
                return
        # Force kill
        print("Force killing...")
        os.kill(pid, signal.SIGKILL)
        time.sleep(1)
        clear_pid()
        print("Scheduler force-killed.")
    except ProcessLookupError:
        clear_pid()
        print("Scheduler already stopped.")
    except Exception as e:
        print(f"Error stopping: {e}")


def cmd_status():
    """Show scheduler status"""
    running = is_running()
    pid = read_pid()

    print("=" * 50)
    print("REPO DEPOT FLYWHEEL STATUS")
    print("=" * 50)
    print(f"  Running:   {'YES' if running else 'NO'}")
    if pid:
        print(f"  PID:       {pid}")
    print(f"  Workspace: {WORKSPACE}")
    print(f"  Log:       {LOG_FILE}")
    print(f"  Config:    {CONFIG_FILE}")

    # API keys
    keys = check_api_keys()
    for k, v in keys.items():
        print(f"  {k}: {'SET' if v else 'MISSING'}")

    # Load flywheel status if available
    cycle_count_file = STATE_DIR / "cycle_count.txt"
    cycle_log_file = STATE_DIR / "cycle_log.jsonl"

    if cycle_count_file.exists():
        try:
            count = int(cycle_count_file.read_text().strip())
            print(f"\n  Cycles completed: {count}")
        except Exception:
            pass

    if cycle_log_file.exists():
        try:
            lines = cycle_log_file.read_text().strip().splitlines()
            recent = [json.loads(l) for l in lines[-5:]]
            print(f"\n  Recent cycles (last {len(recent)}):")
            for c in recent:
                print(
                    f"    Cycle {c['cycle']}: "
                    f"{c['tasks_succeeded']}/{c['tasks_dispatched']} tasks, "
                    f"{c['artifacts_created']} artifacts, "
                    f"{c['commits_made']} commits, "
                    f"{c['duration_seconds']:.0f}s"
                )
        except Exception:
            pass

    # Load config
    config = load_config()
    print(f"\n  Config:")
    for k, v in config.items():
        print(f"    {k}: {v}")

    print("=" * 50)


def cmd_scan():
    """Scan repos and show staleness"""
    sys.path.insert(0, str(WORKSPACE))
    from repo_depot.flywheel.flywheel_controller import FlywheelController

    config = load_config()
    ctrl = FlywheelController(WORKSPACE, config)
    staleness = ctrl.scan_repos()

    print(
        f"\n{'Repo':<35} {'Tier':<5} {'Score':<8} {'Stale(d)':<10} {'Docs':<5} {'Tests':<6} {'Arch':<5}"
    )
    print("-" * 80)
    for s in staleness:
        print(
            f"{s.name:<35} {s.tier:<5} {s.priority_score:<8.0f} "
            f"{s.days_since_agent_commit:<10.1f} "
            f"{'Y' if s.has_docs else 'N':<5} "
            f"{'Y' if s.has_tests else 'N':<6} "
            f"{'Y' if s.has_architecture else 'N':<5}"
        )

    print(f"\nTotal: {len(staleness)} repos scanned")
    print(f"Top 3 for next cycle: {', '.join(s.name for s in staleness[:3])}")


def cmd_once():
    """Run one cycle and exit"""
    setup_logging()
    logger = logging.getLogger("scheduler")

    keys = check_api_keys()
    if not any(keys.values()):
        print("ERROR: No API keys set. Cannot run.")
        return

    sys.path.insert(0, str(WORKSPACE))
    from repo_depot.flywheel.flywheel_controller import FlywheelController

    config = load_config()
    ctrl = FlywheelController(WORKSPACE, config)
    result = ctrl.run_one_cycle()

    print(f"\nResult: {result.tasks_succeeded}/{result.tasks_dispatched} tasks succeeded")
    print(f"Artifacts: {result.artifacts_created}, Commits: {result.commits_made}")
    if result.errors:
        print(f"Errors: {len(result.errors)}")


# ===========================================================================
# MAIN
# ===========================================================================


def main():
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    if len(sys.argv) < 2:
        print("REPO DEPOT Autonomous Scheduler")
        print()
        print("Usage:")
        print(f"  python3 {sys.argv[0]} start         Start scheduler (foreground)")
        print(f"  python3 {sys.argv[0]} start --bg    Start scheduler (background)")
        print(f"  python3 {sys.argv[0]} stop          Stop running scheduler")
        print(f"  python3 {sys.argv[0]} status        Show status")
        print(f"  python3 {sys.argv[0]} scan          Show repo staleness")
        print(f"  python3 {sys.argv[0]} once          Run one cycle and exit")
        return

    command = sys.argv[1]

    if command == "start":
        bg = "--bg" in sys.argv or "--background" in sys.argv
        cmd_start(background=bg)
    elif command == "stop":
        cmd_stop()
    elif command == "status":
        cmd_status()
    elif command == "scan":
        cmd_scan()
    elif command == "once":
        cmd_once()
    elif command == "_run_daemon":
        _run_daemon()
    else:
        print(f"Unknown command: {command}")
        print("Valid: start, stop, status, scan, once")


if __name__ == "__main__":
    main()
