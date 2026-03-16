#!/usr/bin/env python3
"""
DIGITAL LABOUR WATCHDOG SERVICE
Ultimate fail-safe for the fail-safe orchestrator itself
Ensures 24/7/365 operation even if the main orchestrator crashes
"""

import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import psutil


class WatchdogService:
    """Watchdog service that monitors and restarts the fail-safe orchestrator"""

    def __init__(self):
        self.name = "WATCHDOG SERVICE"
        self.version = "1.0"
        self.start_time = datetime.now()

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('watchdog_service.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(self.name)

        # Watchdog configuration
        self.workspace_dir = Path(__file__).parent
        self.orchestrator_script = self.workspace_dir / "fail_safe_orchestrator.py"
        self.check_interval = 30  # seconds
        self.restart_delay = 10  # seconds
        self.max_restarts_per_hour = 5
        self.max_memory_mb = 1024  # Restart if orchestrator uses >1GB RAM

        # Runtime state
        self.orchestrator_process: subprocess.Popen = None
        self.restart_times = []
        self.running = True

        # Graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, initiating watchdog shutdown...")
        self.running = False

    async def start_watchdog(self):
        """Start the watchdog service"""
        self.logger.info("🐕 Starting DIGITAL LABOUR WATCHDOG SERVICE v1.0")
        self.logger.info("🛡️ Protecting the fail-safe orchestrator with ultimate redundancy")

        try:
            # Initial orchestrator startup
            await self._start_orchestrator()

            # Main monitoring loop
            while self.running:
                try:
                    await self._check_orchestrator_health()
                    await asyncio.sleep(self.check_interval)

                except Exception as e:
                    self.logger.error(f"Watchdog monitoring error: {e}")
                    await asyncio.sleep(self.check_interval)

        except Exception as e:
            self.logger.critical(f"Critical watchdog error: {e}")
            await self._emergency_restart()
            raise

    async def _start_orchestrator(self):
        """Start the fail-safe orchestrator"""
        try:
            self.logger.info("🚀 Starting fail-safe orchestrator...")

            # Set environment variable to indicate watchdog protection
            env = os.environ.copy()
            env['WATCHDOG_PROTECTED'] = 'true'

            self.orchestrator_process = subprocess.Popen(
                [sys.executable, str(self.orchestrator_script)],
                cwd=str(self.workspace_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )

            self.logger.info(f"✅ Fail-safe orchestrator started (PID: {self.orchestrator_process.pid})")

        except Exception as e:
            self.logger.error(f"Failed to start orchestrator: {e}")
            raise

    async def _check_orchestrator_health(self):
        """Check if the orchestrator is still healthy"""
        try:
            if self.orchestrator_process is None:
                self.logger.warning("⚠️ Orchestrator process is None, restarting...")
                await self._restart_orchestrator()
                return

            # Check if process is still running
            if self.orchestrator_process.poll() is not None:
                exit_code = self.orchestrator_process.returncode
                self.logger.warning(f"⚠️ Orchestrator process ended with code {exit_code}, restarting...")
                await self._restart_orchestrator()
                return

            # Check resource usage
            try:
                proc = psutil.Process(self.orchestrator_process.pid)
                memory_mb = proc.memory_info().rss / 1024 / 1024

                if memory_mb > self.max_memory_mb:
                    self.logger.warning(f"⚠️ Orchestrator using {memory_mb:.1f}MB RAM (> {self.max_memory_mb}MB), restarting...")
                    await self._restart_orchestrator()
                    return

                # Check if process is responsive (basic check)
                cpu_percent = proc.cpu_percent()
                if cpu_percent > 95:  # Stuck at 100% CPU
                    self.logger.warning(f"⚠️ Orchestrator stuck at {cpu_percent}% CPU, restarting...")
                    await self._restart_orchestrator()
                    return

            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                self.logger.warning(f"⚠️ Cannot monitor orchestrator process: {e}, restarting...")
                await self._restart_orchestrator()
                return

            # Check for excessive restarts
            now = datetime.now()
            recent_restarts = [t for t in self.restart_times if now - t < timedelta(hours=1)]

            if len(recent_restarts) >= self.max_restarts_per_hour:
                self.logger.critical(f"🚨 Too many orchestrator restarts ({len(recent_restarts)}) in the last hour!")
                await self._send_critical_alert("WATCHDOG: Excessive orchestrator restarts detected")
                # Don't restart immediately, wait for manual intervention
                await asyncio.sleep(300)  # Wait 5 minutes
                return

        except Exception as e:
            self.logger.error(f"Error checking orchestrator health: {e}")
            await self._restart_orchestrator()

    async def _restart_orchestrator(self):
        """Restart the fail-safe orchestrator"""
        try:
            # Stop existing process if running
            if self.orchestrator_process and self.orchestrator_process.poll() is None:
                self.logger.info("🛑 Stopping existing orchestrator process...")
                try:
                    self.orchestrator_process.terminate()
                    self.orchestrator_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.logger.warning("Force killing orchestrator process...")
                    self.orchestrator_process.kill()
                    self.orchestrator_process.wait()

            # Wait before restart
            self.logger.info(f"⏳ Waiting {self.restart_delay} seconds before restart...")
            await asyncio.sleep(self.restart_delay)

            # Start new process
            await self._start_orchestrator()

            # Record restart time
            self.restart_times.append(datetime.now())

            # Clean old restart times (keep last 24 hours)
            cutoff = datetime.now() - timedelta(hours=24)
            self.restart_times = [t for t in self.restart_times if t > cutoff]

            self.logger.info(f"🔄 Orchestrator restarted (total restarts today: {len(self.restart_times)})")

        except Exception as e:
            self.logger.error(f"Failed to restart orchestrator: {e}")
            await self._send_critical_alert(f"WATCHDOG: Failed to restart orchestrator - {e}")

    async def _emergency_restart(self):
        """Emergency restart procedure when watchdog itself is failing"""
        try:
            self.logger.critical("🚨 WATCHDOG EMERGENCY RESTART PROCEDURE")

            # Try to start orchestrator directly
            env = os.environ.copy()
            env['EMERGENCY_MODE'] = 'true'

            emergency_process = subprocess.Popen(
                [sys.executable, str(self.orchestrator_script)],
                cwd=str(self.workspace_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            self.logger.critical(f"🚨 Emergency orchestrator started (PID: {emergency_process.pid})")

            # Send critical alert
            await self._send_critical_alert("WATCHDOG: Emergency restart procedure activated")

        except Exception as e:
            self.logger.critical(f"🚨 EMERGENCY RESTART FAILED: {e}")
            # At this point, manual intervention is required

    async def _send_critical_alert(self, message: str):
        """Send critical alert"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Log critical alert
            self.logger.critical(f"🚨 CRITICAL ALERT: {message}")

            # Write to critical alerts log
            alert_entry = {
                "timestamp": timestamp,
                "service": "watchdog",
                "level": "critical",
                "message": message
            }

            with open(self.workspace_dir / "critical_alerts.log", 'a') as f:
                import json
                json.dump(alert_entry, f)
                f.write('\n')

            # Here you could add:
            # - Email alerts
            # - SMS notifications
            # - External monitoring service integration
            # - Auto-ticketing system

        except Exception as e:
            self.logger.error(f"Failed to send critical alert: {e}")

    def get_watchdog_status(self) -> dict:
        """Get watchdog status"""
        return {
            "service": self.name,
            "version": self.version,
            "uptime": str(datetime.now() - self.start_time),
            "orchestrator_pid": self.orchestrator_process.pid if self.orchestrator_process else None,
            "orchestrator_running": self.orchestrator_process.poll() is None if self.orchestrator_process else False,
            "restarts_last_hour": len([t for t in self.restart_times if datetime.now() - t < timedelta(hours=1)]),
            "restarts_last_24h": len(self.restart_times),
            "status": "active"
        }

async def main():
    """Main entry point"""
    watchdog = WatchdogService()

    try:
        await watchdog.start_watchdog()
    except KeyboardInterrupt:
        watchdog.logger.info("Received keyboard interrupt, shutting down watchdog...")
    except Exception as e:
        watchdog.logger.critical(f"Critical watchdog failure: {e}")
    finally:
        # Final cleanup
        if watchdog.orchestrator_process and watchdog.orchestrator_process.poll() is None:
            try:
                watchdog.orchestrator_process.terminate()
                watchdog.orchestrator_process.wait(timeout=5)
            except Exception:
                watchdog.orchestrator_process.kill()

if __name__ == "__main__":
    # Ensure proper permissions
    if os.name == 'nt':  # Windows
        try:
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                print("⚠️ WARNING: Watchdog not running as administrator. Limited restart capabilities.")
        except Exception:
            pass

    asyncio.run(main())
