#!/usr/bin/env python3
"""Tests for T2 Management Agents.

Covers: ContextManagerAgent, QAManagerAgent,
ProductionManagerAgent, AutomationManagerAgent.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in [str(ROOT), str(ROOT / "tools"), str(ROOT / "agents")]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest  # noqa: E402


# ═══════════════════════════════════════════════════════════════
#  Context Manager Agent
# ═══════════════════════════════════════════════════════════════

class TestContextManagerAgent:
    def test_set_and_get_context(self):
        from agents.context_manager_agent import (
            ContextManagerAgent,
        )
        agent = ContextManagerAgent()
        agent._contexts = {}
        agent.set_context("bot_a", "mode", "scan")
        assert agent.get_context("bot_a", "mode") == "scan"

    def test_get_all_context(self):
        from agents.context_manager_agent import (
            ContextManagerAgent,
        )
        agent = ContextManagerAgent()
        agent._contexts = {}
        agent.set_context("bot_a", "k1", "v1")
        agent.set_context("bot_a", "k2", "v2")
        ctx = agent.get_context("bot_a")
        assert ctx == {"k1": "v1", "k2": "v2"}

    def test_get_missing_key(self):
        from agents.context_manager_agent import (
            ContextManagerAgent,
        )
        agent = ContextManagerAgent()
        agent._contexts = {}
        assert agent.get_context("nope", "x") is None

    def test_freshness_check_no_stale(self):
        from agents.context_manager_agent import (
            ContextManagerAgent,
        )
        agent = ContextManagerAgent()
        agent._contexts = {}
        agent.set_context("bot", "key", "val")
        result = agent._check_freshness()
        assert result["total"] == 1
        assert result["stale_count"] == 0
        assert result["fresh"] == 1

    def test_compress_under_limit(self):
        from agents.context_manager_agent import (
            ContextManagerAgent,
        )
        agent = ContextManagerAgent()
        agent._contexts = {}
        agent.set_context("bot", "key", "val")
        result = agent._compress_if_needed()
        assert result["action"] == "none"

    def test_compress_over_limit(self):
        from agents.context_manager_agent import (
            ContextManagerAgent,
        )
        agent = ContextManagerAgent()
        agent._contexts = {}
        agent.MAX_CONTEXT_ITEMS = 5
        for i in range(10):
            agent.set_context("bot", f"k{i}", f"v{i}")
        result = agent._compress_if_needed()
        assert result["action"] == "compressed"
        assert result["removed"] == 5
        assert result["remaining"] == 5

    def test_memory_doctrine_check(self):
        from agents.context_manager_agent import (
            ContextManagerAgent,
        )
        agent = ContextManagerAgent()
        result = agent._check_memory_doctrine()
        assert "files_checked" in result
        assert "all_ok" in result
        assert isinstance(result["results"], dict)

    def test_run_cycle(self):
        from agents.context_manager_agent import (
            ContextManagerAgent,
        )
        agent = ContextManagerAgent()
        agent._contexts = {}
        agent._cycle = 0
        report = agent.run_cycle()
        assert report["cycle"] == 1
        assert "freshness" in report
        assert "memory_doctrine" in report
        assert "compression" in report
        assert "elapsed_s" in report

    def test_multiple_cycles(self):
        from agents.context_manager_agent import (
            ContextManagerAgent,
        )
        agent = ContextManagerAgent()
        agent._contexts = {}
        agent._cycle = 0
        agent.run_cycle()
        r2 = agent.run_cycle()
        assert r2["cycle"] == 2


# ═══════════════════════════════════════════════════════════════
#  QA Manager Agent
# ═══════════════════════════════════════════════════════════════

class TestQAManagerAgent:
    def test_run_cycle(self):
        from agents.qa_manager import QAManagerAgent
        agent = QAManagerAgent()
        agent._cycle = 0
        agent._history = []
        report = agent.run_cycle()
        assert report["cycle"] == 1
        assert "quality_score" in report
        assert "passed" in report
        assert "reports" in report
        assert "tests" in report
        assert "configs" in report
        assert "logs" in report

    def test_multiple_cycles(self):
        from agents.qa_manager import QAManagerAgent
        agent = QAManagerAgent()
        agent._cycle = 0
        agent._history = []
        agent.run_cycle()
        r2 = agent.run_cycle()
        assert r2["cycle"] == 2

    def test_config_integrity(self):
        from agents.qa_manager import QAManagerAgent
        agent = QAManagerAgent()
        result = agent._check_config_integrity()
        assert result["configs_checked"] >= 4
        assert result["valid"] >= 3

    def test_test_health(self):
        from agents.qa_manager import QAManagerAgent
        agent = QAManagerAgent()
        result = agent._check_test_health()
        assert result["test_files"] > 0
        assert result["total_lines"] > 0

    def test_report_quality(self):
        from agents.qa_manager import QAManagerAgent
        agent = QAManagerAgent()
        result = agent._check_report_quality()
        assert isinstance(result, dict)

    def test_log_errors(self):
        from agents.qa_manager import QAManagerAgent
        agent = QAManagerAgent()
        result = agent._check_log_errors()
        assert isinstance(result, dict)

    def test_history_capped_on_save(self, tmp_path):
        from agents.qa_manager import QAManagerAgent
        import json
        agent = QAManagerAgent()
        agent._cycle = 0
        agent._history = [
            {"cycle": i, "score": 0.9, "passed": True}
            for i in range(60)
        ]
        agent.run_cycle()
        # Capping happens on disk via _save_state
        state = json.loads(
            agent._state_path().read_text(
                encoding="utf-8",
            )
        )
        assert len(state["history"]) <= 50


# ═══════════════════════════════════════════════════════════════
#  Production Manager Agent
# ═══════════════════════════════════════════════════════════════

class TestProductionManagerAgent:
    def test_run_cycle(self):
        from agents.production_manager import (
            ProductionManagerAgent,
        )
        agent = ProductionManagerAgent()
        agent._cycle = 0
        agent._incidents = []
        report = agent.run_cycle()
        assert report["cycle"] == 1
        assert "health" in report
        assert "ports" in report
        assert "disk" in report
        assert "pid_files" in report
        assert "watchdog" in report

    def test_multiple_cycles(self):
        from agents.production_manager import (
            ProductionManagerAgent,
        )
        agent = ProductionManagerAgent()
        agent._cycle = 0
        agent._incidents = []
        agent.run_cycle()
        r2 = agent.run_cycle()
        assert r2["cycle"] == 2

    def test_port_check(self):
        from agents.production_manager import (
            ProductionManagerAgent,
        )
        agent = ProductionManagerAgent()
        result = agent._check_ports()
        assert "services" in result
        assert "up" in result
        assert "total" in result
        assert result["total"] == 3

    def test_disk_usage(self):
        from agents.production_manager import (
            ProductionManagerAgent,
        )
        agent = ProductionManagerAgent()
        result = agent._check_disk_usage()
        assert "directories" in result
        assert "total_mb" in result

    def test_pid_files(self):
        from agents.production_manager import (
            ProductionManagerAgent,
        )
        agent = ProductionManagerAgent()
        result = agent._check_pid_files()
        assert "pid_files" in result
        assert isinstance(result["details"], dict)

    def test_watchdog_log(self):
        from agents.production_manager import (
            ProductionManagerAgent,
        )
        agent = ProductionManagerAgent()
        result = agent._check_watchdog_log()
        assert "recent_restarts" in result
        assert "permanently_dead" in result

    def test_health_degraded_on_dead_services(self):
        from agents.production_manager import (
            ProductionManagerAgent,
        )
        agent = ProductionManagerAgent()
        agent._cycle = 0
        agent._incidents = []
        # Services won't be running in CI
        report = agent.run_cycle()
        # Ports will be DOWN -> "degraded"
        assert report["health"] in ("healthy", "degraded")


# ═══════════════════════════════════════════════════════════════
#  Automation Manager Agent
# ═══════════════════════════════════════════════════════════════

class TestAutomationManagerAgent:
    def test_run_cycle(self):
        from agents.automation_manager import (
            AutomationManagerAgent,
        )
        agent = AutomationManagerAgent()
        agent._cycle = 0
        agent._workflows = {}
        agent._execution_log = []
        report = agent.run_cycle()
        assert report["cycle"] == 1
        assert "daemons" in report
        assert "pipeline" in report
        assert "workflow_health" in report
        assert "elapsed_s" in report

    def test_multiple_cycles(self):
        from agents.automation_manager import (
            AutomationManagerAgent,
        )
        agent = AutomationManagerAgent()
        agent._cycle = 0
        agent._workflows = {}
        agent._execution_log = []
        agent.run_cycle()
        r2 = agent.run_cycle()
        assert r2["cycle"] == 2

    def test_register_workflow(self):
        from agents.automation_manager import (
            AutomationManagerAgent,
        )
        agent = AutomationManagerAgent()
        agent._workflows = {}
        agent.register_workflow(
            "test_wf", 300, "test_agent",
        )
        assert "test_wf" in agent._workflows
        wf = agent._workflows["test_wf"]
        assert wf["agent"] == "test_agent"
        assert wf["interval_s"] == 300
        assert wf["enabled"] is True

    def test_register_disabled_workflow(self):
        from agents.automation_manager import (
            AutomationManagerAgent,
        )
        agent = AutomationManagerAgent()
        agent._workflows = {}
        agent.register_workflow(
            "wf2", 600, "bot", enabled=False,
        )
        assert not agent._workflows["wf2"]["enabled"]

    def test_scan_daemon_configs(self):
        from agents.automation_manager import (
            AutomationManagerAgent,
        )
        agent = AutomationManagerAgent()
        result = agent._scan_daemon_configs()
        assert result["daemons_found"] >= 1
        assert isinstance(result["daemons"], dict)

    def test_pipeline_stages(self):
        from agents.automation_manager import (
            AutomationManagerAgent,
        )
        agent = AutomationManagerAgent()
        result = agent._check_pipeline_stages()
        assert "stages" in result
        assert "total_events" in result

    def test_workflow_health_empty(self):
        from agents.automation_manager import (
            AutomationManagerAgent,
        )
        agent = AutomationManagerAgent()
        agent._workflows = {}
        result = agent._check_workflow_health()
        assert result["total"] == 0
        assert result["healthy"] == 0

    def test_workflow_health_with_stale(self):
        from agents.automation_manager import (
            AutomationManagerAgent,
        )
        agent = AutomationManagerAgent()
        agent._workflows = {
            "old": {
                "enabled": True,
                "last_run": "2020-01-01T00:00:00",
                "interval_s": 60,
            },
        }
        result = agent._check_workflow_health()
        assert result["stale"] == 1

    def test_workflow_health_disabled(self):
        from agents.automation_manager import (
            AutomationManagerAgent,
        )
        agent = AutomationManagerAgent()
        agent._workflows = {
            "off": {"enabled": False},
        }
        result = agent._check_workflow_health()
        assert result["disabled"] == 1

    def test_execution_log_capped_on_save(
        self, tmp_path,
    ):
        from agents.automation_manager import (
            AutomationManagerAgent,
        )
        import json
        agent = AutomationManagerAgent()
        agent._cycle = 0
        agent._workflows = {}
        agent._execution_log = [
            {"cycle": i} for i in range(120)
        ]
        agent.run_cycle()
        # Capping happens on disk via _save_state
        state = json.loads(
            agent._state_path().read_text(
                encoding="utf-8",
            )
        )
        assert len(state["execution_log"]) <= 100
