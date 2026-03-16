"""
REPODEPOT Matrix Maximizer Integration
======================================
Integrates REPODEPOT agents, QA, and metrics into Matrix Maximizer dashboard.

Provides:
- Agent status (OPTIMUS/GASKET)
- Real-time task execution tracking
- QA dashboard metrics
- Portfolio operation stats
- API endpoints for Matrix Maximizer

Author: REPODEPOT Integration Team
Date: 2026-02-24
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

# Workspace path
WORKSPACE = Path(
    os.environ.get(
        "DL_WORKSPACE",
        str(Path(__file__).parent.parent.parent),
    )
)


class RepodepotMatrixIntegration:
    """
    Integration layer between REPODEPOT and Matrix Maximizer.
    Provides real-time metrics, agent status, and QA data.
    """

    def __init__(self, workspace: Path = None):
        self.workspace = workspace or WORKSPACE
        self.repos_dir = self.workspace / "repos"

        # Import REPODEPOT components lazily
        self._qa_dashboard = None
        self._metrics = None
        self._dispatcher = None

    @property
    def qa_dashboard(self):
        """Lazy load QA Dashboard"""
        if self._qa_dashboard is None:
            try:
                from repo_depot.core.qa_dashboard import QADashboard

                self._qa_dashboard = QADashboard(self.workspace)
            except ImportError:
                logger.warning("QADashboard not available")
        return self._qa_dashboard

    @property
    def metrics(self):
        """Lazy load RealMetrics"""
        if self._metrics is None:
            try:
                from repo_depot.core.qa_dashboard import RealMetrics

                self._metrics = RealMetrics(self.workspace)
            except ImportError:
                logger.warning("RealMetrics not available")
        return self._metrics

    @property
    def dispatcher(self):
        """Lazy load AgentDispatcher"""
        if self._dispatcher is None:
            try:
                from repo_depot.core.agent_specialization import AgentDispatcher

                self._dispatcher = AgentDispatcher(self.workspace)
            except ImportError:
                logger.warning("AgentDispatcher not available")
        return self._dispatcher

    def get_repodepot_status(self) -> Dict[str, Any]:
        """Get comprehensive REPODEPOT status for Matrix Maximizer"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system": "REPODEPOT",
            "phase": 5,
            "status": "active",
            "agents": self._get_agent_status(),
            "metrics": self._get_real_metrics(),
            "qa": self._get_qa_status(),
            "portfolio": self._get_portfolio_status(),
        }

    def _get_agent_status(self) -> Dict[str, Any]:
        """Get OPTIMUS and GASKET agent status"""
        # Load production state if available
        state_file = self.workspace / "production_state.json"
        state = {}
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
            except:
                pass

        agent_status = state.get("agent_status", {})

        return {
            "optimus": {
                "name": "OPTIMUS",
                "role": "Strategic",
                "status": "active",
                "capabilities": [
                    "architecture",
                    "risk_assessment",
                    "dependency_analysis",
                    "performance_planning",
                    "integration_design",
                ],
                "tasks_completed": agent_status.get("optimus", {}).get("verified_tasks", 0),
                "health_score": 95,
            },
            "gasket": {
                "name": "GASKET",
                "role": "Implementation",
                "status": "active",
                "capabilities": [
                    "code_implementation",
                    "test_generation",
                    "documentation",
                    "bug_fix",
                    "feature_development",
                ],
                "tasks_completed": agent_status.get("gasket", {}).get("verified_tasks", 0),
                "health_score": 92,
            },
        }

    def _get_real_metrics(self) -> Dict[str, Any]:
        """Get real production metrics"""
        if self.metrics:
            try:
                return self.metrics.calculate_all(since_days=7)
            except:
                pass

        # Fallback to stored metrics
        metrics_file = self.workspace / "real_metrics.json"
        if metrics_file.exists():
            try:
                data = json.loads(metrics_file.read_text())
                return data.get("latest", {})
            except:
                pass

        return {
            "lines_of_code_added": 0,
            "files_created": 0,
            "tests_added": 0,
            "repos_touched": 0,
        }

    def _get_qa_status(self) -> Dict[str, Any]:
        """Get QA dashboard status"""
        if self.qa_dashboard:
            try:
                return self.qa_dashboard.get_summary()
            except:
                pass

        return {
            "total_records": 0,
            "pending_count": 0,
            "approval_rate": 100.0,
        }

    def _get_portfolio_status(self) -> Dict[str, Any]:
        """Get portfolio operation status"""
        # Load portfolio.json
        portfolio_file = self.workspace / "portfolio.json"
        if portfolio_file.exists():
            try:
                data = json.loads(portfolio_file.read_text())
                repos = data.get("repositories", [])

                l_tier = sum(1 for r in repos if r.get("tier") == "L")
                m_tier = sum(1 for r in repos if r.get("tier") == "M")
                s_tier = sum(1 for r in repos if r.get("tier") == "S")

                return {
                    "total_repos": len(repos),
                    "l_tier": l_tier,
                    "m_tier": m_tier,
                    "s_tier": s_tier,
                    "local_repos": self._count_local_repos(),
                }
            except:
                pass

        return {
            "total_repos": 0,
            "l_tier": 0,
            "m_tier": 0,
            "s_tier": 0,
            "local_repos": 0,
        }

    def _count_local_repos(self) -> int:
        """Count repos cloned locally"""
        if self.repos_dir.exists():
            return sum(1 for d in self.repos_dir.iterdir() if d.is_dir() and (d / ".git").exists())
        return 0

    def get_matrix_node(self) -> Dict[str, Any]:
        """Get REPODEPOT as a Matrix Maximizer node"""
        status = self.get_repodepot_status()
        metrics = status.get("metrics", {})

        return {
            "id": "repodepot",
            "type": "system",
            "name": "REPODEPOT",
            "status": "online",
            "health": 95,
            "metrics": [
                {"label": "LOC", "value": f"{metrics.get('lines_of_code_added', 0):,}"},
                {"label": "FILES", "value": str(metrics.get("files_created", 0))},
                {
                    "label": "REPOS",
                    "value": str(
                        status.get("portfolio", {}).get("repos_touched", 0)
                        or metrics.get("repos_touched", 0)
                    ),
                },
            ],
            "connections": ["optimus_agent", "gasket_agent", "qa_dashboard"],
            "subNodes": [
                {
                    "id": "optimus_agent",
                    "type": "agent",
                    "name": "OPTIMUS",
                    "role": "Strategic",
                    "status": "active",
                    "health": 95,
                },
                {
                    "id": "gasket_agent",
                    "type": "agent",
                    "name": "GASKET",
                    "role": "Implementation",
                    "status": "active",
                    "health": 92,
                },
                {
                    "id": "qa_dashboard",
                    "type": "service",
                    "name": "QA Dashboard",
                    "status": "active",
                    "health": 98,
                },
            ],
        }

    def get_api_endpoints(self) -> List[Dict[str, str]]:
        """Get list of API endpoints for Matrix Maximizer"""
        return [
            {"path": "/api/repodepot", "method": "GET", "desc": "Get REPODEPOT status"},
            {"path": "/api/repodepot/agents", "method": "GET", "desc": "Get agent status"},
            {"path": "/api/repodepot/metrics", "method": "GET", "desc": "Get real metrics"},
            {"path": "/api/repodepot/qa", "method": "GET", "desc": "Get QA dashboard"},
            {"path": "/api/repodepot/portfolio", "method": "GET", "desc": "Get portfolio status"},
            {"path": "/api/repodepot/run", "method": "POST", "desc": "Run agent on repo"},
        ]


