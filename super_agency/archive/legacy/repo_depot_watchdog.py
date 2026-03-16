#!/usr/bin/env python3
"""
REPO DEPOT WATCHDOG - 24/7/365 FAILSAFE DAEMON
===============================================
CRITICAL INFRASTRUCTURE - TOP PRIORITY

This watchdog ensures Repo Depot NEVER goes down.
It monitors the process and automatically restarts if:
- Process crashes
- Process becomes unresponsive
- System reboots
- Any other failure condition

RUN THIS AS A PERSISTENT SERVICE.
"""

import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import psutil

# Configure logging
LOG_FILE = Path(__file__).parent / "repo_depot_watchdog.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - WATCHDOG - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False)),
        logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
WORKSPACE = Path(__file__).parent
REPO_DEPOT_SCRIPT = WORKSPACE / "optimus_repo_depot_launcher.py"
STATUS_FILE = WORKSPACE / "repo_depot_status.json"
WATCHDOG_STATUS_FILE = WORKSPACE / "repo_depot_watchdog_status.json"
PYTHON_EXE = WORKSPACE / ".venv" / "Scripts" / "python.exe"
CHECK_INTERVAL = 30  # seconds
STALE_THRESHOLD = 300  # seconds - if status file older than this, assume dead
MAX_RESTARTS_PER_HOUR = 10
RESTART_COOLDOWN = 60  # seconds between restarts


