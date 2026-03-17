"""NERVE Watchdog — 24/7 process guardian.

Spawns `automation.nerve --daemon` as a subprocess, monitors it every 30 seconds,
and auto-restarts on crash. Rate-limited to 10 restarts/hour to prevent spin-loops.

Usage:
    python -m automation.watchdog          # run watchdog (+ NERVE daemon)
    python -m automation.watchdog --status # print watchdog + NERVE status
    python -m automation.watchdog --stop   # write stop signal, watchdog exits cleanly

Windows Task Scheduler entry point:
    <VENV>\\Scripts\\python.exe -m automation.watchdog
"""

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PYTHON_EXE = sys.executable
STATE_FILE = PROJECT_ROOT / "data" / "nerve_state.json"
WATCHDOG_STATUS = PROJECT_ROOT / "data" / "watchdog_status.json"
STOP_SIGNAL = PROJECT_ROOT / "data" / "watchdog_stop.flag"
LOG_FILE = PROJECT_ROOT / "data" / "watchdog.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Watchdog tunables
CHECK_INTERVAL = 30          # seconds between health checks
STALE_THRESHOLD_MIN = 90     # minutes — NERVE cycle is 60 min, allow 30 min slack
MAX_RESTARTS_PER_HOUR = 10
RESTART_COOLDOWN = 60        # seconds between restart attempts

# Logging
_fmt = logging.Formatter("%(asctime)s [%(levelname)s] watchdog — %(message)s")
logger = logging.getLogger("watchdog")
if not logger.handlers:
    _sh = logging.StreamHandler()
    _sh.setFormatter(_fmt)
    logger.addHandler(_sh)
    _fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    _fh.setFormatter(_fmt)
    logger.addHandler(_fh)
    logger.setLevel(logging.INFO)
logger.propagate = False


def _save_status(state: dict):
    WATCHDOG_STATUS.parent.mkdir(parents=True, exist_ok=True)
    WATCHDOG_STATUS.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _nerve_cmd() -> list[str]:
    return [PYTHON_EXE, "-m", "automation.nerve", "--daemon"]


def _is_alive(proc: subprocess.Popen | None) -> bool:
    return proc is not None and proc.poll() is None


def _nerve_state_is_stale() -> bool:
    """Return True if NERVE hasn't updated its state file within STALE_THRESHOLD_MIN."""
    if not STATE_FILE.exists():
        return False  # NERVE hasn't run yet — not a signal to restart
    try:
        mtime = datetime.fromtimestamp(STATE_FILE.stat().st_mtime, tz=timezone.utc)
        age = (datetime.now(timezone.utc) - mtime).total_seconds() / 60
        return age > STALE_THRESHOLD_MIN
    except OSError:
        return False


def _restart_count_last_hour(restart_times: list[datetime]) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    return sum(1 for t in restart_times if t > cutoff)


def _escalate(message: str):
    """Log escalation — optionally email via SMTP (uses .env SMTP creds if available)."""
    logger.error(f"[ESCALATE] {message}")
    try:
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")
        import smtplib
        from email.message import EmailMessage

        smtp_host = os.getenv("SMTP_HOST", "")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASS", "")
        alert_to = os.getenv("ALERT_EMAIL", smtp_user)

        if not (smtp_host and smtp_user and smtp_pass):
            return  # No SMTP configured — silent

        msg = EmailMessage()
        msg["Subject"] = f"[DIGITAL LABOUR] Watchdog escalation — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        msg["From"] = smtp_user
        msg["To"] = alert_to
        msg.set_content(message)

        with smtplib.SMTP(smtp_host, smtp_port) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)
        logger.info("Escalation email sent.")
    except Exception as e:
        logger.warning(f"Escalation email failed (non-fatal): {e}")


