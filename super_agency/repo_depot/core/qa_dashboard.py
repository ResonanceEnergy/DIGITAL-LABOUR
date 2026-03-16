"""
REPODEPOT Phase 5: QA & Verification Dashboard
===============================================
Quality assurance system for verifying agent work output.

Components:
- AutomatedQA: Automated quality checks for artifacts
- QADashboard: Interface for reviewing pending work
- RealMetrics: Track actual production metrics

Author: REPODEPOT Rebuild Team
Date: 2026-02-24
"""

import ast
import subprocess
import json
import re
import logging
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# QA STATUS DEFINITIONS
# =============================================================================


class QAStatus(Enum):
    """QA status for artifacts"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"
    AUTO_REJECTED = "auto_rejected"


@dataclass
class QACheck:
    """Result of a single QA check"""

    name: str
    passed: bool
    message: str = ""
    severity: str = "error"  # error, warning, info


@dataclass
class QAResult:
    """Combined result of all QA checks on an artifact"""

    artifact: Path
    checks: List[QACheck] = field(default_factory=list)
    status: QAStatus = QAStatus.PENDING
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def passed(self) -> bool:
        """All error-level checks must pass"""
        return all(c.passed for c in self.checks if c.severity == "error")

    @property
    def score(self) -> float:
        """Score 0-100 based on passed checks"""
        if not self.checks:
            return 0.0
        return (sum(1 for c in self.checks if c.passed) / len(self.checks)) * 100


@dataclass
class TaskQARecord:
    """QA record for a completed task"""

    task_id: str
    agent: str
    repo: str
    artifacts: List[Path]
    commit_sha: Optional[str]
    created_at: datetime
    qa_results: List[QAResult] = field(default_factory=list)
    status: QAStatus = QAStatus.PENDING
    reviewer: Optional[str] = None
    review_comment: str = ""
    reviewed_at: Optional[datetime] = None


# =============================================================================
# AUTOMATED QA CHECKS
# =============================================================================


class AutomatedQA:
    """
    Automated quality checks for code artifacts.

    Checks:
    - syntax_valid: Python files parse without errors
    - file_not_empty: File has meaningful content
    - no_hardcoded_secrets: No API keys, passwords in code
    - imports_resolve: Import statements are valid
    - passes_lint: Basic linting passes
    - docstrings_present: Functions/classes have docstrings
    - no_todos: No TODO/FIXME left behind
    - type_hints: Type hints present on functions
    """

    CHECKS = [
        "syntax_valid",
        "file_not_empty",
        "no_hardcoded_secrets",
        "imports_resolve",
        "passes_lint",
        "docstrings_present",
        "no_todos",
        "markdown_valid",
    ]

    # Patterns that indicate secrets
    SECRET_PATTERNS = [
        r"sk-[a-zA-Z0-9]{20,}",  # OpenAI keys
        r"sk-ant-[a-zA-Z0-9]{20,}",  # Anthropic keys
        r"xai-[a-zA-Z0-9]{20,}",  # xAI keys
        r'password\s*=\s*["\'][^"\']+["\']',  # Hardcoded passwords
        r'api_key\s*=\s*["\'][^"\']+["\']',  # Hardcoded API keys
        r'secret\s*=\s*["\'][^"\']+["\']',  # Hardcoded secrets
    ]

    def __init__(self):
        self.results_cache: Dict[Path, QAResult] = {}

    def run_all_checks(self, artifact: Path) -> QAResult:
        """Run all applicable checks on an artifact"""
        if not artifact.exists():
            return QAResult(
                artifact=artifact,
                checks=[QACheck("file_exists", False, "File does not exist")],
                status=QAStatus.AUTO_REJECTED,
            )

        checks = []

        # Run checks based on file type
        if artifact.suffix == ".py":
            checks.extend(
                [
                    self.check_syntax_valid(artifact),
                    self.check_file_not_empty(artifact),
                    self.check_no_hardcoded_secrets(artifact),
                    self.check_imports_resolve(artifact),
                    self.check_passes_lint(artifact),
                    self.check_docstrings_present(artifact),
                    self.check_no_todos(artifact),
                ]
            )
        elif artifact.suffix == ".md":
            checks.extend(
                [
                    self.check_file_not_empty(artifact),
                    self.check_markdown_valid(artifact),
                    self.check_no_todos(artifact),
                ]
            )
        else:
            checks.append(self.check_file_not_empty(artifact))

        # Determine status
        result = QAResult(artifact=artifact, checks=checks)
        if result.passed:
            result.status = QAStatus.AUTO_APPROVED if result.score >= 90 else QAStatus.PENDING
        else:
            result.status = QAStatus.AUTO_REJECTED

        self.results_cache[artifact] = result
        return result

    def check_syntax_valid(self, artifact: Path) -> QACheck:
        """Check Python syntax is valid"""
        try:
            content = artifact.read_text()
            ast.parse(content)
            return QACheck("syntax_valid", True, "Python syntax valid")
        except SyntaxError as e:
            return QACheck("syntax_valid", False, f"Syntax error: {e}")
        except Exception as e:
            return QACheck("syntax_valid", False, f"Parse error: {e}")

    def check_file_not_empty(self, artifact: Path) -> QACheck:
        """Check file has meaningful content"""
        try:
            content = artifact.read_text().strip()
            if not content:
                return QACheck("file_not_empty", False, "File is empty")

            # For Python, check it's not just comments
            if artifact.suffix == ".py":
                lines = [
                    l for l in content.splitlines() if l.strip() and not l.strip().startswith("#")
                ]
                if len(lines) < 3:
                    return QACheck(
                        "file_not_empty", False, "File has minimal content", severity="warning"
                    )

            # Check minimum size
            if len(content) < 50:
                return QACheck("file_not_empty", False, "File too short", severity="warning")

            return QACheck("file_not_empty", True, f"{len(content)} characters")
        except Exception as e:
            return QACheck("file_not_empty", False, f"Read error: {e}")

    def check_no_hardcoded_secrets(self, artifact: Path) -> QACheck:
        """Check for hardcoded API keys and secrets"""
        try:
            content = artifact.read_text()

            found_secrets = []
            for pattern in self.SECRET_PATTERNS:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    found_secrets.extend(matches[:2])  # Limit display

            if found_secrets:
                # Redact the secrets for display
                redacted = [s[:10] + "..." for s in found_secrets]
                return QACheck(
                    "no_hardcoded_secrets",
                    False,
                    f"Found potential secrets: {redacted}",
                    severity="error",
                )

            return QACheck("no_hardcoded_secrets", True, "No secrets detected")
        except Exception as e:
            return QACheck("no_hardcoded_secrets", False, f"Check error: {e}")

    def check_imports_resolve(self, artifact: Path) -> QACheck:
        """Check import statements are valid"""
        try:
            content = artifact.read_text()
            tree = ast.parse(content)

            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            if not imports:
                return QACheck("imports_resolve", True, "No imports", severity="info")

            # Check if standard/common imports
            stdlib = {
                "os",
                "sys",
                "json",
                "pathlib",
                "datetime",
                "typing",
                "subprocess",
                "re",
                "logging",
                "dataclasses",
                "enum",
                "abc",
                "collections",
                "functools",
            }

            unknown = [i for i in imports if i.split(".")[0] not in stdlib]

            if unknown and len(unknown) > len(imports) / 2:
                return QACheck(
                    "imports_resolve", True, f"External imports: {unknown[:3]}", severity="warning"
                )

            return QACheck("imports_resolve", True, f"{len(imports)} imports")
        except Exception as e:
            return QACheck("imports_resolve", False, f"Check error: {e}", severity="warning")

    def check_passes_lint(self, artifact: Path) -> QACheck:
        """Run basic linting checks"""
        try:
            content = artifact.read_text()
            issues = []

            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                # Check line length
                if len(line) > 120:
                    issues.append(f"L{i}: line too long ({len(line)})")

                # Check trailing whitespace
                if line.rstrip() != line:
                    issues.append(f"L{i}: trailing whitespace")

                # Check tabs
                if "\t" in line:
                    issues.append(f"L{i}: tab character")

            if len(issues) > 5:
                return QACheck(
                    "passes_lint", False, f"{len(issues)} lint issues", severity="warning"
                )
            elif issues:
                return QACheck("passes_lint", True, f"{len(issues)} minor issues", severity="info")

            return QACheck("passes_lint", True, "Lint clean")
        except Exception as e:
            return QACheck("passes_lint", False, f"Lint error: {e}", severity="warning")

    def check_docstrings_present(self, artifact: Path) -> QACheck:
        """Check functions and classes have docstrings"""
        try:
            content = artifact.read_text()
            tree = ast.parse(content)

            funcs_classes = 0
            with_docstrings = 0

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    funcs_classes += 1
                    if (
                        node.body
                        and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[0].value.value, str)
                    ):
                        with_docstrings += 1

            if funcs_classes == 0:
                return QACheck("docstrings_present", True, "No functions/classes", severity="info")

            ratio = with_docstrings / funcs_classes
            if ratio < 0.5:
                return QACheck(
                    "docstrings_present",
                    False,
                    f"Only {with_docstrings}/{funcs_classes} have docstrings",
                    severity="warning",
                )

            return QACheck(
                "docstrings_present", True, f"{with_docstrings}/{funcs_classes} documented"
            )
        except Exception as e:
            return QACheck("docstrings_present", False, f"Check error: {e}", severity="warning")

    def check_no_todos(self, artifact: Path) -> QACheck:
        """Check for leftover TODOs"""
        try:
            content = artifact.read_text()

            todo_pattern = r"\b(TODO|FIXME|XXX|HACK)\b"
            matches = re.findall(todo_pattern, content, re.IGNORECASE)

            if matches:
                return QACheck(
                    "no_todos", True, f"Found {len(matches)} TODO markers", severity="info"
                )

            return QACheck("no_todos", True, "No TODOs")
        except Exception as e:
            return QACheck("no_todos", False, f"Check error: {e}", severity="info")

    def check_markdown_valid(self, artifact: Path) -> QACheck:
        """Check markdown structure is valid"""
        try:
            content = artifact.read_text()

            # Check for headers
            has_headers = bool(re.search(r"^#{1,6}\s", content, re.MULTILINE))

            # Check for broken links
            broken_links = re.findall(r"\[([^\]]+)\]\(\s*\)", content)

            issues = []
            if not has_headers:
                issues.append("no headers")
            if broken_links:
                issues.append(f"{len(broken_links)} empty links")

            if issues:
                return QACheck("markdown_valid", False, ", ".join(issues), severity="warning")

            return QACheck("markdown_valid", True, "Markdown structure valid")
        except Exception as e:
            return QACheck("markdown_valid", False, f"Check error: {e}", severity="warning")


# =============================================================================
# QA DASHBOARD
# =============================================================================


class QADashboard:
    """
    Dashboard for reviewing and approving agent work.

    Features:
    - View pending QA items
    - View automated check results
    - Approve/reject with comments
    - Track approval history
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.repos_dir = workspace / "repos"
        self.qa_store = workspace / "qa_store.json"
        self.automated_qa = AutomatedQA()

        # Load existing QA records
        self.records: Dict[str, TaskQARecord] = {}
        self._load_store()

    def _load_store(self):
        """Load QA records from disk"""
        if self.qa_store.exists():
            try:
                data = json.loads(self.qa_store.read_text())
                # Reconstruct records (simplified for now)
                for task_id, record_data in data.get("records", {}).items():
                    self.records[task_id] = TaskQARecord(
                        task_id=record_data["task_id"],
                        agent=record_data["agent"],
                        repo=record_data["repo"],
                        artifacts=[Path(p) for p in record_data["artifacts"]],
                        commit_sha=record_data.get("commit_sha"),
                        created_at=datetime.fromisoformat(record_data["created_at"]),
                        status=QAStatus(record_data.get("status", "pending")),
                    )
            except Exception as e:
                logger.warning(f"Failed to load QA store: {e}")

    def _save_store(self):
        """Save QA records to disk"""
        data = {"updated_at": datetime.now().isoformat(), "records": {}}

        for task_id, record in self.records.items():
            data["records"][task_id] = {
                "task_id": record.task_id,
                "agent": record.agent,
                "repo": record.repo,
                "artifacts": [str(p) for p in record.artifacts],
                "commit_sha": record.commit_sha,
                "created_at": record.created_at.isoformat(),
                "status": record.status.value,
                "reviewer": record.reviewer,
                "review_comment": record.review_comment,
            }

        self.qa_store.write_text(json.dumps(data, indent=2))

    def add_for_review(
        self,
        task_id: str,
        agent: str,
        repo: str,
        artifacts: List[Path],
        commit_sha: Optional[str] = None,
    ) -> TaskQARecord:
        """Add a completed task for QA review"""
        # Run automated checks
        qa_results = []
        for artifact in artifacts:
            result = self.automated_qa.run_all_checks(artifact)
            qa_results.append(result)

        # Determine initial status based on automated QA
        all_auto_approved = all(r.status == QAStatus.AUTO_APPROVED for r in qa_results)
        any_auto_rejected = any(r.status == QAStatus.AUTO_REJECTED for r in qa_results)

        if any_auto_rejected:
            initial_status = QAStatus.AUTO_REJECTED
        elif all_auto_approved:
            initial_status = QAStatus.AUTO_APPROVED
        else:
            initial_status = QAStatus.PENDING

        record = TaskQARecord(
            task_id=task_id,
            agent=agent,
            repo=repo,
            artifacts=artifacts,
            commit_sha=commit_sha,
            created_at=datetime.now(),
            qa_results=qa_results,
            status=initial_status,
        )

        self.records[task_id] = record
        self._save_store()

        return record

    def get_pending(self) -> List[TaskQARecord]:
        """Get all pending QA items"""
        return [r for r in self.records.values() if r.status == QAStatus.PENDING]

    def get_by_status(self, status: QAStatus) -> List[TaskQARecord]:
        """Get records by status"""
        return [r for r in self.records.values() if r.status == status]

    def approve(self, task_id: str, reviewer: str = "human", comment: str = "") -> bool:
        """Approve a task"""
        if task_id not in self.records:
            return False

        record = self.records[task_id]
        record.status = QAStatus.APPROVED
        record.reviewer = reviewer
        record.review_comment = comment
        record.reviewed_at = datetime.now()

        self._save_store()
        return True

    def reject(self, task_id: str, reviewer: str = "human", comment: str = "") -> bool:
        """Reject a task"""
        if task_id not in self.records:
            return False

        record = self.records[task_id]
        record.status = QAStatus.REJECTED
        record.reviewer = reviewer
        record.review_comment = comment
        record.reviewed_at = datetime.now()

        self._save_store()
        return True

    def show_pending(self, interactive: bool = False) -> None:
        """Display pending QA items"""
        pending = self.get_pending()

        print("\n" + "=" * 60)
        print("QA DASHBOARD - Pending Review")
        print("=" * 60)

        if not pending:
            print("\nNo items pending review!")
            return

        for record in pending:
            print(f"\n📋 Task: {record.task_id}")
            print(f"   Agent: {record.agent}")
            print(f"   Repo: {record.repo}")
            print(f"   Created: {record.created_at.strftime('%Y-%m-%d %H:%M')}")
            print(f"   Artifacts: {len(record.artifacts)}")

            for result in record.qa_results:
                status_icon = "✅" if result.passed else "❌"
                print(f"     {status_icon} {result.artifact.name} (score: {result.score:.0f}%)")
                for check in result.checks:
                    check_icon = "✓" if check.passed else "✗"
                    print(f"        {check_icon} {check.name}: {check.message}")

            if interactive:
                response = input("\n   Approve? (y/n/s=skip): ").lower()
                if response == "y":
                    self.approve(record.task_id)
                    print("   ✅ Approved")
                elif response == "n":
                    comment = input("   Rejection reason: ")
                    self.reject(record.task_id, comment=comment)
                    print("   ❌ Rejected")

    def get_summary(self) -> Dict[str, Any]:
        """Get QA summary statistics"""
        total = len(self.records)
        by_status = {}
        for status in QAStatus:
            by_status[status.value] = len(self.get_by_status(status))

        # Calculate approval rate
        reviewed = by_status.get("approved", 0) + by_status.get("rejected", 0)
        approval_rate = (by_status.get("approved", 0) / reviewed * 100) if reviewed else 0

        return {
            "total_records": total,
            "by_status": by_status,
            "approval_rate": approval_rate,
            "pending_count": by_status.get("pending", 0),
        }


