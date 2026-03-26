"""Matrix Display Formatters — Human-readable display for each pillar monitor.

Each pillar has a display class that formats monitor data into:
  - Compact card (mobile-first, single glance)
  - Detailed panel (full breakdown for desktop/terminal)
  - Alert summary (actionable items only)

The UnifiedMatrixDisplay aggregates all four into a single display payload.

Usage:
    from resonance.matrix_display import unified_display

    # Full display payload (all 4 pillars + alerts)
    display = unified_display.render()

    # Individual pillar displays
    brs_card = unified_display.brs.render_card(monitor_data)
    ncc_panel = unified_display.ncc.render_panel(monitor_data)
"""

from __future__ import annotations

from datetime import datetime, timezone


# ═══════════════════════════════════════════════════════════════════
# Base Display
# ═══════════════════════════════════════════════════════════════════

class _PillarDisplay:
    """Base class for pillar display formatters."""

    PILLAR = ""
    ICON = ""

    def render_card(self, data: dict) -> dict:
        """Compact card — mobile-first single-glance view."""
        return {
            "pillar": self.PILLAR,
            "icon": self.ICON,
            "status": data.get("status", "UNKNOWN"),
            "grade": data.get("grade", "?"),
            "alert_count": len(data.get("alerts", [])),
            "headline": self._headline(data),
        }

    def render_panel(self, data: dict) -> dict:
        """Full detailed panel view."""
        return {
            "pillar": self.PILLAR,
            "icon": self.ICON,
            "role": data.get("role", ""),
            "status": data.get("status", "UNKNOWN"),
            "grade": data.get("grade", "?"),
            "timestamp": data.get("timestamp", ""),
            "metrics": data.get("metrics", {}),
            "freshness": data.get("freshness", {}),
            "alerts": data.get("alerts", []),
            "headline": self._headline(data),
            "details": self._details(data),
        }

    def render_alerts(self, data: dict) -> list[dict]:
        """Actionable alert items for this pillar."""
        alerts = []
        for a in data.get("alerts", []):
            alerts.append({
                "pillar": self.PILLAR,
                "severity": a.get("severity", "INFO"),
                "message": a.get("msg", ""),
            })
        return alerts

    def _headline(self, data: dict) -> str:
        return f"{self.PILLAR} {data.get('status', 'UNKNOWN')}"

    def _details(self, data: dict) -> list[str]:
        return []


# ═══════════════════════════════════════════════════════════════════
# BRS Display
# ═══════════════════════════════════════════════════════════════════

class BRSMatrixDisplay(_PillarDisplay):
    PILLAR = "BRS"
    ICON = "EXEC"

    def _headline(self, data: dict) -> str:
        metrics = data.get("metrics", {})
        fleet = metrics.get("fleet", {})
        queue = metrics.get("queue", {})
        active = len(fleet.get("active_agents", []))
        queued = queue.get("queued", 0)
        return f"{active} agents | {queued} queued | {data.get('grade', '?')}"

    def _details(self, data: dict) -> list[str]:
        lines = []
        metrics = data.get("metrics", {})

        fleet = metrics.get("fleet", {})
        lines.append(f"Fleet: {fleet.get('total_agents', 0)} total, "
                     f"{len(fleet.get('active_agents', []))} active, "
                     f"{len(fleet.get('paused_agents', []))} paused")

        kpi = metrics.get("kpi_7d", {})
        if kpi and "error" not in kpi:
            lines.append(f"KPI 7d: {kpi.get('total_tasks', 0)} tasks, "
                         f"pass rate {kpi.get('pass_rate', 'N/A')}%")

        rev = metrics.get("revenue_30d", {})
        if rev and "error" not in rev:
            lines.append(f"Revenue 30d: ${rev.get('total_revenue', 0):.2f} | "
                         f"Cost: ${rev.get('total_cost', 0):.2f} | "
                         f"Margin: {rev.get('gross_margin', 0):.1f}%")

        queue = metrics.get("queue", {})
        lines.append(f"Queue: {queue.get('queued', 0)} pending, "
                     f"{queue.get('running', 0)} running, "
                     f"{queue.get('completed', 0)} done")

        nerve = metrics.get("nerve", {})
        lines.append(f"NERVE: {nerve.get('status', 'unknown')}")

        return lines


