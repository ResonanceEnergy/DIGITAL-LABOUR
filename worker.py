"""Unified Daemon Worker â Runs all DIGITAL LABOUR background daemons in one process.

Designed for Railway deployment as a single worker service alongside the web API.
Runs NERVE, C-Suite Scheduler, Task Scheduler, Revenue Daemon, and Resonance Sync
as concurrent threads with independent schedules and crash recovery.

Usage:
    python worker.py              # Run all daemons
    python worker.py --health     # Check if worker is alive (for Railway health checks)
"""

import argparse
import json
import logging
import os
import signal
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# ââ Setup ââââââââââââââââââââââââââââââââââââââââââââââââââââââ
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("worker")

# ââ State ââââââââââââââââââââââââââââââââââââââââââââââââââââââ
SHUTDOWN = threading.Event()
DAEMON_STATUS = {}
STATUS_LOCK = threading.Lock()
WORKER_START_TIME = datetime.now(timezone.utc)


def update_status(name: str, status: str, detail: str = ""):
    with STATUS_LOCK:
        DAEMON_STATUS[name] = {
            "status": status,
            "detail": detail,
            "updated": datetime.now(timezone.utc).isoformat(),
        }


# ââ Daemon Wrappers ââââââââââââââââââââââââââââââââââââââââââââ

def run_nerve(interval_minutes: int = 60):
    """NERVE daemon â autonomous execution cycles."""
    name = "NERVE"
    update_status(name, "starting")
    while not SHUTDOWN.is_set():
        try:
            logger.info(f"[{name}] Starting cycle...")
            update_status(name, "running", "cycle in progress")
            from automation.nerve import run_cycle
            run_cycle()
            update_status(name, "idle", f"next cycle in {interval_minutes}m")
            logger.info(f"[{name}] Cycle complete. Sleeping {interval_minutes}m.")
        except ImportError as e:
            update_status(name, "error", f"import failed: {e}")
            logger.error(f"[{name}] Import error: {e}")
            SHUTDOWN.wait(300)  # Retry in 5 min
            continue
        except Exception as e:
            update_status(name, "error", str(e)[:200])
            logger.error(f"[{name}] Cycle error: {e}\n{traceback.format_exc()}")
        # Sleep in 1-second increments so we can respond to shutdown
        for _ in range(interval_minutes * 60):
            if SHUTDOWN.is_set():
                break
            time.sleep(1)
    update_status(name, "stopped")


def run_csuite_scheduler(interval_minutes: int = 30):
    """C-Suite Scheduler â executive cadence (standup, CFO, COO, board)."""
    name = "C-Suite"
    update_status(name, "starting")
    while not SHUTDOWN.is_set():
        try:
            logger.info(f"[{name}] Checking cadence...")
            update_status(name, "running", "checking cadence")
            from c_suite.scheduler import run_due_actions
            run_due_actions()
            update_status(name, "idle", f"next check in {interval_minutes}m")
            logger.info(f"[{name}] Cadence check done. Sleeping {interval_minutes}m.")
        except ImportError as e:
            update_status(name, "error", f"import failed: {e}")
            logger.error(f"[{name}] Import error: {e}")
            SHUTDOWN.wait(300)
            continue
        except Exception as e:
            update_status(name, "error", str(e)[:200])
            logger.error(f"[{name}] Error: {e}\n{traceback.format_exc()}")
        for _ in range(interval_minutes * 60):
            if SHUTDOWN.is_set():
                break
            time.sleep(1)
    update_status(name, "stopped")


def run_task_scheduler(interval_minutes: int = 5):
    """Task Scheduler â retainer client task runner."""
    name = "TaskSched"
    update_status(name, "starting")
    while not SHUTDOWN.is_set():
        try:
            logger.info(f"[{name}] Checking tasks...")
            update_status(name, "running", "checking due tasks")
            from scheduler.runner import process_due_tasks
            process_due_tasks()
            update_status(name, "idle", f"next check in {interval_minutes}m")
        except ImportError as e:
            update_status(name, "error", f"import failed: {e}")
            logger.error(f"[{name}] Import error: {e}")
            SHUTDOWN.wait(300)
            continue
        except Exception as e:
            update_status(name, "error", str(e)[:200])
            logger.error(f"[{name}] Error: {e}\n{traceback.format_exc()}")
        for _ in range(interval_minutes * 60):
            if SHUTDOWN.is_set():
                break
            time.sleep(1)
    update_status(name, "stopped")


