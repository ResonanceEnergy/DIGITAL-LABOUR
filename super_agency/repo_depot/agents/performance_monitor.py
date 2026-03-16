# REPO DEPOT AGENTS - Performance Monitor

import asyncio
import logging
import psutil
import os
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import statistics
import json
from collections import deque

from .agent_registry import AgentRegistry

logger = logging.getLogger(__name__)


class MetricType(Enum):
    TASK_SUCCESS_RATE = "task_success_rate"
    TASK_DURATION = "task_duration"
    RESOURCE_USAGE = "resource_usage"
    ERROR_RATE = "error_rate"
    COLLABORATION_EFFICIENCY = "collaboration_efficiency"
    SPECIALIZATION_MATCH = "specialization_match"


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """Individual performance metric"""

    metric_type: MetricType
    value: float
    timestamp: datetime
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceAlert:
    """Performance alert for monitoring"""

    alert_id: str
    level: AlertLevel
    message: str
    agent_id: Optional[str] = None
    metric_type: Optional[MetricType] = None
    threshold_value: float = 0.0
    actual_value: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentPerformanceProfile:
    """Performance profile for an agent"""

    agent_id: str
    metrics_history: Dict[MetricType, deque] = field(
        default_factory=lambda: {mt: deque(maxlen=1000) for mt in MetricType}
    )
    current_stats: Dict[str, Any] = field(default_factory=dict)
    alerts: List[PerformanceAlert] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

    def add_metric(self, metric: PerformanceMetric):
        """Add a metric to the history"""
        if metric.metric_type in self.metrics_history:
            self.metrics_history[metric.metric_type].append(metric)
        self.last_updated = datetime.now()

    def get_recent_metrics(
        self, metric_type: MetricType, hours: int = 24
    ) -> List[PerformanceMetric]:
        """Get recent metrics for the specified type and time window"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [m for m in self.metrics_history[metric_type] if m.timestamp > cutoff]

    def calculate_stats(self, metric_type: MetricType, hours: int = 24) -> Dict[str, Any]:
        """Calculate statistics for a metric type"""
        recent_metrics = self.get_recent_metrics(metric_type, hours)
        if not recent_metrics:
            return {"count": 0, "average": 0.0, "min": 0.0, "max": 0.0}

        values = [m.value for m in recent_metrics]
        return {
            "count": len(values),
            "average": statistics.mean(values),
            "min": min(values),
            "max": max(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
        }


class PerformanceMonitor:
    """
    Real-time performance monitoring and alerting system for agents.
    Tracks metrics, detects anomalies, and provides optimization recommendations.
    """

    def __init__(self, agent_registry: AgentRegistry):
        self.registry = agent_registry
        self.agent_profiles: Dict[str, AgentPerformanceProfile] = {}
        self.global_metrics: Dict[MetricType, deque] = {
            mt: deque(maxlen=5000) for mt in MetricType
        }
        self.alerts: List[PerformanceAlert] = []
        self.alert_callbacks: List[Callable] = []

        # Monitoring configuration
        self.monitoring_interval = 30  # seconds
        self.alert_thresholds = self._default_thresholds()
        self.system_resources = {}

        # Control flags
        self.is_monitoring = False
        self.monitoring_task: Optional[asyncio.Task] = None

        # Make MetricType accessible as an instance attribute for compatibility
        self.MetricType = MetricType

        # Initialize profiles for existing agents
        self._initialize_profiles()

    def _default_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Default alert thresholds"""
        return {
            "task_success_rate": {"warning": 0.8, "critical": 0.6},
            "task_duration": {"warning": 3600, "critical": 7200},  # seconds
            "error_rate": {"warning": 0.1, "critical": 0.25},
            "resource_usage": {"warning": 0.8, "critical": 0.95},  # percentage
        }

    def _initialize_profiles(self):
        """Initialize performance profiles for all registered agents"""
        for agent_id in self.registry.agents.keys():
            self.agent_profiles[agent_id] = AgentPerformanceProfile(agent_id=agent_id)

    async def start_monitoring(self):
        """Start the performance monitoring system"""
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Performance monitoring started")

    async def stop_monitoring(self):
        """Stop the performance monitoring system"""
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Performance monitoring stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                await self._collect_system_metrics()
                await self._check_alerts()
                await self._cleanup_old_data()
                await asyncio.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.monitoring_interval)

    async def _collect_system_metrics(self):
        """Collect system-wide performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            await self.record_global_metric(
                MetricType.RESOURCE_USAGE, cpu_percent, {"resource": "cpu"}
            )

            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            await self.record_global_metric(
                MetricType.RESOURCE_USAGE, memory_percent, {"resource": "memory"}
            )

            # Disk usage
            disk = psutil.disk_usage(os.sep)
            disk_percent = disk.percent
            await self.record_global_metric(
                MetricType.RESOURCE_USAGE, disk_percent, {"resource": "disk"}
            )

            self.system_resources = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "timestamp": datetime.now(),
            }

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")

    async def record_agent_metric(
        self,
        agent_id: str,
        metric_type: MetricType,
        value: float,
        task_id: Optional[str] = None,
        metadata: Dict[str, Any] = None,
    ):
        """Record a metric for a specific agent"""
        if metadata is None:
            metadata = {}

        metric = PerformanceMetric(
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now(),
            agent_id=agent_id,
            task_id=task_id,
            metadata=metadata,
        )

        if agent_id not in self.agent_profiles:
            self.agent_profiles[agent_id] = AgentPerformanceProfile(agent_id=agent_id)

        self.agent_profiles[agent_id].add_metric(metric)

        # Also record globally
        await self.record_global_metric(metric_type, value, metadata)

        # Check for alerts
        await self._check_metric_alerts(agent_id, metric)

    async def record_global_metric(
        self, metric_type: MetricType, value: float, metadata: Dict[str, Any] = None
    ):
        """Record a global system metric"""
        if metadata is None:
            metadata = {}

        metric = PerformanceMetric(
            metric_type=metric_type, value=value, timestamp=datetime.now(), metadata=metadata
        )

        self.global_metrics[metric_type].append(metric)

    async def _check_metric_alerts(self, agent_id: str, metric: PerformanceMetric):
        """Check if a metric triggers an alert"""
        thresholds = self.alert_thresholds.get(metric.metric_type.value, {})

        alert_level = None
        if metric.value >= thresholds.get("critical", float("inf")):
            alert_level = AlertLevel.CRITICAL
        elif metric.value >= thresholds.get("warning", float("inf")):
            alert_level = AlertLevel.WARNING

        if alert_level:
            alert = PerformanceAlert(
                alert_id=f"{metric.metric_type.value}_{agent_id}_{int(datetime.now().timestamp())}",
                level=alert_level,
                message=f"{metric.metric_type.value} threshold exceeded for agent {agent_id}",
                agent_id=agent_id,
                metric_type=metric.metric_type,
                threshold_value=thresholds.get(alert_level.value, 0.0),
                actual_value=metric.value,
            )

            self.alerts.append(alert)
            self.agent_profiles[agent_id].alerts.append(alert)

            # Trigger callbacks
            for callback in self.alert_callbacks:
                try:
                    await callback(alert)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")

            logger.warning(f"🚨 {alert_level.value.upper()} ALERT: {alert.message}")

    async def _check_alerts(self):
        """Check for system-wide alerts"""
        # Check agent health (agents that haven't reported metrics recently)
        cutoff = datetime.now() - timedelta(minutes=30)

        for agent_id, profile in self.agent_profiles.items():
            if profile.last_updated < cutoff:
                agent = self.registry.agents.get(agent_id)
                if agent and agent.status.name == "ACTIVE":
                    alert = PerformanceAlert(
                        alert_id=f"health_{agent_id}_{int(datetime.now().timestamp())}",
                        level=AlertLevel.WARNING,
                        message=f"Agent {agent_id} has not reported metrics recently",
                        agent_id=agent_id,
                    )
                    self.alerts.append(alert)
                    logger.warning(f"🚨 HEALTH ALERT: Agent {agent_id} may be unresponsive")

    async def _cleanup_old_data(self):
        """Clean up old performance data"""
        cutoff = datetime.now() - timedelta(days=7)

        # Clean global metrics
        for metric_type, metrics in self.global_metrics.items():
            while metrics and metrics[0].timestamp < cutoff:
                metrics.popleft()

        # Clean agent alerts (keep only recent ones)
        alert_cutoff = datetime.now() - timedelta(hours=24)
        self.alerts = [a for a in self.alerts if a.timestamp > alert_cutoff]

        for profile in self.agent_profiles.values():
            profile.alerts = [a for a in profile.alerts if a.timestamp > alert_cutoff]

    def add_alert_callback(self, callback: Callable):
        """Add a callback for alert notifications"""
        self.alert_callbacks.append(callback)

    def get_agent_performance_report(self, agent_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive performance report for an agent"""
        if agent_id not in self.agent_profiles:
            return {"error": "Agent not found"}

        profile = self.agent_profiles[agent_id]

        report = {
            "agent_id": agent_id,
            "time_window_hours": hours,
            "metrics": {},
            "alerts": [self._alert_to_dict(a) for a in profile.alerts[-10:]],  # Last 10 alerts
            "last_updated": profile.last_updated.isoformat(),
        }

        # Calculate stats for each metric type
        for metric_type in MetricType:
            stats = profile.calculate_stats(metric_type, hours)
            report["metrics"][metric_type.value] = stats

        return report

    def get_system_performance_report(self) -> Dict[str, Any]:
        """Get system-wide performance report"""
        report = {
            "system_resources": self.system_resources,
            "agent_count": len(self.agent_profiles),
            "active_alerts": len(
                [a for a in self.alerts if a.timestamp > datetime.now() - timedelta(hours=1)]
            ),
            "global_metrics": {},
        }

        # Global metric stats
        for metric_type in MetricType:
            metrics = list(self.global_metrics[metric_type])
            if metrics:
                values = [m.value for m in metrics]
                report["global_metrics"][metric_type.value] = {
                    "count": len(values),
                    "average": statistics.mean(values),
                    "min": min(values),
                    "max": max(values),
                    "latest": values[-1] if values else 0.0,
                }

        return report

    def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_alerts = [a for a in self.alerts if a.timestamp > cutoff]
        return [self._alert_to_dict(a) for a in recent_alerts]

    def _alert_to_dict(self, alert: PerformanceAlert) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            "alert_id": alert.alert_id,
            "level": alert.level.value,
            "message": alert.message,
            "agent_id": alert.agent_id,
            "metric_type": alert.metric_type.value if alert.metric_type else None,
            "threshold_value": alert.threshold_value,
            "actual_value": alert.actual_value,
            "timestamp": alert.timestamp.isoformat(),
        }

    def get_performance_recommendations(self, agent_id: str) -> List[str]:
        """Get performance optimization recommendations for an agent"""
        if agent_id not in self.agent_profiles:
            return ["Agent not found"]

        profile = self.agent_profiles[agent_id]
        recommendations = []

        # Analyze task success rate
        success_stats = profile.calculate_stats(MetricType.TASK_SUCCESS_RATE)
        if success_stats["count"] > 0 and success_stats["average"] < 0.8:
            recommendations.append(
                "Consider additional training for task types with low success rates"
            )

        # Analyze task duration
        duration_stats = profile.calculate_stats(MetricType.TASK_DURATION)
        if duration_stats["count"] > 0 and duration_stats["average"] > 1800:  # 30 minutes
            recommendations.append(
                "Tasks are taking longer than expected - consider specialization refinement"
            )

        # Check for error patterns
        error_stats = profile.calculate_stats(MetricType.ERROR_RATE)
        if error_stats["count"] > 0 and error_stats["average"] > 0.1:
            recommendations.append(
                "High error rate detected - review error handling and capabilities"
            )

        # Check recent alerts
        recent_alerts = [
            a for a in profile.alerts if a.timestamp > datetime.now() - timedelta(hours=24)
        ]
        if recent_alerts:
            recommendations.append(f"Address {len(recent_alerts)} recent performance alerts")

        if not recommendations:
            recommendations.append("Performance is within acceptable parameters")

        return recommendations


# Global performance monitor instance
performance_monitor = PerformanceMonitor(AgentRegistry())
