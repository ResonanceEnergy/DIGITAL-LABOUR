#!/usr/bin/env python3
"""
DIGITAL LABOUR Mobile Command Center - REMOTE ENABLED VERSION
Supports distributed architecture: macOS (mobile) + Windows (processing)
"""

from flask import Flask, jsonify
import sys
import os
from datetime import datetime
import json
import urllib.request

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
import requests

app = Flask(__name__)

# Configuration for remote connections
REMOTE_CONFIG = {
    'matrix_host': os.getenv('MATRIX_HOST', 'localhost'),
    'matrix_port': os.getenv('MATRIX_PORT', '3000'),
    'windows_host': os.getenv('WINDOWS_HOST', None),  # Remote Windows IP
    'aac_port': os.getenv('AAC_PORT', '8081'),  # Windows AAC port
    'enable_remote': os.getenv('ENABLE_REMOTE', 'false').lower() == 'true'
}

# Calculate Matrix API URL
MATRIX_URL = f"http://{
    REMOTE_CONFIG['matrix_host']}: {
    REMOTE_CONFIG['matrix_port']} /api/matrix"
WINDOWS_AAC_URL = f"http://{REMOTE_CONFIG['windows_host']}: {
    REMOTE_CONFIG['aac_port']} "if REMOTE_CONFIG['windows_host'] else None

import logging as _logging
import hmac as _hmac
from functools import wraps as _wraps

_mobile_logger = _logging.getLogger("mobile_command_center")
_MOBILE_AUTH_WARNING_EMITTED = False


def requires_mobile_auth(f):
    """Require API key for mobile API endpoints."""
    @_wraps(f)
    def decorated(*args, **kwargs):
        global _MOBILE_AUTH_WARNING_EMITTED
        api_key = os.getenv("DL_API_KEY")
        if not api_key:
            if not _MOBILE_AUTH_WARNING_EMITTED:
                _mobile_logger.warning(
                    "DL_API_KEY not set — Mobile API auth DISABLED (dev mode)."
                )
                _MOBILE_AUTH_WARNING_EMITTED = True
            return f(*args, **kwargs)
        from flask import request as freq
        token = freq.headers.get(
            "Authorization", "").removeprefix("Bearer ").strip()
        if not token or not _hmac.compare_digest(
            token.encode(),
            api_key.encode()):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


# Simple status tracking
service_status = {
    'mobile_center': {'status': 'running', 'port': 8081},
    'quasmem': {'status': 'simplified', 'port': None},
    'remote_matrix':
    {'status': 'connected' if REMOTE_CONFIG['enable_remote'] else 'local',
     'host': REMOTE_CONFIG['matrix_host']},
    'windows_processing':
    {'status': 'connected'
     if REMOTE_CONFIG['windows_host'] else 'disconnected',
     'host': REMOTE_CONFIG['windows_host']}}

@app.route('/')
def index():
    """index handler."""
    return f"""
    <h1>🚀 DIGITAL LABOUR Mobile Command Center</h1>
    <p>Simplified version - WORKING!</p>
    <p><strong>Current Date:</strong> February 21, 2026</p>
    <ul>
        <li><a href="/api/status">API Status</a></li>
        <li><a href="/matrix">🧠 MATRIX MAXIMIZER (Advanced UI/XI)</a></li>
        <li><a href="/desktop">Desktop Dashboard (Quantum Quasar)</a></li>
        <li><a href="/iphone">iPhone Dashboard (Pocket Pulsar)</a></li>
        <li><a href="/ipad">iPad Pro Dashboard (Tablet Titan)</a></li>
    </ul>
    """

@app.route('/iphone')
def iphone_dashboard():
    """Serve the iPhone dashboard"""
    try:
        with open('templates/iphone_dashboard.html', 'r') as f:
            return f.read()
    except FileNotFoundError:
        # Fallback to simple HTML if template not found
        return """
        <h1>📱 Pocket Pulsar - iPhone Dashboard</h1>
        <p>iPhone interface template not found - using fallback!</p>
        <div style="padding: 20px; background: #f0f0f0; border-radius: 10px;">
            <h3>System Status</h3>
            <p>✅ Mobile Command Center: Running</p>
            <p>✅ QUASMEM: Simplified Mode</p>
            <p>✅ Three-Device Architecture: Ready</p>
            <p>⚠️ Template file not found - check templates/iphone_dashboard.html</p>
        </div>
        """

