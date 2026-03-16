"""
REPODEPOT Phase 4: Agent Specialization
========================================
Separates OPTIMUS (Strategic) and GASKET (Implementation) roles.

OPTIMUS: Architecture, Risk Assessment, Dependencies, Performance, Integration
GASKET: Code Implementation, Tests, Documentation, Bug Fixes, Features

Each agent has specialized prompts, workflows, and output formats.

Author: REPODEPOT Rebuild Team
Date: 2026-02-24
"""

import subprocess
import json
import logging
import os
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from abc import ABC, abstractmethod

# Import the AI generator from task_executor
try:
    from .task_executor import AICodeGenerator, API_KEYS
except ImportError:
    from task_executor import AICodeGenerator, API_KEYS

logger = logging.getLogger(__name__)


# =============================================================================
# AGENT TYPE DEFINITIONS
# =============================================================================


class AgentType(Enum):
    """Agent specialization types"""

    OPTIMUS = "optimus"  # Strategic
    GASKET = "gasket"  # Implementation


class TaskCategory(Enum):
    """Task categories for routing"""

    # OPTIMUS tasks (Strategic)
    ARCHITECTURE = "architecture"
    RISK_ASSESSMENT = "risk_assessment"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    PERFORMANCE_PLANNING = "performance_planning"
    INTEGRATION_DESIGN = "integration_design"

    # GASKET tasks (Implementation)
    CODE_IMPLEMENTATION = "code_implementation"
    TEST_GENERATION = "test_generation"
    DOCUMENTATION = "documentation"
    BUG_FIX = "bug_fix"
    FEATURE_DEVELOPMENT = "feature_development"


# Task routing map
TASK_ROUTING: Dict[TaskCategory, AgentType] = {
    # Strategic - OPTIMUS
    TaskCategory.ARCHITECTURE: AgentType.OPTIMUS,
    TaskCategory.RISK_ASSESSMENT: AgentType.OPTIMUS,
    TaskCategory.DEPENDENCY_ANALYSIS: AgentType.OPTIMUS,
    TaskCategory.PERFORMANCE_PLANNING: AgentType.OPTIMUS,
    TaskCategory.INTEGRATION_DESIGN: AgentType.OPTIMUS,
    # Implementation - GASKET
    TaskCategory.CODE_IMPLEMENTATION: AgentType.GASKET,
    TaskCategory.TEST_GENERATION: AgentType.GASKET,
    TaskCategory.DOCUMENTATION: AgentType.GASKET,
    TaskCategory.BUG_FIX: AgentType.GASKET,
    TaskCategory.FEATURE_DEVELOPMENT: AgentType.GASKET,
}


# =============================================================================
# TASK DEFINITIONS
# =============================================================================


@dataclass
class AgentTask:
    """Task for agent execution"""

    id: str
    category: TaskCategory
    repo: str
    target: Optional[str] = None  # Specific file or component
    params: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def agent_type(self) -> AgentType:
        return TASK_ROUTING[self.category]


@dataclass
class AgentResult:
    """Result from agent execution"""

    task_id: str
    agent: AgentType
    success: bool
    artifacts: List[Path]
    commit_sha: Optional[str] = None
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# BASE AGENT CLASS
# =============================================================================


class BaseAgent(ABC):
    """Base class for specialized agents"""

    agent_type: AgentType
    capabilities: List[TaskCategory]

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.repos_dir = workspace / "repos"
        self.ai = AICodeGenerator()
        self.logger = logging.getLogger(f"agent.{self.agent_type.value}")

    @abstractmethod
    def execute(self, task: AgentTask) -> AgentResult:
        """Execute a task and return result"""
        pass

    def get_repo_path(self, repo_name: str) -> Path:
        """Get path to repo"""
        return self.repos_dir / repo_name

    def commit_artifacts(
        self, repo_path: Path, artifacts: List[Path], message: str
    ) -> Optional[str]:
        """Commit artifacts to git and return SHA"""
        try:
            # Stage files
            for artifact in artifacts:
                rel_path = artifact.relative_to(repo_path)
                subprocess.run(["git", "add", str(rel_path)], cwd=repo_path, capture_output=True)

            # Commit
            result = subprocess.run(
                [
                    "git",
                    "commit",
                    "-m",
                    message,
                    f"--author={self.agent_type.value.upper()} <{self.agent_type.value}@repodepot>",
                ],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                # Get SHA
                sha_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"], cwd=repo_path, capture_output=True, text=True
                )
                return sha_result.stdout.strip()[:8]
            return None
        except Exception as e:
            self.logger.error(f"Commit failed: {e}")
            return None


