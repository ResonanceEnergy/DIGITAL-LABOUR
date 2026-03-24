# REPODEPOT COMPREHENSIVE FIX PLAN
## From Simulation to Real Production
**Created:** 2026-02-24
**Status:** CRITICAL - Current system produces no real output

---

## 🚨 PROBLEM STATEMENT

### Current State: Simulated Work
| Claimed | Actual |
|---------|--------|
| 1,172 tasks "completed" | 0 real code produced |
| 482 OPTIMUS tasks | 0 files created |
| 690 GASKET tasks | 0 commits made |
| 95 pending tasks | Tasks regenerate infinitely |

### Root Causes Identified
1. **No Execution Engine** - Tasks marked complete without work
2. **Counter Inflation** - Every 2 seconds, 6 fake completions
3. **No Code Generation** - `complete_task()` creates no files
4. **No Verification** - No QA validates output
5. **Circular Queue** - Empty queue just regenerates same tasks
6. **Misleading Metrics** - `production_state.json` shows fake progress

### Code Evidence (production_agent_collaboration.py:418-431)
```python
def process_agent_tasks(agent, batch_size=3):
    for _ in range(batch_size):
        task = self.get_next_task(agent)
        if task:
            self.assign_task(task, agent)
            self.start_task(task)
            # ⚠️ IMMEDIATELY COMPLETES - NO ACTUAL WORK
            self.complete_task(task, [f"artifact_{task.id}.log"])
```

---

## ✅ WHAT REAL WORK LOOKS LIKE

Based on REPO_DEPOT_DOCTRINE.md and ROADMAP.md, real tasks should produce:

### Tangible Outputs
| Task Type | Expected Output | Verification |
|-----------|-----------------|--------------|
| Architecture Review | `docs/ARCHITECTURE.md` with diagrams | File exists, >100 lines |
| Code Generation | `.py` files in target repo | Syntax valid, tests pass |
| Documentation | README updates, API docs | Schema compliance |
| Testing | `tests/*.py` with assertions | pytest passes |
| Integration | Updated `requirements.txt`, configs | Dependencies resolve |

### Git Evidence
Every completed task MUST produce:
- 1+ file changes
- 1 git commit with task ID
- Verifiable diff

---

## 📋 COMPREHENSIVE FIX PLAN

### PHASE 1: Foundation (Immediate - Day 1-3)

#### 1.1 Create Real Task Executor
Replace fake completion with actual work execution:

```python
# New file: task_executor.py
class TaskExecutor:
    def execute_task(self, task: Task) -> ExecutionResult:
        """Execute task and produce real artifacts"""

        handler = self.get_handler(task.title)

        # Execute the actual work
        result = handler.execute(
            repo=task.repo,
            workspace=self.workspace,
            context=self.get_context(task)
        )

        # Verify output exists
        if not self.verify_output(result.artifacts):
            raise TaskExecutionError("No artifacts produced")

        # Commit changes
        commit_sha = self.git_commit(
            message=f"[{task.id}] {task.title}",
            files=result.artifacts
        )

        return ExecutionResult(
            task_id=task.id,
            commit_sha=commit_sha,
            artifacts=result.artifacts,
            metrics=result.metrics
        )
```

#### 1.2 Define Task Handlers
Create specific handlers for each task type:

| Handler | Input | Output |
|---------|-------|--------|
| `ArchitectureReviewHandler` | repo name | `docs/ARCHITECTURE.md` |
| `DocumentationHandler` | repo + code | Updated `README.md` |
| `CodeAnalysisHandler` | repo | `reports/analysis.json` |
| `TestGenerationHandler` | source files | `tests/test_*.py` |
| `DependencyCheckHandler` | requirements | Updated `requirements.txt` |

