#!/usr/bin/env python3
"""
Executive Decision Matrix
Phase 2: Decision Framework with Authority Boundaries

Maps executive decision matrix to autonomy levels and implements
decision approval workflows with executive consultation processes.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum

from ceo_command_authority import DecisionAuthority, DecisionCategory, ceo_authority
from oversight_framework import oversight

class AutonomyLevel(Enum):
    """Autonomy levels for decision delegation"""
    FULL_AUTONOMOUS = "full_autonomous"  # No executive oversight required
    ROUTINE_EXECUTIVE = "routine_executive"  # Executive team routine approval
    SENIOR_EXECUTIVE = "senior_executive"  # Senior executive consultation
    CEO_CONSULTATION = "ceo_consultation"  # CEO consultation required
    CEO_APPROVAL = "ceo_approval"  # CEO approval required
    EXECUTIVE_OVERRIDE = "executive_override"  # CEO emergency override

class DecisionMatrix:
    """
    Executive Decision Matrix
    Maps decisions to appropriate authority levels based on impact and category
    """

    def __init__(self, config_path: str = "decision_matrix_config.json"):
        """Initialize."""
        self.config_path = config_path
        self.matrix = self._load_decision_matrix()
        self.authority_mappings = self._load_authority_mappings()
        self.escalation_rules = self._load_escalation_rules()

    def _load_decision_matrix(self) -> Dict[str, Dict[str, AutonomyLevel]]:
        """Load the comprehensive decision matrix"""
        return {
            # Strategic Decisions
            "strategic": {
                "mission_definition": AutonomyLevel.CEO_APPROVAL,
                "major_partnerships": AutonomyLevel.CEO_APPROVAL,
                "market_expansion": AutonomyLevel.CEO_CONSULTATION,
                "brand_strategy": AutonomyLevel.SENIOR_EXECUTIVE,
                "organizational_change": AutonomyLevel.CEO_CONSULTATION
            },

            # Financial Decisions
            "financial": {
                "budget_over_1m": AutonomyLevel.CEO_APPROVAL,
                "budget_500k_1m": AutonomyLevel.CEO_CONSULTATION,
                "budget_100k_500k": AutonomyLevel.SENIOR_EXECUTIVE,
                "budget_under_100k": AutonomyLevel.ROUTINE_EXECUTIVE,
                "investment_opportunities": AutonomyLevel.CEO_APPROVAL,
                "cost_reductions": AutonomyLevel.SENIOR_EXECUTIVE
            },

            # Operational Decisions
            "operational": {
                "process_changes": AutonomyLevel.ROUTINE_EXECUTIVE,
                "resource_allocation": AutonomyLevel.SENIOR_EXECUTIVE,
                "vendor_selection": AutonomyLevel.ROUTINE_EXECUTIVE,
                "facility_changes": AutonomyLevel.CEO_CONSULTATION,
                "personnel_changes": AutonomyLevel.SENIOR_EXECUTIVE
            },

            # Technical Decisions
            "technical": {
                "architecture_changes": AutonomyLevel.CEO_CONSULTATION,
                "major_upgrades": AutonomyLevel.SENIOR_EXECUTIVE,
                "security_changes": AutonomyLevel.CEO_APPROVAL,
                "infrastructure_scaling": AutonomyLevel.ROUTINE_EXECUTIVE,
                "tool_adoption": AutonomyLevel.ROUTINE_EXECUTIVE
            },

            # Intelligence Decisions
            "intelligence": {
                "source_acquisition": AutonomyLevel.CEO_CONSULTATION,
                "analysis_methodology": AutonomyLevel.SENIOR_EXECUTIVE,
                "data_privacy": AutonomyLevel.CEO_APPROVAL,
                "intelligence_sharing": AutonomyLevel.CEO_CONSULTATION,
                "council_operations": AutonomyLevel.ROUTINE_EXECUTIVE
            },

            # Crisis Decisions
            "crisis": {
                "emergency_response": AutonomyLevel.EXECUTIVE_OVERRIDE,
                "system_failure": AutonomyLevel.CEO_APPROVAL,
                "security_breach": AutonomyLevel.EXECUTIVE_OVERRIDE,
                "reputation_threat": AutonomyLevel.CEO_APPROVAL,
                "operational_disruption": AutonomyLevel.CEO_CONSULTATION
            }
        }

    def _load_authority_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Load authority level mappings to executive roles"""
        return {
            "full_autonomous": {
                "authority": "NCC Autonomous",
                "approvers": ["NCC_SYSTEM"],
                "timeline": "immediate",
                "consultation_required": False
            },
            "routine_executive": {
                "authority": "Executive Team",
                "approvers": ["COO", "CTO", "CFO", "CIO"],
                "timeline": "24_hours",
                "consultation_required": False
            },
            "senior_executive": {
                "authority": "Senior Executive",
                "approvers": ["CEO", "COO", "CTO", "CFO", "CIO"],
                "timeline": "48_hours",
                "consultation_required": True
            },
            "ceo_consultation": {
                "authority": "CEO Consultation",
                "approvers": ["CEO"],
                "timeline": "72_hours",
                "consultation_required": True
            },
            "ceo_approval": {
                "authority": "CEO Approval",
                "approvers": ["CEO"],
                "timeline": "decision_based",
                "consultation_required": True
            },
            "executive_override": {
                "authority": "EXECUTIVE_OVERRIDE",
                "approvers": ["CEO"],
                "timeline": "immediate",
                "consultation_required": False
            }
        }

    def _load_escalation_rules(self) -> Dict[str, List[str]]:
        """Load decision escalation rules"""
        return {
            "ethical_concerns": ["escalate_to_ceo", "require_ethics_review"],
            "financial_risk": ["escalate_to_cfo", "require_risk_assessment"],
            "reputational_risk": ["escalate_to_ceo", "require_pr_review"],
            "operational_impact": ["escalate_to_coo", "require_impact_analysis"],
            "technical_risk": ["escalate_to_cto", "require_security_review"],
            "intelligence_sensitivity": ["escalate_to_cio", "require_privacy_review"]
        }

    def evaluate_decision(self, category: str, decision_type: str,
                         impact_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a decision against the matrix

        Args:
            category: Decision category
            decision_type: Specific decision type
            impact_assessment: Impact assessment data

        Returns:
            Decision evaluation result
        """
        # Get base autonomy level
        base_level = self._get_base_autonomy_level(category, decision_type)

        # Apply escalation rules
        escalated_level = self._apply_escalation_rules(
            base_level, impact_assessment)

        # Get authority requirements
        authority_info = self.authority_mappings.get(escalated_level.value, {})

        return {
            "category": category,
            "decision_type": decision_type,
            "base_autonomy": base_level.value,
            "final_autonomy": escalated_level.value,
            "escalated": base_level != escalated_level,
            "authority_required": authority_info.get("authority", "Unknown"),
            "approvers": authority_info.get("approvers", []),
            "timeline": authority_info.get("timeline", "unknown"),
            "consultation_required": authority_info.get("consultation_required", False),
            "impact_assessment": impact_assessment
        }

    def _get_base_autonomy_level(
            self, category: str, decision_type: str) ->AutonomyLevel:
        """Get base autonomy level from matrix"""
        if category in self.matrix and decision_type in self.matrix[category]:
            return self.matrix[category][decision_type]

        # Default to CEO consultation for unknown decisions
        return AutonomyLevel.CEO_CONSULTATION

    def _apply_escalation_rules(
            self, base_level: AutonomyLevel, impact_assessment: Dict
            [str, Any]) ->AutonomyLevel:
        """Apply escalation rules based on impact assessment"""
        escalated_level = base_level

        # Check escalation triggers
        for trigger, rules in self.escalation_rules.items():
            if self._check_escalation_trigger(trigger, impact_assessment):
                for rule in rules:
                    if rule == "escalate_to_ceo":
                        escalated_level = max(
                            escalated_level, AutonomyLevel.CEO_APPROVAL)
                    elif rule == "escalate_to_cfo" and base_level.value in ["routine_executive", "senior_executive"]:
                        escalated_level = max(
                            escalated_level, AutonomyLevel.SENIOR_EXECUTIVE)

        # Crisis situations always escalate to override level
        if impact_assessment.get("crisis_level", "none") != "none":
            escalated_level = AutonomyLevel.EXECUTIVE_OVERRIDE

        return escalated_level

    def _check_escalation_trigger(
            self, trigger: str, impact_assessment: Dict[str, Any]) ->bool:
        """Check if an escalation trigger is met"""
        if trigger == "ethical_concerns":
            return impact_assessment.get("ethical_score", 1.0) < 0.8

        elif trigger == "financial_risk":
            return impact_assessment.get("financial_impact", 0) > 500000

        elif trigger == "reputational_risk":
            return impact_assessment.get("reputational_impact", "low") in ["high", "critical"]

        elif trigger == "operational_impact":
            return impact_assessment.get("operational_impact", "low") in ["high", "critical"]

        elif trigger == "technical_risk":
            return impact_assessment.get("technical_risk", "low") in ["high", "critical"]

        elif trigger == "intelligence_sensitivity":
            return impact_assessment.get("sensitivity_level", "low") in ["high", "critical"]

        return False

    def route_decision(self, category: str, decision_type: str, title: str,
                      description: str, impact_assessment: Dict[str, Any],
                      proposed_by: str) -> Dict[str, Any]:
        """
        Route a decision through the approval matrix

        Returns:
            Routing result with decision ID and status
        """
        # Evaluate decision
        evaluation = self.evaluate_decision(
            category, decision_type, impact_assessment)

        # Prepare decision data for CEO authority
        ethical_assessment = impact_assessment.get("ethical_assessment", {})
        risk_assessment = impact_assessment.get("risk_assessment", {})
        timeline = evaluation.get("timeline", "72_hours")
        financial_impact = impact_assessment.get("financial_impact", 0)

        # Convert autonomy level to DecisionAuthority
        authority_mapping = {
            "full_autonomous": DecisionAuthority.NCC_AUTONOMOUS,
            "routine_executive": DecisionAuthority.EXECUTIVE_ROUTINE,
            "senior_executive": DecisionAuthority.CEO_CONSULTATION,
            "ceo_consultation": DecisionAuthority.CEO_CONSULTATION,
            "ceo_approval": DecisionAuthority.CEO_APPROVAL,
            "executive_override": DecisionAuthority.EXECUTIVE_OVERRIDE
        }

        authority_required = authority_mapping.get(
            evaluation["final_autonomy"], DecisionAuthority.CEO_CONSULTATION)

        # Submit to CEO authority framework
        decision_id = ceo_authority.submit_executive_decision(
            category=category,
            title=title,
            description=description,
            impact_level=impact_assessment.get("impact_level", "medium"),
            authority_required=authority_required,
            proposed_by=proposed_by,
            ethical_assessment=ethical_assessment,
            risk_assessment=risk_assessment,
            timeline=timeline,
            financial_impact=financial_impact
        )

        return {
            "decision_id": decision_id,
            "evaluation": evaluation,
            "routing_status": "submitted",
            "next_steps": self._get_next_steps(evaluation)
        }

    def _get_next_steps(self, evaluation: Dict[str, Any]) -> List[str]:
        """Get next steps for decision routing"""
        next_steps = []

        if evaluation["final_autonomy"] == "full_autonomous":
            next_steps.append(
                "Decision auto-approved - proceeding with execution")
        elif evaluation["final_autonomy"] == "executive_override":
            next_steps.append(
                "EXECUTIVE_OVERRIDE required - immediate CEO declaration needed")
        else:
            approvers = evaluation.get("approvers", [])
            next_steps.append(f"Decision routed to: {', '.join(approvers)}")
            next_steps.append(
                f"Timeline: {evaluation.get('timeline', 'unknown')}")

        if evaluation.get("consultation_required"):
            next_steps.append(
                "Consultation session required before final approval")

        return next_steps

# Global decision matrix instance
decision_matrix = DecisionMatrix()

# Convenience functions
def evaluate_decision_matrix(category: str, decision_type: str,
                           impact_assessment: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for decision evaluation"""
    return decision_matrix.evaluate_decision(
        category, decision_type, impact_assessment)

def route_executive_decision(category: str, decision_type: str, title: str,
                           description: str, impact_assessment: Dict[str, Any],
                           proposed_by: str) -> Dict[str, Any]:
    """Convenience function for decision routing"""
    return decision_matrix.route_decision(
        category, decision_type, title, description, impact_assessment,
        proposed_by)