# =============================================================================
# OPTIMUS AGENT - Strategic
# =============================================================================


class OptimusAgent(BaseAgent):
    """
    Strategic analysis and architecture agent.

    Responsibilities:
    - Architecture Review & Design
    - Risk Assessment
    - Dependency Analysis
    - Performance Optimization Planning
    - Cross-repo Integration Design
    """

    agent_type = AgentType.OPTIMUS
    capabilities = [
        TaskCategory.ARCHITECTURE,
        TaskCategory.RISK_ASSESSMENT,
        TaskCategory.DEPENDENCY_ANALYSIS,
        TaskCategory.PERFORMANCE_PLANNING,
        TaskCategory.INTEGRATION_DESIGN,
    ]

    def execute(self, task: AgentTask) -> AgentResult:
        """Execute strategic task"""
        start = datetime.now()

        handlers = {
            TaskCategory.ARCHITECTURE: self._architecture_review,
            TaskCategory.RISK_ASSESSMENT: self._risk_assessment,
            TaskCategory.DEPENDENCY_ANALYSIS: self._dependency_analysis,
            TaskCategory.PERFORMANCE_PLANNING: self._performance_planning,
            TaskCategory.INTEGRATION_DESIGN: self._integration_design,
        }

        handler = handlers.get(task.category)
        if not handler:
            return AgentResult(
                task_id=task.id,
                agent=self.agent_type,
                success=False,
                artifacts=[],
                errors=[f"No handler for {task.category}"],
            )

        try:
            artifacts = handler(task)
            duration = (datetime.now() - start).total_seconds()

            # Commit if artifacts created
            commit_sha = None
            if artifacts:
                repo_path = self.get_repo_path(task.repo)
                commit_sha = self.commit_artifacts(
                    repo_path, artifacts, f"[OPTIMUS] {task.category.value}: {task.repo}"
                )

            return AgentResult(
                task_id=task.id,
                agent=self.agent_type,
                success=len(artifacts) > 0,
                artifacts=artifacts,
                commit_sha=commit_sha,
                duration_seconds=duration,
                metrics={"files_created": len(artifacts)},
            )

        except Exception as e:
            self.logger.error(f"Task failed: {e}")
            return AgentResult(
                task_id=task.id,
                agent=self.agent_type,
                success=False,
                artifacts=[],
                errors=[str(e)],
            )

    def _architecture_review(self, task: AgentTask) -> List[Path]:
        """Generate architecture documentation with diagrams"""
        repo_path = self.get_repo_path(task.repo)
        if not repo_path.exists():
            raise FileNotFoundError(f"Repo not found: {repo_path}")

        # Analyze structure
        structure = self._analyze_structure(repo_path)

        # Generate with AI
        prompt = f"""Create comprehensive architecture documentation for a repository named "{task.repo}".

Repository Structure:
{json.dumps(structure, indent=2)}

Generate a complete ARCHITECTURE.md with:
1. Executive Summary (2-3 paragraphs)
2. System Overview with ASCII diagram
3. Component breakdown (describe each major component)
4. Data Flow description
5. Dependencies (internal and external)
6. Mermaid diagram for component relationships
7. Deployment Architecture
8. Security Considerations
9. Performance Characteristics
10. Future Roadmap considerations

Be specific to this repository structure. Use markdown formatting.
Include actual mermaid diagrams in ```mermaid blocks.
"""

        content = self.ai.generate(prompt, max_tokens=4000, task_type="architecture")

        # Write file
        output_path = repo_path / "docs" / "ARCHITECTURE.md"
        output_path.parent.mkdir(exist_ok=True)
        output_path.write_text(content)

        self.logger.info(f"Created {output_path}")
        return [output_path]

    def _risk_assessment(self, task: AgentTask) -> List[Path]:
        """Generate risk assessment document"""
        repo_path = self.get_repo_path(task.repo)

        # Gather info for risk analysis
        structure = self._analyze_structure(repo_path)
        deps = self._get_dependencies(repo_path)

        prompt = f"""Create a comprehensive Risk Assessment for repository "{task.repo}".

Structure:
{json.dumps(structure, indent=2)}

Dependencies:
{json.dumps(deps, indent=2)}

Generate RISK_ASSESSMENT.md with:
1. Executive Summary
2. Risk Categories:
   - Technical Risks (complexity, tech debt, architecture issues)
   - Security Risks (vulnerabilities, exposure points)
   - Operational Risks (deployment, maintenance, monitoring)
   - Dependency Risks (outdated packages, supply chain)
3. Risk Matrix (Impact vs Likelihood table)
4. Mitigation Strategies for top 5 risks
5. Recommended Actions (prioritized)
6. Timeline for risk remediation

Use markdown tables for the risk matrix.
"""

        content = self.ai.generate(prompt, max_tokens=3000, task_type="risk_assessment")

        output_path = repo_path / "docs" / "RISK_ASSESSMENT.md"
        output_path.parent.mkdir(exist_ok=True)
        output_path.write_text(content)

        return [output_path]

    def _dependency_analysis(self, task: AgentTask) -> List[Path]:
        """Analyze and document dependencies"""
        repo_path = self.get_repo_path(task.repo)

        deps = self._get_dependencies(repo_path)

        prompt = f"""Create a Dependency Analysis document for repository "{task.repo}".

Found dependencies:
{json.dumps(deps, indent=2)}

Generate DEPENDENCIES.md with:
1. Dependency Overview
2. Direct Dependencies (with versions and purpose)
3. Transitive Dependencies (key ones)
4. Dependency Graph (mermaid diagram)
5. Version Analysis:
   - Outdated packages
   - Security advisories
   - Recommended updates
6. Dependency Health Score
7. Reduction Opportunities
8. Update Roadmap

Include mermaid dependency graph.
"""

        content = self.ai.generate(prompt, max_tokens=2500, task_type="dependency_analysis")

        output_path = repo_path / "docs" / "DEPENDENCIES.md"
        output_path.parent.mkdir(exist_ok=True)
        output_path.write_text(content)

        return [output_path]

    def _performance_planning(self, task: AgentTask) -> List[Path]:
        """Create performance optimization plan"""
        repo_path = self.get_repo_path(task.repo)
        structure = self._analyze_structure(repo_path)

        prompt = f"""Create a Performance Optimization Plan for repository "{task.repo}".

Structure:
{json.dumps(structure, indent=2)}

Generate PERFORMANCE_PLAN.md with:
1. Current State Assessment
2. Performance Metrics to Track
3. Bottleneck Analysis
4. Optimization Opportunities:
   - Code-level optimizations
   - Architecture improvements
   - Caching strategies
   - Database/storage optimizations
5. Implementation Priorities
6. Resource Requirements
7. Expected Improvements (quantified where possible)
8. Monitoring & Validation Plan

Focus on actionable recommendations.
"""

        content = self.ai.generate(prompt, max_tokens=2500, task_type="performance_planning")

        output_path = repo_path / "docs" / "PERFORMANCE_PLAN.md"
        output_path.parent.mkdir(exist_ok=True)
        output_path.write_text(content)

        return [output_path]

    def _integration_design(self, task: AgentTask) -> List[Path]:
        """Design cross-repo integration"""
        repo_path = self.get_repo_path(task.repo)

        # Check for other repos
        other_repos = [
            d.name for d in self.repos_dir.iterdir() if d.is_dir() and d.name != task.repo
        ][:5]

        prompt = f"""Create an Integration Design document for repository "{task.repo}".

Other repos in portfolio: {other_repos}

Generate INTEGRATION_DESIGN.md with:
1. Integration Overview
2. Current Integration Points
3. Proposed Integrations:
   - With other portfolio repos
   - External service integrations
4. API Design (if applicable)
5. Data Flow Diagrams (mermaid)
6. Authentication & Authorization
7. Error Handling Strategy
8. Implementation Phases
9. Testing Strategy for Integrations

Include mermaid sequence diagrams for key flows.
"""

        content = self.ai.generate(prompt, max_tokens=2500, task_type="integration_design")

        output_path = repo_path / "docs" / "INTEGRATION_DESIGN.md"
        output_path.parent.mkdir(exist_ok=True)
        output_path.write_text(content)

        return [output_path]

    def _analyze_structure(self, repo_path: Path) -> Dict[str, Any]:
        """Analyze repository structure"""
        structure = {
            "name": repo_path.name,
            "files": [],
            "directories": [],
            "languages": set(),
        }

        for item in repo_path.iterdir():
            if item.name.startswith("."):
                continue
            if item.is_file():
                structure["files"].append(item.name)
                if item.suffix:
                    structure["languages"].add(item.suffix)
            elif item.is_dir():
                structure["directories"].append(item.name)

        structure["languages"] = list(structure["languages"])
        return structure

    def _get_dependencies(self, repo_path: Path) -> Dict[str, Any]:
        """Extract dependencies from repo"""
        deps = {"python": [], "node": [], "other": []}

        # Python
        req_file = repo_path / "requirements.txt"
        if req_file.exists():
            deps["python"] = [
                line.strip()
                for line in req_file.read_text(encoding='utf-8', errors='replace').splitlines()
                if line.strip() and not line.startswith("#")
            ]

        pyproject = repo_path / "pyproject.toml"
        if pyproject.exists():
            deps["pyproject"] = True

        # Node
        pkg_file = repo_path / "package.json"
        if pkg_file.exists():
            try:
                pkg = json.loads(pkg_file.read_text(encoding='utf-8', errors='replace'))
                deps["node"] = list(pkg.get("dependencies", {}).keys())
            except:
                pass

        return deps


