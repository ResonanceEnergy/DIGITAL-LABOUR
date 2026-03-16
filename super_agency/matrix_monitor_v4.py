#!/usr/bin/env python3
"""
MATRIX MONITOR v4.0 - ENTERPRISE COMMAND CENTER
HTTP polling real-time updates, tabbed dashboard, live activity feeds
Inspired by Grafana/Netdata best practices
"""

import json
import logging
import os
import platform
import shutil
import socket
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import psutil
from flask import Flask, jsonify, render_template
from flask import request as flask_request
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)


def _get_python_executable():
    """Return a reliable Python interpreter path.

    ``sys.executable`` may point to a .venv that has been deleted or to a path
    with special characters that ``subprocess.Popen`` cannot handle on Windows.
    Fall back to the ``python`` / ``python3`` on PATH when the venv binary is
    missing or lives inside a virtual-environment directory.
    """
    exe = sys.executable
    # If it resolves and is NOT inside a venv, use it directly
    if exe and os.path.isfile(exe) and '.venv' not in exe and 'venv' not in exe:
        return exe
    # Try the system python on PATH
    for name in ('python3', 'python'):
        found = shutil.which(name)
        if found and '.venv' not in found and 'venv' not in found:
            return found
    # Last resort — trust whatever sys.executable says
    return exe or 'python'

# ============================================
# DATA STORES - Time series & activity logs
# ============================================
MAX_HISTORY = 60  # Keep 60 data points (5 min at 5s intervals)
cpu_history = deque(maxlen=MAX_HISTORY)
ram_history = deque(maxlen=MAX_HISTORY)
activity_log = deque(maxlen=100)  # Last 100 activities
repo_metrics_history = deque(maxlen=MAX_HISTORY)

# Initialize with zeros
for _ in range(MAX_HISTORY):
    cpu_history.append(0)
    ram_history.append(0)

# Cached device sync status (updated in background to avoid blocking API)
_device_sync_cache = {
    'pulsar': {'name': 'Pocket Pulsar', 'device': 'iPhone 15', 'host': '192.168.1.101',
               'status': 'offline', 'reachable': False, 'last_sync': None},
    'titan':  {'name': 'Tablet Titan', 'device': 'iPad', 'host': '192.168.1.102',
               'status': 'offline', 'reachable': False, 'last_sync': None}
}
_device_sync_lock = threading.Lock()

# Cached process scan results (updated in background to avoid 3x process_iter per API call)
_process_cache = {
    'qforge_active': False,
    'qusar_active': False,
    'watchdog_active': False,
    'repo_depot_active': False,
    'openclaw_active': False,
    'gasket_active': False,
    'sync_engine_active': False,
    'matrix_maximizer_active': False,
    'optimus_depot_active': False,
    'repo_depot_pid': None,
}
_process_cache_lock = threading.Lock()

def log_activity(category: str, message: str, level: str = "info"):
    """Add activity to the log"""
    activity_log.appendleft({
        'timestamp': datetime.now().isoformat(),
        'time_display': datetime.now().strftime('%H:%M:%S'),
        'category': category,
        'message': message,
        'level': level  # info, success, warning, error
    })

# Background data collection
def collect_metrics():
    """Background thread to collect metrics every 5 seconds"""
    cycle = 0
    while True:
        try:
            cpu_history.append(psutil.cpu_percent(interval=None))
            ram_history.append(psutil.virtual_memory().percent)

            # Check repo depot status
            status_file = Path('repo_depot_status.json')
            if status_file.exists():
                try:
                    with open(status_file, 'r', encoding='utf-8') as fh:
                        data = json.load(fh)
                        repo_metrics_history.append(
                            {'timestamp': datetime.now().isoformat(),
                             'completed': data.get('metrics', {}).get(
                                 'repos_completed', 0),
                             'building': data.get('metrics', {}).get(
                                 'repos_building', 0)})
                except (json.JSONDecodeError, OSError):
                    pass

            # Refresh process cache every 2nd cycle (~10s) - single scan used by all API reads
            if cycle % 2 == 0:
                _refresh_process_cache()

            # Update device sync cache every 6th cycle (~30s) to avoid constant TCP blocking
            if cycle % 6 == 0:
                _refresh_device_sync_cache()
            cycle += 1

            time.sleep(5)
        except OSError as e:
            logger.error("Metrics collection error: %s", e)
            time.sleep(5)