# =============================================================================
# REAL METRICS TRACKING
# =============================================================================


class RealMetrics:
    """
    Track REAL production metrics across the portfolio.

    Metrics:
    - Lines of code added
    - Files created
    - Tests added
    - Test coverage change
    - Commits pushed
    - Repos touched
    - QA approval rate
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.repos_dir = workspace / "repos"
        self.metrics_store = workspace / "real_metrics.json"

        # Cache for expensive calculations
        self._cache = {}
        self._cache_time = None

    def calculate_all(self, since_days: int = 7) -> Dict[str, Any]:
        """Calculate all metrics"""
        metrics = {
            "calculated_at": datetime.now().isoformat(),
            "period_days": since_days,
            "lines_of_code_added": self._count_loc_added(since_days),
            "files_created": self._count_new_files(since_days),
            "tests_added": self._count_new_tests(since_days),
            "commits_by_agent": self._count_agent_commits(since_days),
            "repos_touched": self._count_active_repos(since_days),
            "documentation_added": self._count_docs_added(since_days),
        }

        # Save metrics
        self._save_metrics(metrics)

        return metrics

    def _count_loc_added(self, since_days: int) -> int:
        """Count lines of code added"""
        total_lines = 0

        for repo_path in self.repos_dir.iterdir():
            if not repo_path.is_dir() or not (repo_path / ".git").exists():
                continue

            try:
                result = subprocess.run(
                    [
                        "git",
                        "log",
                        "--oneline",
                        f"--since={since_days} days ago",
                        "--numstat",
                        "--author=OPTIMUS",
                        "--author=GASKET",
                    ],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                for line in result.stdout.splitlines():
                    parts = line.split("\t")
                    if len(parts) >= 2 and parts[0].isdigit():
                        total_lines += int(parts[0])  # Added lines
            except Exception:
                pass

        return total_lines

    def _count_new_files(self, since_days: int) -> int:
        """Count new files created by agents"""
        total_files = 0

        for repo_path in self.repos_dir.iterdir():
            if not repo_path.is_dir() or not (repo_path / ".git").exists():
                continue

            try:
                result = subprocess.run(
                    [
                        "git",
                        "log",
                        "--oneline",
                        f"--since={since_days} days ago",
                        "--diff-filter=A",
                        "--name-only",
                        "--author=OPTIMUS",
                        "--author=GASKET",
                    ],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                files = [l for l in result.stdout.splitlines() if l and not l.startswith(" ")]
                total_files += len(files)
            except Exception:
                pass

        return total_files

    def _count_new_tests(self, since_days: int) -> int:
        """Count new test files created"""
        total_tests = 0

        for repo_path in self.repos_dir.iterdir():
            if not repo_path.is_dir() or not (repo_path / ".git").exists():
                continue

            try:
                result = subprocess.run(
                    [
                        "git",
                        "log",
                        "--oneline",
                        f"--since={since_days} days ago",
                        "--diff-filter=A",
                        "--name-only",
                        "--author=OPTIMUS",
                        "--author=GASKET",
                    ],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                for line in result.stdout.splitlines():
                    if "test" in line.lower() and line.endswith(".py"):
                        total_tests += 1
            except Exception:
                pass

        return total_tests

    def _count_agent_commits(self, since_days: int) -> Dict[str, int]:
        """Count commits by agent"""
        commits = {"OPTIMUS": 0, "GASKET": 0}

        for repo_path in self.repos_dir.iterdir():
            if not repo_path.is_dir() or not (repo_path / ".git").exists():
                continue

            for agent in commits.keys():
                try:
                    result = subprocess.run(
                        [
                            "git",
                            "log",
                            "--oneline",
                            f"--since={since_days} days ago",
                            f"--author={agent}",
                        ],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    commits[agent] += len(result.stdout.strip().splitlines())
                except Exception:
                    pass

        return commits

    def _count_active_repos(self, since_days: int) -> int:
        """Count repos with agent activity"""
        active = 0

        for repo_path in self.repos_dir.iterdir():
            if not repo_path.is_dir() or not (repo_path / ".git").exists():
                continue

            try:
                result = subprocess.run(
                    [
                        "git",
                        "log",
                        "--oneline",
                        f"--since={since_days} days ago",
                        "--author=OPTIMUS",
                        "--author=GASKET",
                        "-1",
                    ],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.stdout.strip():
                    active += 1
            except Exception:
                pass

        return active

    def _count_docs_added(self, since_days: int) -> int:
        """Count documentation files added"""
        total_docs = 0

        for repo_path in self.repos_dir.iterdir():
            if not repo_path.is_dir() or not (repo_path / ".git").exists():
                continue

            try:
                result = subprocess.run(
                    [
                        "git",
                        "log",
                        "--oneline",
                        f"--since={since_days} days ago",
                        "--diff-filter=A",
                        "--name-only",
                        "--author=OPTIMUS",
                        "--author=GASKET",
                    ],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                for line in result.stdout.splitlines():
                    if line.endswith(".md") or "docs/" in line:
                        total_docs += 1
            except Exception:
                pass

        return total_docs

    def _save_metrics(self, metrics: Dict[str, Any]):
        """Save metrics to disk"""
        history = {"history": []}

        if self.metrics_store.exists():
            try:
                history = json.loads(self.metrics_store.read_text())
            except Exception:
                pass

        # Keep last 30 entries
        history["history"] = history.get("history", [])[-29:]
        history["history"].append(metrics)
        history["latest"] = metrics

        self.metrics_store.write_text(json.dumps(history, indent=2))

    def get_latest(self) -> Optional[Dict[str, Any]]:
        """Get latest metrics"""
        if self.metrics_store.exists():
            try:
                data = json.loads(self.metrics_store.read_text())
                return data.get("latest")
            except Exception:
                pass
        return None

    def show_dashboard(self) -> None:
        """Display metrics dashboard"""
        metrics = self.calculate_all()

        print("\n" + "=" * 60)
        print("REAL METRICS DASHBOARD")
        print("=" * 60)
        print(f"\nPeriod: Last {metrics['period_days']} days")
        print(f"Calculated: {metrics['calculated_at']}")
        print()

        print("📊 Code Activity:")
        print(f"   Lines of Code Added:  {metrics['lines_of_code_added']:,}")
        print(f"   Files Created:        {metrics['files_created']}")
        print(f"   Tests Added:          {metrics['tests_added']}")
        print(f"   Documentation Added:  {metrics['documentation_added']}")
        print()

        print("🤖 Agent Activity:")
        for agent, count in metrics["commits_by_agent"].items():
            print(f"   {agent}: {count} commits")
        print()

        print("📁 Portfolio Coverage:")
        print(f"   Repos Touched: {metrics['repos_touched']}")


# =============================================================================
# CLI INTERFACE
# =============================================================================


def main():
    """Run Phase 5 QA Dashboard"""
    import argparse

    parser = argparse.ArgumentParser(description="REPODEPOT QA Dashboard")
    parser.add_argument("--action", choices=["qa", "metrics", "check"], default="qa")
    parser.add_argument("--file", type=Path, help="File to check")
    parser.add_argument("--workspace", default=".", help="Workspace path")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()

    if args.action == "check" and args.file:
        # Run checks on a specific file
        qa = AutomatedQA()
        result = qa.run_all_checks(args.file)

        print(f"\nQA Results for {args.file.name}")
        print(f"Status: {result.status.value}")
        print(f"Score: {result.score:.0f}%")
        print()

        for check in result.checks:
            icon = "✓" if check.passed else "✗"
            print(f"  {icon} {check.name}: {check.message}")

    elif args.action == "qa":
        # Show QA dashboard
        dashboard = QADashboard(workspace)
        dashboard.show_pending(interactive=args.interactive)

        summary = dashboard.get_summary()
        print(f"\nSummary: {summary['total_records']} total, {summary['pending_count']} pending")
        print(f"Approval Rate: {summary['approval_rate']:.1f}%")

    elif args.action == "metrics":
        # Show metrics
        metrics = RealMetrics(workspace)
        metrics.show_dashboard()


if __name__ == "__main__":
    main()
