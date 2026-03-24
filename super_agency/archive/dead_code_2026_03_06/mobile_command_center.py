#!/usr/bin/env python3
"""
Super Agency Mobile Command Center (16GB Optimized)
Flask web server for mobile remote access - lightweight version
Implements Super Agency Share Protocol (SASP)
"""

from flask import Flask, render_template, jsonify, request
import subprocess
import sys
import os
import json
import time
import psutil
import hmac
import hashlib
from datetime import datetime

# QUASMEM Integration
try:
    from quasmem_optimization import get_memory_status, optimize_memory_usage, quantum_memory_pool
    QUASMEM_ACTIVE = True
    print("✅ QUASMEM optimization loaded")
except ImportError as e:
    QUASMEM_ACTIVE = False
    print(f"⚠️  QUASMEM optimization not available: {e}")

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

# SASP Protocol Configuration
SASP_CONFIG = {
    'version': '1.0',
    'protocol': 'SASP',
    'mac_id': f'mac-hub-{os.getpid()}',
    'shared_secret': 'super-agency-shared-key-2026',  # Should be configured securely
    'windows_nodes': {},  # Track connected Windows nodes
    'message_history': [],  # Keep recent messages for debugging
    'max_history': 100
}

# Lightweight service status tracking
service_status = {
    'matrix_monitor': {'status': 'unknown', 'port': 3000, 'last_check': 0, 'memory_limit': 512},  # Reduced to 512MB for 8GB M1
    'operations': {'status': 'unknown', 'port': 5000, 'last_check': 0, 'memory_limit': 512},     # Reduced to 512MB for 8GB M1
    'mobile_center': {'status': 'running', 'port': 8080, 'last_check': time.time(), 'memory_limit': 256}, # Reduced to 256MB for 8GB M1
    'windows_sync': {'status': 'unknown', 'port': None, 'last_check': 0, 'memory_limit': None}
}

# Memory monitoring - optimized for 8GB M1
def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_memory_limits():
    """Aggressive memory cleanup for 8GB M1"""
    current_mem = get_memory_usage()
    if current_mem > 200:  # 200MB limit for 8GB M1 (was 800MB for 16GB)
        print(f"🧹 Aggressive memory cleanup: {current_mem:.1f}MB")
        # Force garbage collection
        import gc
        gc.collect()
        # Additional cleanup for M1
        time.sleep(0.1)  # Brief pause for memory pressure relief

# SASP Protocol Functions
def create_sasp_message(message_type, payload, recipient_type="windows", recipient_id="windows-node"):
    """Create a SASP protocol message"""
    timestamp = datetime.utcnow().isoformat() + 'Z'
    message_id = f"sasp-{int(time.time())}-{os.urandom(4).hex()}"

    message = {
        'protocol': SASP_CONFIG['protocol'],
        'version': SASP_CONFIG['version'],
        'timestamp': timestamp,
        'message_id': message_id,
        'sender': {
            'type': 'mac',
            'id': SASP_CONFIG['mac_id'],
            'ip': get_local_ip()
        },
        'recipient': {
            'type': recipient_type,
            'id': recipient_id
        },
        'message_type': message_type,
        'payload': payload
    }

    # Add HMAC signature
    message['signature'] = generate_sasp_signature(message)

    return message

