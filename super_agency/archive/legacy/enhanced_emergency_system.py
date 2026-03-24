#!/usr/bin/env python3
"""
Enhanced Emergency Override System
Active monitoring and human intervention capabilities for DIGITAL LABOUR
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from emergency_override_mechanisms import EmergencyOverrideMechanisms, OverrideType, OverrideSeverity
from operations_centers import operations_manager
from conductor_integration_manager import ConductorIntegrationManager

class EmergencyTrigger(Enum):
    """Types of emergency triggers"""
    SYSTEM_CRASH = "system_crash"
    SECURITY_BREACH = "security_breach"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    DECISION_FAILURE = "decision_failure"
    HUMAN_INTERVENTION = "human_intervention"
    EXTERNAL_THREAT = "external_threat"

@dataclass
class EmergencyCondition:
    """Emergency condition monitoring"""
    condition_id: str
    trigger_type: EmergencyTrigger
    name: str
    description: str
    threshold: Any
    current_value: Any = None
    triggered: bool = False
    last_checked: Optional[datetime] = None
    check_interval: int = 60  # seconds

@dataclass
class ActiveEmergency:
    """Active emergency response"""
    emergency_id: str
    trigger_condition: EmergencyCondition
    override_type: OverrideType
    severity: OverrideSeverity
    response_actions: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    status: str = "active"
    human_acknowledged: bool = False

class EnhancedEmergencySystem:
    """Enhanced emergency override system with active monitoring"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.emergency_mechanisms = EmergencyOverrideMechanisms()
        self.monitoring_conditions = self._initialize_monitoring_conditions()
        self.active_emergencies: Dict[str, ActiveEmergency] = {}
        self.monitoring_active = False

    def _initialize_monitoring_conditions(self) -> List[EmergencyCondition]:
        """Initialize emergency monitoring conditions"""
        return [
            EmergencyCondition(
                condition_id="cpu_critical",
                trigger_type=EmergencyTrigger.RESOURCE_EXHAUSTION,
                name="Critical CPU Usage",
                description="CPU usage exceeds 95% for extended period",
                threshold=95.0,
                check_interval=30
            ),
            EmergencyCondition(
                condition_id="memory_critical",
                trigger_type=EmergencyTrigger.RESOURCE_EXHAUSTION,
                name="Critical Memory Usage",
                description="Memory usage exceeds 90%",
                threshold=90.0,
                check_interval=60
            ),
            EmergencyCondition(
                condition_id="agent_failure",
                trigger_type=EmergencyTrigger.SYSTEM_CRASH,
                name="Agent System Failure",
                description="More than 50% of agents inactive",
                threshold=0.5,
                check_interval=120
            ),
            EmergencyCondition(
                condition_id="security_alert",
                trigger_type=EmergencyTrigger.SECURITY_BREACH,
                name="Security Alert",
                description="Security monitoring system detects threat",
                threshold=True,
                check_interval=30
            ),
            EmergencyCondition(
                condition_id="decision_timeout",
                trigger_type=EmergencyTrigger.DECISION_FAILURE,
                name="Decision Timeout",
                description="Critical decisions taking too long",
                threshold=300,  # 5 minutes
                check_interval=60
            )
        ]

    async def start_emergency_monitoring(self) -> Dict[str, Any]:
        """Start continuous emergency monitoring"""
        self.logger.info("🚨 Starting Enhanced Emergency Monitoring System")

        try:
            # Start monitoring loop
            asyncio.create_task(self._emergency_monitoring_loop())
            self.monitoring_active = True

            return {
                "success": True,
                "message": "Emergency monitoring system activated",
                "conditions_monitored": len(self.monitoring_conditions),
                "monitoring_interval": "continuous"
            }
        except Exception as e:
            self.logger.error(f"Failed to start emergency monitoring: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _emergency_monitoring_loop(self):
        """Continuous emergency monitoring loop"""
        while self.monitoring_active:
            try:
                # Check all emergency conditions
                for condition in self.monitoring_conditions:
                    await self._check_emergency_condition(condition)

                # Check for active emergency responses
                await self._manage_active_emergencies()

                # Save emergency status
                await self._save_emergency_status()

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                self.logger.error(f"Emergency monitoring loop error: {e}")
                await asyncio.sleep(60)

    async def _check_emergency_condition(self, condition: EmergencyCondition):
        """Check a specific emergency condition"""
        try:
            # Get current system metrics
            current_value = await self._get_condition_value(condition)

            condition.current_value = current_value
            condition.last_checked = datetime.now()

            # Check if threshold is exceeded
            if self._is_threshold_exceeded(condition):
                if not condition.triggered:
                    # New emergency triggered
                    await self._trigger_emergency(condition)
                    condition.triggered = True
            else:
                if condition.triggered:
                    # Emergency resolved
                    await self._resolve_emergency(condition)
                    condition.triggered = False

        except Exception as e:
            self.logger.error(f"Error checking condition {condition.condition_id}: {e}")

    async def _get_condition_value(self, condition: EmergencyCondition) -> Any:
        """Get current value for emergency condition"""
        if condition.condition_id == "cpu_critical":
            import psutil
            return psutil.cpu_percent(interval=1)
        elif condition.condition_id == "memory_critical":
            import psutil
            return psutil.virtual_memory().percent
        elif condition.condition_id == "agent_failure":
            status = await operations_manager.get_operations_status()
            total_agents = status["overall_metrics"]["total_agents"]
            active_agents = status["overall_metrics"]["active_agents"]
            return (total_agents - active_agents) / total_agents if total_agents > 0 else 0
        elif condition.condition_id == "security_alert":
            # Placeholder for security monitoring
            return False
        elif condition.condition_id == "decision_timeout":
            # Placeholder for decision monitoring
            return 0
        return 0

    def _is_threshold_exceeded(self, condition: EmergencyCondition) -> bool:
        """Check if condition threshold is exceeded"""
        if isinstance(condition.threshold, (int, float)):
            if condition.condition_id in ["cpu_critical", "memory_critical", "agent_failure"]:
                return condition.current_value >= condition.threshold
            elif condition.condition_id == "decision_timeout":
                return condition.current_value >= condition.threshold
        return False

    async def _trigger_emergency(self, condition: EmergencyCondition):
        """Trigger emergency response for condition"""
        self.logger.warning(f"🚨 EMERGENCY TRIGGERED: {condition.name}")

        # Create emergency response
        emergency = ActiveEmergency(
            emergency_id=f"emergency_{condition.condition_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            trigger_condition=condition,
            override_type=self._get_override_type_for_condition(condition),
            severity=self._get_severity_for_condition(condition),
            response_actions=self._get_response_actions_for_condition(condition)
        )

        self.active_emergencies[emergency.emergency_id] = emergency

        # Execute immediate response actions
        await self._execute_emergency_response(emergency)

        # Notify human operators
        await self._notify_human_operators(emergency)

    async def _execute_emergency_response(self, emergency: ActiveEmergency):
        """Execute emergency response actions"""
        for action in emergency.response_actions:
            try:
                self.logger.info(f"Executing emergency action: {action}")
                # Execute the action (placeholder for actual implementation)
                await self._execute_action(action)
                emergency.response_actions.remove(action)
            except Exception as e:
                self.logger.error(f"Failed to execute emergency action {action}: {e}")

    async def _notify_human_operators(self, emergency: ActiveEmergency):
        """Notify human operators of emergency"""
        notification = {
            "emergency_id": emergency.emergency_id,
            "type": emergency.trigger_condition.trigger_type.value,
            "severity": emergency.severity.value,
            "description": emergency.trigger_condition.description,
            "timestamp": emergency.started_at.isoformat(),
            "requires_acknowledgment": True
        }

        # Save notification for human review
        notification_file = f"emergency_notification_{emergency.emergency_id}.json"
        with open(notification_file, 'w') as f:
            json.dump(notification, f, indent=2, default=str)

        self.logger.critical(f"🚨 HUMAN INTERVENTION REQUIRED: {emergency.emergency_id}")

    def _get_override_type_for_condition(self, condition: EmergencyCondition) -> OverrideType:
        """Get appropriate override type for condition"""
        if condition.trigger_type == EmergencyTrigger.RESOURCE_EXHAUSTION:
            return OverrideType.RESOURCE_REALLOCATION
        elif condition.trigger_type == EmergencyTrigger.SYSTEM_CRASH:
            return OverrideType.SYSTEM_SHUTDOWN
        elif condition.trigger_type == EmergencyTrigger.SECURITY_BREACH:
            return OverrideType.COMMUNICATION_LOCKDOWN
        else:
            return OverrideType.EMERGENCY_MODE

    def _get_severity_for_condition(self, condition: EmergencyCondition) -> OverrideSeverity:
        """Get severity level for condition"""
        if "critical" in condition.condition_id:
            return OverrideSeverity.CRITICAL
        elif condition.trigger_type == EmergencyTrigger.SECURITY_BREACH:
            return OverrideSeverity.SEVERE
        else:
            return OverrideSeverity.MODERATE

    def _get_response_actions_for_condition(self, condition: EmergencyCondition) -> List[str]:
        """Get response actions for condition"""
        actions = []
        if condition.condition_id == "cpu_critical":
            actions.extend(["reduce_cpu_intensive_tasks", "scale_down_operations", "alert_administrators"])
        elif condition.condition_id == "memory_critical":
            actions.extend(["trigger_memory_cleanup", "reduce_memory_usage", "alert_administrators"])
        elif condition.condition_id == "agent_failure":
            actions.extend(["restart_failed_agents", "redistribute_workload", "alert_administrators"])
        return actions

    async def _execute_action(self, action: str):
        """Execute a specific emergency action"""
        # Placeholder for actual action execution
        if action == "reduce_cpu_intensive_tasks":
            # Implement CPU reduction logic
            pass
        elif action == "trigger_memory_cleanup":
            # Implement memory cleanup
            pass
        elif action == "restart_failed_agents":
            # Implement agent restart
            pass
        # Add more actions as needed

    async def _resolve_emergency(self, condition: EmergencyCondition):
        """Resolve emergency when condition returns to normal"""
        # Find and resolve related emergencies
        for emergency_id, emergency in self.active_emergencies.items():
            if emergency.trigger_condition.condition_id == condition.condition_id:
                emergency.status = "resolved"
                self.logger.info(f"✅ EMERGENCY RESOLVED: {emergency.emergency_id}")

    async def _manage_active_emergencies(self):
        """Manage ongoing emergency responses"""
        current_time = datetime.now()

        for emergency_id, emergency in list(self.active_emergencies.items()):
            # Check for emergency timeout (24 hours)
            if (current_time - emergency.started_at).total_seconds() > 86400:
                emergency.status = "timed_out"
                self.logger.warning(f"Emergency {emergency_id} timed out")

            # Remove resolved/timed out emergencies
            if emergency.status in ["resolved", "timed_out"]:
                del self.active_emergencies[emergency_id]

    async def _save_emergency_status(self):
        """Save current emergency system status"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "monitoring_active": self.monitoring_active,
            "active_emergencies": len(self.active_emergencies),
            "conditions_monitored": len(self.monitoring_conditions),
            "emergency_details": [
                {
                    "id": e.emergency_id,
                    "type": e.trigger_condition.trigger_type.value,
                    "severity": e.severity.value,
                    "status": e.status,
                    "started": e.started_at.isoformat()
                } for e in self.active_emergencies.values()
            ]
        }

        status_file = f"emergency_system_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(status_file, 'w') as f:
            json.dump(status, f, indent=2, default=str)

    async def acknowledge_emergency(self, emergency_id: str, human_user: str) -> Dict[str, Any]:
        """Human acknowledgment of emergency"""
        if emergency_id in self.active_emergencies:
            emergency = self.active_emergencies[emergency_id]
            emergency.human_acknowledged = True
            self.logger.info(f"✅ Emergency {emergency_id} acknowledged by {human_user}")

            return {
                "success": True,
                "message": f"Emergency {emergency_id} acknowledged",
                "emergency_details": {
                    "id": emergency.emergency_id,
                    "type": emergency.trigger_condition.trigger_type.value,
                    "severity": emergency.severity.value
                }
            }
        else:
            return {
                "success": False,
                "error": f"Emergency {emergency_id} not found"
            }

    async def get_emergency_status(self) -> Dict[str, Any]:
        """Get current emergency system status"""
        return {
            "monitoring_active": self.monitoring_active,
            "active_emergencies": len(self.active_emergencies),
            "conditions_monitored": len(self.monitoring_conditions),
            "emergency_list": [
                {
                    "id": e.emergency_id,
                    "type": e.trigger_condition.trigger_type.value,
                    "severity": e.severity.value,
                    "status": e.status,
                    "acknowledged": e.human_acknowledged
                } for e in self.active_emergencies.values()
            ]
        }

async def main():
    """Main emergency system activation"""
    emergency_system = EnhancedEmergencySystem()
    result = await emergency_system.start_emergency_monitoring()

    # Save activation report
    report_file = f"emergency_system_activation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)

    print(f"✅ Enhanced Emergency System activated. Report: {report_file}")
    return result

if __name__ == "__main__":
    asyncio.run(main())
