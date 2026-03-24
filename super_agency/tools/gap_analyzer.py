#!/usr/bin/env python3
"""
Gap Analyzer -- Mandate vs Reality Assessment
=============================================
Compares system mandates, goals, and capabilities
against actual state to identify actionable gaps.

Gap categories:
  - Mandate: goals not being measured or met
  - Research: projects with stale/missing research
  - Pipeline: stages that fail or never run
  - Knowledge: topics with no ingested content
  - Integration: subsystems not connected

Usage::

    python tools/gap_analyzer.py          # full analysis
    python tools/gap_analyzer.py summary  # top gaps only
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "agents"))

from agents.common import (  # noqa: E402
    Log, ensure_dir, now_iso,
)

# ── Paths ──────────────────────────────────────────────────

MANDATES = ROOT / "agent_mandates.json"
PROTOCOLS = ROOT / "agent_protocols.json"
SETTINGS_FILE = ROOT / "config" / "settings.json"
SKILLS = ROOT / "config" / "skill_registry.json"
PROJECTS = ROOT / "config" / "research_projects.json"
WATCHLIST = ROOT / "config" / "intelligence_watchlist.json"
SCHED_STATE = ROOT / "config" / "scheduler_state.json"
METRICS_HIST = (
    ROOT / "reports" / "metrics" / "metrics_history.json"
)
KNOWLEDGE_DIR = ROOT / "knowledge" / "secondbrain"
REPORTS_DIR = ROOT / "reports"
IDEAS_DIR = ROOT / "reports" / "ideas"
RESEARCH_DIR = ROOT / "reports" / "research"
INTEL_DIR = ROOT / "reports" / "intelligence"
GAPS_DIR = ROOT / "reports" / "gaps"
BRAIN_STATE = ROOT / "config" / "brain_state.json"

ensure_dir(GAPS_DIR)

# Message bus (best-effort)
_bus: Any = None
try:
    from agents.message_bus import bus
    _bus = bus
except Exception:
    pass


def _emit(topic: str, payload: Any = None):
    if _bus:
        _bus.publish(  # type: ignore[union-attr]
            topic, payload or {},
            source="gap_analyzer",
        )


# ── Helpers ────────────────────────────────────────────────

def _load_json(path: Path) -> dict:
    """Safely load a JSON file (must be object)."""
    if not path.exists():
        return {}
    try:
        data = json.loads(
            path.read_text(encoding="utf-8"),
        )
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _file_age_hours(path: Path) -> float | None:
    """Age of a file in hours, or None if missing."""
    if not path.exists():
        return None
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    delta = datetime.now() - mtime
    return delta.total_seconds() / 3600


SEVERITY_WEIGHT = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
}


# ── GapAnalyzer ────────────────────────────────────────────

class GapAnalyzer:
    """Analyzes gaps between mandates and reality."""

    def __init__(self):
        self.mandates = _load_json(MANDATES)
        self.protocols = _load_json(PROTOCOLS)
        self.settings = _load_json(SETTINGS_FILE)
        self.skills = _load_json(SKILLS)
        self.projects = _load_json(PROJECTS)
        self.watchlist = _load_json(WATCHLIST)
        self.scheduler = _load_json(SCHED_STATE)
        self.metrics_hist = self._load_metrics()

    @staticmethod
    def _load_metrics() -> dict:
        """Load metrics history (may be list or dict)."""
        if not METRICS_HIST.exists():
            return {}
        try:
            data = json.loads(
                METRICS_HIST.read_text(encoding="utf-8"),
            )
        except (json.JSONDecodeError, OSError):
            return {}
        if isinstance(data, list):
            return {"snapshots": data}
        if isinstance(data, dict):
            return data
        return {}

    # ── Full Analysis ──────────────────────────────────────

    def analyze(self) -> dict[str, Any]:
        """Full gap analysis across all dimensions."""
        gaps: dict[str, Any] = {
            "timestamp": now_iso(),
            "mandate_gaps": self.mandate_gaps(),
            "research_gaps": self.research_gaps(),
            "pipeline_gaps": self.pipeline_gaps(),
            "knowledge_gaps": self.knowledge_gaps(),
            "integration_gaps": self.integration_gaps(),
            "summary": {},
        }

        all_gaps: list[dict] = []
        for cat in (
            "mandate_gaps", "research_gaps",
            "pipeline_gaps", "knowledge_gaps",
            "integration_gaps",
        ):
            all_gaps.extend(gaps[cat])

        by_sev: dict[str, int] = defaultdict(int)
        for g in all_gaps:
            by_sev[g.get("severity", "LOW")] += 1

        gaps["summary"] = {
            "total_gaps": len(all_gaps),
            "critical": by_sev["CRITICAL"],
            "high": by_sev["HIGH"],
            "medium": by_sev["MEDIUM"],
            "low": by_sev["LOW"],
            "top_actions": self._top_actions(all_gaps),
        }

        # Persist
        out = GAPS_DIR / "latest_gaps.json"
        out.write_text(
            json.dumps(gaps, indent=2, default=str),
            encoding="utf-8",
        )
        _emit("gaps.analyzed", gaps["summary"])
        return gaps

    # ── Mandate Gaps ───────────────────────────────────────

    def mandate_gaps(self) -> list[dict]:
        """Mandates not being measured or met."""
        gaps: list[dict] = []
        mandates = self.mandates.get("mandates", {})
        goals = self.mandates.get("goals", {})

        # Efficiency mandate: task completion tracking?
        if "efficiency" in mandates:
            snapshots = self.metrics_hist.get(
                "snapshots", [],
            )
            if not snapshots:
                gaps.append({
                    "id": "mandate_efficiency_untracked",
                    "category": "mandate",
                    "severity": "HIGH",
                    "title": (
                        "Efficiency mandate has no "
                        "metrics"
                    ),
                    "detail": (
                        "Mandate requires 95% "
                        "completion within SLA but "
                        "no metrics track task "
                        "completion rates"
                    ),
                    "action": "run_metrics",
                })

        # Reliability mandate: log file exists?
        if "reliability" in mandates:
            log_f = ROOT / "logs" / "bit_rage_labour.log"
            if not log_f.exists():
                gaps.append({
                    "id": "mandate_reliability_no_logs",
                    "category": "mandate",
                    "severity": "CRITICAL",
                    "title": (
                        "No runtime logs for uptime "
                        "tracking"
                    ),
                    "detail": (
                        "Mandate requires 99.9% "
                        "uptime but no log file "
                        "exists to measure it"
                    ),
                    "action": "run_validation",
                })

        # Innovation mandate: ideas generated?
        if "innovation" in mandates:
            ideas = list(IDEAS_DIR.glob("*.json"))
            if not ideas:
                gaps.append({
                    "id": "mandate_innovation_no_ideas",
                    "category": "mandate",
                    "severity": "HIGH",
                    "title": "No idea generation output",
                    "detail": (
                        "Mandate requires 1+ "
                        "improvement per week but "
                        "no ideas generated"
                    ),
                    "action": "run_ideas",
                })
            else:
                newest = max(
                    ideas,
                    key=lambda f: f.stat().st_mtime,
                )
                age = _file_age_hours(newest)
                if age and age > 168:
                    gaps.append({
                        "id": (
                            "mandate_innovation_stale"
                        ),
                        "category": "mandate",
                        "severity": "MEDIUM",
                        "title": (
                            "Idea generation is stale"
                        ),
                        "detail": (
                            f"Latest ideas are "
                            f"{age:.0f}h old (>7 days)"
                        ),
                        "action": "run_ideas",
                    })

        # Long-term goal: "Full autonomous operation"
        long_term = goals.get("long_term", [])
        if any(
            "autonomous" in g.lower()
            for g in long_term
        ):
            if not BRAIN_STATE.exists():
                gaps.append({
                    "id": "goal_autonomy_not_active",
                    "category": "mandate",
                    "severity": "HIGH",
                    "title": (
                        "Autonomy goal: brain not "
                        "yet active"
                    ),
                    "detail": (
                        "Long-term goal is full "
                        "autonomous operation but "
                        "the autonomous brain has "
                        "no state file"
                    ),
                    "action": "run_brain_cycle",
                })

        return gaps

    # ── Research Gaps ──────────────────────────────────────

    def research_gaps(self) -> list[dict]:
        """Projects with stale or missing research."""
        gaps: list[dict] = []
        projects = self.projects.get("projects", [])

        for proj in projects:
            name = proj.get("name", "Unknown")
            repos = proj.get("repos", [])
            milestones = proj.get("milestones", [])

            # Check for any research output
            slug = name.lower().replace(" ", "_")
            proj_hits = list(
                RESEARCH_DIR.glob(f"*{slug}*"),
            )
            if not proj_hits:
                repo_hits: list[Path] = []
                for r in repos:
                    rn = (
                        r if isinstance(r, str)
                        else r.get("name", "")
                    )
                    repo_hits.extend(
                        RESEARCH_DIR.glob(f"*{rn}*"),
                    )
                if not repo_hits:
                    gaps.append({
                        "id": (
                            f"research_{slug}_no_output"
                        ),
                        "category": "research",
                        "severity": "MEDIUM",
                        "title": (
                            f"No research output: "
                            f"{name}"
                        ),
                        "detail": (
                            f"Project '{name}' with "
                            f"{len(repos)} repos has "
                            "no research reports"
                        ),
                        "action": "run_research",
                    })

            # Check incomplete milestones
            incomplete = [
                m for m in milestones
                if m.get("status") != "complete"
            ]
            if (
                milestones
                and len(incomplete) > len(milestones) * 0.7
            ):
                gaps.append({
                    "id": (
                        f"research_{slug}_milestones"
                    ),
                    "category": "research",
                    "severity": "MEDIUM",
                    "title": (
                        f"Most milestones incomplete"
                        f": {name}"
                    ),
                    "detail": (
                        f"{len(incomplete)}/"
                        f"{len(milestones)} "
                        f"milestones incomplete"
                    ),
                    "action": "run_research",
                })

        return gaps

    # ── Pipeline Gaps ──────────────────────────────────────

    def pipeline_gaps(self) -> list[dict]:
        """Stages that fail or never run."""
        gaps: list[dict] = []

        # Scheduler cycle freshness
        last_runs = self.scheduler.get("last_run", {})
        if not last_runs:
            gaps.append({
                "id": "pipeline_scheduler_no_state",
                "category": "pipeline",
                "severity": "CRITICAL",
                "title": (
                    "Scheduler has no run history"
                ),
                "detail": (
                    "No scheduler state found -- "
                    "research cycles may not be "
                    "running"
                ),
                "action": "run_research",
            })
        else:
            expected_h = {
                "fast": 1, "standard": 8,
                "deep": 48, "weekly": 336,
            }
            for cycle, ts in last_runs.items():
                if not ts:
                    gaps.append({
                        "id": (
                            f"pipeline_{cycle}"
                            "_never_ran"
                        ),
                        "category": "pipeline",
                        "severity": "HIGH",
                        "title": (
                            f"Cycle never ran: {cycle}"
                        ),
                        "detail": (
                            f"'{cycle}' has never "
                            "completed successfully"
                        ),
                        "action": "run_research",
                    })
                    continue
                try:
                    last_dt = datetime.fromisoformat(ts)
                    now = datetime.now().astimezone()
                    age = (
                        now - last_dt
                    ).total_seconds() / 3600
                    limit = expected_h.get(cycle, 48)
                    if age > limit:
                        sev = (
                            "HIGH" if age > limit * 2
                            else "MEDIUM"
                        )
                        gaps.append({
                            "id": (
                                f"pipeline_{cycle}"
                                "_overdue"
                            ),
                            "category": "pipeline",
                            "severity": sev,
                            "title": (
                                f"Cycle overdue: "
                                f"{cycle}"
                            ),
                            "detail": (
                                f"'{cycle}' last ran "
                                f"{age:.0f}h ago, "
                                f"expected every "
                                f"{limit}h"
                            ),
                            "action": "run_research",
                        })
                except (ValueError, TypeError):
                    pass

        # Report directory freshness
        checks = [
            ("Research", RESEARCH_DIR, 48),
            ("Ideas", IDEAS_DIR, 168),
            ("Intelligence", INTEL_DIR, 72),
            (
                "Metrics",
                ROOT / "reports" / "metrics",
                24,
            ),
        ]
        for label, directory, max_age in checks:
            if not directory.exists():
                gaps.append({
                    "id": (
                        f"pipeline_"
                        f"{label.lower()}_missing"
                    ),
                    "category": "pipeline",
                    "severity": "MEDIUM",
                    "title": (
                        f"No {label} output directory"
                    ),
                    "detail": (
                        f"{directory} does not exist"
                    ),
                    "action": "run_research",
                })
                continue

            files = list(directory.glob("*.json"))
            if not files:
                gaps.append({
                    "id": (
                        f"pipeline_"
                        f"{label.lower()}_empty"
                    ),
                    "category": "pipeline",
                    "severity": "MEDIUM",
                    "title": f"No {label} reports",
                    "detail": (
                        f"{directory} has no JSON "
                        "output files"
                    ),
                    "action": "run_research",
                })
            else:
                newest = max(
                    files,
                    key=lambda f: f.stat().st_mtime,
                )
                age_val = _file_age_hours(newest)
                if age_val is not None and age_val > max_age:
                    gaps.append({
                        "id": (
                            f"pipeline_"
                            f"{label.lower()}_stale"
                        ),
                        "category": "pipeline",
                        "severity": "MEDIUM",
                        "title": (
                            f"Stale {label} reports"
                        ),
                        "detail": (
                            f"Latest {label} report "
                            f"is {age:.0f}h old "
                            f"(max {max_age}h)"
                        ),
                        "action": "run_research",
                    })

        return gaps

    # ── Knowledge Gaps ─────────────────────────────────────

    def knowledge_gaps(self) -> list[dict]:
        """Watchlist topics with no ingested content."""
        gaps: list[dict] = []
        sources = self.watchlist.get("sources", [])

        # Count ingested videos
        ingested = 0
        if KNOWLEDGE_DIR.exists():
            for d in KNOWLEDGE_DIR.iterdir():
                if (
                    d.is_dir()
                    and not d.name.startswith(".")
                ):
                    for m in d.iterdir():
                        if m.is_dir():
                            ingested += sum(
                                1 for v in m.iterdir()
                                if v.is_dir()
                            )

        if ingested == 0 and sources:
            gaps.append({
                "id": "knowledge_no_ingests",
                "category": "knowledge",
                "severity": "HIGH",
                "title": (
                    "No Second Brain content ingested"
                ),
                "detail": (
                    f"{len(sources)} watchlist sources"
                    " but zero videos ingested"
                ),
                "action": "run_research",
            })

        # Topic index coverage
        topic_idx = (
            KNOWLEDGE_DIR / "topic_index.json"
        )
        if topic_idx.exists():
            try:
                idx = json.loads(
                    topic_idx.read_text(
                        encoding="utf-8",
                    ),
                )
                total = idx.get("total_entries", 0)
                kw = idx.get("total_keywords", 0)
                if total > 0 and kw < total * 3:
                    gaps.append({
                        "id": (
                            "knowledge_sparse_index"
                        ),
                        "category": "knowledge",
                        "severity": "LOW",
                        "title": "Sparse topic index",
                        "detail": (
                            f"Only {kw} keywords for "
                            f"{total} entries "
                            "(expect 3x)"
                        ),
                        "action": "run_ideas",
                    })
            except (json.JSONDecodeError, OSError):
                pass

        return gaps

    # ── Integration Gaps ───────────────────────────────────

    def integration_gaps(self) -> list[dict]:
        """Subsystem integrations not working."""
        gaps: list[dict] = []

        integ_dir = ROOT / "reports" / "integrations"
        if not integ_dir.exists():
            gaps.append({
                "id": "integration_no_reports",
                "category": "integration",
                "severity": "HIGH",
                "title": (
                    "No integration sync reports"
                ),
                "detail": (
                    "NCC/NCL/AAC/DIGITAL LABOUR sync "
                    "has never produced output"
                ),
                "action": "run_integrations",
            })
        else:
            files = list(integ_dir.glob("*.json"))
            if files:
                newest = max(
                    files,
                    key=lambda f: f.stat().st_mtime,
                )
                age = _file_age_hours(newest)
                if age and age > 48:
                    gaps.append({
                        "id": (
                            "integration_stale_sync"
                        ),
                        "category": "integration",
                        "severity": "MEDIUM",
                        "title": (
                            "Integration sync is stale"
                        ),
                        "detail": (
                            f"Last sync {age:.0f}h ago"
                            " (expected every 24h)"
                        ),
                        "action": "run_integrations",
                    })

        # Skill registry populated?
        agents = self.skills.get("agents", {})
        if len(agents) < 5:
            gaps.append({
                "id": "integration_sparse_skills",
                "category": "integration",
                "severity": "MEDIUM",
                "title": (
                    "Skill registry underpopulated"
                ),
                "detail": (
                    f"Only {len(agents)} agents "
                    "registered (expected 8+)"
                ),
                "action": "run_validation",
            })

        return gaps

    # ── Helpers ─────────────────────────────────────────────

    def _top_actions(
        self, all_gaps: list[dict], top_n: int = 5,
    ) -> list[dict]:
        """Rank and deduplicate top actions."""
        scores: dict[str, int] = defaultdict(int)
        for g in all_gaps:
            action = g.get("action", "")
            sev = g.get("severity", "LOW")
            scores[action] += SEVERITY_WEIGHT.get(
                sev, 1,
            )

        ranked = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return [
            {"action": a, "priority_score": s}
            for a, s in ranked[:top_n]
        ]


# ── CLI ────────────────────────────────────────────────────

def main():
    Log.info("=== Gap Analyzer ===")
    analyzer = GapAnalyzer()
    result = analyzer.analyze()

    summary = result["summary"]
    Log.info(
        f"Total gaps: {summary['total_gaps']} "
        f"(C:{summary['critical']} "
        f"H:{summary['high']} "
        f"M:{summary['medium']} "
        f"L:{summary['low']})"
    )

    for cat in (
        "mandate_gaps", "research_gaps",
        "pipeline_gaps", "knowledge_gaps",
        "integration_gaps",
    ):
        items = result[cat]
        if items:
            label = cat.replace("_", " ").title()
            Log.info(f"--- {label} ({len(items)}) ---")
            for g in items:
                Log.info(
                    f"  [{g['severity']}] "
                    f"{g['title']}"
                )

    if summary["top_actions"]:
        Log.info("--- Top Actions ---")
        for a in summary["top_actions"]:
            Log.info(
                f"  -> {a['action']} "
                f"(score: {a['priority_score']})"
            )

    return result


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "full"
    if cmd == "summary":
        analyzer = GapAnalyzer()
        result = analyzer.analyze()
        for a in result["summary"]["top_actions"]:
            print(
                f"{a['action']}: "
                f"{a['priority_score']}"
            )
    else:
        main()
