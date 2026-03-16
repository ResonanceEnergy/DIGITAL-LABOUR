"""
Crisis Management Framework
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

from oversight_framework import OversightFramework
from ceo_command_authority import CEOCommandAuthority, DecisionAuthority
from executive_decision_matrix import DecisionMatrix

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CrisisSeverity(Enum):
    """Crisis severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EXISTENTIAL = "existential"


class CrisisType(Enum):
    """Types of crises"""
    TECHNICAL = "technical"
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    SECURITY = "security"
    REPUTATIONAL = "reputational"
    REGULATORY = "regulatory"
    STRATEGIC = "strategic"


@dataclass
class CrisisEvent:
    """Crisis event data structure"""
    crisis_id: str
    title: str
    description: str
    crisis_type: CrisisType
    severity: CrisisSeverity
    detected_at: str
    reported_by: str
    affected_systems: List[str]
    impact_assessment: Dict[str, Any]
    immediate_actions: List[str]
    escalation_path: List[str]
    status: str = "active"
    resolved_at: Optional[str] = None
    resolution_summary: Optional[str] = None


@dataclass
class ExecutiveBriefing:
    """Executive intelligence briefing"""
    briefing_id: str
    title: str
    priority: str
    executive_summary: str
    key_findings: List[str]
    recommendations: List[str]
    intelligence_sources: List[str]
    confidence_level: float
    generated_at: str
    expires_at: str
    classification: str = "confidential"


