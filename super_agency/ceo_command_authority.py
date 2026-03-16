#!/usr/bin/env python3
"""
CEO Command Authority Framework
Phase 2: CEO Authority + Decision Framework Integration

Implements CEO supreme command authority with EXECUTIVE_OVERRIDE protocols,
decision routing system with authority boundaries, and executive command matrix.
"""

import json
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from enum import Enum
from dataclasses import dataclass, asdict
import hashlib

from oversight_framework import oversight

class DecisionAuthority(Enum):
    """Decision authority levels"""
    NCC_AUTONOMOUS = "ncc_autonomous"  # NCC handles autonomously
    EXECUTIVE_ROUTINE = "executive_routine"  # Executive team routine decisions
    CEO_CONSULTATION = "ceo_consultation"  # Requires CEO consultation
    CEO_APPROVAL = "ceo_approval"  # Requires CEO approval
    EXECUTIVE_OVERRIDE = "executive_override"  # CEO emergency override

class DecisionCategory(Enum):
    """Decision categories for routing"""
    STRATEGIC = "strategic"  # Mission, vision, partnerships
    FINANCIAL = "financial"  # Budget, resources, investments
    OPERATIONAL = "operational"  # Day-to-day operations
    TECHNICAL = "technical"  # Technology, architecture
    INTELLIGENCE = "intelligence"  # Intelligence operations
    CRISIS = "crisis"  # Emergency situations

@dataclass
class ExecutiveDecision:
    """Executive decision structure"""
    decision_id: str
    category: DecisionCategory
    title: str
    description: str
    impact_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    authority_required: DecisionAuthority
    proposed_by: str
    ethical_assessment: Dict[str, float]
    risk_assessment: Dict[str, Any]
    timeline: str
    status: str = "pending"
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    executed_at: Optional[str] = None
    outcome: Optional[str] = None

@dataclass
class ExecutiveOverride:
    """EXECUTIVE_OVERRIDE protocol structure"""
    override_id: str
    reason: str
    declared_by: str
    declared_at: str
    affected_systems: List[str]
    override_duration: int  # hours
    status: str = "active"
    deactivated_at: Optional[str] = None
    deactivation_reason: Optional[str] = None

