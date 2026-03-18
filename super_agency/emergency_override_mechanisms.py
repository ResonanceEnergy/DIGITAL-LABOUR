"""
Emergency Override Mechanisms
Phase 3: Crisis Management Protocols + Executive Briefings
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json
import logging
from pathlib import Path

from crisis_management_framework import CrisisManagementFramework
from executive_briefings_system import ExecutiveBriefingsSystem
from ceo_command_authority import CEOCommandAuthority, DecisionAuthority
from executive_decision_matrix import DecisionMatrix
from oversight_framework import OversightFramework

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OverrideType(Enum):
    """Types of emergency overrides"""
    SYSTEM_SHUTDOWN = "system_shutdown"
    RESOURCE_REALLOCATION = "resource_reallocation"
    DECISION_BYPASS = "decision_bypass"
    COMMUNICATION_LOCKDOWN = "communication_lockdown"
    DATA_PURGE = "data_purge"
    EMERGENCY_MODE = "emergency_mode"


class OverrideSeverity(Enum):
    """Override severity levels"""
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"
    EXISTENTIAL = "existential"


@dataclass
class EmergencyOverride:
    """Emergency override instance"""
    override_id: str
    override_type: OverrideType
    severity: OverrideSeverity
    reason: str
    justification: str
    declared_by: str
    affected_systems: List[str]
    override_actions: List[str]
    safeguards_bypassed: List[str]
    declared_at: str
    expires_at: str
    status: str = "active"
    executed_actions: List[str] = None
    deactivated_at: Optional[str] = None
    deactivation_reason: Optional[str] = None

    def __post_init__(self):
        """Initialize."""
        if self.executed_actions is None:
            self.executed_actions = []


@dataclass
class OverrideSafeguard:
    """Override safeguard mechanism"""
    safeguard_id: str
    name: str
    description: str
    bypass_allowed: bool
    bypass_conditions: List[str]
    monitoring_required: bool
    ethical_review_required: bool


class EmergencyOverrideMechanisms:
    """
    Emergency Override Mechanisms for BIT RAGE LABOUR
    Provides controlled emergency override capabilities with safeguards
    """


    def __init__(self):
        """__init__ handler."""
        self.crisis_framework = CrisisManagementFramework()
        self.briefings_system = ExecutiveBriefingsSystem()
        self.ceo_authority = CEOCommandAuthority()
        self.decision_matrix = DecisionMatrix()
        self.oversight = OversightFramework()

        # Override state
        self.active_overrides: Dict[str, EmergencyOverride] = {}
        self.override_history: List[EmergencyOverride] = []

        # Safeguards and protocols
        self.safeguards = self._load_safeguards()
        self.override_protocols = self._load_override_protocols()
        self.emergency_procedures = self._load_emergency_procedures()

        logger.info("Emergency Override Mechanisms initialized")

    def _load_safeguards(self) -> Dict[str, OverrideSafeguard]:
        """Load override safeguard mechanisms"""
        return {
            "ethical_compliance": OverrideSafeguard(
                safeguard_id="ethical_compliance",
                name="Ethical Compliance Check",
                description="Verify override aligns with ethical guidelines",
                bypass_allowed=False,
                bypass_conditions=[],
                monitoring_required=True,
                ethical_review_required=True
            ),
            "authority_verification": OverrideSafeguard(
                safeguard_id="authority_verification",
                name="Authority Verification",
                description="Verify declaring authority has proper clearance",
                bypass_allowed=False,
                bypass_conditions=[],
                monitoring_required=True,
                ethical_review_required=False
            ),
            "impact_assessment": OverrideSafeguard(
                safeguard_id="impact_assessment",
                name="Impact Assessment",
                description="Assess potential impact of override actions",
                bypass_allowed=True,
                bypass_conditions=["existential_crisis", "imminent_threat"],
                monitoring_required=True,
                ethical_review_required=True
            ),
            "rollback_capability": OverrideSafeguard(
                safeguard_id="rollback_capability",
                name="Rollback Capability",
                description="Ensure override actions can be rolled back",
                bypass_allowed=True,
                bypass_conditions=["irreversible_actions_required"],
                monitoring_required=True,
                ethical_review_required=False
            ),
            "notification_protocols": OverrideSafeguard(
                safeguard_id="notification_protocols",
                name="Notification Protocols",
                description="Ensure proper notification of override activation",
                bypass_allowed=False,
                bypass_conditions=[],
                monitoring_required=True,
                ethical_review_required=False
            )
        }

    def _load_override_protocols(self) -> Dict[str, Dict[str, Any]]:
        """Load override protocols for different scenarios"""
        return {
            "system_shutdown": {
                "allowed_severity": ["critical", "existential"],
                "required_approvals": ["ceo"],
                "maximum_duration": 72,  # hours
                "rollback_required": True,
                "monitoring_level": "continuous"
            },
            "resource_reallocation": {
                "allowed_severity": ["moderate", "severe", "critical", "existential"],
                "required_approvals": ["ceo", "coo"],
                "maximum_duration": 48,
                "rollback_required": True,
                "monitoring_level": "high"
            },
            "decision_bypass": {
                "allowed_severity": ["severe", "critical", "existential"],
                "required_approvals": ["ceo"],
                "maximum_duration": 24,
                "rollback_required": False,
                "monitoring_level": "continuous"
            },
            "communication_lockdown": {
                "allowed_severity": ["critical", "existential"],
                "required_approvals": ["ceo", "council_52"],
                "maximum_duration": 12,
                "rollback_required": True,
                "monitoring_level": "continuous"
            },
            "data_purge": {
                "allowed_severity": ["existential"],
                "required_approvals": ["ceo", "council_52", "ethics_board"],
                "maximum_duration": 6,
                "rollback_required": False,
                "monitoring_level": "continuous"
            },
            "emergency_mode": {
                "allowed_severity": ["critical", "existential"],
                "required_approvals": ["ceo"],
                "maximum_duration": 96,
                "rollback_required": True,
                "monitoring_level": "continuous"
            }
        }

    def _load_emergency_procedures(self) -> Dict[str, List[str]]:
        """Load emergency procedures for different override types"""
        return {
            "system_shutdown": [
                "Isolate affected systems",
                "Preserve critical data",
                "Notify all users of shutdown",
                "Activate backup communication channels",
                "Begin controlled shutdown sequence"
            ],
            "resource_reallocation": [
                "Assess current resource allocation",
                "Identify critical needs",
                "Reallocate resources to priority systems",
                "Monitor resource utilization",
                "Prepare rollback procedures"
            ],
            "decision_bypass": [
                "Document bypassed decision processes",
                "Execute emergency decision protocol",
                "Log all bypass actions",
                "Schedule post-emergency review",
                "Monitor decision outcomes"
            ],
            "communication_lockdown": [
                "Activate secure communication channels",
                "Restrict external communications",
                "Establish internal communication protocols",
                "Monitor communication attempts",
                "Prepare communication restoration plan"
            ],
            "data_purge": [
                "Identify data to be purged",
                "Create backup of critical data",
                "Execute secure data deletion",
                "Verify data destruction",
                "Document purge actions"
            ],
            "emergency_mode": [
                "Activate emergency command protocols",
                "Reconfigure system priorities",
                "Enable emergency decision pathways",
                "Monitor system stability",
                "Prepare for emergency escalation"
            ]
        }

    def declare_emergency_override(
            self, override_type: OverrideType, severity: OverrideSeverity,
            reason: str, justification: str, declared_by: str,
            affected_systems: List[str],
            duration_hours: int) ->str:
        """
        Declare an emergency override

        Args:
            override_type: Type of override
            severity: Override severity
            reason: Reason for override
            justification: Detailed justification
            declared_by: Who is declaring the override
            affected_systems: Systems affected
            duration_hours: Duration in hours

        Returns:
            Override ID

        Raises:
            ValueError: If override cannot be declared
        """
        # Validate override protocol
        if not self._validate_override_protocol(
            override_type, severity, duration_hours):
            raise ValueError(
                f"Override protocol validation failed for {override_type.value}")

        # Check safeguards
        if not self._check_override_safeguards(
            override_type, severity, justification):
            raise ValueError("Override safeguards not satisfied")

        # Verify authority
        if not self._verify_override_authority(
            declared_by, override_type, severity):
            raise ValueError("Insufficient authority for override declaration")

        override_id = f"override_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Get override actions
        override_actions = self.emergency_procedures.get(
            override_type.value, [])

        # Determine bypassed safeguards
        bypassed_safeguards = self._determine_bypassed_safeguards(
            override_type, severity)

        override = EmergencyOverride(
            override_id=override_id,
            override_type=override_type,
            severity=severity,
            reason=reason,
            justification=justification,
            declared_by=declared_by,
            affected_systems=affected_systems,
            override_actions=override_actions,
            safeguards_bypassed=bypassed_safeguards,
            declared_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + \
                        timedelta(hours=duration_hours)).isoformat()
        )

        self.active_overrides[override_id] = override

        # Execute override actions
        self._execute_override_actions(override)

        # Generate emergency briefing
        self._generate_emergency_briefing(override)

        logger.critical(
            f"EMERGENCY OVERRIDE DECLARED: {override_id} - {override_type.value} ({severity.value})")

        return override_id

    def _validate_override_protocol(
            self, override_type: OverrideType, severity: OverrideSeverity,
            duration_hours: int) ->bool:
        """Validate override against protocol requirements"""
        protocol = self.override_protocols.get(override_type.value)
        if not protocol:
            return False

        # Check severity
        if severity.value not in protocol["allowed_severity"]:
            logger.error(
                f"Severity {severity.value} not allowed for {override_type.value}")
            return False

        # Check duration
        if duration_hours > protocol["maximum_duration"]:
            logger.error(
                f"Duration {duration_hours}h exceeds maximum {protocol['maximum_duration']}h")
            return False

        return True

    def _check_override_safeguards(
            self, override_type: OverrideType, severity: OverrideSeverity,
            justification: str) ->bool:
        """Check if override passes safeguard requirements"""
        for safeguard in self.safeguards.values():
            if not safeguard.bypass_allowed:
                # Check if safeguard can be bypassed
                bypass_conditions = safeguard.bypass_conditions
                if severity.value not in bypass_conditions and "existential_crisis" not in bypass_conditions:
                    logger.error(
                        f"Safeguard {safeguard.name} cannot be bypassed")
                    return False

        # Perform ethical compliance check
        ethical_score = self._assess_ethical_compliance(
            justification, override_type, severity)
        if ethical_score < 0.8:  # Minimum ethical threshold
            logger.error(f"Ethical compliance score too low: {ethical_score}")
            return False

        return True

    def _assess_ethical_compliance(
            self, justification: str, override_type: OverrideType,
            severity: OverrideSeverity) ->float:
        """Assess ethical compliance of override"""
        # Simple ethical assessment based on justification quality
        justification_length = len(justification)
        has_ethical_considerations = any(
            word in justification.lower()
            for word
            in
            ["ethical", "moral", "responsible", "accountable", "transparent"])

        base_score = 0.5
        if justification_length > 100:
            base_score += 0.2
        if has_ethical_considerations:
            base_score += 0.2
        if severity == OverrideSeverity.EXISTENTIAL:
            base_score += 0.1  # Higher tolerance for existential crises

        return min(base_score, 1.0)

    def _verify_override_authority(
            self, declared_by: str, override_type: OverrideType,
            severity: OverrideSeverity) ->bool:
        """Verify authority to declare override"""
        # In a real system, this would check user roles and permissions
        # For now, accept CEO and system accounts
        authorized_entities = ["CEO", "crisis_management_system", "council_52"]

        return declared_by in authorized_entities

    def _determine_bypassed_safeguards(self, override_type: OverrideType,
                                     severity: OverrideSeverity) -> List[str]:
        """Determine which safeguards are bypassed"""
        bypassed = []

        for safeguard in self.safeguards.values():
            if safeguard.bypass_allowed:
                if severity.value in safeguard.bypass_conditions or "existential_crisis" in safeguard.bypass_conditions:
                    bypassed.append(safeguard.safeguard_id)

        return bypassed

    def _execute_override_actions(self, override: EmergencyOverride):
        """Execute override actions"""
        logger.warning(
            f"Executing override actions for {override.override_id}")

        for action in override.override_actions:
            logger.info(f"Override action: {action}")
            override.executed_actions.append(action)
            # In a real implementation, these would trigger actual system actions

    def _generate_emergency_briefing(self, override: EmergencyOverride):
        """Generate emergency briefing for override"""
        briefing_title = f"EMERGENCY OVERRIDE: {
            override.override_type.value.upper()} "

        briefing_content = f"""
        EMERGENCY OVERRIDE DECLARED

        Type: {override.override_type.value}
        Severity: {override.severity.value}
        Reason: {override.reason}
        Declared By: {override.declared_by}
        Affected Systems: {', '.join(override.affected_systems)}
        Expires: {override.expires_at}

        Actions Taken: {', '.join(override.executed_actions)}
        Bypassed Safeguards: {', '.join(override.safeguards_bypassed)}
        """

        # Generate intelligence briefing
        self.briefings_system.collect_intelligence(
            source="emergency_override_system",
            title=briefing_title,
            content=briefing_content,
            confidence=1.0,
            tags=["emergency", "override",
                override.override_type.value, override.severity.value]
        )

    def deactivate_override(
            self, override_id: str, reason: str, deactivated_by: str) ->bool:
        """
        Deactivate an emergency override

        Args:
            override_id: Override to deactivate
            reason: Reason for deactivation
            deactivated_by: Who is deactivating

        Returns:
            Success status
        """
        if override_id not in self.active_overrides:
            logger.error(f"Override {override_id} not found")
            return False

        override = self.active_overrides[override_id]

        # Verify deactivation authority
        if not self._verify_deactivation_authority(deactivated_by, override):
            logger.error(
                f"Insufficient authority to deactivate override {override_id}")
            return False

        override.status = "deactivated"
        override.deactivated_at = datetime.now().isoformat()
        override.deactivation_reason = reason

        # Execute rollback procedures
        self._execute_rollback_procedures(override)

        # Move to history
        self.override_history.append(override)
        del self.active_overrides[override_id]

        # Generate deactivation briefing
        self._generate_deactivation_briefing(override, reason)

        logger.warning(
            f"Emergency override deactivated: {override_id} - {reason}")

        return True

    def _verify_deactivation_authority(
            self, deactivated_by: str, override: EmergencyOverride) ->bool:
        """Verify authority to deactivate override"""
        # CEO can deactivate any override
        if deactivated_by == "CEO":
            return True

        # Original declarer can deactivate their own overrides
        if deactivated_by == override.declared_by:
            return True

        # Crisis management system can deactivate
        if deactivated_by == "crisis_management_system":
            return True

        return False

    def _execute_rollback_procedures(self, override: EmergencyOverride):
        """Execute rollback procedures for override"""
        logger.info(
            f"Executing rollback procedures for override {override.override_id}")

        # In a real implementation, this would reverse the override actions
        rollback_actions = [
            f"Rollback: {action}" for action in override.executed_actions
        ]

        for action in rollback_actions:
            logger.info(f"Rollback action: {action}")

    def _generate_deactivation_briefing(
            self, override: EmergencyOverride, reason: str):
        """Generate briefing for override deactivation"""
        briefing_title = f"EMERGENCY OVERRIDE DEACTIVATED: {
            override.override_type.value.upper()} "

        briefing_content = f"""
        EMERGENCY OVERRIDE DEACTIVATED

        Override ID: {override.override_id}
        Type: {override.override_type.value}
        Reason for Deactivation: {reason}
        Deactivated At: {override.deactivated_at}

        Original Declaration:
        - Reason: {override.reason}
        - Declared By: {override.declared_by}
        - Duration: From {override.declared_at} to {override.expires_at}
        """

        self.briefings_system.collect_intelligence(
            source="emergency_override_system",
            title=briefing_title,
            content=briefing_content,
            confidence=1.0,
            tags=["emergency", "override", "deactivated",
                override.override_type.value]
        )

    def get_override_status(self) -> Dict[str, Any]:
        """Get current override status"""
        return {
            "active_overrides": len(self.active_overrides),
            "total_overrides_declared": len(self.override_history),
            "active_override_details": [
                {
                    "id": override.override_id,
                    "type": override.override_type.value,
                    "severity": override.severity.value,
                    "declared_at": override.declared_at,
                    "expires_at": override.expires_at,
                    "affected_systems": override.affected_systems
                }
                for override in self.active_overrides.values()
            ],
            "system_status": "override_active" if self.active_overrides else "normal"
        }

    def check_override_expiry(self):
        """Check for expired overrides and deactivate them"""
        now = datetime.now()
        expired_overrides = []

        for override_id, override in self.active_overrides.items():
            expires_at = datetime.fromisoformat(override.expires_at)
            if now >= expires_at:
                expired_overrides.append(override_id)

        for override_id in expired_overrides:
            self.deactivate_override(override_id, "Automatic expiry", "system")

        if expired_overrides:
            logger.info(
                f"Auto-deactivated {len(expired_overrides)} expired overrides")


# Convenience functions
def declare_emergency_override(
        override_type: str, severity: str, reason: str, justification: str,
        declared_by: str, affected_systems: List[str],
        duration_hours: int) ->str:
    """Convenience function for emergency override declaration"""
    mechanisms = EmergencyOverrideMechanisms()
    type_enum = OverrideType(override_type)
    severity_enum = OverrideSeverity(severity)
    return mechanisms.declare_emergency_override(
        type_enum, severity_enum, reason, justification, declared_by,
        affected_systems, duration_hours
    )


def deactivate_emergency_override(
        override_id: str, reason: str, deactivated_by: str) ->bool:
    """Convenience function for override deactivation"""
    mechanisms = EmergencyOverrideMechanisms()
    return mechanisms.deactivate_override(override_id, reason, deactivated_by)


def get_override_status() -> Dict[str, Any]:
    """Get current override status"""
    mechanisms = EmergencyOverrideMechanisms()
    return mechanisms.get_override_status()


def check_override_expiry():
    """Check for expired overrides"""
    mechanisms = EmergencyOverrideMechanisms()
    mechanisms.check_override_expiry()