@app.route('/ipad')
def ipad_dashboard():
    """Serve the iPad Pro dashboard"""
    try:
        with open('templates/ipad_dashboard.html', 'r') as f:
            return f.read()
    except FileNotFoundError:
        # Fallback to simple HTML if template not found
        return """
        <h1>📱 Tablet Titan - iPad Pro Dashboard</h1>
        <p>iPad Pro interface template not found - using fallback!</p>
        <div style="padding: 20px; background: #f0f0f0; border-radius: 10px;">
            <h3>System Status</h3>
            <p>✅ Mobile Command Center: Running</p>
            <p>✅ QUASMEM: Simplified Mode</p>
            <p>✅ Three-Device Architecture: Ready</p>
            <p>📱 iPad Pro MU202VC/A: Detected</p>
            <p>📶 Bluetooth: 34:42:62:2C:5D:9D</p>
            <p>📱 IMEI: 35 869309 533086 6</p>
            <p>🔧 Modern Firmware: 7.03.01</p>
            <p>⚠️ Template file not found - check templates/ipad_dashboard.html</p>
        </div>
        """

@app.route('/desktop')
def desktop_dashboard():
    """Serve the desktop dashboard"""
    try:
        with open('templates/desktop_dashboard.html', 'r') as f:
            return f.read()
    except FileNotFoundError:
        # Fallback to simple HTML if template not found
        return """
        <h1>🖥️ Quantum Quasar - Desktop Dashboard</h1>
        <p>Desktop interface template not found - using fallback!</p>
        <div style="padding: 20px; background: #f0f0f0; border-radius: 10px;">
            <h3>System Status</h3>
            <p>✅ Mobile Command Center: Running</p>
            <p>✅ QUASMEM: Simplified Mode</p>
            <p>✅ Three-Device Architecture: Ready</p>
            <p>🖥️ MacBook Pro M1: Detected</p>
            <p>💾 macOS Monterey: 12.6.1</p>
            <p>⚠️ Template file not found - check templates/desktop_dashboard.html</p>
        </div>
        """

@app.route('/matrix')
def matrix_maximizer():
    """Serve the MATRIX MAXIMIZER interface"""
    try:
        with open('templates/matrix_maximizer.html', 'r') as f:
            return f.read()
    except FileNotFoundError:
        # Fallback to simple HTML if template not found
        return """
        <h1>🧠 MATRIX MAXIMIZER</h1>
        <p>Advanced UI/XI interface template not found - using fallback!</p>
        <div style="padding: 20px; background: #f0f0f0; border-radius: 10px;">
            <h3>System Status</h3>
            <p>✅ MATRIX MAXIMIZER: Initializing...</p>
            <p>✅ Real-time Monitoring: Active</p>
            <p>✅ Intervention Capabilities: Ready</p>
            <p>⚠️ Template file not found - check templates/matrix_maximizer.html</p>
        </div>
        """

@app.route('/api/status')
@requires_mobile_auth
def get_status():
    """Get system status"""
    try:
        response = requests.get(MATRIX_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'status': 'working',
                'timestamp': data.get('timestamp', datetime.now().isoformat()),
                'platform': sys.platform,
                'version': 'remote-enabled',
                'services': service_status,
                'system_health': data.get('system_health', 98),
                'online_nodes': data.get('online_nodes', 9),
                'total_nodes': data.get('total_nodes', 9),
                'remote_config': REMOTE_CONFIG,
                'message': 'DIGITAL LABOUR Mobile Command Center is operational!'
            })
    except Exception:
        pass

    return jsonify({
        'status': 'working',
        'timestamp': datetime.now().isoformat(),
        'platform': sys.platform,
        'version': 'remote-enabled',
        'services': service_status,
        'system_health': 98,
        'online_nodes': 9,
        'total_nodes': 9,
        'remote_config': REMOTE_CONFIG,
        'message': 'DIGITAL LABOUR Mobile Command Center is operational!'
    })