#### 1.3 Create Verification System
```python
class TaskVerifier:
    def verify_completion(self, task: Task, result: ExecutionResult) -> bool:
        checks = [
            self.artifacts_exist(result.artifacts),
            self.git_commit_valid(result.commit_sha),
            self.file_not_empty(result.artifacts),
            self.passes_quality_gate(result),
        ]
        return all(checks)
```

---

### PHASE 2: Integration (Day 4-7)

#### 2.1 Connect to Real Repos
Currently: Tasks reference repos but don't touch them.
Fix: Clone/pull repos and make real changes.

```python
class RepoManager:
    def __init__(self, portfolio_path: str):
        self.repos = self.load_portfolio(portfolio_path)
        self.workspace = Path("./active_repos")

    def ensure_repo_available(self, repo_name: str) -> Path:
        """Clone or pull repo for work"""
        repo_path = self.workspace / repo_name

        if not repo_path.exists():
            subprocess.run([
                "git", "clone",
                f"git@github.com:ResonanceEnergy/{repo_name}.git",
                str(repo_path)
            ])
        else:
            subprocess.run(["git", "pull"], cwd=repo_path)

        return repo_path
```

#### 2.2 AI Integration for Code Generation
Use Copilot/Claude/Gemini APIs for actual work:

```python
class AICodeGenerator:
    def generate_documentation(self, repo_path: Path) -> str:
        """Generate real README content"""

        # Analyze repo structure
        files = list(repo_path.rglob("*.py"))

        # Build context
        context = self.build_context(files)

        # Call AI API
        response = self.ai_client.complete(
            prompt=f"Generate comprehensive README for: {context}",
            max_tokens=2000
        )

        return response.text

    def generate_tests(self, source_file: Path) -> str:
        """Generate real test file"""
        source = source_file.read_text()

        response = self.ai_client.complete(
            prompt=f"Generate pytest tests for:\n{source}",
            max_tokens=1500
        )

        return response.text
```

#### 2.3 Quality Gates
Before marking complete, verify quality:

```python
class QualityGate:
    def check_python_file(self, file_path: Path) -> QualityResult:
        results = {
            "syntax": self.check_syntax(file_path),
            "imports": self.check_imports(file_path),
            "lint": self.run_ruff(file_path),
            "tests": self.run_tests(file_path),
        }
        return QualityResult(
            passed=all(r.passed for r in results.values()),
            details=results
        )
```

---

### PHASE 3: Portfolio Operations (Day 8-14)

#### 3.1 Prioritize Real Repos
Current portfolio has 27 repos. Focus on:

| Priority | Repos | Reason |
|----------|-------|--------|
| 1 (L tier) | Super-Agency, NCC-Doctrine, AAC, NCL | Core infrastructure |
| 2 (L tier) | Resonance-Energy-Systems, ResonanceEnergy_Enterprise | Enterprise |
| 3 (M tier) | YOUTUBEDROP, TESLA-TECH, NATEBJONES | Active projects |
| 4 (S tier) | Others | Lower priority |

#### 3.2 Define Repo-Specific Task Templates
Each repo needs appropriate tasks:

```yaml
# task_templates.yaml
Super-Agency:
  tasks:
    - type: documentation
      files: [README.md, ARCHITECTURE.md]
      frequency: weekly
    - type: dependency_audit
      frequency: daily
    - type: test_coverage
      target: 80%
      frequency: weekly

AAC:
  tasks:
    - type: financial_validation
      frequency: daily
    - type: compliance_check
      frequency: weekly
```

#### 3.3 Implement Progress Persistence
Real progress tracking with git history:

```python
class ProgressTracker:
    def get_real_progress(self, repo: str) -> RepoProgress:
        """Calculate progress from actual git commits"""
        repo_path = self.repos[repo]

        # Count commits from agents
        commits = subprocess.check_output([
            "git", "log", "--oneline",
            "--author=OPTIMUS", "--author=GASKET",
            "--since=7 days ago"
        ], cwd=repo_path)

        # Count files changed
        diff = subprocess.check_output([
            "git", "diff", "--stat", "HEAD~10"
        ], cwd=repo_path)

        return RepoProgress(
            commits=len(commits.splitlines()),
            files_changed=len(diff.splitlines()),
            last_activity=self.get_last_commit_date(repo_path)
        )
```

