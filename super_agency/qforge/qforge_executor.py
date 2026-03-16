#!/usr/bin/env python3
"""
QFORGE Execution Layer - High-Performance Task Executor
Handles task execution, tool integration, and result aggregation

Features:
- VS Code integration for development tasks
- SASP communication with QUSAR
- Real-time performance monitoring
- Tool and API integration
- Result aggregation and reporting
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

# Import SASP components with fallback
try:
    from sasp_protocol import (
        SASPNetworkManager,
        SASPNode,
        SASPProtocol,
        SASPSecurityManager,
        SASPServer,
        get_sasp_network,
        get_sasp_protocol,
    )
    SASP_AVAILABLE = True
except ImportError:
    SASP_AVAILABLE = False
    SASPProtocol = None
    SASPNetworkManager = None

    # Stub classes for standalone mode
    class SASPSecurityManager:
        """Stub security manager for standalone mode"""
        def __init__(self, key: str):
            self.key = key

    class SASPServer:
        """Stub SASP server for standalone mode"""
        def __init__(self, host, port, security_manager, use_tls=False):
            self.host = host
            self.port = port
            self.handlers = {}
            self._running = False
            self._connections = []

        def register_handler(self, msg_type: str, handler):
            self.handlers[msg_type] = handler

        def start(self):
            """Start the stub server (logs only in standalone mode)"""
            self._running = True
            logger.info(
                f"[Standalone] SASP stub server started on {self.host}:{self.port}")

        def stop(self):
            """Stop the stub server"""
            self._running = False
            self._connections.clear()
            logger.info("[Standalone] SASP stub server stopped")

        def accept_connections(self):
            """Accept connections (no-op in standalone mode)"""
            if not self._running:
                logger.warning(
                    "[Standalone] Cannot accept connections - server not running")
                return
            logger.debug(
                "[Standalone] Ready to accept connections (stub mode)")

    logger = logging.getLogger(__name__)
    logger.info("SASP Protocol not available - running in standalone mode")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - QFORGE - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ExecutionTask:
    """Task to be executed by QFORGE"""
    task_id: str
    action: str
    target: str
    parameters: Dict[str, Any]
    priority: str
    status: str = "pending"
    result: Optional[Any] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

class TaskExecutor:
    """Executes tasks with high performance"""

    def __init__(self):
        self.active_tasks: Dict[str, ExecutionTask] = {}
        self.completed_tasks: List[ExecutionTask] = []
        # Alias for completed_tasks
        self.task_history: List[ExecutionTask] = []
        self.task_queue = asyncio.Queue()

    async def execute_pending_tasks(self) -> Dict[str, Any]:
        """Execute all pending tasks in the queue"""
        tasks_executed = 0
        results = []

        while not self.task_queue.empty():
            task = await self.task_queue.get()
            result = await self.execute_task(task)
            results.append(result)
            tasks_executed += 1

        return {
            'tasks_executed': tasks_executed,
            'results': results,
            'status': 'completed'
        }

    async def optimize_performance(self) -> Dict[str, Any]:
        """Optimize system performance"""
        return await self._optimize_performance({})

    async def execute_task(self, task: ExecutionTask) -> Any:
        """Execute a single task"""
        task.status = "running"
        task.started_at = datetime.now().isoformat()

        logger.info(f"🚀 Executing task: {task.action} on {task.target}")

        try:
            if task.action == "analyze_data":
                result = await self._analyze_data(task.parameters)
            elif task.action == "generate_report":
                result = await self._generate_report(task.parameters)
            elif task.action == "collect_intelligence":
                result = await self._collect_intelligence(task.parameters)
            elif task.action == "diagnose_issues":
                result = await self._diagnose_issues(task.parameters)
            elif task.action == "optimize_performance":
                result = await self._optimize_performance(task.parameters)
            else:
                result = await self._execute_generic_task(task)

            task.status = "completed"
            task.result = result
            task.completed_at = datetime.now().isoformat()

            logger.info(f"✅ Task completed: {task.action}")
            return result

        except Exception as e:
            task.status = "failed"
            task.result = str(e)
            task.completed_at = datetime.now().isoformat()
            logger.error(f"❌ Task failed: {task.action} - {e}")
            return None

    async def _analyze_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze data task"""
        # Simulate data analysis
        await asyncio.sleep(2)  # Simulate processing time
        return {
            "analysis_type": "comprehensive",
            "insights": ["Trend identified", "Anomaly detected"],
            "confidence": 0.92
        }

    async def _generate_report(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate report task"""
        # Simulate report generation
        await asyncio.sleep(3)
        return {
            "report_type": "executive_summary",
            "sections": ["Executive Summary", "Key Findings", "Recommendations"],
            "generated_at": datetime.now().isoformat()
        }

    async def _collect_intelligence(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Collect intelligence data"""
        # Simulate intelligence gathering
        await asyncio.sleep(1)
        return {
            "sources_checked": 5,
            "intelligence_items": 12,
            "priority_items": 3
        }

    async def _diagnose_issues(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Diagnose system issues"""
        # Simulate diagnostics
        await asyncio.sleep(2)
        return {
            "issues_found": 2,
            "severity": "medium",
            "recommendations": ["Update configuration", "Restart service"]
        }

    async def _optimize_performance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize system performance"""
        # Simulate optimization
        await asyncio.sleep(4)
        return {
            "optimizations_applied": 5,
            "performance_improvement": "15%",
            "resource_efficiency": "improved"
        }

    async def _execute_generic_task(self, task: ExecutionTask) -> Dict[str, Any]:
        """Execute generic task using subprocess"""
        try:
            # Execute command if it's a system command
            if task.action.startswith("run_"):
                command = task.action[4:]  # Remove "run_" prefix
                result = subprocess.run(
                    command.split(),
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                return {
                    "command": command,
                    "return_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            else:
                return {"status": "unknown_action", "action": task.action}

        except Exception as e:
            return {"status": "error", "error": str(e)}

class PerformanceMonitor:
    """Monitors execution performance"""

    def __init__(self):
        self.metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "avg_execution_time": 0,
            "active_tasks": 0,
            "cpu_usage": 0,
            "memory_usage": 0
        }

    def update_metrics(self, task: ExecutionTask):
        """Update metrics after task completion"""
        if task.status == "completed":
            self.metrics["tasks_completed"] += 1
        elif task.status == "failed":
            self.metrics["tasks_failed"] += 1

        self.metrics["active_tasks"] = len(
            [t for t in self.metrics if t.status == "running"])

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report"""
        success_rate = 0
        if self.metrics["tasks_completed"] + self.metrics["tasks_failed"] > 0:
            success_rate = self.metrics["tasks_completed"] / (
                self.metrics["tasks_completed"] + self.metrics["tasks_failed"])

        return {
            "tasks_completed": self.metrics["tasks_completed"],
            "tasks_failed": self.metrics["tasks_failed"],
            "success_rate": success_rate,
            "active_tasks": self.metrics["active_tasks"],
            "system_health": "good" if success_rate > 0.8 else "needs_attention"
        }

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        try:
            import psutil
            self.metrics["cpu_usage"] = psutil.cpu_percent()
            self.metrics["memory_usage"] = psutil.virtual_memory().percent
        except ImportError:
            pass
        return self.metrics


class QFORGEExecutor:
    """Main QFORGE execution component"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8888):
        self.host = host
        self.port = port

        # Initialize components
        self.task_executor = TaskExecutor()
        self.performance_monitor = PerformanceMonitor()
        self.sasp_server = None

        # Initialize SASP security
        self.security_manager = SASPSecurityManager(
            "qforge-secret-key-change-in-production")

        # Task management
        self.pending_goals: List[Dict[str, Any]] = []

        logger.info("🔨 QFORGE Executor initialized")

    def start(self):
        """Start QFORGE execution services"""
        # Start SASP server
        self.sasp_server = SASPServer(
            self.host,
            self.port,
            self.security_manager,
            use_tls=False  # For development
        )

        # Register message handlers
        self.sasp_server.register_handler('ping', self._handle_ping)
        self.sasp_server.register_handler('task', self._handle_task)
        self.sasp_server.register_handler(
            'status_request', self._handle_status_request)

        # Start server
        self.sasp_server.start()

        logger.info(f"🚀 QFORGE started on {self.host}:{self.port}")

    def stop(self):
        """Stop QFORGE services"""
        if self.sasp_server:
            self.sasp_server.stop()
        logger.info("🛑 QFORGE stopped")

    def _handle_ping(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ping messages"""
        return {
            'response': 'pong',
            'timestamp': time.time(),
            'status': 'active'
        }

    def _handle_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task execution requests"""
        try:
            result = self.task_executor.execute_task(payload)
            return {
                'task_id': payload.get('task_id'),
                'status': 'completed',
                'result': result
            }
        except Exception as e:
            return {
                'task_id': payload.get('task_id'),
                'status': 'failed',
                'error': str(e)
            }

    def _handle_status_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status requests"""
        return {
            'status': 'active',
            'active_tasks': len(self.task_executor.active_tasks),
            'completed_tasks': len(self.task_executor.task_history),
            'performance': self.performance_monitor.get_system_metrics()
        }

    async def _process_goals(self, goals: List[Dict[str, Any]]):
        """Process goals received from QUSAR"""
        logger.info(f"🎯 Processing {len(goals)} goals from QUSAR")

        for goal in goals:
            tasks = goal.get("tasks", [])
            for task_data in tasks:
                task = ExecutionTask(
                    task_id=f"{goal['goal_id']}_{task_data['action']}",
                    action=task_data["action"],
                    target=task_data["target"],
                    parameters=task_data,
                    priority=goal.get("priority", "medium")
                )

                # Execute task
                result = await self.task_executor.execute_task(task)

                # Update performance metrics
                self.performance_monitor.update_metrics(task)

                logger.info(f"📊 Task result: {result}")

        # Send feedback to QUSAR
        await self._send_feedback_to_qusar(goals)

    async def _send_feedback_to_qusar(self, goals: List[Dict[str, Any]]):
        """Send execution feedback to QUSAR"""
        # This would use SASP client to send feedback
        # For now, just log the completion
        logger.info(f"📤 Feedback sent for {len(goals)} goals")

    async def run_maintenance_cycle(self):
        """Run periodic maintenance tasks"""
        while True:
            try:
                # Accept incoming SASP connections
                if hasattr(self, 'sasp_server') and self.sasp_server:
                    self.sasp_server.accept_connections()

                # Clean up completed tasks
                self._cleanup_completed_tasks()

                # Update performance metrics
                self._update_system_metrics()

                # Log status
                report = self.performance_monitor.get_performance_report()
                logger.info(
                    f"🔄 Maintenance cycle - Success rate: {report['success_rate']:.2%}")

            except Exception as e:
                logger.error(f"❌ Maintenance cycle error: {e}")

            await asyncio.sleep(5)  # Run every 5 seconds for responsiveness

    def _cleanup_completed_tasks(self):
        """Clean up old completed tasks"""
        # Move completed tasks to history and remove old ones
        current_time = datetime.now()
        tasks_to_remove = []

        for task_id, task in self.task_executor.active_tasks.items():
            if task.status in ["completed", "failed"]:
                # Keep tasks for 1 hour
                if task.completed_at:
                    completed_time = datetime.fromisoformat(task.completed_at)
                    if (current_time - completed_time).total_seconds() > 3600:
                        tasks_to_remove.append(task_id)

        for task_id in tasks_to_remove:
            del self.task_executor.active_tasks[task_id]

    def _update_system_metrics(self):
        """Update system performance metrics"""
        # This would integrate with system monitoring
        # For now, just update basic metrics
        pass

async def main():
    """Main QFORGE execution"""
    print("🔨 Starting QFORGE Execution Layer")

    executor = QFORGEExecutor()

    # Start services
    executor.start()

    # Start maintenance cycle
    await executor.run_maintenance_cycle()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Shutting down QFORGE...")
        # executor.stop() would be called here