# ═══════════════════════════════════════════════════════════════════
# NCC Display
# ═══════════════════════════════════════════════════════════════════

class NCCMatrixDisplay(_PillarDisplay):
    PILLAR = "NCC"
    ICON = "GOV"

    def _headline(self, data: dict) -> str:
        metrics = data.get("metrics", {})
        orch = metrics.get("orchestrator", {})
        relay = metrics.get("relay", {})
        routes = len(orch.get("routes", []))
        depth = relay.get("outbox_depth", 0)
        return f"Orchestrator {orch.get('status', '?')} | {routes} routes | outbox {depth}"

    def _details(self, data: dict) -> list[str]:
        lines = []
        metrics = data.get("metrics", {})

        orch = metrics.get("orchestrator", {})
        lines.append(f"Orchestrator: {orch.get('status', 'unknown')}")
        lines.append(f"Routes: {', '.join(orch.get('routes', []))}")
        lines.append(f"Adapters: {', '.join(orch.get('adapter_names', []))}")

        relay = metrics.get("relay", {})
        lines.append(f"Relay: {relay.get('status', 'unknown')} | "
                     f"Outbox: {relay.get('outbox_depth', 0)} events")

        decisions = orch.get("recent_decisions", [])
        if decisions:
            last = decisions[-1]
            dtype = last.get("directive", {}).get("type", "?")
            lines.append(f"Last decision: {dtype}")

        sync = metrics.get("sync_state", {})
        if sync.get("last_check"):
            lines.append(f"Last sync: {sync['last_check']}")

        return lines


# ═══════════════════════════════════════════════════════════════════
# NCL Display
# ═══════════════════════════════════════════════════════════════════

class NCLMatrixDisplay(_PillarDisplay):
    PILLAR = "NCL"
    ICON = "BRAIN"

    def _headline(self, data: dict) -> str:
        metrics = data.get("metrics", {})
        available = metrics.get("available", False)
        digest = metrics.get("digest", {}) or {}
        health_score = digest.get("trinity_health_score")
        score_str = f"health {health_score}" if health_score is not None else "no score"
        return f"{'Online' if available else 'Offline'} | {score_str}"

    def _details(self, data: dict) -> list[str]:
        lines = []
        metrics = data.get("metrics", {})
        freshness = data.get("freshness", {})

        available = metrics.get("available", False)
        lines.append(f"NCL Data: {'available' if available else 'NOT FOUND'}")

        digest = metrics.get("digest", {}) or {}
        if digest:
            lines.append(f"Trinity health: {digest.get('trinity_health_score', 'N/A')}")
            lines.append(f"Drift count: {digest.get('drift_count', 'N/A')}")
            agency_drift = digest.get("agency_drift")
            if agency_drift is not None:
                lines.append(f"AGENCY drift: {agency_drift}")
            lines.append(f"Daily brief: {'yes' if digest.get('has_daily_brief') else 'no'}")
            lines.append(f"Event log files: {digest.get('event_log_files', 0)}")

        trinity = metrics.get("trinity_health")
        if trinity:
            pillar_dirty = trinity.get("pillar_dirty", {})
            if pillar_dirty:
                parts = [f"{k}={v}" for k, v in pillar_dirty.items()]
                lines.append(f"Pillar dirty: {', '.join(parts)}")

        sources = freshness.get("sources", {})
        for name, info in sources.items():
            age = info.get("age_hours", "?")
            stale = " [STALE]" if info.get("stale") else ""
            lines.append(f"  {name}: {age}h old{stale}")

        events = metrics.get("recent_events", [])
        if events:
            lines.append(f"Recent events: {len(events)}")

        return lines


# ═══════════════════════════════════════════════════════════════════
# AAC Display
# ═══════════════════════════════════════════════════════════════════

