#!/usr/bin/env python3
"""
Agent Success Metrics — KPI tracking and scoring for agents.

Provides a unified metrics framework that every agent can
report into.  Aggregates success rates, latency, throughput,
quality scores, and intelligence value across the hierarchy.

Metric categories:
  - Operational: uptime, run count, latency p50/p95
  - Quality: error rate, retry rate, data freshness
  - Intelligence: insights generated, accuracy, actionability
  - Collaboration: messages sent/received, delegation success
  - Learning: improvement rate, knowledge growth

Usage::

    from tools.agent_metrics import (
        MetricsCollector, AgentScorecard, MetricsDashboard,
    )

    mc = MetricsCollector()
    mc.record("orchestrator", "stage_success", 1)
    mc.record("orchestrator", "stage_duration_s", 12.4)

    card = AgentScorecard("orchestrator", mc)
    print(card.summary())
"""

from __future__ import annotations

import json
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
METRICS_DIR = ROOT / "data" / "agent_metrics"
METRICS_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════
#  METRICS COLLECTOR
# ═══════════════════════════════════════════════════════════════

class MetricsCollector:
    """Central collector for agent telemetry.

    Agents call ``record(agent, metric, value)`` and the
    collector maintains rolling windows of observations
    for each (agent, metric) pair.
    """

    def __init__(self, window: int = 500) -> None:
        self._window = window
        self._data: dict[
            str, dict[str, deque[float]]
        ] = defaultdict(
            lambda: defaultdict(
                lambda: deque(maxlen=window),
            ),
        )
        self._counters: dict[str, dict[str, int]] = (
            defaultdict(lambda: defaultdict(int))
        )

    def record(
        self,
        agent: str,
        metric: str,
        value: float = 1.0,
    ) -> None:
        self._data[agent][metric].append(value)
        self._counters[agent][metric] += 1

    def increment(
        self,
        agent: str,
        metric: str,
        delta: int = 1,
    ) -> None:
        self._counters[agent][metric] += delta

    def get_values(
        self,
        agent: str,
        metric: str,
    ) -> list[float]:
        return list(self._data[agent][metric])

    def get_count(
        self,
        agent: str,
        metric: str,
    ) -> int:
        return self._counters[agent][metric]

    def agents(self) -> list[str]:
        return sorted(
            set(self._data.keys())
            | set(self._counters.keys())
        )

    def metrics_for(self, agent: str) -> list[str]:
        return sorted(
            set(self._data.get(agent, {}).keys())
            | set(self._counters.get(agent, {}).keys())
        )

    def snapshot(self) -> dict[str, Any]:
        """Full snapshot for persistence."""
        out: dict[str, Any] = {}
        for agent in self.agents():
            out[agent] = {}
            for m in self.metrics_for(agent):
                vals = self.get_values(agent, m)
                cnt = self.get_count(agent, m)
                entry: dict[str, Any] = {"count": cnt}
                if vals:
                    entry["last"] = vals[-1]
                    entry["mean"] = round(
                        statistics.mean(vals), 4,
                    )
                    if len(vals) >= 2:
                        entry["stdev"] = round(
                            statistics.stdev(vals), 4,
                        )
                out[agent][m] = entry
        return out

    def save(
        self,
        path: Optional[Path] = None,
    ) -> Path:
        dest = path or (
            METRICS_DIR / "metrics_snapshot.json"
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ts": datetime.now().isoformat(),
            "metrics": self.snapshot(),
        }
        dest.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
        return dest


# ═══════════════════════════════════════════════════════════════
#  AGENT SCORECARD
# ═══════════════════════════════════════════════════════════════

@dataclass
class _KPI:
    name: str
    value: float
    target: float
    weight: float = 1.0

    @property
    def score(self) -> float:
        if self.target == 0:
            return 1.0
        raw = self.value / self.target
        return min(raw, 1.0)