# =============================================================================
# GASKET AGENT - Implementation
# =============================================================================


class GasketAgent(BaseAgent):
    """
    Implementation and building agent.

    Responsibilities:
    - Code Implementation
    - Test Generation
    - Documentation Writing
    - Bug Fixes
    - Feature Development
    """

    agent_type = AgentType.GASKET
    capabilities = [
        TaskCategory.CODE_IMPLEMENTATION,
        TaskCategory.TEST_GENERATION,
        TaskCategory.DOCUMENTATION,
        TaskCategory.BUG_FIX,
        TaskCategory.FEATURE_DEVELOPMENT,
    ]

    def execute(self, task: AgentTask) -> AgentResult:
        """Execute implementation task"""
        start = datetime.now()

        handlers = {
            TaskCategory.CODE_IMPLEMENTATION: self._code_implementation,
            TaskCategory.TEST_GENERATION: self._test_generation,
            TaskCategory.DOCUMENTATION: self._documentation,
            TaskCategory.BUG_FIX: self._bug_fix,
            TaskCategory.FEATURE_DEVELOPMENT: self._feature_development,
        }

        handler = handlers.get(task.category)
        if not handler:
            return AgentResult(
                task_id=task.id,
                agent=self.agent_type,
                success=False,
                artifacts=[],
                errors=[f"No handler for {task.category}"],
            )

        try:
            artifacts = handler(task)
            duration = (datetime.now() - start).total_seconds()

            # Commit if artifacts created
            commit_sha = None
            if artifacts:
                repo_path = self.get_repo_path(task.repo)
                commit_sha = self.commit_artifacts(
                    repo_path, artifacts, f"[GASKET] {task.category.value}: {task.repo}"
                )

            return AgentResult(
                task_id=task.id,
                agent=self.agent_type,
                success=len(artifacts) > 0,
                artifacts=artifacts,
                commit_sha=commit_sha,
                duration_seconds=duration,
                metrics={"files_created": len(artifacts)},
            )

        except Exception as e:
            self.logger.error(f"Task failed: {e}")
            return AgentResult(
                task_id=task.id,
                agent=self.agent_type,
                success=False,
                artifacts=[],
                errors=[str(e)],
            )

    def _code_implementation(self, task: AgentTask) -> List[Path]:
        """Implement code based on spec"""
        repo_path = self.get_repo_path(task.repo)

        spec = task.params.get("spec", "Utility module")
        filename = task.params.get("filename", "utils.py")

        prompt = f"""Implement Python code for repository "{task.repo}".

Specification: {spec}
Filename: {filename}

Generate complete, production-ready Python code with:
1. Module docstring
2. Proper imports
3. Type hints
4. Docstrings for all functions/classes
5. Error handling
6. Logging
7. Example usage in __main__ block

Code should be idiomatic Python following PEP8.
"""

        content = self.ai.generate(prompt, max_tokens=2500, task_type="code_implementation")

        # Ensure it's valid Python
        content = self._extract_python(content)

        output_path = repo_path / "src" / filename
        output_path.parent.mkdir(exist_ok=True)
        output_path.write_text(content)

        return [output_path]

    def _test_generation(self, task: AgentTask) -> List[Path]:
        """Generate test files for source code"""
        repo_path = self.get_repo_path(task.repo)

        # Find source files to test
        source_files = []
        for pattern in ["*.py", "src/*.py", "**/*.py"]:
            source_files.extend(repo_path.glob(pattern))

        # Filter out tests and __pycache__
        source_files = [
            f
            for f in source_files
            if "test" not in f.name.lower() and "__pycache__" not in str(f) and f.is_file()
        ][
            :3
        ]  # Limit to 3 files

        artifacts = []
        for source_file in source_files:
            try:
                source_content = source_file.read_text(encoding='utf-8', errors='replace')
                if len(source_content) < 50:
                    continue

                prompt = f"""Generate comprehensive pytest tests for this Python file from "{task.repo}":

Filename: {source_file.name}
Content:
```python
{source_content[:3000]}
```

Generate tests with:
1. Import statements
2. Fixtures if needed
3. Multiple test functions covering:
   - Happy path
   - Edge cases
   - Error conditions
4. Descriptive test names
5. Assertions with clear messages
6. pytest markers where appropriate

Output only Python code.
"""

                test_content = self.ai.generate(
                    prompt, max_tokens=2000, task_type="test_generation"
                )
                test_content = self._extract_python(test_content)

                # Validate syntax
                try:
                    compile(test_content, "<string>", "exec")
                except SyntaxError:
                    continue

                test_path = repo_path / "tests" / f"test_{source_file.name}"
                test_path.parent.mkdir(exist_ok=True)
                test_path.write_text(test_content)
                artifacts.append(test_path)

            except Exception as e:
                self.logger.warning(f"Failed to generate tests for {source_file}: {e}")

        return artifacts

    def _documentation(self, task: AgentTask) -> List[Path]:
        """Generate documentation"""
        repo_path = self.get_repo_path(task.repo)
        doc_type = task.params.get("type", "readme")

        structure = self._analyze_structure(repo_path)

        if doc_type == "readme":
            prompt = f"""Create a comprehensive README.md for repository "{task.repo}".

Structure:
{json.dumps(structure, indent=2)}

Generate README with:
1. Title and badges
2. Description (clear value proposition)
3. Features list
4. Installation instructions
5. Quick Start / Usage examples
6. Configuration options
7. API Reference (if applicable)
8. Contributing guidelines
9. License

Make it professional and developer-friendly.
"""
            output_name = "README.md"
        elif doc_type == "api":
            prompt = f"""Create API documentation for repository "{task.repo}".

Structure: {json.dumps(structure, indent=2)}

Generate API.md with function/class documentation.
"""
            output_name = "docs/API.md"
        else:
            prompt = f"Create documentation for {task.repo}"
            output_name = f"docs/{doc_type.upper()}.md"

        content = self.ai.generate(prompt, max_tokens=3000, task_type="documentation")

        output_path = repo_path / output_name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)

        return [output_path]

    def _bug_fix(self, task: AgentTask) -> List[Path]:
        """Fix a bug in code"""
        repo_path = self.get_repo_path(task.repo)

        target_file = task.params.get("file")
        bug_description = task.params.get("description", "General bug fix")

        if not target_file:
            return []

        target_path = repo_path / target_file
        if not target_path.exists():
            return []

        original_content = target_path.read_text(encoding='utf-8', errors='replace')

        prompt = f"""Fix the following bug in this Python file:

Bug Description: {bug_description}

Current Code:
```python
{original_content[:4000]}
```

Provide the COMPLETE fixed file content.
Explain the fix in a comment at the top.
"""

        fixed_content = self.ai.generate(prompt, max_tokens=4000, task_type="bug_fix")
        fixed_content = self._extract_python(fixed_content)

        # Validate
        try:
            compile(fixed_content, "<string>", "exec")
        except SyntaxError:
            return []

        target_path.write_text(fixed_content)
        return [target_path]

    def _feature_development(self, task: AgentTask) -> List[Path]:
        """Develop a new feature"""
        repo_path = self.get_repo_path(task.repo)

        feature_name = task.params.get("name", "new_feature")
        feature_spec = task.params.get("spec", "New feature implementation")

        prompt = f"""Implement a new feature for repository "{task.repo}".

Feature: {feature_name}
Specification: {feature_spec}

Generate a complete Python module with:
1. Feature implementation
2. Configuration options
3. Error handling
4. Logging
5. Type hints
6. Docstrings
7. Example usage

Output production-ready code.
"""

        content = self.ai.generate(prompt, max_tokens=3000, task_type="feature_development")
        content = self._extract_python(content)

        filename = f"{feature_name.lower().replace(' ', '_')}.py"
        output_path = repo_path / "src" / "features" / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)

        return [output_path]

    def _analyze_structure(self, repo_path: Path) -> Dict[str, Any]:
        """Analyze repository structure"""
        structure = {"name": repo_path.name, "files": [], "directories": []}

        for item in repo_path.iterdir():
            if item.name.startswith("."):
                continue
            if item.is_file():
                structure["files"].append(item.name)
            elif item.is_dir():
                structure["directories"].append(item.name)

        return structure

    def _extract_python(self, content: str) -> str:
        """Extract Python code from markdown code blocks"""
        import re

        # Find python code blocks
        pattern = r"```python\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)

        if matches:
            return "\n\n".join(matches)

        # If no code blocks, assume it's raw code
        return content


