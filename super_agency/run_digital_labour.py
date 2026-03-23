#!/usr/bin/env python3
"""
Launch script for full DIGITAL LABOUR runtime mode.
DIGITAL LABOUR autonomous orchestration platform.
Updated for departmental matrix structure.
Features auto-restart watchdog for crashed daemon threads.
"""

import logging
import logging.handlers
import asyncio
import sys
import os
import time
import socket
import threading
import warnings
from pathlib import Path
from datetime import datetime
from typing import Any

# Silence Streamlit ScriptRunContext warnings when running outside Streamlit
warnings.filterwarnings("ignore", message=".*ScriptRunContext.*")
warnings.filterwarnings("ignore", module="streamlit")

from dotenv import load_dotenv  # noqa: E402
load_dotenv()

# Import departmental systems
from departmental_agent_manager import (  # noqa: E402
    DepartmentalAgentManager,
)
from agents.orchestrator import (  # noqa: E402
    main as run_departmental_orchestrator,
)
from agents.bus_subscribers import (  # noqa: E402
    register_all as register_bus_subscribers,
)
from matrix_maximizer import MatrixMaximizer  # noqa: E402
from mobile_command_center_simple import (  # noqa: E402
    app as mobile_app,
)
from operations_api import (  # noqa: E402
    app as operations_app,
)
from continuous_memory_backup import (  # noqa: E402
    ContinuousMemoryBackup,
)

# ── Centralized logging with rotation ─────────────────────────────────
_LOG_DIR = Path(__file__).resolve().parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)


class _JsonFormatter(logging.Formatter):
    """Structured JSON log formatter for machine-readable output."""

    def format(self, record):
        import json as _json
        entry = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            entry["exc"] = self.formatException(record.exc_info)
        return _json.dumps(entry, default=str)