def run_revenue_daemon(interval_minutes: int = 30):
    """Revenue Daemon â Stripe polling + income updates."""
    name = "Revenue"
    update_status(name, "starting")
    while not SHUTDOWN.is_set():
        try:
            logger.info(f"[{name}] Checking revenue...")
            update_status(name, "running", "polling Stripe")
            from automation.revenue_daemon import check_stripe_revenue
            result = check_stripe_revenue()
            detail = f"revenue: ${result.get('total', 0):.2f}" if isinstance(result, dict) else "done"
            update_status(name, "idle", f"{detail}, next in {interval_minutes}m")
            logger.info(f"[{name}] Revenue check done. Sleeping {interval_minutes}m.")
        except ImportError as e:
            update_status(name, "error", f"import failed: {e}")
            logger.error(f"[{name}] Import error: {e}")
            SHUTDOWN.wait(300)
            continue
        except Exception as e:
            update_status(name, "error", str(e)[:200])
            logger.error(f"[{name}] Error: {e}\n{traceback.format_exc()}")
        for _ in range(interval_minutes * 60):
            if SHUTDOWN.is_set():
                break
            time.sleep(1)
    update_status(name, "stopped")


def run_resonance_sync(interval_minutes: int = 30):
    """Resonance Sync â cross-pillar data synchronization."""
    name = "Resonance"
    update_status(name, "starting")
    while not SHUTDOWN.is_set():
        try:
            logger.info(f"[{name}] Running sync...")
            update_status(name, "running", "syncing pillars")
            from resonance.sync import run_due_jobs
            run_due_jobs()
            update_status(name, "idle", f"next sync in {interval_minutes}m")
        except ImportError as e:
            update_status(name, "error", f"import failed: {e}")
            logger.error(f"[{name}] Import error: {e}")
            SHUTDOWN.wait(300)
            continue
        except Exception as e:
            update_status(name, "error", str(e)[:200])
            logger.error(f"[{name}] Error: {e}\n{traceback.format_exc()}")
        for _ in range(interval_minutes * 60):
            if SHUTDOWN.is_set():
                break
            time.sleep(1)
    update_status(name, "stopped")




def run_galactia(interval_minutes: int = 30):
    """Galactia Unified Intelligence Engine — parallel ingest + VERITAS + ML + Governor."""
    name = "Galactia"
    update_status(name, "starting")
    time.sleep(30)  # Let other daemons stabilize first
    consecutive_failures = 0

    while not SHUTDOWN.is_set():
        try:
            logger.info(f"[{name}] Starting unified cycle (parallel ingest + VERITAS + ML + Governor)...")
            update_status(name, "running", "unified: parallel ingest + scoring + governance")
            from galactia.galactia import run_cycle
            report = run_cycle()
            ingestion = report.get("phases", {}).get("ingestion", {})
            scoring = report.get("phases", {}).get("scoring", {})
            ingested = ingestion.get("total_new", 0)
            veritas = scoring.get("veritas", {}).get("scored", 0)
            ml = scoring.get("ml", {}).get("scored", 0)
            elapsed = report.get("elapsed_seconds", "?")
            detail = f"{ingested} ingested, {veritas} VERITAS, {ml} ML in {elapsed}s, next in {interval_minutes}m"
            update_status(name, "idle", detail)
            logger.info(f"[{name}] Cycle complete — {detail}")
            consecutive_failures = 0
        except ImportError as e:
            update_status(name, "error", f"import failed: {e}")
            logger.error(f"[{name}] Import error: {e}")
            SHUTDOWN.wait(300)
            continue
        except Exception as e:
            consecutive_failures += 1
            update_status(name, "error", str(e)[:200])
            logger.error(f"[{name}] Cycle error: {e}\n{traceback.format_exc()}")
            if consecutive_failures >= 5:
                logger.error(f"[{name}] 5 consecutive failures — backing off 10 min")
                SHUTDOWN.wait(600)
                consecutive_failures = 0
                continue
        for _ in range(interval_minutes * 60):
            if SHUTDOWN.is_set():
                break
            time.sleep(1)
    update_status(name, "stopped")


def run_queue_processor(poll_interval: int = 10):
    """Queue Processor daemon — polls DB for queued tasks and processes them."""
    name = "QueueProc"
    update_status(name, "starting")
    while not SHUTDOWN.is_set():
        try:
            from dispatcher.queue import TaskQueue
            from dispatcher.router import create_event, route_task
            queue = TaskQueue()
            task = queue.dequeue()
            if task:
                update_status(name, "running", f"processing {task.get('task_type', '?')}")
                logger.info(f"[{name}] Processing queued task {task['task_id']} ({task.get('task_type', '?')})")
                try:
                    inputs = json.loads(task.get("inputs", "{}")) if isinstance(task.get("inputs"), str) else task.get("inputs", {})
                    event = create_event(
                        task_type=task["task_type"],
                        inputs=inputs,
                        client_id=task.get("client", "direct"),
                    )
                    result = route_task(event)
                    qa_data = result.get("qa", {})
                    qa_status = qa_data.get("status", "")
                    outputs = result.get("outputs", {})
                    cost = result.get("billing", {}).get("amount", 0.0)
                    queue.complete(task["task_id"], outputs=outputs, qa_status=qa_status, cost_usd=cost)
                    logger.info(f"[{name}] Task {task['task_id']} completed: QA={qa_status}")
                except Exception as e:
                    queue.fail(task["task_id"], error=str(e)[:500])
                    logger.error(f"[{name}] Task {task['task_id']} failed: {e}")
            else:
                update_status(name, "idle", "no queued tasks")
        except ImportError as e:
            update_status(name, "error", f"import failed: {e}")
            logger.error(f"[{name}] Import error: {e}")
            SHUTDOWN.wait(60)
            continue
        except Exception as e:
            update_status(name, "error", str(e)[:200])
            logger.error(f"[{name}] Error: {e}\n{traceback.format_exc()}")
        for _ in range(poll_interval):
            if SHUTDOWN.is_set():
                break
            time.sleep(1)
    update_status(name, "stopped")

