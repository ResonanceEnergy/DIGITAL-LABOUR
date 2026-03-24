#!/usr/bin/env python3
"""
Super Agency Background Daemon
A robust, always-running background service that manages all Super Agency operations.

Modern Best Practices Applied:
- Watchdog pattern for self-healing
- Structured logging with rotation
- Health checks with auto-recovery
- Graceful shutdown handling
- Resource-efficient scheduling

Can be installed as a Windows Service using NSSM or run directly.
"""

import os
import sys
import time
import json
import signal
import logging
import psutil
import threading
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, Optional

# Configuration
CONFIG = {
    "intervals": {
        "refresh": 300,           # 5 minutes - main refresh cycle
        "health_check": 60,       # 1 minute - quick health check
        "deep_health": 600,       # 10 minutes - comprehensive health check
        "backlog": 300,           # 5 minutes - backlog management
        "doctrine": 3600,         # 1 hour - memory doctrine
        "git_sync": 300,          # 5 minutes - git sync (was 2x 5min tasks)
    },
    "health_thresholds": {
        "cpu_warning": 80,
        "cpu_critical": 95,
        "memory_warning": 80,
        "memory_critical": 95,
        "disk_warning": 85,
        "disk_critical": 95,
    },
    "logging": {
        "max_bytes": 10 * 1024 * 1024,  # 10 MB
        "backup_count": 5,
    },
    "watchdog": {
        "stale_threshold": 600,   # 10 minutes without heartbeat = stale
        "max_restarts": 3,        # Max auto-restarts per hour
    }
}


