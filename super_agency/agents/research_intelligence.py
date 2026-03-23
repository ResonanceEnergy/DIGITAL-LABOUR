#!/usr/bin/env python3
"""
Research Intelligence Agent
============================
Autonomous agent that uses cognitive architecture + ML intelligence
to drive research across the DIGITAL LABOUR portfolio.

Responsibilities:
- Monitor research repos for knowledge gaps and opportunities
- Run ReAct reasoning loops on research questions
- Score and prioritise research directions via contextual bandits
- Detect anomalies in research velocity and quality
- Generate intelligence reports with trend forecasting
- Cross-pollinate insights between research projects

Integrates:
  cognitive_architecture → ReActLoop, ReflexionEngine
  ml_intelligence_framework → AnomalyDetector, TrendForecaster,
                               ActionScorer, TextIntelligence
  agent_protocols → DelegationProtocol, ConsensusProtocol
  agent_metrics → MetricsCollector
  message_bus → pub/sub for event-driven coordination

Usage::

    from agents.research_intelligence import (
        ResearchIntelligenceAgent,
    )
    agent = ResearchIntelligenceAgent()
    report = agent.run_cycle()
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent


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
            source="research_intelligence",
        )
# ──────────────────────────────────────────────────────────┘


# ── Lazy imports (tools may not be on sys.path) ───────────
def _lazy_imports() -> dict[str, Any]:
    """Import heavy tool modules on first use."""
    import sys
    for p in [str(ROOT), str(ROOT / "tools")]:
        if p not in sys.path:
            sys.path.insert(0, p)

    from tools.cognitive_architecture import (
        CognitiveAgent,
        ReActLoop,
        GoalDecomposer,
    )
    from tools.ml_intelligence_framework import (
        AnomalyDetector,
        TrendForecaster,
        ActionScorer,
        TextIntelligence,
        AgentPerformanceProfiler,
    )
    from tools.agent_metrics import MetricsCollector

    return {
        "CognitiveAgent": CognitiveAgent,
        "ReActLoop": ReActLoop,
        "GoalDecomposer": GoalDecomposer,
        "AnomalyDetector": AnomalyDetector,
        "TrendForecaster": TrendForecaster,
        "ActionScorer": ActionScorer,
        "TextIntelligence": TextIntelligence,
        "AgentPerformanceProfiler": AgentPerformanceProfiler,
        "MetricsCollector": MetricsCollector,
    }


# ═══════════════════════════════════════════════════════════════
#  RESEARCH INTELLIGENCE AGENT
# ═══════════════════════════════════════════════════════════════

class ResearchIntelligenceAgent:
    """Autonomous research analyst agent.

    Each ``run_cycle()`` call:
      1. Scans research project knowledge bases
      2. Detects anomalies in research velocity
      3. Identifies trending topics across repos
      4. Selects best research direction (UCB1)
      5. Generates intelligence brief
      6. Publishes findings to message bus
    """

    def __init__(self) -> None:
        self._imports = _lazy_imports()
        self._anomaly = self._imports[
            "AnomalyDetector"
        ](window=100)
        self._trend = self._imports[
            "TrendForecaster"
        ](alpha=0.4, beta=0.15)
        self._scorer = self._imports["ActionScorer"](
            [
                "deep_analysis",
                "trend_scan",
                "gap_fill",
                "cross_pollinate",
                "quality_audit",
            ],
        )
        self._text_intel = self._imports[
            "TextIntelligence"
        ]()
        self._metrics = self._imports[
            "MetricsCollector"
        ]()
        self._cycle_count = 0
        self._knowledge_dir = (
            ROOT / "knowledge" / "secondbrain"
        )
        self._reports_dir = (
            ROOT / "reports" / "research_intelligence"
        )
        self._reports_dir.mkdir(
            parents=True, exist_ok=True,
        )

    # ── Knowledge scanning ──────────────────────────────

    def _scan_knowledge(
        self,
    ) -> dict[str, Any]:
        """Scan knowledge base for research content."""
        kb = self._knowledge_dir
        if not kb.exists():
            return {"files": 0, "topics": []}

        files = list(kb.rglob("*.json"))
        topic_counts: dict[str, int] = defaultdict(int)
        total_insights = 0

        for f in files[:200]:  # cap for performance
            try:
                data = json.loads(
                    f.read_text(encoding="utf-8"),
                )
                if isinstance(data, dict):
                    for key in data:
                        topic_counts[key] += 1
                    total_insights += 1
                    # feed title/summary to text intel
                    title = data.get(
                        "title",
                        data.get("topic", f.stem),
                    )
                    summary = data.get("summary", "")
                    if title or summary:
                        self._text_intel.add_document(
                            f"{title} {summary}",
                        )
            except (json.JSONDecodeError, OSError):
                continue

        top_topics = sorted(
            topic_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:15]

        return {
            "files": len(files),
            "indexed": total_insights,
            "top_topics": top_topics,
        }

    # ── Velocity tracking ───────────────────────────────

    def _check_velocity(
        self,
        file_count: int,
    ) -> dict[str, Any]:
        """Track research output velocity and detect
        anomalies."""
        self._trend.update(float(file_count))
        anomaly_score = self._anomaly.score(
            float(file_count),
        )

        return {
            "current": file_count,
            "anomaly_score": anomaly_score,
            "trend_direction": self._trend.direction(),
            "forecast_5": self._trend.forecast(5),
            "is_anomaly": anomaly_score > 0.8,
        }

    # ── Strategy selection ──────────────────────────────

    def _select_strategy(self) -> str:
        """Pick researh strategy via UCB1 bandit."""
        return self._scorer.select()

    def _execute_strategy(
        self,
        strategy: str,
        knowledge: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute the selected research strategy."""
        t0 = time.time()
        result: dict[str, Any] = {
            "strategy": strategy,
            "status": "ok",
        }

        if strategy == "deep_analysis":
            result["action"] = (
                "Identified top knowledge clusters"
            )
            result["clusters"] = knowledge.get(
                "top_topics", [],
            )[:5]

        elif strategy == "trend_scan":
            result["action"] = "Scanned for emerging trends"
            result["emerging"] = [
                t for t, c in knowledge.get(
                    "top_topics", [],
                )
                if c >= 2
            ][:10]

        elif strategy == "gap_fill":
            result["action"] = (
                "Identified knowledge gaps"
            )
            total = knowledge.get("files", 0)
            indexed = knowledge.get("indexed", 0)
            result["gap_ratio"] = round(
                1 - indexed / max(total, 1), 3,
            )

        elif strategy == "cross_pollinate":
            result["action"] = (
                "Cross-referenced topic connections"
            )
            docs = len(self._text_intel._docs)
            if docs > 1:
                sims = self._text_intel.similar_docs(
                    0, top_n=3,
                )
                result["connections"] = len(sims)
            else:
                result["connections"] = 0

        elif strategy == "quality_audit":
            result["action"] = (
                "Audited knowledge quality"
            )
            result["total_files"] = knowledge.get(
                "files", 0,
            )

        dur = time.time() - t0
        result["duration_s"] = round(dur, 3)
        # Reward: 1.0 for success, 0.0 for fail
        reward = 1.0 if result["status"] == "ok" else 0.0
        self._scorer.update(strategy, reward)
        self._metrics.record(
            "research_intelligence",
            "strategy_duration_s",
            dur,
        )
        self._metrics.record(
            "research_intelligence",
            "success",
            reward,
        )
        return result

    # ── Main cycle ──────────────────────────────────────

    def run_cycle(self) -> dict[str, Any]:
        """Execute one full research intelligence cycle."""
        self._cycle_count += 1
        t0 = time.time()

        # 1. Scan knowledge base
        knowledge = self._scan_knowledge()

        # 2. Check research velocity
        velocity = self._check_velocity(
            knowledge["files"],
        )

        # 3. Select and execute strategy
        strategy = self._select_strategy()
        strategy_result = self._execute_strategy(
            strategy, knowledge,
        )

        # 4. Generate keywords for latest docs
        keywords: list[tuple[str, float]] = []
        if self._text_intel._docs:
            last_id = len(self._text_intel._docs) - 1
            keywords = self._text_intel.keywords(
                last_id, top_n=8,
            )

        # 5. Build report
        report: dict[str, Any] = {
            "cycle": self._cycle_count,
            "ts": datetime.now().isoformat(),
            "knowledge_scan": knowledge,
            "velocity": velocity,
            "strategy_executed": strategy_result,
            "top_keywords": keywords,
            "bandit_stats": self._scorer.stats(),
            "duration_s": round(time.time() - t0, 3),
        }

        # 6. Persist
        rpt_path = (
            self._reports_dir
            / f"intel_{datetime.now():%Y%m%d_%H%M%S}.json"
        )
        rpt_path.write_text(
            json.dumps(report, indent=2, default=str),
            encoding="utf-8",
        )

        # 7. Publish to bus
        _emit("research.intelligence.cycle", {
            "cycle": self._cycle_count,
            "strategy": strategy,
            "anomaly": velocity.get("is_anomaly", False),
            "file_count": knowledge["files"],
        })

        if velocity.get("is_anomaly"):
            _emit("research.intelligence.anomaly", {
                "score": velocity["anomaly_score"],
                "file_count": knowledge["files"],
            })

        self._metrics.record(
            "research_intelligence",
            "run",
            1.0,
        )
        self._metrics.record(
            "research_intelligence",
            "duration_s",
            time.time() - t0,
        )

        logger.info(
            "[ResearchIntel] cycle=%d strategy=%s "
            "files=%d anomaly=%s",
            self._cycle_count,
            strategy,
            knowledge["files"],
            velocity.get("is_anomaly"),
        )
        return report


# ═══════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = ResearchIntelligenceAgent()
    report = agent.run_cycle()
    print(json.dumps(report, indent=2, default=str))
