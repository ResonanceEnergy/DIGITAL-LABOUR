#!/usr/bin/env python3
"""
BIT RAGE LABOUR CPU Regulator & Task Manager
Intelligent CPU management and task scheduling system for optimal performance
"""

import psutil
import threading
import time
import logging
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import queue
import signal
import sys

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    """TaskPriority handler."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


class TaskStatus(Enum):
    """TaskStatus handler."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

@dataclass
class Task:
    """Represents a task in the task manager"""
    id: str
    name: str
    priority: TaskPriority
    function: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    cpu_limit: Optional[float] = None  # CPU usage limit as percentage
    memory_limit: Optional[float] = None  # Memory usage limit as percentage
    timeout: Optional[int] = None  # Timeout in seconds
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    process: Optional[psutil.Process] = None
    thread: Optional[threading.Thread] = None


class CPURegulator:
    """__init__ handler."""
    """Intelligent CPU regulator that monitors and controls system resources"""

    def __init__(self, target_cpu_percent: float = 80.0, memory_threshold: float = 85.0):
        self.target_cpu_percent = target_cpu_percent
        self.memory_threshold = memory_threshold
        self.is_regulating = False
        self.regulation_thread: Optional[threading.Thread] = None
        self.cpu_history: List[float] = []
        self.memory_history: List[float] = []
        self.history_size = 10
        # pid -> original nice value
        self.throttle_processes: Dict[int, float] = {}

        # CPU regulation settings
        self.cpu_check_interval = 2.0  # seconds
        self.throttle_threshold = 90.0  # CPU % to start throttling
        self.unthrottle_threshold = 70.0  # CPU % to stop throttling

        logger.info(
            f"CPU Regulator initialized - Target CPU: {target_cpu_percent}%, Memory threshold: {memory_threshold}%")

    def start_regulation(self):
        """Start the CPU regulation thread"""
        if self.is_regulating:
            logger.warning("CPU regulation already running")
            return

        self.is_regulating = True
        self.regulation_thread = threading.Thread(
            target=self._regulation_loop, daemon=True)
        self.regulation_thread.start()
        logger.info("CPU regulation started")

    def stop_regulation(self):
        """Stop the CPU regulation thread"""
        self.is_regulating = False
        if self.regulation_thread:
            self.regulation_thread.join(timeout=5)
        self._unthrottle_all_processes()
        logger.info("CPU regulation stopped")

    def _regulation_loop(self):
        """Main regulation loop"""
        while self.is_regulating:
            try:
                self._update_system_metrics()
                self._regulate_cpu_usage()
                self._regulate_memory_usage()
                time.sleep(self.cpu_check_interval)
            except Exception as e:
                logger.error(f"Regulation loop error: {e}")
                time.sleep(self.cpu_check_interval)

    def _update_system_metrics(self):
        """Update CPU and memory usage history"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent

        self.cpu_history.append(cpu_percent)
        self.memory_history.append(memory_percent)

        # Keep history size limited
        if len(self.cpu_history) > self.history_size:
            self.cpu_history.pop(0)
        if len(self.memory_history) > self.history_size:
            self.memory_history.pop(0)

    def _regulate_cpu_usage(self):
        """Regulate CPU usage by throttling processes if needed"""
        current_cpu = self.cpu_history[-1] if self.cpu_history else 0

        if current_cpu > self.throttle_threshold:
            self._throttle_high_cpu_processes()
        elif current_cpu < self.unthrottle_threshold:
            self._unthrottle_processes()

    def _regulate_memory_usage(self):
        """Regulate memory usage by killing or warning high-memory processes"""
        current_memory = self.memory_history[-1] if self.memory_history else 0

        if current_memory > self.memory_threshold:
            logger.warning(
                f"High memory usage detected: {current_memory:.1f}%")
            self._kill_high_memory_processes()

    def _throttle_high_cpu_processes(self):
        """Throttle processes that are using too much CPU"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'cpu_percent', 'name']):
                try:
                    if proc.info['cpu_percent'] > 20.0:  # Processes using >20% CPU
                        processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort by CPU usage descending
            processes.sort(key=lambda p: p.info['cpu_percent'], reverse=True)

            # Throttle top CPU consumers
            for proc in processes[:3]:  # Throttle top 3
                pid = proc.info['pid']
                if pid not in self.throttle_processes:
                    try:
                        ps_proc = psutil.Process(pid)
                        original_nice = ps_proc.nice()
                        self.throttle_processes[pid] = original_nice

                        # Increase nice value (lower priority) on Unix-like systems
                        if os.name != 'nt':
                            # Max nice is 19
                            ps_proc.nice(min(original_nice + 10, 19))
                            logger.info(
                                f"Throttled process {pid} ({proc.info['name']}) - CPU: {proc.info['cpu_percent']:.1f}%")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

        except Exception as e:
            logger.error(f"Error throttling processes: {e}")

    def _unthrottle_processes(self):
        """Restore normal priority to throttled processes"""
        to_remove = []
        for pid, original_nice in self.throttle_processes.items():
            try:
                ps_proc = psutil.Process(pid)
                ps_proc.nice(original_nice)
                to_remove.append(pid)
                logger.info(f"Unthrottled process {pid}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                to_remove.append(pid)

        for pid in to_remove:
            del self.throttle_processes[pid]

    def _unthrottle_all_processes(self):
        """Unthrottle all processes"""
        for pid, original_nice in self.throttle_processes.items():
            try:
                ps_proc = psutil.Process(pid)
                ps_proc.nice(original_nice)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        self.throttle_processes.clear()

    def _kill_high_memory_processes(self):
        """Kill processes using excessive memory"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'memory_percent', 'name']):
                try:
                    if proc.info['memory_percent'] > 15.0:  # Processes using >15% memory
                        processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort by memory usage descending
            processes.sort(
                key=lambda p: p.info['memory_percent'], reverse=True)

            # Kill top memory consumer if memory is critical
            if self.memory_history[-1] > 95.0 and processes:
                proc = processes[0]
                pid = proc.info['pid']
                try:
                    ps_proc = psutil.Process(pid)
                    ps_proc.kill()
                    logger.warning(
                        f"Killed high-memory process {pid} ({proc.info['name']}) - Memory: {proc.info['memory_percent']:.1f}%")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        except Exception as e:
            logger.error(f"Error killing high-memory processes: {e}")

    def get_regulation_status(self) -> Dict[str, Any]:
        """Get current regulation status"""
        return {
            "is_regulating": self.is_regulating,
            "current_cpu": self.cpu_history[-1] if self.cpu_history else 0,
            "current_memory": self.memory_history[-1] if self.memory_history else 0,
            "throttled_processes": len(self.throttle_processes),
            "target_cpu": self.target_cpu_percent,
            "memory_threshold": self.memory_threshold
        }

class TaskManager:
    """Intelligent task manager with priority scheduling and resource management"""

    def __init__(self, max_concurrent_tasks: int=4,
                 cpu_regulator: Optional[CPURegulator]=None):
        self.tasks: Dict[str, Task] = {}
        self.task_queue = queue.PriorityQueue()
        self.running_tasks: Dict[str, Task] = {}
        self.completed_tasks: Dict[str, Task] = {}
        self.failed_tasks: Dict[str, Task] = {}

        self.max_concurrent_tasks = max_concurrent_tasks
        self.cpu_regulator = cpu_regulator
        self.executor = ThreadPoolExecutor(
            max_workers=max_concurrent_tasks, thread_name_prefix="TaskManager")

        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.monitor_thread: Optional[threading.Thread] = None

        # Task statistics
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "avg_completion_time": 0.0
        }

        logger.info(
            f"Task Manager initialized - Max concurrent tasks: {max_concurrent_tasks}")

    def start(self):
        """Start the task manager"""
        if self.is_running:
            logger.warning("Task manager already running")
            return

        self.is_running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop, daemon=True)
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True)

        self.scheduler_thread.start()
        self.monitor_thread.start()

        logger.info("Task manager started")

    def stop(self):
        """Stop the task manager"""
        self.is_running = False

        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        self.executor.shutdown(wait=True)

        # Cancel running tasks
        for task_id, task in self.running_tasks.items():
            self._cancel_task(task)

        logger.info("Task manager stopped")

    def add_task(self, task: Task) -> str:
        """Add a task to the manager"""
        self.tasks[task.id] = task
        self.stats["total_tasks"] += 1

        # Add to queue with priority
        priority_value = task.priority.value
        self.task_queue.put((priority_value, task.created_at, task.id))

        logger.info(
            f"Added task: {task.name} (ID: {task.id}, Priority: {task.priority.name})")
        return task.id

    def create_task(self, name: str, priority: TaskPriority,
                     function: Callable, *args, **kwargs) ->str:
        """Create and add a task"""
        task_id = f"{name}_{int(time.time() * 1000)}"
        task = Task(
            id=task_id,
            name=name,
            priority=priority,
            function=function,
            args=args,
            kwargs=kwargs
        )
        return self.add_task(task)

    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                # Check if we can run more tasks
                if len(self.running_tasks) < self.max_concurrent_tasks:
                    self._schedule_next_task()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                time.sleep(1)

    def _schedule_next_task(self):
        """Schedule the next task from the queue"""
        try:
            if self.task_queue.empty():
                return

            priority, created_at, task_id = self.task_queue.get_nowait()
            task = self.tasks.get(task_id)

            if not task or task.status != TaskStatus.PENDING:
                return

            # Check dependencies
            if not self._check_dependencies(task):
                # Put back in queue if dependencies not met
                self.task_queue.put((priority, created_at, task_id))
                return

            # Check resource limits
            if not self._check_resource_limits(task):
                # Put back in queue if resources not available
                self.task_queue.put((priority, created_at, task_id))
                return

            # Start the task
            self._start_task(task)

        except queue.Empty:
            pass
        except Exception as e:
            logger.error(f"Error scheduling task: {e}")

    def _check_dependencies(self, task: Task) -> bool:
        """Check if task dependencies are met"""
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True

    def _check_resource_limits(self, task: Task) -> bool:
        """Check if system resources are available for the task"""
        if not self.cpu_regulator:
            return True

        status = self.cpu_regulator.get_regulation_status()

        # Check CPU limit
        if task.cpu_limit and status["current_cpu"] > task.cpu_limit:
            return False

        # Check memory limit
        if task.memory_limit and status["current_memory"] > task.memory_limit:
            return False

        return True

    def _start_task(self, task: Task):
        """Start executing a task"""
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        self.running_tasks[task.id] = task

        # Submit to thread pool
        future = self.executor.submit(self._execute_task, task)
        future.add_done_callback(lambda f: self._task_completed(task.id, f))

        logger.info(f"Started task: {task.name} (ID: {task.id})")

    def _execute_task(self, task: Task) -> Any:
        """Execute a task function"""
        try:
            # Set process reference for monitoring
            task.process = psutil.Process()

            result = task.function(*task.args, **task.kwargs)
            return result
        except Exception as e:
            raise e

    def _task_completed(self, task_id: str, future):
        """Handle task completion"""
        task = self.running_tasks.pop(task_id, None)
        if not task:
            return

        task.completed_at = time.time()

        try:
            result = future.result()
            task.status = TaskStatus.COMPLETED
            task.result = result
            self.completed_tasks[task.id] = task
            self.stats["completed_tasks"] += 1

            # Update average completion time
            completion_time = task.completed_at - task.started_at
            self.stats["avg_completion_time"] = (
                (self.stats["avg_completion_time"] * \
                 (self.stats["completed_tasks"] - 1)) + completion_time
            ) / self.stats["completed_tasks"]

            logger.info(
                f"Completed task: {task.name} (ID: {task.id}) in {completion_time:.2f}s")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self.failed_tasks[task.id] = task
            self.stats["failed_tasks"] += 1

            logger.error(
                f"Failed task: {task.name} (ID: {task.id}) - Error: {e}")

    def _monitor_loop(self):
        """Monitor running tasks and enforce limits"""
        while self.is_running:
            try:
                current_time = time.time()

                for task_id, task in list(self.running_tasks.items()):
                    # Check timeout
                    if task.timeout and task.started_at:
                        if current_time - task.started_at > task.timeout:
                            logger.warning(f"Task {task.name} timed out")
                            self._cancel_task(task)
                            continue

                    # Check resource limits
                    if task.process:
                        try:
                            cpu_percent = task.process.cpu_percent()
                            memory_percent = task.process.memory_percent()

                            if task.cpu_limit and cpu_percent > task.cpu_limit:
                                logger.warning(
                                    f"Task {task.name} exceeded CPU limit ({cpu_percent:.1f}% > {task.cpu_limit}%)")
                                self._cancel_task(task)
                                continue

                            if task.memory_limit and memory_percent > task.memory_limit:
                                logger.warning(
                                    f"Task {task.name} exceeded memory limit ({memory_percent:.1f}% > {task.memory_limit}%)")
                                self._cancel_task(task)
                                continue

                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass

                time.sleep(5)  # Monitor every 5 seconds

            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                time.sleep(5)

    def _cancel_task(self, task: Task):
        """Cancel a running task"""
        task.status = TaskStatus.CANCELLED
        self.failed_tasks[task.id] = task

        # Note: ThreadPoolExecutor doesn't support cancelling individual tasks easily
        # In a production system, you'd want to implement proper cancellation

        logger.info(f"Cancelled task: {task.name} (ID: {task.id})")

    def get_status(self) -> Dict[str, Any]:
        """Get task manager status"""
        return {
            "is_running": self.is_running,
            "queued_tasks": self.task_queue.qsize(),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "stats": self.stats
        }

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        task = self.tasks.get(task_id)
        if not task:
            return None

        return {
            "id": task.id,
            "name": task.name,
            "status": task.status.value,
            "priority": task.priority.name,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "result": task.result,
            "error": task.error
        }

class CPUAndTaskManager:
    """Integrated CPU Regulator and Task Manager"""

    def __init__(self):
        self.cpu_regulator = CPURegulator()
        self.task_manager = TaskManager(cpu_regulator=self.cpu_regulator)
        self.is_running = False

        logger.info("CPU and Task Manager initialized")

    def start(self):
        """Start both CPU regulator and task manager"""
        if self.is_running:
            logger.warning("CPU and Task Manager already running")
            return

        self.cpu_regulator.start_regulation()
        self.task_manager.start()
        self.is_running = True

        logger.info("CPU and Task Manager started")

    def stop(self):
        """Stop both CPU regulator and task manager"""
        self.is_running = False
        self.task_manager.stop()
        self.cpu_regulator.stop_regulation()

        logger.info("CPU and Task Manager stopped")

    def add_task(self, name: str, priority: TaskPriority, function: Callable,
                *args, **kwargs) -> str:
        """Add a task to the task manager"""
        return self.task_manager.create_task(
            name, priority, function, *args, **kwargs)

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status"""
        return {
            "cpu_regulator": self.cpu_regulator.get_regulation_status(),
            "task_manager": self.task_manager.get_status(),
            "overall_status": "running" if self.is_running else "stopped"
        }

    def display_dashboard(self):
        """Display the CPU and Task Manager dashboard"""
        status = self.get_status()

        print("\n🚀 BIT RAGE LABOUR CPU & Task Manager Dashboard")
        print("=" * 60)

        # CPU Regulator Status
        cpu_status = status["cpu_regulator"]
        print("\n🎛️ CPU REGULATOR:")
        print(
            f"   Status: {'🟢 Active' if cpu_status['is_regulating'] else '🔴 Inactive'}")
        print(f"   Current CPU: {cpu_status['current_cpu']:.1f}%")
        print(f"   Current Memory: {cpu_status['current_memory']:.1f}%")
        print(f"   Target CPU: {cpu_status['target_cpu']:.1f}%")
        print(f"   Memory Threshold: {cpu_status['memory_threshold']:.1f}%")
        print(f"   Throttled Processes: {cpu_status['throttled_processes']}")

        # Task Manager Status
        tm_status = status["task_manager"]
        print("\n📋 TASK MANAGER:")
        print(
            f"   Status: {'🟢 Active' if tm_status['is_running'] else '🔴 Inactive'}")
        print(f"   Queued Tasks: {tm_status['queued_tasks']}")
        print(f"   Running Tasks: {tm_status['running_tasks']}")
        print(f"   Completed Tasks: {tm_status['completed_tasks']}")
        print(f"   Failed Tasks: {tm_status['failed_tasks']}")
        print(f"   Max Concurrent: {tm_status['max_concurrent_tasks']}")

        # Statistics
        stats = tm_status["stats"]
        print("\n📊 STATISTICS:")
        print(f"   Total Tasks: {stats['total_tasks']}")
        print(
            f"   Success Rate: {(stats['completed_tasks'] / max(stats['total_tasks'], 1)) * 100:.1f}%")
        print(f"   Avg Completion Time: {stats['avg_completion_time']:.2f}s")

        print("\n💡 SYSTEM HEALTH:")
        cpu_ok = cpu_status['current_cpu'] < cpu_status['target_cpu']
        mem_ok = cpu_status['current_memory'] < cpu_status['memory_threshold']
        tasks_ok = tm_status['failed_tasks'] == 0

        if cpu_ok and mem_ok and tasks_ok:
            print("   ✅ All systems operating normally")
        else:
            if not cpu_ok:
                print("   ⚠️  High CPU usage detected")
            if not mem_ok:
                print("   ⚠️  High memory usage detected")
            if not tasks_ok:
                print(f"   ⚠️  {tm_status['failed_tasks']} failed tasks")

def main():
    """Main function for CPU and Task Manager"""
    import argparse

    parser = argparse.ArgumentParser(
        description="BIT RAGE LABOUR CPU Regulator & Task Manager")
    parser.add_argument(
        "command", choices=["start", "stop", "status", "dashboard"],
        help="Command to execute")
    parser.add_argument("--cpu-target", type=float, default=80.0,
                       help="Target CPU percentage (default: 80.0)")
    parser.add_argument("--memory-threshold", type=float, default=85.0,
                       help="Memory threshold percentage (default: 85.0)")
    parser.add_argument("--max-tasks", type=int, default=4,
                       help="Maximum concurrent tasks (default: 4)")

    args = parser.parse_args()

    manager = CPUAndTaskManager()
    manager.cpu_regulator.target_cpu_percent = args.cpu_target
    manager.cpu_regulator.memory_threshold = args.memory_threshold
    manager.task_manager.max_concurrent_tasks = args.max_tasks

    if args.command == "start":
        print("🚀 Starting CPU Regulator & Task Manager...")
        manager.start()

        # Keep running until interrupted
        try:
            while True:
                time.sleep(1)
                if not manager.is_running:
                    break
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user")
        finally:
            manager.stop()

    elif args.command == "stop":
        print("🛑 Stopping CPU Regulator & Task Manager...")
        manager.stop()

    elif args.command == "status":
        status = manager.get_status()
        print(json.dumps(status, indent=2))

    elif args.command == "dashboard":
        if manager.is_running:
            manager.display_dashboard()
        else:
            print("❌ CPU and Task Manager is not running")
            print("   Use 'start' command to begin monitoring")

if __name__ == "__main__":
    main()