# ââ Health Check Server ââââââââââââââââââââââââââââââââââââââââ

class HealthHandler(BaseHTTPRequestHandler):
    """Minimal HTTP health check for Railway."""

    def do_GET(self):
        if self.path == "/health" or self.path == "/":
            uptime = (datetime.now(timezone.utc) - WORKER_START_TIME).total_seconds()
            with STATUS_LOCK:
                status_copy = dict(DAEMON_STATUS)
            body = json.dumps({
                "status": "running",
                "uptime_seconds": round(uptime),
                "daemons": status_copy,
                "shutdown_requested": SHUTDOWN.is_set(),
            }, indent=2)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress default access logs


def run_health_server(port: int = 8080):
    """Run health check HTTP server on a separate port."""
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.timeout = 1
    logger.info(f"[Health] Listening on port {port}")
    while not SHUTDOWN.is_set():
        server.handle_request()
    server.server_close()


# ââ Main âââââââââââââââââââââââââââââââââââââââââââââââââââââââ

def graceful_shutdown(signum, frame):
    logger.info(f"Received signal {signum}. Shutting down all daemons...")
    SHUTDOWN.set()


def main():
    parser = argparse.ArgumentParser(description="DIGITAL LABOUR Unified Worker")
    parser.add_argument("--health", action="store_true", help="Just print health and exit")
    parser.add_argument("--health-port", type=int, default=int(os.getenv("WORKER_HEALTH_PORT", "8080")),
                        help="Port for health check HTTP server")
    args = parser.parse_args()

    if args.health:
        print(json.dumps({"status": "ok", "pid": os.getpid()}))
        return

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, graceful_shutdown)
    signal.signal(signal.SIGINT, graceful_shutdown)

    logger.info("=" * 60)
    logger.info("  DIGITAL LABOUR â UNIFIED WORKER")
    logger.info(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    logger.info("=" * 60)

    # Ensure data directories exist
    (PROJECT_ROOT / "data").mkdir(exist_ok=True)
    (PROJECT_ROOT / "data" / "nerve_logs").mkdir(exist_ok=True)
    (PROJECT_ROOT / "galactia" / "data").mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "galactia" / "data" / "cycle_logs").mkdir(parents=True, exist_ok=True)

    # Start all daemon threads
    daemons = [
        ("NERVE", run_nerve, {"interval_minutes": 60}),
        ("C-Suite", run_csuite_scheduler, {"interval_minutes": 30}),
        ("TaskSched", run_task_scheduler, {"interval_minutes": 5}),
        ("Revenue", run_revenue_daemon, {"interval_minutes": 30}),
        ("Resonance", run_resonance_sync, {"interval_minutes": 30}),
        ("Galactia", run_galactia, {"interval_minutes": 30}),
        ("QueueProc", run_queue_processor, {"poll_interval": 10}),
    ]

    threads = []
    for name, target, kwargs in daemons:
        t = threading.Thread(target=target, kwargs=kwargs, name=name, daemon=True)
        t.start()
        threads.append(t)
        logger.info(f"  [START] {name} daemon thread")

    # Start health check server
    health_thread = threading.Thread(
        target=run_health_server,
        kwargs={"port": args.health_port},
        name="HealthCheck",
        daemon=True,
    )
    health_thread.start()

    logger.info(f"\n  All {len(daemons)} daemons launched. Health check on :{args.health_port}")
    logger.info("  Press Ctrl+C or send SIGTERM to stop.\n")

    # Wait for shutdown signal
    try:
        while not SHUTDOWN.is_set():
            SHUTDOWN.wait(10)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received.")
        SHUTDOWN.set()

    # Wait for threads to finish (with timeout)
    logger.info("Waiting for daemon threads to stop...")
    for t in threads:
        t.join(timeout=10)

    logger.info("All daemons stopped. Worker exiting.")


if __name__ == "__main__":
    main()

