#!/usr/bin/env python3
"""Tests for Phase 17 — Research Agent Framework modules."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in [str(ROOT), str(ROOT / "tools"), str(ROOT / "agents")]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest  # noqa: E402


# ═══════════════════════════════════════════════════════════════
#  ML Intelligence Framework
# ═══════════════════════════════════════════════════════════════

class TestAnomalyDetector:
    def test_warmup_returns_zero(self):
        from tools.ml_intelligence_framework import (
            AnomalyDetector,
        )
        det = AnomalyDetector(window=20)
        # First few values return 0 (warmup)
        for v in [1.0, 2.0, 3.0]:
            assert det.score(v) == 0.0

    def test_normal_values_low_score(self):
        from tools.ml_intelligence_framework import (
            AnomalyDetector,
        )
        det = AnomalyDetector(window=20)
        for v in range(20):
            det.score(float(v % 5))
        # Normal-ish value should score low
        s = det.score(3.0)
        assert s < 0.5

    def test_anomaly_high_score(self):
        from tools.ml_intelligence_framework import (
            AnomalyDetector,
        )
        det = AnomalyDetector(window=50, z_threshold=2.0)
        for _ in range(50):
            det.score(10.0)
        # Extreme outlier
        s = det.score(1000.0)
        assert s > 0.5

    def test_reset(self):
        from tools.ml_intelligence_framework import (
            AnomalyDetector,
        )
        det = AnomalyDetector(window=10)
        for v in range(10):
            det.score(float(v))
        det.reset()
        assert det.recent_alerts() == []


class TestTrendForecaster:
    def test_upward_trend(self):
        from tools.ml_intelligence_framework import (
            TrendForecaster,
        )
        tf = TrendForecaster(alpha=0.5, beta=0.3)
        for v in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
            tf.update(float(v))
        assert tf.direction() == "up"
        fc = tf.forecast(3)
        assert len(fc) == 3
        assert fc[0] > 10  # should project upward

    def test_flat_trend(self):
        from tools.ml_intelligence_framework import (
            TrendForecaster,
        )
        tf = TrendForecaster()
        tf.update(5.0)
        assert tf.direction() == "flat"

    def test_empty_forecast(self):
        from tools.ml_intelligence_framework import (
            TrendForecaster,
        )
        tf = TrendForecaster()
        assert tf.forecast() == []


class TestTextIntelligence:
    def test_add_and_keywords(self):
        from tools.ml_intelligence_framework import (
            TextIntelligence,
        )
        ti = TextIntelligence()
        did = ti.add_document(
            "quantum computing research energy systems"
        )
        assert did == 0
        kw = ti.keywords(0, top_n=3)
        assert len(kw) > 0
        assert all(isinstance(k, tuple) for k in kw)

    def test_similar_docs(self):
        from tools.ml_intelligence_framework import (
            TextIntelligence,
        )
        ti = TextIntelligence()
        ti.add_document("quantum computing research")
        ti.add_document("quantum physics research")
        ti.add_document("cooking recipes food")
        sims = ti.similar_docs(0, top_n=2)
        # doc 1 should be more similar to doc 0
        assert len(sims) > 0
        assert sims[0][0] == 1  # physics doc


class TestActionScorer:
    def test_explores_all_first(self):
        from tools.ml_intelligence_framework import (
            ActionScorer,
        )
        scorer = ActionScorer(["a", "b", "c"])
        seen: set[str] = set()
        for _ in range(3):
            a = scorer.select()
            seen.add(a)
            scorer.update(a, 0.5)
        # UCB1 explores untried actions first
        assert len(seen) == 3

    def test_stats(self):
        from tools.ml_intelligence_framework import (
            ActionScorer,
        )
        scorer = ActionScorer(["x", "y"])
        scorer.update("x", 1.0)
        scorer.update("y", 0.0)
        s = scorer.stats()
        assert s["x"]["avg_reward"] == 1.0
        assert s["y"]["avg_reward"] == 0.0


class TestKMeansCluster:
    def test_basic_clustering(self):
        from tools.ml_intelligence_framework import (
            KMeansCluster,
        )
        km = KMeansCluster(k=2, max_iter=20)
        data = [
            [0.0, 0.0], [0.1, 0.1], [0.2, 0.0],
            [10.0, 10.0], [10.1, 10.1], [10.2, 10.0],
        ]
        labels = km.fit(data)
        assert len(labels) == 6
        # First 3 should be same cluster, last 3 same
        assert labels[0] == labels[1] == labels[2]
        assert labels[3] == labels[4] == labels[5]
        assert labels[0] != labels[3]

    def test_empty_data(self):
        from tools.ml_intelligence_framework import (
            KMeansCluster,
        )
        km = KMeansCluster(k=2)
        assert km.fit([]) == []


class TestAgentPerformanceProfiler:
    def test_record_and_stats(self, tmp_path):
        from tools.ml_intelligence_framework import (
            AgentPerformanceProfiler,
        )
        prof = AgentPerformanceProfiler()
        prof.record("test_agent", "scan", 1.5, True)
        prof.record("test_agent", "scan", 2.0, True)
        prof.record("test_agent", "scan", 3.0, False)
        stats = prof.agent_stats("test_agent")
        assert stats["runs"] == 3
        assert 0.6 < stats["success_rate"] < 0.7
        # Save
        dest = prof.save(tmp_path / "perf.json")
        assert dest.exists()


# ═══════════════════════════════════════════════════════════════
#  Agent Metrics
# ═══════════════════════════════════════════════════════════════

class TestMetricsCollector:
    def test_record_and_retrieve(self):
        from tools.agent_metrics import MetricsCollector
        mc = MetricsCollector()
        mc.record("orchestrator", "duration_s", 5.0)
        mc.record("orchestrator", "duration_s", 10.0)
        vals = mc.get_values("orchestrator", "duration_s")
        assert vals == [5.0, 10.0]

    def test_increment(self):
        from tools.agent_metrics import MetricsCollector
        mc = MetricsCollector()
        mc.increment("brain", "cycles", 1)
        mc.increment("brain", "cycles", 1)
        assert mc.get_count("brain", "cycles") == 2

    def test_snapshot(self):
        from tools.agent_metrics import MetricsCollector
        mc = MetricsCollector()
        mc.record("a", "x", 5.0)
        snap = mc.snapshot()
        assert "a" in snap
        assert snap["a"]["x"]["mean"] == 5.0

    def test_save(self, tmp_path):
        from tools.agent_metrics import MetricsCollector
        mc = MetricsCollector()
        mc.record("a", "x", 1.0)
        dest = mc.save(tmp_path / "metrics.json")
        assert dest.exists()


class TestAgentScorecard:
    def test_scorecard(self):
        from tools.agent_metrics import (
            MetricsCollector, AgentScorecard,
        )
        mc = MetricsCollector()
        mc.record("bot", "success", 1.0)
        mc.record("bot", "success", 1.0)
        mc.record("bot", "duration_s", 2.0)
        mc.record("bot", "error", 0.01)
        mc.increment("bot", "run")
        card = AgentScorecard("bot", mc)
        assert 0 <= card.overall_score() <= 1
        assert card.grade() in "ABCDF"
        s = card.summary()
        assert s["agent"] == "bot"


class TestMetricsDashboard:
    def test_dashboard(self, tmp_path):
        from tools.agent_metrics import (
            MetricsCollector, MetricsDashboard,
        )
        mc = MetricsCollector()
        mc.record("bot1", "success", 1.0)
        mc.record("bot2", "success", 0.5)
        dash = MetricsDashboard(mc)
        rpt = dash.report()
        assert rpt["agent_count"] == 2
        dest = dash.save(tmp_path / "dash.json")
        assert dest.exists()


# ═══════════════════════════════════════════════════════════════
#  Research Intelligence Agent
# ═══════════════════════════════════════════════════════════════

class TestResearchIntelligenceAgent:
    def test_run_cycle(self):
        from agents.research_intelligence import (
            ResearchIntelligenceAgent,
        )
        agent = ResearchIntelligenceAgent()
        report = agent.run_cycle()
        assert report["cycle"] == 1
        assert "knowledge_scan" in report
        assert "velocity" in report
        assert "strategy_executed" in report

    def test_multiple_cycles(self):
        from agents.research_intelligence import (
            ResearchIntelligenceAgent,
        )
        agent = ResearchIntelligenceAgent()
        agent.run_cycle()
        r2 = agent.run_cycle()
        assert r2["cycle"] == 2


# ═══════════════════════════════════════════════════════════════
#  Alignment Monitor
# ═══════════════════════════════════════════════════════════════

class TestAlignmentMonitor:
    def test_check_all(self):
        from agents.alignment_monitor import (
            AlignmentMonitor,
        )
        m = AlignmentMonitor()
        report = m.check_all()
        assert "aligned" in report
        assert "checks" in report
        assert len(report["checks"]) == 5

    def test_config_check(self):
        from agents.alignment_monitor import (
            AlignmentMonitor,
        )
        m = AlignmentMonitor()
        r = m.check_config_consistency()
        assert r["check"] == "config_consistency"

    def test_constitution_loaded(self):
        from agents.alignment_monitor import (
            CONSTITUTION,
        )
        assert len(CONSTITUTION) >= 7


# ═══════════════════════════════════════════════════════════════
#  Learning Agent
# ═══════════════════════════════════════════════════════════════

class TestLearningAgent:
    def test_learn_cycle(self):
        from agents.learning_agent import LearningAgent
        agent = LearningAgent()
        report = agent.learn_cycle()
        assert report["cycle"] == 1
        assert "errors_observed" in report
        assert "report_quality" in report

    def test_recommendations(self):
        from agents.learning_agent import LearningAgent
        agent = LearningAgent()
        recs = agent.get_recommendations()
        assert isinstance(recs, list)


# ═══════════════════════════════════════════════════════════════
#  Hierarchy
# ═══════════════════════════════════════════════════════════════

class TestAgentRegistry:
    def test_defaults_loaded(self):
        from agents.hierarchy import AgentRegistry
        reg = AgentRegistry()
        assert reg.get("ceo") is not None
        assert reg.get("ceo").tier == 0
        assert reg.get("orchestrator").tier == 2

    def test_register_and_query(self):
        from agents.hierarchy import AgentRegistry
        reg = AgentRegistry()
        reg.register(
            "test_bot", tier=3,
            capabilities=["scan", "report"],
        )
        bots = reg.by_capability("scan")
        assert any(a.name == "test_bot" for a in bots)

    def test_by_tier(self):
        from agents.hierarchy import AgentRegistry
        reg = AgentRegistry()
        execs = reg.by_tier(1)
        names = [a.name for a in execs]
        assert "cto" in names

    def test_save(self, tmp_path):
        from agents.hierarchy import AgentRegistry
        reg = AgentRegistry()
        dest = reg.save(tmp_path / "reg.json")
        assert dest.exists()


class TestTaskRouter:
    def test_route_by_capability(self):
        from agents.hierarchy import (
            AgentRegistry, TaskRouter,
        )
        reg = AgentRegistry()
        reg.register(
            "scanner", tier=3,
            capabilities=["scan"],
        )
        router = TaskRouter(reg)
        assignment = router.route("scan")
        assert assignment is not None
        assert assignment.agent == "scanner"

    def test_escalate(self):
        from agents.hierarchy import (
            AgentRegistry, TaskRouter,
        )
        reg = AgentRegistry()
        reg.register(
            "worker", tier=3,
            capabilities=["analyze"],
        )
        reg.register(
            "manager", tier=2,
            capabilities=["analyze"],
        )
        router = TaskRouter(reg)
        esc = router.escalate("analyze", "worker")
        assert esc is not None
        assert esc.tier <= 2


# ═══════════════════════════════════════════════════════════════
#  Model persistence
# ═══════════════════════════════════════════════════════════════

class TestModelPersistence:
    def test_save_and_load(self, tmp_path):
        from tools.ml_intelligence_framework import (
            save_model, load_model,
        )
        save_model(
            "test_model",
            {"weights": [1, 2, 3]},
            tmp_path / "test_model.json",
        )
        state = load_model(
            "test_model",
            tmp_path / "test_model.json",
        )
        assert state == {"weights": [1, 2, 3]}

    def test_load_missing(self, tmp_path):
        from tools.ml_intelligence_framework import (
            load_model,
        )
        result = load_model(
            "nonexistent",
            tmp_path / "nope.json",
        )
        assert result is None
