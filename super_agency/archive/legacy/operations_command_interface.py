#!/usr/bin/env python3
"""
Operations Command Interface (OCI)
Conversational Operations Management System
Enables real-time dialogue with department heads and operational updates
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import re
from agents.daily_brief import collect_repo_summary
from agents.repo_sentry import check_repo_status

class OperationsCommandInterface:
    """
    OCI - Operations Command Interface
    Provides conversational access to all BIT RAGE LABOUR operations
    """

    def __init__(self):
        """Initialize."""
        self.departments = self._initialize_departments()
        self.conversation_history = []
        self.operational_context = {}

    def _initialize_departments(self) -> Dict[str, Dict]:
        """Initialize department mappings and their operational interfaces"""

        departments = {
            # Core Operations
            "ncc": {
                "name": "Neural Command Center",
                "head": "NCC Command Director",
                "systems": ["command_processor", "resource_allocator", "intelligence_synthesizer"],
                "capabilities": ["strategic_coordination", "resource_management", "crisis_response"],
                "data_sources": ["NCC/ncc_orchestrator.py", "NCC/engine/", "NCC/adapters/"]
            },
            "council_52": {
                "name": "Council 52 Intelligence",
                "head": "Chief Intelligence Officer",
                "systems": ["intelligence_gathering", "analysis_engine", "council_operations"],
                "capabilities": ["market_intelligence", "predictive_analysis", "strategic_foresight"],
                "data_sources": ["council_52_system", "intelligence_feeds"]
            },
            "portfolio_operations": {
                "name": "Portfolio Operations",
                "head": "Portfolio Director",
                "systems": ["company_monitoring", "performance_tracking", "integration_management"],
                "capabilities": ["company_oversight", "performance_monitoring", "integration_coordination"],
                "data_sources": ["portfolio.json", "companies/", "agents/portfolio_*.py"]
            },

            # Technology Divisions
            "ai_research": {
                "name": "AI Research Division",
                "head": "Chief AI Officer",
                "systems": ["ncl_second_brain", "machine_learning", "neural_networks"],
                "capabilities": ["ai_development", "cognitive_processing", "pattern_recognition"],
                "data_sources": ["ncl_second_brain/", "agents/ncl_*.py"]
            },
            "platform_engineering": {
                "name": "Platform Engineering",
                "head": "Chief Technology Officer",
                "systems": ["infrastructure", "devops", "system_architecture"],
                "capabilities": ["system_design", "infrastructure_management", "deployment_automation"],
                "data_sources": ["infrastructure/", "deployment_configs/"]
            },

            # Business Divisions
            "market_intelligence": {
                "name": "Market Intelligence",
                "head": "Chief Market Officer",
                "systems": ["market_analysis", "competitive_intelligence", "trend_monitoring"],
                "capabilities": ["market_research", "competitive_analysis", "trend_forecasting"],
                "data_sources": ["market_data/", "intelligence_reports/"]
            },
            "product_development": {
                "name": "Product Development",
                "head": "Chief Product Officer",
                "systems": ["product_management", "roadmap_planning", "feature_development"],
                "capabilities": ["product_strategy", "roadmap_management", "feature_prioritization"],
                "data_sources": ["product_backlog/", "roadmap_docs/"]
            },

            # Operational Divisions
            "security_operations": {
                "name": "Security Operations",
                "head": "Chief Security Officer",
                "systems": ["threat_detection", "security_monitoring", "incident_response"],
                "capabilities": ["security_monitoring", "threat_analysis", "incident_management"],
                "data_sources": ["security_logs/", "threat_intelligence/"]
            },
            "financial_operations": {
                "name": "Financial Operations",
                "head": "Chief Financial Officer",
                "systems": ["financial_planning", "budget_management", "performance_analytics"],
                "capabilities": ["financial_planning", "budget_oversight", "performance_analysis"],
                "data_sources": ["financial_reports/", "budget_data/"]
            }
        }

        # Add portfolio companies as departments
        portfolio_file = Path(__file__).parent / "portfolio.json"
        if portfolio_file.exists():
            portfolio_data = json.loads(portfolio_file.read_text())
            for repo in portfolio_data.get("repositories", []):
                dept_key = repo["name"].lower().replace("-", "_")
                # Don't override core departments
                if dept_key not in departments:
                    departments[dept_key] = {
                        "name": repo["name"],
                        "head": f"{repo['name']} Operations Lead",
                        "systems": ["company_operations", "development", "integration"],
                        "capabilities": ["operational_execution", "development_progress", "integration_status"],
                        "data_sources": [f"companies/{repo['name']}/", f"repos/{repo['name']}/"],
                        "portfolio_company": True,
                        "tier": repo.get("tier", "TBD"),
                        "autonomy_level": repo.get("autonomy_level", "L1")
                    }

        return departments

    async def process_query(self, query: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process natural language query and return operational update

        Args:
            query: Natural language query about operations
            user_context: User context information

        Returns:
            Structured response with operational data
        """

        # Parse query to identify department and intent
        department, intent = self._parse_query(query)

        if not department:
            return {
                "response_type": "clarification_needed",
                "message": "I need to know which department or division you'd like an update from. Try asking about NCC, Council 52, or a specific portfolio company.",
                "available_departments": list(self.departments.keys())[:10]  # Show first 10
            }

        # Get operational update for the department
        update = await self._get_department_update(department, intent)

        # Store in conversation history
        self.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "department": department,
            "response": update
        })

        return update

    def _parse_query(self, query: str) -> tuple[str, str]:
        """
        Parse natural language query to identify department and intent

        Returns:
            (department_key, intent_type)
        """

        query_lower = query.lower()

        # Department identification patterns
        department_patterns = {
            "ncc": ["ncc", "neural command", "command center", "neural command center"],
            "council_52": ["council", "council 52", "intelligence", "cio", "chief intelligence"],
            "portfolio_operations": ["portfolio", "companies", "company operations"],
            "ai_research": ["ai", "artificial intelligence", "research", "ncl", "neural"],
            "platform_engineering": ["platform", "engineering", "infrastructure", "tech", "cto"],
            "market_intelligence": ["market", "marketing", "market intelligence", "cmo"],
            "product_development": ["product", "development", "product development", "cpo"],
            "security_operations": ["security", "security operations", "cso"],
            "financial_operations": ["financial", "finance", "financial operations", "cfo"]
        }

        # Check for specific department mentions
        for dept_key, patterns in department_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                return dept_key, self._identify_intent(query_lower)

        # Check for portfolio company mentions
        portfolio_file = Path(__file__).parent / "portfolio.json"
        if portfolio_file.exists():
            portfolio_data = json.loads(portfolio_file.read_text())
            for repo in portfolio_data.get("repositories", []):
                if repo["name"].lower() in query_lower:
                    return repo["name"].lower().replace("-", "_"), self._identify_intent(query_lower)

        return None, "general_update"

    def _identify_intent(self, query: str) -> str:
        """Identify the intent of the query"""

        intents = {
            "status": ["status", "how are", "what's up", "situation"],
            "performance": ["performance", "metrics", "kpis", "results"],
            "issues": ["issues", "problems", "challenges", "blockers"],
            "progress": ["progress", "advancement", "development", "updates"],
            "resources": ["resources", "capacity", "utilization", "allocation"],
            "risks": ["risks", "threats", "concerns", "warnings"]
        }

        for intent, patterns in intents.items():
            if any(pattern in query for pattern in patterns):
                return intent

        return "general_update"

    async def _get_department_update(self, department: str, intent: str) -> Dict[str, Any]:
        """Get operational update for specific department"""

        if department not in self.departments:
            return {
                "response_type": "department_not_found",
                "message": f"Department '{department}' not found. Available departments include: {', '.join(list(self.departments.keys())[:5])}...",
                "department": department
            }

        dept_info = self.departments[department]

        # Gather operational data based on department type
        if dept_info.get("portfolio_company"):
            update_data = await self._get_portfolio_company_update(department, intent)
        else:
            update_data = await self._get_core_department_update(department, intent)

        return {
            "response_type": "operational_update",
            "department": department,
            "department_name": dept_info["name"],
            "head": dept_info["head"],
            "intent": intent,
            "timestamp": datetime.now().isoformat(),
            "data": update_data
        }

    async def _get_portfolio_company_update(self, company_key: str, intent: str) -> Dict[str, Any]:
        """Get operational update for portfolio company"""

        # Find company in portfolio
        portfolio_file = Path(__file__).parent / "portfolio.json"
        company = None
        if portfolio_file.exists():
            portfolio_data = json.loads(portfolio_file.read_text())
            for repo in portfolio_data.get("repositories", []):
                if repo["name"].lower().replace("-", "_") == company_key:
                    company = repo
                    break

        if not company:
            return {"error": "Company not found in portfolio"}

        # Get repo status
        try:
            repo_status = check_repo_status(company["name"])
        except Exception:
            repo_status = {"status": "unknown", "last_check": None}

        # Get daily brief data
        try:
            brief_data = collect_repo_summary(company["name"])
        except Exception:
            brief_data = {"commits": 0, "delta": None}

        return {
            "company_name": company["name"],
            "tier": company.get("tier", "TBD"),
            "autonomy_level": company.get("autonomy_level", "L1"),
            "visibility": company.get("visibility", "public"),
            "repo_status": repo_status,
            "recent_activity": brief_data,
            "operational_health": self._assess_operational_health(brief_data, repo_status)
        }

    async def _get_core_department_update(self, department: str, intent: str) -> Dict[str, Any]:
        """Get operational update for core BIT RAGE LABOUR department"""

        dept_info = self.departments[department]

        # Simulate operational data gathering (in real implementation, this would query actual systems)
        base_data = {
            "systems_status": {},
            "recent_activities": [],
            "performance_metrics": {},
            "active_projects": [],
            "resource_utilization": {}
        }

        # Add department-specific data
        if department == "ncc":
            base_data.update(await self._get_ncc_status())
        elif department == "council_52":
            base_data.update(await self._get_council_52_status())
        elif department == "portfolio_operations":
            base_data.update(await self._get_portfolio_status())

        return base_data

    async def _get_ncc_status(self) -> Dict[str, Any]:
        """Get NCC operational status"""
        return {
            "command_queue_depth": 0,
            "active_operations": 0,
            "system_health": "operational",
            "last_crisis_response": None,
            "resource_utilization": 65
        }

    async def _get_council_52_status(self) -> Dict[str, Any]:
        """Get Council 52 operational status"""
        return {
            "active_intelligence_streams": 12,
            "pending_analyses": 3,
            "intelligence_quality_score": 8.7,
            "last_major_insight": "2026-02-20T10:30:00Z"
        }

    async def _get_portfolio_status(self) -> Dict[str, Any]:
        """Get portfolio operations status"""
        portfolio_file = Path(__file__).parent / "portfolio.json"
        if portfolio_file.exists():
            portfolio_data = json.loads(portfolio_file.read_text())
            total_repos = len(portfolio_data.get("repositories", []))
            active_repos = sum(1 for r in portfolio_data.get("repositories", [])
                              if r.get("integration_status") == "READY_FOR_INTEGRATION")
        else:
            total_repos = 0
            active_repos = 0

        return {
            "total_companies": total_repos,
            "active_companies": active_repos,
            "integration_progress": f"{active_repos}/{total_repos}",
            "recent_deployments": []
        }

    def _assess_operational_health(self, brief_data: Dict, repo_status: Dict) -> str:
        """Assess operational health based on available data"""

        if not brief_data.get("delta"):
            return "inactive"

        commits = brief_data.get("commits", 0)
        if commits > 10:
            return "highly_active"
        elif commits > 5:
            return "active"
        elif commits > 0:
            return "moderately_active"
        else:
            return "low_activity"

    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get summary of conversation history"""
        return {
            "total_queries": len(self.conversation_history),
            "departments_queried": list(set(h["department"] for h in self.conversation_history if h.get("department"))),
            "last_query": self.conversation_history[-1] if self.conversation_history else None,
            "conversation_span": self._calculate_conversation_span()
        }

    def _calculate_conversation_span(self) -> str:
        """Calculate time span of conversation"""
        if not self.conversation_history:
            return "0 minutes"

        start = datetime.fromisoformat(self.conversation_history[0]["timestamp"])
        end = datetime.fromisoformat(self.conversation_history[-1]["timestamp"])
        duration = end - start

        if duration.days > 0:
            return f"{duration.days} days"
        elif duration.seconds > 3600:
            return f"{duration.seconds // 3600} hours"
        else:
            return f"{duration.seconds // 60} minutes"

# Global OCI instance
oci = OperationsCommandInterface()

async def handle_operations_query(query: str, user_context: Dict = None) -> Dict[str, Any]:
    """
    Main entry point for operations queries
    Usage: Can be called from chat interfaces, APIs, or command line
    """
    # Create a new instance for each call to avoid event loop issues
    oci = OperationsCommandInterface()
    return await oci.process_query(query, user_context)

if __name__ == "__main__":
    # CLI interface for testing
    import sys

    async def main():
        if len(sys.argv) < 2:
            print("Usage: python operations_command_interface.py 'your query here'")
            print("Example: python operations_command_interface.py 'How is NCC doing today?'")
            return

        query = " ".join(sys.argv[1:])
        result = await handle_operations_query(query)

        print(f"\n🤖 Operations Command Interface Response")
        print(f"Department: {result.get('department_name', 'Unknown')}")
        print(f"Head: {result.get('head', 'Unknown')}")
        print(f"Response Type: {result.get('response_type', 'Unknown')}")
        print(f"\n{result.get('message', 'No message')}")
        print(f"\nData: {json.dumps(result.get('data', {}), indent=2)}")

    asyncio.run(main())
