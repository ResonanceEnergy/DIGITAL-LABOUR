"""Unified Matrix Monitor — Cross-pillar monitoring for BRS / NCC / NCL / AAC.

Each pillar has its own monitor class that collects status, metrics, and health.
The UnifiedMatrixMonitor aggregates all four into a single situational picture.

Pillars:
  BRS  — BitRage Resonance System (execution layer — this system)
  NCC  — Natrix Command & Control (governance / orchestrator)
  NCL  — Neural Cognitive Lattice (intelligence / BRAIN)
  AAC  — Autonomous Audit Controller (financial / BANK)

Usage:
    from resonance.matrix_monitor import unified_monitor

    # Individual pillar monitors
    brs_state = unified_monitor.brs.collect()
    ncc_state = unified_monitor.ncc.collect()
    ncl_state = unified_monitor.ncl.collect()
    aac_state = unified_monitor.aac.collect()

    # Full cross-pillar snapshot
    full = unified_monitor.collect_all()
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ═══════════════════════════════════════════════════════════════════
# BRS Matrix Monitor
# ═══════════════════════════════════════════════════════════════════

class BRSMatrixMonitor:
    """Monitor for the BRS execution layer (DIGITAL LABOUR agents)."""

    PILLAR = "BRS"
    ROLE = "Execution"

    def collect(self) -> dict:
        """Collect full BRS state snapshot."""
        from resonance.brs_bridge import brs

        fleet = brs.fleet_status()
        kpi = brs.kpi_summary()
        rev = brs.revenue_summary()
        queue = brs.queue_status()
        nerve = brs.nerve_status()
        freshness = brs.data_freshness()

        # Derive health grade
        grade = self._grade(fleet, kpi, queue, freshness)

        return {
            "pillar": self.PILLAR,
            "role": self.ROLE,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": grade["status"],
            "grade": grade["grade"],
            "alerts": grade["alerts"],
            "metrics": {
                "fleet": fleet,
                "kpi_7d": kpi,
                "revenue_30d": rev,
                "queue": queue,
                "nerve": nerve,
            },
            "freshness": freshness,
        }

    def _grade(self, fleet: dict, kpi: dict, queue: dict, freshness: dict) -> dict:
        alerts = []
        status = "GREEN"

        # Check paused agents
        paused = fleet.get("paused_agents", [])
        if len(paused) > 3:
            alerts.append({"severity": "HIGH", "msg": f"{len(paused)} agents paused"})
            status = "AMBER"

        # Check queue depth
        queued = queue.get("queued", 0)
        if queued > 50:
            alerts.append({"severity": "HIGH", "msg": f"Queue depth {queued} (>50)"})
            status = "RED"
        elif queued > 20:
            alerts.append({"severity": "MEDIUM", "msg": f"Queue depth {queued} (>20)"})
            if status == "GREEN":
                status = "AMBER"

        # Check pass rate
        pass_rate = kpi.get("pass_rate", "N/A")
        if isinstance(pass_rate, (int, float)) and pass_rate < 70:
            alerts.append({"severity": "HIGH", "msg": f"QA pass rate {pass_rate}% (<70%)"})
            status = "RED"

        # Data freshness
        if freshness.get("stale"):
            alerts.append({"severity": "MEDIUM", "msg": "BRS data sources stale"})
            if status == "GREEN":
                status = "AMBER"

        grade = "A" if status == "GREEN" else "B" if status == "AMBER" else "C"
        return {"status": status, "grade": grade, "alerts": alerts}


# ═══════════════════════════════════════════════════════════════════
# NCC Matrix Monitor
# ═══════════════════════════════════════════════════════════════════

class NCCMatrixMonitor:
    """Monitor for NCC governance layer (orchestrator + relay)."""

    PILLAR = "NCC"
    ROLE = "Governance"

    def collect(self) -> dict:
        """Collect full NCC state snapshot."""
        timestamp = datetime.now(timezone.utc).isoformat()

        # Orchestrator health
        try:
            from NCC.ncc_orchestrator import health as ncc_health, pending_decisions
            orchestrator = {
                "status": "online",
                **ncc_health(),
                "recent_decisions": pending_decisions(5),
            }
        except Exception as e:
            orchestrator = {"status": "error", "error": str(e)}

        # Relay health
        try:
            from resonance.ncc_bridge import ncc
            relay_health = ncc.relay_health()
            outbox_dir = PROJECT_ROOT / "data" / "ncc_outbox"
            outbox_depth = 0
            if outbox_dir.exists():
                for f in outbox_dir.glob("*.ndjson"):
                    outbox_depth += len(f.read_text(encoding="utf-8").strip().splitlines())
            relay = {
                "status": "online" if relay_health else "offline",
                "health": relay_health,
                "outbox_depth": outbox_depth,
            }
        except Exception as e:
            relay = {"status": "error", "error": str(e)}

        # Sync state
        sync_file = PROJECT_ROOT / "data" / "resonance_sync_state.json"
        try:
            sync_state = json.loads(sync_file.read_text("utf-8")) if sync_file.exists() else {}
        except Exception:
            sync_state = {}

        grade = self._grade(orchestrator, relay)

        return {
            "pillar": self.PILLAR,
            "role": self.ROLE,
            "timestamp": timestamp,
            "status": grade["status"],
            "grade": grade["grade"],
            "alerts": grade["alerts"],
            "metrics": {
                "orchestrator": orchestrator,
                "relay": relay,
                "sync_state": sync_state,
            },
            "freshness": {
                "available": orchestrator.get("status") == "online",
                "relay_online": relay.get("status") == "online",
                "outbox_depth": relay.get("outbox_depth", 0),
            },
        }

    def _grade(self, orchestrator: dict, relay: dict) -> dict:
        alerts = []
        status = "GREEN"

        if orchestrator.get("status") != "online":
            alerts.append({"severity": "CRITICAL", "msg": "NCC Orchestrator offline"})
            status = "RED"

        if relay.get("status") != "online":
            alerts.append({"severity": "HIGH", "msg": "NCC Relay offline"})
            if status == "GREEN":
                status = "AMBER"

        depth = relay.get("outbox_depth", 0)
        if depth > 100:
            alerts.append({"severity": "HIGH", "msg": f"Outbox depth {depth} (>100)"})
            status = "RED"
        elif depth > 50:
            alerts.append({"severity": "MEDIUM", "msg": f"Outbox depth {depth} (>50)"})
            if status == "GREEN":
                status = "AMBER"

        grade = "A" if status == "GREEN" else "B" if status == "AMBER" else "C"
        return {"status": status, "grade": grade, "alerts": alerts}


# ═══════════════════════════════════════════════════════════════════
# NCL Matrix Monitor
# ═══════════════════════════════════════════════════════════════════

class NCLMatrixMonitor:
    """Monitor for NCL intelligence layer (BRAIN pillar)."""

    PILLAR = "NCL"
    ROLE = "Intelligence"

    def collect(self) -> dict:
        """Collect full NCL state snapshot."""
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            from resonance.ncl_bridge import ncl
            available = ncl.available
            digest = ncl.intelligence_digest() if available else None
            freshness = ncl.data_freshness()
            trinity = ncl.trinity_health() if available else None
            recent_events = ncl.recent_events(limit=5) if available else []
        except Exception as e:
            available = False
            digest = None
            freshness = {"available": False, "stale": True, "error": str(e)}
            trinity = None
            recent_events = []

        grade = self._grade(available, freshness, trinity)

        return {
            "pillar": self.PILLAR,
            "role": self.ROLE,
            "timestamp": timestamp,
            "status": grade["status"],
            "grade": grade["grade"],
            "alerts": grade["alerts"],
            "metrics": {
                "available": available,
                "digest": digest,
                "trinity_health": trinity,
                "recent_events": recent_events,
            },
            "freshness": freshness,
        }

    def _grade(self, available: bool, freshness: dict, trinity: dict | None) -> dict:
        alerts = []
        status = "GREEN"

        if not available:
            alerts.append({"severity": "HIGH", "msg": "NCL data directory not found"})
            status = "RED"
            return {"status": status, "grade": "C", "alerts": alerts}

        if freshness.get("stale"):
            alerts.append({"severity": "MEDIUM", "msg": "NCL intelligence data stale"})
            if status == "GREEN":
                status = "AMBER"

        # Trinity drift
        if trinity:
            drift = trinity.get("drift_count", 0)
            if drift and drift > 3:
                alerts.append({"severity": "HIGH", "msg": f"Trinity drift count {drift} (>3)"})
                status = "RED"
            elif drift and drift > 1:
                alerts.append({"severity": "MEDIUM", "msg": f"Trinity drift count {drift}"})
                if status == "GREEN":
                    status = "AMBER"

        grade = "A" if status == "GREEN" else "B" if status == "AMBER" else "C"
        return {"status": status, "grade": grade, "alerts": alerts}


# ═══════════════════════════════════════════════════════════════════
# AAC Matrix Monitor
# ═══════════════════════════════════════════════════════════════════

class AACMatrixMonitor:
    """Monitor for AAC financial layer (BANK pillar)."""

    PILLAR = "AAC"
    ROLE = "Financial"

    def collect(self) -> dict:
        """Collect full AAC state snapshot."""
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            from resonance.aac_bridge import aac
            freshness = aac.data_freshness()
            engine_available = freshness.get("engine_available", False)

            # Read cached snapshot (don't call live API on every monitor poll)
            cache_file = PROJECT_ROOT / "data" / "resonance_cache" / "aac_snapshot.json"
            cached = None
            if cache_file.exists():
                try:
                    cached = json.loads(cache_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
        except Exception as e:
            freshness = {"engine_available": False, "stale": True, "error": str(e)}
            engine_available = False
            cached = None

        grade = self._grade(engine_available, freshness, cached)

        return {
            "pillar": self.PILLAR,
            "role": self.ROLE,
            "timestamp": timestamp,
            "status": grade["status"],
            "grade": grade["grade"],
            "alerts": grade["alerts"],
            "metrics": {
                "engine_available": engine_available,
                "cached_snapshot": cached,
            },
            "freshness": freshness,
        }

    def _grade(self, engine_available: bool, freshness: dict, cached: dict | None) -> dict:
        alerts = []
        status = "GREEN"

        if not engine_available:
            alerts.append({"severity": "MEDIUM", "msg": "AAC engine not available"})
            if status == "GREEN":
                status = "AMBER"

        if freshness.get("stale"):
            alerts.append({"severity": "MEDIUM", "msg": "AAC financial data stale"})
            if status == "GREEN":
                status = "AMBER"

        if cached and cached.get("status") == "offline":
            alerts.append({"severity": "HIGH", "msg": "AAC departments offline"})
            status = "RED"

        grade = "A" if status == "GREEN" else "B" if status == "AMBER" else "C"
        return {"status": status, "grade": grade, "alerts": alerts}


# ═══════════════════════════════════════════════════════════════════
# Unified Matrix Monitor
# ═══════════════════════════════════════════════════════════════════

class UnifiedMatrixMonitor:
    """Cross-pillar aggregator — collects from all four pillar monitors.

    Provides:
      - Individual pillar snapshots via .brs / .ncc / .ncl / .aac
      - Combined snapshot via .collect_all()
      - Overall system grade via ._overall_grade()
    """

    def __init__(self):
        self.brs = BRSMatrixMonitor()
        self.ncc = NCCMatrixMonitor()
        self.ncl = NCLMatrixMonitor()
        self.aac = AACMatrixMonitor()

    def collect_all(self) -> dict:
        """Collect snapshots from all four pillars + compute overall grade."""
        timestamp = datetime.now(timezone.utc).isoformat()

        pillars = {}
        for name, monitor in [("brs", self.brs), ("ncc", self.ncc),
                               ("ncl", self.ncl), ("aac", self.aac)]:
            try:
                pillars[name] = monitor.collect()
            except Exception as e:
                logger.error("Matrix monitor %s failed: %s", name, e)
                pillars[name] = {
                    "pillar": name.upper(),
                    "status": "ERROR",
                    "grade": "F",
                    "error": str(e),
                    "alerts": [{"severity": "CRITICAL", "msg": f"Monitor collection failed: {e}"}],
                }

        overall = self._overall_grade(pillars)

        return {
            "timestamp": timestamp,
            "overall_status": overall["status"],
            "overall_grade": overall["grade"],
            "system_alerts": overall["alerts"],
            "pillars": pillars,
            "cross_pillar": self._cross_pillar_checks(pillars),
        }

    def _overall_grade(self, pillars: dict) -> dict:
        """Compute overall system grade from pillar grades."""
        all_alerts = []
        statuses = []

        for name, data in pillars.items():
            statuses.append(data.get("status", "ERROR"))
            for alert in data.get("alerts", []):
                alert_copy = dict(alert)
                alert_copy["pillar"] = name.upper()
                all_alerts.append(alert_copy)

        red_count = statuses.count("RED") + statuses.count("ERROR")
        amber_count = statuses.count("AMBER")

        if red_count >= 2:
            status = "RED"
        elif red_count >= 1:
            status = "AMBER"
        elif amber_count >= 2:
            status = "AMBER"
        else:
            status = "GREEN"

        grade_map = {"GREEN": "A", "AMBER": "B", "RED": "C"}
        return {"status": status, "grade": grade_map.get(status, "C"), "alerts": all_alerts}

    def _cross_pillar_checks(self, pillars: dict) -> list[dict]:
        """Run cross-pillar integration health checks."""
        checks = []

        # Check NCC relay can reach governance
        ncc_data = pillars.get("ncc", {})
        relay_status = ncc_data.get("metrics", {}).get("relay", {}).get("status")
        orch_status = ncc_data.get("metrics", {}).get("orchestrator", {}).get("status")

        if relay_status == "offline" and orch_status == "online":
            checks.append({
                "check": "ncc_relay_disconnect",
                "severity": "HIGH",
                "msg": "NCC Orchestrator online but Relay offline — events not propagating",
            })

        # Check NCL freshness impacts BRS decisions
        ncl_data = pillars.get("ncl", {})
        brs_data = pillars.get("brs", {})
        if ncl_data.get("freshness", {}).get("stale") and brs_data.get("status") == "GREEN":
            checks.append({
                "check": "ncl_stale_brs_active",
                "severity": "MEDIUM",
                "msg": "NCL intelligence stale while BRS executing — decisions may lack context",
            })

        # Check AAC offline + revenue data dependency
        aac_data = pillars.get("aac", {})
        if not aac_data.get("metrics", {}).get("engine_available") and brs_data.get("status") != "RED":
            checks.append({
                "check": "aac_offline_brs_active",
                "severity": "LOW",
                "msg": "AAC engine offline — financial visibility limited",
            })

        # Check all pillars reporting
        for name in ("brs", "ncc", "ncl", "aac"):
            if pillars.get(name, {}).get("status") == "ERROR":
                checks.append({
                    "check": f"{name}_monitor_error",
                    "severity": "CRITICAL",
                    "msg": f"{name.upper()} monitor failed to collect data",
                })

        return checks


# Module-level singleton
unified_monitor = UnifiedMatrixMonitor()
