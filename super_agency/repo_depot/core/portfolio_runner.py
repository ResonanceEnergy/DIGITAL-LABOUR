"""
REPODEPOT Portfolio Runner - Phase 3
=====================================
Runs task executor across the entire portfolio with prioritization.

Features:
- Repo prioritization by tier (L > M > S)
- Task templates per repo type
- Progress tracking via git commits
- Parallel execution across repos

Author: REPODEPOT Rebuild Team
Date: 2026-02-24
"""

import json
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from repo_depot.core.task_executor import (
    TaskExecutor,
    TaskType,
    ExecutionResult,
    LocalRepoManager,
    ai_generator,
    quality_gate,
)
from repo_depot.core.agent_specialization import (
    AgentDispatcher,
    AgentTask,
    AgentResult,
    TaskCategory,
    AgentType,
)
from repo_depot.core.qa_dashboard import QADashboard, AutomatedQA, RealMetrics, QAStatus

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - PORTFOLIO - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RepoTier(Enum):
    L = "L"  # Large - Core infrastructure
    M = "M"  # Medium - Active projects
    S = "S"  # Small - Lower priority


@dataclass
class RepoConfig:
    """Configuration for a repository"""

    name: str
    tier: RepoTier
    visibility: str
    risk_tier: str
    category: str = ""
    tasks: List[TaskType] = field(default_factory=list)

    @property
    def priority(self) -> int:
        """Higher number = higher priority"""
        base = {"L": 100, "M": 50, "S": 10}[self.tier.value]
        # Boost for low risk
        if self.risk_tier == "LOW":
            base += 5
        # Boost for infrastructure
        if self.category in ["infrastructure", "doctrine"]:
            base += 20
        return base


@dataclass
class RepoProgress:
    """Progress tracking for a repo"""

    repo_name: str
    agent_commits: int = 0
    files_changed: int = 0
    last_activity: Optional[datetime] = None
    tasks_completed: List[str] = field(default_factory=list)
    artifacts_created: List[str] = field(default_factory=list)


# Task templates by tier
TASK_TEMPLATES = {
    RepoTier.L: [
        TaskType.ARCHITECTURE_REVIEW,
        TaskType.DOCUMENTATION,
        TaskType.TEST_GENERATION,
    ],
    RepoTier.M: [
        TaskType.ARCHITECTURE_REVIEW,
        TaskType.DOCUMENTATION,
    ],
    RepoTier.S: [
        TaskType.DOCUMENTATION,
    ],
}

# Category-specific tasks
CATEGORY_TASKS = {
    "infrastructure": [TaskType.ARCHITECTURE_REVIEW, TaskType.TEST_GENERATION],
    "doctrine": [TaskType.DOCUMENTATION],
    "enterprise": [TaskType.ARCHITECTURE_REVIEW, TaskType.DOCUMENTATION],
}