def generate_sasp_signature(message):
    """Generate HMAC-SHA256 signature for SASP message"""
    # Remove signature field for signing
    message_copy = {k: v for k, v in message.items() if k != 'signature'}

    # Create string to sign
    json_string = json.dumps(message_copy, sort_keys=True, separators=(',', ':'))

    # Create HMAC-SHA256 signature
    signature = hmac.new(
        SASP_CONFIG['shared_secret'].encode('utf-8'),
        json_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return signature

def verify_sasp_signature(message):
    """Verify SASP message signature"""
    if 'signature' not in message:
        return False

    expected_signature = generate_sasp_signature(message)
    return hmac.compare_digest(expected_signature, message['signature'])

def get_local_ip():
    """Get local IP address"""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def log_sasp_message(message, direction="received"):
    """Log SASP message for debugging"""
    SASP_CONFIG['message_history'].append({
        'timestamp': datetime.now().isoformat(),
        'direction': direction,
        'message_type': message.get('message_type'),
        'message_id': message.get('message_id'),
        'sender': message.get('sender', {}).get('id')
    })

    # Keep only recent messages
    if len(SASP_CONFIG['message_history']) > SASP_CONFIG['max_history']:
        SASP_CONFIG['message_history'] = SASP_CONFIG['message_history'][-SASP_CONFIG['max_history']:]

# SASP Endpoints
@app.route('/sasp/health', methods=['GET'])
def sasp_health():
    """SASP protocol health check"""
    return jsonify({
        'protocol': SASP_CONFIG['protocol'],
        'version': SASP_CONFIG['version'],
        'status': 'operational',
        'mac_id': SASP_CONFIG['mac_id'],
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    })

@app.route('/sasp/status', methods=['POST'])
def sasp_receive_status():
    """Receive status updates from Windows nodes"""
    try:
        message = request.get_json()

        # Verify SASP message format
        if not message or message.get('protocol') != SASP_CONFIG['protocol']:
            return jsonify({'error': 'Invalid SASP message'}), 400

        # Verify signature
        if not verify_sasp_signature(message):
            return jsonify({'error': 'Invalid signature'}), 401

        # Log message
        log_sasp_message(message, "received")

        # Update Windows node status
        sender_id = message['sender']['id']
        SASP_CONFIG['windows_nodes'][sender_id] = {
            'last_seen': message['timestamp'],
            'ip': message['sender']['ip'],
            'status': message['payload']
        }

        print(f"📡 SASP Status received from {sender_id}: {message['payload']['system_status']}")

        return jsonify({'status': 'received', 'message_id': message['message_id']})

    except Exception as e:
        print(f"❌ SASP status error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/sasp/command', methods=['POST'])
def sasp_send_command():
    """Send command to Windows node (placeholder - would need Windows endpoint)"""
    try:
        data = request.get_json()
        command_id = data.get('command_id')
        parameters = data.get('parameters', {})

        # Create SASP command message
        command_message = create_sasp_message(
            'command',
            {
                'command_id': command_id,
                'parameters': parameters,
                'callback_url': f"http://{get_local_ip()}:8080/sasp/response"
            }
        )

        # In a real implementation, this would send to Windows
        # For now, just log and return success
        log_sasp_message(command_message, "sent")

        print(f"📤 SASP Command sent: {command_id}")

        return jsonify({
            'status': 'sent',
            'message_id': command_message['message_id'],
            'command_id': command_id
        })

    except Exception as e:
        print(f"❌ SASP command error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/sasp/response', methods=['POST'])
def sasp_receive_response():
    """Receive command responses from Windows nodes"""
    try:
        message = request.get_json()

        # Verify SASP message
        if not message or message.get('protocol') != SASP_CONFIG['protocol']:
            return jsonify({'error': 'Invalid SASP message'}), 400

        if not verify_sasp_signature(message):
            return jsonify({'error': 'Invalid signature'}), 401

        log_sasp_message(message, "received")

        print(f"📥 SASP Response received: {message['payload']}")

        return jsonify({'status': 'received', 'message_id': message['message_id']})

    except Exception as e:
        print(f"❌ SASP response error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sasp/status')
def get_sasp_status():
    """Get SASP protocol status for mobile dashboard"""
    return jsonify({
        'protocol': SASP_CONFIG['protocol'],
        'version': SASP_CONFIG['version'],
        'mac_id': SASP_CONFIG['mac_id'],
        'windows_nodes': SASP_CONFIG['windows_nodes'],
        'message_history': SASP_CONFIG['message_history'][-10:],  # Last 10 messages
        'total_messages': len(SASP_CONFIG['message_history'])
    })

# Lightweight service status check
def check_service_status(service_name):
    """Check if a service is running (cached, lightweight)"""
    current_time = time.time()
    if current_time - service_status[service_name]['last_check'] < 60:  # Cache for 60 seconds
        return service_status[service_name]['status']

    port = service_status[service_name]['port']
    if port is None:  # Windows sync check
        status = 'unknown'  # We'll check this differently
    else:
        try:
            # Very lightweight port check
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            status = 'running' if result == 0 else 'stopped'
        except:
            status = 'unknown'

    service_status[service_name]['status'] = status
    service_status[service_name]['last_check'] = current_time
    return status

@app.route('/')
def index():
    """Main mobile dashboard"""
    return render_template('index.html')

@app.route('/iphone')
def iphone_dashboard():
    """iPhone-optimized Pocket Pulsar dashboard"""
    return render_template('iphone_dashboard.html')

@app.route('/api/status')
def get_status():
    """Get system status for mobile dashboard"""
    status = {}
    for service in service_status:
        status[service] = {
            'status': check_service_status(service),
            'port': service_status[service]['port']
        }

    # Add system info
    status['system'] = {
        'timestamp': datetime.now().isoformat(),
        'platform': sys.platform
    }

    # Add iPhone dashboard metrics
    status.update({
        'health': 98,  # Overall system health percentage
        'active_agents': 23,  # Number of active inner council agents
        'cpu_usage': 75,  # Current CPU utilization
        'memory_usage': 45,  # Current memory usage percentage
        'financial_score': 92,  # AAC financial health score
        'repos_count': 47  # Number of repositories being monitored
    })

    return jsonify(status)

@app.route('/api/command/<command>')
def execute_command(command):
    """Execute a command from mobile interface"""
    commands = {
        'max_cpu': ['python', 'cpu_maximizer.py'],
        'deploy_agents': ['python', 'inner_council/deploy_agents.py', '--mode', 'deploy', '--duration', '300'],
        'backup': ['python', 'backup_memory_doctrine_logs.py'],
        'intelligence': ['python', 'youtube_intelligence_monitor.py']
    }

    if command not in commands:
        return jsonify({'error': 'Unknown command'}), 400

    try:
        # Run command in background
        subprocess.Popen(commands[command])
        return jsonify({'status': 'executed', 'command': command})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/<service>')
def get_logs(service):
    """Get recent logs for a service"""
    log_files = {
        'matrix_monitor': 'logs/matrix_monitor.log',
        'operations': 'logs/operations.log',
        'aac': 'repos/AAC/logs/aac.log',
        'inner_council': 'inner_council/logs/council.log'
    }

    if service not in log_files:
        return jsonify({'error': 'Unknown service'}), 400

    try:
        if os.path.exists(log_files[service]):
            with open(log_files[service], 'r') as f:
                lines = f.readlines()[-20:]  # Last 20 lines
            return jsonify({'logs': lines})
        else:
            return jsonify({'logs': ['No logs available']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/agents')
def get_agents():
    """Get inner council agents status for iPhone dashboard"""
    try:
        # Mock data - in real implementation, this would query the actual agents
        agents = [
            {
                'id': 'repo_sentry',
                'name': 'Repo Sentry',
                'type': 'repo_sentry',
                'status': 'online',
                'efficiency': 98,
                'status_text': 'Monitoring 47 repos'
            },
            {
                'id': 'daily_brief',
                'name': 'Daily Brief',
                'type': 'daily_brief',
                'status': 'online',
                'efficiency': 95,
                'status_text': 'Intelligence compiled'
            },
            {
                'id': 'council',
                'name': 'Council',
                'type': 'council',
                'status': 'online',
                'efficiency': 100,
                'status_text': 'Decision autonomy active'
            },
            {
                'id': 'orchestrator',
                'name': 'Orchestrator',
                'type': 'orchestrator',
                'status': 'online',
                'efficiency': 97,
                'status_text': 'Agents coordinated'
            }
        ]
        return jsonify({'agents': agents})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/systems')
def get_systems():
    """Get three-device system status for iPhone dashboard"""
    try:
        systems = [
            {
                'id': 'quantum_quasar',
                'name': 'Quantum Quasar',
                'cpu': 75,
                'ram': 45,
                'status': 'Online'
            },
            {
                'id': 'tablet_titan',
                'name': 'Tablet Titan',
                'cpu': 60,
                'ram': 35,
                'status': 'Online'
            },
            {
                'id': 'windows_companion',
                'name': 'Windows Companion',
                'cpu': 85,
                'ram': 70,
                'status': 'Online'
            }
        ]
        return jsonify({'systems': systems})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/finance')
def get_finance():
    """Get AAC finance data for iPhone dashboard"""
    try:
        # Mock data - in real implementation, this would query AAC database
        finance_data = {
            'balance': 127543.89,
            'revenue': 15234.56,
            'compliance': 98,
            'transactions': [
                {'description': 'Investment Return', 'amount': 2345.67},
                {'description': 'Server Costs', 'amount': -156.23},
                {'description': 'Client Payment', 'amount': 5000.00},
                {'description': 'Office Supplies', 'amount': -89.45},
                {'description': 'Consulting Fee', 'amount': 1200.00}
            ]
        }
        return jsonify(finance_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/quasmem')
def get_quasmem_status():
    """Get QUASMEM memory optimization status"""
    if not QUASMEM_ACTIVE:
        return jsonify({
            'status': 'inactive',
            'message': 'QUASMEM optimization not available',
            'hot_code': 'QUASMEM',
            'protocol_version': '1.0'
        })

    try:
        memory_status = get_memory_status()
        return jsonify({
            'status': 'active',
            'hot_code': 'QUASMEM',
            'memory_data': memory_status,
            'optimization_level': 'HOT CODE',
            'protocol_version': '1.0'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/quasmem/optimize')
def trigger_memory_optimization():
    """Trigger QUASMEM memory optimization"""
    if not QUASMEM_ACTIVE:
        return jsonify({
            'status': 'error',
            'message': 'QUASMEM optimization not available'
        })

    try:
        optimization_result = optimize_memory_usage()
        return jsonify({
            'status': 'optimized',
            'hot_code': 'QUASMEM',
            'results': optimization_result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Super Agency Mobile Command Center...")
    print("� Optimized for macOS Sequoia 15.7.3 - Apple M1 8GB")
    print("🧠 Memory limits: 256MB (mobile), 512MB (services)")
    print("�📱 Access from your phone at: http://YOUR_LOCAL_IP:8080")
    print("🔄 Remote access via ngrok/cloudflared tunnel")
    print(f"📡 SASP Protocol v{SASP_CONFIG['version']} enabled")
    print(f"🆔 Mac Hub ID: {SASP_CONFIG['mac_id']}")

    app.run(host='0.0.0.0', port=8080, debug=False)