---

### PHASE 4: Agent Specialization (Day 15-21)

#### 4.1 OPTIMUS Role (Strategic)
```python
class OptimusAgent:
    """Strategic analysis and architecture"""

    tasks = [
        "Architecture Review",
        "Risk Assessment",
        "Dependency Analysis",
        "Performance Optimization Planning",
        "Cross-repo Integration Design",
    ]

    def execute_architecture_review(self, repo: str) -> list[Path]:
        """Produce real architecture documentation"""
        repo_path = self.get_repo(repo)

        # Analyze structure
        structure = self.analyze_structure(repo_path)

        # Generate diagram (mermaid)
        diagram = self.generate_diagram(structure)

        # Write file
        output = repo_path / "docs" / "ARCHITECTURE.md"
        output.parent.mkdir(exist_ok=True)
        output.write_text(f"""# Architecture

## System Overview
{structure.summary}

## Component Diagram
```mermaid
{diagram}
```

## Dependencies
{structure.dependencies}
""")

        return [output]
```

#### 4.2 GASKET Role (Implementation)
```python
class GasketAgent:
    """Implementation and building"""

    tasks = [
        "Code Implementation",
        "Test Generation",
        "Documentation Writing",
        "Bug Fixes",
        "Feature Development",
    ]

    def execute_test_generation(self, source_file: Path) -> list[Path]:
        """Generate real test file"""

        source = source_file.read_text()

        # Use AI to generate tests
        tests = self.ai.generate_tests(source)

        # Validate tests
        if not self.validate_python(tests):
            raise ValueError("Generated tests have syntax errors")

        # Write file
        test_path = source_file.parent / "tests" / f"test_{source_file.name}"
        test_path.parent.mkdir(exist_ok=True)
        test_path.write_text(tests)

        # Run tests to verify
        result = subprocess.run(
            ["pytest", str(test_path), "-v"],
            capture_output=True
        )

        return [test_path]
```

---

### PHASE 5: QA & Verification (Day 22-28)

#### 5.1 Manual QA Interface
Create dashboard for human verification:

```python
# qa_dashboard.py
def show_pending_qa():
    """Show tasks awaiting QA"""
    pending = Task.objects.filter(status="completed", qa_status="pending")

    for task in pending:
        print(f"Task: {task.title}")
        print(f"Artifacts: {task.artifacts}")
        print(f"Commit: {task.commit_sha}")
        print("---")

        # Show diff
        subprocess.run(["git", "show", task.commit_sha])

        # Prompt for approval
        approved = input("Approve? (y/n): ")
        if approved == "y":
            task.qa_status = "approved"
        else:
            task.qa_status = "rejected"
            task.status = "pending"  # Send back for retry
```

#### 5.2 Automated Quality Checks
```python
class AutomatedQA:
    checks = [
        "syntax_valid",
        "no_hardcoded_secrets",
        "imports_resolve",
        "file_not_empty",
        "passes_lint",
        "docstrings_present",
    ]

    def run_all_checks(self, artifacts: list[Path]) -> QAResult:
        results = {}
        for artifact in artifacts:
            results[artifact] = {
                check: getattr(self, check)(artifact)
                for check in self.checks
            }
        return QAResult(results)
```

#### 5.3 Production Metrics
Track REAL progress:

```python
class RealMetrics:
    def calculate(self) -> dict:
        return {
            "lines_of_code_added": self.count_loc_added(),
            "files_created": self.count_new_files(),
            "tests_added": self.count_new_tests(),
            "test_coverage_change": self.calculate_coverage_delta(),
            "commits_pushed": self.count_commits(),
            "repos_touched": self.count_active_repos(),
            "qa_approval_rate": self.calculate_qa_rate(),
        }
```

