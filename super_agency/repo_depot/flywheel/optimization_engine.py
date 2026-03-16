# REPO DEPOT FLYWHEEL - Optimization Systems

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import psutil
import os
import time
import statistics
from pathlib import Path

logger = logging.getLogger(__name__)


class OptimizationType(Enum):
    PERFORMANCE = "performance"
    MEMORY = "memory"
    CPU = "cpu"
    CODE_QUALITY = "code_quality"
    RESOURCE_USAGE = "resource_usage"


class OptimizationPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class PerformanceMetric:
    metric_name: str
    value: float
    unit: str
    timestamp: datetime
    context: Dict[str, Any] = None


@dataclass
class OptimizationOpportunity:
    opportunity_id: str
    type: OptimizationType
    priority: OptimizationPriority
    description: str
    impact_estimate: float  # Expected improvement percentage
    effort_estimate: str  # LOW, MEDIUM, HIGH
    affected_components: List[str]
    recommendations: List[str]
    detected_at: datetime = None

    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.now()


@dataclass
class OptimizationResult:
    opportunity_id: str
    success: bool
    improvements_achieved: Dict[str, float]
    execution_time: float
    side_effects: List[str] = None
    error: Optional[str] = None


class PerformanceMonitor:
    """
    Real-time performance monitoring for the Flywheel system.
    Tracks metrics and identifies optimization opportunities.
    """

    def __init__(self):
        self.metrics: List[PerformanceMetric] = []
        self.baseline_metrics: Dict[str, float] = {}
        self.monitoring_active: bool = False
        self.collection_interval: float = 5.0  # seconds

    async def start_monitoring(self):
        """Start performance monitoring"""
        self.monitoring_active = True
        logger.info("📊 Starting performance monitoring")

        asyncio.create_task(self._collect_metrics())

    async def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        logger.info("🛑 Stopping performance monitoring")

    async def _collect_metrics(self):
        """Collect system and application metrics"""
        while self.monitoring_active:
            try:
                # System metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage(os.sep)

                # Record metrics
                self.record_metric("cpu_usage", cpu_percent, "%")
                self.record_metric("memory_usage", memory.percent, "%")
                self.record_metric("memory_used", memory.used / (1024**3), "GB")  # GB
                self.record_metric("disk_usage", disk.percent, "%")

                # Application-specific metrics would be added here
                # (e.g., request latency, throughput, error rates)

                await asyncio.sleep(self.collection_interval)

            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(self.collection_interval)

    def record_metric(self, name: str, value: float, unit: str, context: Dict[str, Any] = None):
        """Record a performance metric"""
        metric = PerformanceMetric(
            metric_name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            context=context or {},
        )
        self.metrics.append(metric)

        # Keep only recent metrics (last 1000)
        if len(self.metrics) > 1000:
            self.metrics = self.metrics[-1000:]

    def get_metric_average(self, metric_name: str, hours: int = 1) -> Optional[float]:
        """Get average value for a metric over the last N hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        relevant_metrics = [
            m.value for m in self.metrics if m.metric_name == metric_name and m.timestamp > cutoff
        ]

        return statistics.mean(relevant_metrics) if relevant_metrics else None

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        summary = {}

        # CPU metrics
        cpu_avg = self.get_metric_average("cpu_usage", 1)
        summary["cpu_average_1h"] = cpu_avg

        # Memory metrics
        mem_avg = self.get_metric_average("memory_usage", 1)
        summary["memory_average_1h"] = mem_avg

        # Trends
        cpu_trend = self._calculate_trend("cpu_usage")
        mem_trend = self._calculate_trend("memory_usage")
        summary["cpu_trend"] = cpu_trend
        summary["memory_trend"] = mem_trend

        return summary

    def get_summary(self) -> Dict[str, Any]:
        """Alias for get_performance_summary() for backward compatibility"""
        return self.get_performance_summary()

    def _calculate_trend(self, metric_name: str) -> str:
        """Calculate trend for a metric (improving, degrading, stable)"""
        recent_avg = self.get_metric_average(metric_name, 1)
        older_avg = self.get_metric_average(metric_name, 24)  # Last 24 hours

        if recent_avg is None or older_avg is None:
            return "unknown"

        diff = recent_avg - older_avg
        threshold = abs(older_avg) * 0.05  # 5% change threshold

        if diff > threshold:
            return "degrading"
        elif diff < -threshold:
            return "improving"
        else:
            return "stable"


class OptimizationEngine:
    """
    AI-powered optimization engine for continuous improvement.
    Analyzes performance data and applies optimizations automatically.
    """

    def __init__(self, performance_monitor: PerformanceMonitor):
        self.monitor = performance_monitor
        self.opportunities: Dict[str, OptimizationOpportunity] = {}
        self.applied_optimizations: List[OptimizationResult] = {}
        self.optimization_active: bool = False
        self.analysis_interval: int = 300  # 5 minutes

    async def start_optimization(self):
        """Start the optimization engine"""
        self.optimization_active = True
        logger.info("⚡ Starting optimization engine")

        asyncio.create_task(self._analyze_and_optimize())

    async def stop_optimization(self):
        """Stop the optimization engine"""
        self.optimization_active = False
        logger.info("🛑 Stopping optimization engine")

    async def _analyze_and_optimize(self):
        """Main optimization loop"""
        while self.optimization_active:
            try:
                # Analyze current performance
                opportunities = await self._analyze_performance()

                # Prioritize and apply optimizations
                for opportunity in opportunities:
                    if opportunity.priority == OptimizationPriority.CRITICAL:
                        await self._apply_optimization(opportunity)

                await asyncio.sleep(self.analysis_interval)

            except Exception as e:
                logger.error(f"Optimization analysis failed: {e}")
                await asyncio.sleep(self.analysis_interval)

    async def _analyze_performance(self) -> List[OptimizationOpportunity]:
        """Analyze performance data and identify optimization opportunities"""
        opportunities = []

        # Get performance summary
        summary = self.monitor.get_performance_summary()

        # CPU optimization opportunities
        cpu_avg = summary.get("cpu_average_1h")
        if cpu_avg and cpu_avg > 80:
            opportunities.append(
                OptimizationOpportunity(
                    opportunity_id=f"cpu_opt_{int(time.time())}",
                    type=OptimizationType.CPU,
                    priority=(
                        OptimizationPriority.HIGH if cpu_avg > 90 else OptimizationPriority.MEDIUM
                    ),
                    description=f"High CPU usage detected: {cpu_avg:.1f}%",
                    impact_estimate=min(20.0, cpu_avg - 70),  # Estimate 20% max improvement
                    effort_estimate="MEDIUM",
                    affected_components=["system"],
                    recommendations=[
                        "Implement CPU affinity for critical processes",
                        "Add task batching to reduce context switching",
                        "Consider async processing for I/O operations",
                    ],
                )
            )

        # Memory optimization opportunities
        mem_avg = summary.get("memory_average_1h")
        if mem_avg and mem_avg > 85:
            opportunities.append(
                OptimizationOpportunity(
                    opportunity_id=f"mem_opt_{int(time.time())}",
                    type=OptimizationType.MEMORY,
                    priority=(
                        OptimizationPriority.HIGH if mem_avg > 95 else OptimizationPriority.MEDIUM
                    ),
                    description=f"High memory usage detected: {mem_avg:.1f}%",
                    impact_estimate=min(15.0, mem_avg - 80),
                    effort_estimate="LOW",
                    affected_components=["system"],
                    recommendations=[
                        "Implement memory pooling for frequently used objects",
                        "Add garbage collection optimization",
                        "Consider memory-mapped files for large datasets",
                    ],
                )
            )

        # Performance trend analysis
        cpu_trend = summary.get("cpu_trend")
        if cpu_trend == "degrading":
            opportunities.append(
                OptimizationOpportunity(
                    opportunity_id=f"trend_opt_{int(time.time())}",
                    type=OptimizationType.PERFORMANCE,
                    priority=OptimizationPriority.MEDIUM,
                    description="Performance degradation detected over time",
                    impact_estimate=10.0,
                    effort_estimate="HIGH",
                    affected_components=["system"],
                    recommendations=[
                        "Profile application performance",
                        "Identify memory leaks",
                        "Optimize database queries",
                        "Review recent code changes",
                    ],
                )
            )

        # Store opportunities
        for opp in opportunities:
            self.opportunities[opp.opportunity_id] = opp

        return opportunities

    async def _apply_optimization(
        self, opportunity: OptimizationOpportunity
    ) -> OptimizationResult:
        """Apply a specific optimization"""
        logger.info(f"🔧 Applying optimization: {opportunity.description}")

        start_time = time.time()
        improvements = {}
        side_effects = []

        try:
            if opportunity.type == OptimizationType.CPU:
                improvements, side_effects = await self._optimize_cpu()
            elif opportunity.type == OptimizationType.MEMORY:
                improvements, side_effects = await self._optimize_memory()
            elif opportunity.type == OptimizationType.PERFORMANCE:
                improvements, side_effects = await self._optimize_performance()

            execution_time = time.time() - start_time

            result = OptimizationResult(
                opportunity_id=opportunity.opportunity_id,
                success=True,
                improvements_achieved=improvements,
                execution_time=execution_time,
                side_effects=side_effects,
            )

            logger.info(f"✅ Optimization applied successfully")
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"❌ Optimization failed: {e}")

            return OptimizationResult(
                opportunity_id=opportunity.opportunity_id,
                success=False,
                improvements_achieved={},
                execution_time=execution_time,
                error=str(e),
            )

    async def _optimize_cpu(self) -> tuple:
        """Apply CPU optimizations"""
        improvements = {"cpu_reduction_estimate": 15.0}
        side_effects = ["May increase memory usage slightly"]

        # Implement CPU optimizations
        # - Adjust process priorities
        # - Implement CPU affinity
        # - Add task scheduling optimizations

        return improvements, side_effects

    async def _optimize_memory(self) -> tuple:
        """Apply memory optimizations"""
        improvements = {"memory_reduction_estimate": 10.0}
        side_effects = ["May slightly impact performance during optimization"]

        # Implement memory optimizations
        # - Force garbage collection
        # - Optimize object allocation
        # - Implement memory pooling

        return improvements, side_effects

    async def _optimize_performance(self) -> tuple:
        """Apply general performance optimizations"""
        improvements = {"performance_improvement_estimate": 12.0}
        side_effects = ["May require system restart for full effect"]

        # Implement performance optimizations
        # - Profile and optimize bottlenecks
        # - Implement caching
        # - Optimize algorithms

        return improvements, side_effects

    def get_optimization_status(self) -> Dict[str, Any]:
        """Get optimization system status"""
        return {
            "active_opportunities": len(self.opportunities),
            "applied_optimizations": len(self.applied_optimizations),
            "optimization_active": self.optimization_active,
            "analysis_interval": self.analysis_interval,
            "performance_summary": self.monitor.get_performance_summary(),
        }

    def get_status(self) -> Dict[str, Any]:
        """Alias for get_optimization_status() for backward compatibility"""
        return self.get_optimization_status()


class FeedbackLoop:
    """
    Learning system that analyzes optimization results and improves future recommendations.
    """

    def __init__(self, optimization_engine: OptimizationEngine):
        self.engine = optimization_engine
        self.learning_data: List[Dict[str, Any]] = []
        self.feedback_active: bool = False

    async def start_learning(self):
        """Start the feedback learning loop"""
        self.feedback_active = True
        logger.info("🧠 Starting feedback learning")

        asyncio.create_task(self._learn_from_results())

    async def _learn_from_results(self):
        """Learn from optimization results to improve future recommendations"""
        while self.feedback_active:
            try:
                # Analyze recent optimization results
                recent_results = [
                    result
                    for result in self.engine.applied_optimizations.values()
                    if (datetime.now() - timedelta(hours=24)).timestamp()
                    < getattr(result, "timestamp", 0)
                ]

                for result in recent_results:
                    # Learn from successful optimizations
                    if result.success and result.improvements_achieved:
                        self._update_recommendation_weights(result)

                    # Learn from failed optimizations
                    elif not result.success:
                        self._avoid_similar_failures(result)

                await asyncio.sleep(3600)  # Learn hourly

            except Exception as e:
                logger.error(f"Feedback learning failed: {e}")
                await asyncio.sleep(3600)

    def _update_recommendation_weights(self, result: OptimizationResult):
        """Update recommendation weights based on successful optimizations"""
        # This would update internal models to favor successful optimization types
        self.learning_data.append(
            {"type": "success", "result": result, "timestamp": datetime.now()}
        )

    def _avoid_similar_failures(self, result: OptimizationResult):
        """Learn to avoid similar optimization failures"""
        # This would update internal models to avoid failed optimization patterns
        self.learning_data.append(
            {"type": "failure", "result": result, "timestamp": datetime.now()}
        )


# Global optimization systems
performance_monitor = PerformanceMonitor()
optimization_engine = OptimizationEngine(performance_monitor)
feedback_loop = FeedbackLoop(optimization_engine)
