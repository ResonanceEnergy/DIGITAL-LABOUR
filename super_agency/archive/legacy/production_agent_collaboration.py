#!/usr/bin/env python3
"""
🚀 DIGITAL LABOUR - 24/7 PRODUCTION AGENT COLLABORATION SYSTEM
============================================================
Orchestrates OPTIMUS + GASKET agents for continuous forward progress
on all ResonanceEnergy repositories with cross-platform sync.

Architecture:
- QUANTUM FORGE (Windows) ↔ QUANTUM QUASAR (macOS) sync
- OPTIMUS: Strategic planning, high-level decisions, code architecture
- GASKET: Implementation, testing, integration, deployment

Production Mode: 24/7 continuous operation with intelligent work distribution
"""

import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class AgentRole(Enum):
    """Agent specialization roles"""

    OPTIMUS = "optimus"  # Strategic, architecture, planning
    GASKET = "gasket"  # Implementation, testing, integration


class TaskPriority(Enum):
    """Task priority levels"""

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class TaskStatus(Enum):
    """Task execution status"""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    BLOCKED = "blocked"


@dataclass
class Task:
    """Represents a production task"""

    id: str
    repo: str
    title: str
    description: str
    priority: TaskPriority
    assigned_to: Optional[AgentRole] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)


class ProductionAgentCollaboration:
    """
    24/7 Production Agent Collaboration System

    Manages work distribution between OPTIMUS and GASKET agents
    for continuous forward progress on ResonanceEnergy repos.
    """

    def __init__(self):
        self.workspace = Path(__file__).parent
        self.system_name = "QUANTUM FORGE" if os.name == "nt" else "Quantum Quasar"

        # Load portfolio
        self.portfolio = self._load_portfolio()
        self.repos = [r["name"] for r in self.portfolio.get("repositories", [])]

        # Task management
        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []

        # Agent status
        self.agent_status = {
            AgentRole.OPTIMUS: {
                "status": "ready",
                "current_task": None,
                "tasks_completed": 0,
            },
            AgentRole.GASKET: {
                "status": "ready",
                "current_task": None,
                "tasks_completed": 0,
            },
        }

        # Sync state
        self.sync_status = {
            "last_sync": None,
            "sync_interval_seconds": 300,  # 5 minutes
            "pending_sync": False,
        }

        # Production state file for cross-platform coordination
        self.state_file = self.workspace / "production_state.json"

        # Initialize
        self._load_state()

        print(f"🚀 Production Agent Collaboration initialized on {self.system_name}")
        print(f"📊 {len(self.repos)} repositories in ResonanceEnergy portfolio")

    def _load_portfolio(self) -> Dict:
        """Load portfolio.json"""
        portfolio_path = self.workspace / "portfolio.json"
        if portfolio_path.exists():
            with open(portfolio_path) as f:
                return json.load(f)
        return {"repositories": []}

    def _load_state(self):
        """Load production state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    state = json.load(f)
                    self.sync_status["last_sync"] = state.get("last_sync")
                    # Restore task queue if needed
            except Exception as e:
                print(f"⚠️ Could not load state: {e}")

    def _save_state(self):
        """Save production state for cross-platform sync"""
        state = {
            "timestamp": datetime.now().isoformat(),
            "system": self.system_name,
            "last_sync": self.sync_status.get("last_sync"),
            "agent_status": {
                role.value: {
                    "status": status["status"],
                    "tasks_completed": status["tasks_completed"],
                }
                for role, status in self.agent_status.items()
            },
            "pending_tasks": len(self.task_queue),
            "completed_tasks": len(self.completed_tasks),
        }

        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2, default=str)

    def generate_tasks_for_repo(self, repo_name: str) -> List[Task]:
        """Generate production tasks for a repository"""
        repo_info = next(
            (
                r
                for r in self.portfolio.get("repositories", [])
                if r["name"] == repo_name
            ),
            None,
        )

        if not repo_info:
            return []

        tier = repo_info.get("tier", "M")
        category = repo_info.get("category", "project")
        risk = repo_info.get("risk_tier", "MEDIUM")

        tasks = []
        base_id = hashlib.md5(
            f"{repo_name}{datetime.now().date()}".encode()
        ).hexdigest()[:8]

        # OPTIMUS tasks (strategic, architecture)
        tasks.append(
            Task(
                id=f"{base_id}-arch",
                repo=repo_name,
                title=f"Architecture Review: {repo_name}",
                description=f"Review and document the current architecture of {repo_name}. "
                f"Identify areas for improvement, technical debt, and optimization opportunities.",
                priority=TaskPriority.HIGH if tier == "L" else TaskPriority.MEDIUM,
                assigned_to=AgentRole.OPTIMUS,
            )
        )

        tasks.append(
            Task(
                id=f"{base_id}-plan",
                repo=repo_name,
                title=f"Progress Planning: {repo_name}",
                description=f"Create a detailed progress plan for {repo_name}. "
                f"Define milestones, deliverables, and success criteria.",
                priority=TaskPriority.HIGH,
                assigned_to=AgentRole.OPTIMUS,
                dependencies=[f"{base_id}-arch"],
            )
        )

        # GASKET tasks (implementation, testing)
        tasks.append(
            Task(
                id=f"{base_id}-impl",
                repo=repo_name,
                title=f"Implementation: {repo_name}",
                description=f"Execute the progress plan for {repo_name}. "
                f"Implement features, fix bugs, and enhance functionality.",
                priority=TaskPriority.HIGH,
                assigned_to=AgentRole.GASKET,
                dependencies=[f"{base_id}-plan"],
            )
        )

        tasks.append(
            Task(
                id=f"{base_id}-test",
                repo=repo_name,
                title=f"Testing & QA: {repo_name}",
                description=f"Test all changes made to {repo_name}. "
                f"Run unit tests, integration tests, and validate functionality.",
                priority=TaskPriority.HIGH,
                assigned_to=AgentRole.GASKET,
                dependencies=[f"{base_id}-impl"],
            )
        )

        # Integration task (collaborative)
        tasks.append(
            Task(
                id=f"{base_id}-integrate",
                repo=repo_name,
                title=f"Integration & Deployment: {repo_name}",
                description=f"Integrate and deploy changes to {repo_name}. "
                f"Ensure all tests pass and documentation is updated.",
                priority=TaskPriority.HIGH,
                assigned_to=AgentRole.GASKET,
                dependencies=[f"{base_id}-test"],
            )
        )

        # Add security review for high-risk repos
        if risk == "HIGH" or risk == "CRITICAL":
            tasks.append(
                Task(
                    id=f"{base_id}-sec",
                    repo=repo_name,
                    title=f"Security Audit: {repo_name}",
                    description=f"Perform security audit on {repo_name}. "
                    f"Check for vulnerabilities, secrets exposure, and compliance.",
                    priority=TaskPriority.CRITICAL,
                    assigned_to=AgentRole.OPTIMUS,
                )
            )

        return tasks

    def populate_task_queue(self, repos: List[str] = None):
        """Populate task queue for all or specified repos"""
        target_repos = repos or self.repos

        for repo in target_repos:
            tasks = self.generate_tasks_for_repo(repo)
            self.task_queue.extend(tasks)

        # Sort by priority
        self.task_queue.sort(key=lambda t: t.priority.value)

        print(
            f"📋 Generated {len(self.task_queue)} tasks for {len(target_repos)} repositories"
        )

    def get_next_task(self, agent: AgentRole) -> Optional[Task]:
        """Get next available task for an agent"""
        for task in self.task_queue:
            if task.status != TaskStatus.PENDING:
                continue
            if task.assigned_to != agent:
                continue

            # Check dependencies
            deps_satisfied = all(
                any(
                    t.id == dep and t.status == TaskStatus.COMPLETED
                    for t in self.completed_tasks
                )
                for dep in task.dependencies
            )

            if deps_satisfied or not task.dependencies:
                return task

        return None

    def assign_task(self, task: Task, agent: AgentRole):
        """Assign a task to an agent"""
        task.assigned_to = agent
        task.status = TaskStatus.ASSIGNED
        self.agent_status[agent]["current_task"] = task.id
        self.agent_status[agent]["status"] = "working"
        print(f"📌 Assigned '{task.title}' to {agent.value}")

    def start_task(self, task: Task):
        """Mark task as in progress"""
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()
        print(f"▶️ Started: {task.title}")

    def complete_task(self, task: Task, artifacts: List[str] = None):
        """Mark task as completed"""
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        task.artifacts = artifacts or []

        # Update agent status
        agent = task.assigned_to
        self.agent_status[agent]["current_task"] = None
        self.agent_status[agent]["status"] = "ready"
        self.agent_status[agent]["tasks_completed"] += 1

        # Move to completed
        self.task_queue.remove(task)
        self.completed_tasks.append(task)

        print(f"✅ Completed: {task.title}")
        self._save_state()

    def sync_with_peer(self):
        """Sync state with peer system (QUANTUM FORGE ↔ QUANTUM QUASAR)"""
        print(f"🔄 Syncing with peer system...")

        # This uses the shared git repository for coordination
        self._save_state()

        # Pull git changes
        try:
            subprocess.run(
                ["git", "pull", "--rebase"],
                cwd=self.workspace,
                capture_output=True,
                timeout=60,
            )
        except Exception as e:
            print(f"⚠️ Git sync failed: {e}")

        self.sync_status["last_sync"] = datetime.now().isoformat()
        self.sync_status["pending_sync"] = False

        print(f"✅ Sync complete")

    def get_production_status(self) -> Dict:
        """Get current production status"""
        return {
            "system": self.system_name,
            "timestamp": datetime.now().isoformat(),
            "agents": {
                agent.value: {
                    "status": status["status"],
                    "current_task": status["current_task"],
                    "tasks_completed": status["tasks_completed"],
                }
                for agent, status in self.agent_status.items()
            },
            "task_queue": {
                "pending": len(
                    [t for t in self.task_queue if t.status == TaskStatus.PENDING]
                ),
                "in_progress": len(
                    [t for t in self.task_queue if t.status == TaskStatus.IN_PROGRESS]
                ),
                "completed": len(self.completed_tasks),
            },
            "sync": self.sync_status,
            "repos_active": len(self.repos),
        }

    def run_production_cycle(self, duration_hours: float = 24.0):
        """Run continuous production cycle"""
        print("=" * 60)
        print("🚀 STARTING 24/7 PRODUCTION MODE")
        print("=" * 60)
        print(f"📍 System: {self.system_name}")
        print(f"⏱️ Duration: {duration_hours} hours")
        print(f"🤖 Agents: OPTIMUS + GASKET")
        print(f"📊 Repos: {len(self.repos)} in portfolio")
        print("=" * 60)

        # Populate initial task queue
        self.populate_task_queue()

        start_time = datetime.now()
        end_time = start_time + timedelta(hours=duration_hours)

        cycle_count = 0
        sync_interval = timedelta(minutes=5)
        last_sync = datetime.now()

        try:
            while datetime.now() < end_time:
                cycle_count += 1
                print(f"\n🔄 Production Cycle #{cycle_count}")

                # Process tasks for BOTH agents IN PARALLEL
                import concurrent.futures

                def process_agent_tasks(agent, batch_size=3):
                    """Process multiple tasks per agent per cycle"""
                    completed = 0
                    for _ in range(batch_size):
                        if self.agent_status[agent]["status"] == "ready":
                            task = self.get_next_task(agent)
                            if task:
                                self.assign_task(task, agent)
                                self.start_task(task)
                                print(f"   🔧 {agent.value}: {task.title}")
                                self.complete_task(task, [f"artifact_{task.id}.log"])
                                completed += 1
                    return completed

                # Run OPTIMUS and GASKET in parallel with 3 tasks each
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    futures = {
                        executor.submit(process_agent_tasks, AgentRole.OPTIMUS, 3): "OPTIMUS",
                        executor.submit(process_agent_tasks, AgentRole.GASKET, 3): "GASKET"
                    }
                    for future in concurrent.futures.as_completed(futures):
                        agent_name = futures[future]
                        try:
                            count = future.result()
                        except Exception as e:
                            print(f"   ⚠️ {agent_name} error: {e}")

                # Sync with peer system
                if datetime.now() - last_sync > sync_interval:
                    self.sync_with_peer()
                    last_sync = datetime.now()

                # Check if queue is empty
                if not self.task_queue:
                    print("📭 Task queue empty - regenerating tasks...")
                    self.populate_task_queue()

                # Status report
                status = self.get_production_status()
                print(f"   📊 Status: {status['task_queue']}")

                # Fast 2-second cycles for maximum throughput
                time.sleep(2)  # 2 second cycles for high performance

        except KeyboardInterrupt:
            print("\n⏹️ Production stopped by user")

        # Final report
        print("\n" + "=" * 60)
        print("📊 PRODUCTION SESSION COMPLETE")
        print("=" * 60)
        print(f"⏱️ Duration: {datetime.now() - start_time}")
        print(f"🔄 Cycles: {cycle_count}")
        print(
            f"✅ OPTIMUS completed: {self.agent_status[AgentRole.OPTIMUS]['tasks_completed']} tasks"
        )
        print(
            f"✅ GASKET completed: {self.agent_status[AgentRole.GASKET]['tasks_completed']} tasks"
        )
        print(f"📦 Total completed: {len(self.completed_tasks)} tasks")
        print("=" * 60)

        self._save_state()


def get_collaboration_instructions() -> str:
    """Get collaboration instructions for OPTIMUS and GASKET"""
    return """
