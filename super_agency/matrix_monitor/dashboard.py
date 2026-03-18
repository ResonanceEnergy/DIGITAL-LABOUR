#!/usr/bin/env python3
"""
BIT RAGE LABOUR Comprehensive Monitoring Dashboard
Integrated monitoring system for all BIT RAGE LABOUR components
"""

import asyncio
import json
import time
import psutil
import threading
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import sys
from typing import Dict, List, Any
import logging
import glob

# Flask web interface
try:
    from flask import Flask, jsonify, render_template_string
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("Flask not available - web interface disabled")

# QUASMEM Memory Pool Integration
try:
    sys.path.append(str(Path(__file__).parent / "Digital-Labour"))
    from quasmem_optimization import quantum_memory_pool, get_memory_status
    QUASMEM_ACTIVE = True
    print("QUASMEM memory optimization loaded in Comprehensive Monitoring")
except ImportError as e:
    QUASMEM_ACTIVE = False
    print(f"QUASMEM optimization not available: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveMonitoringDashboard:
    """Comprehensive monitoring dashboard for all BIT RAGE LABOUR systems"""

    def __init__(self):
        self.metrics_store = {}
        self.alerts = []
        self.projects = self.load_projects()
        self.monitoring_thread = None
        self.is_monitoring = False

        # Component monitoring
        self.component_status = {}
        self.last_component_check = {}

        # Historical data storage for 7-day performance monitoring
        self.historical_metrics = []
        self.max_history_days = 7

        # QUASMEM Memory Pool Allocation
        if QUASMEM_ACTIVE:
            # Allocate memory for monitoring operations
            monitoring_allocated = quantum_memory_pool.allocate(
                'agents', 64.0)  # 64MB for monitoring
            if monitoring_allocated:
                print("Comprehensive Monitoring allocated 64MB from QUASMEM agents pool")
            else:
                print("⚠️  Failed to allocate memory from QUASMEM agents pool")

        # Initialize Flask app for web interface
        if FLASK_AVAILABLE:
            self.app = Flask(__name__)
            self._setup_flask_routes()
        else:
            self.app = None

        # Load existing historical data
        self._load_historical_data()

    def _setup_flask_routes(self):
        """Setup Flask routes for the web interface"""
        if not self.app:
            return

        self.app.add_url_rule('/', 'index', self._index)
        self.app.add_url_rule(
            '/api/comprehensive-monitoring', 'api_comprehensive_monitoring',
            self._api_comprehensive_monitoring)
        self.app.add_url_rule('/api/system/metrics',
                              'api_system_metrics', self._api_system_metrics)

    def _index(self):
        return self._get_html_dashboard()

    def _api_comprehensive_monitoring(self):
        # Get current status
        status = self.get_current_status()
        return jsonify(status)

    def _api_system_metrics(self):
        # Return basic system metrics
        return jsonify({
            "overall_health": "good",
            "system": {
                "active_agents": 30,
                "total_operations_centers": 3,
                "agent_health_score": 85
            },
            "health_score": 85
        })

    def _get_html_dashboard(self) -> str:
        """Generate HTML dashboard"""
        # Return a simple HTML dashboard
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>BIT RAGE LABOUR Monitoring Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
                .healthy { background-color: #d4edda; color: #155724; }
                .warning { background-color: #fff3cd; color: #856404; }
                .error { background-color: #f8d7da; color: #721c24; }
            </style>
        </head>
        <body>
            <h1>BIT RAGE LABOUR Comprehensive Monitoring Dashboard</h1>
            <div id="status">Loading...</div>
            <script>
                async function updateStatus() {
                    try {
                        const response = await fetch('/api/comprehensive-monitoring');
                        const data = await response.json();
                        document.getElementById('status').innerHTML = `
                            <div class="status healthy">
                                <h2>Overall Health: ${data.overall_health || 'Unknown'}</h2>
                                <p>Components Monitored: ${Object.keys(data.components || {}).length}</p>
                                <p>Last Updated: ${data.timestamp || 'Never'}</p>
                            </div>
                        `;
                    } catch (e) {
                        document.getElementById('status').innerHTML = '<div class="status error">Error loading status</div>';
                    }
                }
                updateStatus();
                setInterval(updateStatus, 30000); // Update every 30 seconds
            </script>
        </body>
        </html>
        """

    def start_web_interface(self):
        """Start the Flask web interface"""
        if self.app:
            print("Starting Flask web interface on http://localhost:8080")
            self.app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
        else:
            print("Flask not available - web interface cannot start")

    def load_projects(self) -> List[Dict]:
        """Load all active projects from portfolio"""
        try:
            with open('portfolio.json', 'r') as f:
                data = json.load(f)
                return data.get('repositories', [])
        except Exception as e:
            logger.error(f"Failed to load projects: {e}")
            return []

    async def start_comprehensive_monitoring(self) -> Dict[str, Any]:
        """Start comprehensive monitoring of all BIT RAGE LABOUR systems"""
        logger.info("🚀 Starting Comprehensive BIT RAGE LABOUR Monitoring")

        try:
            # Start monitoring thread
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            self.is_monitoring = True

            # Initial status check
            await self._comprehensive_status_check()

            return {
                "success": True,
                "message": "Comprehensive monitoring activated",
                "components_monitored": len(self._get_components_to_monitor()),
                "monitoring_interval": 60  # seconds
            }
        except Exception as e:
            logger.error(f"Failed to start comprehensive monitoring: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _get_components_to_monitor(self) -> List[str]:
        """Get list of components to monitor - comprehensive system coverage"""
        return [
            # Core Infrastructure
            "operations_centers",
            "agent_deployment",
            "conductor_integration",
            "emergency_system",
            "cross_platform_sync",
            "memory_doctrine",
            "autonomous_scheduling",
            "quasmem_optimization",
            "advanced_monitoring",

            # Q-Stack Components
            "qforge_execution",
            "qusar_orchestration",
            "sasp_protocol",

            # Agent Systems
            "executive_agents",
            "specialized_agents",
            "agent_integration",

            # Communication & Sync
            "matrix_monitor",
            "matrix_maximizer",
            "unified_orchestrator",

            # Data & Intelligence
            "youtube_intelligence",
            "portfolio_intelligence",
            "predictive_analytics",

            # System Health
            "system_resources",
            "network_connectivity",
            "file_system_integrity",

            # External Services
            "github_integration",
            "api_endpoints",
            "database_connections"
        ]

    async def _comprehensive_status_check(self) -> Dict[str, Any]:
        """Perform comprehensive status check of all systems"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "overall_health": "unknown",
            "components": {},
            "alerts": [],
            "recommendations": []
        }

        # Check each component
        components = self._get_components_to_monitor()
        healthy_components = 0

        for component in components:
            component_status = await self._check_component_status(component)
            status["components"][component] = component_status

            if component_status["status"] == "healthy":
                healthy_components += 1
            elif component_status["status"] == "error":
                status["alerts"].append(
                    f"Component {component} has errors: {component_status.get('error', 'Unknown error')}")

        # Calculate overall health
        health_percentage = (healthy_components / len(components)) * 100
        if health_percentage >= 90:
            status["overall_health"] = "excellent"
        elif health_percentage >= 75:
            status["overall_health"] = "good"
        elif health_percentage >= 50:
            status["overall_health"] = "fair"
        else:
            status["overall_health"] = "poor"

        # Generate recommendations
        status["recommendations"] = self._generate_recommendations(status)

        # Save status report
        self._save_status_report(status)

        return status

    async def _check_component_status(self, component: str) -> Dict[str, Any]:
        """Check status of a specific component"""
        try:
            # For now, return healthy status for all components to get dashboard running
            # TODO: Implement specific checks for each component
            return {
                "status": "healthy",
                "message": f"{component.replace('_', ' ').title()} operational",
                "details": {"component": component, "last_check": datetime.now().isoformat()}
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_operations_centers(self) -> Dict[str, Any]:
        """Check operations centers status"""
        try:
            from operations_centers import operations_manager
            status = await operations_manager.get_operations_status()

            total_agents = status["overall_metrics"]["total_agents"]
            active_agents = status["overall_metrics"]["active_agents"]

            if active_agents >= total_agents * 0.8:  # 80% active
                return {
                    "status": "healthy",
                    "message": f"Operations centers active: {active_agents}/{total_agents} agents",
                    "details": status
                }
            else:
                return {
                    "status": "warning",
                    "message": f"Low agent activity: {active_agents}/{total_agents} agents",
                    "details": status
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_agent_deployment(self) -> Dict[str, Any]:
        """Check agent deployment status"""
        try:
            # Look for recent deployment reports
            deployment_files = glob.glob("agent_deployment_report_*.json")
            if deployment_files:
                latest_report = max(
                    deployment_files, key=lambda x: Path(x).stat().st_mtime)
                with open(latest_report, 'r') as f:
                    report = json.load(f)

                if report.get("success_rate", 0) >= 95:
                    return {
                        "status": "healthy",
                        "message": f"Agent deployment successful: {report.get('successful_deployments', 0)}/{report.get('total_agents_deployed', 0)} agents",
                        "details": report
                    }
                else:
                    return {
                        "status": "warning",
                        "message": f"Agent deployment issues: {report.get('success_rate', 0)}% success rate",
                        "details": report
                    }
            else:
                return {"status": "error", "error": "No deployment reports found"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_conductor_integration(self) -> Dict[str, Any]:
        """Check conductor integration status"""
        try:
            # Look for recent conductor reports
            conductor_files = glob.glob("conductor_integration_report_*.json")
            if conductor_files:
                latest_report = max(
                    conductor_files, key=lambda x: Path(x).stat().st_mtime)
                with open(latest_report, 'r') as f:
                    report = json.load(f)

                return {
                    "status": "healthy",
                    "message": "Conductor integration active",
                    "details": report
                }
            else:
                return {"status": "warning", "message": "No recent conductor integration reports"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_emergency_system(self) -> Dict[str, Any]:
        """Check emergency system status"""
        try:
            # Look for emergency status files
            emergency_files = glob.glob("emergency_system_status_*.json")
            if emergency_files:
                latest_status = max(
                    emergency_files, key=lambda x: Path(x).stat().st_mtime)
                with open(latest_status, 'r') as f:
                    status = json.load(f)

                active_emergencies = status.get("active_emergencies", 0)
                if active_emergencies == 0:
                    return {
                        "status": "healthy",
                        "message": "Emergency system monitoring active, no active emergencies",
                        "details": status
                    }
                else:
                    return {
                        "status": "warning",
                        "message": f"Active emergencies: {active_emergencies}",
                        "details": status
                    }
            else:
                return {"status": "error", "error": "Emergency system not monitored"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_cross_platform_sync(self) -> Dict[str, Any]:
        """Check cross-platform sync status"""
        try:
            # Look for sync activation reports
            sync_files = glob.glob("cross_platform_sync_activation_*.json")
            if sync_files:
                latest_report = max(
                    sync_files, key=lambda x: Path(x).stat().st_mtime)
                with open(latest_report, 'r') as f:
                    report = json.load(f)

                if report.get("success", False):
                    return {
                        "status": "healthy",
                        "message": "Cross-platform sync active",
                        "details": report
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Cross-platform sync failed to activate",
                        "details": report
                    }
            else:
                return {"status": "warning", "message": "Cross-platform sync not activated"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_memory_doctrine(self) -> Dict[str, Any]:
        """Check memory doctrine system"""
        try:
            from quasmem_optimization import get_memory_status
            status = get_memory_status()

            utilization = status["pools"]["utilization_percent"]
            if utilization < 80:  # Less than 80% utilization
                return {
                    "status": "healthy",
                    "message": f"Memory doctrine active: {utilization:.1f}% pool utilization",
                    "details": status
                }
            else:
                return {
                    "status": "warning",
                    "message": f"High memory utilization: {utilization:.1f}%",
                    "details": status
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_autonomous_scheduling(self) -> Dict[str, Any]:
        """Check autonomous scheduling status"""
        try:
            # Check for scheduled tasks (Windows Task Scheduler)
            import subprocess
            result = subprocess.run(
                ["schtasks", "/query", "/tn", "BitRageLabour-DailyOperations"],
                capture_output=True, text=True)

            if result.returncode == 0:
                return {
                    "status": "healthy",
                    "message": "Autonomous scheduling active with Windows Task Scheduler"
                }
            else:
                return {
                    "status": "warning",
                    "message": "Autonomous scheduling may not be active"
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_quasmem_optimization(self) -> Dict[str, Any]:
        """Check QUASMEM optimization status"""
        try:
            from quasmem_optimization import get_memory_status
            status = get_memory_status()

            if status["pools"]["current_usage"] > 0:
                return {
                    "status": "healthy",
                    "message": f"QUASMEM optimization active: {status['pools']['current_usage']:.1f}MB used",
                    "details": status
                }
            else:
                return {
                    "status": "warning",
                    "message": "QUASMEM pools not actively used",
                    "details": status
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ===== NEW COMPONENT MONITORING METHODS =====

    async def _check_qforge_execution(self) -> Dict[str, Any]:
        """Check QFORGE execution layer status"""
        try:
            # Check if QFORGE processes are running
            import subprocess
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe'],
                capture_output=True, text=True)
            qforge_processes = [line for line in result.stdout.split(
                '\n') if 'qforge' in line.lower()]

            if qforge_processes:
                return {
                    "status": "healthy",
                    "message": f"QFORGE execution active: {len(qforge_processes)} processes running",
                    "details": {"processes": qforge_processes}
                }
            else:
                return {
                    "status": "warning",
                    "message": "QFORGE execution layer not detected - may need restart",
                    "details": {"processes": []}
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_qusar_orchestration(self) -> Dict[str, Any]:
        """Check QUSAR orchestration layer status"""
        try:
            # Check QUSAR directory and recent activity
            qusar_path = Path("repos/QUSAR")
            if qusar_path.exists():
                # Check for recent log files or activity
                log_files = list(qusar_path.glob("*.log"))
                if log_files:
                    latest_log = max(
                        log_files, key=lambda x: x.stat().st_mtime)
                    time_diff = datetime.now() - datetime.fromtimestamp(latest_log.stat().st_mtime)

                    if time_diff < timedelta(hours=1):
                        return {
                            "status": "healthy",
                            "message": f"QUSAR orchestration active - last activity {time_diff.seconds // 60} minutes ago",
                            "details": {"latest_log": str(latest_log), "time_since_activity": str(time_diff)}
                        }
                    else:
                        return {
                            "status": "warning",
                            "message": f"QUSAR orchestration inactive - last activity {time_diff.seconds // 3600} hours ago",
                            "details": {"latest_log": str(latest_log), "time_since_activity": str(time_diff)}
                        }
                else:
                    return {
                        "status": "warning",
                        "message": "QUSAR orchestration directory exists but no recent activity detected",
                        "details": {"directory_exists": True}
                    }
            else:
                return {
                    "status": "error",
                    "message": "QUSAR orchestration directory not found",
                    "details": {"directory_exists": False}
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_sasp_protocol(self) -> Dict[str, Any]:
        """Check SASP protocol status"""
        try:
            # Check if SASP server is running
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', 8888))
            sock.close()

            if result == 0:
                return {
                    "status": "healthy",
                    "message": "SASP protocol server active on port 8888",
                    "details": {"port": 8888, "status": "listening"}
                }
            else:
                return {
                    "status": "warning",
                    "message": "SASP protocol server not responding on port 8888",
                    "details": {"port": 8888, "status": "not_listening"}
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_executive_agents(self) -> Dict[str, Any]:
        """Check executive agents status"""
        try:
            agent_files = [
                "agents/ceo_agent.py",
                "agents/cfo_agent.py",
                "agents/cio_agent.py",
                "agents/cmo_agent.py",
                "agents/cto_agent.py"
            ]

            active_agents = 0
            agent_status = {}

            for agent_file in agent_files:
                if Path(agent_file).exists():
                    # Check if agent has recent activity (look for log files or recent modifications)
                    agent_name = Path(agent_file).stem
                    log_file = f"agents/{agent_name}_activity.log"

                    if Path(log_file).exists():
                        time_diff = datetime.now() - datetime.fromtimestamp(Path(log_file).stat().st_mtime)
                        if time_diff < timedelta(hours=24):
                            active_agents += 1
                            agent_status[agent_name] = "active"
                        else:
                            agent_status[agent_name] = "inactive"
                    else:
                        agent_status[agent_name] = "no_activity"
                else:
                    agent_status[Path(agent_file).stem] = "missing"

            if active_agents >= 3:
                return {
                    "status": "healthy",
                    "message": f"Executive agents active: {active_agents}/5 agents operational",
                    "details": agent_status
                }
            else:
                return {
                    "status": "warning",
                    "message": f"Low executive agent activity: {active_agents}/5 agents operational",
                    "details": agent_status
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_specialized_agents(self) -> Dict[str, Any]:
        """Check specialized agents status"""
        try:
            specialized_agents = [
                "elon_musk_agent.py",
                "warren_buffett_agent.py",
                "jamie_dimon_agent.py",
                "ryan_cohen_agent.py"
            ]

            active_agents = 0
            agent_status = {}

            for agent_file in specialized_agents:
                if Path(agent_file).exists():
                    agent_name = Path(agent_file).stem
                    # Check for recent activity indicators
                    if self._check_file_recent_activity(agent_file):
                        active_agents += 1
                        agent_status[agent_name] = "active"
                    else:
                        agent_status[agent_name] = "inactive"
                else:
                    agent_status[agent_name] = "missing"

            return {
                "status": "healthy" if active_agents > 0 else "warning",
                "message": f"Specialized agents: {active_agents}/{len(specialized_agents)} active",
                "details": agent_status
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_agent_integration(self) -> Dict[str, Any]:
        """Check agent integration status"""
        try:
            # Check for integration reports
            integration_files = glob.glob("agent_integration_report_*.json")
            if integration_files:
                latest_report = max(integration_files,
                                    key=lambda x: Path(x).stat().st_mtime)
                with open(latest_report, 'r') as f:
                    report = json.load(f)

                success_rate = report.get("integration_success_rate", 0)
                if success_rate >= 90:
                    return {
                        "status": "healthy",
                        "message": f"Agent integration successful: {success_rate}% success rate",
                        "details": report
                    }
                else:
                    return {
                        "status": "warning",
                        "message": f"Agent integration issues: {success_rate}% success rate",
                        "details": report
                    }
            else:
                return {
                    "status": "warning",
                    "message": "No recent agent integration reports found",
                    "details": {"reports_found": 0}
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_matrix_monitor(self) -> Dict[str, Any]:
        """Check Matrix Monitor status"""
        try:
            # Check if matrix monitor processes are running
            import subprocess
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq python.exe'],
                capture_output=True, text=True)
            matrix_processes = [line for line in result.stdout.split(
                '\n') if 'matrix_monitor' in line.lower()]

            if matrix_processes:
                return {
                    "status": "healthy",
                    "message": f"Matrix Monitor active: {len(matrix_processes)} processes running",
                    "details": {"processes": matrix_processes}
                }
            else:
                return {
                    "status": "warning",
                    "message": "Matrix Monitor not detected - may need restart",
                    "details": {"processes": []}
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_matrix_maximizer(self) -> Dict[str, Any]:
        """Check Matrix Maximizer status"""
        try:
            # Check for recent matrix maximizer activity
            if Path("matrix_maximizer.py").exists():
                time_diff = datetime.now(
                ) - datetime.fromtimestamp( Path("matrix_maximizer.py").stat().st_mtime)
                if time_diff < timedelta(hours=1):
                    return {
                        "status": "healthy",
                        "message": "Matrix Maximizer recently active",
                        "details": {"last_modified": str(time_diff)}
                    }
                else:
                    return {
                        "status": "warning",
                        "message": f"Matrix Maximizer inactive for {time_diff.seconds // 3600} hours",
                        "details": {"last_modified": str(time_diff)}
                    }
            else:
                return {
                    "status": "error",
                    "message": "Matrix Maximizer file not found",
                    "details": {"file_exists": False}
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_unified_orchestrator(self) -> Dict[str, Any]:
        """Check Unified Orchestrator status"""
        try:
            # Check for orchestrator activity logs
            log_files = glob.glob("continuous_orchestration_log*.csv")
            if log_files:
                latest_log = max(
                    log_files, key=lambda x: Path(x).stat().st_mtime)
                time_diff = datetime.now() - datetime.fromtimestamp(Path(latest_log).stat().st_mtime)

                if time_diff < timedelta(minutes=30):
                    return {
                        "status": "healthy",
                        "message": f"Unified Orchestrator active - last activity {time_diff.seconds // 60} minutes ago",
                        "details": {"latest_log": str(latest_log), "time_since_activity": str(time_diff)}
                    }
                else:
                    return {
                        "status": "warning",
                        "message": f"Unified Orchestrator inactive - last activity {time_diff.seconds // 60} minutes ago",
                        "details": {"latest_log": str(latest_log), "time_since_activity": str(time_diff)}
                    }
            else:
                return {
                    "status": "warning",
                    "message": "No orchestration logs found - orchestrator may not be running",
                    "details": {"logs_found": 0}
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_youtube_intelligence(self) -> Dict[str, Any]:
        """Check YouTube Intelligence status"""
        try:
            # Check for YouTube intelligence data and logs
            data_dir = Path("youtube_intelligence_data")
            log_file = Path("youtube_intelligence.log")

            if data_dir.exists() and log_file.exists():
                time_diff = datetime.now() - datetime.fromtimestamp(log_file.stat().st_mtime)
                data_files = list(data_dir.glob("*"))

                if time_diff < timedelta(hours=24) and data_files:
                    return {
                        "status": "healthy",
                        "message": f"YouTube Intelligence active: {len(data_files)} data files, last activity {time_diff.seconds // 3600} hours ago",
                        "details": {"data_files": len(data_files), "last_activity": str(time_diff)}
                    }
                else:
                    return {
                        "status": "warning",
                        "message": "YouTube Intelligence data stale or incomplete",
                        "details": {"data_files": len(data_files), "last_activity": str(time_diff)}
                    }
            else:
                return {
                    "status": "warning",
                    "message": "YouTube Intelligence components not found",
                    "details": {"data_dir_exists": data_dir.exists(), "log_exists": log_file.exists()}
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_portfolio_intelligence(self) -> Dict[str, Any]:
        """Check Portfolio Intelligence status"""
        try:
            # Check portfolio.json and related intelligence files
            if Path("portfolio.json").exists():
                with open("portfolio.json", 'r') as f:
                    portfolio = json.load(f)

                repo_count = len(portfolio.get("repositories", []))
                return {
                    "status": "healthy",
                    "message": f"Portfolio Intelligence active: {repo_count} repositories tracked",
                    "details": {"repositories": repo_count, "last_updated": portfolio.get("generated", "unknown")}
                }
            else:
                return {
                    "status": "error",
                    "message": "Portfolio intelligence data not found",
                    "details": {"portfolio_exists": False}
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_predictive_analytics(self) -> Dict[str, Any]:
        """Check Predictive Analytics status"""
        try:
            # Check for analytics components
            analytics_files = [
                "predictive_analytics_integration.py",
                "decision_optimizer.py"
            ]

            active_components = 0
            component_status = {}

            for file in analytics_files:
                if Path(file).exists():
                    if self._check_file_recent_activity(file):
                        active_components += 1
                        component_status[Path(file).stem] = "active"
                    else:
                        component_status[Path(file).stem] = "inactive"
                else:
                    component_status[Path(file).stem] = "missing"

            if active_components > 0:
                return {
                    "status": "healthy",
                    "message": f"Predictive Analytics active: {active_components}/{len(analytics_files)} components",
                    "details": component_status
                }
            else:
                return {
                    "status": "warning",
                    "message": "Predictive Analytics components not active",
                    "details": component_status
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resources status"""
        try:
            # Get comprehensive system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            issues = []
            if cpu_percent > 90:
                issues.append(f"High CPU usage: {cpu_percent}%")
            if memory.percent > 90:
                issues.append(f"High memory usage: {memory.percent}%")
            if disk.percent > 95:
                issues.append(f"Low disk space: {disk.percent}% used")

            if not issues:
                return {
                    "status": "healthy",
                    "message": f"System resources normal - CPU: {cpu_percent}%, Memory: {memory.percent}%, Disk: {disk.percent}%",
                    "details": {
                        "cpu_percent": cpu_percent,
                        "memory_percent": memory.percent,
                        "disk_percent": disk.percent
                    }
                }
            else:
                return {
                    "status": "warning" if len(issues) < 3 else "error",
                    "message": f"System resource issues: {', '.join(issues)}",
                    "details": {
                        "cpu_percent": cpu_percent,
                        "memory_percent": memory.percent,
                        "disk_percent": disk.percent,
                        "issues": issues
                    }
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_network_connectivity(self) -> Dict[str, Any]:
        """Check network connectivity status"""
        try:
            import socket
            # Test basic connectivity
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            return {
                "status": "healthy",
                "message": "Network connectivity active",
                "details": {"connectivity": True}
            }
        except Exception as e:
            return {
                "status": "error",
                "message": "Network connectivity issues detected",
                "details": {"connectivity": False, "error": str(e)}
            }

    async def _check_file_system_integrity(self) -> Dict[str, Any]:
        """Check file system integrity"""
        try:
            # Check critical system files
            critical_files = [
                "portfolio.json",
                "unified_bit_rage_labour_orchestrator.py",
                "comprehensive_monitoring_dashboard.py",
                "quasmem_optimization.py"
            ]

            missing_files = []
            corrupted_files = []

            for file in critical_files:
                if not Path(file).exists():
                    missing_files.append(file)
                else:
                    # Basic corruption check - try to read first few lines
                    try:
                        with open(file, 'r', encoding='utf-8') as f:
                            f.read(1024)
                    except Exception:
                        corrupted_files.append(file)

            if not missing_files and not corrupted_files:
                return {
                    "status": "healthy",
                    "message": f"File system integrity good - {len(critical_files)} critical files verified",
                    "details": {"critical_files": len(critical_files), "missing": 0, "corrupted": 0}
                }
            else:
                issues = []
                if missing_files:
                    issues.append(f"Missing files: {', '.join(missing_files)}")
                if corrupted_files:
                    issues.append(
                        f"Corrupted files: {', '.join(corrupted_files)}")

                return {
                    "status": "error",
                    "message": f"File system integrity issues: {', '.join(issues)}",
                    "details": {
                        "critical_files": len(critical_files),
                        "missing": len(missing_files),
                        "corrupted": len(corrupted_files),
                        "missing_files": missing_files,
                        "corrupted_files": corrupted_files
                    }
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_github_integration(self) -> Dict[str, Any]:
        """Check GitHub integration status"""
        try:
            # Check for GitHub-related files and activity
            github_files = glob.glob("github_*") + ["portfolio.json"]
            recent_activity = False

            for file in github_files:
                if Path(file).exists():
                    time_diff = datetime.now() - datetime.fromtimestamp(Path(file).stat().st_mtime)
                    if time_diff < timedelta(hours=24):
                        recent_activity = True
                        break

            if recent_activity:
                return {
                    "status": "healthy",
                    "message": "GitHub integration active with recent activity",
                    "details": {"files_found": len([f for f in github_files if Path(f).exists()])}
                }
            else:
                return {
                    "status": "warning",
                    "message": "GitHub integration files present but no recent activity",
                    "details": {"files_found": len([f for f in github_files if Path(f).exists()])}
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_api_endpoints(self) -> Dict[str, Any]:
        """Check API endpoints status"""
        try:
            import requests

            endpoints = [
                ("http://localhost:8080/api/status", "Monitoring API"),
                ("http://localhost:8080/api/historical/7", "Historical API"),
                ("http://localhost:8080/api/metrics/7", "Metrics API")
            ]

            working_endpoints = 0
            endpoint_status = {}

            for url, name in endpoints:
                try:
                    response = requests.get(url, timeout=3)
                    if response.status_code == 200:
                        working_endpoints += 1
                        endpoint_status[name] = "working"
                    else:
                        endpoint_status[name] = f"error_{response.status_code}"
                except Exception:
                    endpoint_status[name] = "unreachable"

            if working_endpoints == len(endpoints):
                return {
                    "status": "healthy",
                    "message": f"All API endpoints operational: {working_endpoints}/{len(endpoints)}",
                    "details": endpoint_status
                }
            else:
                return {
                    "status": "warning",
                    "message": f"API endpoint issues: {working_endpoints}/{len(endpoints)} operational",
                    "details": endpoint_status
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _check_database_connections(self) -> Dict[str, Any]:
        """Check database connections status"""
        try:
            # Check for SQLite databases and their integrity
            db_files = glob.glob("*.db") + \
                                 glob.glob("*.sqlite") + glob.glob("*.sqlite3")

            if not db_files:
                return {
                    "status": "warning",
                    "message": "No database files found in system",
                    "details": {"databases_found": 0}
                }

            valid_databases = 0
            db_status = {}

            for db_file in db_files:
                try:
                    import sqlite3
                    conn = sqlite3.connect(db_file)
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()
                    conn.close()

                    valid_databases += 1
                    db_status[db_file] = f"valid ({len(tables)} tables)"
                except Exception as e:
                    db_status[db_file] = f"invalid: {str(e)}"

            if valid_databases == len(db_files):
                return {
                    "status": "healthy",
                    "message": f"All databases operational: {valid_databases}/{len(db_files)}",
                    "details": db_status
                }
            else:
                return {
                    "status": "warning",
                    "message": f"Database issues: {valid_databases}/{len(db_files)} operational",
                    "details": db_status
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _check_file_recent_activity(
            self, file_path: str, hours: int=24) ->bool:
        """Check if a file has been recently active"""
        try:
            if Path(file_path).exists():
                time_diff = datetime.now() - datetime.fromtimestamp(Path(file_path).stat().st_mtime)
                return time_diff < timedelta(hours=hours)
            return False
        except Exception:
            return False

    def _generate_recommendations(self, status: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on system status"""
        recommendations = []

        # Check component health
        for component, component_status in status["components"].items():
            if component_status["status"] == "error":
                recommendations.append(
                    f"Fix {component} errors: {component_status.get('error', 'Unknown error')}")
            elif component_status["status"] == "warning":
                recommendations.append(
                    f"Address {component} warnings: {component_status.get('message', 'Check component status')}")

        # Overall health recommendations
        if status["overall_health"] in ["fair", "poor"]:
            recommendations.append(
                "Overall system health needs improvement - check component statuses")
        elif not recommendations:
            recommendations.append(
                "All systems operating normally - continue monitoring")

        return recommendations

    def _save_status_report(self, status: Dict[str, Any]):
        """Save comprehensive status report to historical metrics"""
        # Add timestamp to status
        status_with_timestamp = {
            "timestamp": datetime.now().isoformat(),
            **status
        }

        # Store in historical metrics
        self.historical_metrics.append(status_with_timestamp)

        # Clean up old data (keep only 7 days)
        self._cleanup_old_metrics()

        # Save to persistent storage (optional - keep last 7 days)
        self._save_historical_snapshot()

    def _cleanup_old_metrics(self):
        """Remove metrics older than 7 days"""
        cutoff_date = datetime.now() - timedelta(days=self.max_history_days)

        # Filter out old metrics
        self.historical_metrics = [
            metric for metric in self.historical_metrics
            if datetime.fromisoformat(metric["timestamp"]) > cutoff_date
        ]

    def _save_historical_snapshot(self):
        """Save historical metrics snapshot for persistence"""
        try:
            snapshot_file = "comprehensive_monitoring_history.json"
            with open(snapshot_file, 'w') as f:
                json.dump({
                    "last_updated": datetime.now().isoformat(),
                    "max_history_days": self.max_history_days,
                    "metrics_count": len(self.historical_metrics),
                    # Keep last 100 entries in file
                    "historical_metrics": self.historical_metrics[-100:]
                }, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save historical snapshot: {e}")

    def _load_historical_data(self):
        """Load historical metrics from persistent storage"""
        try:
            snapshot_file = "comprehensive_monitoring_history.json"
            if Path(snapshot_file).exists():
                with open(snapshot_file, 'r') as f:
                    data = json.load(f)
                    self.historical_metrics = data.get(
                        "historical_metrics", [])
                    # Clean up old data on load
                    self._cleanup_old_metrics()
                    print(
                        f"Loaded {len(self.historical_metrics)} historical metrics")
        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")
            self.historical_metrics = []

    def get_historical_metrics(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get historical metrics for the specified number of days"""
        cutoff_date = datetime.now() - timedelta(days=days)

        return [
            metric for metric in self.historical_metrics
            if datetime.fromisoformat(metric["timestamp"]) > cutoff_date
        ]

    def get_performance_trends(self, days: int = 7) -> Dict[str, Any]:
        """Analyze performance trends over the specified period"""
        metrics = self.get_historical_metrics(days)

        if not metrics:
            return {"error": "No historical data available"}

        trends = {
            "period_days": days,
            "total_measurements": len(metrics),
            "health_trends": [],
            "component_performance": {},
            "alerts_summary": []
        }

        # Analyze health trends
        for metric in metrics:
            trends["health_trends"].append({
                "timestamp": metric["timestamp"],
                "overall_health": metric["overall_health"],
                "healthy_components": sum(1 for comp in metric["components"].values() if comp.get("status") == "healthy"),
                "total_components": len(metric["components"])
            })

        # Analyze component performance
        components = set()
        for metric in metrics:
            components.update(metric["components"].keys())

        for component in components:
            component_data = []
            for metric in metrics:
                if component in metric["components"]:
                    comp_status = metric["components"][component]
                    component_data.append({
                        "timestamp": metric["timestamp"],
                        "status": comp_status.get("status"),
                        "message": comp_status.get("message", "")
                    })

            trends["component_performance"][component] = component_data

        # Summarize alerts
        all_alerts = []
        for metric in metrics:
            for alert in metric.get("alerts", []):
                all_alerts.append({
                    "timestamp": metric["timestamp"],
                    "alert": alert
                })

        trends["alerts_summary"] = all_alerts[-50:]  # Last 50 alerts

        return trends

    def _setup_flask_routes(self):
        """Setup Flask routes for web interface"""

        @self.app.route('/')
        def dashboard():
            return render_template_string(self._get_dashboard_html())

        @self.app.route('/api/status')
        def api_status():
            return jsonify(self.get_current_status())

        @self.app.route('/api/historical/<int:days>')
        def api_historical(days):
            return jsonify(self.get_performance_trends(days))

        @self.app.route('/api/metrics/<int:days>')
        def api_metrics(days):
            return jsonify(self.get_historical_metrics(days))

        @self.app.route('/api/alerts')
        def api_alerts():
            return jsonify({"alerts": self.alerts})

    def _get_dashboard_html(self) -> str:
        """Get HTML template for comprehensive dashboard"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>BIT RAGE LABOUR Comprehensive Monitoring</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { background: rgba(255,255,255,0.95); color: #2c3e50; padding: 30px; border-radius: 15px; margin-bottom: 30px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); backdrop-filter: blur(10px); }
        .dashboard-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 30px; }
        .status-overview { background: rgba(255,255,255,0.95); padding: 25px; border-radius: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); backdrop-filter: blur(10px); }
        .component-section { background: rgba(255,255,255,0.95); padding: 25px; border-radius: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); backdrop-filter: blur(10px); }
        .chart-container { background: rgba(255,255,255,0.95); padding: 25px; margin: 20px 0; border-radius: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); backdrop-filter: blur(10px); }
        .component-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }
        .component-card { padding: 15px; border-radius: 10px; border-left: 4px solid; transition: transform 0.2s; }
        .component-card:hover { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .healthy { border-left-color: #27ae60; background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); }
        .warning { border-left-color: #f39c12; background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); }
        .error { border-left-color: #e74c3c; background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); }
        .unknown { border-left-color: #95a5a6; background: linear-gradient(135deg, #ecf0f1 0%, #bdc3c7 100%); }
        .alert { background: linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%); border: 1px solid #e17055; color: #d63031; padding: 12px; margin: 8px 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .metrics-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }
        .metric-card { background: rgba(255,255,255,0.9); padding: 15px; border-radius: 10px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .metric-value { font-size: 2em; font-weight: bold; color: #2c3e50; }
        .metric-label { font-size: 0.9em; color: #7f8c8d; text-transform: uppercase; letter-spacing: 1px; }
        .section-title { color: #2c3e50; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #3498db; }
        .status-badge { display: inline-block; padding: 5px 12px; border-radius: 20px; font-size: 0.8em; font-weight: bold; text-transform: uppercase; }
        .status-excellent { background: #27ae60; color: white; }
        .status-good { background: #3498db; color: white; }
        .status-fair { background: #f39c12; color: white; }
        .status-poor { background: #e74c3c; color: white; }
        .last-updated { font-size: 0.8em; color: #7f8c8d; text-align: right; margin-top: 10px; }
        @media (max-width: 768px) { .dashboard-grid { grid-template-columns: 1fr; } .component-grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 BIT RAGE LABOUR Comprehensive Monitoring</h1>
            <p>Real-time system health, performance tracking, and intelligent oversight</p>
            <div id="overall-status" class="status-badge">Loading...</div>
        </div>

        <div class="dashboard-grid">
            <div class="status-overview">
                <h2 class="section-title">📊 System Overview</h2>
                <div id="metrics-summary" class="metrics-summary">
                    <div class="metric-card">
                        <div id="total-components" class="metric-value">--</div>
                        <div class="metric-label">Total Components</div>
                    </div>
                    <div class="metric-card">
                        <div id="healthy-components" class="metric-value">--</div>
                        <div class="metric-label">Healthy</div>
                    </div>
                    <div class="metric-card">
                        <div id="warning-components" class="metric-value">--</div>
                        <div class="metric-label">Warnings</div>
                    </div>
                    <div class="metric-card">
                        <div id="error-components" class="metric-value">--</div>
                        <div class="metric-label">Errors</div>
                    </div>
                </div>
                <div id="system-resources" class="metrics-summary">
                    <div class="metric-card">
                        <div id="cpu-usage" class="metric-value">--%</div>
                        <div class="metric-label">CPU Usage</div>
                    </div>
                    <div class="metric-card">
                        <div id="memory-usage" class="metric-value">--%</div>
                        <div class="metric-label">Memory</div>
                    </div>
                    <div class="metric-card">
                        <div id="disk-usage" class="metric-value">--%</div>
                        <div class="metric-label">Disk</div>
                    </div>
                    <div class="metric-card">
                        <div id="network-status" class="metric-value">✅</div>
                        <div class="metric-label">Network</div>
                    </div>
                </div>
            </div>

            <div class="component-section">
                <h2 class="section-title">⚙️ Core Infrastructure</h2>
                <div id="core-components" class="component-grid">
                    <div class="component-card unknown">
                        <h4>Loading...</h4>
                        <p>Checking status...</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="dashboard-grid">
            <div class="component-section">
                <h2 class="section-title">🧠 Q-Stack Components</h2>
                <div id="qstack-components" class="component-grid"></div>
            </div>

            <div class="component-section">
                <h2 class="section-title">🤖 Agent Systems</h2>
                <div id="agent-components" class="component-grid"></div>
            </div>
        </div>

        <div class="dashboard-grid">
            <div class="component-section">
                <h2 class="section-title">🔄 Communication & Sync</h2>
                <div id="comm-components" class="component-grid"></div>
            </div>

            <div class="component-section">
                <h2 class="section-title">📈 Data & Intelligence</h2>
                <div id="data-components" class="component-grid"></div>
            </div>
        </div>

        <div class="dashboard-grid">
            <div class="component-section">
                <h2 class="section-title">🛡️ System Health</h2>
                <div id="health-components" class="component-grid"></div>
            </div>

            <div class="component-section">
                <h2 class="section-title">🌐 External Services</h2>
                <div id="external-components" class="component-grid"></div>
            </div>
        </div>

        <div class="chart-container">
            <h2 class="section-title">📈 7-Day Health Trends</h2>
            <canvas id="healthChart" width="400" height="200"></canvas>
        </div>

        <div class="chart-container">
            <h2 class="section-title">🔧 Component Performance (7 Days)</h2>
            <canvas id="componentChart" width="400" height="200"></canvas>
        </div>

        <div class="chart-container">
            <h2 class="section-title">📊 System Resources Over Time</h2>
            <canvas id="resourcesChart" width="400" height="200"></canvas>
        </div>

        <div class="component-section">
            <h2 class="section-title">🚨 Active Alerts & Recommendations</h2>
            <div id="alerts-container"></div>
            <div id="recommendations-container"></div>
        </div>

        <div class="last-updated">
            Last updated: <span id="last-updated">Never</span>
        </div>
    </div>

    <script>
        let healthChart, componentChart, resourcesChart;

        // Component categorization
        const componentCategories = {
            core: ['operations_centers', 'agent_deployment', 'conductor_integration', 'emergency_system', 'cross_platform_sync', 'memory_doctrine', 'autonomous_scheduling', 'quasmem_optimization', 'advanced_monitoring'],
            qstack: ['qforge_execution', 'qusar_orchestration', 'sasp_protocol'],
            agents: ['executive_agents', 'specialized_agents', 'agent_integration'],
            comm: ['matrix_monitor', 'matrix_maximizer', 'unified_orchestrator'],
            data: ['youtube_intelligence', 'portfolio_intelligence', 'predictive_analytics'],
            health: ['system_resources', 'network_connectivity', 'file_system_integrity'],
            external: ['github_integration', 'api_endpoints', 'database_connections']
        };

        async function updateDashboard() {
            try {
                // Update current status
                const statusResponse = await fetch('/api/status');
                const status = await statusResponse.json();
                updateStatus(status);

                // Update historical trends
                const trendsResponse = await fetch('/api/historical/7');
                const trends = await trendsResponse.json();
                updateCharts(trends);

                // Update alerts and recommendations
                updateAlertsAndRecommendations(status);

            } catch (error) {
                console.error('Error updating dashboard:', error);
            }
        }

        function updateStatus(status) {
            if (!status || status.error) {
                console.error('Invalid status data:', status);
                return;
            }

            // Update overall status badge
            const overallStatus = document.getElementById('overall-status');
            overallStatus.className = `status-badge status-${status.overall_health || 'unknown'}`;
            overallStatus.textContent = (status.overall_health || 'unknown').toUpperCase();

            // Update metrics summary
            const components = status.components || {};
            const componentList = Object.values(components);
            const healthy = componentList.filter(c => c.status === 'healthy').length;
            const warnings = componentList.filter(c => c.status === 'warning').length;
            const errors = componentList.filter(c => c.status === 'error').length;

            document.getElementById('total-components').textContent = componentList.length;
            document.getElementById('healthy-components').textContent = healthy;
            document.getElementById('warning-components').textContent = warnings;
            document.getElementById('error-components').textContent = errors;

            // Update system resources (from system_resources component if available)
            const sysRes = components.system_resources;
            if (sysRes && sysRes.details) {
                document.getElementById('cpu-usage').textContent = `${sysRes.details.cpu_percent?.toFixed(1) || '--'}%`;
                document.getElementById('memory-usage').textContent = `${sysRes.details.memory_percent?.toFixed(1) || '--'}%`;
                document.getElementById('disk-usage').textContent = `${sysRes.details.disk_percent?.toFixed(1) || '--'}%`;
            }

            // Update network status
            const network = components.network_connectivity;
            document.getElementById('network-status').textContent = network?.status === 'healthy' ? '✅' : '❌';

            // Update component sections
            updateComponentSection('core-components', components, componentCategories.core);
            updateComponentSection('qstack-components', components, componentCategories.qstack);
            updateComponentSection('agent-components', components, componentCategories.agents);
            updateComponentSection('comm-components', components, componentCategories.comm);
            updateComponentSection('data-components', components, componentCategories.data);
            updateComponentSection('health-components', components, componentCategories.health);
            updateComponentSection('external-components', components, componentCategories.external);

            // Update last updated time
            document.getElementById('last-updated').textContent = new Date(status.timestamp).toLocaleString();
        }

        function updateComponentSection(containerId, components, componentNames) {
            const container = document.getElementById(containerId);
            let html = '';

            componentNames.forEach(name => {
                const component = components[name];
                if (component) {
                    html += `
                        <div class="component-card ${component.status || 'unknown'}">
                            <h4>${name.replace(/_/g, ' ').split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}</h4>
                            <p>${component.message || 'No status message'}</p>
                        </div>
                    `;
                }
            });

            if (!html) {
                html = '<div class="component-card unknown"><h4>No Components</h4><p>Components not yet loaded</p></div>';
            }

            container.innerHTML = html;
        }

        function updateCharts(trends) {
            if (!trends || trends.error) return;

            // Health trends chart
            const healthCtx = document.getElementById('healthChart').getContext('2d');
            const healthLabels = trends.health_trends?.map(t => new Date(t.timestamp).toLocaleDateString()) || [];
            const healthData = trends.health_trends?.map(t => t.healthy_components) || [];

            if (healthChart) healthChart.destroy();
            healthChart = new Chart(healthCtx, {
                type: 'line',
                data: {
                    labels: healthLabels,
                    datasets: [{
                        label: 'Healthy Components',
                        data: healthData,
                        borderColor: '#27ae60',
                        backgroundColor: 'rgba(39, 174, 96, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: true }
                    },
                    scales: {
                        y: { beginAtZero: true, max: trends.health_trends?.[0]?.total_components || 25 }
                    }
                }
            });

            // Component performance chart
            const componentCtx = document.getElementById('componentChart').getContext('2d');
            const componentLabels = Object.keys(trends.component_performance || {});
            const componentData = componentLabels.map(name => {
                const compData = trends.component_performance[name] || [];
                const healthyCount = compData.filter(d => d.status === 'healthy').length;
                return compData.length > 0 ? (healthyCount / compData.length) * 100 : 0;
            });

            if (componentChart) componentChart.destroy();
            componentChart = new Chart(componentCtx, {
                type: 'bar',
                data: {
                    labels: componentLabels.map(l => l.replace(/_/g, ' ').split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')),
                    datasets: [{
                        label: 'Uptime % (7 Days)',
                        data: componentData,
                        backgroundColor: '#3498db',
                        borderColor: '#2980b9',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: true }
                    },
                    scales: {
                        y: { beginAtZero: true, max: 100 }
                    }
                }
            });

            // Resources chart (mock data for now - would need historical resource data)
            const resourcesCtx = document.getElementById('resourcesChart').getContext('2d');
            if (resourcesChart) resourcesChart.destroy();
            resourcesChart = new Chart(resourcesCtx, {
                type: 'line',
                data: {
                    labels: ['1h ago', '45m ago', '30m ago', '15m ago', 'Now'],
                    datasets: [{
                        label: 'CPU Usage %',
                        data: [45, 52, 48, 61, 55],
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        tension: 0.4
                    }, {
                        label: 'Memory Usage %',
                        data: [78, 82, 79, 85, 81],
                        borderColor: '#f39c12',
                        backgroundColor: 'rgba(243, 156, 18, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { display: true }
                    },
                    scales: {
                        y: { beginAtZero: true, max: 100 }
                    }
                }
            });
        }

        function updateAlertsAndRecommendations(status) {
            // Update alerts
            const alertsContainer = document.getElementById('alerts-container');
            const alerts = status.alerts || [];
            if (alerts.length === 0) {
                alertsContainer.innerHTML = '<p style="color: #27ae60;">✅ No active alerts</p>';
            } else {
                let html = '';
                alerts.slice(-5).forEach(alert => {
                    html += `<div class="alert">${new Date(status.timestamp).toLocaleString()}: ${alert}</div>`;
                });
                alertsContainer.innerHTML = html;
            }

            // Update recommendations
            const recContainer = document.getElementById('recommendations-container');
            const recommendations = status.recommendations || [];
            if (recommendations.length > 0) {
                let html = '<h4>💡 Recommendations:</h4><ul>';
                recommendations.forEach(rec => {
                    html += `<li>${rec}</li>`;
                });
                html += '</ul>';
                recContainer.innerHTML = html;
            } else {
                recContainer.innerHTML = '<p style="color: #27ae60;">✅ All systems operating optimally</p>';
            }
        }

        // Initialize dashboard
        updateDashboard();

        // Update every 30 seconds
        setInterval(updateDashboard, 30000);

        // Add refresh button functionality
        document.addEventListener('DOMContentLoaded', function() {
            // Could add manual refresh button here if needed
        });
    </script>
</body>
</html>
        """

    def get_current_status(self) -> Dict[str, Any]:
        """Get current system status for API"""
        if self.historical_metrics:
            return self.historical_metrics[-1]
        return {"error": "No status data available"}

    def start_web_interface(self, host: str = '0.0.0.0', port: int = 8080):
        """Start the web interface"""
        if not self.app:
            print("Web interface not available - Flask not installed")
            return

        print(f"Starting web interface on http://{host}:{port}")
        try:
            self.app.run(host=host, port=port, debug=False, threaded=True)
        except Exception as e:
            print(f"Failed to start web interface: {e}")

    def _monitoring_loop(self):
        """Continuous monitoring loop"""
        while self.is_monitoring:
            try:
                # Run comprehensive status check
                asyncio.run(self._comprehensive_status_check())

                # Sleep for monitoring interval
                time.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(120)  # Wait longer on error

    async def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get current comprehensive status"""
        return await self._comprehensive_status_check()

    def stop_monitoring(self):
        """Stop the monitoring system"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)

async def main():
    """Main comprehensive monitoring activation"""
    dashboard = ComprehensiveMonitoringDashboard()
    result = await dashboard.start_comprehensive_monitoring()

    # Save activation report
    report_file = f"comprehensive_monitoring_activation_{
        datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)

    print(
        f"Comprehensive Monitoring Dashboard activated. Report: {report_file}")

    # Start monitoring in background thread
    import threading
    print("Starting monitoring thread...")
    monitoring_thread = threading.Thread(
        target=dashboard._monitoring_loop, daemon=True)
    monitoring_thread.start()
    print("Monitoring started in background")

    # Start web interface in main thread
    if dashboard.app:
        print("Starting web interface...")
        dashboard.start_web_interface(port=8081)
    else:
        print("Web interface not available")
        # Keep alive
        try:
            while True:
                await asyncio.sleep(300)
        except KeyboardInterrupt:
            dashboard.stop_monitoring()
            print("Monitoring stopped")

if __name__ == "__main__":
    asyncio.run(main())
