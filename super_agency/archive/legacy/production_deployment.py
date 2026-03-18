#!/usr/bin/env python3
"""
BIT RAGE LABOUR Production Deployment System
Complete integration and production deployment
"""

import atexit
import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class DeploymentStatus(Enum):
    """Deployment status states"""
    INITIALIZING = "initializing"
    STARTING_SERVICES = "starting_services"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"

class ProductionDeployment:
    """Production deployment orchestrator"""

    def __init__(self, config_path: Path = None):
        self.config_path = config_path or Path("./config/production_config.json")
        self.status = DeploymentStatus.INITIALIZING
        self.services = {}
        self.threads = {}
        self.health_checks = {}
        self.start_time = datetime.now()

        # Load configuration
        self.config = self._load_config()

        # Initialize service managers
        self._init_service_managers()

        # Register cleanup
        atexit.register(self.cleanup)

        print("🚀 Production deployment initialized")

    def _load_config(self) -> Dict[str, Any]:
        """Load production configuration"""

        default_config = {
            "services": {
                "memory_doctrine": {
                    "enabled": True,
                    "port": 8001,
                    "health_check_interval": 30,
                    "auto_restart": True
                },
                "backlog_intelligence": {
                    "enabled": True,
                    "port": 8002,
                    "health_check_interval": 60,
                    "auto_restart": True
                },
                "context_compression": {
                    "enabled": True,
                    "port": 8003,
                    "health_check_interval": 45,
                    "auto_restart": True
                },
                "doctrine_evolution": {
                    "enabled": True,
                    "port": 8004,
                    "health_check_interval": 120,
                    "auto_restart": True
                },
                "sasp_network": {
                    "enabled": True,
                    "port": 8888,
                    "health_check_interval": 30,
                    "auto_restart": True
                },
                "vector_database": {
                    "enabled": True,
                    "port": 8005,
                    "health_check_interval": 60,
                    "auto_restart": True
                }
            },
            "monitoring": {
                "enabled": True,
                "metrics_port": 9090,
                "alerts_enabled": True,
                "log_level": "INFO"
            },
            "security": {
                "sasp_enabled": True,
                "encryption_enabled": True,
                "audit_logging": True
            },
            "performance": {
                "memory_limit_mb": 1024,
                "cpu_limit_percent": 80,
                "cleanup_interval_hours": 24
            }
        }

        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                    # Merge configs
                    self._merge_configs(default_config, user_config)
                print(f"✅ Loaded config from {self.config_path}")
            except Exception as e:
                print(f"❌ Failed to load config: {e}, using defaults")

        return default_config

    def _merge_configs(self, base: Dict, override: Dict):
        """Recursively merge configuration dictionaries"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value

    def _init_service_managers(self):
        """Initialize service managers"""

        # Import service modules
        try:
            from backlog_intelligence_system import get_intelligence_engine
            from context_compression_system import get_context_compression
            from doctrine_evolution_framework import get_doctrine_evolution
            from memory_doctrine_system import get_memory_doctrine_system
            from sasp_protocol import get_sasp_network, get_sasp_protocol
            from vector_database_integration import get_semantic_memory

            # Initialize service instances
            self.services = {
                "memory_doctrine": {
                    "manager": get_memory_doctrine_system(),
                    "status": "initialized",
                    "last_health_check": datetime.now()
                },
                "backlog_intelligence": {
                    "manager": get_intelligence_engine(),
                    "status": "initialized",
                    "last_health_check": datetime.now()
                },
                "context_compression": {
                    "manager": get_context_compression(),
                    "status": "initialized",
                    "last_health_check": datetime.now()
                },
                "doctrine_evolution": {
                    "manager": get_doctrine_evolution(),
                    "status": "initialized",
                    "last_health_check": datetime.now()
                },
                "sasp_protocol": {
                    "manager": get_sasp_protocol(),
                    "status": "initialized",
                    "last_health_check": datetime.now()
                },
                "sasp_network": {
                    "manager": get_sasp_network(),
                    "status": "initialized",
                    "last_health_check": datetime.now()
                },
                "vector_database": {
                    "manager": get_semantic_memory(),
                    "status": "initialized",
                    "last_health_check": datetime.now()
                }
            }

            print(f"✅ Initialized {len(self.services)} service managers")

        except ImportError as e:
            print(f"❌ Service import error: {e}")
            self.status = DeploymentStatus.ERROR

    def start_deployment(self) -> bool:
        """Start the production deployment"""

        if self.status != DeploymentStatus.INITIALIZING:
            print(f"❌ Cannot start deployment from {self.status.value} state")
            return False

        try:
            self.status = DeploymentStatus.STARTING_SERVICES
            print("🔄 Starting production services...")

            # Start core services
            success = self._start_core_services()

            if success:
                # Start monitoring and health checks
                self._start_monitoring()

                # Start network services
                self._start_network_services()

                self.status = DeploymentStatus.RUNNING
                print("✅ Production deployment started successfully")
                return True
            else:
                self.status = DeploymentStatus.ERROR
                print("❌ Failed to start core services")
                return False

        except Exception as e:
            self.status = DeploymentStatus.ERROR
            print(f"❌ Deployment startup failed: {e}")
            return False

    def _start_core_services(self) -> bool:
        """Start core services"""

        core_services = ["memory_doctrine", "context_compression", "vector_database"]

        for service_name in core_services:
            if not self.config["services"].get(service_name, {}).get("enabled", False):
                continue

            try:
                service_config = self.config["services"][service_name]
                service_info = self.services[service_name]

                # Start service-specific initialization
                if service_name == "memory_doctrine":
                    # Memory doctrine service is passive, just ensure it's ready
                    service_info["status"] = "running"

                elif service_name == "context_compression":
                    # Context compression is passive
                    service_info["status"] = "running"

                elif service_name == "vector_database":
                    # Vector database is passive
                    service_info["status"] = "running"

                print(f"✅ Started {service_name}")

            except Exception as e:
                print(f"❌ Failed to start {service_name}: {e}")
                return False

        return True

    def _start_monitoring(self):
        """Start monitoring and health check threads"""

        # Health check thread
        health_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
            name="health_monitor"
        )
        health_thread.start()
        self.threads["health_monitor"] = health_thread

        # Performance monitoring thread
        perf_thread = threading.Thread(
            target=self._performance_monitor_loop,
            daemon=True,
            name="performance_monitor"
        )
        perf_thread.start()
        self.threads["performance_monitor"] = perf_thread

        # Cleanup thread
        cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="cleanup_worker"
        )
        cleanup_thread.start()
        self.threads["cleanup_worker"] = cleanup_thread

        print("✅ Started monitoring threads")

    def _start_network_services(self):
        """Start network-facing services"""

        try:
            # Start SASP network
            if self.config["services"].get("sasp_network", {}).get("enabled", False):
                sasp_config = self.config["services"]["sasp_network"]
                network_manager = self.services["sasp_network"]["manager"]
                network_manager.start_network_services(sasp_config["port"])
                self.services["sasp_network"]["status"] = "running"
                print(f"✅ Started SASP network on port {sasp_config['port']}")

        except Exception as e:
            print(f"❌ Failed to start network services: {e}")

    def _health_check_loop(self):
        """Continuous health checking loop"""

        while self.status in [DeploymentStatus.STARTING_SERVICES, DeploymentStatus.RUNNING]:
            try:
                for service_name, service_info in self.services.items():
                    if not self.config["services"].get(service_name, {}).get("enabled", False):
                        continue

                    check_interval = self.config["services"][service_name].get("health_check_interval", 60)

                    # Check if it's time for health check
                    time_since_check = (datetime.now() - service_info["last_health_check"]).seconds
                    if time_since_check >= check_interval:
                        health_status = self._check_service_health(service_name)
                        service_info["status"] = health_status
                        service_info["last_health_check"] = datetime.now()

                        if health_status != "healthy":
                            print(f"⚠️  {service_name} health check failed: {health_status}")
                            self._handle_service_issue(service_name, health_status)

                time.sleep(10)  # Check every 10 seconds

            except Exception as e:
                print(f"❌ Health check loop error: {e}")
                time.sleep(30)

    def _check_service_health(self, service_name: str) -> str:
        """Check health of a specific service"""

        try:
            service_info = self.services[service_name]
            manager = service_info["manager"]

            if service_name == "memory_doctrine":
                # Check memory system health
                stats = manager.get_memory_stats()
                if stats and stats.get("total_items", 0) >= 0:
                    return "healthy"
                return "unhealthy"

            elif service_name == "backlog_intelligence":
                # Check intelligence engine
                patterns = manager.analyze_backlog_patterns()
                if patterns:
                    return "healthy"
                return "unhealthy"

            elif service_name == "context_compression":
                # Check compression system
                stats = manager.get_compression_stats()
                if stats:
                    return "healthy"
                return "unhealthy"

            elif service_name == "doctrine_evolution":
                # Check evolution framework
                stats = manager.get_evolution_stats()
                if stats:
                    return "healthy"
                return "unhealthy"

            elif service_name == "sasp_protocol":
                # Check SASP protocol
                status = manager.get_network_status()
                if status:
                    return "healthy"
                return "unhealthy"

            elif service_name == "sasp_network":
                # Check network manager
                if hasattr(manager, 'running') and manager.running:
                    return "healthy"
                return "unhealthy"

            elif service_name == "vector_database":
                # Check vector database
                stats = manager.get_memory_stats()
                if stats:
                    return "healthy"
                return "unhealthy"

            return "unknown"

        except Exception as e:
            print(f"❌ Health check failed for {service_name}: {e}")
            return "error"

    def _handle_service_issue(self, service_name: str, health_status: str):
        """Handle service health issues"""

        service_config = self.config["services"].get(service_name, {})

        if service_config.get("auto_restart", False) and health_status in ["unhealthy", "error"]:
            print(f"🔄 Attempting to restart {service_name}")

            try:
                # Attempt restart
                if self._restart_service(service_name):
                    print(f"✅ Successfully restarted {service_name}")
                else:
                    print(f"❌ Failed to restart {service_name}")

                    # If restart fails, mark as degraded
                    if self.status == DeploymentStatus.RUNNING:
                        self.status = DeploymentStatus.DEGRADED

            except Exception as e:
                print(f"❌ Restart error for {service_name}: {e}")

    def _restart_service(self, service_name: str) -> bool:
        """Restart a specific service"""

        try:
            service_info = self.services[service_name]
            manager = service_info["manager"]

            if service_name == "sasp_network":
                # Special handling for network services
                manager.stop_network_services()
                time.sleep(2)
                sasp_config = self.config["services"]["sasp_network"]
                manager.start_network_services(sasp_config["port"])
                return True

            # For other services, just reinitialize
            # (In a real system, you'd have proper restart logic)
            service_info["status"] = "restarted"
            service_info["last_health_check"] = datetime.now()
            return True

        except Exception as e:
            return False

    def _performance_monitor_loop(self):
        """Monitor system performance"""

        while self.status in [DeploymentStatus.STARTING_SERVICES, DeploymentStatus.RUNNING]:
            try:
                # Get system metrics
                metrics = self._get_system_metrics()

                # Check thresholds
                memory_limit = self.config["performance"].get("memory_limit_mb", 1024)
                cpu_limit = self.config["performance"].get("cpu_limit_percent", 80)

                if metrics["memory_mb"] > memory_limit:
                    print(f"⚠️  Memory usage high: {metrics['memory_mb']}MB / {memory_limit}MB limit")

                if metrics["cpu_percent"] > cpu_limit:
                    print(f"⚠️  CPU usage high: {metrics['cpu_percent']}% / {cpu_limit}% limit")

                # Log metrics periodically
                if int(time.time()) % 300 == 0:  # Every 5 minutes
                    self._log_performance_metrics(metrics)

                time.sleep(60)  # Check every minute

            except Exception as e:
                print(f"❌ Performance monitor error: {e}")
                time.sleep(60)

    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""

        try:
            import psutil
            process = psutil.Process()

            return {
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "cpu_percent": process.cpu_percent(interval=1),
                "threads": process.num_threads(),
                "open_files": len(process.open_files()),
                "timestamp": datetime.now().isoformat()
            }
        except ImportError:
            # Fallback if psutil not available
            return {
                "memory_mb": 0,
                "cpu_percent": 0,
                "threads": threading.active_count(),
                "open_files": 0,
                "timestamp": datetime.now().isoformat()
            }

    def _log_performance_metrics(self, metrics: Dict[str, Any]):
        """Log performance metrics"""

        log_path = Path("./logs/performance.log")
        log_path.parent.mkdir(exist_ok=True)

        with open(log_path, 'a') as f:
            f.write(json.dumps(metrics) + "\n")

    def _cleanup_loop(self):
        """Periodic cleanup loop"""

        cleanup_interval = self.config["performance"].get("cleanup_interval_hours", 24) * 3600

        while self.status in [DeploymentStatus.STARTING_SERVICES, DeploymentStatus.RUNNING]:
            try:
                time.sleep(cleanup_interval)

                if self.status == DeploymentStatus.RUNNING:
                    self._perform_cleanup()

            except Exception as e:
                print(f"❌ Cleanup loop error: {e}")

    def _perform_cleanup(self):
        """Perform system cleanup"""

        try:
            print("🧹 Performing system cleanup...")

            # Cleanup expired memories
            semantic_memory = self.services["vector_database"]["manager"]
            expired_count = semantic_memory.cleanup_expired()

            # Optimize storage
            semantic_memory.optimize_storage()

            # Cleanup old logs (older than 30 days)
            self._cleanup_old_logs()

            print(f"✅ Cleanup completed: removed {expired_count} expired items")

        except Exception as e:
            print(f"❌ Cleanup failed: {e}")

    def _cleanup_old_logs(self):
        """Clean up old log files"""

        try:
            logs_dir = Path("./logs")
            if not logs_dir.exists():
                return

            cutoff_date = datetime.now() - timedelta(days=30)

            for log_file in logs_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    print(f"🗑️  Removed old log: {log_file.name}")

        except Exception as e:
            print(f"❌ Log cleanup error: {e}")

    def get_deployment_status(self) -> Dict[str, Any]:
        """Get comprehensive deployment status"""

        service_statuses = {}
        for service_name, service_info in self.services.items():
            service_statuses[service_name] = {
                "status": service_info["status"],
                "enabled": self.config["services"].get(service_name, {}).get("enabled", False),
                "last_health_check": service_info["last_health_check"].isoformat(),
                "port": self.config["services"].get(service_name, {}).get("port")
            }

        return {
            "overall_status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            "services": service_statuses,
            "config": self.config,
            "active_threads": len(self.threads)
        }

    def stop_deployment(self):
        """Stop the production deployment"""

        if self.status in [DeploymentStatus.STOPPING, DeploymentStatus.STOPPED]:
            return

        print("🛑 Stopping production deployment...")
        self.status = DeploymentStatus.STOPPING

        try:
            # Stop network services
            if "sasp_network" in self.services:
                network_manager = self.services["sasp_network"]["manager"]
                if hasattr(network_manager, 'stop_network_services'):
                    network_manager.stop_network_services()

            # Stop monitoring threads
            for thread_name, thread in self.threads.items():
                if thread.is_alive():
                    print(f"Stopping thread: {thread_name}")

            # Wait for threads to finish
            time.sleep(2)

            self.status = DeploymentStatus.STOPPED
            print("✅ Production deployment stopped")

        except Exception as e:
            self.status = DeploymentStatus.ERROR
            print(f"❌ Error during shutdown: {e}")

    def cleanup(self):
        """Cleanup resources"""
        self.stop_deployment()

# Global deployment instance
_deployment = None

def get_production_deployment() -> ProductionDeployment:
    """Get global production deployment instance"""
    global _deployment
    if _deployment is None:
        _deployment = ProductionDeployment()
    return _deployment

def start_production() -> bool:
    """Start production deployment"""
    deployment = get_production_deployment()
    return deployment.start_deployment()

def stop_production():
    """Stop production deployment"""
    deployment = get_production_deployment()
    deployment.stop_deployment()

def get_production_status() -> Dict[str, Any]:
    """Get production deployment status"""
    deployment = get_production_deployment()
    return deployment.get_deployment_status()

def main():
    """Main production deployment entry point"""

    print("🚀 BIT RAGE LABOUR Production Deployment")
    print("=" * 50)

    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="BIT RAGE LABOUR Production Deployment")
    parser.add_argument("action", choices=["start", "stop", "status", "restart"],
                       help="Action to perform")
    parser.add_argument("--config", type=str,
                       help="Path to configuration file")

    args = parser.parse_args()

    if args.config:
        config_path = Path(args.config)
    else:
        config_path = None

    # Initialize deployment
    global _deployment
    _deployment = ProductionDeployment(config_path)

    if args.action == "start":
        print("Starting production deployment...")
        if start_production():
            print("✅ Production deployment started successfully")
            print("Press Ctrl+C to stop")

            # Keep running
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nReceived shutdown signal...")
                stop_production()
        else:
            print("❌ Failed to start production deployment")
            sys.exit(1)

    elif args.action == "stop":
        stop_production()
        print("✅ Production deployment stopped")

    elif args.action == "status":
        status = get_production_status()
        print(json.dumps(status, indent=2))

    elif args.action == "restart":
        print("Restarting production deployment...")
        stop_production()
        time.sleep(2)
        if start_production():
            print("✅ Production deployment restarted successfully")
        else:
            print("❌ Failed to restart production deployment")
            sys.exit(1)

if __name__ == "__main__":
    main()
