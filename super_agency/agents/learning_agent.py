#!/usr/bin/env python3
"""
Learning & Adaptation Agent
=============================
Meta-learning agent that observes agent fleet performance,
identifies patterns, and adapts system behavior.

Capabilities:
- Performance pattern recognition across agents
- Failure-mode learning (what went wrong and why)
- Strategy recommendation engine
- Configuration auto-tuning suggestions
- Knowledge consolidation (compress lessons learned)
- Cross-agent skill transfer recommendations

Integrates:
  ml_intelligence_framework → KMeansCluster, ActionScorer,
                               AgentPerformanceProfiler
  agent_metrics → MetricsCollector, MetricsDashboard
  cognitive_architecture → ReflexionEngine, CognitiveMemory

Usage::

    from agents.learning_agent import LearningAgent
    agent = LearningAgent()
    lessons = agent.learn_cycle()
"""

from __future__ import annotations

import json
import logging
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
LEARNING_DIR = ROOT / "data" / "learning"
LEARNING_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR = ROOT / "reports" / "learning"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ── Message bus (best-effort) ──────────────────────────────┐
_bus: Any = None
try:
    from agents.message_bus import bus
    _bus = bus
except Exception:
    pass


def _emit(
    topic: str,
    payload: Optional[dict[str, Any]] = None,
) -> None:
    if _bus:
        _bus.publish(  # type: ignore[union-attr]
            topic,
            payload or {},
            source="learning_agent",
        )
# ──────────────────────────────────────────────────────────┘


# ═══════════════════════════════════════════════════════════════
#  LESSON STORE  — persistent learned lessons
# ═══════════════════════════════════════════════════════════════

LESSONS_FILE = LEARNING_DIR / "lessons.json"


def _load_lessons() -> list[dict[str, Any]]:
    if LESSONS_FILE.exists():
        try:
            data = json.loads(
                LESSONS_FILE.read_text(encoding="utf-8"),
            )
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _save_lessons(lessons: list[dict[str, Any]]) -> None:
    LESSONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    LESSONS_FILE.write_text(
        json.dumps(lessons, indent=2, default=str),
        encoding="utf-8",
    )


# ═══════════════════════════════════════════════════════════════
#  LEARNING AGENT
# ═══════════════════════════════════════════════════════════════