class AACMatrixDisplay(_PillarDisplay):
    PILLAR = "AAC"
    ICON = "BANK"

    def _headline(self, data: dict) -> str:
        metrics = data.get("metrics", {})
        engine = metrics.get("engine_available", False)
        cached = metrics.get("cached_snapshot", {})
        dept_count = len(cached.get("departments", {})) if cached else 0
        return f"Engine {'online' if engine else 'offline'} | {dept_count} departments"

    def _details(self, data: dict) -> list[str]:
        lines = []
        metrics = data.get("metrics", {})
        freshness = data.get("freshness", {})

        engine = metrics.get("engine_available", False)
        lines.append(f"AAC Engine: {'connected' if engine else 'offline'}")

        cached = metrics.get("cached_snapshot")
        if cached and cached.get("departments"):
            for dept, dept_data in cached["departments"].items():
                if isinstance(dept_data, dict) and "error" not in dept_data:
                    metric_count = len(dept_data)
                    healthy_count = sum(1 for v in dept_data.values()
                                       if isinstance(v, dict) and v.get("healthy"))
                    lines.append(f"  {dept}: {healthy_count}/{metric_count} healthy")
                elif isinstance(dept_data, dict) and "error" in dept_data:
                    lines.append(f"  {dept}: ERROR — {dept_data['error'][:60]}")

        sources = freshness.get("sources", {})
        for name, info in sources.items():
            age = info.get("age_hours", "?")
            stale = " [STALE]" if info.get("stale") else ""
            lines.append(f"  {name}: {age}h old{stale}")

        return lines


# ═══════════════════════════════════════════════════════════════════
# Unified Display
# ═══════════════════════════════════════════════════════════════════

class UnifiedMatrixDisplay:
    """Renders the full 4-pillar matrix display from monitor data."""

    def __init__(self):
        self.brs = BRSMatrixDisplay()
        self.ncc = NCCMatrixDisplay()
        self.ncl = NCLMatrixDisplay()
        self.aac = AACMatrixDisplay()
        self._displays = {"brs": self.brs, "ncc": self.ncc,
                          "ncl": self.ncl, "aac": self.aac}

    def render(self, monitor_data: dict | None = None) -> dict:
        """Render full display payload from monitor data.

        If monitor_data is None, collects fresh data from unified_monitor.
        """
        if monitor_data is None:
            from resonance.matrix_monitor import unified_monitor
            monitor_data = unified_monitor.collect_all()

        timestamp = monitor_data.get("timestamp", datetime.now(timezone.utc).isoformat())
        pillars = monitor_data.get("pillars", {})

        cards = {}
        panels = {}
        all_alerts = []

        for name, display in self._displays.items():
            pillar_data = pillars.get(name, {})
            cards[name] = display.render_card(pillar_data)
            panels[name] = display.render_panel(pillar_data)
            all_alerts.extend(display.render_alerts(pillar_data))

        # Add cross-pillar checks
        for check in monitor_data.get("cross_pillar", []):
            all_alerts.append({
                "pillar": "CROSS",
                "severity": check.get("severity", "INFO"),
                "message": check.get("msg", ""),
            })

        # Sort alerts by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
        all_alerts.sort(key=lambda a: severity_order.get(a["severity"], 9))

        return {
            "timestamp": timestamp,
            "overall_status": monitor_data.get("overall_status", "UNKNOWN"),
            "overall_grade": monitor_data.get("overall_grade", "?"),
            "cards": cards,
            "panels": panels,
            "alerts": all_alerts,
            "alert_count": len(all_alerts),
            "critical_count": sum(1 for a in all_alerts if a["severity"] in ("CRITICAL", "HIGH")),
        }

    def render_card(self, pillar: str, monitor_data: dict | None = None) -> dict:
        """Render a single pillar card."""
        if monitor_data is None:
            from resonance.matrix_monitor import unified_monitor
            monitor_data = unified_monitor.collect_all()
        pillar_data = monitor_data.get("pillars", {}).get(pillar, {})
        display = self._displays.get(pillar)
        if display:
            return display.render_card(pillar_data)
        return {"error": f"Unknown pillar: {pillar}"}

    def render_panel(self, pillar: str, monitor_data: dict | None = None) -> dict:
        """Render a single pillar panel."""
        if monitor_data is None:
            from resonance.matrix_monitor import unified_monitor
            monitor_data = unified_monitor.collect_all()
        pillar_data = monitor_data.get("pillars", {}).get(pillar, {})
        display = self._displays.get(pillar)
        if display:
            return display.render_panel(pillar_data)
        return {"error": f"Unknown pillar: {pillar}"}


# Module-level singleton
unified_display = UnifiedMatrixDisplay()