_use_json = os.environ.get("LOG_FORMAT", "").lower() == "json"
_formatter = (
    _JsonFormatter() if _use_json
    else logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s "
        "%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)

# Console handler
_console = logging.StreamHandler()
_console.setFormatter(_formatter)

# Rotating file handler: 5 MB per file, keep 5 backups
_file_handler = logging.handlers.RotatingFileHandler(
    _LOG_DIR / "bit_rage_labour.log",
    maxBytes=5_000_000, backupCount=5,
    encoding="utf-8",
)
_file_handler.setFormatter(_formatter)

logging.basicConfig(level=logging.INFO, handlers=[_console, _file_handler])
logger = logging.getLogger(__name__)

# ── Runtime state (exposed for status endpoints) ────────────────────────
_runtime_state: dict[str, Any] = {
    "boot_time": None,
    "threads": {},
    "health_history": [],
}

HEALTH_INTERVAL_MINUTES = 5
MAX_HEALTH_HISTORY = 20
MAX_RESTARTS = 5


def get_runtime_state():
    """Return a JSON-safe snapshot of runtime state."""
    threads = {}
    for name, info in _runtime_state["threads"].items():
        t = info["thread"]
        threads[name] = {
            "alive": t.is_alive() if t else False,
            "restarts": info["restarts"],
            "last_restart": info["last_restart"],
        }
    return {
        "boot_time": _runtime_state["boot_time"],
        "uptime_seconds": (
            int(time.time() - _runtime_state["_boot_ts"])
            if _runtime_state.get("_boot_ts") else 0
        ),
        "threads": threads,
        "recent_health": _runtime_state["health_history"][-5:],
    }


# ── Thread starters ─────────────────────────────────────────────────────

def _start_matrix():
    matrix = MatrixMaximizer()
    matrix.run(host='0.0.0.0', port=8080, debug=False)


def _start_mobile():
    mobile_app.run(host='0.0.0.0', port=8081, debug=False, use_reloader=False)


def _start_operations_api():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    from hypercorn.config import Config
    from hypercorn.asyncio import serve
    config = Config()
    config.bind = ['0.0.0.0:5001']
    shutdown_event = asyncio.Event()
    loop.run_until_complete(
        serve(operations_app, config, shutdown_trigger=shutdown_event.wait)
    )


def _start_orchestrator():
    run_departmental_orchestrator()


def _start_memory_backup():
    backup = ContinuousMemoryBackup(backup_interval=600, max_backups=10)
    backup.start_continuous_backup()
    # Block this thread so it stays alive for the watchdog
    while backup.running:
        import time as _time
        _time.sleep(60)


def _launch_thread(name: str, target, register: bool = True):
    """Launch a daemon thread, optionally registering it for the watchdog."""
    t = threading.Thread(target=target, daemon=True, name=name)
    t.start()
    if register:
        _runtime_state["threads"][name] = {
            "thread": t,
            "starter": target,
            "restarts": 0,
            "last_restart": None,
        }
    logger.info(f"[BOOT] {name} started (tid={t.ident})")
    return t


# ── Watchdog ─────────────────────────────────────────────────────────────

def _watchdog_cycle():
    """Check thread health + port liveness; restart crashed threads."""
    now_str = datetime.now().isoformat(timespec="seconds")
    check = {"ts": now_str, "services": {}}

    for name, info in _runtime_state["threads"].items():
        t = info["thread"]
        alive = t.is_alive() if t else False

        if not alive and info["restarts"] < MAX_RESTARTS:
            logger.warning(
                f"[WATCHDOG] {name} DEAD — restarting "
                f"(attempt {info['restarts'] + 1}"
                f"/{MAX_RESTARTS})"
            )
            new_t = threading.Thread(
                target=info["starter"],
                daemon=True, name=name,
            )
            new_t.start()
            info["thread"] = new_t
            info["restarts"] += 1
            info["last_restart"] = now_str
            alive = True
        elif not alive:
            logger.error(
                f"[WATCHDOG] {name} DEAD — max "
                f"restarts ({MAX_RESTARTS}) reached, "
                "not restarting"
            )
            # Emit alert for permanently dead service
            try:
                from agents.resilience import _emit_alert
                _emit_alert(
                    "service_dead",
                    f"Service {name} exhausted "
                    f"{MAX_RESTARTS} restart attempts",
                    severity="CRITICAL",
                    component=name,
                )
            except Exception:
                pass

        check["services"][name] = "UP" if alive else "DOWN"

    # Port liveness
    for label, port in [("Matrix", 8080), ("Mobile", 8081), ("OpsAPI", 5001)]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(("127.0.0.1", port))
            s.close()
            check["services"][f"{label}_port"] = "UP"
        except OSError:
            check["services"][f"{label}_port"] = "DOWN"

    _runtime_state["health_history"].append(check)
    if len(_runtime_state["health_history"]) > MAX_HEALTH_HISTORY:
        hist = _runtime_state["health_history"]
        _runtime_state["health_history"] = (
            hist[-MAX_HEALTH_HISTORY:]
        )

    up = [k for k, v in check["services"].items() if v == "UP"]
    down = [k for k, v in check["services"].items() if v == "DOWN"]
    logger.info(
        f"[WATCHDOG] UP={len(up)} DOWN={len(down)} "
        f"{' | '.join(down) if down else 'all healthy'}"
    )


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    logger.info(
        "Starting DIGITAL LABOUR runtime - "
        "DIGITAL LABOUR Primary v4.0 "
        "(auto-restart watchdog)"
    )

    _runtime_state["boot_time"] = datetime.now().isoformat(timespec="seconds")
    _runtime_state["_boot_ts"] = time.time()

    # Initialize departmental agent manager
    root_path = Path(__file__).parent
    agent_manager = DepartmentalAgentManager(root_path)
    logger.info("Departmental Agent Manager initialized")

    # Wire message bus subscribers before launching threads
    register_bus_subscribers()

    # Bootstrap OpenClaw skill registry (core agents declare capabilities)
    try:
        sys.path.insert(0, str(root_path / "tools"))
        from skill_registry import (  # type: ignore[import-not-found]
            bootstrap_core,
        )
        n = bootstrap_core()
        logger.info(f"Skill registry bootstrapped: {n} core agents registered")
    except Exception as exc:
        logger.warning(f"Skill registry bootstrap skipped: {exc}")

    if not agent_manager.org_structure:
        logger.error("Failed to load organization structure, aborting")
        return

    org = agent_manager.org_structure
    org_name = org.get(
        'organization', {},
    ).get('name', 'Unknown')
    primary = org.get(
        'primary_directive', {},
    ).get('objective', 'N/A')
    logger.info(
        f"Organization loaded: {org_name} "
        f"| Primary mission: {primary}"
    )

    # Register DL agents in the hierarchy
    try:
        from agents.hierarchy import AgentRegistry
        _dl_registry = AgentRegistry()
        dl_manifest = org.get(
            'dl_integration_manifest', {},
        )
        if dl_manifest.get('status') == 'READY_FOR_MERGE':
            logger.info(
                "DL integration manifest: "
                "READY_FOR_MERGE — DL agents "
                "registered in hierarchy"
            )
    except Exception as exc:
        logger.warning(
            f"DL hierarchy registration skipped: {exc}"
        )

    # Boot all services via watchdog-registered threads
    _launch_thread("Matrix", _start_matrix)
    _launch_thread("Mobile", _start_mobile)
    _launch_thread("OpsAPI", _start_operations_api)
    _launch_thread("Orchestrator", _start_orchestrator)
    _launch_thread("MemoryBackup", _start_memory_backup)

    # 24/7 research scheduler daemon
    try:
        from tools.research_scheduler import (
            start_daemon_thread,
        )
        start_daemon_thread(check_interval_s=60)
        logger.info("Research scheduler daemon started")
    except Exception as exc:
        logger.warning(
            f"Research scheduler not started: {exc}"
        )

    # Autonomous brain — self-directing intelligence core
    try:
        from tools.autonomous_brain import (
            start_daemon_thread as start_brain,
        )
        start_brain(interval_s=900)
        logger.info(
            "Autonomous brain daemon started "
            "(15-min think cycles)"
        )
    except Exception as exc:
        logger.warning(
            f"Autonomous brain not started: {exc}"
        )

    # Research intelligence agent — ML-driven research analysis
    try:
        from agents.research_intelligence import (
            ResearchIntelligenceAgent,
        )
        _ri = ResearchIntelligenceAgent()

        def _ri_loop():
            import time as _t
            while True:
                try:
                    _ri.run_cycle()
                except Exception as _e:
                    logger.warning(
                        f"Research intelligence cycle "
                        f"error: {_e}"
                    )
                _t.sleep(1800)  # 30-min cycles

        _launch_thread(
            "ResearchIntelligence", _ri_loop,
        )
        logger.info(
            "Research intelligence agent started "
            "(30-min cycles)"
        )
    except Exception as exc:
        logger.warning(
            "Research intelligence not started: "
            f"{exc}"
        )

    # Alignment monitor — constitutional safety checks
    try:
        from agents.alignment_monitor import (
            AlignmentMonitor,
        )
        _am = AlignmentMonitor()

        def _am_loop():
            import time as _t
            while True:
                try:
                    _am.check_all()
                except Exception as _e:
                    logger.warning(
                        f"Alignment check error: {_e}"
                    )
                _t.sleep(3600)  # hourly checks

        _launch_thread("AlignmentMonitor", _am_loop)
        logger.info(
            "Alignment monitor started (hourly checks)"
        )
    except Exception as exc:
        logger.warning(
            f"Alignment monitor not started: {exc}"
        )

    # Learning agent — meta-learning from fleet performance
    try:
        from agents.learning_agent import LearningAgent
        _la = LearningAgent()

        def _la_loop():
            import time as _t
            while True:
                try:
                    _la.learn_cycle()
                except Exception as _e:
                    logger.warning(
                        f"Learning cycle error: {_e}"
                    )
                _t.sleep(3600)  # hourly learning

        _launch_thread("LearningAgent", _la_loop)
        logger.info(
            "Learning agent started (hourly cycles)"
        )
    except Exception as exc:
        logger.warning(
            f"Learning agent not started: {exc}"
        )

    # Context manager — context freshness & memory doctrine
    try:
        from agents.context_manager_agent import (
            ContextManagerAgent,
        )
        _cm = ContextManagerAgent()

        def _cm_loop():
            import time as _t
            while True:
                try:
                    _cm.run_cycle()
                except Exception as _e:
                    logger.warning(
                        f"Context manager error: {_e}"
                    )
                _t.sleep(900)  # 15-min cycles

        _launch_thread("ContextManager", _cm_loop)
        logger.info(
            "Context manager started (15-min cycles)"
        )
    except Exception as exc:
        logger.warning(
            f"Context manager not started: {exc}"
        )

    # QA manager — quality assurance gates
    try:
        from agents.qa_manager import QAManagerAgent
        _qa = QAManagerAgent()

        def _qa_loop():
            import time as _t
            while True:
                try:
                    _qa.run_cycle()
                except Exception as _e:
                    logger.warning(
                        f"QA manager error: {_e}"
                    )
                _t.sleep(1800)  # 30-min cycles

        _launch_thread("QAManager", _qa_loop)
        logger.info(
            "QA manager started (30-min cycles)"
        )
    except Exception as exc:
        logger.warning(
            f"QA manager not started: {exc}"
        )

    # Production manager — deployment & health gates
    try:
        from agents.production_manager import (
            ProductionManagerAgent,
        )
        _pm = ProductionManagerAgent()

        def _pm_loop():
            import time as _t
            while True:
                try:
                    _pm.run_cycle()
                except Exception as _e:
                    logger.warning(
                        f"Production manager error: "
                        f"{_e}"
                    )
                _t.sleep(900)  # 15-min cycles

        _launch_thread("ProductionManager", _pm_loop)
        logger.info(
            "Production manager started "
            "(15-min cycles)"
        )
    except Exception as exc:
        logger.warning(
            "Production manager not started: "
            f"{exc}"
        )

    # Automation manager — pipeline orchestration
    try:
        from agents.automation_manager import (
            AutomationManagerAgent,
        )
        _auto = AutomationManagerAgent()

        def _auto_loop():
            import time as _t
            while True:
                try:
                    _auto.run_cycle()
                except Exception as _e:
                    logger.warning(
                        f"Automation manager error: "
                        f"{_e}"
                    )
                _t.sleep(1800)  # 30-min cycles

        _launch_thread("AutomationManager", _auto_loop)
        logger.info(
            "Automation manager started "
            "(30-min cycles)"
        )
    except Exception as exc:
        logger.warning(
            "Automation manager not started: "
            f"{exc}"
        )

    logger.info(
        "DIGITAL LABOUR operational — "
        "DIGITAL LABOUR primary"
    )
    logger.info("Press Ctrl+C to shutdown")

    try:
        tick = 0
        while True:
            time.sleep(60)
            tick += 1
            if tick % HEALTH_INTERVAL_MINUTES == 0:
                _watchdog_cycle()
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
    finally:
        logger.info("DIGITAL LABOUR shutdown complete")


if __name__ == '__main__':
    main()