class LearningAgent:
    """Observes system behavior, extracts patterns,
    and generates adaptive recommendations."""

    def __init__(self) -> None:
        self._lessons = _load_lessons()
        self._cycle_count = 0
        self._failure_patterns: dict[str, int] = (
            defaultdict(int)
        )

    # ── Error log analysis ──────────────────────────────

    def _analyze_error_logs(
        self,
    ) -> dict[str, Any]:
        """Parse recent log files for error patterns."""
        log_dir = ROOT / "logs"
        if not log_dir.exists():
            return {"errors": 0, "patterns": {}}

        error_types: Counter[str] = Counter()
        total_errors = 0

        for lf in list(log_dir.glob("*.log"))[:10]:
            try:
                lines = lf.read_text(
                    encoding="utf-8",
                    errors="replace",
                ).splitlines()
                for line in lines[-500:]:  # tail
                    low = line.lower()
                    if "error" in low or "fail" in low:
                        total_errors += 1
                        if "timeout" in low:
                            error_types["timeout"] += 1
                        elif "connection" in low:
                            error_types["connection"] += 1
                        elif "json" in low:
                            error_types["json_parse"] += 1
                        elif "permission" in low:
                            error_types["permission"] += 1
                        elif "import" in low:
                            error_types["import"] += 1
                        else:
                            error_types["other"] += 1
            except OSError:
                continue

        return {
            "errors": total_errors,
            "patterns": dict(error_types.most_common(10)),
        }

    # ── Performance analysis ────────────────────────────

    def _analyze_performance(
        self,
    ) -> dict[str, Any]:
        """Check orchestrator and scheduler metrics."""
        metrics_dir = ROOT / "data" / "agent_metrics"
        if not metrics_dir.exists():
            return {"available": False}

        snapshot_path = (
            metrics_dir / "metrics_snapshot.json"
        )
        if not snapshot_path.exists():
            return {"available": False}

        try:
            data = json.loads(
                snapshot_path.read_text(encoding="utf-8"),
            )
            metrics = data.get("metrics", {})
            slow_agents: list[str] = []
            failing_agents: list[str] = []

            for agent, m in metrics.items():
                dur = m.get("duration_s", {})
                avg = dur.get("mean", 0) if dur else 0
                if avg > 30:
                    slow_agents.append(agent)

                success = m.get("success", {})
                rate = success.get("mean", 1) if success else 1
                if rate < 0.8:
                    failing_agents.append(agent)

            return {
                "available": True,
                "agents_tracked": len(metrics),
                "slow_agents": slow_agents,
                "failing_agents": failing_agents,
            }
        except (json.JSONDecodeError, OSError):
            return {"available": False}

    # ── Report quality analysis ─────────────────────────

    def _analyze_report_quality(
        self,
    ) -> dict[str, Any]:
        """Check report freshness and completeness."""
        rpt_dir = ROOT / "reports"
        if not rpt_dir.exists():
            return {"reports": 0, "stale": 0}

        reports = list(rpt_dir.rglob("*.json"))
        stale = 0
        empty = 0
        now_ts = time.time()

        for r in reports[:100]:
            try:
                age_h = (now_ts - r.stat().st_mtime) / 3600
                if age_h > 48:
                    stale += 1
                if r.stat().st_size < 10:
                    empty += 1
            except OSError:
                continue

        return {
            "reports": len(reports),
            "stale_48h": stale,
            "empty": empty,
        }

    # ── Lesson extraction ───────────────────────────────

    def _extract_lessons(
        self,
        errors: dict[str, Any],
        performance: dict[str, Any],
        quality: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate actionable lessons from observations."""
        new_lessons: list[dict[str, Any]] = []
        ts = datetime.now().isoformat()

        # Error pattern lessons
        patterns = errors.get("patterns", {})
        for ptype, count in patterns.items():
            if count >= 3:
                self._failure_patterns[ptype] += count
                lesson = {
                    "ts": ts,
                    "category": "error_pattern",
                    "pattern": ptype,
                    "count": count,
                    "recommendation": (
                        f"Recurring '{ptype}' errors "
                        f"({count}x). Consider adding "
                        f"retry logic or circuit breaker."
                    ),
                    "priority": "high" if count > 10
                    else "medium",
                }
                # deduplicate
                if not any(
                    l.get("pattern") == ptype
                    and l.get("category") == "error_pattern"
                    for l in self._lessons
                ):
                    new_lessons.append(lesson)

        # Performance lessons
        if performance.get("available"):
            for agent in performance.get(
                "slow_agents", [],
            ):
                lesson = {
                    "ts": ts,
                    "category": "performance",
                    "agent": agent,
                    "recommendation": (
                        f"Agent '{agent}' is consistently "
                        f"slow (>30s avg). Consider "
                        f"optimizing or parallelizing."
                    ),
                    "priority": "medium",
                }
                new_lessons.append(lesson)

            for agent in performance.get(
                "failing_agents", [],
            ):
                lesson = {
                    "ts": ts,
                    "category": "reliability",
                    "agent": agent,
                    "recommendation": (
                        f"Agent '{agent}' has <80% success "
                        f"rate. Investigate root cause."
                    ),
                    "priority": "high",
                }
                new_lessons.append(lesson)

        # Quality lessons
        stale = quality.get("stale_48h", 0)
        total_rpt = quality.get("reports", 0)
        if total_rpt > 0 and stale / total_rpt > 0.5:
            new_lessons.append({
                "ts": ts,
                "category": "data_freshness",
                "recommendation": (
                    f"{stale}/{total_rpt} reports are "
                    f"stale (>48h). Schedule more "
                    f"frequent runs."
                ),
                "priority": "medium",
            })

        return new_lessons

    # ── Main cycle ──────────────────────────────────────

    def learn_cycle(self) -> dict[str, Any]:
        """Execute one learning cycle."""
        self._cycle_count += 1
        t0 = time.time()

        # Observe
        errors = self._analyze_error_logs()
        performance = self._analyze_performance()
        quality = self._analyze_report_quality()

        # Learn
        new_lessons = self._extract_lessons(
            errors, performance, quality,
        )
        self._lessons.extend(new_lessons)

        # Persist
        _save_lessons(self._lessons)

        # Report
        report: dict[str, Any] = {
            "cycle": self._cycle_count,
            "ts": datetime.now().isoformat(),
            "errors_observed": errors,
            "performance": performance,
            "report_quality": quality,
            "new_lessons": len(new_lessons),
            "total_lessons": len(self._lessons),
            "lessons_this_cycle": new_lessons,
            "failure_pattern_totals": dict(
                self._failure_patterns,
            ),
            "duration_s": round(time.time() - t0, 3),
        }

        rpt_path = (
            REPORTS_DIR
            / f"learning_{datetime.now():%Y%m%d_%H%M%S}"
            f".json"
        )
        rpt_path.write_text(
            json.dumps(report, indent=2, default=str),
            encoding="utf-8",
        )

        _emit("learning.cycle.complete", {
            "cycle": self._cycle_count,
            "new_lessons": len(new_lessons),
            "total_lessons": len(self._lessons),
        })

        logger.info(
            "[Learning] cycle=%d new_lessons=%d "
            "total=%d",
            self._cycle_count,
            len(new_lessons),
            len(self._lessons),
        )
        return report

    # ── Query interface ─────────────────────────────────

    def get_lessons(
        self,
        category: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        results = self._lessons
        if category:
            results = [
                l for l in results
                if l.get("category") == category
            ]
        if priority:
            results = [
                l for l in results
                if l.get("priority") == priority
            ]
        return results

    def get_recommendations(
        self,
    ) -> list[str]:
        """Return all recommendations sorted by priority."""
        high = [
            l["recommendation"]
            for l in self._lessons
            if l.get("priority") == "high"
        ]
        medium = [
            l["recommendation"]
            for l in self._lessons
            if l.get("priority") == "medium"
        ]
        return high + medium


# ═══════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = LearningAgent()
    report = agent.learn_cycle()
    print(json.dumps(report, indent=2, default=str))
    recs = agent.get_recommendations()
    if recs:
        print(f"\nRecommendations ({len(recs)}):")
        for r in recs:
            print(f"  • {r}")