# =============================================================================
# AGENT DISPATCHER
# =============================================================================


class AgentDispatcher:
    """
    Routes tasks to appropriate agents based on task category.
    Manages agent instances and execution.
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.optimus = OptimusAgent(workspace)
        self.gasket = GasketAgent(workspace)
        self.agents = {
            AgentType.OPTIMUS: self.optimus,
            AgentType.GASKET: self.gasket,
        }
        self.execution_log: List[AgentResult] = []

        logger.info("Agent Dispatcher initialized")
        logger.info(f"  OPTIMUS capabilities: {[c.value for c in self.optimus.capabilities]}")
        logger.info(f"  GASKET capabilities: {[c.value for c in self.gasket.capabilities]}")

    def dispatch(self, task: AgentTask) -> AgentResult:
        """Dispatch task to appropriate agent"""
        agent_type = task.agent_type
        agent = self.agents[agent_type]

        logger.info(f"Dispatching {task.category.value} to {agent_type.value}")

        result = agent.execute(task)
        self.execution_log.append(result)

        if result.success:
            logger.info(f"Task {task.id} completed: {len(result.artifacts)} artifacts")
        else:
            logger.warning(f"Task {task.id} failed: {result.errors}")

        return result

    def create_task(
        self, category: TaskCategory, repo: str, target: Optional[str] = None, **params
    ) -> AgentTask:
        """Helper to create tasks"""
        task_id = f"{category.value}_{repo}_{datetime.now().strftime('%H%M%S')}"
        return AgentTask(id=task_id, category=category, repo=repo, target=target, params=params)

    def run_strategic_analysis(self, repo: str) -> List[AgentResult]:
        """Run full strategic analysis on a repo (OPTIMUS)"""
        results = []

        for category in self.optimus.capabilities:
            task = self.create_task(category, repo)
            result = self.dispatch(task)
            results.append(result)

        return results

    def run_implementation_tasks(self, repo: str) -> List[AgentResult]:
        """Run implementation tasks on a repo (GASKET)"""
        results = []

        # Tests and docs for all repos
        for category in [TaskCategory.TEST_GENERATION, TaskCategory.DOCUMENTATION]:
            task = self.create_task(category, repo, type="readme")
            result = self.dispatch(task)
            results.append(result)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        stats = {
            "total_tasks": len(self.execution_log),
            "successful": sum(1 for r in self.execution_log if r.success),
            "failed": sum(1 for r in self.execution_log if not r.success),
            "by_agent": {
                "optimus": sum(1 for r in self.execution_log if r.agent == AgentType.OPTIMUS),
                "gasket": sum(1 for r in self.execution_log if r.agent == AgentType.GASKET),
            },
            "artifacts_created": sum(len(r.artifacts) for r in self.execution_log),
            "total_duration": sum(r.duration_seconds for r in self.execution_log),
        }
        return stats


# =============================================================================
# CLI INTERFACE
# =============================================================================


def main():
    """Run Phase 4 Agent Specialization demo"""
    import argparse

    parser = argparse.ArgumentParser(description="REPODEPOT Agent Specialization")
    parser.add_argument("--repo", required=True, help="Repository to process")
    parser.add_argument(
        "--agent", choices=["optimus", "gasket", "both"], default="both", help="Agent to run"
    )
    parser.add_argument("--workspace", default=".", help="Workspace path")

    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    dispatcher = AgentDispatcher(workspace)

    print(f"\n{'='*60}")
    print("REPODEPOT Phase 4: Agent Specialization")
    print(f"{'='*60}")
    print(f"Repository: {args.repo}")
    print(f"Agent(s): {args.agent}")
    print()

    results = []

    if args.agent in ["optimus", "both"]:
        print("Running OPTIMUS (Strategic Analysis)...")
        results.extend(dispatcher.run_strategic_analysis(args.repo))

    if args.agent in ["gasket", "both"]:
        print("\nRunning GASKET (Implementation)...")
        results.extend(dispatcher.run_implementation_tasks(args.repo))

    print(f"\n{'='*60}")
    print("Results:")
    print(f"{'='*60}")

    for r in results:
        status = "✓" if r.success else "✗"
        agent = r.agent.value.upper()
        artifacts = ", ".join(str(a.name) for a in r.artifacts) if r.artifacts else "none"
        print(f"  [{status}] {agent}: {len(r.artifacts)} artifact(s) - {artifacts}")

    stats = dispatcher.get_stats()
    print(
        f"\nStats: {stats['successful']}/{stats['total_tasks']} succeeded, {stats['artifacts_created']} files created"
    )


if __name__ == "__main__":
    main()
