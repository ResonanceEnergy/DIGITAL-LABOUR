#!/usr/bin/env python3
"""
Inner Council Orchestrator Integration
Connect council intelligence with daily DIGITAL LABOUR operations
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class OrchestratorIntegration:
    """Integration between Inner Council and DIGITAL LABOUR orchestrator"""

    def __init__(self, decisions_dir: str="decisions",
                 reports_dir: str="reports/daily"):
        self.decisions_dir = Path(decisions_dir)
        self.reports_dir = Path(reports_dir)
        self.decisions_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)

    def process_council_intelligence(self, daily_report: Dict[str, Any]) -> Dict[str, Any]:
        """Process Inner Council intelligence for orchestrator consumption"""

        # Create council intelligence proposal for decision framework
        proposal = {
            "id": f"council_intel_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "type": "council_intelligence",
            "repo": "inner_council",
            "action": "strategic_planning",
            "autonomy": "L2",
            "risk": "LOW",
            "rationale": "Daily intelligence from Inner Council monitoring and analysis",
            "data": {
                "council_members_monitored": daily_report.get("council_members_monitored"),
                "new_content_analyzed": daily_report.get("new_content_analyzed"),
                "key_insights": daily_report.get("key_insights", []),
                "policy_recommendations": daily_report.get("policy_recommendations", []),
                "strategic_actions": daily_report.get("strategic_actions", []),
                "risk_alerts": daily_report.get("risk_alerts", [])
            },
            "proposed_actions": self._generate_proposed_actions(daily_report),
            "timestamp": datetime.now().isoformat()
        }

        # Save proposal for council review
        self._save_proposal(proposal)

        # Generate immediate operational recommendations
        operations_recommendations = self._generate_operations_recommendations(
            daily_report)

        return {
            "proposal_id": proposal["id"],
            "processed_at": datetime.now().isoformat(),
            "recommendations": operations_recommendations,
            "requires_council_review": self._requires_council_review(daily_report)
        }

    def _generate_proposed_actions(self, daily_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate specific proposed actions from council intelligence"""

        actions = []

        # Analyze strategic actions for implementation
        strategic_actions = daily_report.get("strategic_actions", [])

        for action_text in strategic_actions[:5]:  # Limit to top 5
            action = {
                "description": action_text,
                "priority": self._assess_action_priority(action_text),
                "timeline": self._estimate_timeline(action_text),
                "resources_required": self._identify_resources(action_text),
                "success_metrics": self._define_success_metrics(action_text),
                "risk_level": "LOW",
                "autonomy_level": "L2"
            }
            actions.append(action)

        return actions

    def _assess_action_priority(self, action_text: str) -> str:
        """Assess priority level for an action"""

        high_priority_keywords = [
            'urgent', 'critical', 'immediate', 'breaking', 'crisis']
        medium_priority_keywords = ['important',
            'significant', 'opportunity', 'trend']

        text_lower = action_text.lower()

        if any(keyword in text_lower for keyword in high_priority_keywords):
            return "HIGH"
        elif any(keyword in text_lower for keyword in medium_priority_keywords):
            return "MEDIUM"
        else:
            return "LOW"

    def _estimate_timeline(self, action_text: str) -> str:
        """Estimate timeline for action implementation"""

        immediate_keywords = ['immediate', 'urgent', 'now', 'today', 'asap']
        short_term_keywords = ['week', 'weeks', 'short', 'quick']
        medium_term_keywords = ['month', 'months', 'quarter']

        text_lower = action_text.lower()

        if any(keyword in text_lower for keyword in immediate_keywords):
            return "IMMEDIATE"
        elif any(keyword in text_lower for keyword in short_term_keywords):
            return "1-2 WEEKS"
        elif any(keyword in text_lower for keyword in medium_term_keywords):
            return "1-3 MONTHS"
        else:
            return "ONGOING"

    def _identify_resources(self, action_text: str) -> List[str]:
        """Identify resources required for action"""

        resources = []

        # Analyze action text for resource requirements
        text_lower = action_text.lower()

        if 'research' in text_lower or 'analysis' in text_lower:
            resources.append("Research team")
        if 'development' in text_lower or 'build' in text_lower:
            resources.append("Development team")
        if 'funding' in text_lower or 'budget' in text_lower:
            resources.append("Financial resources")
        if 'partnership' in text_lower or 'collaboration' in text_lower:
            resources.append("Business development")
        if 'training' in text_lower or 'education' in text_lower:
            resources.append("Training resources")

        # Default resources if none identified
        if not resources:
            resources = ["Operations team", "Project management"]

        return resources

    def _define_success_metrics(self, action_text: str) -> List[str]:
        """Define success metrics for action"""

        metrics = []

        # Generic success metrics based on action type
        text_lower = action_text.lower()

        if 'monitoring' in text_lower or 'tracking' in text_lower:
            metrics.append("Increased monitoring coverage")
            metrics.append("Early detection rate")
        elif 'development' in text_lower or 'build' in text_lower:
            metrics.append("Successful implementation")
            metrics.append("Performance metrics met")
        elif 'partnership' in text_lower:
            metrics.append("Partnership established")
            metrics.append("Joint value creation")
        elif 'research' in text_lower:
            metrics.append("Insights generated")
            metrics.append("Knowledge base expansion")

        # Default metrics
        if not metrics:
            metrics = ["Action completed successfully",
                "Positive impact measured"]

        return metrics

    def _generate_operations_recommendations(self, daily_report:
                                             Dict[str, Any]) ->Dict[str, Any]:
        """Generate operational recommendations from council intelligence"""

        recommendations = {
            "immediate_actions": [],
            "resource_allocations": [],
            "monitoring_adjustments": [],
            "risk_mitigations": []
        }

        # Process policy recommendations
        policy_recs = daily_report.get("policy_recommendations", [])
        for rec in policy_recs[:3]:  # Top 3
            if 'resource' in rec.lower():
                recommendations["resource_allocations"].append(rec)
            elif 'monitoring' in rec.lower():
                recommendations["monitoring_adjustments"].append(rec)
            else:
                recommendations["immediate_actions"].append(rec)

        # Process risk alerts
        risk_alerts = daily_report.get("risk_alerts", [])
        recommendations["risk_mitigations"] = risk_alerts[:3]

        return recommendations

    def _requires_council_review(self, daily_report: Dict[str, Any]) -> bool:
        """Determine if council review is required"""

        # Require review for high-impact insights
        indicators = [
            daily_report.get("new_content_analyzed", 0) > 20,  # High volume
            len(daily_report.get("risk_alerts", [])
                ) > 5,      # Multiple risk alerts
            any('critical' in alert.lower()
                # Critical alerts
                for alert in daily_report.get("risk_alerts", [])),
            any('urgent' in action.lower() for action in daily_report.get(
                "strategic_actions", []))  # Urgent actions
        ]

        return any(indicators)

    def _save_proposal(self, proposal: Dict[str, Any]):
        """Save proposal for council review"""

        proposal_file = self.decisions_dir / f"{proposal['id']}.json"

        with open(proposal_file, 'w') as f:
            json.dump(proposal, f, indent=2)

        logger.info(f"Saved council intelligence proposal: {proposal['id']}")

    def get_pending_proposals(self) -> List[Dict[str, Any]]:
        """Get pending council intelligence proposals"""

        proposals = []

        if not self.decisions_dir.exists():
            return proposals

        for proposal_file in self.decisions_dir.glob("council_intel_*.json"):
            try:
                with open(proposal_file, 'r') as f:
                    proposal = json.load(f)
                    proposals.append(proposal)
            except Exception as e:
                logger.error(f"Error loading proposal {proposal_file}: {e}")

        # Sort by timestamp (most recent first)
        proposals.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return proposals

    def update_daily_report(self, daily_report: Dict[str, Any]):
        """Update daily operations report with council intelligence"""

        report_date = daily_report.get(
            "date", datetime.now().date().isoformat())
        report_file = self.reports_dir / f"council_intel_{report_date}.md"

        report_content = f"""# Inner Council Intelligence Report - {report_date}

## Executive Summary
- **Council Members Monitored**: {daily_report.get('council_members_monitored', 0)}
- **New Content Analyzed**: {daily_report.get('new_content_analyzed', 0)}
- **Key Insights Generated**: {len(daily_report.get('key_insights', []))}
- **Policy Recommendations**: {len(daily_report.get('policy_recommendations', []))}

## Key Insights
{chr(10).join(f"- {insight}" for insight in daily_report.get('key_insights', [])[:10])}

## Policy Recommendations
{chr(10).join(f"- {rec}" for rec in daily_report.get('policy_recommendations', [])[:10])}

## Strategic Actions
{chr(10).join(f"- {action}" for action in daily_report.get('strategic_actions', [])[:10])}

## Risk Alerts
{chr(10).join(f"- {alert}" for alert in daily_report.get('risk_alerts', [])[:10])}

---
*Generated by Inner Council - {datetime.now().isoformat()}*
"""

        with open(report_file, 'w') as f:
            f.write(report_content)

        logger.info(
            f"Updated daily report with council intelligence: {report_file}")

    def get_action_status(self) -> Dict[str, Any]:
        """Get status of council-driven actions"""

        pending_proposals = self.get_pending_proposals()

        status = {
            "pending_proposals": len(pending_proposals),
            "recent_proposals": [p.get("id") for p in pending_proposals[:5]],
            "requires_review": len([p for p in pending_proposals if self._requires_council_review(p.get("data", {}))]),
            "last_update": datetime.now().isoformat()
        }

        return status