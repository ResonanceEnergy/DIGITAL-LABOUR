#!/usr/bin/env python3
"""
BIT RAGE LABOUR HEALTH CHECK SYSTEM
Provides standardized health check endpoints for all agency components
"""

import json
import psutil
import time
from datetime import datetime
from flask import Flask, jsonify, request
from typing import Dict, Any, Optional

class HealthCheck:
    """Standardized health check system for agency components"""

    def __init__(self, component_name: str, version: str = "1.0"):
        self.component_name = component_name
        self.version = version
        self.start_time = time.time()
        self.last_activity = time.time()

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = time.time()

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        current_time = time.time()

        return {
            "component": self.component_name,
            "version": self.version,
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": int(current_time - self.start_time),
            "last_activity_seconds": int(current_time - self.last_activity),
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent
            }
        }

    def get_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health information including process info"""
        status = self.get_health_status()

        try:
            process = psutil.Process()
            status["process"] = {
                "pid": process.pid,
                "cpu_percent": process.cpu_percent(),
                "memory_info": {
                    "rss": process.memory_info().rss,
                    "vms": process.memory_info().vms,
                    "percent": process.memory_percent()
                },
                "num_threads": process.num_threads(),
                "num_fds": len(process.open_files()) if hasattr(process, 'open_files') else None
            }
        except Exception as e:
            status["process"] = {"error": str(e)}

        return status

def create_health_app(health_check: HealthCheck, port: int = 8000) -> Flask:
    """Create a Flask app with health check endpoints"""

    app = Flask(__name__)

    @app.route('/health')
    def health():
        """Basic health check endpoint"""
        return jsonify(health_check.get_health_status())

    @app.route('/health/detailed')
    def detailed_health():
        """Detailed health check endpoint"""
        return jsonify(health_check.get_detailed_health())

    @app.route('/health/ping')
    def ping():
        """Simple ping endpoint"""
        health_check.update_activity()
        return jsonify({"status": "pong", "timestamp": datetime.now().isoformat()})

    @app.route('/health/metrics')
    def metrics():
        """Prometheus-style metrics endpoint"""
        status = health_check.get_health_status()

        metrics = f"""# HELP bit_rage_labour_component_health Component health status
# TYPE bit_rage_labour_component_health gauge
bit_rage_labour_component_health{{component="{status['component']}"}} {1 if status['status'] == 'healthy' else 0}

# HELP bit_rage_labour_uptime_seconds Component uptime in seconds
# TYPE bit_rage_labour_uptime_seconds counter
bit_rage_labour_uptime_seconds{{component="{status['component']}"}} {status['uptime_seconds']}

# HELP bit_rage_labour_cpu_percent CPU usage percentage
# TYPE bit_rage_labour_cpu_percent gauge
bit_rage_labour_cpu_percent{{component="{status['component']}"}} {status['system']['cpu_percent']}

# HELP bit_rage_labour_memory_percent Memory usage percentage
# TYPE bit_rage_labour_memory_percent gauge
bit_rage_labour_memory_percent{{component="{status['component']}"}} {status['system']['memory_percent']}
"""

        return metrics, 200, {'Content-Type': 'text/plain; charset=utf-8'}

    return app

def run_health_server(health_check: HealthCheck, port: int = 8000, host: str = '0.0.0.0'):
    """Run the health check server"""
    app = create_health_app(health_check, port)
    print(f"🏥 Starting health check server for {health_check.component_name} on port {port}")
    app.run(host=host, port=port, debug=False)

# Example usage for individual components
if __name__ == "__main__":
    import sys

    component_name = sys.argv[1] if len(sys.argv) > 1 else "unknown_component"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000

    health = HealthCheck(component_name)
    run_health_server(health, port)