class AgentScorecard:
    """Builds a weighted scorecard for one agent.

    KPIs:
      success_rate  — runs succeeded / total  (target 0.95)
      avg_latency   — average duration        (target <10s)
      error_rate    — errors / total           (target <0.05)
      throughput    — runs per hour            (target 10)
    """

    def __init__(
        self,
        agent: str,
        collector: MetricsCollector,
    ) -> None:
        self.agent = agent
        self._mc = collector

    def _safe_mean(self, metric: str) -> float:
        vals = self._mc.get_values(self.agent, metric)
        return statistics.mean(vals) if vals else 0.0

    def kpis(self) -> list[_KPI]:
        sr = self._safe_mean("success")
        lat = self._safe_mean("duration_s")
        err = self._safe_mean("error")
        tp = float(
            self._mc.get_count(self.agent, "run"),
        )
        return [
            _KPI("success_rate", sr, 0.95, 2.0),
            _KPI(
                "avg_latency",
                max(1 - lat / 30.0, 0),
                1.0,
                1.0,
            ),
            _KPI(
                "error_rate",
                max(1 - err / 0.1, 0),
                1.0,
                1.5,
            ),
            _KPI("throughput", min(tp / 100.0, 1), 1.0),
        ]

    def overall_score(self) -> float:
        kpis = self.kpis()
        total_w = sum(k.weight for k in kpis) or 1.0
        weighted = sum(k.score * k.weight for k in kpis)
        return round(weighted / total_w, 4)

    def grade(self) -> str:
        s = self.overall_score()
        if s >= 0.9:
            return "A"
        if s >= 0.8:
            return "B"
        if s >= 0.7:
            return "C"
        if s >= 0.6:
            return "D"
        return "F"

    def summary(self) -> dict[str, Any]:
        kpis = self.kpis()
        return {
            "agent": self.agent,
            "overall_score": self.overall_score(),
            "grade": self.grade(),
            "kpis": {
                k.name: {
                    "value": round(k.value, 4),
                    "target": k.target,
                    "score": round(k.score, 4),
                }
                for k in kpis
            },
        }


# ═══════════════════════════════════════════════════════════════
#  METRICS DASHBOARD — aggregate view
# ═══════════════════════════════════════════════════════════════

class MetricsDashboard:
    """Aggregates scorecards for all agents into a single
    dashboard report.
    """

    def __init__(
        self,
        collector: MetricsCollector,
    ) -> None:
        self._mc = collector

    def report(self) -> dict[str, Any]:
        agents = self._mc.agents()
        cards = {
            a: AgentScorecard(a, self._mc).summary()
            for a in agents
        }
        scores = [
            c["overall_score"] for c in cards.values()
        ]
        return {
            "ts": datetime.now().isoformat(),
            "agent_count": len(agents),
            "system_score": round(
                statistics.mean(scores), 4,
            ) if scores else 0.0,
            "agents": cards,
        }

    def save(
        self,
        path: Optional[Path] = None,
    ) -> Path:
        dest = path or (
            METRICS_DIR / "dashboard.json"
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            json.dumps(self.report(), indent=2),
            encoding="utf-8",
        )
        return dest


# ═══════════════════════════════════════════════════════════════
#  HIERARCHY METRICS  — roll-up by tier
# ═══════════════════════════════════════════════════════════════

# Agent hierarchy for roll-up scoring
AGENT_HIERARCHY: dict[str, list[str]] = {
    "executive": [
        "ceo", "cto", "cfo", "cmo", "cio",
    ],
    "management": [
        "orchestrator", "council",
        "research_scheduler", "autonomous_brain",
    ],
    "operational": [
        "repo_sentry", "portfolio_intel",
        "research_metrics", "gap_analyzer",
        "self_check_validator", "idea_engine",
    ],
    "support": [
        "bus_subscribers", "memory_backup",
        "api_cost_tracker", "topic_index",
    ],
}


def tier_scores(
    collector: MetricsCollector,
) -> dict[str, float]:
    """Average score per hierarchy tier."""
    result: dict[str, float] = {}
    for tier, agents in AGENT_HIERARCHY.items():
        scores = []
        for a in agents:
            if a in collector.agents():
                card = AgentScorecard(a, collector)
                scores.append(card.overall_score())
        result[tier] = round(
            statistics.mean(scores), 4,
        ) if scores else 0.0
    return result
