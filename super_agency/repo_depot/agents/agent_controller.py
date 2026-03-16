# REPO DEPOT AGENTS - Agent Controller

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import json

from .agent_registry import AgentRegistry, AgentStatus, AgentSpecialization
from .specialization_engine import SpecializationEngine
from .collaboration_framework import CollaborationFramework, CollaborationMode
from .performance_monitor import PerformanceMonitor, MetricType

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentTask:
    """Task for agent execution"""

    task_id: str
    description: str
    priority: TaskPriority
    required_specializations: List[AgentSpecialization]
    estimated_duration: int  # seconds
    dependencies: List[str] = field(default_factory=list)
    assigned_agent: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    collaboration_session: Optional[str] = None


@dataclass
class AgentControllerConfig:
    """Configuration for the agent controller"""

    max_concurrent_tasks: int = 10
    task_timeout: int = 3600  # 1 hour
    auto_scaling_enabled: bool = True
    collaboration_threshold: int = (
        3  # Tasks requiring this many specializations trigger collaboration
    )
    performance_monitoring_enabled: bool = True


class AgentController:
    """
    Central controller for agent orchestration, task assignment, and coordination.
    Integrates registry, specialization, collaboration, and performance monitoring.
    """

    def __init__(self, config: AgentControllerConfig = None):
        self.config = config or AgentControllerConfig()

        # Core components
        self.registry = AgentRegistry()
        self.specialization_engine = SpecializationEngine(self.registry)
        self.collaboration_framework = CollaborationFramework(self.registry)
        self.performance_monitor = PerformanceMonitor(self.registry)

        # Task management
        self.tasks: Dict[str, AgentTask] = {}
        self.active_tasks: Set[str] = set()
        self.task_queue: asyncio.Queue = asyncio.Queue()

        # Control flags
        self.is_running = False
        self.controller_task: Optional[asyncio.Task] = None

        # Initialize with existing agents
        self._register_existing_agents()

    def _register_existing_agents(self):
        """Register any existing agents from the registry"""
        # This would be populated from configuration or discovery
        pass

    async def start(self):
        """Start the agent controller"""
        self.is_running = True

        # Start subsystems
        await self.collaboration_framework.start()
        if self.config.performance_monitoring_enabled:
            await self.performance_monitor.start_monitoring()

        # Start main controller loop
        self.controller_task = asyncio.create_task(self._controller_loop())

        # Register alert callbacks
        self.performance_monitor.add_alert_callback(self._handle_performance_alert)

        logger.info("Agent controller started")

    async def stop(self):
        """Stop the agent controller"""
        self.is_running = False

        if self.controller_task:
            self.controller_task.cancel()
            try:
                await self.controller_task
            except asyncio.CancelledError:
                pass

        # Stop subsystems
        await self.collaboration_framework.stop()
        await self.performance_monitor.stop_monitoring()

        logger.info("Agent controller stopped")

    async def _controller_loop(self):
        """Main controller loop for task processing"""
        while self.is_running:
            try:
                # Process pending tasks
                await self._process_task_queue()

                # Check for task timeouts
                await self._check_task_timeouts()

                # Balance agent workload
                await self._balance_workload()

                # Brief pause
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error in controller loop: {e}")
                await asyncio.sleep(10)

    async def submit_task(
        self,
        description: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        required_specializations: List[AgentSpecialization] = None,
        estimated_duration: int = 1800,
    ) -> str:
        """Submit a new task for execution"""
        if required_specializations is None:
            required_specializations = [AgentSpecialization.IMPLEMENTATION]

        task_id = f"task_{int(datetime.now().timestamp())}_{len(self.tasks)}"

        task = AgentTask(
            task_id=task_id,
            description=description,
            priority=priority,
            required_specializations=required_specializations,
            estimated_duration=estimated_duration,
        )

        self.tasks[task_id] = task
        await self.task_queue.put(task_id)

        logger.info(f"Task submitted: {task_id} - {description}")
        return task_id

    async def _process_task_queue(self):
        """Process tasks from the queue"""
        # Check if we can handle more concurrent tasks
        if len(self.active_tasks) >= self.config.max_concurrent_tasks:
            return

        try:
            # Get next task (with timeout to avoid blocking)
            task_id = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
            task = self.tasks[task_id]

            # Assign task to agent(s)
            await self._assign_task(task)
            self.task_queue.task_done()

        except asyncio.TimeoutError:
            pass  # No tasks in queue
        except Exception as e:
            logger.error(f"Error processing task queue: {e}")

    async def _assign_task(self, task: AgentTask):
        """Assign a task to appropriate agent(s)"""
        # Check if task requires collaboration
        if len(task.required_specializations) >= self.config.collaboration_threshold:
            await self._assign_collaborative_task(task)
        else:
            await self._assign_single_agent_task(task)

    async def _assign_single_agent_task(self, task: AgentTask):
        """Assign task to a single agent"""
        # Use specialization engine to recommend best agent
        recommended_agent = self.specialization_engine.recommend_agent_for_task(
            task.description, [s.value for s in task.required_specializations]
        )

        if recommended_agent:
            await self._assign_to_agent(task, recommended_agent)
        else:
            logger.warning(f"No suitable agent found for task {task.task_id}")
            # Could implement task queuing or agent scaling here

    async def _assign_collaborative_task(self, task: AgentTask):
        """Assign task requiring multiple agents/collaboration"""
        # Find agents with required specializations
        participants = []
        for spec in task.required_specializations:
            agents = self.registry.get_agents_by_specialization(spec)
            active_agents = [a for a in agents if a.status == AgentStatus.ACTIVE]
            if active_agents:
                participants.extend(
                    [a.agent_id for a in active_agents[:2]]
                )  # Max 2 per specialization

        if len(participants) >= 2:
            # Create collaboration session
            session_id = await self.collaboration_framework.initiate_collaboration(
                initiator_id="controller",
                participants=list(set(participants)),  # Remove duplicates
                objective=task.description,
                mode=CollaborationMode.SEQUENTIAL,
            )

            task.collaboration_session = session_id
            task.status = TaskStatus.ASSIGNED
            self.active_tasks.add(task.task_id)

            logger.info(f"Collaborative task {task.task_id} assigned to session {session_id}")
        else:
            # Fall back to single agent assignment
            await self._assign_single_agent_task(task)

    async def _assign_to_agent(self, task: AgentTask, agent_id: str):
        """Assign task to specific agent"""
        task.assigned_agent = agent_id
        task.status = TaskStatus.ASSIGNED
        task.started_at = datetime.now()
        self.active_tasks.add(task.task_id)

        # Update agent status
        self.registry.update_agent_status(agent_id, AgentStatus.ACTIVE)

        # Record assignment metric
        await self.performance_monitor.record_agent_metric(
            agent_id,
            MetricType.TASK_DURATION,
            0.0,
            task.task_id,
            {"action": "assigned", "priority": task.priority.value},
        )

        logger.info(f"Task {task.task_id} assigned to agent {agent_id}")

    async def complete_task(
        self, task_id: str, result: Dict[str, Any] = None, error_message: str = None
    ):
        """Mark a task as completed"""
        if task_id not in self.tasks:
            logger.warning(f"Unknown task: {task_id}")
            return

        task = self.tasks[task_id]
        task.completed_at = datetime.now()
        task.result = result or {}
        task.error_message = error_message

        if error_message:
            task.status = TaskStatus.FAILED
        else:
            task.status = TaskStatus.COMPLETED

        # Remove from active tasks
        self.active_tasks.discard(task_id)

        # Update agent status and metrics
        if task.assigned_agent:
            agent = self.registry.agents.get(task.assigned_agent)
            if agent:
                # Update agent performance metrics
                duration = (
                    task.completed_at - (task.started_at or task.created_at)
                ).total_seconds()
                success = task.status == TaskStatus.COMPLETED

                await self.performance_monitor.record_agent_metric(
                    task.assigned_agent,
                    MetricType.TASK_SUCCESS_RATE,
                    1.0 if success else 0.0,
                    task_id,
                )
                await self.performance_monitor.record_agent_metric(
                    task.assigned_agent, MetricType.TASK_DURATION, duration, task_id
                )

                # Update specialization
                await self.specialization_engine.analyze_task_performance(
                    task.assigned_agent, task.description, success, duration
                )

                # Free up agent
                self.registry.update_agent_status(task.assigned_agent, AgentStatus.ACTIVE)

        # Clean up collaboration session if it exists
        if task.collaboration_session:
            # Session cleanup would be handled by collaboration framework
            pass

        logger.info(f"Task {task_id} completed with status: {task.status.value}")

    async def _check_task_timeouts(self):
        """Check for tasks that have exceeded timeout"""
        now = datetime.now()
        timeout_threshold = timedelta(seconds=self.config.task_timeout)

        for task_id in list(self.active_tasks):
            task = self.tasks[task_id]
            if task.started_at and (now - task.started_at) > timeout_threshold:
                logger.warning(f"Task {task_id} timed out")
                await self.complete_task(task_id, error_message="Task timeout")

    async def _balance_workload(self):
        """Balance workload across agents"""
        if not self.config.auto_scaling_enabled:
            return

        # Simple load balancing - could be enhanced
        agent_workloads = {}
        for agent_id, agent in self.registry.agents.items():
            if agent.status == AgentStatus.ACTIVE:
                workload = sum(
                    1
                    for t in self.tasks.values()
                    if t.assigned_agent == agent_id and t.status == TaskStatus.IN_PROGRESS
                )
                agent_workloads[agent_id] = workload

        # Log workload distribution
        if agent_workloads:
            avg_workload = sum(agent_workloads.values()) / len(agent_workloads)
            logger.debug(f"Average agent workload: {avg_workload:.2f}")

    async def _handle_performance_alert(self, alert):
        """Handle performance alerts"""
        logger.warning(f"Performance alert received: {alert.message}")

        # Could implement automatic remediation based on alert type
        if alert.agent_id:
            # Check if agent needs to be taken offline or reassigned
            if "unresponsive" in alert.message.lower():
                self.registry.update_agent_status(alert.agent_id, AgentStatus.ERROR)

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        task = self.tasks.get(task_id)
        if not task:
            return None

        return {
            "task_id": task.task_id,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "assigned_agent": task.assigned_agent,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "progress": self._calculate_task_progress(task),
            "collaboration_session": task.collaboration_session,
        }

    def _calculate_task_progress(self, task: AgentTask) -> float:
        """Calculate task progress percentage"""
        if task.status == TaskStatus.COMPLETED:
            return 100.0
        elif task.status == TaskStatus.FAILED:
            return 0.0
        elif task.status == TaskStatus.IN_PROGRESS and task.started_at:
            elapsed = (datetime.now() - task.started_at).total_seconds()
            estimated = task.estimated_duration
            return min(90.0, (elapsed / estimated) * 100.0)  # Cap at 90% until actually complete
        else:
            return 0.0

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        total_tasks = len(self.tasks)
        active_tasks = len(self.active_tasks)
        completed_tasks = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        failed_tasks = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)

        return {
            "is_running": self.is_running,
            "total_tasks": total_tasks,
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": (completed_tasks / total_tasks) if total_tasks > 0 else 0.0,
            "active_agents": sum(
                1 for a in self.registry.agents.values() if a.status == AgentStatus.ACTIVE
            ),
            "performance_stats": self.performance_monitor.get_system_performance_report(),
            "specialization_stats": self.specialization_engine.get_system_specialization_stats(),
            "active_sessions": len(self.collaboration_framework.get_active_sessions()),
        }

    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get list of pending tasks"""
        pending = [t for t in self.tasks.values() if t.status == TaskStatus.PENDING]
        return [self.get_task_status(t.task_id) for t in pending]

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or active task"""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        if task.status in [TaskStatus.PENDING, TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            self.active_tasks.discard(task_id)

            if task.assigned_agent:
                self.registry.update_agent_status(task.assigned_agent, AgentStatus.ACTIVE)

            logger.info(f"Task {task_id} cancelled")
            return True

        return False


# Global agent controller instance
agent_controller = AgentController()