class CEOCommandAuthority:
    """
    CEO Command Authority Framework
    Implements supreme executive command with EXECUTIVE_OVERRIDE protocols
    """

    def __init__(self, config_path: str = "ceo_authority_config.json"):
        """Initialize CEO Command Authority."""
        self.config_path = config_path
        self.config = self._load_config()
        self._setup_logging()

        # Decision routing matrix
        self.decision_matrix = self._load_decision_matrix()

        # Active decisions and overrides
        self.active_decisions: Dict[str, ExecutiveDecision] = {}
        self.active_overrides: Dict[str, ExecutiveOverride] = {}

        # Executive team authority boundaries
        self.executive_boundaries = self._load_executive_boundaries()

        # Override safeguards
        self.override_safeguards = self._load_override_safeguards()

    def _load_config(self) -> Dict[str, Any]:
        """Load CEO authority configuration"""
        default_config = {
            "ceo_authority": {
                "enabled": True,
                "decision_timeout_hours": {
                    "routine": 24,
                    "important": 72,
                    "critical": 24,
                    "crisis": 1
                },
                "override_protocols": {
                    "max_duration_hours": 24,
                    "requires_cio_acknowledgment": True,
                    "requires_executive_notification": True,
                    "auto_deactivation_enabled": True
                },
                "decision_categories": {
                    "strategic_threshold": 1000000,  # $1M threshold for CEO approval
                    "operational_threshold": 100000,  # $100K threshold for executive approval
                    "intelligence_sensitivity": ["HIGH", "CRITICAL"]
                }
            },
            "executive_team": {
                "ceo": "CEO",
                "cio": "CIO",
                "cto": "CTO",
                "cfo": "CFO",
                "coo": "COO"
            }
        }

        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                user_config = json.load(f)
                self._deep_update(default_config, user_config)

        return default_config

    def _deep_update(self, base_dict: Dict, update_dict: Dict):
        """Deep update dictionary"""
        for key, value in update_dict.items():
            if isinstance(value, dict) and key in base_dict:
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def _setup_logging(self):
        """Setup CEO authority logging"""
        os.makedirs("logs/ceo_authority", exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - CEO-Authority - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/ceo_authority/ceo_authority.log'),
                logging.StreamHandler()
            ]
        )

        self.logger = logging.getLogger("CEO-Authority")

    def _load_decision_matrix(self) -> Dict[str, Dict[str, DecisionAuthority]]:
        """Load executive decision routing matrix"""
        return {
            "strategic": {
                "low_impact": DecisionAuthority.EXECUTIVE_ROUTINE,
                "medium_impact": DecisionAuthority.CEO_CONSULTATION,
                "high_impact": DecisionAuthority.CEO_APPROVAL,
                "critical_impact": DecisionAuthority.CEO_APPROVAL
            },
            "financial": {
                "low_impact": DecisionAuthority.EXECUTIVE_ROUTINE,
                "medium_impact": DecisionAuthority.CEO_CONSULTATION,
                "high_impact": DecisionAuthority.CEO_APPROVAL,
                "critical_impact": DecisionAuthority.CEO_APPROVAL
            },
            "operational": {
                "low_impact": DecisionAuthority.NCC_AUTONOMOUS,
                "medium_impact": DecisionAuthority.EXECUTIVE_ROUTINE,
                "high_impact": DecisionAuthority.CEO_CONSULTATION,
                "critical_impact": DecisionAuthority.CEO_APPROVAL
            },
            "technical": {
                "low_impact": DecisionAuthority.EXECUTIVE_ROUTINE,
                "medium_impact": DecisionAuthority.CEO_CONSULTATION,
                "high_impact": DecisionAuthority.CEO_APPROVAL,
                "critical_impact": DecisionAuthority.CEO_APPROVAL
            },
            "intelligence": {
                "low_impact": DecisionAuthority.EXECUTIVE_ROUTINE,
                "medium_impact": DecisionAuthority.CEO_CONSULTATION,
                "high_impact": DecisionAuthority.CEO_APPROVAL,
                "critical_impact": DecisionAuthority.CEO_APPROVAL
            },
            "crisis": {
                "low_impact": DecisionAuthority.CEO_APPROVAL,
                "medium_impact": DecisionAuthority.CEO_APPROVAL,
                "high_impact": DecisionAuthority.EXECUTIVE_OVERRIDE,
                "critical_impact": DecisionAuthority.EXECUTIVE_OVERRIDE
            }
        }

    def _load_executive_boundaries(self) -> Dict[str, Dict[str, Any]]:
        """Load executive authority boundaries"""
        return {
            "CEO": {
                "decision_limit": float('inf'),
                "approval_categories": ["all"],
                "override_authority": True,
                "strategic_veto": True
            },
            "CIO": {
                "decision_limit": 500000,
                "approval_categories": ["intelligence", "technical"],
                "override_authority": False,
                "strategic_veto": False
            },
            "CTO": {
                "decision_limit": 750000,
                "approval_categories": ["technical", "operational"],
                "override_authority": False,
                "strategic_veto": False
            },
            "CFO": {
                "decision_limit": 1000000,
                "approval_categories": ["financial", "operational"],
                "override_authority": False,
                "strategic_veto": False
            },
            "COO": {
                "decision_limit": 500000,
                "approval_categories": ["operational", "strategic"],
                "override_authority": False,
                "strategic_veto": False
            }
        }

    def _load_override_safeguards(self) -> Dict[str, Any]:
        """Load EXECUTIVE_OVERRIDE safeguards"""
        return {
            "max_duration_hours": 24,
            "requires_multiple_acknowledgments": True,
            "auto_audit_enabled": True,
            "post_override_review_required": True,
            "safeguard_checks": [
                "ethical_compliance_check",
                "council_52_status_check",
                "system_integrity_check",
                "executive_notification_check"
            ]
        }

    def evaluate_decision_authority(
            self, category: str, impact_level: str, proposed_by: str,
            financial_impact: float=0) ->DecisionAuthority:
        """
        Evaluate which authority level is required for a decision

        Args:
            category: Decision category (strategic, financial, etc.)
            impact_level: Impact level (low, medium, high, critical)
            proposed_by: Who is proposing the decision
            financial_impact: Financial impact in dollars

        Returns:
            Required decision authority level
        """
        # Check financial thresholds
        if financial_impact >=self.config["ceo_authority"] [
            "decision_categories"] ["strategic_threshold"]:
            return DecisionAuthority.CEO_APPROVAL

        if financial_impact >=self.config["ceo_authority"] [
            "decision_categories"] ["operational_threshold"]:
            if category in ["strategic", "financial"]:
                return DecisionAuthority.CEO_CONSULTATION

        # Check decision matrix
        if category in self.decision_matrix and impact_level in self.decision_matrix[category]:
            required_authority = self.decision_matrix[category][impact_level]

            # Check if proposer has authority
            if proposed_by in self.executive_boundaries:
                boundaries = self.executive_boundaries[proposed_by]

                # Check financial limits
                if financial_impact > boundaries["decision_limit"]:
                    return DecisionAuthority.CEO_APPROVAL

                # Check category permissions
                if required_authority == DecisionAuthority.EXECUTIVE_ROUTINE:
                    if category not in boundaries["approval_categories"] and "all" not in boundaries["approval_categories"]:
                        return DecisionAuthority.CEO_CONSULTATION

            return required_authority

        # Default to CEO approval for unknown cases
        return DecisionAuthority.CEO_APPROVAL

    def submit_executive_decision(
            self, category: str, title: str, description: str, impact_level:
            str, proposed_by: str, ethical_assessment: Dict[str, float],
            risk_assessment: Dict[str, Any],
            timeline: str, financial_impact: float=0,
            authority_required: DecisionAuthority=None) ->str:
        """
        Submit a decision for executive routing

        Returns:
            Decision ID for tracking
        """
        # Generate decision ID
        decision_id = hashlib.sha256(
            f"{proposed_by}_{title}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        # Evaluate required authority (use provided or calculate)
        if authority_required is None:
            authority_required = self.evaluate_decision_authority(
                category, impact_level, proposed_by, financial_impact
            )

        # Create decision object
        decision = ExecutiveDecision(
            decision_id=decision_id,
            category=DecisionCategory(category),
            title=title,
            description=description,
            impact_level=impact_level,
            authority_required=authority_required,
            proposed_by=proposed_by,
            ethical_assessment=ethical_assessment,
            risk_assessment=risk_assessment,
            timeline=timeline
        )

        # Store decision
        self.active_decisions[decision_id] = decision

        # Audit the decision submission
        oversight.audit_executive_decision(
            proposed_by, f"decision_submission_{category}",
            ethical_assessment, impact_level
        )

        # Route decision based on authority
        if authority_required == DecisionAuthority.NCC_AUTONOMOUS:
            self._auto_approve_decision(decision_id)
        elif authority_required == DecisionAuthority.EXECUTIVE_ROUTINE:
            self._route_to_executive_team(decision_id)
        elif authority_required == DecisionAuthority.CEO_CONSULTATION:
            self._route_to_ceo_consultation(decision_id)
        elif authority_required == DecisionAuthority.CEO_APPROVAL:
            self._route_to_ceo_approval(decision_id)

        self.logger.info(
            f"Decision submitted: {decision_id} - {title} - Authority: {authority_required.value}")

        return decision_id

    def declare_executive_override(
            self, reason: str, declared_by: str, affected_systems: List[str],
            duration_hours: int) ->str:
        """
        Declare EXECUTIVE_OVERRIDE protocol

        Args:
            reason: Reason for override
            declared_by: Who is declaring the override
            affected_systems: Systems affected by override
            duration_hours: Duration of override

        Returns:
            Override ID
        """
        # Validate override authority
        if declared_by != self.config["executive_team"]["ceo"]:
            raise ValueError("Only CEO can declare EXECUTIVE_OVERRIDE")

        # Check safeguards
        if not self._check_override_safeguards():
            raise ValueError("Override safeguards not satisfied")

        # Generate override ID
        override_id = hashlib.sha256(
            f"EXECUTIVE_OVERRIDE_{declared_by}_{datetime.now().isoformat()}".encode(
            )
        ).hexdigest()[:16]

        # Create override object
        override = ExecutiveOverride(
            override_id=override_id,
            reason=reason,
            declared_by=declared_by,
            declared_at=datetime.now().isoformat(),
            affected_systems=affected_systems,
            override_duration=duration_hours
        )

        # Store override
        self.active_overrides[override_id] = override

        # Activate override protocols
        self._activate_override_protocols(override)

        # Notify executive team
        self._notify_executive_override(override)

        self.logger.critical(
            f"EXECUTIVE_OVERRIDE declared: {override_id} - {reason}")

        return override_id

    def _check_override_safeguards(self) -> bool:
        """Check if override safeguards are satisfied"""
        # Implement safeguard checks
        checks_passed = True

        for check in self.override_safeguards["safeguard_checks"]:
            if check == "ethical_compliance_check":
                # Check recent ethical violations
                report = oversight.get_executive_ethics_report(7)
                if report["ethical_compliance_rate"] < 0.8:
                    self.logger.warning(
                        "Override blocked: Low ethical compliance rate")
                    checks_passed = False

            elif check == "council_52_status_check":
                # Check Council 52 operational status
                # This would integrate with Council 52 health checks
                pass

            elif check == "system_integrity_check":
                # Check system integrity
                # This would check NCC system health
                pass

        return checks_passed

    def _activate_override_protocols(self, override: ExecutiveOverride):
        """Activate override protocols across systems"""
        # NCC manual command mode
        # Council 52 suspension of autonomous operations
        # Executive notification system activation

        self.logger.critical(
            f"Override protocols activated for systems: {override.affected_systems}")

    def _notify_executive_override(self, override: ExecutiveOverride):
        """Notify executive team of override"""
        notification = {
            "type": "EXECUTIVE_OVERRIDE",
            "override_id": override.override_id,
            "reason": override.reason,
            "declared_by": override.declared_by,
            "affected_systems": override.affected_systems,
            "timestamp": override.declared_at
        }

        # Send to executive notification system
        self.logger.critical(
            f"Executive override notification sent: {notification}")

    def approve_decision(self, decision_id: str, approved_by: str) -> bool:
        """Approve an executive decision"""
        if decision_id not in self.active_decisions:
            return False

        decision = self.active_decisions[decision_id]

        # Validate approval authority
        if not self._validate_approval_authority(decision, approved_by):
            return False

        # Update decision
        decision.status = "approved"
        decision.approved_by = approved_by
        decision.approved_at = datetime.now().isoformat()

        # Execute decision
        self._execute_decision(decision_id)

        self.logger.info(f"Decision approved: {decision_id} by {approved_by}")

        return True

    def _validate_approval_authority(
            self, decision: ExecutiveDecision, approved_by: str) ->bool:
        """Validate that approver has authority for this decision"""
        if decision.authority_required == DecisionAuthority.CEO_APPROVAL:
            return approved_by == self.config["executive_team"]["ceo"]

        elif decision.authority_required == DecisionAuthority.CEO_CONSULTATION:
            return approved_by in self.executive_boundaries

        elif decision.authority_required == DecisionAuthority.EXECUTIVE_ROUTINE:
            return approved_by in self.executive_boundaries

        return False

    def _auto_approve_decision(self, decision_id: str):
        """Auto-approve NCC autonomous decisions"""
        if decision_id in self.active_decisions:
            decision = self.active_decisions[decision_id]
            decision.status = "auto_approved"
            decision.approved_by = "NCC_AUTONOMOUS"
            decision.approved_at = datetime.now().isoformat()
            self._execute_decision(decision_id)

    def _route_to_executive_team(self, decision_id: str):
        """Route to executive team for routine approval"""
        # Implementation for executive team routing
        pass

    def _route_to_ceo_consultation(self, decision_id: str):
        """Route to CEO for consultation"""
        # Implementation for CEO consultation routing
        pass

    def _route_to_ceo_approval(self, decision_id: str):
        """Route to CEO for approval"""
        # Implementation for CEO approval routing
        pass

    def _execute_decision(self, decision_id: str):
        """Execute an approved decision"""
        if decision_id in self.active_decisions:
            decision = self.active_decisions[decision_id]
            decision.executed_at = datetime.now().isoformat()
            decision.status = "executed"

            self.logger.info(f"Decision executed: {decision_id}")

    def get_executive_dashboard(self) -> Dict[str, Any]:
        """Get CEO executive dashboard"""
        return {
            "active_decisions": len([d for d in self.active_decisions.values() if d.status == "pending"]),
            "approved_today": len([d for d in self.active_decisions.values()
                                 if d.approved_at and d.approved_at.startswith(datetime.now().strftime("%Y-%m-%d"))]),
            "active_overrides": len(self.active_overrides),
            "pending_approvals": [asdict(d) for d in self.active_decisions.values()
                                if d.status == "pending" and d.authority_required in
                                [DecisionAuthority.CEO_APPROVAL, DecisionAuthority.CEO_CONSULTATION]],
            "system_status": "normal" if not self.active_overrides else "override_active"
        }

    def deactivate_override(self, override_id: str, reason: str):
        """Deactivate an EXECUTIVE_OVERRIDE"""
        if override_id in self.active_overrides:
            override = self.active_overrides[override_id]
            override.status = "deactivated"
            override.deactivated_at = datetime.now().isoformat()
            override.deactivation_reason = reason

            # Restore normal operations
            self._restore_normal_operations(override)

            self.logger.critical(
                f"EXECUTIVE_OVERRIDE deactivated: {override_id} - {reason}")

    def _restore_normal_operations(self, override: ExecutiveOverride):
        """Restore normal system operations after override"""
        # Restore NCC autonomous operations
        # Restore Council 52 normal operations
        # Log override completion

        self.logger.info(
            f"Normal operations restored after override: {override.override_id}")

# Global CEO authority instance
ceo_authority = CEOCommandAuthority()

# Convenience functions
def submit_decision(
        category: str, title: str, description: str, impact_level: str,
        proposed_by: str, ethical_assessment: Dict[str, float],
        risk_assessment: Dict[str, Any],
        timeline: str, financial_impact: float=0) ->str:
    """Convenience function for decision submission"""
    return ceo_authority.submit_executive_decision(
        category, title, description, impact_level, proposed_by,
        ethical_assessment, risk_assessment, timeline, financial_impact
    )

def declare_override(
        reason: str, declared_by: str, affected_systems: List[str],
        duration_hours: int) ->str:
    """Convenience function for EXECUTIVE_OVERRIDE declaration"""
    return ceo_authority.declare_executive_override(
        reason, declared_by, affected_systems, duration_hours)

def approve_decision(decision_id: str, approved_by: str) -> bool:
    """Convenience function for decision approval"""
    return ceo_authority.approve_decision(decision_id, approved_by)

def get_ceo_dashboard() -> Dict[str, Any]:
    """Convenience function for CEO dashboard"""
    return ceo_authority.get_executive_dashboard()