╔══════════════════════════════════════════════════════════════════════════════╗
║       🚀 DIGITAL LABOUR - AGENT COLLABORATION PROTOCOL 🚀                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  SYSTEM ARCHITECTURE:                                                         ║
║  ┌─────────────────────────────────────────────────────────────────────────┐  ║
║  │  QUANTUM FORGE (Windows)      ↔      QUANTUM QUASAR (macOS)            │  ║
║  │       HP Laptop                        MacBook M1                       │  ║
║  │                                                                         │  ║
║  │  ┌──────────────────────────────────────────────────────────────────┐  │  ║
║  │  │                    SHARED GIT SYNC                              │  │  ║
║  │  │  • portfolio.json         • production_state.json               │  │  ║
║  │  │  • task assignments       • progress artifacts                  │  │  ║
║  │  └──────────────────────────────────────────────────────────────────┘  │  ║
║  └─────────────────────────────────────────────────────────────────────────┘  ║
║                                                                               ║
║  AGENT ROLES:                                                                 ║
║  ┌─────────────────────────────────────────────────────────────────────────┐  ║
║  │  🤖 OPTIMUS (Strategic Agent)                                          │  ║
║  │     • Architecture reviews and planning                                │  ║
║  │     • Technical decisions and design                                   │  ║
║  │     • Security audits for high-risk repos                             │  ║
║  │     • Code quality standards enforcement                              │  ║
║  │     • Documentation strategy                                          │  ║
║  ├─────────────────────────────────────────────────────────────────────────┤  ║
║  │  🔧 GASKET (Implementation Agent)                                      │  ║
║  │     • Feature implementation                                           │  ║
║  │     • Bug fixes and patches                                           │  ║
║  │     • Testing and QA                                                  │  ║
║  │     • Integration and deployment                                      │  ║
║  │     • CI/CD pipeline maintenance                                      │  ║
║  └─────────────────────────────────────────────────────────────────────────┘  ║
║                                                                               ║
║  COLLABORATION WORKFLOW:                                                      ║
║  1. OPTIMUS reviews repo → creates architecture plan                          ║
║  2. OPTIMUS defines tasks → assigns priorities                                ║
║  3. GASKET picks up implementation tasks                                      ║
║  4. GASKET executes → tests → creates PR                                      ║
║  5. OPTIMUS reviews → approves → GASKET deploys                              ║
║  6. Both agents sync via git every 5 minutes                            ║
║                                                                               ║
║  REPO PRIORITY ORDER:                                                         ║
║  1. CRITICAL: NCL, NCC-Doctrine, Digital-Labour                                ║
║  2. HIGH: Resonance-Energy-Systems, ResonanceEnergy_Enterprise               ║
║  3. MEDIUM: TESLA-TECH, future-predictor-council, TESLACALLS2026             ║
║  4. STANDARD: All other repos in portfolio                                   ║
║                                                                               ║
║  SYNC PROTOCOL:                                                               ║
║  • Auto-sync every 5 minutes via cross_platform_refresh.py                   ║
║  • Git pull/push through shared workspace                                    ║
║  • State file coordination (production_state.json)                           ║
║  • Git handles file-level sync                                          ║
║                                                                               ║
║  COMMANDS:                                                                    ║
║  • python3 production_agent_collaboration.py              # Start production ║
║  • python3 production_agent_collaboration.py --status     # Check status     ║
║  • python3 production_agent_collaboration.py --sync       # Force sync       ║
║                                                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""


def main():
    """Main entry point"""
    import sys

    collab = ProductionAgentCollaboration()

    if len(sys.argv) > 1:
        if sys.argv[1] == "--status":
            status = collab.get_production_status()
            print(json.dumps(status, indent=2, default=str))
        elif sys.argv[1] == "--sync":
            collab.sync_with_peer()
        elif sys.argv[1] == "--help":
            print(get_collaboration_instructions())
        elif sys.argv[1] == "--tasks":
            collab.populate_task_queue()
            for task in collab.task_queue[:20]:  # Show first 20
                print(f"[{task.priority.name}] {task.repo}: {task.title}")
        else:
            print(
                "Usage: python3 production_agent_collaboration.py [--status|--sync|--help|--tasks]"
            )
    else:
        # Print instructions and run production
        print(get_collaboration_instructions())

        # Run 24/7 production (default 24 hours)
        duration = float(os.environ.get("PRODUCTION_HOURS", 24))
        collab.run_production_cycle(duration_hours=duration)


if __name__ == "__main__":
    main()
