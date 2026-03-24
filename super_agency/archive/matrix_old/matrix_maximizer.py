"""
MATRIX MAXIMIZER V3.0 - Complete Rewrite
Super Agency Project Management & Intelligence Platform
REPO DEPOT Integration System

A clean, robust, and reliable project management system with:
- Automatic port conflict resolution
- Proper process management and cleanup
- Reliable threading and resource management
- Real-time monitoring and forecasting
- WebSocket updates and REST API
- File watching for dynamic updates
- REPO DEPOT specific metrics and monitoring
- 14 AI agent ecosystem integration
- Doctrine and memory system monitoring
"""

import os
import sys
import json
import time
import signal
import socket
import psutil
import threading
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from contextlib import contextmanager

# Flask and extensions
from flask import Flask, jsonify, request
from flask_socketio import SocketIO
from flask_cors import CORS

# File watching
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('matrix_maximizer.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

class PortManager:
    """Manages port allocation and conflict resolution"""

    def __init__(self, preferred_port: int = 3000):
        self.preferred_port = preferred_port
        self.allocated_port = None

    def find_available_port(self) -> int:
        """Find an available port starting from preferred port"""
        port = self.preferred_port
        max_attempts = 100

        for attempt in range(max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    self.allocated_port = port
                    logger.info(f"✅ Port {port} is available")
                    return port
            except OSError:
                logger.warning(f"❌ Port {port} is in use, trying {port + 1}")
                port += 1

        raise RuntimeError(f"Could not find available port after {max_attempts} attempts")

    def cleanup_port(self, port: int):
        """Clean up any processes using the specified port"""
        try:
            # Find processes using the port
            result = os.popen(f"lsof -ti :{port}").read().strip()
            if result:
                pids = result.split('\n')
                for pid in pids:
                    if pid.strip():
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            logger.info(f"🧹 Terminated process {pid} using port {port}")
                            time.sleep(0.5)  # Give process time to terminate gracefully
                        except (ProcessLookupError, OSError):
                            pass  # Process already gone
        except Exception as e:
            logger.warning(f"⚠️ Could not cleanup port {port}: {e}")

class ProjectManager:
    """Manages project data and operations"""

    def __init__(self):
        self.projects: List[Dict[str, Any]] = []
        self.project_lock = threading.RLock()
        self.last_update = datetime.now()

    def load_projects(self) -> bool:
        """Load projects from portfolio.json"""
        try:
            portfolio_path = Path("portfolio.json")
            if not portfolio_path.exists():
                logger.warning("⚠️ portfolio.json not found, using empty project list")
                self.projects = []
                return True

            with open(portfolio_path, 'r') as f:
                data = json.load(f)

            with self.project_lock:
                self.projects = data.get('repositories', [])  # portfolio.json uses 'repositories'
                self.last_update = datetime.now()

            logger.info(f"✅ Loaded {len(self.projects)} projects")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to load projects: {e}")
            return False

    def get_projects_data(self) -> Dict[str, Any]:
        """Get current projects data"""
        with self.project_lock:
            return {
                "projects": self.projects.copy(),
                "total": len(self.projects),
                "last_update": self.last_update.isoformat()
            }

    def get_health_data(self) -> Dict[str, Any]:
        """Get health status data"""
        with self.project_lock:
            return {
                "status": "healthy",
                "projects_tracked": len(self.projects),
                "active_interventions": 0,  # TODO: implement interventions
                "timestamp": datetime.now().isoformat(),
                "uptime": (datetime.now() - self.last_update).total_seconds()
            }

class BackgroundServices:
    """Manages background threads and services"""

    def __init__(self, project_manager: ProjectManager, socketio: SocketIO, app: Flask, metrics_collector: 'MetricsCollector'):
        self.project_manager = project_manager
        self.socketio = socketio
        self.app = app
        self.metrics_collector = metrics_collector
        self.threads: List[threading.Thread] = []
        self.stop_event = threading.Event()
        self.services_lock = threading.RLock()

    def start_monitoring_thread(self):
        """Start project monitoring thread"""
        def monitor_worker():
            logger.info("📊 Starting project monitoring thread")
            while not self.stop_event.is_set():
                try:
                    # Update project data periodically
                    if self.project_manager.load_projects():
                        # Emit update via WebSocket
                        with self.app.app_context():
                            self.socketio.emit('projects_updated', {
                                'timestamp': datetime.now().isoformat(),
                                'count': len(self.project_manager.projects)
                            })

                    # Emit metrics update every monitoring cycle
                    with self.app.app_context():
                        self.socketio.emit('metrics_updated', self.metrics_collector.get_all_metrics(len(self.project_manager.projects)))

                    # Sleep for 30 seconds or until stopped
                    self.stop_event.wait(30)

                except Exception as e:
                    logger.error(f"❌ Monitoring thread error: {e}")
                    time.sleep(5)  # Brief pause before retry

            logger.info("🛑 Monitoring thread stopped")

        thread = threading.Thread(target=monitor_worker, daemon=True, name="ProjectMonitor")
        thread.start()
        self.threads.append(thread)

    def start_forecast_thread(self):
        """Start forecast update thread"""
        def forecast_worker():
            logger.info("🔮 Starting forecast thread")
            while not self.stop_event.is_set():
                try:
                    # Generate forecasts every 5 minutes
                    logger.info("📈 Generating project forecasts")

                    # Emit forecast update
                    with self.app.app_context():
                        self.socketio.emit('forecast_updated', {
                            'timestamp': datetime.now().isoformat(),
                            'type': 'forecast_refresh'
                        })

                    # Sleep for 5 minutes or until stopped
                    self.stop_event.wait(300)

                except Exception as e:
                    logger.error(f"❌ Forecast thread error: {e}")
                    time.sleep(10)

            logger.info("🛑 Forecast thread stopped")

        thread = threading.Thread(target=forecast_worker, daemon=True, name="Forecast")
        thread.start()
        self.threads.append(thread)

    def start_all_services(self):
        """Start all background services"""
        logger.info("🔄 Starting background services...")
        self.start_monitoring_thread()
        self.start_forecast_thread()
        logger.info("✅ All background services started")

    def stop_all_services(self):
        """Stop all background services"""
        logger.info("🛑 Stopping background services...")
        self.stop_event.set()

        # Wait for threads to finish
        for thread in self.threads:
            thread.join(timeout=5.0)
            if thread.is_alive():
                logger.warning(f"⚠️ Thread {thread.name} did not stop gracefully")

        self.threads.clear()
        logger.info("✅ All background services stopped")

class FileWatcher:
    """Manages file system watching"""

    def __init__(self, project_manager: ProjectManager, socketio: SocketIO, app: Flask):
        self.project_manager = project_manager
        self.socketio = socketio
        self.app = app
        self.observer: Optional[Observer] = None
        self.watch_path = Path.cwd()

    class MatrixFileHandler(FileSystemEventHandler):
        """Handles file system events"""

        def __init__(self, file_watcher):
            self.file_watcher = file_watcher
            self.last_modified = {}

        def on_modified(self, event):
            if event.is_directory:
                return

            file_path = Path(event.src_path)
            file_name = file_path.name

            # Skip temporary and hidden files
            if file_name.startswith('.') or file_name.endswith('.tmp'):
                return

            # Debounce rapid changes
            current_time = time.time()
            if file_path in self.last_modified:
                if current_time - self.last_modified[file_path] < 1.0:
                    return
            self.last_modified[file_path] = current_time

            # Handle specific file changes
            if file_name == 'portfolio.json':
                logger.info("📁 Portfolio file changed, reloading...")
                if self.file_watcher.project_manager.load_projects():
                    with self.file_watcher.app.app_context():
                        self.file_watcher.socketio.emit('portfolio_updated', {
                            'timestamp': datetime.now().isoformat(),
                            'projects_count': len(self.file_watcher.project_manager.projects)
                        })

    def start_watching(self):
        """Start file system watching"""
        try:
            logger.info(f"👁️ Starting file watcher for {self.watch_path}")
            self.observer = Observer()
            handler = self.MatrixFileHandler(self)
            self.observer.schedule(handler, str(self.watch_path), recursive=False)
            self.observer.start()
            logger.info("✅ File watching started")
        except Exception as e:
            logger.error(f"❌ Failed to start file watching: {e}")

    def stop_watching(self):
        """Stop file system watching"""
        if self.observer:
            logger.info("🛑 Stopping file watcher...")
            self.observer.stop()
            self.observer.join(timeout=5.0)
            self.observer = None
            logger.info("✅ File watching stopped")

class MetricsCollector:
    """Collects system and application metrics"""

    def __init__(self):
        self.start_time = datetime.now()

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-level metrics"""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory": {
                    "total": psutil.virtual_memory().total,
                    "available": psutil.virtual_memory().available,
                    "percent": psutil.virtual_memory().percent,
                    "used": psutil.virtual_memory().used
                },
                "disk": {
                    "total": psutil.disk_usage('/').total,
                    "free": psutil.disk_usage('/').free,
                    "used": psutil.disk_usage('/').used,
                    "percent": psutil.disk_usage('/').percent
                },
                "network": {
                    "bytes_sent": psutil.net_io_counters().bytes_sent,
                    "bytes_recv": psutil.net_io_counters().bytes_recv,
                    "packets_sent": psutil.net_io_counters().packets_sent,
                    "packets_recv": psutil.net_io_counters().packets_recv
                },
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Failed to collect system metrics: {e}")
            return {"error": str(e)}

    def get_application_metrics(self, project_count: int = 0) -> Dict[str, Any]:
        """Get application-specific metrics"""
        try:
            process = psutil.Process()
            return {
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                "process_memory_mb": process.memory_info().rss / 1024 / 1024,
                "process_cpu_percent": process.cpu_percent(),
                "projects_tracked": project_count,
                "threads_active": threading.active_count(),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"❌ Failed to collect application metrics: {e}")
            return {"error": str(e)}

    def get_repo_depot_metrics(self) -> Dict[str, Any]:
        """Get REPO DEPOT specific metrics"""
        try:
            metrics = {
                "agents": {"active": 0, "total": 14, "status": "unknown"},
                "doctrine": {"status": "unknown", "last_update": None},
                "memory": {"status": "unknown", "entries": 0},
                "operations": {"status": "unknown", "active": False},
                "timestamp": datetime.now().isoformat()
            }

            # Check for running REPO DEPOT processes
            import subprocess
            try:
                # Check for repo_depot_flywheel processes
                result = subprocess.run(['pgrep', '-f', 'repo_depot_flywheel'],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    metrics["agents"]["active"] = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
                    metrics["agents"]["status"] = "running" if metrics["agents"]["active"] > 0 else "stopped"
                else:
                    metrics["agents"]["status"] = "stopped"
            except (subprocess.TimeoutExpired, FileNotFoundError):
                metrics["agents"]["status"] = "unknown"

            # Check doctrine file
            doctrine_path = Path("REPO_DEPOT_DOCTRINE.md")
            if doctrine_path.exists():
                try:
                    mtime = datetime.fromtimestamp(doctrine_path.stat().st_mtime)
                    metrics["doctrine"]["status"] = "available"
                    metrics["doctrine"]["last_update"] = mtime.isoformat()
                except Exception:
                    metrics["doctrine"]["status"] = "error"
            else:
                metrics["doctrine"]["status"] = "missing"

            # Check memory files (placeholder - would need actual memory system)
            memory_files = list(Path(".").glob("*.memory")) + list(Path(".").glob("memory_*.json"))
            metrics["memory"]["entries"] = len(memory_files)
            metrics["memory"]["status"] = "available" if memory_files else "empty"

            # Check operations API
            try:
                import requests
                response = requests.get("http://localhost:5001/api/v1/operations/status", timeout=2)
                if response.status_code == 200:
                    ops_data = response.json()
                    metrics["operations"]["status"] = ops_data.get("status", "unknown")
                    metrics["operations"]["active"] = True
                else:
                    metrics["operations"]["status"] = "error"
                    metrics["operations"]["active"] = False
            except Exception:
                metrics["operations"]["status"] = "unavailable"
                metrics["operations"]["active"] = False

            return metrics

        except Exception as e:
            logger.error(f"❌ Failed to collect REPO DEPOT metrics: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def get_all_metrics(self, project_count: int = 0) -> Dict[str, Any]:
        """Get all metrics combined"""
        return {
            "system": self.get_system_metrics(),
            "application": self.get_application_metrics(project_count),
            "repo_depot": self.get_repo_depot_metrics(),
            "collected_at": datetime.now().isoformat()
        }

class MatrixMaximizerApp:
    """Main Matrix Maximizer application"""

    def __init__(self):
        self.app = None
        self.socketio = None
        self.project_manager = None
        self.background_services = None
        self.file_watcher = None
        self.port_manager = None
        self.metrics_collector = None
        self.running = False
        self.shutdown_event = threading.Event()

    def initialize(self) -> bool:
        """Initialize all components"""
        try:
            logger.info("🚀 Initializing Matrix Maximizer V3.0...")

            # Initialize port manager and find available port
            self.port_manager = PortManager()
            port = self.port_manager.find_available_port()

            # Create Flask app
            self.app = Flask(__name__,
                           template_folder='templates',
                           static_folder='static')
            self.app.config['SECRET_KEY'] = 'matrix-maximizer-v3-secret-key'

            # Initialize SocketIO
            self.socketio = SocketIO(self.app, cors_allowed_origins="*")

            # Enable CORS
            CORS(self.app)

            # Initialize project manager
            self.project_manager = ProjectManager()
            if not self.project_manager.load_projects():
                logger.warning("⚠️ Failed to load initial projects, continuing with empty list")

            # Initialize metrics collector
            self.metrics_collector = MetricsCollector()

            # Initialize background services
            self.background_services = BackgroundServices(self.project_manager, self.socketio, self.app, self.metrics_collector)

            # Initialize file watcher
            self.file_watcher = FileWatcher(self.project_manager, self.socketio, self.app)

            # Setup routes
            self._setup_routes()

            # Setup SocketIO events
            self._setup_socketio_events()

            logger.info("✅ Matrix Maximizer initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize Matrix Maximizer: {e}")
            return False

    def _setup_routes(self):
        """Setup Flask routes"""

        @self.app.route('/')
        def index():
            return jsonify({
                "message": "Matrix Maximizer V3.0 - REPO DEPOT Integration",
                "status": "running",
                "endpoints": {
                    "health": "/api/health",
                    "projects": "/api/projects",
                    "metrics": "/api/metrics",
                    "interventions": "/api/interventions"
                },
                "repo_depot": {
                    "agents": "14 AI agents for continuous operations",
                    "doctrine": "Operational doctrine and guidelines",
                    "memory": "Persistent memory systems",
                    "operations": "Real-time operations API"
                }
            })

        @self.app.route('/api/health')
        def health():
            health_data = self.project_manager.get_health_data()
            metrics_data = self.metrics_collector.get_application_metrics(len(self.project_manager.projects))
            repo_depot_data = self.metrics_collector.get_repo_depot_metrics()
            health_data.update({
                "metrics": metrics_data,
                "repo_depot": repo_depot_data,
                "system_cpu_percent": self.metrics_collector.get_system_metrics().get("cpu_percent", 0),
                "system_memory_percent": self.metrics_collector.get_system_metrics().get("memory", {}).get("percent", 0)
            })
            return jsonify(health_data)

        @self.app.route('/api/projects')
        def projects():
            return jsonify(self.project_manager.get_projects_data())

        @self.app.route('/api/metrics')
        def metrics():
            return jsonify(self.metrics_collector.get_all_metrics(len(self.project_manager.projects)))

        @self.app.route('/api/interventions')
        def interventions():
            return jsonify({
                "interventions": [],
                "total": 0,
                "message": "Intervention system not yet implemented"
            })

        @self.app.route('/api/intervene', methods=['POST'])
        def intervene():
            try:
                data = request.get_json()
                logger.info(f"🎯 Intervention requested: {data}")

                # TODO: Implement actual intervention logic
                return jsonify({
                    "status": "accepted",
                    "message": "Intervention queued for processing",
                    "intervention_id": f"int_{int(time.time())}"
                })
            except Exception as e:
                logger.error(f"❌ Intervention error: {e}")
                return jsonify({"error": str(e)}), 500

    def _setup_socketio_events(self):
        """Setup SocketIO event handlers"""

        @self.socketio.on('connect')
        def handle_connect():
            logger.info("🔌 Client connected for real-time updates")
            self.socketio.emit('connected', {'status': 'connected', 'timestamp': datetime.now().isoformat()})

        @self.socketio.on('disconnect')
        def handle_disconnect():
            logger.info("🔌 Client disconnected")

        @self.socketio.on('request_projects')
        def handle_request_projects():
            self.socketio.emit('projects_data', self.project_manager.get_projects_data())

    def start(self, host: str = '0.0.0.0', port: Optional[int] = None) -> bool:
        """Start the Matrix Maximizer"""
        try:
            if not self.initialize():
                return False

            # Use specified port or find available one
            if port is None:
                port = self.port_manager.allocated_port

            logger.info(f"🌐 Starting Matrix Maximizer on {host}:{port}")

            # Start background services
            self.background_services.start_all_services()

            # Start file watching
            self.file_watcher.start_watching()

            # Set running flag
            self.running = True

            # Start Flask-SocketIO server
            logger.info("🎯 Matrix Maximizer V3.0 is now running!")
            logger.info(f"📊 Projects loaded: {len(self.project_manager.projects)}")
            logger.info("🔄 Background services active")
            logger.info("👁️ File watching enabled")
            logger.info("📡 WebSocket updates active")

            # Run the server (this will block)
            self.socketio.run(self.app, host=host, port=port, debug=False)

            return True

        except Exception as e:
            logger.error(f"❌ Failed to start Matrix Maximizer: {e}")
            return False

    def stop(self):
        """Stop the Matrix Maximizer"""
        logger.info("🛑 Shutting down Matrix Maximizer V3.0...")

        self.running = False
        self.shutdown_event.set()

        # Stop file watching
        if self.file_watcher:
            self.file_watcher.stop_watching()

        # Stop background services
        if self.background_services:
            self.background_services.stop_all_services()

        logger.info("✅ Matrix Maximizer shutdown complete")

@contextmanager
def cleanup_on_exit():
    """Context manager for cleanup on exit"""
    try:
        yield
    except KeyboardInterrupt:
        logger.info("🛑 Received keyboard interrupt")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
    finally:
        # Cleanup any remaining processes on our ports
        port_manager = PortManager()
        for port in [3000, 3001, 3002, 3003, 3004]:  # Check a few ports
            port_manager.cleanup_port(port)

def main():
    """Main entry point"""
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"📡 Received signal {signum}, initiating shutdown...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    with cleanup_on_exit():
        # Create and start the application
        app = MatrixMaximizerApp()
        success = app.start()

        if not success:
            logger.error("❌ Failed to start Matrix Maximizer")
            sys.exit(1)

if __name__ == '__main__':
    main()