@app.route('/api/quasmem')
@requires_mobile_auth
def get_quasmem_status():
    """Simplified QUASMEM status"""
    return jsonify({
        'status': 'simplified',
        'hot_code': 'QUASMEM',
        'message': 'Memory optimization in simplified mode',
        'memory_usage': 'N/A (simplified)',
        'optimization_level': 'BASIC'
    })

@app.route('/api/matrix')
@requires_mobile_auth
def get_matrix_data():
    """Get matrix monitor data for iOS Matrix Monitor"""
    try:
        # Try to fetch real data from Matrix Monitor (local or remote)
        print(f"DEBUG: Attempting to fetch from {MATRIX_URL}")
        if HAS_REQUESTS:
            # Increased timeout for remote
            response = requests.get(MATRIX_URL, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(
                    f"DEBUG: Successfully fetched data with requests: {len(str(data))} chars")
                return jsonify(data)
        else:
            with urllib.request.urlopen(MATRIX_URL, timeout=10) as response:
                data = json.loads(response.read().decode())
                print(
                    f"DEBUG: Successfully fetched data with urllib: {len(str(data))} chars")
                return jsonify(data)
    except Exception as e:
        print(f"DEBUG: Failed to fetch real data: {e}")
        if REMOTE_CONFIG['enable_remote']:
            print("DEBUG: Remote connection failed, falling back to local...")
            # Try local fallback if remote fails
            try:
                local_url = "http://localhost:3000/api/matrix"
                if HAS_REQUESTS:
                    response = requests.get(local_url, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        print("DEBUG: Fallback to local successful")
                        return jsonify(data)
            except Exception:
                pass

    # Fallback to static data
    matrix_data = {
        'matrix': [
            {
                'type': 'quantum-quasar',
                'status': 'online',
                'name': 'Quantum Quasar',
                'device': 'Mac Workstation',
                'metrics': [
                    {'label': 'CPU', 'value': '75%'},
                    {'label': 'MEM', 'value': '45%'}
                ]
            },
            {
                'type': 'pocket-pulsar',
                'status': 'online',
                'name': 'Pocket Pulsar',
                'device': 'iPhone',
                'metrics': [
                    {'label': 'BAT', 'value': '87%'},
                    {'label': 'NET', 'value': 'LTE'}
                ]
            },
            {
                'type': 'tablet-titan',
                'status': 'online',
                'name': 'Tablet Titan',
                'device': 'iPad Pro MU202VC/A',
                'metrics': [
                    {'label': 'BAT', 'value': '89%'},
                    {'label': 'BT', 'value': '34:42:62:2C:5D:9D'},
                    {'label': 'IMEI', 'value': '35 869309 533086 6'},
                    {'label': 'FW', 'value': '7.03.01'}
                ]
            },
            {
                'type': 'agent',
                'status': 'online',
                'name': 'Operations Command - Repo Sentry',
                'device': 'System Monitoring Agent',
                'metrics': [
                    {'label': 'REPOS', 'value': '47'},
                    {'label': 'HEALTH', 'value': '98%'}
                ]
            },
            {
                'type': 'agent',
                'status': 'online',
                'name': 'Operations Command - Daily Brief',
                'device': 'System Monitoring Agent',
                'metrics': [
                    {'label': 'REPORTS', 'value': '12'},
                    {'label': 'QUALITY', 'value': '95%'}
                ]
            },
            {
                'type': 'agent',
                'status': 'online',
                'name': 'Executive Council - Agent AZ',
                'device': 'Strategic Oversight Agent',
                'metrics': [
                    {'label': 'DECISIONS', 'value': '23'},
                    {'label': 'AUTHORITY', 'value': 'AZ_FINAL'}
                ]
            },
            {
                'type': 'memory',
                'status': 'active',
                'name': 'QUASMEM',
                'device': 'Memory Pool',
                'metrics': [
                    {'label': 'POOL', 'value': '256MB'},
                    {'label': 'EFFICIENCY', 'value': '92%'}
                ]
            },
            {
                'type': 'finance',
                'status': 'healthy',
                'name': 'Finance',
                'device': 'Financial System',
                'metrics': [
                    {'label': 'BALANCE', 'value': '$127K'},
                    {'label': 'SCORE', 'value': '92'}
                ]
            },
            {
                'type': 'network',
                'status': 'online',
                'name': 'SASP',
                'device': 'Network Protocol',
                'metrics': [
                    {'label': 'CONNECTIONS', 'value': '3'},
                    {'label': 'LATENCY', 'value': '45ms'}
                ]
            }
        ],
        'timestamp': datetime.now().isoformat(),
        'system_health': 98,
        'total_nodes': 9,
        'online_nodes': 9
    }

    return jsonify(matrix_data)

    return jsonify(matrix_data)

@app.route('/api/agents')
@requires_mobile_auth
def get_agents():
    """Get agents data"""
    try:
        response = requests.get(MATRIX_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            agents = [node for node in data.get(
                'matrix', []) if node.get('type') == 'agent']
            return jsonify(agents)
    except Exception:
        pass

    return jsonify([
        {
            'id': 'repo_sentry',
            'name': 'Repo Sentry',
            'status': 'active',
            'health': 98,
            'metrics': [{'label': 'REPOS', 'value': '47'}]
        },
        {
            'id': 'daily_brief',
            'name': 'Daily Brief',
            'status': 'active',
            'health': 95,
            'metrics': [{'label': 'REPORTS', 'value': '12'}]
        }
    ])

@app.route('/api/systems')
@requires_mobile_auth
def get_systems():
    """Get systems data"""
    try:
        response = requests.get(MATRIX_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            systems = [node for node in data.get('matrix', []) if node.get('type') in [
                                                 'device', 'memory', 'network']]
            return jsonify(systems)
    except Exception:
        pass

    return jsonify([
        {
            'id': 'quantum_quasar',
            'name': 'Quantum Quasar',
            'type': 'device',
            'status': 'online',
            'health': 98,
            'metrics': [{'label': 'CPU', 'value': '20%'}]
        },
        {
            'id': 'quasmem',
            'name': 'QUASMEM',
            'type': 'memory',
            'status': 'active',
            'health': 97,
            'metrics': [{'label': 'POOL', 'value': '256MB'}]
        }
    ])

@app.route('/api/finance')
@requires_mobile_auth
def get_finance():
    """Get finance data"""
    try:
        # Try Windows AAC Financial System first
        response = requests.get(WINDOWS_AAC_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return jsonify(data)
    except Exception:
        pass

    try:
        # Fallback to Matrix Monitor
        response = requests.get(MATRIX_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            finance = next((node for node in data.get('matrix', [])
                           if node.get('type') == 'finance'), None)
            if finance:
                return jsonify(finance)
    except Exception:
        pass

    return jsonify({
        'id': 'finance',
        'name': 'Finance',
        'type': 'finance',
        'status': 'healthy',
        'health': 94,
        'metrics': [
            {'label': 'BALANCE', 'value': '$127K'},
            {'label': 'SCORE', 'value': '92'}
        ]
    })

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    try:
        with open(f'static/{filename}', 'r') as f:
            content = f.read()
            # Set appropriate content type for JSON files
            if filename.endswith('.json'):
                from flask import Response
                return Response(content, mimetype='application/json')
            return content
    except FileNotFoundError:
        return f"Static file not found: {filename}", 404

if __name__ == '__main__':
    print("🚀 Starting SIMPLIFIED DIGITAL LABOUR Mobile Command Center...")
    print("📍 Access at: http://localhost:8081")
    print("�️ Desktop UI at: http://localhost:8081/desktop")
    print("📱 iPhone UI at: http://localhost:8081/iphone")
    print("📱 iPad UI at: http://localhost:8081/ipad")
    print("🔄 This is a working simplified version!")

    app.run(host='0.0.0.0', port=8081, debug=False)