class RepoDepotWatchdog:
    """24/7/365 Watchdog for Repo Depot - CRITICAL INFRASTRUCTURE"""

    def __init__(self):
        self.running = True
        self.repo_depot_process = None
        self.restart_times = []
        self.total_restarts = 0
        self.start_time = datetime.now()
        self.last_restart = None

        # Signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

        logger.info("=" * 60)
        logger.info("🔥 REPO DEPOT WATCHDOG INITIALIZED")
        logger.info("=" * 60)
        logger.info(f"   Script: {REPO_DEPOT_SCRIPT}")
        logger.info(f"   Python: {PYTHON_EXE}")
        logger.info(f"   Check Interval: {CHECK_INTERVAL}s")
        logger.info(f"   Stale Threshold: {STALE_THRESHOLD}s")
        logger.info("=" * 60)

    def _shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        logger.warning(f"🛑 Received signal {signum}, shutting down watchdog...")
        self.running = False
        self._save_status("SHUTDOWN")

    def _save_status(self, status: str):
        """Save watchdog status"""
        try:
            data = {
                "status": status,
                "start_time": self.start_time.isoformat(),
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                "total_restarts": self.total_restarts,
                "last_restart": self.last_restart.isoformat() if self.last_restart else None,
                "repo_depot_pid": self.repo_depot_process.pid if self.repo_depot_process else None,
                "last_check": datetime.now().isoformat()
            }
            with open(WATCHDOG_STATUS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save watchdog status: {e}")

    def _is_repo_depot_running(self) -> bool:
        """Check if Repo Depot is running and healthy"""
        # Method 1: Check our tracked process
        if self.repo_depot_process:
            if self.repo_depot_process.poll() is None:
                # Process is running, check if responsive
                return self._is_responsive()
            else:
                logger.warning(f"🔴 Tracked process {self.repo_depot_process.pid} has exited")
                self.repo_depot_process = None

        # Method 2: Check for any python process running repo depot
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    cmdline = proc.info.get('cmdline') or []
                    cmdline_str = ' '.join(cmdline).lower()
                    if 'optimus_repo_depot' in cmdline_str or 'repo_depot_launcher' in cmdline_str:
                        logger.info(f"🟢 Found existing Repo Depot process: PID {proc.pid}")
                        # Adopt this process
                        return self._is_responsive()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return False

    def _is_responsive(self) -> bool:
        """Check if Repo Depot is responsive (status file is recent)"""
        if not STATUS_FILE.exists():
            logger.warning("⚠️ Status file does not exist")
            return False

        try:
            mtime = datetime.fromtimestamp(STATUS_FILE.stat().st_mtime)
            age = (datetime.now() - mtime).total_seconds()

            if age > STALE_THRESHOLD:
                logger.warning(f"⚠️ Status file is stale ({age:.0f}s old, threshold: {STALE_THRESHOLD}s)")
                return False

            # Also check the actual status
            with open(STATUS_FILE, 'r') as f:
                status = json.load(f)

            if status.get('status') in ['ERROR', 'CRASHED', 'STOPPED']:
                logger.warning(f"⚠️ Repo Depot status indicates problem: {status.get('status')}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking status file: {e}")
            return False

    def _can_restart(self) -> bool:
        """Check if we can restart (rate limiting)"""
        # Remove restart times older than 1 hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        self.restart_times = [t for t in self.restart_times if t > one_hour_ago]

        if len(self.restart_times) >= MAX_RESTARTS_PER_HOUR:
            logger.error(f"🚨 TOO MANY RESTARTS ({len(self.restart_times)}/hour) - Manual intervention required!")
            return False

        # Check cooldown
        if self.last_restart:
            cooldown_remaining = RESTART_COOLDOWN - (datetime.now() - self.last_restart).total_seconds()
            if cooldown_remaining > 0:
                logger.info(f"⏳ Cooldown: {cooldown_remaining:.0f}s remaining")
                return False

        return True

    def _start_repo_depot(self) -> bool:
        """Start Repo Depot process"""
        if not self._can_restart():
            return False

        try:
            logger.info("🚀 STARTING REPO DEPOT...")

            # Kill any zombie processes first
            self._kill_stale_processes()

            # Start new process
            self.repo_depot_process = subprocess.Popen(
                [str(PYTHON_EXE), str(REPO_DEPOT_SCRIPT)],
                cwd=str(WORKSPACE),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )

            self.restart_times.append(datetime.now())
            self.last_restart = datetime.now()
            self.total_restarts += 1

            logger.info(f"✅ Repo Depot started with PID {self.repo_depot_process.pid}")
            logger.info(f"   Total restarts this session: {self.total_restarts}")

            # Wait a moment and verify it started
            time.sleep(5)
            if self.repo_depot_process.poll() is not None:
                logger.error(f"🔴 Repo Depot exited immediately with code {self.repo_depot_process.returncode}")
                self.repo_depot_process = None
                return False

            return True

        except Exception as e:
            logger.error(f"❌ Failed to start Repo Depot: {e}")
            return False

    def _kill_stale_processes(self):
        """Kill any stale Repo Depot processes"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    cmdline = proc.info.get('cmdline') or []
                    cmdline_str = ' '.join(cmdline).lower()
                    if 'optimus_repo_depot' in cmdline_str:
                        logger.warning(f"🔪 Killing stale process PID {proc.pid}")
                        proc.terminate()
                        proc.wait(timeout=5)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                continue

    def run(self):
        """Main watchdog loop - RUNS FOREVER"""
        logger.info("🔥 WATCHDOG LOOP STARTING - 24/7/365 OPERATION")

        while self.running:
            try:
                self._save_status("MONITORING")

                if self._is_repo_depot_running():
                    logger.debug("✅ Repo Depot is healthy")
                else:
                    logger.warning("🔴 REPO DEPOT DOWN - INITIATING RESTART")
                    if self._start_repo_depot():
                        logger.info("✅ Repo Depot restarted successfully")
                    else:
                        logger.error("❌ Failed to restart Repo Depot")

                # Sleep until next check
                time.sleep(CHECK_INTERVAL)

            except Exception as e:
                logger.error(f"❌ Watchdog error: {e}")
                time.sleep(10)  # Brief pause before continuing

        self._save_status("STOPPED")
        logger.info("🛑 Watchdog stopped")


def main():
    """Entry point"""
    print("=" * 60)
    print("  🔥 REPO DEPOT WATCHDOG - CRITICAL INFRASTRUCTURE")
    print("  24/7/365 FAILSAFE DAEMON")
    print("=" * 60)
    print()
    print("  This watchdog ensures Repo Depot NEVER goes down.")
    print("  Press Ctrl+C to stop (NOT RECOMMENDED)")
    print()
    print("=" * 60)

    watchdog = RepoDepotWatchdog()
    watchdog.run()


if __name__ == "__main__":
    main()
