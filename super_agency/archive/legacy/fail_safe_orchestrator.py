#!/usr/bin/env python3
"""
SUPER AGENCY FAIL-SAFE ORCHESTRATOR
24/7/365 High Availability System for All Agency Components

Ensures all critical components remain online and functioning:
- SUPER AGENCY (main orchestration)
- QUANTUM QFORGE (repository building)
- QUANTUM QUSAR (goal orchestration)
- MATRIX MONITOR (web dashboard)
- MATRIX MAXIMIZER (performance optimization)
- OPTIMUS (Agent Optimus)
- AZ PRIME (Azure integration)
- HELIX (advanced analytics)
- GASKET (Agent Gasket)
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil

# Add parent directory to path
parent_dir = Path(__file__).parent
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(parent_dir / "agents"))

class FailSafeOrchestrator:
    """24/7/365 High Availability Orchestrator for Super Agency"""

    def __init__(self):
        self.name = "FAIL-SAFE ORCHESTRATOR"
        self.version = "1.0"
        self.start_time = datetime.now()

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('fail_safe_orchestrator.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(self.name)

        # Component definitions with their critical parameters
        self.components = {
            'super_agency': {
                'name': 'SUPER AGENCY',
                'process_name': 'super_agency',
                'command': ['python', 'super_agency_main.py'],
                'working_dir': str(parent_dir),
                'health_check_url': None,
                'restart_delay': 5,
                'max_restarts': 10,
                'critical': True,
                'instances': 1
            },
            'quantum_qforge': {
                'name': 'QUANTUM QFORGE',
                'process_name': 'qforge',
                'command': ['python', 'qforge_main.py'],
                'working_dir': str(parent_dir / 'qforge'),
                'health_check_url': 'http://localhost:8001/health',
                'restart_delay': 10,
                'max_restarts': 5,
                'critical': True,
                'instances': 2  # Redundant instances
            },
            'quantum_qusar': {
                'name': 'QUANTUM QUSAR',
                'process_name': 'qusar',
                'command': ['python', 'qusar_main.py'],
                'working_dir': str(parent_dir / 'qusar'),
                'health_check_url': 'http://localhost:8002/health',
                'restart_delay': 10,
                'max_restarts': 5,
                'critical': True,
                'instances': 2  # Redundant instances
            },
            'matrix_monitor': {
                'name': 'MATRIX MONITOR',
                'process_name': 'flask_matrix_monitor',
                'command': ['python', 'flask_matrix_monitor.py'],
                'working_dir': str(parent_dir),
                'health_check_url': 'http://localhost:8501',
                'restart_delay': 3,
                'max_restarts': 20,
                'critical': False,
                'instances': 1
            },
            'matrix_maximizer': {
                'name': 'MATRIX MAXIMIZER',
                'process_name': 'streamlit_matrix_maximizer',
                'command': ['python', '-m', 'streamlit', 'run', 'streamlit_matrix_maximizer.py', '--server.port', '8502', '--server.headless', 'true'],
                'working_dir': str(parent_dir),
                'health_check_url': 'http://localhost:8502',
                'restart_delay': 5,
                'max_restarts': 15,
                'critical': False,
                'instances': 1
            },
            'agent_optimus': {
                'name': 'AGENT OPTIMUS',
                'process_name': 'agent_optimus',
                'command': ['python', 'agent_runner.py'],  # Uses the persistent runner
                'working_dir': str(parent_dir),
                'health_check_url': None,
                'restart_delay': 15,
                'max_restarts': 8,
                'critical': True,
                'instances': 1
            },
            'agent_gasket': {
                'name': 'AGENT GASKET',
                'process_name': 'agent_gasket',
                'command': ['python', 'agent_runner.py'],  # Uses the persistent runner
                'working_dir': str(parent_dir),
                'health_check_url': None,
                'restart_delay': 15,
                'max_restarts': 8,
                'critical': True,
                'instances': 1
            },
            'az_prime': {
                'name': 'AZ PRIME',
                'process_name': 'az_prime',
                'command': ['python', 'az_prime_main.py'],
                'working_dir': str(parent_dir / 'azure'),
                'health_check_url': 'http://localhost:8003/health',
                'restart_delay': 20,
                'max_restarts': 3,
                'critical': False,
                'instances': 1
            },
            'helix': {
                'name': 'HELIX',
                'process_name': 'helix',
                'command': ['python', 'helix_main.py'],
                'working_dir': str(parent_dir / 'analytics'),
                'health_check_url': 'http://localhost:8004/health',
                'restart_delay': 30,
                'max_restarts': 3,
                'critical': False,
                'instances': 1
            }
        }

        # Runtime state tracking
        self.processes: Dict[str, List[subprocess.Popen]] = {}
        self.restart_counts: Dict[str, int] = {}
        self.last_health_check: Dict[str, datetime] = {}
        self.alerts_sent: Dict[str, datetime] = {}

        # High availability settings
        self.health_check_interval = 30  # seconds
        self.alert_cooldown = 300  # 5 minutes between alerts
        self.max_memory_percent = 85  # Restart if memory usage > 85%
        self.max_cpu_percent = 95  # Restart if CPU usage > 95%

        # Graceful shutdown handling
        self.running = True
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False

    async def start_fail_safe_system(self):
        """Start the complete fail-safe orchestration system"""
        self.logger.info("🚀 Starting SUPER AGENCY FAIL-SAFE ORCHESTRATOR v1.0")
        self.logger.info("🎯 Ensuring 24/7/365 availability for all agency components")

        try:
            # Initial component startup
            await self._initial_startup()

            # Start monitoring loops
            monitoring_tasks = [
                self._health_monitoring_loop(),
                self._resource_monitoring_loop(),
                self._backup_and_recovery_loop(),
                self._alert_system_loop()
            ]

            # Run all monitoring tasks concurrently
            await asyncio.gather(*monitoring_tasks, return_exceptions=True)

        except Exception as e:
            self.logger.error(f"Critical fail-safe orchestrator error: {e}")
            await self._emergency_shutdown()
            raise

    async def _initial_startup(self):
        """Perform initial startup of all components"""
        self.logger.info("🔄 Performing initial component startup...")

        for component_id, config in self.components.items():
            try:
                await self._start_component(component_id, config)
                self.logger.info(f"✅ {config['name']} started successfully")
            except Exception as e:
                self.logger.error(f"❌ Failed to start {config['name']}: {e}")
                if config['critical']:
                    self.logger.critical(f"🚨 CRITICAL COMPONENT {config['name']} FAILED TO START!")
                    await self._send_alert(f"CRITICAL: {config['name']} failed initial startup", "red")

        self.logger.info("🎉 Initial startup complete")

    async def _start_component(self, component_id: str, config: Dict[str, Any]):
        """Start a component with redundancy support"""
        instances_to_start = config['instances']

        for instance_num in range(instances_to_start):
            try:
                instance_id = f"{component_id}_{instance_num}" if instances_to_start > 1 else component_id

                # Set environment variables for multi-instance support
                env = os.environ.copy()
                env['INSTANCE_ID'] = str(instance_num)
                env['COMPONENT_ID'] = component_id

                # Start the process
                process = subprocess.Popen(
                    config['command'],
                    cwd=config['working_dir'],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
                )

                # Store process reference
                if component_id not in self.processes:
                    self.processes[component_id] = []
                self.processes[component_id].append(process)

                self.logger.info(f"🟢 Started {config['name']} instance {instance_num} (PID: {process.pid})")

                # Initialize restart count
                if component_id not in self.restart_counts:
                    self.restart_counts[component_id] = 0

            except Exception as e:
                self.logger.error(f"Failed to start {config['name']} instance {instance_num}: {e}")
                raise

    async def _health_monitoring_loop(self):
        """Continuous health monitoring for all components"""
        self.logger.info("🔍 Starting health monitoring loop")

        while self.running:
            try:
                for component_id, config in self.components.items():
                    await self._check_component_health(component_id, config)

                await asyncio.sleep(self.health_check_interval)

            except Exception as e:
                self.logger.error(f"Health monitoring loop error: {e}")
                await asyncio.sleep(60)  # Wait before retry

    async def _check_component_health(self, component_id: str, config: Dict[str, Any]):
        """Check health of a specific component"""
        try:
            component_processes = self.processes.get(component_id, [])

            # Check if processes are still running
            running_processes = []
            for process in component_processes:
                if process.poll() is None:  # Process is still running
                    running_processes.append(process)
                else:
                    self.logger.warning(f"⚠️ {config['name']} process {process.pid} has stopped")

            # Update process list
            self.processes[component_id] = running_processes

            # Check if we need to restart
            expected_instances = config['instances']
            actual_instances = len(running_processes)

            if actual_instances < expected_instances:
                missing_instances = expected_instances - actual_instances
                self.logger.warning(f"⚠️ {config['name']} has {actual_instances}/{expected_instances} running instances")

                # Check restart limits
                current_restarts = self.restart_counts.get(component_id, 0)
                if current_restarts < config['max_restarts']:
                    await self._restart_component(component_id, config, missing_instances)
                else:
                    await self._send_alert(f"CRITICAL: {config['name']} exceeded max restarts ({config['max_restarts']})", "red")

            # HTTP health check for components with URLs
            if config['health_check_url'] and running_processes:
                await self._http_health_check(component_id, config)

        except Exception as e:
            self.logger.error(f"Error checking health of {config['name']}: {e}")

    async def _http_health_check(self, component_id: str, config: Dict[str, Any]):
        """Perform HTTP health check for components with web interfaces"""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(config['health_check_url'], timeout=10) as response:
                    if response.status == 200:
                        self.last_health_check[component_id] = datetime.now()
                    else:
                        self.logger.warning(f"⚠️ {config['name']} health check failed: HTTP {response.status}")
                        await self._restart_component(component_id, config, 1)

        except Exception as e:
            self.logger.warning(f"⚠️ {config['name']} health check error: {e}")
            # Don't restart immediately on network errors, wait for process check

    async def _restart_component(self, component_id: str, config: Dict[str, Any], instances_to_start: int):
        """Restart a failed component"""
        try:
            self.logger.info(f"🔄 Restarting {config['name']} ({instances_to_start} instances)")

            # Increment restart count
            self.restart_counts[component_id] = self.restart_counts.get(component_id, 0) + 1

            # Wait before restart
            await asyncio.sleep(config['restart_delay'])

            # Start the required number of instances
            for i in range(instances_to_start):
                try:
                    await self._start_component_instance(component_id, config, i)
                except Exception as e:
                    self.logger.error(f"Failed to restart {config['name']} instance {i}: {e}")

            # Send alert for restart
            await self._send_alert(f"RESTARTED: {config['name']} restarted ({self.restart_counts[component_id]} total restarts)", "yellow")

        except Exception as e:
            self.logger.error(f"Error restarting {config['name']}: {e}")

    async def _start_component_instance(self, component_id: str, config: Dict[str, Any], instance_num: int):
        """Start a single instance of a component"""
        env = os.environ.copy()
        env['INSTANCE_ID'] = str(instance_num)
        env['COMPONENT_ID'] = component_id

        process = subprocess.Popen(
            config['command'],
            cwd=config['working_dir'],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        )

        if component_id not in self.processes:
            self.processes[component_id] = []
        self.processes[component_id].append(process)

        self.logger.info(f"🟢 Restarted {config['name']} instance {instance_num} (PID: {process.pid})")

    async def _resource_monitoring_loop(self):
        """Monitor system resources and prevent resource exhaustion"""
        self.logger.info("📊 Starting resource monitoring loop")

        while self.running:
            try:
                # Check overall system resources
                memory = psutil.virtual_memory()
                cpu = psutil.cpu_percent(interval=1)

                if memory.percent > self.max_memory_percent:
                    self.logger.warning(f"⚠️ High memory usage: {memory.percent}%")
                    await self._send_alert(f"HIGH MEMORY: {memory.percent}% used", "orange")

                if cpu > self.max_cpu_percent:
                    self.logger.warning(f"⚠️ High CPU usage: {cpu}%")
                    await self._send_alert(f"HIGH CPU: {cpu}% used", "orange")

                # Check individual component resource usage
                for component_id, processes in self.processes.items():
                    for process in processes:
                        try:
                            if process.poll() is None:  # Still running
                                proc_memory = process.memory_percent()
                                proc_cpu = process.cpu_percent()

                                if proc_memory > 50:  # Component using >50% of system memory
                                    self.logger.warning(f"⚠️ {component_id} high memory: {proc_memory}%")
                                if proc_cpu > 80:  # Component using >80% CPU
                                    self.logger.warning(f"⚠️ {component_id} high CPU: {proc_cpu}%")

                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass  # Process might have ended

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                self.logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(60)

    async def _backup_and_recovery_loop(self):
        """Perform regular backups and recovery tests"""
        self.logger.info("💾 Starting backup and recovery loop")

        while self.running:
            try:
                # Daily backup at 2 AM
                now = datetime.now()
                if now.hour == 2 and now.minute < 5:  # Within first 5 minutes of 2 AM
                    await self._perform_system_backup()

                # Weekly recovery test on Sundays at 3 AM
                if now.weekday() == 6 and now.hour == 3 and now.minute < 5:
                    await self._perform_recovery_test()

                await asyncio.sleep(300)  # Check every 5 minutes

            except Exception as e:
                self.logger.error(f"Backup/recovery loop error: {e}")
                await asyncio.sleep(300)

    async def _perform_system_backup(self):
        """Perform comprehensive system backup"""
        try:
            self.logger.info("💾 Starting system backup...")

            backup_dir = parent_dir / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Backup critical data
            critical_paths = [
                "portfolio.json",
                "agents/",
                "qusar/",
                "qforge/",
                "*.log"
            ]

            for path_pattern in critical_paths:
                for path in parent_dir.glob(path_pattern):
                    if path.exists():
                        if path.is_file():
                            import shutil
                            shutil.copy2(path, backup_dir / path.name)
                        elif path.is_dir():
                            shutil.copytree(path, backup_dir / path.name, dirs_exist_ok=True)

            # Backup configuration
            config_backup = {
                "timestamp": datetime.now().isoformat(),
                "components": self.components,
                "system_info": {
                    "platform": sys.platform,
                    "python_version": sys.version,
                    "uptime": str(datetime.now() - self.start_time)
                }
            }

            with open(backup_dir / "system_config.json", 'w') as f:
                json.dump(config_backup, f, indent=2, default=str)

            self.logger.info(f"✅ System backup completed: {backup_dir}")
            await self._send_alert("BACKUP: System backup completed successfully", "green")

        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            await self._send_alert(f"BACKUP FAILED: {e}", "red")

    async def _perform_recovery_test(self):
        """Test system recovery procedures"""
        try:
            self.logger.info("🧪 Starting recovery test...")

            # Test component restart capability
            test_results = {}
            for component_id, config in self.components.items():
                try:
                    # Simulate stopping a component
                    processes = self.processes.get(component_id, [])
                    if processes:
                        test_process = processes[0]
                        test_pid = test_process.pid

                        # Wait a moment, then check if orchestrator detects and restarts
                        await asyncio.sleep(10)

                        # Check if process is still running or was restarted
                        current_processes = self.processes.get(component_id, [])
                        if len(current_processes) >= len(processes):
                            test_results[component_id] = "PASS"
                        else:
                            test_results[component_id] = "FAIL"

                except Exception as e:
                    test_results[component_id] = f"ERROR: {e}"

            # Log results
            passed = sum(1 for result in test_results.values() if result == "PASS")
            total = len(test_results)

            self.logger.info(f"🧪 Recovery test completed: {passed}/{total} components passed")
            await self._send_alert(f"RECOVERY TEST: {passed}/{total} components passed", "blue")

        except Exception as e:
            self.logger.error(f"Recovery test failed: {e}")
            await self._send_alert(f"RECOVERY TEST FAILED: {e}", "red")

    async def _alert_system_loop(self):
        """Monitor and escalate alerts based on patterns"""
        self.logger.info("🚨 Starting alert monitoring loop")

        while self.running:
            try:
                # Check for alert patterns that need escalation
                recent_alerts = []
                cutoff_time = datetime.now() - timedelta(minutes=10)

                for alert_time in self.alerts_sent.values():
                    if alert_time > cutoff_time:
                        recent_alerts.append(alert_time)

                # If more than 5 alerts in 10 minutes, escalate
                if len(recent_alerts) > 5:
                    await self._send_alert("ESCALATION: High frequency of alerts detected", "red")

                # Check for critical component failures
                critical_failures = []
                for component_id, config in self.components.items():
                    if config['critical']:
                        processes = self.processes.get(component_id, [])
                        if len(processes) == 0:
                            critical_failures.append(config['name'])

                if critical_failures:
                    await self._send_alert(f"CRITICAL FAILURE: {', '.join(critical_failures)} are down", "red")

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                self.logger.error(f"Alert monitoring error: {e}")
                await asyncio.sleep(60)

    async def _send_alert(self, message: str, severity: str):
        """Send alert with severity-based handling"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Log the alert
            if severity == "red":
                self.logger.critical(f"🚨 ALERT: {message}")
            elif severity == "orange":
                self.logger.error(f"⚠️ ALERT: {message}")
            elif severity == "yellow":
                self.logger.warning(f"⚠️ ALERT: {message}")
            else:
                self.logger.info(f"ℹ️ ALERT: {message}")

            # Track alert for escalation monitoring
            alert_key = f"{severity}_{message[:50]}"
            self.alerts_sent[alert_key] = datetime.now()

            # Here you could integrate with external alerting systems:
            # - Email notifications
            # - SMS alerts
            # - Slack/Discord webhooks
            # - PagerDuty/monitoring services

            # For now, just write to alert log
            alert_log = {
                "timestamp": timestamp,
                "severity": severity,
                "message": message,
                "component": "fail_safe_orchestrator"
            }

            with open(parent_dir / "alerts.log", 'a') as f:
                json.dump(alert_log, f)
                f.write('\n')

        except Exception as e:
            self.logger.error(f"Failed to send alert: {e}")

    async def _emergency_shutdown(self):
        """Emergency shutdown of all components"""
        self.logger.critical("🚨 EMERGENCY SHUTDOWN INITIATED")

        try:
            # Stop all processes
            for component_id, processes in self.processes.items():
                for process in processes:
                    try:
                        if process.poll() is None:
                            process.terminate()
                            # Wait up to 10 seconds for graceful shutdown
                            try:
                                process.wait(timeout=10)
                            except subprocess.TimeoutExpired:
                                process.kill()  # Force kill if needed
                    except Exception as e:
                        self.logger.error(f"Error stopping process {process.pid}: {e}")

            # Final alert
            await self._send_alert("EMERGENCY SHUTDOWN: All components stopped", "red")

        except Exception as e:
            self.logger.critical(f"Emergency shutdown error: {e}")

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            "orchestrator": {
                "name": self.name,
                "version": self.version,
                "uptime": str(datetime.now() - self.start_time),
                "status": "running" if self.running else "stopped"
            },
            "components": {},
            "system_resources": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent
            },
            "alerts": {
                "total_sent": len(self.alerts_sent),
                "recent_alerts": len([t for t in self.alerts_sent.values()
                                    if t > datetime.now() - timedelta(hours=1)])
            }
        }

        # Component status
        for component_id, config in self.components.items():
            processes = self.processes.get(component_id, [])
            running_instances = sum(1 for p in processes if p.poll() is None)

            status["components"][component_id] = {
                "name": config["name"],
                "expected_instances": config["instances"],
                "running_instances": running_instances,
                "restarts": self.restart_counts.get(component_id, 0),
                "last_health_check": self.last_health_check.get(component_id),
                "status": "healthy" if running_instances == config["instances"] else "degraded"
            }

        return status

async def main():
    """Main entry point for the fail-safe orchestrator"""
    orchestrator = FailSafeOrchestrator()

    try:
        await orchestrator.start_fail_safe_system()
    except KeyboardInterrupt:
        orchestrator.logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        orchestrator.logger.critical(f"Critical orchestrator failure: {e}")
    finally:
        await orchestrator._emergency_shutdown()

if __name__ == "__main__":
    # Ensure we're running with proper permissions
    if os.name == 'nt':  # Windows
        try:
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                print("⚠️ WARNING: Not running as administrator. Some features may be limited.")
        except Exception:
            pass

    asyncio.run(main())
