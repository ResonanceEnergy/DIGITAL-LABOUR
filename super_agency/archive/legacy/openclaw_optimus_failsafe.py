#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  OPENCLAW OPTIMUS FAILSAFE                                                   ║
║  Monitors OpenClaw gateway + Discord channel every 15 minutes                ║
║  Auto-restarts if gateway is down or Discord is disconnected                 ║
║                                                                              ║
║  Checks:                                                                     ║
║    1. Gateway port 18789 is listening (TCP socket probe)                     ║
║    2. `openclaw gateway health` returns healthy                              ║
║    3. `openclaw channels status` shows Discord connected                     ║
║                                                                              ║
║  Recovery:                                                                   ║
║    - Attempts `openclaw gateway restart` first                               ║
║    - Falls back to kill + fresh `openclaw gateway start`                     ║
║    - Logs every check and restart to failsafe log + JSON history             ║
║                                                                              ║
║  Run: python openclaw_optimus_failsafe.py              (single check)        ║
║  Run: python openclaw_optimus_failsafe.py --daemon     (loop every 15 min)   ║
║  Run: python openclaw_optimus_failsafe.py --interval 5 (custom minutes)      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import argparse
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 18789
CHECK_INTERVAL_MINUTES = 15
MAX_RESTART_ATTEMPTS = 3
RESTART_COOLDOWN_SECONDS = 30
OPENCLAW_CMD = r"C:\Users\gripa\AppData\Roaming\npm\openclaw.cmd"