def _refresh_process_cache():
    """Single process scan that feeds get_agent_status, get_repo_depot_status, and watchdog.
    Runs in background thread every ~10s so API calls never iterate processes."""
    global _process_cache
    qforge = False
    qusar = False
    watchdog = False
    depot = False
    depot_pid = None
    openclaw = False
    gasket = False
    sync_engine = False
    maximizer = False
    optimus_depot = False

    # Also check filesystem hints for qforge/qusar
    qforge_paths = [Path('qforge'), Path('agents/qforge'),
                         Path('qforge_executor.py')]
    if any(p.exists() for p in qforge_paths):
        qforge = True
    qusar_paths = [Path('qusar'), Path('agents/qusar'),
                        Path('qusar_orchestrator.py')]
    if any(p.exists() for p in qusar_paths):
        qusar = True

    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info.get('cmdline', []) or [])
                lower = cmdline.lower()
                if 'qforge' in lower:
                    qforge = True
                if 'qusar' in lower:
                    qusar = True
                if 'watchdog' in lower:
                    watchdog = True
                if 'optimus_repo_depot_launcher' in lower:
                    depot = True
                    depot_pid = proc.info['pid']
                if 'openclaw' in lower:
                    openclaw = True
                if 'optimus_openclaw_depot' in lower:
                    optimus_depot = True
                    gasket = True
                    sync_engine = True
                if 'matrix_maximizer' in lower:
                    maximizer = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    with _process_cache_lock:
        _process_cache['qforge_active'] = qforge
        _process_cache['qusar_active'] = qusar
        _process_cache['watchdog_active'] = watchdog
        _process_cache['repo_depot_active'] = depot
        _process_cache['openclaw_active'] = openclaw
        _process_cache['gasket_active'] = gasket
        _process_cache['sync_engine_active'] = sync_engine
        _process_cache['matrix_maximizer_active'] = maximizer
        _process_cache['optimus_depot_active'] = optimus_depot
        _process_cache['repo_depot_pid'] = depot_pid

    # Also read from OPTIMUS DEPOT internal state file
    depot_state_file = Path('optimus_state') / 'matrix_monitor_state.json'
    if depot_state_file.exists():
        try:
            with open(depot_state_file, 'r', encoding='utf-8') as fh:
                depot_data = json.load(fh)
                cache = depot_data.get('process_cache', {})
                with _process_cache_lock:
                    for key in ['openclaw_active', 'gasket_active',
                                'sync_engine_active',
                                 'matrix_maximizer_active']:
                        if cache.get(key):
                            _process_cache[key] = True
        except (json.JSONDecodeError, OSError):
            pass


def _refresh_device_sync_cache():
    """Refresh PULSAR/TITAN device reachability (runs in background thread)"""
    global _device_sync_cache

    config_file = Path('unified_orchestrator_config.json')
    config = {}
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as fh:
                config = json.load(fh)
        except (json.JSONDecodeError, OSError):
            pass

    pulsar_host = config.get('pulsar_host', '192.168.1.101')
    titan_host = config.get('titan_host', '192.168.1.102')

    def _check(host, port=8080, timeout=0.5):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except (socket.error, OSError):
            return False

    def _last_sync(device_name):
        sync_file = Path('data') / 'device_sync_status.json'
        if sync_file.exists():
            try:
                with open(sync_file, 'r', encoding='utf-8') as fh:
                    return json.load(fh).get(device_name, {}).get('last_sync')
            except (json.JSONDecodeError, OSError):
                pass
        return None

    pulsar_reachable = _check(pulsar_host)
    titan_reachable = _check(titan_host)
    pulsar_ls = _last_sync('pulsar')
    titan_ls = _last_sync('titan')

    new_cache = {
        'pulsar': {
            'name': 'Pocket Pulsar', 'device': 'iPhone 15', 'host': pulsar_host,
            'status': 'synced' if (pulsar_reachable and pulsar_ls) else ('reachable' if pulsar_reachable else 'offline'),
            'reachable': pulsar_reachable, 'last_sync': pulsar_ls
        },
        'titan': {
            'name': 'Tablet Titan', 'device': 'iPad', 'host': titan_host,
            'status': 'synced' if (titan_reachable and titan_ls) else ('reachable' if titan_reachable else 'offline'),
            'reachable': titan_reachable, 'last_sync': titan_ls
        }
    }

    with _device_sync_lock:
        _device_sync_cache = new_cache

# Start background collection
collector_thread = threading.Thread(target=collect_metrics, daemon=True)
collector_thread.start()

# ============================================
# HTML TEMPLATE - Modern Dashboard
# ============================================
# HTML template has been moved to templates/matrix_monitor_v4.html
# CSS → static/css/matrix_monitor_v4.css
# JS  → static/js/matrix_monitor_v4.js
# ============================================
# API ENDPOINTS
# ============================================