class PortfolioRunner:
    """
    Runs tasks across entire portfolio with prioritization.
    """

    def __init__(self, workspace: Path, portfolio_path: Path = None):
        self.workspace = workspace
        self.repos_dir = workspace / "repos"

        # Load portfolio
        portfolio_path = portfolio_path or workspace / "portfolio.json"
        self.repos = self._load_portfolio(portfolio_path)

        # Initialize executor
        self.executor = TaskExecutor(workspace)
        self.executor.repo_manager = LocalRepoManager(self.repos_dir)

        # Initialize agent dispatcher (Phase 4)
        self.dispatcher = AgentDispatcher(workspace)

        # Initialize QA Dashboard and Metrics (Phase 5)
        self.qa_dashboard = QADashboard(workspace)
        self.metrics = RealMetrics(workspace)

        # Progress tracking
        self.progress: Dict[str, RepoProgress] = {}

        logger.info(f"Portfolio Runner initialized with {len(self.repos)} repos")

    def _load_portfolio(self, path: Path) -> List[RepoConfig]:
        """Load and parse portfolio.json"""
        with open(path) as f:
            data = json.load(f)

        repos = []
        for r in data.get("repositories", []):
            try:
                tier = RepoTier(r.get("tier", "S"))
                category = r.get("category", "")

                # Assign tasks based on tier and category
                tasks = list(TASK_TEMPLATES.get(tier, []))
                if category and category in CATEGORY_TASKS:
                    for task in CATEGORY_TASKS[category]:
                        if task not in tasks:
                            tasks.append(task)

                repos.append(
                    RepoConfig(
                        name=r["name"],
                        tier=tier,
                        visibility=r.get("visibility", "private"),
                        risk_tier=r.get("risk_tier", "LOW"),
                        category=category,
                        tasks=tasks,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse repo {r.get('name')}: {e}")

        # Sort by priority (highest first)
        repos.sort(key=lambda r: r.priority, reverse=True)

        return repos

    def get_prioritized_repos(self, max_count: int = None) -> List[RepoConfig]:
        """Get repos sorted by priority"""
        repos = self.repos
        if max_count:
            repos = repos[:max_count]
        return repos

    def get_repos_by_tier(self, tier: RepoTier) -> List[RepoConfig]:
        """Get all repos of a specific tier"""
        return [r for r in self.repos if r.tier == tier]

    def run_task_on_repo(
        self, repo: RepoConfig, task_type: TaskType, agent: str = "GASKET"
    ) -> ExecutionResult:
        """Execute a single task on a repo"""
        # Check if repo exists locally
        repo_path = self.repos_dir / repo.name
        if not repo_path.exists():
            logger.warning(f"Repo {repo.name} not found locally, skipping")
            return ExecutionResult(success=False, error="Repo not found locally")

        # Execute task
        result = self.executor.execute_task(task_type=task_type, repo_name=repo.name, agent=agent)

        # Update progress
        if result.success:
            if repo.name not in self.progress:
                self.progress[repo.name] = RepoProgress(repo_name=repo.name)

            self.progress[repo.name].tasks_completed.append(task_type.value)
            self.progress[repo.name].artifacts_created.extend([str(a) for a in result.artifacts])
            self.progress[repo.name].last_activity = datetime.now()

        return result

    def run_all_tasks_on_repo(
        self, repo: RepoConfig, agent: str = "GASKET"
    ) -> List[ExecutionResult]:
        """Run all assigned tasks on a repo"""
        results = []

        for task_type in repo.tasks:
            logger.info(f"Running {task_type.value} on {repo.name}")
            result = self.run_task_on_repo(repo, task_type, agent)
            results.append(result)

            if not result.success:
                logger.warning(f"Task {task_type.value} failed on {repo.name}: {result.error}")

        return results

    def run_portfolio(
        self,
        max_repos: int = None,
        tier_filter: RepoTier = None,
        parallel: bool = False,
        max_workers: int = 3,
    ) -> Dict[str, List[ExecutionResult]]:
        """
        Run tasks across portfolio.

        Args:
            max_repos: Maximum number of repos to process
            tier_filter: Only process repos of this tier
            parallel: Run repos in parallel
            max_workers: Number of parallel workers

        Returns:
            Dict mapping repo name to list of results
        """
        repos = self.get_prioritized_repos(max_repos)

        if tier_filter:
            repos = [r for r in repos if r.tier == tier_filter]

        logger.info(f"Running portfolio tasks on {len(repos)} repos")

        all_results = {}

        if parallel and len(repos) > 1:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self.run_all_tasks_on_repo, repo): repo for repo in repos
                }

                for future in as_completed(futures):
                    repo = futures[future]
                    try:
                        results = future.result()
                        all_results[repo.name] = results
                    except Exception as e:
                        logger.error(f"Error processing {repo.name}: {e}")
                        all_results[repo.name] = [ExecutionResult(success=False, error=str(e))]
        else:
            for repo in repos:
                results = self.run_all_tasks_on_repo(repo)
                all_results[repo.name] = results

        return all_results

    def get_progress_report(self) -> Dict[str, Any]:
        """Generate progress report from git history"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "repos_processed": len(self.progress),
            "total_tasks": sum(len(p.tasks_completed) for p in self.progress.values()),
            "total_artifacts": sum(len(p.artifacts_created) for p in self.progress.values()),
            "by_repo": {},
        }

        for name, prog in self.progress.items():
            report["by_repo"][name] = {
                "tasks_completed": prog.tasks_completed,
                "artifacts_count": len(prog.artifacts_created),
                "last_activity": prog.last_activity.isoformat() if prog.last_activity else None,
            }

        return report

    def get_git_progress(self, repo_name: str) -> Optional[RepoProgress]:
        """Get progress from actual git commits"""
        repo_path = self.repos_dir / repo_name
        if not repo_path.exists() or not (repo_path / ".git").exists():
            return None

        progress = RepoProgress(repo_name=repo_name)

        try:
            # Count agent commits
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "--oneline",
                    "--author=OPTIMUS",
                    "--author=GASKET",
                    "--author=ResonanceEnergy",
                    "--author=re-repo-bot",
                    "--since=7 days ago",
                ],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            progress.agent_commits = (
                len(result.stdout.strip().splitlines()) if result.stdout else 0
            )

            # Get last commit date
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ci"], cwd=repo_path, capture_output=True, text=True
            )
            if result.stdout:
                progress.last_activity = datetime.fromisoformat(
                    result.stdout.strip().replace(" ", "T").rsplit("+", 1)[0]
                )

        except Exception as e:
            logger.warning(f"Error getting git progress for {repo_name}: {e}")

        return progress

    # ==========================================================================
    # PHASE 4: Agent Specialization Integration
    # ==========================================================================

    def run_with_agents(
        self, repo: RepoConfig, run_optimus: bool = True, run_gasket: bool = True
    ) -> List[AgentResult]:
        """
        Run specialized agents on a repo.

        OPTIMUS handles: Architecture, Risk, Dependencies, Performance, Integration
        GASKET handles: Tests, Documentation, Code, Bug Fixes, Features
        """
        repo_path = self.repos_dir / repo.name
        if not repo_path.exists():
            logger.warning(f"Repo {repo.name} not found locally")
            return []

        results = []

        if run_optimus:
            logger.info(f"Running OPTIMUS on {repo.name}")
            results.extend(self.dispatcher.run_strategic_analysis(repo.name))

        if run_gasket:
            logger.info(f"Running GASKET on {repo.name}")
            results.extend(self.dispatcher.run_implementation_tasks(repo.name))

        return results

    def run_agent_portfolio(
        self,
        max_repos: int = None,
        tier_filter: RepoTier = None,
        agent_type: str = "both",  # "optimus", "gasket", or "both"
    ) -> Dict[str, List[AgentResult]]:
        """
        Run specialized agents across portfolio.

        Args:
            max_repos: Maximum repos to process
            tier_filter: Only process this tier
            agent_type: Which agent(s) to run
        """
        repos = self.get_prioritized_repos(max_repos)

        if tier_filter:
            repos = [r for r in repos if r.tier == tier_filter]

        run_optimus = agent_type in ["optimus", "both"]
        run_gasket = agent_type in ["gasket", "both"]

        logger.info(
            f"Running agents on {len(repos)} repos (OPTIMUS: {run_optimus}, GASKET: {run_gasket})"
        )

        all_results = {}

        for repo in repos:
            results = self.run_with_agents(repo, run_optimus, run_gasket)
            all_results[repo.name] = results

            # Log progress
            success_count = sum(1 for r in results if r.success)
            logger.info(f"  {repo.name}: {success_count}/{len(results)} tasks succeeded")

        return all_results

    def get_agent_stats(self) -> Dict[str, Any]:
        """Get statistics from agent dispatcher"""
        return self.dispatcher.get_stats()

    # ==========================================================================
    # PHASE 5: QA & Verification Integration
    # ==========================================================================

    def submit_for_qa(self, result: AgentResult, repo_name: str) -> None:
        """Submit agent result for QA review"""
        if result.success and result.artifacts:
            self.qa_dashboard.add_for_review(
                task_id=result.task_id,
                agent=result.agent.value,
                repo=repo_name,
                artifacts=result.artifacts,
                commit_sha=result.commit_sha,
            )

    def run_with_qa(
        self,
        repo: RepoConfig,
        run_optimus: bool = True,
        run_gasket: bool = True,
        auto_submit_qa: bool = True,
    ) -> List[AgentResult]:
        """Run agents and automatically submit for QA"""
        results = self.run_with_agents(repo, run_optimus, run_gasket)

        if auto_submit_qa:
            for result in results:
                if result.success:
                    self.submit_for_qa(result, repo.name)

        return results

    def get_qa_summary(self) -> Dict[str, Any]:
        """Get QA dashboard summary"""
        return self.qa_dashboard.get_summary()

    def get_metrics(self, since_days: int = 7) -> Dict[str, Any]:
        """Get real production metrics"""
        return self.metrics.calculate_all(since_days)

    def show_qa_dashboard(self, interactive: bool = False) -> None:
        """Display QA dashboard"""
        self.qa_dashboard.show_pending(interactive=interactive)

    def show_metrics_dashboard(self) -> None:
        """Display metrics dashboard"""
        self.metrics.show_dashboard()


def run_portfolio_phase3():
    """Run Phase 3 portfolio operations"""
    print("=" * 60)
    print("REPODEPOT PHASE 3 - PORTFOLIO OPERATIONS")
    print("=" * 60)

    workspace = Path(
        str(Path(__file__).parent.parent.parent)
    )

    runner = PortfolioRunner(workspace)

    # Show prioritized repos
    print("\n📊 Portfolio by Priority:")
    for i, repo in enumerate(runner.repos[:10], 1):
        print(f"  {i}. [{repo.tier.value}] {repo.name} (priority: {repo.priority})")
        print(f"      Tasks: {[t.value for t in repo.tasks]}")

    # Run on top 5 L-tier repos
    print("\n🚀 Running tasks on L-tier repos...")
    l_repos = runner.get_repos_by_tier(RepoTier.L)
    print(f"   Found {len(l_repos)} L-tier repos")

    results = runner.run_portfolio(tier_filter=RepoTier.L, max_repos=3)

    # Report
    print("\n" + "=" * 60)
    print("📋 RESULTS")
    print("=" * 60)

    total_success = 0
    total_tasks = 0

    for repo_name, repo_results in results.items():
        success = sum(1 for r in repo_results if r.success)
        total = len(repo_results)
        total_success += success
        total_tasks += total

        print(f"\n  {repo_name}:")
        for result in repo_results:
            status = "✅" if result.success else "❌"
            artifacts = len(result.artifacts) if result.artifacts else 0
            print(f"    {status} Artifacts: {artifacts}")
            if result.error:
                print(f"       Error: {result.error}")

    print(f"\n📊 Total: {total_success}/{total_tasks} tasks succeeded")

    # Save progress report
    report = runner.get_progress_report()
    report_path = workspace / "portfolio_progress.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n💾 Progress saved to {report_path}")

    return runner


if __name__ == "__main__":
    run_portfolio_phase3()
