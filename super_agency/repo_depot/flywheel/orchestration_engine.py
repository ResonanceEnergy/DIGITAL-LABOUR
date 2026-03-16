# REPO DEPOT FLYWHEEL - Orchestration Engine

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FlywheelTask:
    task_id: str
    name: str
    description: str
    priority: TaskPriority
    phase: str
    assigned_agent: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class OrchestrationEngine:
    """
    Core orchestration engine for the REPO DEPOT Flywheel.
    Manages task scheduling, dependencies, and execution flow.
    """

    def __init__(self):
        self.tasks: Dict[str, FlywheelTask] = {}
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.completed_tasks: List[str] = []
        self.failed_tasks: List[str] = []
        self.max_concurrent_tasks: int = 5
        self.is_running: bool = False

    async def start_engine(self):
        """Start the orchestration engine"""
        self.is_running = True
        logger.info("🚀 Starting Flywheel Orchestration Engine")

        # Start task processor
        asyncio.create_task(self._process_task_queue())

        # Start dependency checker
        asyncio.create_task(self._check_dependencies())

    async def stop_engine(self):
        """Stop the orchestration engine"""
        self.is_running = False
        logger.info("🛑 Stopping Flywheel Orchestration Engine")

        # Cancel all running tasks
        for task_id, task in self.running_tasks.items():
            if not task.done():
                task.cancel()

    def add_task(self, task: FlywheelTask) -> str:
        """Add a task to the orchestration queue"""
        self.tasks[task.task_id] = task

        # Add to priority queue based on priority and dependencies
        priority_value = (task.priority.value, len(task.dependencies), task.created_at.timestamp())
        self.task_queue.put_nowait((priority_value, task.task_id))

        logger.info(f"📝 Added task: {task.name} ({task.task_id})")
        return task.task_id

    async def _process_task_queue(self):
        """Process tasks from the queue"""
        while self.is_running:
            try:
                # Check if we can run more tasks
                if len(self.running_tasks) >= self.max_concurrent_tasks:
                    await asyncio.sleep(1)
                    continue

                # Get next task
                try:
                    priority, task_id = self.task_queue.get_nowait()
                except asyncio.QueueEmpty:
                    await asyncio.sleep(1)
                    continue

                task = self.tasks.get(task_id)
                if not task:
                    continue

                # Check if dependencies are met
                if not self._dependencies_met(task):
                    # Re-queue task
                    self.task_queue.put_nowait((priority, task_id))
                    await asyncio.sleep(1)
                    continue

                # Start task execution
                asyncio.create_task(self._execute_task(task))

            except Exception as e:
                logger.error(f"Error processing task queue: {e}")
                await asyncio.sleep(5)

    def _dependencies_met(self, task: FlywheelTask) -> bool:
        """Check if all task dependencies are completed"""
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True

    async def _execute_task(self, task: FlywheelTask):
        """Execute a single task"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self.running_tasks[task.task_id] = asyncio.current_task()

        try:
            logger.info(f"▶️  Starting task: {task.name}")

            # Execute based on task type
            result = await self._run_task_logic(task)

            # Mark as completed
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            self.completed_tasks.append(task.task_id)

            logger.info(f"✅ Completed task: {task.name}")

        except Exception as e:
            logger.error(f"❌ Failed task: {task.name} - {e}")
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self.failed_tasks.append(task.task_id)

        finally:
            # Remove from running tasks
            self.running_tasks.pop(task.task_id, None)

    async def _run_task_logic(self, task: FlywheelTask) -> Any:
        """Execute the actual task logic based on task type"""
        if task.phase == "planning":
            return await self._execute_planning_task(task)
        elif task.phase == "construction":
            return await self._execute_construction_task(task)
        elif task.phase == "optimization":
            return await self._execute_optimization_task(task)
        elif task.phase == "deployment":
            return await self._execute_deployment_task(task)
        else:
            raise ValueError(f"Unknown task phase: {task.phase}")

    async def _execute_planning_task(self, task: FlywheelTask) -> Dict[str, Any]:
        """Execute planning phase tasks"""
        # Placeholder - integrate with planning agents
        await asyncio.sleep(2)  # Simulate work
        return {
            "phase": "planning",
            "task_type": task.metadata.get("task_type", "analysis"),
            "requirements": ["req1", "req2", "req3"],
            "estimated_effort": "medium",
        }

    async def _execute_construction_task(self, task: FlywheelTask) -> Dict[str, Any]:
        """Execute construction phase tasks"""
        # Placeholder - integrate with builder agents
        await asyncio.sleep(3)  # Simulate work
        return {
            "phase": "construction",
            "components_built": ["comp1", "comp2"],
            "code_generated": 150,
            "tests_added": 5,
        }

    async def _execute_optimization_task(self, task: FlywheelTask) -> Dict[str, Any]:
        """Execute optimization phase tasks"""
        # Placeholder - integrate with optimization systems
        await asyncio.sleep(2)  # Simulate work
        return {
            "phase": "optimization",
            "performance_improved": 25.5,
            "issues_fixed": 3,
            "recommendations": ["rec1", "rec2"],
        }

    async def _execute_deployment_task(self, task: FlywheelTask) -> Dict[str, Any]:
        """Execute deployment phase tasks"""
        # Placeholder - integrate with deployment systems
        await asyncio.sleep(1)  # Simulate work
        return {
            "phase": "deployment",
            "deployed_to": ["staging", "production"],
            "tests_passed": 95,
            "rollback_available": True,
        }

    async def _check_dependencies(self):
        """Periodically check for tasks that can now run due to completed dependencies"""
        while self.is_running:
            await asyncio.sleep(10)  # Check every 10 seconds

            # Re-queue tasks whose dependencies are now met
            pending_tasks = [t for t in self.tasks.values() if t.status == TaskStatus.PENDING]
            for task in pending_tasks:
                if self._dependencies_met(task):
                    # Task can now run - it should already be in queue
                    pass

    def get_engine_status(self) -> Dict[str, Any]:
        """Get current engine status"""
        return {
            "is_running": self.is_running,
            "total_tasks": len(self.tasks),
            "pending_tasks": len(
                [t for t in self.tasks.values() if t.status == TaskStatus.PENDING]
            ),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "queue_size": self.task_queue.qsize(),
        }

    def get_status(self) -> Dict[str, Any]:
        """Alias for get_engine_status() for backward compatibility"""
        return self.get_engine_status()


# Global orchestration engine instance
orchestration_engine = OrchestrationEngine()