---

## 📁 NEW FILE STRUCTURE

```
repo_depot/
├── agents/
│   ├── __init__.py           # Agent registry
│   ├── optimus.py            # Strategic agent
│   ├── gasket.py             # Implementation agent
│   └── base.py               # Base agent class
│
├── core/
│   ├── __init__.py
│   ├── task_executor.py      # Real task execution
│   ├── repo_manager.py       # Git operations
│   ├── ai_generator.py       # AI code generation
│   └── quality_gate.py       # Quality checks
│
├── flywheel/
│   ├── __init__.py
│   ├── orchestrator.py       # Task scheduling
│   ├── progress_tracker.py   # Real progress
│   └── metrics.py            # Production metrics
│
├── templates/
│   ├── architecture.md.j2    # Doc templates
│   ├── readme.md.j2
│   └── test_file.py.j2
│
├── qa/
│   ├── __init__.py
│   ├── automated_checks.py   # Auto QA
│   ├── manual_review.py      # Human QA
│   └── dashboard.py          # QA UI
│
└── config/
    ├── task_templates.yaml   # Task definitions
    ├── repo_priorities.yaml  # Portfolio config
    └── quality_settings.yaml # QA thresholds
```

---

## 🎯 SUCCESS CRITERIA

### Week 1 Milestones
- [ ] Task executor creates real files
- [ ] Git commits from agent actions
- [ ] 1 repo has agent-generated README

### Week 2 Milestones
- [ ] 3 repos have agent-generated documentation
- [ ] Test files generated and passing
- [ ] QA dashboard functional

### Week 3 Milestones
- [ ] All L-tier repos (7) have agent activity
- [ ] 50+ real commits from agents
- [ ] Automated QA catching issues

### Week 4 Milestones
- [ ] Full portfolio coverage
- [ ] Human QA review process
- [ ] Metrics dashboard accurate

---

## 🔧 IMMEDIATE ACTIONS

### Today
1. **STOP** the current fake production cycle
2. **RESET** production_state.json to zero
3. **CREATE** task_executor.py skeleton

### This Week
1. Implement `ArchitectureReviewHandler` for ONE repo
2. Test with Super-Agency repo
3. Verify git commit appears on GitHub

### Command to Reset
```bash
cd "$HOME/repos/SuperAgency-Shared"

# Reset fake metrics
echo '{
  "timestamp": "'$(date -Iseconds)'",
  "system": "Quantum Quasar",
  "last_sync": null,
  "agent_status": {
    "optimus": {"status": "rebuilding", "tasks_completed": 0},
    "gasket": {"status": "rebuilding", "tasks_completed": 0}
  },
  "pending_tasks": 0,
  "completed_tasks": 0,
  "note": "RESET - Transitioning from simulation to real production"
}' > production_state.json

# Remove from master orchestrator temporarily
# Until real executor is ready
```

---

## 📊 COMPARISON: Before vs After

| Aspect | Before (Simulation) | After (Real) |
|--------|---------------------|--------------|
| Task completion | 2 seconds | Minutes-hours |
| Output | Counter increment | Files + commits |
| Verification | None | Automated + Human QA |
| Progress | Fake JSON | Git history |
| Portfolio impact | Zero | Real changes |
| Auditability | Impossible | Full git trail |

---

## 🏗️ IMPLEMENTATION PRIORITY

1. **task_executor.py** - Core execution engine
2. **repo_manager.py** - Git operations
3. **One handler** - ArchitectureReviewHandler
4. **quality_gate.py** - Basic checks
5. **Reset pipeline** - Remove fake completion

This document is the **plan to make a plan** operational. The next step is implementing [task_executor.py](repo_depot/core/task_executor.py) with real execution logic.

---

*Document Version: 1.0*
*Author: Audit Agent*
*Reviewed: Pending CEO approval*