class SuperAgencyDaemon:
    """Main daemon class with watchdog and health monitoring."""

    def __init__(self):
        self.base_path = Path(__file__).parent
        self.log_path = self.base_path / "logs"
        self.log_path.mkdir(exist_ok=True)

        # Setup logging
        self.logger = self._setup_logging()

        # State tracking
        self.running = True
        self.last_heartbeat = datetime.now()
        self.task_timers: Dict[str, datetime] = {}
        self.error_counts: Dict[str, int] = {}
        self.restart_times: list = []

        # Health status
        self.health_status = {
            "status": "starting",
            "last_check": None,
            "issues": [],
            "metrics": {}
        }

        # Initialize task timers
        for task in CONFIG["intervals"]:
            self.task_timers[task] = datetime.min

        # Signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)

        self.logger.info("Super Agency Daemon initialized")

    def _setup_logging(self) -> logging.Logger:
        """Setup structured logging with rotation."""
        logger = logging.getLogger("SuperAgencyDaemon")
        logger.setLevel(logging.INFO)

        # Console handler
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(console)

        # Rotating file handler
        log_file = self.log_path / "daemon.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=CONFIG["logging"]["max_bytes"],
            backupCount=CONFIG["logging"]["backup_count"]
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
        ))
        logger.addHandler(file_handler)

        return logger

    def _shutdown_handler(self, signum, frame):
        """Handle graceful shutdown."""
        self.logger.info(f"Shutdown signal received ({signum})")
        self.running = False

    def _should_run_task(self, task_name: str) -> bool:
        """Check if a task should run based on its interval."""
        interval = CONFIG["intervals"].get(task_name, 300)
        last_run = self.task_timers.get(task_name, datetime.min)
        return (datetime.now() - last_run).total_seconds() >= interval

    def _mark_task_complete(self, task_name: str):
        """Mark a task as completed."""
        self.task_timers[task_name] = datetime.now()

    def _run_script(self, script: str, args: list = None) -> bool:
        """Run a Python or PowerShell script safely."""
        script_path = self.base_path / script
        if not script_path.exists():
            self.logger.warning(f"Script not found: {script}")
            return False

        try:
            if script.endswith('.py'):
                cmd = [sys.executable, str(script_path)]
            elif script.endswith('.ps1'):
                cmd = ['powershell.exe', '-ExecutionPolicy', 'Bypass', '-File', str(script_path)]
            else:
                self.logger.error(f"Unknown script type: {script}")
                return False

            if args:
                cmd.extend(args)

            result = subprocess.run(
                cmd,
                cwd=str(self.base_path),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                self.logger.debug(f"Script completed: {script}")
                return True
            else:
                self.logger.warning(f"Script failed ({script}): {result.stderr[:200]}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"Script timeout: {script}")
            return False
        except Exception as e:
            self.logger.error(f"Script error ({script}): {e}")
            return False

    def collect_health_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive system health metrics."""
        try:
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": psutil.cpu_percent(interval=0.5),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage(str(self.base_path)).percent,
                "process_count": len(psutil.pids()),
                "daemon_memory_mb": psutil.Process().memory_info().rss / (1024 * 1024),
                "daemon_cpu_percent": psutil.Process().cpu_percent()
            }

            # Check for Super Agency processes
            sa_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'super' in cmdline.lower() or 'matrix' in cmdline.lower():
                        sa_processes.append({
                            "pid": proc.info['pid'],
                            "name": proc.info['name']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            metrics["super_agency_processes"] = len(sa_processes)

            return metrics

        except Exception as e:
            self.logger.error(f"Health metrics error: {e}")
            return {"error": str(e)}

    def check_health(self, deep: bool = False) -> Dict[str, Any]:
        """Perform health check with optional deep inspection."""
        issues = []
        metrics = self.collect_health_metrics()

        # CPU check
        cpu = metrics.get("cpu_percent", 0)
        if cpu >= CONFIG["health_thresholds"]["cpu_critical"]:
            issues.append(f"CRITICAL: CPU at {cpu}%")
        elif cpu >= CONFIG["health_thresholds"]["cpu_warning"]:
            issues.append(f"WARNING: CPU at {cpu}%")

        # Memory check
        mem = metrics.get("memory_percent", 0)
        if mem >= CONFIG["health_thresholds"]["memory_critical"]:
            issues.append(f"CRITICAL: Memory at {mem}%")
        elif mem >= CONFIG["health_thresholds"]["memory_warning"]:
            issues.append(f"WARNING: Memory at {mem}%")

        # Disk check
        disk = metrics.get("disk_percent", 0)
        if disk >= CONFIG["health_thresholds"]["disk_critical"]:
            issues.append(f"CRITICAL: Disk at {disk}%")
        elif disk >= CONFIG["health_thresholds"]["disk_warning"]:
            issues.append(f"WARNING: Disk at {disk}%")

        if deep:
            # Deep checks - verify critical services
            self.logger.info("Running deep health check...")

            # Check Matrix Monitor
            matrix_running = any(
                'matrix' in ' '.join(p.cmdline()).lower()
                for p in psutil.process_iter(['cmdline'])
                if p.cmdline()
            )
            if not matrix_running:
                issues.append("Matrix Monitor not running")
                # Auto-recovery: restart Matrix Monitor
                self._auto_recover_service("flask_matrix_monitor.py", "Matrix Monitor")

            # Check for stale PID files
            for pid_file in self.base_path.glob("*.pid"):
                try:
                    pid = int(pid_file.read_text().strip())
                    if not psutil.pid_exists(pid):
                        issues.append(f"Stale PID file: {pid_file.name}")
                        pid_file.unlink()  # Clean up
                except:
                    pass

        # Update health status
        self.health_status = {
            "status": "healthy" if not issues else ("warning" if "WARNING" in str(issues) else "critical"),
            "last_check": datetime.now().isoformat(),
            "issues": issues,
            "metrics": metrics
        }

        # Write health status to file
        health_file = self.base_path / "daemon_health.json"
        with open(health_file, 'w') as f:
            json.dump(self.health_status, f, indent=2)

        return self.health_status

    def _auto_recover_service(self, script: str, service_name: str):
        """Attempt to auto-recover a failed service."""
        # Check restart limits
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        self.restart_times = [t for t in self.restart_times if t > hour_ago]

        if len(self.restart_times) >= CONFIG["watchdog"]["max_restarts"]:
            self.logger.warning(f"Max restarts reached for {service_name} - skipping")
            return

        self.logger.info(f"Auto-recovering: {service_name}")
        self.restart_times.append(now)

        # Start the service
        script_path = self.base_path / script
        if script_path.exists():
            try:
                subprocess.Popen(
                    [sys.executable, str(script_path)],
                    cwd=str(self.base_path),
                    start_new_session=True
                )
                self.logger.info(f"Restarted: {service_name}")
            except Exception as e:
                self.logger.error(f"Failed to restart {service_name}: {e}")

    def task_refresh(self):
        """Combined 5-minute refresh task (consolidates duplicate tasks)."""
        self.logger.info("Running refresh cycle...")

        # Cross-platform refresh
        self._run_script("cross_platform_refresh.py")

        # Memory/doctrine backup (from refresh_5min.ps1)
        self._run_script("backup_memory_doctrine_logs.ps1")

        # Backlog management
        self._run_script("backlog_management_system.py")

    def task_git_sync(self):
        """Git synchronization task."""
        self.logger.info("Running git sync...")
        try:
            # Pull latest
            result = subprocess.run(
                ['git', 'pull'],
                cwd=str(self.base_path),
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                self.logger.debug("Git sync completed")
            else:
                self.logger.warning(f"Git sync issue: {result.stderr[:100]}")

        except Exception as e:
            self.logger.error(f"Git sync error: {e}")

    def task_doctrine(self):
        """Memory doctrine maintenance."""
        self.logger.info("Running doctrine maintenance...")
        self._run_script("memory_doctrine_system.py")

    def heartbeat(self):
        """Update heartbeat timestamp."""
        self.last_heartbeat = datetime.now()
        heartbeat_file = self.base_path / "daemon_heartbeat.txt"
        heartbeat_file.write_text(self.last_heartbeat.isoformat())

    def run(self):
        """Main daemon loop."""
        self.logger.info("=" * 60)
        self.logger.info("SUPER AGENCY DAEMON STARTED")
        self.logger.info(f"PID: {os.getpid()}")
        self.logger.info(f"Base Path: {self.base_path}")
        self.logger.info("=" * 60)

        # Write PID file
        pid_file = self.base_path / "daemon.pid"
        pid_file.write_text(str(os.getpid()))

        # Initial health check
        self.check_health(deep=True)

        try:
            while self.running:
                cycle_start = time.time()

                # Heartbeat
                self.heartbeat()

                # Quick health check (every minute)
                if self._should_run_task("health_check"):
                    self.check_health(deep=False)
                    self._mark_task_complete("health_check")

                # Deep health check (every 10 minutes)
                if self._should_run_task("deep_health"):
                    health = self.check_health(deep=True)
                    if health["issues"]:
                        self.logger.warning(f"Health issues: {health['issues']}")
                    self._mark_task_complete("deep_health")

                # 5-minute refresh (consolidated from 2 tasks)
                if self._should_run_task("refresh"):
                    self.task_refresh()
                    self._mark_task_complete("refresh")

                # Git sync
                if self._should_run_task("git_sync"):
                    self.task_git_sync()
                    self._mark_task_complete("git_sync")

                # Doctrine maintenance (hourly)
                if self._should_run_task("doctrine"):
                    self.task_doctrine()
                    self._mark_task_complete("doctrine")

                # Sleep until next check (10 second intervals)
                elapsed = time.time() - cycle_start
                sleep_time = max(0, 10 - elapsed)
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        except Exception as e:
            self.logger.error(f"Daemon error: {e}")
            raise
        finally:
            self.logger.info("Daemon shutting down...")
            pid_file.unlink(missing_ok=True)
            self.logger.info("SUPER AGENCY DAEMON STOPPED")


def main():
    """Entry point."""
    daemon = SuperAgencyDaemon()
    daemon.run()


if __name__ == "__main__":
    main()
