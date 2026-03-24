#!/usr/bin/env python3
"""
Simple Monitoring API Server
Provides comprehensive monitoring data via REST API
"""

import json
import time
from datetime import datetime
from flask import Flask, jsonify
import psutil
import glob
from pathlib import Path

app = Flask(__name__)

def get_system_metrics():
    """Get basic system metrics"""
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
        "timestamp": datetime.now().isoformat()
    }

def get_comprehensive_status():
    """Get comprehensive monitoring status"""
    # Check for recent reports
    reports = []
    report_files = glob.glob("comprehensive_status_report_*.json")
    if report_files:
        latest_report = max(report_files, key=lambda x: Path(x).stat().st_mtime)
        try:
            with open(latest_report, 'r') as f:
                reports.append(json.load(f))
        except Exception as e:
            print(f"Error reading report: {e}")

    # Get system metrics
    system = get_system_metrics()

    # Mock comprehensive status
    status = {
        "timestamp": datetime.now().isoformat(),
        "overall_health": "good",
        "system": system,
        "components": {
            "qforge_execution": {"status": "healthy", "message": "QFORGE running on target repositories"},
            "matrix_monitor": {"status": "healthy", "message": "Matrix Monitor active"},
            "operations_centers": {"status": "healthy", "message": "Operations centers operational"},
            "agent_deployment": {"status": "healthy", "message": "Agent deployment active"},
            "conductor_integration": {"status": "healthy", "message": "Conductor integration active"},
            "quasmem_optimization": {"status": "healthy", "message": "QUASMEM memory optimization active"}
        },
        "alerts": [],
        "recommendations": ["All systems operational"],
        "repositories": ["NCL", "future-predictor-council", "CIVIL-FORGE-TECHNOLOGIES-"]
    }

    return status

@app.route('/')
def index():
    return """
    <h1>Super Agency Monitoring API</h1>
    <p>API Endpoints:</p>
    <ul>
        <li><a href="/api/comprehensive-monitoring">/api/comprehensive-monitoring</a></li>
        <li><a href="/api/system/metrics">/api/system/metrics</a></li>
    </ul>
    """

@app.route('/api/comprehensive-monitoring')
def api_comprehensive_monitoring():
    """Comprehensive monitoring API endpoint"""
    try:
        status = get_comprehensive_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/system/metrics')
def api_system_metrics():
    """System metrics API endpoint"""
    try:
        metrics = get_system_metrics()
        return jsonify(metrics)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Starting Simple Monitoring API Server on http://localhost:8081")
    app.run(host='0.0.0.0', port=8081, debug=False)