def get_agent_status():
    """Get agent status from cached background process scan"""
    with _process_cache_lock:
        return {
            'qforge': 'ACTIVE' if _process_cache['qforge_active'] else 'OFFLINE',
            'qusar': 'ACTIVE' if _process_cache['qusar_active'] else 'OFFLINE',
            'openclaw': 'ACTIVE' if _process_cache['openclaw_active'] else 'OFFLINE',
            'gasket': 'ACTIVE' if _process_cache['gasket_active'] else 'OFFLINE',
            'sync_engine': 'ACTIVE' if _process_cache['sync_engine_active'] else 'OFFLINE',
            'matrix_maximizer': 'ACTIVE' if _process_cache['matrix_maximizer_active'] else 'OFFLINE',
            'optimus_depot': 'ACTIVE' if _process_cache['optimus_depot_active'] else 'OFFLINE',
            'matrix_monitor': 'ACTIVE'
        }


def get_device_sync_status():
    """Get PULSAR (iPhone) and TITAN (iPad) cross-device sync status from cache"""
    with _device_sync_lock:
        return dict(_device_sync_cache)

def get_agent_activity():
    """Get agent activity data"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    return {
        'optimus': {
            'active_work': {
                'agent': 'OPTIMUS',
                'current_task': 'Repository Intelligence & QFORGE Operations',
                'progress': 85,
                'active_operations': [
                    'Repository intelligence analysis',
                    'QFORGE task execution optimization',
                    'Matrix Monitor integration',
                    'Portfolio monitoring'
                ],
                'next_steps': ['Continue repo analysis', 'Update metrics']
            },
            'progress': 85,
            'decisions': [f"{now}: QFORGE integration active"]
        },
        'gasket': {
            'active_work': {
                'agent': 'GASKET',
                'current_task': 'CPU Optimization & QUSAR Feedback Loops',
                'progress': 78,
                'active_operations': [
                    'CPU optimization active',
                    'QUSAR feedback loops management',
                    'Infrastructure management',
                    'Memory doctrine maintenance'
                ],
                'next_steps': ['Optimize resource usage', 'Update feedback loops']
            },
            'progress': 78,
            'decisions': [f"{now}: QUSAR orchestration active"]
        }
    }

def get_repo_depot_status():
    """Get Repo Depot status using cached process scan"""
    try:
        # Get repo count from portfolio
        total_repos = 27
        try:
            with open('portfolio.json', 'r', encoding='utf-8') as fh:
                portfolio = json.load(fh)
                total_repos = len(portfolio.get('repositories', []))
        except (json.JSONDecodeError, OSError):
            pass

        # Read process state from cache (no process_iter here)
        with _process_cache_lock:
            active = _process_cache['repo_depot_active']
            pid = _process_cache['repo_depot_pid']

        # Get metrics from status file
        metrics = {
            'total_repos': total_repos,
            'repos_completed': 0,
            'repos_building': 0,
            'flywheel_cycles': 0,
            'files_created': 0,
            'errors': 0
        }

        status_file = Path('repo_depot_status.json')
        if status_file.exists():
            try:
                with open(status_file, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                    if 'metrics' in data:
                        metrics.update(data['metrics'])
                        metrics['total_repos'] = total_repos
            except (json.JSONDecodeError, OSError):
                pass

        return {
            'active': active,
            'pid': pid,
            'metrics': metrics
        }
    except (OSError, psutil.Error) as e:
        logger.error("Error getting repo depot status: %s", e)
        return {
            'active': False,
            'pid': None,
            'metrics': {
                'total_repos': 27,
                'repos_completed': 0,
                'repos_building': 0,
                'flywheel_cycles': 0,
                'files_created': 0,
                'errors': 0
            }
        }

def get_repos():
    """Get repository list"""
    try:
        with open('portfolio.json', 'r', encoding='utf-8') as fh:
            data = json.load(fh)
            repos = data.get('repositories', [])
            # Add progress to each repo
            for i, repo in enumerate(repos):
                repo['progress'] = min(100, 50 + (i * 2))
            return repos
    except (json.JSONDecodeError, OSError):
        return []

def get_system_info():
    """Get system information"""
    mem = psutil.virtual_memory()
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time

    return {
        'platform': platform.system() + ' ' + platform.release(),
        'cpu_count': psutil.cpu_count(),
        'total_ram': f"{mem.total / (1024**3):.1f} GB",
        'python_version': platform.python_version(),
        'uptime': str(uptime).split('.')[0]
    }

@app.route('/')
def index():
    return render_template('matrix_monitor_v4.html')

@app.route('/api/v4/status')
def api_status():
    """Main status endpoint with all data"""
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    agent_status = get_agent_status()
    repo_depot = get_repo_depot_status()
    agent_activity = get_agent_activity()
    repos = get_repos()
    system = get_system_info()
    device_sync = get_device_sync_status()

    # Read watchdog state from cached background process scan
    with _process_cache_lock:
        watchdog_active = _process_cache['watchdog_active']

    return jsonify({        'cpu': cpu,
        'ram': mem.percent,
        'qforge': agent_status['qforge'],
        'qusar': agent_status['qusar'],
        'openclaw': agent_status.get('openclaw', 'OFFLINE'),
        'gasket': agent_status.get('gasket', 'OFFLINE'),
        'sync_engine': agent_status.get('sync_engine', 'OFFLINE'),
        'matrix_maximizer': agent_status.get('matrix_maximizer', 'OFFLINE'),
        'optimus_depot': agent_status.get('optimus_depot', 'OFFLINE'),
        'matrix_monitor': agent_status['matrix_monitor'],
        'repo_depot': repo_depot,
        'agent_activity': agent_activity,
        'repos': repos,
        'activity_log': list(activity_log),
        'system': system,
        'device_sync': device_sync,
        'watchdog': 'ACTIVE' if watchdog_active else 'OFFLINE',
        'timestamp': datetime.now().isoformat(),
        'cpu_history': list(cpu_history),
        'ram_history': list(ram_history)
    })

@app.route('/api/v4/control/start-depot', methods=['POST'])
def start_depot():
    """Start Repo Depot"""
    try:
        subprocess.Popen(
            [_get_python_executable(), 'optimus_repo_depot_launcher.py'],
            cwd=os.getcwd(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        log_activity('repo_depot', 'Repo Depot started', 'success')
        return jsonify({'success': True, 'message': 'Repo Depot starting...'})
    except OSError as e:
        log_activity('repo_depot', f'Failed to start: {e}', 'error')
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/v4/control/stop-depot', methods=['POST'])
def stop_depot():
    """Stop Repo Depot"""
    try:
        for proc in psutil.process_iter(['pid', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any(
                    'optimus_repo_depot_launcher' in str(arg) for arg in
                     cmdline):
                    proc.terminate()
                    log_activity('repo_depot', 'Repo Depot stopped', 'warning')
                    return jsonify(
                        {'success': True, 'message': 'Repo Depot stopped'})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return jsonify({'success': False, 'message': 'Repo Depot not found'})
    except (OSError, psutil.Error) as e:
        log_activity('repo_depot', f'Failed to stop: {e}', 'error')
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'matrix_monitor_v4',
        'version': '4.0.0',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/v4/optimus-depot')
def api_optimus_depot():
    """OPTIMUS DEPOT unified engine status - reads from internal state files"""
    depot_state_file = Path('optimus_state') / 'optimus_depot_state.json'
    monitor_state_file = Path('optimus_state') / 'matrix_monitor_state.json'
    maximizer_state_file = Path('optimus_state') / \
                                'matrix_maximizer_state.json'

    depot_data = {}
    if depot_state_file.exists():
        try:
            with open(depot_state_file, 'r', encoding='utf-8') as fh:
                depot_data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            pass

    monitor_data = {}
    if monitor_state_file.exists():
        try:
            with open(monitor_state_file, 'r', encoding='utf-8') as fh:
                monitor_data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            pass

    maximizer_data = {}
    if maximizer_state_file.exists():
        try:
            with open(maximizer_state_file, 'r', encoding='utf-8') as fh:
                maximizer_data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            pass

    return jsonify({
        'optimus_depot': depot_data,
        'matrix_monitor_internal': monitor_data,
        'matrix_maximizer_internal': maximizer_data,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/v4/matrix-nodes')
def api_matrix_nodes():
    """Get matrix visualization nodes from OPTIMUS DEPOT internal maximizer"""
    maximizer_state_file = Path('optimus_state') / \
                                'matrix_maximizer_state.json'
    if maximizer_state_file.exists():
        try:
            with open(maximizer_state_file, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
                return jsonify({
                    'matrix_nodes': data.get('matrix_nodes', []),
                    'total_nodes': data.get('total_nodes', 0),
                    'system_health': data.get('system_health', 0),
                    'timestamp': datetime.now().isoformat()
                })
        except (json.JSONDecodeError, OSError):
            pass
    return jsonify({'matrix_nodes': [], 'total_nodes': 0, 'error': 'No data'})


@app.route('/api/v4/alerts')
def api_alerts():
    """Get alerts from OPTIMUS DEPOT internal maximizer"""
    maximizer_state_file = Path('optimus_state') / \
                                'matrix_maximizer_state.json'
    if maximizer_state_file.exists():
        try:
            with open(maximizer_state_file, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
                return jsonify({
                    'alerts': data.get('alerts', []),
                    'predictions': data.get('predictions', []),
                    'timestamp': datetime.now().isoformat()
                })
        except (json.JSONDecodeError, OSError):
            pass
    return jsonify({'alerts': [], 'predictions': []})


@app.route('/api/v4/devices')
def api_devices():
    """Dedicated endpoint for PULSAR/TITAN device sync status"""
    device_sync = get_device_sync_status()
    return jsonify({
        'device_sync': device_sync,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/v4/devices/sync', methods=['POST'])
def api_device_sync():
    """Record a sync event from PULSAR or TITAN"""
    data = flask_request.get_json(silent=True) or {}
    device_name = data.get('device', '').lower()

    if device_name not in ('pulsar', 'titan'):
        return jsonify(
            {'success': False,
             'error': 'Invalid device. Use pulsar or titan.'}), 400

    # Write sync timestamp
    sync_file = Path('data') / 'device_sync_status.json'
    sync_file.parent.mkdir(exist_ok=True)

    sync_data = {}
    if sync_file.exists():
        try:
            with open(sync_file, 'r', encoding='utf-8') as fh:
                sync_data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            pass

    sync_data[device_name] = {
        'last_sync': datetime.now().strftime('%H:%M:%S'),
        'last_sync_iso': datetime.now().isoformat(),
        'device_info': data.get('device_info', {}),
        'sync_type': data.get('sync_type', 'manual')
    }

    with open(sync_file, 'w', encoding='utf-8') as fh:
        json.dump(sync_data, fh, indent=2)

    device_label = 'Pocket Pulsar' if device_name == 'pulsar' else 'Tablet Titan'
    log_activity('sync', f'{device_label} synced successfully', 'success')

    return jsonify(
        {'success': True, 'message': f'{device_label}  sync recorded'})


@app.route('/pulsar')
def pulsar_view():
    """Optimized view for Pocket Pulsar (iPhone)"""
    return render_template('matrix_monitor_v4.html')


@app.route('/titan')
def titan_view():
    """Optimized view for Tablet Titan (iPad)"""
    return render_template('matrix_monitor_v4.html')


@app.route('/docs')
def docs_view():
    """API documentation endpoint"""
    return jsonify({
        'service': 'Matrix Monitor v4.0',
        'endpoints': {
            '/': 'Dashboard UI',
            '/pulsar': 'iPhone-optimized dashboard',
            '/titan': 'iPad-optimized dashboard',
            '/api/v4/status': 'GET - Full system status (polled every 3s)',
            '/api/v4/devices': 'GET - PULSAR/TITAN device sync status',
            '/api/v4/devices/sync': 'POST - Record device sync event {device, sync_type, device_info}',
            '/api/v4/control/start-depot': 'POST - Start Repo Depot',
            '/api/v4/control/stop-depot': 'POST - Stop Repo Depot',
            '/api/health': 'GET - Health check',
            '/docs': 'GET - This documentation'
        },
        'devices': {
            'pulsar': 'Pocket Pulsar (iPhone 15) - 192.168.1.101',
            'titan': 'Tablet Titan (iPad) - 192.168.1.102'
        },
        'version': '4.0.0'
    })

# ============================================
# MAIN
# ============================================
if __name__ == '__main__':
    # Create PID file
    pid_file = '.matrix_monitor_v4.pid'
    with open(pid_file, 'w', encoding='utf-8') as pid_fh:
        pid_fh.write(str(os.getpid()))

    # Log startup
    log_activity('system', 'Matrix Monitor v4.0 starting...', 'info')
    log_activity('system', 'Enterprise Command Center initialized', 'success')

    print("=" * 60)
    print("    MATRIX MONITOR v4.0 - ENTERPRISE COMMAND CENTER")
    print("    http://localhost:8501")
    print("    http://192.168.100.132:8501 (network)")
    print("")
    print("    DEVICE ROUTES:")
    print("    PULSAR (iPhone): http://192.168.100.132:8501/pulsar")
    print("    TITAN  (iPad):   http://192.168.100.132:8501/titan")
    print("")
    print("    API: /api/v4/status | /api/v4/devices")
    print("=" * 60)

    try:
        app.run(host='0.0.0.0', port=8501, debug=False, threaded=True)
    finally:
        if os.path.exists(pid_file):
            os.remove(pid_file)
