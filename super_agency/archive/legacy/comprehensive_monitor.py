#!/usr/bin/env python3
"""
DIGITAL LABOUR COMPREHENSIVE MONITORING DASHBOARD
Real-time monitoring of all components and fail-safe systems
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import psutil
from flask import Flask, jsonify, render_template_string, request

# Add parent directory to path
parent_dir = Path(__file__).parent
sys.path.insert(0, str(parent_dir))

try:
    from fail_safe_orchestrator import FailSafeOrchestrator
    from watchdog_service import WatchdogService
except ImportError:
    # Handle case where modules aren't available yet
    FailSafeOrchestrator = None
    WatchdogService = None

class ComprehensiveMonitor:
    """Comprehensive monitoring dashboard for the entire DIGITAL LABOUR"""

    def __init__(self):
        self.app = Flask(__name__)
        self.workspace_dir = Path(__file__).parent
        self.setup_routes()

    def setup_routes(self):
        """Setup Flask routes"""

        @self.app.route('/')
        def dashboard():
            """Main monitoring dashboard"""
            return render_template_string(self.get_dashboard_html())

        @self.app.route('/api/status')
        def api_status():
            """API endpoint for system status"""
            return jsonify(self.get_system_status())

        @self.app.route('/api/logs/<log_type>')
        def api_logs(log_type):
            """API endpoint for logs"""
            return jsonify(self.get_recent_logs(log_type))

        @self.app.route('/api/alerts')
        def api_alerts():
            """API endpoint for alerts"""
            return jsonify(self.get_recent_alerts())

    def get_system_status(self) -> dict:
        """Get comprehensive system status"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=0.5),
                "memory": {
                    "total": psutil.virtual_memory().total,
                    "available": psutil.virtual_memory().available,
                    "percent": psutil.virtual_memory().percent
                },
                "disk": {
                    "total": psutil.disk_usage('/').total,
                    "free": psutil.disk_usage('/').free,
                    "percent": psutil.disk_usage('/').percent
                }
            },
            "components": {},
            "fail_safe": {},
            "watchdog": {}
        }

        # Check component processes
        component_processes = {
            'bit_rage_labour': ['bit_rage_labour'],
            'quantum_qforge': ['qforge', 'qforge_main'],
            'quantum_qusar': ['qusar', 'qusar_main'],
            'matrix_monitor': ['flask_matrix_monitor'],
            'matrix_maximizer': ['streamlit_matrix_maximizer'],
            'agent_optimus': ['agent_optimus'],
            'agent_gasket': ['agent_gasket'],
            'az_prime': ['az_prime', 'az_prime_main'],
            'helix': ['helix', 'helix_main']
        }

        for component, process_names in component_processes.items():
            running_count = 0
            total_processes = 0

            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc_name = proc.info['name'].lower()
                    if any(pn.lower() in proc_name for pn in process_names):
                        running_count += 1
                        total_processes += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            status["components"][component] = {
                "running": running_count > 0,
                "process_count": running_count,
                "status": "healthy" if running_count > 0 else "down"
            }

        # Check fail-safe orchestrator
        orchestrator_running = False
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'fail_safe_orchestrator.py' in str(proc.info.get('cmdline', [])):
                    orchestrator_running = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        status["fail_safe"] = {
            "orchestrator_running": orchestrator_running,
            "status": "active" if orchestrator_running else "inactive"
        }

        # Check watchdog service
        watchdog_running = False
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'watchdog_service.py' in str(proc.info.get('cmdline', [])):
                    watchdog_running = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        status["watchdog"] = {
            "service_running": watchdog_running,
            "status": "protecting" if watchdog_running else "inactive"
        }

        return status

    def get_recent_logs(self, log_type: str, lines: int = 50) -> list:
        """Get recent log entries"""
        log_files = {
            'watchdog': 'watchdog_service.log',
            'orchestrator': 'fail_safe_orchestrator.log',
            'alerts': 'alerts.log',
            'critical': 'critical_alerts.log'
        }

        if log_type not in log_files:
            return []

        log_file = self.workspace_dir / log_files[log_type]
        if not log_file.exists():
            return []

        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines_content = f.readlines()[-lines:]
                return [line.strip() for line in lines_content]
        except Exception as e:
            return [f"Error reading log: {e}"]

    def get_recent_alerts(self, hours: int = 24) -> list:
        """Get recent alerts"""
        alerts = []

        # Check alerts.log
        alerts_file = self.workspace_dir / "alerts.log"
        if alerts_file.exists():
            try:
                with open(alerts_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        try:
                            alert = json.loads(line.strip())
                            alert_time = datetime.fromisoformat(alert['timestamp'])
                            if datetime.now() - alert_time < timedelta(hours=hours):
                                alerts.append(alert)
                        except:
                            continue
            except Exception as e:
                alerts.append({"error": f"Error reading alerts: {e}"})

        # Check critical alerts
        critical_file = self.workspace_dir / "critical_alerts.log"
        if critical_file.exists():
            try:
                with open(critical_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        try:
                            alert = json.loads(line.strip())
                            alert_time = datetime.fromisoformat(alert['timestamp'])
                            if datetime.now() - alert_time < timedelta(hours=hours):
                                alert['level'] = 'CRITICAL'
                                alerts.append(alert)
                        except:
                            continue
            except Exception as e:
                alerts.append({"error": f"Error reading critical alerts: {e}"})

        # Sort by timestamp, most recent first
        alerts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return alerts[:100]  # Limit to 100 most recent

    def get_dashboard_html(self) -> str:
        """Get the HTML for the monitoring dashboard"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="30">
    <title>🚀 DIGITAL LABOUR COMPREHENSIVE MONITOR</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            color: #ffffff;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #00d4ff, #ff6b6b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .status-card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .status-card h3 {
            margin-top: 0;
            color: #00d4ff;
            border-bottom: 2px solid #00d4ff;
            padding-bottom: 10px;
        }
        .component-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
        }
        .component {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 5px;
            margin-bottom: 5px;
        }
        .component-name {
            font-weight: bold;
        }
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }
        .status-healthy { background-color: #00ff00; }
        .status-down { background-color: #ff0000; }
        .status-warning { background-color: #ffff00; }
        .status-active { background-color: #00d4ff; }
        .status-inactive { background-color: #666; }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .metric {
            text-align: center;
            padding: 15px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
        }
        .metric-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #00ff00;
        }
        .metric-label {
            font-size: 0.9em;
            color: #ccc;
            margin-top: 5px;
        }
        .alerts-section {
            margin-top: 30px;
        }
        .alerts-list {
            max-height: 300px;
            overflow-y: auto;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 15px;
        }
        .alert {
            padding: 8px 12px;
            margin-bottom: 8px;
            border-radius: 5px;
            border-left: 4px solid;
        }
        .alert-critical {
            background: rgba(255, 0, 0, 0.2);
            border-left-color: #ff0000;
        }
        .alert-warning {
            background: rgba(255, 255, 0, 0.2);
            border-left-color: #ffff00;
        }
        .alert-info {
            background: rgba(0, 212, 255, 0.2);
            border-left-color: #00d4ff;
        }
        .timestamp {
            font-size: 0.8em;
            color: #ccc;
        }
        .last-updated {
            text-align: center;
            margin-top: 20px;
            color: #ccc;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 DIGITAL LABOUR COMPREHENSIVE MONITOR</h1>
            <p>24/7/365 Fail-Safe System Status</p>
        </div>

        <div class="status-grid">
            <div class="status-card">
                <h3>🛡️ Fail-Safe Systems</h3>
                <div id="fail-safe-status">Loading...</div>
            </div>

            <div class="status-card">
                <h3>⚙️ Agency Components</h3>
                <div id="components-status">Loading...</div>
            </div>

            <div class="status-card">
                <h3>🖥️ System Resources</h3>
                <div id="system-metrics">Loading...</div>
            </div>
        </div>

        <div class="alerts-section">
            <h2>🚨 Recent Alerts</h2>
            <div class="alerts-list" id="alerts-list">Loading...</div>
        </div>

        <div class="last-updated" id="last-updated">
            Last updated: <span id="update-time">Never</span>
        </div>
    </div>

    <script>
        async function updateDashboard() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();

                updateFailSafeStatus(data);
                updateComponentsStatus(data);
                updateSystemMetrics(data);
                updateAlerts();

                document.getElementById('update-time').textContent = new Date().toLocaleString();
            } catch (error) {
                console.error('Error updating dashboard:', error);
            }
        }

        function updateFailSafeStatus(data) {
            const status = data.fail_safe;
            const watchdog = data.watchdog;

            let html = `
                <div class="component">
                    <span class="component-name">Fail-Safe Orchestrator</span>
                    <span class="status-indicator ${status.orchestrator_running ? 'status-active' : 'status-inactive'}"></span>
                    <span>${status.status.toUpperCase()}</span>
                </div>
                <div class="component">
                    <span class="component-name">Watchdog Service</span>
                    <span class="status-indicator ${watchdog.service_running ? 'status-active' : 'status-inactive'}"></span>
                    <span>${watchdog.status.toUpperCase()}</span>
                </div>
            `;

            document.getElementById('fail-safe-status').innerHTML = html;
        }

        function updateComponentsStatus(data) {
            let html = '';

            for (const [component, info] of Object.entries(data.components)) {
                const displayName = component.replace(/_/g, ' ').replace(/\\b\\w/g, l => l.toUpperCase());
                const statusClass = info.running ? 'status-healthy' : 'status-down';

                html += `
                    <div class="component">
                        <span class="component-name">${displayName}</span>
                        <span class="status-indicator ${statusClass}"></span>
                        <span>${info.status.toUpperCase()}</span>
                        <span>(${info.process_count} proc)</span>
                    </div>
                `;
            }

            document.getElementById('components-status').innerHTML = html;
        }

        function updateSystemMetrics(data) {
            const sys = data.system;

            let html = `
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-value">${sys.cpu_percent.toFixed(1)}%</div>
                        <div class="metric-label">CPU Usage</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${sys.memory.percent.toFixed(1)}%</div>
                        <div class="metric-label">Memory Usage</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${sys.disk.percent.toFixed(1)}%</div>
                        <div class="metric-label">Disk Usage</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${(sys.memory.available / 1024 / 1024 / 1024).toFixed(1)}GB</div>
                        <div class="metric-label">Memory Free</div>
                    </div>
                </div>
            `;

            document.getElementById('system-metrics').innerHTML = html;
        }

        async function updateAlerts() {
            try {
                const response = await fetch('/api/alerts');
                const alerts = await response.json();

                let html = '';
                for (const alert of alerts.slice(0, 20)) {  // Show last 20 alerts
                    const level = alert.level || alert.severity || 'info';
                    const levelClass = level.toLowerCase().includes('critical') ? 'alert-critical' :
                                     level.toLowerCase().includes('warning') || level === 'yellow' ? 'alert-warning' :
                                     'alert-info';

                    html += `
                        <div class="alert ${levelClass}">
                            <strong>${alert.level || alert.severity || 'INFO'}</strong>: ${alert.message}
                            <div class="timestamp">${alert.timestamp}</div>
                        </div>
                    `;
                }

                if (alerts.length === 0) {
                    html = '<div class="alert alert-info">No recent alerts</div>';
                }

                document.getElementById('alerts-list').innerHTML = html;
            } catch (error) {
                console.error('Error updating alerts:', error);
            }
        }

        // Update dashboard immediately and then every 30 seconds
        updateDashboard();
        setInterval(updateDashboard, 30000);
    </script>
</body>
</html>
        """

def run_monitoring_dashboard(port: int = 8601):
    """Run the comprehensive monitoring dashboard"""
    monitor = ComprehensiveMonitor()
    print(f"📊 Starting Comprehensive Monitoring Dashboard on port {port}")
    print(f"🌐 Open http://localhost:{port} in your browser to monitor the system")
    monitor.app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8601
    run_monitoring_dashboard(port)