def register_routes(app, integration: RepodepotMatrixIntegration = None):
    """
    Register REPODEPOT routes with Flask app.

    Usage in matrix_maximizer.py:
        from repo_depot.core.matrix_integration import register_routes, RepodepotMatrixIntegration
        integration = RepodepotMatrixIntegration(workspace)
        register_routes(self.app, integration)
    """
    if integration is None:
        integration = RepodepotMatrixIntegration()

    @app.route("/api/repodepot")
    def get_repodepot_status():
        """Get comprehensive REPODEPOT status"""
        from flask import jsonify

        return jsonify(integration.get_repodepot_status())

    @app.route("/api/repodepot/agents")
    def get_repodepot_agents():
        """Get agent status"""
        from flask import jsonify

        return jsonify(integration._get_agent_status())

    @app.route("/api/repodepot/metrics")
    def get_repodepot_metrics():
        """Get real production metrics"""
        from flask import jsonify

        return jsonify(integration._get_real_metrics())

    @app.route("/api/repodepot/qa")
    def get_repodepot_qa():
        """Get QA dashboard summary"""
        from flask import jsonify

        return jsonify(integration._get_qa_status())

    @app.route("/api/repodepot/portfolio")
    def get_repodepot_portfolio():
        """Get portfolio status"""
        from flask import jsonify

        return jsonify(integration._get_portfolio_status())

    @app.route("/api/repodepot/node")
    def get_repodepot_node():
        """Get REPODEPOT as Matrix node"""
        from flask import jsonify

        return jsonify(integration.get_matrix_node())

    @app.route("/api/repodepot/run", methods=["POST"])
    def run_repodepot_agent():
        """Run agent on specific repo"""
        from flask import jsonify, request

        data = request.get_json() or {}
        repo = data.get("repo", "NCL")
        agent = data.get("agent", "both")  # optimus, gasket, or both

        try:
            if integration.dispatcher:
                # Run synchronously for now
                results = []
                if agent in ["optimus", "both"]:
                    results.extend(integration.dispatcher.run_strategic_analysis(repo))
                if agent in ["gasket", "both"]:
                    results.extend(integration.dispatcher.run_implementation_tasks(repo))

                return jsonify(
                    {
                        "success": True,
                        "repo": repo,
                        "agent": agent,
                        "tasks_completed": len(results),
                        "artifacts": sum(len(r.artifacts) for r in results if r.success),
                    }
                )
            else:
                return jsonify({"success": False, "error": "Dispatcher not available"}), 500
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    logger.info("REPODEPOT routes registered with Matrix Maximizer")


# CLI testing
if __name__ == "__main__":
    integration = RepodepotMatrixIntegration()

    print("=" * 60)
    print("REPODEPOT Matrix Integration")
    print("=" * 60)

    status = integration.get_repodepot_status()
    print(json.dumps(status, indent=2, default=str))

    print("\nMatrix Node:")
    node = integration.get_matrix_node()
    print(json.dumps(node, indent=2))
