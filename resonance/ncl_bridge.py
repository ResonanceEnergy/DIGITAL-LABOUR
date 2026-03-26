"""NCL Intelligence Bridge — Reads BRAIN pillar data for AXIOM and ops.

Connects to NCL's data outputs:
  - Daily briefs: intelligence summaries for CEO morning standup
  - Trinity health: pillar drift scores for governance monitoring
  - Event stream: latest ingested events for situational awareness

Data is surfaced to AXIOM (CEO) and the ops dashboard.

Usage:
    from resonance.ncl_bridge import ncl

    brief = ncl.latest_daily_brief()    # Markdown daily brief
    health = ncl.trinity_health()       # Pillar health scores
    events = ncl.recent_events(limit=20)  # Latest event stream
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

NCL_DATA = Path(os.getenv("NCL_DATA_PATH", str(Path.home() / "NCL" / "data")))

# Data older than this (hours) is considered stale
NCL_STALE_THRESHOLD_HOURS = float(os.getenv("NCL_STALE_HOURS", "48"))


class NCLBridge:
    """Read-only connector to NCL BRAIN pillar data."""

    def __init__(self, data_root: Path = NCL_DATA):
        self.data_root = data_root
        self.derived_dir = data_root / "derived"
        self.daily_dir = data_root / "derived" / "daily"
        self.trinity_dir = data_root / "trinity"
        self.event_log_dir = data_root / "event_log"

    @property
    def available(self) -> bool:
        """Check if NCL data directory exists."""
        return self.data_root.exists()

    # ── Daily Briefs ────────────────────────────────────────────

    def latest_daily_brief(self) -> str | None:
        """Read the latest NCL daily brief (markdown)."""
        brief_file = self.daily_dir / "latest_daily_brief.md"
        if brief_file.exists():
            return brief_file.read_text(encoding="utf-8")
        # Fallback: find newest daily_brief_*.md
        briefs = sorted(self.daily_dir.glob("daily_brief_*.md"), reverse=True)
        if briefs:
            return briefs[0].read_text(encoding="utf-8")
        return None

    def daily_brief_for_date(self, date_str: str) -> str | None:
        """Read daily brief for a specific date (YYYY-MM-DD)."""
        brief_file = self.daily_dir / f"daily_brief_{date_str}.md"
        if brief_file.exists():
            return brief_file.read_text(encoding="utf-8")
        return None

    # ── Trinity Health ──────────────────────────────────────────

    def trinity_health(self) -> dict | None:
        """Get latest trinity health score + pillar drift data."""
        ledger = self.trinity_dir / "feedback_ledger.ndjson"
        if not ledger.exists():
            return None
        # Read last line of the ledger
        lines = ledger.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return None
        try:
            return json.loads(lines[-1])
        except json.JSONDecodeError:
            return None

    def trinity_history(self, limit: int = 10) -> list[dict]:
        """Get recent trinity health entries."""
        ledger = self.trinity_dir / "feedback_ledger.ndjson"
        if not ledger.exists():
            return []
        lines = ledger.read_text(encoding="utf-8").strip().splitlines()
        result = []
        for line in lines[-limit:]:
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return result

    # ── Event Stream ────────────────────────────────────────────

    def recent_events(self, limit: int = 20) -> list[dict]:
        """Get the most recent events from the NCL event log."""
        # Find newest event log files
        log_files = sorted(self.event_log_dir.glob("**/*.ndjson"), reverse=True)
        events = []
        for log_file in log_files:
            if len(events) >= limit:
                break
            lines = log_file.read_text(encoding="utf-8").strip().splitlines()
            for line in reversed(lines):
                if len(events) >= limit:
                    break
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return events

    # ── Derived Data ────────────────────────────────────────────

    def derived_summaries(self, limit: int = 5) -> list[dict]:
        """Get recent derived summary events."""
        derived_files = sorted(self.derived_dir.glob("*.ndjson"), reverse=True)
        results = []
        for f in derived_files[:limit]:
            lines = f.read_text(encoding="utf-8").strip().splitlines()
            for line in lines:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return results

    # ── AGENCY Pillar Status ────────────────────────────────────

    def agency_drift_score(self) -> int | None:
        """Get AGENCY pillar's current drift score from trinity."""
        health = self.trinity_health()
        if health and "pillar_dirty" in health:
            return health["pillar_dirty"].get("AGENCY")
        return None

    # ── Summary for C-Suite ─────────────────────────────────────

    def data_freshness(self) -> dict:
        """Check freshness of NCL data sources. Returns staleness info."""
        result = {"available": self.available, "stale": False, "sources": {}}
        if not self.available:
            result["stale"] = True
            result["reason"] = "NCL data directory not found"
            return result

        now = datetime.now(timezone.utc)
        checks = {
            "daily_brief": self.daily_dir / "latest_daily_brief.md",
            "trinity_ledger": self.trinity_dir / "feedback_ledger.ndjson",
        }
        for name, path in checks.items():
            if path.exists():
                mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                age_hours = (now - mtime).total_seconds() / 3600
                is_stale = age_hours > NCL_STALE_THRESHOLD_HOURS
                result["sources"][name] = {
                    "exists": True, "age_hours": round(age_hours, 1), "stale": is_stale,
                }
                if is_stale:
                    result["stale"] = True
            else:
                result["sources"][name] = {"exists": False, "stale": True}
                result["stale"] = True

        return result

    def intelligence_digest(self) -> dict:
        """Compiled digest for AXIOM (CEO) morning standup."""
        health = self.trinity_health()
        freshness = self.data_freshness()
        return {
            "ncl_available": self.available,
            "data_stale": freshness.get("stale", True),
            "freshness": freshness.get("sources", {}),
            "trinity_health_score": health.get("health_score") if health else None,
            "drift_count": health.get("drift_count") if health else None,
            "pillar_dirty": health.get("pillar_dirty") if health else None,
            "agency_drift": self.agency_drift_score(),
            "has_daily_brief": (self.daily_dir / "latest_daily_brief.md").exists(),
            "event_log_files": len(list(self.event_log_dir.glob("**/*.ndjson"))) if self.event_log_dir.exists() else 0,
        }


# Module-level singleton
ncl = NCLBridge()