class CrisisManagementFramework:
    """
    Crisis Management Framework for DIGITAL LABOUR
    Handles crisis detection, response, and executive briefings
    """

    def __init__(self):
        """Initialize."""
        self.oversight = OversightFramework()
        self.ceo_authority = CEOCommandAuthority()
        self.decision_matrix = DecisionMatrix()

        # Crisis management state
        self.active_crises: Dict[str, CrisisEvent] = {}
        self.crisis_history: List[CrisisEvent] = []
        self.executive_briefings: Dict[str, ExecutiveBriefing] = {}

        # Crisis response protocols
        self.crisis_protocols = self._load_crisis_protocols()
        self.escalation_thresholds = self._load_escalation_thresholds()

        logger.info("Crisis Management Framework initialized")

    def _load_crisis_protocols(self) -> Dict[str, Dict[str, Any]]:
        """Load crisis response protocols"""
        return {
            "technical_failure": {
                "immediate_actions": [
                    "Isolate affected systems",
                    "Activate backup systems",
                    "Notify technical team",
                    "Begin impact assessment"
                ],
                "escalation_triggers": ["system_down", "data_loss", "security_breach"],
                "executive_notification": "immediate"
            },
            "financial_crisis": {
                "immediate_actions": [
                    "Freeze all financial transactions",
                    "Contact financial regulators",
                    "Assess liquidity position",
                    "Prepare contingency funding"
                ],
                "escalation_triggers": ["market_crash", "liquidity_crisis", "regulatory_action"],
                "executive_notification": "immediate"
            },
            "security_breach": {
                "immediate_actions": [
                    "Isolate compromised systems",
                    "Activate incident response team",
                    "Preserve evidence",
                    "Notify security authorities"
                ],
                "escalation_triggers": ["data_breach", "system_compromise", "ransomware"],
                "executive_notification": "immediate"
            },
            "reputational_crisis": {
                "immediate_actions": [
                    "Monitor social media and news",
                    "Prepare public statement",
                    "Contact key stakeholders",
                    "Assess brand impact"
                ],
                "escalation_triggers": ["negative_coverage", "stakeholder_concerns", "regulatory_scandal"],
                "executive_notification": "within_1_hour"
            }
        }

    def _load_escalation_thresholds(self) -> Dict[str, Dict[str, Any]]:
        """Load crisis escalation thresholds"""
        return {
            "severity_escalation": {
                "medium": ["notify_executive_team"],
                "high": ["notify_ceo", "activate_crisis_team"],
                "critical": ["declare_emergency", "activate_executive_override"],
                "existential": ["maximum_escalation", "board_notification"]
            },
            "impact_escalation": {
                "financial_impact": {
                    "high": "notify_cfo",
                    "critical": "notify_ceo"
                },
                "operational_impact": {
                    "high": "notify_coo",
                    "critical": "notify_ceo"
                },
                "reputational_impact": {
                    "high": "notify_ceo",
                    "critical": "activate_crisis_communications"
                }
            }
        }

    def detect_crisis(self, title: str, description: str,
                      crisis_type: CrisisType, severity: CrisisSeverity,
                      detected_by: str, affected_systems: List[str],
                      impact_assessment: Dict[str, Any]) ->str:
        """
        Detect and register a new crisis event

        Args:
            title: Crisis title
            description: Detailed description
            crisis_type: Type of crisis
            severity: Crisis severity level
            detected_by: Who detected the crisis
            affected_systems: Systems affected
            impact_assessment: Impact assessment data

        Returns:
            Crisis ID
        """
        crisis_id = f"crisis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Determine immediate actions based on crisis type
        protocol = self.crisis_protocols.get(crisis_type.value, {})
        immediate_actions = protocol.get("immediate_actions", [
            "Assess situation",
            "Notify relevant teams",
            "Begin impact analysis"
        ])

        # Determine escalation path based on severity
        escalation_path = self._determine_escalation_path(
            severity, impact_assessment)

        crisis = CrisisEvent(
            crisis_id=crisis_id,
            title=title,
            description=description,
            crisis_type=crisis_type,
            severity=severity,
            detected_at=datetime.now().isoformat(),
            reported_by=detected_by,
            affected_systems=affected_systems,
            impact_assessment=impact_assessment,
            immediate_actions=immediate_actions,
            escalation_path=escalation_path
        )

        self.active_crises[crisis_id] = crisis

        # Execute immediate actions
        self._execute_immediate_actions(crisis)

        # Escalate based on severity
        self._escalate_crisis(crisis)

        logger.warning(
            f"Crisis detected: {crisis_id} - {title} (Severity: {severity.value})")

        return crisis_id

    def _determine_escalation_path(
            self, severity: CrisisSeverity, impact_assessment: Dict
            [str, Any]) ->List[str]:
        """Determine escalation path based on severity and impact"""
        escalation_path = []

        # Base escalation by severity
        severity_actions = self.escalation_thresholds["severity_escalation"].get(
            severity.value, [])
        escalation_path.extend(severity_actions)

        # Additional escalation by impact
        for impact_type, threshold in impact_assessment.items():
            if impact_type in self.escalation_thresholds["impact_escalation"]:
                impact_actions = self.escalation_thresholds["impact_escalation"][impact_type]
                if threshold in ["high", "critical"]:
                    escalation_path.extend(impact_actions.get(threshold, []))

        return list(set(escalation_path))  # Remove duplicates

    def _execute_immediate_actions(self, crisis: CrisisEvent):
        """Execute immediate crisis response actions"""
        logger.info(
            f"Executing immediate actions for crisis {crisis.crisis_id}")

        for action in crisis.immediate_actions:
            logger.info(f"Action: {action}")
            # In a real implementation, these would trigger actual system actions

    def _escalate_crisis(self, crisis: CrisisEvent):
        """Escalate crisis based on determined path"""
        logger.info(
            f"Escalating crisis {crisis.crisis_id} via: {crisis.escalation_path}")

        for escalation_action in crisis.escalation_path:
            if escalation_action == "notify_executive_team":
                self._notify_executive_team(crisis)
            elif escalation_action == "notify_ceo":
                self._notify_ceo(crisis)
            elif escalation_action == "activate_crisis_team":
                self._activate_crisis_team(crisis)
            elif escalation_action == "declare_emergency":
                self._declare_emergency(crisis)
            elif escalation_action == "activate_executive_override":
                self._activate_executive_override(crisis)

    def _notify_executive_team(self, crisis: CrisisEvent):
        """Notify executive team of crisis"""
        logger.info(f"Notifying executive team of crisis {crisis.crisis_id}")

        # Generate executive briefing
        briefing = self.generate_executive_briefing(
            title=f"Crisis Alert: {crisis.title}",
            priority="high",
            executive_summary=f"A {crisis.severity.value} severity {crisis.crisis_type.value} crisis has been detected affecting: {', '.join(crisis.affected_systems)}",
            key_findings=[
                f"Crisis Type: {crisis.crisis_type.value}",
                f"Severity: {crisis.severity.value}",
                f"Detected by: {crisis.reported_by}",
                f"Affected Systems: {', '.join(crisis.affected_systems)}"
            ],
            recommendations=crisis.immediate_actions,
            intelligence_sources=["crisis_detection_system"],
            confidence_level=0.95
        )

        # Submit to CEO authority for executive routing
        self.ceo_authority.submit_executive_decision(
            category="crisis",
            title=f"Crisis Response: {crisis.title}",
            description=f"Executive notification for {crisis.severity.value} crisis",
            impact_level=crisis.severity.value,
            proposed_by="crisis_management_system",
            ethical_assessment={"urgency": 1.0, "transparency": 0.9},
            risk_assessment={"escalation_risk": 0.8, "impact_risk": 0.9},
            timeline="immediate",
            financial_impact=crisis.impact_assessment.get(
                "financial_impact", 0)
        )

    def _notify_ceo(self, crisis: CrisisEvent):
        """Notify CEO directly"""
        logger.warning(f"CEO notification for crisis {crisis.crisis_id}")

        # Generate high-priority CEO briefing
        briefing = self.generate_executive_briefing(
            title=f"CEO Alert: {crisis.title}",
            priority="critical",
            executive_summary=f"CRITICAL: {crisis.severity.value.upper()} crisis requires CEO attention. {crisis.description}",
            key_findings=[
                f"Immediate CEO attention required",
                f"Crisis Type: {crisis.crisis_type.value}",
                f"Severity: {crisis.severity.value}",
                f"Impact: {json.dumps(crisis.impact_assessment)}"
            ],
            recommendations=[
                "CEO to assess situation immediately",
                "Consider executive override if necessary",
                "Prepare crisis communication strategy"
            ],
            intelligence_sources=[
                "crisis_management_system", "executive_intelligence"],
            confidence_level=0.98
        )

    def _activate_crisis_team(self, crisis: CrisisEvent):
        """Activate crisis response team"""
        logger.info(f"Activating crisis response team for {crisis.crisis_id}")

        # In a real implementation, this would activate specific team members
        # and communication channels

    def _declare_emergency(self, crisis: CrisisEvent):
        """Declare emergency state"""
        logger.critical(f"EMERGENCY DECLARED for crisis {crisis.crisis_id}")

        # Generate emergency briefing
        briefing = self.generate_executive_briefing(
            title=f"EMERGENCY: {crisis.title}",
            priority="existential",
            executive_summary=f"EMERGENCY STATE DECLARED: {crisis.description}",
            key_findings=[
                "Emergency protocols activated",
                "All systems on high alert",
                "Executive override may be required"
            ],
            recommendations=[
                "Activate all emergency protocols",
                "Prepare for executive override",
                "Notify all critical stakeholders"
            ],
            intelligence_sources=["emergency_system"],
            confidence_level=1.0
        )

    def _activate_executive_override(self, crisis: CrisisEvent):
        """Activate executive override for crisis response"""
        logger.critical(
            f"EXECUTIVE OVERRIDE activation for crisis {crisis.crisis_id}")

        try:
            override_id = self.ceo_authority.declare_executive_override(
                reason=f"Critical crisis response: {crisis.title}",
                declared_by="crisis_management_system",
                affected_systems=crisis.affected_systems,
                duration_hours=24
            )
            logger.warning(f"Executive override activated: {override_id}")
        except ValueError as e:
            logger.error(f"Executive override blocked: {e}")

    def generate_executive_briefing(
            self, title: str, priority: str, executive_summary: str,
            key_findings: List[str],
            recommendations: List[str],
            intelligence_sources: List[str],
            confidence_level: float) ->str:
        """
        Generate an executive intelligence briefing

        Returns:
            Briefing ID
        """
        briefing_id = f"briefing_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        briefing = ExecutiveBriefing(
            briefing_id=briefing_id,
            title=title,
            priority=priority,
            executive_summary=executive_summary,
            key_findings=key_findings,
            recommendations=recommendations,
            intelligence_sources=intelligence_sources,
            confidence_level=confidence_level,
            generated_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(hours=24)).isoformat()
        )

        self.executive_briefings[briefing_id] = briefing

        logger.info(f"Executive briefing generated: {briefing_id} - {title}")

        return briefing_id

    def resolve_crisis(self, crisis_id: str, resolution_summary: str) -> bool:
        """
        Resolve a crisis event

        Args:
            crisis_id: ID of crisis to resolve
            resolution_summary: Summary of resolution

        Returns:
            Success status
        """
        if crisis_id not in self.active_crises:
            logger.error(f"Crisis {crisis_id} not found")
            return False

        crisis = self.active_crises[crisis_id]
        crisis.status = "resolved"
        crisis.resolved_at = datetime.now().isoformat()
        crisis.resolution_summary = resolution_summary

        # Move to history
        self.crisis_history.append(crisis)
        del self.active_crises[crisis_id]

        logger.info(f"Crisis {crisis_id} resolved: {resolution_summary}")

        # Generate resolution briefing
        self.generate_executive_briefing(
            title=f"Crisis Resolved: {crisis.title}",
            priority="medium",
            executive_summary=f"Crisis {crisis_id} has been successfully resolved.",
            key_findings=[
                f"Resolution: {resolution_summary}",
                f"Duration: {self._calculate_crisis_duration(crisis)}",
                f"Final Status: {crisis.status}"
            ],
            recommendations=[
                "Conduct post-crisis review",
                "Update crisis response protocols",
                "Document lessons learned"
            ],
            intelligence_sources=["crisis_resolution_system"],
            confidence_level=0.95
        )

        return True

    def _calculate_crisis_duration(self, crisis: CrisisEvent) -> str:
        """Calculate crisis duration"""
        if not crisis.resolved_at:
            return "Ongoing"

        start = datetime.fromisoformat(crisis.detected_at)
        end = datetime.fromisoformat(crisis.resolved_at)
        duration = end - start

        return f"{duration.total_seconds() / 3600:.1f} hours"

    def get_crisis_status(self) -> Dict[str, Any]:
        """Get current crisis management status"""
        return {
            "active_crises": len(self.active_crises),
            "total_crises_handled": len(self.crisis_history),
            "crisis_summary": [
                {
                    "id": c.crisis_id,
                    "title": c.title,
                    "severity": c.severity.value,
                    "type": c.crisis_type.value,
                    "status": c.status,
                    "detected_at": c.detected_at
                }
                # Last 5 resolved
                for c in list(self.active_crises.values()) + self.crisis_history[-5:]
            ],
            "executive_briefings": len(self.executive_briefings),
            "system_status": "crisis_active" if self.active_crises else "normal"
        }

    def get_executive_briefings(self, priority_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get executive briefings, optionally filtered by priority"""
        briefings = list(self.executive_briefings.values())

        if priority_filter:
            briefings = [b for b in briefings if b.priority == priority_filter]

        # Sort by priority and recency
        priority_order = {"existential": 0, "critical": 1,
            "high": 2, "medium": 3, "low": 4}
        briefings.sort(key=lambda b: (priority_order.get(
            b.priority, 5), b.generated_at), reverse=True)

        return [asdict(b) for b in briefings]


# Convenience functions
def detect_crisis(title: str, description: str, crisis_type: str,
                 severity: str, detected_by: str, affected_systems: List[str],
                 impact_assessment: Dict[str, Any]) -> str:
    """Convenience function for crisis detection"""
    framework = CrisisManagementFramework()

    crisis_type_enum = CrisisType(crisis_type)
    severity_enum = CrisisSeverity(severity)

    return framework.detect_crisis(
        title=title,
        description=description,
        crisis_type=crisis_type_enum,
        severity=severity_enum,
        detected_by=detected_by,
        affected_systems=affected_systems,
        impact_assessment=impact_assessment
    )


def generate_executive_briefing(
        title: str, priority: str, executive_summary: str,
        key_findings: List[str],
        recommendations: List[str],
        intelligence_sources: List[str],
        confidence_level: float) ->str:
    """Convenience function for executive briefing generation"""
    framework = CrisisManagementFramework()
    return framework.generate_executive_briefing(
        title=title,
        priority=priority,
        executive_summary=executive_summary,
        key_findings=key_findings,
        recommendations=recommendations,
        intelligence_sources=intelligence_sources,
        confidence_level=confidence_level
    )


def get_crisis_status() -> Dict[str, Any]:
    """Get current crisis management status"""
    framework = CrisisManagementFramework()
    return framework.get_crisis_status()


def get_executive_briefings(priority_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get executive briefings"""
    framework = CrisisManagementFramework()
    return framework.get_executive_briefings(priority_filter)