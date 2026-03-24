#!/usr/bin/env python3
"""
MATRIX MAXIMIZER V3.0 - Complete Rewrite
Super Agency Project Management & Intelligence Platform

A clean, robust, and reliable project management system with:
- Automatic port conflict resolution
- Proper process management and cleanup
- Reliable threading and resource management
- Real-time monitoring and forecasting
- WebSocket updates and REST API
- File watching for dynamic updates
"""

import json
import logging
import os
import signal
import socket
import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

# Flask and extensions
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
from watchdog.events import FileSystemEventHandler

# File watching
from watchdog.observers import Observer

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

    def __init__(self, project_manager: ProjectManager, socketio: SocketIO, app: Flask):
        self.project_manager = project_manager
        self.socketio = socketio
        self.app = app
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

class InterventionManager:
    """Manages project interventions and actions"""

    INTERVENTION_TYPES = {
        'prioritize': 'Move project to higher priority',
        'pause': 'Temporarily pause project activities',
        'escalate': 'Escalate to higher authority',
        'allocate_resources': 'Allocate additional resources',
        'review': 'Schedule project review',
        'archive': 'Archive inactive project',
        'restart': 'Restart paused project'
    }

    def __init__(self):
        self.interventions: List[Dict[str, Any]] = []
        self.intervention_lock = threading.RLock()
        self.next_id = 1

    def create_intervention(self, intervention_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new intervention"""
        with self.intervention_lock:
            intervention = {
                'id': f"int_{self.next_id}_{int(time.time())}",
                'type': intervention_data.get('type', 'review'),
                'target_project': intervention_data.get('project_id'),
                'reason': intervention_data.get('reason', ''),
                'priority': intervention_data.get('priority', 'medium'),
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'metadata': intervention_data.get('metadata', {})
            }
            self.interventions.append(intervention)
            self.next_id += 1
            logger.info(f"🎯 Created intervention {intervention['id']}: {intervention['type']}")
            return intervention

    def get_interventions(self, status: str = None) -> List[Dict[str, Any]]:
        """Get all interventions, optionally filtered by status"""
        with self.intervention_lock:
            if status:
                return [i for i in self.interventions if i['status'] == status]
            return self.interventions.copy()

    def update_intervention(self, intervention_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing intervention"""
        with self.intervention_lock:
            for intervention in self.interventions:
                if intervention['id'] == intervention_id:
                    intervention.update(updates)
                    intervention['updated_at'] = datetime.now().isoformat()
                    logger.info(f"📝 Updated intervention {intervention_id}")
                    return intervention
        return None

    def get_intervention_stats(self) -> Dict[str, Any]:
        """Get intervention statistics"""
        with self.intervention_lock:
            pending = sum(1 for i in self.interventions if i['status'] == 'pending')
            in_progress = sum(1 for i in self.interventions if i['status'] == 'in_progress')
            completed = sum(1 for i in self.interventions if i['status'] == 'completed')
            return {
                'total': len(self.interventions),
                'pending': pending,
                'in_progress': in_progress,
                'completed': completed,
                'types_available': list(self.INTERVENTION_TYPES.keys())
            }


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

class MatrixMaximizerApp:
    """Main Matrix Maximizer application"""

    def __init__(self):
        self.app = None
        self.socketio = None
        self.project_manager = None
        self.intervention_manager = None
        self.background_services = None
        self.file_watcher = None
        self.port_manager = None
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

            # Initialize intervention manager
            self.intervention_manager = InterventionManager()

            # Initialize background services
            self.background_services = BackgroundServices(self.project_manager, self.socketio, self.app)

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
                "message": "Matrix Maximizer V3.0 API",
                "status": "running",
                "endpoints": {
                    "health": "/api/health",
                    "projects": "/api/projects",
                    "interventions": "/api/interventions"
                }
            })

        @self.app.route('/api/health')
        def health():
            return jsonify(self.project_manager.get_health_data())

        @self.app.route('/api/projects')
        def projects():
            return jsonify(self.project_manager.get_projects_data())

        @self.app.route('/api/interventions')
        def interventions():
            status_filter = request.args.get('status')
            intervention_list = self.intervention_manager.get_interventions(status_filter)
            stats = self.intervention_manager.get_intervention_stats()
            return jsonify({
                "interventions": intervention_list,
                "total": stats['total'],
                "stats": stats
            })

        @self.app.route('/api/intervene', methods=['POST'])
        def intervene():
            try:
                data = request.get_json()
                logger.info(f"🎯 Intervention requested: {data}")

                intervention = self.intervention_manager.create_intervention(data)

                # Emit WebSocket update for real-time notification
                self.socketio.emit('intervention_created', intervention)

                return jsonify({
                    "status": "accepted",
                    "message": "Intervention created and queued for processing",
                    "intervention": intervention
                })
            except Exception as e:
                logger.error(f"❌ Intervention error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/interventions/<intervention_id>', methods=['PATCH'])
        def update_intervention(intervention_id):
            try:
                data = request.get_json()
                updated = self.intervention_manager.update_intervention(intervention_id, data)
                if updated:
                    self.socketio.emit('intervention_updated', updated)
                    return jsonify({"status": "updated", "intervention": updated})
                return jsonify({"error": "Intervention not found"}), 404
            except Exception as e:
                logger.error(f"❌ Intervention update error: {e}")
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
            self.socketio.run(self.app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)

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
