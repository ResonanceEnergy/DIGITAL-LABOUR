#!/usr/bin/env python3
"""
Inner Council Test Suite
Comprehensive tests for the Inner Council intelligence system
"""

import sys
import json
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from council import InnerCouncil, CouncilMember
from integrations.ncl_integration import NCLIntegration
from integrations.orchestrator_integration import OrchestratorIntegration
from scripts.report_generator import generate_comprehensive_report
from scripts.maintenance import generate_health_report
from scripts.analytics import analyze_council_activity


class TestInnerCouncil:
    """Test Inner Council core functionality"""

    def setup_method(self):
        """Setup test fixtures"""
        self.council = InnerCouncil()
        self.test_member = CouncilMember(
            name="Test Member",
            channel_id="UC123456789",
            focus_areas=["AI", "Technology"],
            priority="high",
            monitoring_frequency="daily"
        )

    def test_council_initialization(self):
        """Test council initializes correctly"""
        assert self.council is not None
        assert len(self.council.members) > 0
        assert isinstance(self.council.members[0], CouncilMember)

    def test_council_member_creation(self):
        """Test council member creation"""
        assert self.test_member.name == "Test Member"
        assert self.test_member.channel_id == "UC123456789"
        assert "AI" in self.test_member.focus_areas
        assert self.test_member.priority == "high"

    def test_monitor_channels(self):
        """Test monitoring council channels"""
        result = self.council.monitor_channels(days_back=1)
        assert result is not None
        assert isinstance(result, dict)

    def test_simulate_content_discovery(self):
        """Test simulated content discovery for a member"""
        member = self.council.members[0]
        content = self.council.simulate_content_discovery(member, days_back=1)
        assert content is not None
        assert isinstance(content, list)


class TestNCLIntegration:
    """Test NCL integration functionality"""

    def setup_method(self):
        """Setup test fixtures"""
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w+', delete=False, suffix='.ndjson')
        self.temp_file.close()
        self.ncl_integration = NCLIntegration(
            ncl_events_path=self.temp_file.name)

    def teardown_method(self):
        """Cleanup test fixtures"""
        os.unlink(self.temp_file.name)

    def test_store_insight(self):
        """Test storing insights in NCL"""
        test_insight = {
            "type": "inner_council_analysis",
            "data": {
                "council_member": "Test Member",
                "content_title": "Test Content",
                "key_insights": ["Test insight"]
            }
        }

        result = self.ncl_integration.store_insight(test_insight)
        assert result is True

        # Verify stored
        insights = self.ncl_integration.query_council_insights()
        assert len(insights) == 1
        assert insights[0]["data"]["council_member"] == "Test Member"

    def test_query_insights(self):
        """Test querying insights"""
        insights_data = [
            {"type": "inner_council_analysis",
             "data": {"council_member": "Member1"}},
            {"type": "inner_council_daily_report",
             "data": {"report_date": "2024-01-01"}},
            {"type": "inner_council_analysis",
             "data": {"council_member": "Member2"}}]

        for insight in insights_data:
            self.ncl_integration.store_insight(insight)

        # Query all (default query_type="recent")
        all_insights = self.ncl_integration.query_council_insights()
        assert len(all_insights) == 3

        # Query analysis only
        analysis_insights = self.ncl_integration.query_council_insights(
            query_type="analysis_only")
        assert len(analysis_insights) == 2

    def test_get_member_insights(self):
        """Test getting insights for specific member"""
        insights_data = [
            {"type": "inner_council_analysis", "data": {
                "council_member": "Member1", "content_title": "Content1"}},
            {"type": "inner_council_analysis", "data": {
                "council_member": "Member2", "content_title": "Content2"}},
            {"type": "inner_council_analysis", "data": {
                "council_member": "Member1", "content_title": "Content3"}}
        ]

        for insight in insights_data:
            self.ncl_integration.store_insight(insight)

        member_insights = self.ncl_integration.get_council_member_insights(
            "Member1")
        assert len(member_insights) == 2
        assert all(i["data"]["council_member"] ==
                   "Member1" for i in member_insights)


class TestOrchestratorIntegration:
    """Test orchestrator integration functionality"""

    def setup_method(self):
        """Setup test fixtures"""
        self.orchestrator = OrchestratorIntegration()

    def test_process_council_intelligence(self):
        """Test processing council intelligence into proposals"""
        test_report = {
            "date": datetime.now().date().isoformat(),
            "council_members_monitored": 3,
            "new_content_analyzed": 5,
            "key_insights": ["AI advancement", "Market shift"],
            "policy_recommendations": ["Update strategy"],
            "strategic_actions": ["Research AI tools"],
            "risk_alerts": ["Competitive pressure"]
        }

        result = self.orchestrator.process_council_intelligence(test_report)
        assert result is not None
        assert "proposal_id" in result

    def test_agent_marketplace_discovery(self):
        """Ensure marketplace can discover and list agents"""
        from inner_council.agents.agent_marketplace import global_marketplace
        available = global_marketplace.list_available_agents()
        assert isinstance(available, list)
        assert len(available) >= 1

    def test_swarm_coordinator_basic(self):
        """Basic swarm operations should work"""
        from inner_council.agents.agent_marketplace import global_marketplace
        from inner_council.swarm_intelligence import SwarmCoordinator
        sc = SwarmCoordinator()
        available = global_marketplace.list_available_agents()
        if available:
            swarm_id = sc.initiate_swarm("test task", [available[0]])
            assert swarm_id is not None
            assert swarm_id in sc.list_swarms()
            results = sc.collect_results(swarm_id)
            assert isinstance(results, dict)
            terminated = sc.terminate_swarm(swarm_id)
            assert terminated is True


