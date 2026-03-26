"""BRS Self-Monitoring Bridge — Reads DIGITAL LABOUR execution layer data.

BRS (BitRage Resonance System) is the execution pillar — this system itself.
This bridge provides a uniform API (matching ncl_bridge + aac_bridge pattern)
for reading BRS operational state: fleet, KPIs, revenue, queue, agents.

Usage:
    from resonance.brs_bridge import brs

    fleet   = brs.fleet_status()       # Agent fleet overview
    kpis    = brs.kpi_summary()        # 7-day KPI roll-up
    revenue = brs.revenue_summary()    # 30-day revenue/cost/margin
    queue   = brs.queue_status()       # Live task queue depth
    health  = brs.system_health()      # Full health check
    digest  = brs.execution_digest()   # Combined digest for C-Suite
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class BRSBridge:
    """Read-only connector to BRS (DIGITAL LABOUR) execution layer data."""

    @property
    def available(self) -> bool:
        return True  # BRS is always available (it's this system)

    # ── Fleet Status ────────────────────────────────────────────

    def fleet_status(self) -> dict:
        """Agent fleet overview — active agents, paused agents, capabilities."""
        agents_dir = PROJECT_ROOT / "agents"
        agents = []
        if agents_dir.exists():
            for d in sorted(agents_dir.iterdir()):
                if d.is_dir() and (d / "runner.py").exists():
                    agents.append(d.name)

        paused = []
        pause_file = PROJECT_ROOT / "data" / "paused_agents.json"
        if pause_file.exists():
            try:
                paused = json.loads(pause_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        return {
            "total_agents": len(agents),
            "active_agents": [a for a in agents if a not in paused],
            "paused_agents": paused,
            "agent_list": agents,
        }

    # ── KPI Summary ─────────────────────────────────────────────

    def kpi_summary(self) -> dict:
        """7-day KPI roll-up from the KPI logger."""
        try:
            from dashboard.health import kpi_summary
            return kpi_summary()
        except Exception as e:
            logger.warning("BRS kpi_summary failed: %s", e)
            return {"error": str(e)}

    # ── Revenue ─────────────────────────────────────────────────

    def revenue_summary(self) -> dict:
        """30-day revenue/cost/margin from billing tracker."""
        try:
            from dashboard.health import revenue_summary
            return revenue_summary()
        except Exception as e:
            logger.warning("BRS revenue_summary failed: %s", e)
            return {"error": str(e)}

    # ── Queue Status ────────────────────────────────────────────

    def queue_status(self) -> dict:
        """Live task queue depth and state."""
        try:
            from dashboard.health import queue_status
            return queue_status()
        except Exception as e:
            logger.warning("BRS queue_status failed: %s", e)
            return {"error": str(e)}

    # ── System Health ───────────────────────────────────────────

    def system_health(self) -> dict:
        """Full system health check."""
        try:
            from dashboard.health import system_health
            return system_health()
        except Exception as e:
            logger.warning("BRS system_health failed: %s", e)
            return {"error": str(e)}

    # ── NERVE / Watchdog ────────────────────────────────────────

    def nerve_status(self) -> dict:
        """Watchdog / NERVE daemon status."""
        stop_flag = PROJECT_ROOT / "data" / "watchdog_stop.flag"
        pid_file = PROJECT_ROOT / "data" / "daemon_pids.json"

        status = "unknown"
        pids = {}
        if stop_flag.exists():
            status = "stopped"
        elif pid_file.exists():
            try:
                pids = json.loads(pid_file.read_text(encoding="utf-8"))
                status = "running" if pids else "idle"
            except Exception:
                status = "error"
        else:
            status = "idle"

        return {"status": status, "daemons": pids}

    # ── C-Suite ─────────────────────────────────────────────────

    def csuite_status(self) -> dict:
        """Latest C-Suite board verdicts."""
        board_file = PROJECT_ROOT / "data" / "csuite_last_board.json"
        if board_file.exists():
            try:
                return json.loads(board_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"status": "no_data"}

    # ── Data Freshness ──────────────────────────────────────────

    def data_freshness(self) -> dict:
        """Check freshness of BRS operational data sources."""
        result = {"available": True, "stale": False, "sources": {}}
        now = datetime.now(timezone.utc)

        checks = {
            "kpi_log": PROJECT_ROOT / "kpi" / "delivery_log.jsonl",
            "billing_db": PROJECT_ROOT / "data" / "billing.db",
            "task_queue": PROJECT_ROOT / "data" / "task_queue.db",
        }
        for name, path in checks.items():
            if path.exists():
                mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                age_hours = (now - mtime).total_seconds() / 3600
                is_stale = age_hours > 24
                result["sources"][name] = {
                    "exists": True, "age_hours": round(age_hours, 1), "stale": is_stale,
                }
                if is_stale:
                    result["stale"] = True
            else:
                result["sources"][name] = {"exists": False, "stale": True}

        return result

    # ── Combined Digest ─────────────────────────────────────────

    def execution_digest(self) -> dict:
        """Combined BRS execution digest for C-Suite / NCC master view."""
        fleet = self.fleet_status()
        kpi = self.kpi_summary()
        rev = self.revenue_summary()
        queue = self.queue_status()
        nerve = self.nerve_status()
        freshness = self.data_freshness()

        return {
            "brs_available": True,
            "data_stale": freshness.get("stale", False),
            "freshness": freshness.get("sources", {}),
            "fleet": fleet,
            "kpi_7d": kpi,
            "revenue_30d": rev,
            "queue": queue,
            "nerve": nerve,
        }


# Module-level singleton
brs = BRSBridge()