WORKSPACE = Path(__file__).parent
LOG_FILE = WORKSPACE / "openclaw_optimus_failsafe.log"
HISTORY_FILE = WORKSPACE / "optimus_state" / "openclaw_failsafe_history.json"

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - FAILSAFE - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("openclaw_failsafe")

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _find_openclaw() -> str:
    """Resolve the openclaw CLI path."""
    if os.path.isfile(OPENCLAW_CMD):
        return OPENCLAW_CMD
    # Fall back to PATH lookup
    try:
        result = subprocess.run(
            "where openclaw", capture_output=True, text=True, shell=True, check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            paths = result.stdout.strip().splitlines()
            cmd = next((p.strip() for p in paths if p.strip().endswith(".cmd")), None)
            return cmd or paths[0].strip()
    except Exception:
        pass
    return "openclaw"  # hope it's on PATH


def _run_cli(args: list, timeout: int = 30) -> Tuple[int, str, str]:
    """Run an openclaw CLI command and return (returncode, stdout, stderr)."""
    cli = _find_openclaw()
    cmd = [cli] + args if not cli.endswith(".cmd") else f'"{cli}" ' + " ".join(args)
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            shell=isinstance(cmd, str), check=False,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def _save_history(entry: Dict):
    """Append an entry to the JSON history file."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            history = []
    history.append(entry)
    # Keep last 500 entries
    if len(history) > 500:
        history = history[-500:]
    HISTORY_FILE.write_text(json.dumps(history, indent=2, default=str), encoding="utf-8")


# ═════════════════════════════════════════════════════════════════════════════
# HEALTH CHECKS
# ═════════════════════════════════════════════════════════════════════════════

def check_gateway_port() -> bool:
    """TCP probe: is port 18789 listening?"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((GATEWAY_HOST, GATEWAY_PORT))
        sock.close()
        return result == 0
    except (socket.error, OSError):
        return False


def check_gateway_health() -> Tuple[bool, str]:
    """Run `openclaw gateway health` and parse result."""
    rc, stdout, stderr = _run_cli(["gateway", "health", "--url", f"ws://{GATEWAY_HOST}:{GATEWAY_PORT}"])
    if rc == 0 and stdout:
        # Healthy if output contains "ok" or "healthy" (case-insensitive)
        healthy = any(kw in stdout.lower() for kw in ("ok", "healthy", "running", "connected"))
        return healthy, stdout
    return False, stderr or stdout or "no output"


def check_gateway_status_json() -> Tuple[bool, Dict]:
    """Run `openclaw gateway status --json` and parse result."""
    rc, stdout, stderr = _run_cli(["gateway", "status", "--json"])
    if rc == 0 and stdout:
        try:
            data = json.loads(stdout)
            running = data.get("running", False) or data.get("status") in ("running", "active")
            return running, data
        except json.JSONDecodeError:
            pass
    return False, {"error": stderr or stdout}


def check_discord_channel() -> Tuple[bool, str]:
    """Run `openclaw channels status` and verify Discord is connected."""
    rc, stdout, stderr = _run_cli(["channels", "status"])
    if rc == 0 and stdout:
        lines = stdout.lower()
        # Look for discord in the output and check it's connected/online
        if "discord" in lines:
            # Discord is listed - check if it's connected
            discord_connected = any(
                kw in lines
                for kw in ("discord: connected", "discord: online", "discord: active",
                           "discord  connected", "discord  online", "discord  active",
                           "discord ✓", "discord: ✓")
            )
            if discord_connected:
                return True, "Discord channel connected"
            # Discord listed but not marked connected - might still be ok
            # Check for explicit error states
            discord_error = any(
                kw in lines
                for kw in ("discord: disconnected", "discord: error", "discord: offline",
                           "discord: failed", "discord  disconnected", "discord  error")
            )
            if discord_error:
                return False, "Discord channel disconnected/errored"
            # Ambiguous - assume connected if discord is listed with no error
            return True, "Discord channel listed (status ambiguous, assuming OK)"
        return False, "Discord channel not found in status output"
    return False, stderr or "channels status command failed"


def run_full_health_check() -> Dict:
    """Run all health checks and return a comprehensive status dict."""
    timestamp = datetime.now().isoformat()
    logger.info("=" * 60)
    logger.info("FAILSAFE HEALTH CHECK STARTING")
    logger.info("=" * 60)

    # Check 1: TCP port probe
    port_ok = check_gateway_port()
    logger.info(f"  [1/4] Gateway port {GATEWAY_PORT}: {'UP' if port_ok else 'DOWN'}")

    # Check 2: Gateway health CLI
    health_ok, health_msg = check_gateway_health()
    logger.info(f"  [2/4] Gateway health: {'OK' if health_ok else 'FAIL'} - {health_msg[:100]}")

    # Check 3: Gateway status JSON
    status_ok, status_data = check_gateway_status_json()
    logger.info(f"  [3/4] Gateway status: {'RUNNING' if status_ok else 'NOT RUNNING'}")

    # Check 4: Discord channel
    discord_ok, discord_msg = check_discord_channel()
    logger.info(f"  [4/4] Discord channel: {'CONNECTED' if discord_ok else 'DISCONNECTED'} - {discord_msg}")

    # Overall verdict
    gateway_alive = port_ok and (health_ok or status_ok)
    all_ok = gateway_alive and discord_ok

    result = {
        "timestamp": timestamp,
        "port_up": port_ok,
        "gateway_healthy": health_ok,
        "gateway_running": status_ok,
        "discord_connected": discord_ok,
        "discord_detail": discord_msg,
        "overall_ok": all_ok,
        "gateway_alive": gateway_alive,
        "action": "none",
    }

    if all_ok:
        logger.info("  VERDICT: ALL SYSTEMS NOMINAL - OpenClaw Optimus healthy")
    elif not gateway_alive:
        logger.warning("  VERDICT: GATEWAY DOWN - restart required")
        result["action"] = "restart_gateway"
    elif not discord_ok:
        logger.warning("  VERDICT: DISCORD DISCONNECTED - restart required")
        result["action"] = "restart_gateway"

    return result


# ═════════════════════════════════════════════════════════════════════════════
# RECOVERY / RESTART
# ═════════════════════════════════════════════════════════════════════════════

def restart_openclaw() -> bool:
    """Attempt to restart the OpenClaw gateway and reconnect Discord."""
    logger.info("=" * 60)
    logger.info("FAILSAFE RECOVERY: Restarting OpenClaw gateway...")
    logger.info("=" * 60)

    for attempt in range(1, MAX_RESTART_ATTEMPTS + 1):
        logger.info(f"  Restart attempt {attempt}/{MAX_RESTART_ATTEMPTS}")

        # Method 1: Try graceful restart via CLI
        logger.info("  Trying: openclaw gateway restart ...")
        rc, stdout, stderr = _run_cli(["gateway", "restart"], timeout=60)
        if rc == 0:
            logger.info(f"  Gateway restart command succeeded: {stdout[:100]}")
            time.sleep(10)  # Give gateway time to fully initialize

            # Verify gateway came back
            if check_gateway_port():
                logger.info("  Gateway port is responding after restart")
                # Give Discord channel time to reconnect
                time.sleep(15)
                discord_ok, discord_msg = check_discord_channel()
                if discord_ok:
                    logger.info(f"  Discord reconnected: {discord_msg}")
                    return True
                else:
                    logger.warning(f"  Discord not yet connected: {discord_msg}")
                    # Try explicit channel reconnect
                    _try_discord_reconnect()
                    time.sleep(10)
                    discord_ok, discord_msg = check_discord_channel()
                    if discord_ok:
                        logger.info(f"  Discord reconnected after explicit login: {discord_msg}")
                        return True
            else:
                logger.warning("  Gateway port not responding after restart command")

        # Method 2: Force stop + start
        logger.info("  Trying: force stop + fresh start ...")
        _run_cli(["gateway", "stop"], timeout=15)
        time.sleep(5)

        # Kill any orphan openclaw processes
        _kill_orphan_processes()
        time.sleep(3)

        # Fresh start
        rc, stdout, stderr = _run_cli(
            ["gateway", "start", "--port", str(GATEWAY_PORT), "--allow-unconfigured", "--force"],
            timeout=60,
        )
        logger.info(f"  Fresh start result: rc={rc}, out={stdout[:100]}")
        time.sleep(10)

        if check_gateway_port():
            logger.info("  Gateway port is responding after fresh start")
            time.sleep(15)
            discord_ok, discord_msg = check_discord_channel()
            if discord_ok:
                logger.info(f"  Discord connected: {discord_msg}")
                return True
            else:
                _try_discord_reconnect()
                time.sleep(10)
                discord_ok, discord_msg = check_discord_channel()
                if discord_ok:
                    logger.info("  Discord reconnected after explicit login")
                    return True
                logger.warning(f"  Discord still not connected: {discord_msg}")

        if attempt < MAX_RESTART_ATTEMPTS:
            logger.info(f"  Cooling down {RESTART_COOLDOWN_SECONDS}s before next attempt...")
            time.sleep(RESTART_COOLDOWN_SECONDS)

    logger.error("  ALL RESTART ATTEMPTS EXHAUSTED - manual intervention required")
    return False


def _try_discord_reconnect():
    """Attempt to explicitly reconnect the Discord channel."""
    logger.info("  Attempting Discord channel reconnect...")
    _run_cli(["channels", "login", "--channel", "discord"], timeout=30)


def _kill_orphan_processes():
    """Kill any orphan openclaw/node processes holding the port."""
    try:
        import psutil
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = " ".join(proc.info.get("cmdline") or []).lower()
                name = (proc.info.get("name") or "").lower()
                if "openclaw" in cmdline or "openclaw" in name:
                    logger.info(f"  Killing orphan process: PID {proc.pid} ({name})")
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except ImportError:
        # psutil not available, try taskkill on Windows
        try:
            subprocess.run(
                'taskkill /F /FI "WINDOWTITLE eq openclaw*" >nul 2>&1',
                shell=True, check=False, timeout=10,
            )
        except Exception:
            pass


# ═════════════════════════════════════════════════════════════════════════════
# MAIN LOOP
# ═════════════════════════════════════════════════════════════════════════════

def run_single_check():
    """Run a single health check cycle and restart if needed."""
    result = run_full_health_check()

    if not result["overall_ok"]:
        logger.warning(f"FAILSAFE TRIGGERED - Action: {result['action']}")
        success = restart_openclaw()
        result["restart_attempted"] = True
        result["restart_success"] = success
        if success:
            logger.info("FAILSAFE RECOVERY SUCCESSFUL")
        else:
            logger.error("FAILSAFE RECOVERY FAILED - OpenClaw may need manual restart")
    else:
        result["restart_attempted"] = False

    _save_history(result)
    return result


def run_daemon(interval_minutes: int = CHECK_INTERVAL_MINUTES):
    """Run the failsafe monitor as a continuous daemon."""
    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║  OPENCLAW OPTIMUS FAILSAFE DAEMON STARTED               ║")
    logger.info(f"║  Check interval: {interval_minutes} minutes" + " " * (40 - len(str(interval_minutes))) + "║")
    logger.info(f"║  Gateway: {GATEWAY_HOST}:{GATEWAY_PORT}" + " " * 27 + "║")
    logger.info("║  Press Ctrl+C to stop                                   ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")

    # Handle graceful shutdown
    running = True

    def signal_handler(sig, frame):
        nonlocal running
        logger.info("FAILSAFE DAEMON: Shutdown signal received, exiting...")
        running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    consecutive_failures = 0
    check_count = 0

    while running:
        check_count += 1
        logger.info(f"--- Failsafe Check #{check_count} ---")

        try:
            result = run_single_check()

            if result["overall_ok"]:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    logger.critical(
                        f"CRITICAL: {consecutive_failures} consecutive failures! "
                        "OpenClaw may have a deeper issue requiring manual intervention."
                    )
        except Exception as e:
            logger.error(f"Failsafe check error: {e}", exc_info=True)
            consecutive_failures += 1

        # Sleep in 10-second intervals so we can respond to signals
        sleep_seconds = interval_minutes * 60
        logger.info(f"Next check in {interval_minutes} minutes...")
        for _ in range(sleep_seconds // 10):
            if not running:
                break
            time.sleep(10)
        if running and sleep_seconds % 10:
            time.sleep(sleep_seconds % 10)

    logger.info("FAILSAFE DAEMON STOPPED")


# ═════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="OpenClaw Optimus Failsafe - Monitor and auto-restart OpenClaw gateway + Discord"
    )
    parser.add_argument(
        "--daemon", action="store_true",
        help="Run as continuous daemon (checks every --interval minutes)"
    )
    parser.add_argument(
        "--interval", type=int, default=CHECK_INTERVAL_MINUTES,
        help=f"Check interval in minutes (default: {CHECK_INTERVAL_MINUTES})"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Print last failsafe history entries and exit"
    )
    args = parser.parse_args()

    if args.status:
        if HISTORY_FILE.exists():
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            last_entries = history[-10:]
            print(json.dumps(last_entries, indent=2))
        else:
            print("No failsafe history found.")
        return

    if args.daemon:
        run_daemon(args.interval)
    else:
        result = run_single_check()
        status = "HEALTHY" if result["overall_ok"] else "UNHEALTHY"
        print(f"\nOpenClaw Optimus Status: {status}")
        if result.get("restart_attempted"):
            print(f"Restart attempted: {'SUCCESS' if result['restart_success'] else 'FAILED'}")
        sys.exit(0 if result["overall_ok"] else 1)


if __name__ == "__main__":
    main()