def run_watchdog():
    """Main watchdog loop — starts NERVE and keeps it alive forever."""
    logger.info("=" * 60)
    logger.info("  NERVE WATCHDOG ONLINE")
    logger.info(f"  Project: {PROJECT_ROOT}")
    logger.info(f"  Python:  {PYTHON_EXE}")
    logger.info(f"  Check interval: {CHECK_INTERVAL}s | Stale threshold: {STALE_THRESHOLD_MIN}min")
    logger.info(f"  Max restarts/hr: {MAX_RESTARTS_PER_HOUR}")
    logger.info("=" * 60)

    # Remove any stale stop signal from a previous run
    STOP_SIGNAL.unlink(missing_ok=True)

    nerve_proc: subprocess.Popen | None = None
    restart_times: list[datetime] = []
    started_at = datetime.now(timezone.utc)
    last_restart: datetime | None = None

    def _start_nerve() -> subprocess.Popen:
        logger.info("Starting NERVE daemon...")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.Popen(
            _nerve_cmd(),
            cwd=str(PROJECT_ROOT),
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        logger.info(f"NERVE started — PID {proc.pid}")
        return proc

    # Graceful shutdown on Ctrl-C / SIGTERM
    _shutdown = [False]

    def _handle_signal(sig, frame):
        logger.info(f"Signal {sig} received — shutting down watchdog.")
        _shutdown[0] = True

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # Initial start
    nerve_proc = _start_nerve()
    restart_times.append(datetime.now(timezone.utc))

    while not _shutdown[0]:
        # Check stop-signal file
        if STOP_SIGNAL.exists():
            logger.info("Stop signal detected — exiting watchdog.")
            break

        time.sleep(CHECK_INTERVAL)

        # Update watchdog status file
        recent = _restart_count_last_hour(restart_times)
        uptime_h = (datetime.now(timezone.utc) - started_at).total_seconds() / 3600
        _save_status({
            "watchdog_pid": os.getpid(),
            "nerve_pid": nerve_proc.pid if _is_alive(nerve_proc) else None,
            "nerve_alive": _is_alive(nerve_proc),
            "uptime_hours": round(uptime_h, 2),
            "total_restarts": len(restart_times),
            "restarts_last_hour": recent,
            "last_restart": last_restart.isoformat() if last_restart else None,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        })

        # ── Health check ──────────────────────────────────────────────
        process_dead = not _is_alive(nerve_proc)
        state_stale = _nerve_state_is_stale()

        if not (process_dead or state_stale):
            continue  # All good

        reason = "process exited" if process_dead else "state file stale (frozen?)"
        logger.warning(f"NERVE unhealthy: {reason}")

        # Rate-limit restarts
        if recent >= MAX_RESTARTS_PER_HOUR:
            msg = (
                f"NERVE restarted {recent} times in the last hour. "
                f"Halting auto-restart — MANUAL INTERVENTION REQUIRED. Reason: {reason}"
            )
            _escalate(msg)
            logger.critical("Restart rate limit hit — watchdog will keep checking but not restart.")
            time.sleep(300)  # back-off 5 min before next check
            continue

        # Cooldown between restarts
        if last_restart:
            since = (datetime.now(timezone.utc) - last_restart).total_seconds()
            if since < RESTART_COOLDOWN:
                wait = RESTART_COOLDOWN - since
                logger.info(f"Cooldown: waiting {wait:.0f}s before restart.")
                time.sleep(wait)

        # Kill zombie if process is frozen (still "alive" but stale)
        if _is_alive(nerve_proc) and state_stale:
            logger.warning("Killing frozen NERVE process...")
            try:
                nerve_proc.terminate()
                nerve_proc.wait(timeout=15)
            except Exception:
                nerve_proc.kill()

        # Restart
        nerve_proc = _start_nerve()
        last_restart = datetime.now(timezone.utc)
        restart_times.append(last_restart)
        restart_times = [t for t in restart_times if t > datetime.now(timezone.utc) - timedelta(hours=2)]

        if recent >= 3:
            _escalate(
                f"NERVE has been restarted {recent + 1} times in the last hour. "
                f"Latest reason: {reason}. System is struggling."
            )

    # ── Shutdown ────────────────────────────────────────────────────────────
    logger.info("Watchdog shutting down — stopping NERVE...")
    if _is_alive(nerve_proc):
        nerve_proc.terminate()
        try:
            nerve_proc.wait(timeout=30)
            logger.info("NERVE stopped cleanly.")
        except subprocess.TimeoutExpired:
            nerve_proc.kill()
            logger.warning("NERVE killed (did not stop within 30s).")

    _save_status({
        "watchdog_pid": None,
        "nerve_pid": None,
        "nerve_alive": False,
        "uptime_hours": round((datetime.now(timezone.utc) - started_at).total_seconds() / 3600, 2),
        "total_restarts": len(restart_times),
        "status": "stopped",
        "stopped_at": datetime.now(timezone.utc).isoformat(),
    })
    logger.info("Watchdog offline.")


def show_status():
    """Print current watchdog + NERVE status."""
    if WATCHDOG_STATUS.exists():
        data = json.loads(WATCHDOG_STATUS.read_text(encoding="utf-8"))
        print(json.dumps(data, indent=2))
    else:
        print("[watchdog] No status file found — watchdog has not run.")

    if STATE_FILE.exists():
        nerve = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        print("\n[NERVE state]")
        print(json.dumps(nerve, indent=2))


def stop_watchdog():
    """Write stop signal so the running watchdog exits on its next check."""
    STOP_SIGNAL.touch()
    print(f"Stop signal written to {STOP_SIGNAL}")
    print("Watchdog will exit within the next 30 seconds.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NERVE Watchdog — keeps NERVE daemon alive 24/7")
    parser.add_argument("--status", action="store_true", help="Show watchdog + NERVE status")
    parser.add_argument("--stop", action="store_true", help="Signal running watchdog to stop")
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.stop:
        stop_watchdog()
    else:
        run_watchdog()