class TestScripts:
    """Test script functionality"""

    @patch('scripts.daily_monitor.OrchestratorIntegration')
    @patch('scripts.daily_monitor.NCLIntegration')
    @patch('scripts.daily_monitor.InnerCouncil')
    def test_daily_monitor(self, mock_council, mock_ncl, mock_orchestrator):
        """Test daily monitor script"""
        from scripts.daily_monitor import main as run_daily_monitor

        mock_council_instance = Mock()
        mock_council.return_value = mock_council_instance
        mock_council_instance.generate_daily_report.return_value = {
            "date": "2024-01-01",
            "council_members_monitored": 3,
            "new_content_analyzed": 5,
            "key_insights": [],
            "policy_recommendations": [],
            "strategic_actions": [],
            "risk_alerts": []
        }

        mock_ncl_instance = Mock()
        mock_ncl.return_value = mock_ncl_instance

        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance
        mock_orch_instance.process_council_intelligence.return_value = {
            "proposal_id": "test-123",
            "requires_council_review": False
        }

        result = run_daily_monitor()
        assert result is True
        mock_council_instance.generate_daily_report.assert_called_once()

    @patch('scripts.report_generator.NCLIntegration')
    def test_report_generator(self, mock_ncl):
        """Test report generator"""
        mock_ncl_instance = Mock()
        mock_ncl.return_value = mock_ncl_instance
        mock_ncl_instance.query_council_insights.return_value = [
            {
                "timestamp": datetime.now().isoformat(),
                "type": "inner_council_analysis",
                "data": {
                    "council_member": "Test Member",
                    "key_insights": ["Test insight"]
                }
            }
        ]

        report = generate_comprehensive_report(days_back=7)
        assert report is not None
        assert "Inner Council Intelligence Report" in report

    @patch('scripts.maintenance.NCLIntegration')
    def test_maintenance_health_report(self, mock_ncl):
        """Test maintenance health report"""
        mock_ncl_instance = Mock()
        mock_ncl.return_value = mock_ncl_instance
        mock_ncl_instance.query_council_insights.return_value = []

        report = generate_health_report()
        assert report is not None
        assert "Inner Council Health Report" in report

    @patch('scripts.analytics.NCLIntegration')
    def test_analytics_activity(self, mock_ncl):
        """Test analytics activity analysis"""
        mock_ncl_instance = Mock()
        mock_ncl.return_value = mock_ncl_instance
        mock_ncl_instance.query_council_insights.return_value = [
            {
                "timestamp": datetime.now().isoformat(),
                "data": {"council_member": "Test Member"}
            }
        ]

        result = analyze_council_activity(days_back=30)
        assert result is not None
        assert "total_insights" in result
        assert "member_activity" in result


class TestConfiguration:
    """Test configuration loading and validation"""

    def test_config_loading(self):
        """Test loading configuration"""
        config_path = Path(__file__).parent.parent / "config" / "settings.json"

        with open(config_path, 'r') as f:
            config = json.load(f)

        assert "system" in config
        assert "council_members" in config
        assert len(config["council_members"]) > 0
        assert "monitoring" in config
        assert "analysis" in config

    def test_config_validation(self):
        """Test configuration validation"""
        config_path = Path(__file__).parent.parent / "config" / "settings.json"

        with open(config_path, 'r') as f:
            config = json.load(f)

        required_system_fields = ["name", "version", "description"]
        for field in required_system_fields:
            assert field in config["system"]

        for member in config["council_members"]:
            required_member_fields = [
                "name", "channel_id", "focus_areas", "priority",
                "monitoring_frequency"]
            for field in required_member_fields:
                assert field in member

        assert "max_videos_per_channel" in config["monitoring"]
        assert "analysis_depth" in config["monitoring"]


class TestIntegration:
    """Test integration between components"""

    def setup_method(self):
        """Setup integration test fixtures"""
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w+', delete=False, suffix='.ndjson')
        self.temp_file.close()
        self.ncl_integration = NCLIntegration(
            ncl_events_path=self.temp_file.name)

    def teardown_method(self):
        """Cleanup integration test fixtures"""
        os.unlink(self.temp_file.name)

    def test_full_council_workflow(self):
        """Test full council workflow from monitoring to storage"""
        council = InnerCouncil()
        member = council.members[0]

        # Monitor channels (uses simulated content)
        new_content = council.monitor_channels(days_back=1)
        assert isinstance(new_content, dict)

        # Store an insight in NCL
        self.ncl_integration.store_insight({
            "type": "inner_council_analysis",
            "data": {
                "council_member": member.name,
                "key_insights": ["Test insight from workflow"]
            }
        })

        stored = self.ncl_integration.query_council_insights()
        assert len(stored) == 1
        assert stored[0]["data"]["council_member"] == member.name

    def test_council_to_orchestrator_integration(self):
        """Test integration between council and orchestrator"""
        test_report = {
            "date": datetime.now().date().isoformat(),
            "council_members_monitored": 1,
            "new_content_analyzed": 1,
            "key_insights": ["AI breakthrough"],
            "policy_recommendations": ["Update AI policy"],
            "strategic_actions": ["Invest in AI"],
            "risk_alerts": []
        }

        orchestrator = OrchestratorIntegration()
        result = orchestrator.process_council_intelligence(test_report)
        assert result is not None
        assert "proposal_id" in result

    @pytest.mark.xfail(
        reason="root-level agents package shadowed by inner_council/agents in sys.path")
    def test_run_script_import(self):
        """Ensure run_digital_labour can be imported without errors"""
        root_dir = str(Path(__file__).parent.parent.parent)
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
        import run_digital_labour
        assert hasattr(run_digital_labour, 'main')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])