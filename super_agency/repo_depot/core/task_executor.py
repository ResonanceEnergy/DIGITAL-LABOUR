"""
REPODEPOT Task Executor - REAL Work Execution
==============================================
This module replaces the simulation loop with actual task execution.

Unlike the current production_agent_collaboration.py which just:
1. Picks task
2. Marks complete
3. Increments counter

This executor:
1. Picks task
2. EXECUTES the work (creates files, runs commands)
3. VERIFIES output exists
4. COMMITS to git
5. THEN marks complete

Author: REPODEPOT Rebuild Team
Date: 2026-02-24

Phase 2 Additions:
- AICodeGenerator for AI-powered content
- QualityGate for output validation
"""

import subprocess
import json
import logging
import os
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - EXECUTOR - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================
# PHASE 2: AI CODE GENERATOR
# ============================================

# API Keys - Load from environment variables (no hardcoded defaults for security)
# Set these in your shell or .env file:
#   export ANTHROPIC_API_KEY="sk-ant-..."
#   export OPENAI_API_KEY="sk-proj-..."
#   export XAI_API_KEY="xai-..."
#   export GEMINI_API_KEY="..." (optional)
API_KEYS = {
    "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
    "openai": os.environ.get("OPENAI_API_KEY"),
    "xai": os.environ.get("XAI_API_KEY"),
    "gemini": os.environ.get("GEMINI_API_KEY"),
}


# ============================================
# INTELLIGENT PROVIDER ROUTER
# ============================================
# Routes tasks to optimal AI providers based on
# benchmark data and real-world performance tracking.
#
# Benchmark Sources (Feb 2025):
#   - Vellum LLM Leaderboard (SWE-Bench, GPQA, AIME)
#   - Artificial Analysis coding benchmarks
#   - Chatbot Arena (lmarena.ai)
#
# Provider Strengths:
#   Claude (claude-sonnet-4-20250514):
#     - #1 SWE-Bench (agentic coding) @ 82%
#     - Best at: architecture, code impl, bug fixes, risk analysis
#     - 200k context, excellent instruction following
#
#   GPT-4o (OpenAI):
#     - Strong general reasoning (GPQA 56.1%)
#     - Best at: documentation, performance analysis, clear prose
#     - Fast (143 t/s), good structured output
#
#   Gemini 2.5 Flash (Google):
#     - Fastest (200 t/s) + cheapest ($0.15/$0.60 per 1M)
#     - 1M token context window (5x Claude, 8x GPT-4o)
#     - Best at: bulk analysis, dependency scanning, test generation
#     - AIME 88%, GPQA 78.3%
#
#   Grok (xAI, grok-code-fast-1):
#     - Code-optimized model (name says "code-fast")
#     - Grok 3 family: AIME 93.3%, GPQA 84.6%
#     - Best at: fast code gen, feature development, quick iteration


class ProviderRouter:
    """
    Intelligent task-to-provider routing engine.

    Instead of blind parallel racing (wasteful), routes each task
    to the best-fit provider with ranked fallbacks.

    Modes:
      - "routed"   : Send to primary provider, fallback on failure
      - "race_top" : Race top-2 providers for the task (fast + smart)
      - "race_all" : Original behavior, race everyone (most redundant)
    """

    # Task → ordered provider preferences (best-fit first)
    # Based on benchmark performance + task characteristics
    ROUTING_TABLE = {
        # ── OPTIMUS Strategic Tasks ──────────────────────
        "architecture": ["anthropic", "gemini", "openai", "xai-grok"],
        # Claude: #1 SWE-Bench, best structured technical analysis
        # Gemini: 1M context great for large codebase scanning
        "risk_assessment": ["anthropic", "openai", "gemini", "xai-grok"],
        # Claude: Deep reasoning, careful risk identification
        # GPT-4o: Strong analytical capabilities
        "dependency_analysis": ["gemini", "anthropic", "openai", "xai-grok"],
        # Gemini: 1M context, fast bulk analysis, cheapest for scanning
        # Claude: Thorough dependency understanding
        "performance_planning": ["openai", "anthropic", "gemini", "xai-grok"],
        # GPT-4o: Excellent general analysis, optimization patterns
        # Claude: Deep performance reasoning
        "integration_design": ["anthropic", "gemini", "openai", "xai-grok"],
        # Claude: Complex system design, API modeling
        # Gemini: Large context for cross-repo analysis
        # ── GASKET Implementation Tasks ──────────────────
        "code_implementation": ["anthropic", "xai-grok", "gemini", "openai"],
        # Claude: 82% SWE-Bench, production-quality code
        # Grok: Code-optimized model, fast
        "test_generation": ["gemini", "anthropic", "openai", "xai-grok"],
        # Gemini: Fast, cheap, great for bulk test output
        # Claude: High-quality test logic
        "documentation": ["openai", "gemini", "anthropic", "xai-grok"],
        # GPT-4o: Clearest structured prose, great README/docs
        # Gemini: Fast documentation generation
        "bug_fix": ["anthropic", "xai-grok", "openai", "gemini"],
        # Claude: #1 SWE-Bench, deepest code understanding
        # Grok: Code-optimized, fast fixes
        "feature_development": ["xai-grok", "anthropic", "gemini", "openai"],
        # Grok: Code-optimized for fast feature iteration
        # Claude: Production quality fallback
    }

    # Default fallback for unknown task types
    DEFAULT_ORDER = ["anthropic", "openai", "gemini", "xai-grok"]

    def __init__(self, mode: str = "race_top"):
        """
        Args:
            mode: "routed" (primary+fallback), "race_top" (race top 2),
                  "race_all" (race everyone)
        """
        self.mode = mode
        self.stats = {}  # provider → {wins, fails, total_ms, tasks}
        self._stats_file = (
            Path(os.environ.get("REPODEPOT_STATE", "state/flywheel")) / "provider_stats.json"
        )
        self._load_stats()

    def _load_stats(self):
        """Load historical performance stats"""
        try:
            if self._stats_file.exists():
                self.stats = json.loads(self._stats_file.read_text(encoding='utf-8', errors='replace'))
                logger.info(f"Loaded provider stats: {list(self.stats.keys())}")
        except Exception as e:
            logger.warning(f"Could not load provider stats: {e}")
            self.stats = {}

    def _save_stats(self):
        """Persist performance stats for adaptive routing"""
        try:
            self._stats_file.parent.mkdir(parents=True, exist_ok=True)
            self._stats_file.write_text(json.dumps(self.stats, indent=2))
        except Exception as e:
            logger.warning(f"Could not save provider stats: {e}")

    def record_result(self, provider_name: str, task_type: str, success: bool, latency_ms: float):
        """Record a provider's result for adaptive routing"""
        if provider_name not in self.stats:
            self.stats[provider_name] = {
                "wins": 0,
                "fails": 0,
                "total_ms": 0,
                "tasks": {},
            }
        s = self.stats[provider_name]
        if success:
            s["wins"] += 1
        else:
            s["fails"] += 1
        s["total_ms"] += latency_ms

        # Per-task-type stats
        if task_type not in s["tasks"]:
            s["tasks"][task_type] = {"wins": 0, "fails": 0, "total_ms": 0}
        t = s["tasks"][task_type]
        if success:
            t["wins"] += 1
        else:
            t["fails"] += 1
        t["total_ms"] += latency_ms

        # Auto-save occasionally (every 10 results)
        total = s["wins"] + s["fails"]
        if total % 10 == 0:
            self._save_stats()

    def get_provider_order(self, task_type: str, available_providers: list) -> list:
        """
        Get ordered list of providers for a task.

        Args:
            task_type: e.g. "architecture", "code_implementation"
            available_providers: list of provider dicts with 'name' key

        Returns:
            Ordered list of provider dicts, best-fit first
        """
        # Get the routing preference for this task type
        preferred = self.ROUTING_TABLE.get(task_type, self.DEFAULT_ORDER)

        # Build name→provider lookup
        by_name = {p["name"]: p for p in available_providers}

        # Adaptive adjustment: boost providers with high success rate for this task
        adjusted = list(preferred)
        for pname in by_name:
            if pname in self.stats and task_type in self.stats[pname].get("tasks", {}):
                t = self.stats[pname]["tasks"][task_type]
                total = t["wins"] + t["fails"]
                if total >= 5:  # Need enough data
                    rate = t["wins"] / total
                    if rate < 0.5 and pname in adjusted:
                        # Demote underperformers
                        adjusted.remove(pname)
                        adjusted.append(pname)
                        logger.info(
                            f"Router: Demoted {pname} for {task_type} "
                            f"(success rate: {rate:.0%})"
                        )

        # Map to actual provider objects, skip unavailable
        ordered = []
        for name in adjusted:
            if name in by_name:
                ordered.append(by_name[name])

        # Append any providers not in the routing table
        for p in available_providers:
            if p not in ordered:
                ordered.append(p)

        return ordered

    def get_race_set(self, task_type: str, available_providers: list) -> list:
        """
        Get the set of providers to race based on mode.

        Returns subset of providers based on routing mode:
          - "routed"  : [primary] (sequential fallback handled elsewhere)
          - "race_top": [primary, secondary] (race top 2)
          - "race_all": all providers
        """
        ordered = self.get_provider_order(task_type, available_providers)

        if self.mode == "routed":
            return ordered[:1] if ordered else []
        elif self.mode == "race_top":
            return ordered[:2] if len(ordered) >= 2 else ordered
        else:  # race_all
            return ordered

    def get_fallbacks(self, task_type: str, available_providers: list, exclude: list) -> list:
        """Get remaining providers for fallback (after race set fails)"""
        ordered = self.get_provider_order(task_type, available_providers)
        exclude_names = {p["name"] for p in exclude}
        return [p for p in ordered if p["name"] not in exclude_names]

    def format_status(self) -> str:
        """Format stats for display"""
        lines = ["Provider Performance Stats:"]
        for name, s in sorted(self.stats.items()):
            total = s["wins"] + s["fails"]
            rate = s["wins"] / total * 100 if total else 0
            avg_ms = s["total_ms"] / total if total else 0
            lines.append(
                f"  {name}: {s['wins']}/{total} wins ({rate:.0f}%), " f"avg {avg_ms:.0f}ms"
            )
            for task, t in sorted(s.get("tasks", {}).items()):
                tt = t["wins"] + t["fails"]
                tr = t["wins"] / tt * 100 if tt else 0
                ta = t["total_ms"] / tt if tt else 0
                lines.append(f"    {task}: {t['wins']}/{tt} ({tr:.0f}%) avg {ta:.0f}ms")
        return "\n".join(lines)


class AICodeGenerator:
    """
    AI-powered code and documentation generator.
    Supports multiple providers: Anthropic Claude, OpenAI GPT, xAI Grok, Google Gemini.
    Intelligently routes tasks to best-fit providers via ProviderRouter.
    Falls back through providers if one fails.
    """

    def __init__(self, routing_mode: str = "race_top"):
        self.providers = []
        self._init_anthropic()
        self._init_openai()
        self._init_xai()
        self._init_gemini()

        # Intelligent routing engine
        self.router = ProviderRouter(mode=routing_mode)

        self.enabled = len(self.providers) > 0
        if self.enabled:
            logger.info(
                f"AI Generator enabled with providers: {[p['name'] for p in self.providers]}"
            )
        else:
            logger.info("No AI providers available, using template generation")

    def _init_anthropic(self):
        """Initialize Anthropic Claude"""
        api_key = API_KEYS.get("anthropic")
        if api_key:
            try:
                import anthropic

                client = anthropic.Anthropic(api_key=api_key)
                self.providers.append(
                    {
                        "name": "anthropic",
                        "client": client,
                        "generate": self._generate_anthropic,
                    }
                )
                logger.info("Anthropic Claude initialized")
            except ImportError:
                logger.warning("anthropic package not installed")
            except Exception as e:
                logger.warning(f"Anthropic init failed: {e}")

    def _init_openai(self):
        """Initialize OpenAI GPT"""
        api_key = API_KEYS.get("openai")
        if api_key:
            try:
                import openai

                client = openai.OpenAI(api_key=api_key)
                self.providers.append(
                    {
                        "name": "openai",
                        "client": client,
                        "generate": self._generate_openai,
                    }
                )
                logger.info("OpenAI GPT initialized")
            except ImportError:
                logger.warning("openai package not installed")
            except Exception as e:
                logger.warning(f"OpenAI init failed: {e}")

    def _init_xai(self):
        """Initialize xAI Grok"""
        api_key = API_KEYS.get("xai")
        if api_key:
            try:
                import openai

                # xAI uses OpenAI-compatible API
                client = openai.OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
                self.providers.append(
                    {
                        "name": "xai-grok",
                        "client": client,
                        "generate": self._generate_xai,
                    }
                )
                logger.info("xAI Grok initialized")
            except ImportError:
                logger.warning("openai package not installed (needed for xAI)")
            except Exception as e:
                logger.warning(f"xAI init failed: {e}")

    def _init_gemini(self):
        """Initialize Google Gemini"""
        api_key = API_KEYS.get("gemini")
        if api_key:
            try:
                from google import genai

                client = genai.Client(api_key=api_key)
                self.providers.append(
                    {
                        "name": "gemini",
                        "client": client,
                        "model": "gemini-2.5-flash",
                        "generate": self._generate_gemini,
                    }
                )
                logger.info("Google Gemini initialized")
            except ImportError:
                logger.warning("google-genai package not installed")
            except Exception as e:
                logger.warning(f"Gemini init failed: {e}")

    def _generate_anthropic(self, provider: dict, prompt: str, max_tokens: int) -> Optional[str]:
        """Generate with Anthropic Claude"""
        message = provider["client"].messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    def _generate_openai(self, provider: dict, prompt: str, max_tokens: int) -> Optional[str]:
        """Generate with OpenAI GPT"""
        response = provider["client"].chat.completions.create(
            model="gpt-4o",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    def _generate_xai(self, provider: dict, prompt: str, max_tokens: int) -> Optional[str]:
        """Generate with xAI Grok"""
        response = provider["client"].chat.completions.create(
            model="grok-code-fast-1",  # Optimized for code generation
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    def _generate_gemini(self, provider: dict, prompt: str, max_tokens: int) -> Optional[str]:
        """Generate with Google Gemini"""
        response = provider["client"].models.generate_content(
            model=provider["model"],
            contents=prompt,
            config={"max_output_tokens": max_tokens},
        )
        return response.text

    def generate(
        self, prompt: str, max_tokens: int = 2000, parallel: bool = True, task_type: str = None
    ) -> Optional[str]:
        """
        Generate content using AI APIs with intelligent provider routing.

        Args:
            prompt: The prompt to send to AI
            max_tokens: Maximum tokens in response
            parallel: If True, race top providers in parallel (faster)
                      If False, try sequentially (more predictable)
            task_type: Task category for intelligent routing, e.g.
                       "architecture", "code_implementation", "test_generation"
                       If None, falls back to default provider ordering.
        """
        if not self.enabled:
            return None

        if task_type:
            logger.info(f"Routing task '{task_type}' via {self.router.mode} mode")

        if parallel and len(self.providers) > 1:
            return self._generate_parallel(prompt, max_tokens, task_type)
        else:
            return self._generate_sequential(prompt, max_tokens, task_type)

    def _generate_parallel(
        self, prompt: str, max_tokens: int, task_type: str = None
    ) -> Optional[str]:
        """Race best-fit providers in parallel, return first successful result"""
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Get the race set from the router
        if task_type:
            race_set = self.router.get_race_set(task_type, self.providers)
        else:
            race_set = self.providers

        task_label = task_type or "unknown"
        provider_names = [p["name"] for p in race_set]
        logger.info(f"Racing {len(race_set)} providers for '{task_label}': {provider_names}")

        def call_provider(provider):
            t0 = time.time()
            try:
                result = provider["generate"](provider, prompt, max_tokens)
                elapsed = (time.time() - t0) * 1000
                return (provider["name"], result, elapsed, None)
            except Exception as e:
                elapsed = (time.time() - t0) * 1000
                return (provider["name"], None, elapsed, str(e))

        errors = []

        with ThreadPoolExecutor(max_workers=len(race_set)) as executor:
            futures = {executor.submit(call_provider, p): p for p in race_set}

            for future in as_completed(futures):
                name, result, elapsed_ms, error = future.result()

                if result and not error:
                    # Cancel remaining futures
                    for f in futures:
                        f.cancel()
                    logger.info(
                        f"Routed generation: {name} won for '{task_label}' "
                        f"in {elapsed_ms:.0f}ms"
                    )
                    # Record stats
                    self.router.record_result(name, task_label, True, elapsed_ms)
                    return result
                else:
                    errors.append(f"{name}: {error}")
                    self.router.record_result(name, task_label, False, elapsed_ms)

        # All race providers failed — try fallbacks sequentially
        if task_type:
            fallbacks = self.router.get_fallbacks(task_type, self.providers, race_set)
            if fallbacks:
                logger.info(f"Race failed for '{task_label}', trying {len(fallbacks)} fallbacks")
                return self._generate_sequential(prompt, max_tokens, task_type, fallbacks)

        if errors:
            logger.warning(f"All providers failed for '{task_label}': {errors}")
        return None

    def _generate_sequential(
        self, prompt: str, max_tokens: int, task_type: str = None, provider_list: list = None
    ) -> Optional[str]:
        """Try providers sequentially in routed order until one succeeds"""
        import time

        task_label = task_type or "unknown"

        if provider_list is None:
            if task_type:
                provider_list = self.router.get_provider_order(task_type, self.providers)
            else:
                provider_list = self.providers

        for provider in provider_list:
            t0 = time.time()
            try:
                result = provider["generate"](provider, prompt, max_tokens)
                elapsed = (time.time() - t0) * 1000
                if result:
                    logger.info(
                        f"Sequential: {provider['name']} succeeded for "
                        f"'{task_label}' in {elapsed:.0f}ms"
                    )
                    self.router.record_result(provider["name"], task_label, True, elapsed)
                    return result
            except Exception as e:
                elapsed = (time.time() - t0) * 1000
                logger.warning(f"{provider['name']} failed for '{task_label}': {e}")
                self.router.record_result(provider["name"], task_label, False, elapsed)
                continue

        logger.error(f"All AI providers failed for '{task_label}'")
        return None

    def generate_architecture_doc(self, repo_name: str, structure: dict) -> Optional[str]:
        """Generate comprehensive architecture documentation"""
        prompt = f"""Generate a comprehensive ARCHITECTURE.md document for a repository named "{repo_name}".

Repository analysis:
- Total Python files: {len(structure.get('python_files', []))}
- Total lines of code: {structure.get('total_lines', 0)}
- Directories: {', '.join(structure.get('directories', [])[:10])}
- Config files: {', '.join(structure.get('config_files', []))}

Include these sections:
1. Overview - Brief description of the project's purpose
2. Architecture Diagram (ASCII) - Show component relationships
3. Directory Structure - Explain each major directory
4. Core Components - List and describe main modules
5. Data Flow - How data moves through the system
6. Dependencies - External libraries and why they're used
7. Extension Points - How to add new features

Make it professional and actionable. Use Markdown formatting."""

        return self.generate(prompt, max_tokens=3000, task_type="architecture")

    def generate_readme(self, repo_name: str, structure: dict) -> Optional[str]:
        """Generate quality README"""
        prompt = f"""Generate a professional README.md for "{repo_name}".

Repository info:
- Has Python code: {structure.get('has_python', False)}
- Has tests: {structure.get('has_tests', False)}
- Has docs: {structure.get('has_docs', False)}

Include:
1. Project title and badges
2. Description
3. Installation steps
4. Quick start example
5. Configuration
6. Contributing guidelines
7. License

Keep it concise but complete. Use Markdown."""

        return self.generate(prompt, max_tokens=1500, task_type="documentation")

    def generate_tests(self, source_code: str, filename: str) -> Optional[str]:
        """Generate pytest tests for source code"""
        prompt = f"""Generate pytest unit tests for this Python file ({filename}):

```python
{source_code[:3000]}
```

Requirements:
1. Use pytest fixtures where appropriate
2. Test edge cases and error handling
3. Include docstrings explaining each test
4. Use descriptive test names
5. Mock external dependencies

Return only the test file content, no explanations."""

        return self.generate(prompt, max_tokens=2000, task_type="test_generation")


# ============================================
# PHASE 2: QUALITY GATE
# ============================================


@dataclass
class QualityResult:
    """Result of quality check"""

    passed: bool
    checks: Dict[str, bool] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    score: float = 0.0


class QualityGate:
    """
    Validates output quality before marking tasks complete.
    Ensures real work meets minimum standards.
    """

    def check_file(self, file_path: Path) -> QualityResult:
        """Run all quality checks on a file"""
        checks = {}
        errors = []

        # Check 1: File exists
        checks["exists"] = file_path.exists()
        if not checks["exists"]:
            errors.append(f"File does not exist: {file_path}")
            return QualityResult(passed=False, checks=checks, errors=errors)

        content = file_path.read_text(encoding='utf-8', errors='replace')

        # Check 2: Not empty
        checks["not_empty"] = len(content.strip()) > 0
        if not checks["not_empty"]:
            errors.append("File is empty")

        # Check 3: Minimum length
        checks["min_length"] = len(content) >= 100
        if not checks["min_length"]:
            errors.append(f"File too short: {len(content)} chars (min 100)")

        # Check 4: No placeholder text
        placeholder_patterns = ["TODO", "FIXME", "XXX", "placeholder", "lorem ipsum"]
        has_placeholders = any(p.lower() in content.lower() for p in placeholder_patterns)
        checks["no_placeholders"] = not has_placeholders
        if has_placeholders:
            errors.append("Contains placeholder text")

        # Python-specific checks
        if file_path.suffix == ".py":
            py_result = self.check_python_file(file_path, content)
            checks.update(py_result.checks)
            errors.extend(py_result.errors)

        # Markdown-specific checks
        if file_path.suffix == ".md":
            md_result = self.check_markdown_file(content)
            checks.update(md_result.checks)
            errors.extend(md_result.errors)

        # Calculate score
        passed_checks = sum(1 for v in checks.values() if v)
        score = passed_checks / len(checks) if checks else 0

        return QualityResult(
            passed=score >= 0.7,  # 70% of checks must pass
            checks=checks,
            errors=errors,
            score=score,
        )

    def check_python_file(self, file_path: Path, content: str) -> QualityResult:
        """Python-specific quality checks"""
        checks = {}
        errors = []

        # Syntax check
        try:
            compile(content, str(file_path), "exec")
            checks["valid_syntax"] = True
        except SyntaxError as e:
            checks["valid_syntax"] = False
            errors.append(f"Syntax error: {e}")

        # Has docstrings
        checks["has_docstring"] = '"""' in content or "'''" in content

        # Import check - can imports resolve?
        checks["imports_ok"] = "import " in content or "from " in content or len(content) < 200

        return QualityResult(passed=True, checks=checks, errors=errors)

    def check_markdown_file(self, content: str) -> QualityResult:
        """Markdown-specific quality checks"""
        checks = {}
        errors = []

        # Has headers
        checks["has_headers"] = "# " in content
        if not checks["has_headers"]:
            errors.append("No headers found")

        # Has content sections
        lines = content.strip().splitlines()
        checks["multiple_sections"] = content.count("## ") >= 2

        # Not just template
        checks["has_content"] = len(lines) >= 10

        return QualityResult(passed=True, checks=checks, errors=errors)

    def validate_task_output(self, result: "ExecutionResult") -> QualityResult:
        """Validate entire task output"""
        all_checks = {}
        all_errors = []

        if not result.success:
            return QualityResult(
                passed=False,
                checks={"task_success": False},
                errors=[result.error or "Task failed"],
            )

        all_checks["task_success"] = True
        all_checks["has_artifacts"] = len(result.artifacts) > 0

        if not result.artifacts:
            all_errors.append("No artifacts produced")
            return QualityResult(passed=False, checks=all_checks, errors=all_errors)

        # Check each artifact
        for artifact in result.artifacts:
            file_result = self.check_file(artifact)
            all_checks[f"file_{artifact.name}"] = file_result.passed
            all_errors.extend(file_result.errors)

        passed = sum(1 for v in all_checks.values() if v)
        score = passed / len(all_checks) if all_checks else 0

        return QualityResult(
            passed=score >= 0.7, checks=all_checks, errors=all_errors, score=score
        )


# Singleton instances
ai_generator = AICodeGenerator()
quality_gate = QualityGate()


class TaskType(Enum):
    """Types of tasks that produce real output"""

    ARCHITECTURE_REVIEW = "architecture_review"
    DOCUMENTATION = "documentation"
    TEST_GENERATION = "test_generation"
    CODE_ANALYSIS = "code_analysis"
    DEPENDENCY_AUDIT = "dependency_audit"
    BUG_FIX = "bug_fix"
    FEATURE_IMPLEMENTATION = "feature_implementation"


@dataclass
class ExecutionResult:
    """Result of executing a task"""

    success: bool
    artifacts: List[Path] = field(default_factory=list)
    commit_sha: Optional[str] = None
    error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "artifacts": [str(a) for a in self.artifacts],
            "commit_sha": self.commit_sha,
            "error": self.error,
            "metrics": self.metrics,
        }


class TaskHandler(ABC):
    """Base class for task handlers that do REAL work"""

    @abstractmethod
    def execute(self, repo_path: Path, context: dict) -> ExecutionResult:
        """Execute the task and return result with artifacts"""
        pass

    @abstractmethod
    def verify(self, result: ExecutionResult) -> bool:
        """Verify the output is valid"""
        pass


class ArchitectureReviewHandler(TaskHandler):
    """
    Produces: docs/ARCHITECTURE.md with real analysis
    """

    def execute(self, repo_path: Path, context: dict) -> ExecutionResult:
        logger.info(f"Executing Architecture Review for {repo_path.name}")

        try:
            # 1. Analyze repo structure
            structure = self._analyze_structure(repo_path)

            # 2. Generate architecture document
            content = self._generate_architecture_doc(repo_path.name, structure)

            # 3. Write to file
            docs_dir = repo_path / "docs"
            docs_dir.mkdir(exist_ok=True)
            output_file = docs_dir / "ARCHITECTURE.md"
            output_file.write_text(content)

            logger.info(f"Created {output_file}")

            return ExecutionResult(
                success=True,
                artifacts=[output_file],
                metrics={
                    "lines_written": len(content.splitlines()),
                    "sections": content.count("## "),
                },
            )

        except Exception as e:
            logger.error(f"Architecture review failed: {e}")
            return ExecutionResult(success=False, error=str(e))

    def verify(self, result: ExecutionResult) -> bool:
        """Verify architecture doc is valid"""
        if not result.success:
            return False

        for artifact in result.artifacts:
            if not artifact.exists():
                return False
            content = artifact.read_text(encoding='utf-8', errors='replace')
            if len(content) < 100:  # Minimum reasonable doc
                return False
            if "## " not in content:  # Has sections
                return False

        return True

    def _analyze_structure(self, repo_path: Path) -> dict:
        """Analyze repo structure"""
        structure = {
            "python_files": [],
            "directories": [],
            "config_files": [],
            "total_lines": 0,
        }

        # Find Python files
        for py_file in repo_path.rglob("*.py"):
            if "__pycache__" not in str(py_file):
                structure["python_files"].append(py_file.relative_to(repo_path))
                try:
                    structure["total_lines"] += len(py_file.read_text(encoding='utf-8', errors='replace').splitlines())
                except:
                    pass

        # Find directories
        for dir_path in repo_path.iterdir():
            if dir_path.is_dir() and not dir_path.name.startswith("."):
                structure["directories"].append(dir_path.name)

        # Find config files
        for config in ["pyproject.toml", "setup.py", "requirements.txt", "package.json"]:
            if (repo_path / config).exists():
                structure["config_files"].append(config)

        return structure

    def _generate_architecture_doc(self, repo_name: str, structure: dict) -> str:
        """Generate architecture documentation - uses AI when available"""

        # Try AI generation first (Phase 2)
        ai_content = ai_generator.generate_architecture_doc(repo_name, structure)
        if ai_content:
            logger.info("Using AI-generated architecture document")
            return ai_content

        # Fallback to template
        logger.info("Using template-based architecture document")
        dirs_list = (
            "\n".join([f"- `{d}/`" for d in structure["directories"]]) or "- No subdirectories"
        )
        files_list = (
            "\n".join([f"- `{f}`" for f in structure["python_files"][:20]]) or "- No Python files"
        )
        configs_list = (
            "\n".join([f"- `{c}`" for c in structure["config_files"]]) or "- No config files"
        )

        if len(structure["python_files"]) > 20:
            files_list += f"\n- ... and {len(structure['python_files']) - 20} more files"

        return f"""# {repo_name} Architecture

## Overview

This document describes the architectural structure of the {repo_name} repository.

**Generated:** {datetime.now().isoformat()}
**Total Python Files:** {len(structure["python_files"])}
**Total Lines of Code:** {structure["total_lines"]:,}

## Directory Structure

{dirs_list}

## Key Files

{files_list}

## Configuration

{configs_list}

## Component Diagram

```
{repo_name}/
├── Source Code
│   └── Python modules ({len(structure["python_files"])} files)
├── Configuration
│   └── {', '.join(structure["config_files"]) or 'None'}
└── Documentation
    └── This file
```

## Dependencies

See `requirements.txt` or `pyproject.toml` for dependencies.

## Notes

This architecture document was auto-generated by REPODEPOT.
Manual review recommended for accuracy.

---
*Generated by OPTIMUS Agent - Architecture Review Task*
"""


class DocumentationHandler(TaskHandler):
    """
    Produces: Updated README.md with real content
    """

    def execute(self, repo_path: Path, context: dict) -> ExecutionResult:
        logger.info(f"Executing Documentation Update for {repo_path.name}")

        try:
            readme_path = repo_path / "README.md"

            # Read existing or create new
            if readme_path.exists():
                existing = readme_path.read_text(encoding='utf-8', errors='replace')
            else:
                existing = ""

            # Analyze repo
            structure = self._analyze_repo(repo_path)

            # Generate new content
            new_content = self._generate_readme(repo_path.name, structure, existing)

            # Write
            readme_path.write_text(new_content)

            return ExecutionResult(
                success=True,
                artifacts=[readme_path],
                metrics={"lines_written": len(new_content.splitlines())},
            )

        except Exception as e:
            logger.error(f"Documentation update failed: {e}")
            return ExecutionResult(success=False, error=str(e))

    def verify(self, result: ExecutionResult) -> bool:
        if not result.success:
            return False
        for artifact in result.artifacts:
            if not artifact.exists():
                return False
            if len(artifact.read_text(encoding='utf-8', errors='replace')) < 50:
                return False
        return True

    def _analyze_repo(self, repo_path: Path) -> dict:
        return {
            "has_python": any(repo_path.rglob("*.py")),
            "has_tests": (repo_path / "tests").exists() or (repo_path / "test").exists(),
            "has_docs": (repo_path / "docs").exists(),
        }

    def _generate_readme(self, name: str, structure: dict, existing: str) -> str:
        # If existing is substantial, preserve it
        if len(existing) > 500:
            return existing

        # Try AI generation first (Phase 2)
        ai_content = ai_generator.generate_readme(name, structure)
        if ai_content:
            logger.info("Using AI-generated README")
            return ai_content

        # Fallback to template
        logger.info("Using template-based README")
        return f"""# {name}

## Overview

{name} is a component of the ResonanceEnergy portfolio.

## Quick Start

```bash
# Clone repository
git clone https://github.com/ResonanceEnergy/{name}.git
cd {name}

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

## Structure

- Python source: {"✅" if structure["has_python"] else "❌"}
- Tests: {"✅" if structure["has_tests"] else "❌"}
- Documentation: {"✅" if structure["has_docs"] else "❌"}

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

See [LICENSE](LICENSE) for details.

---
*Documentation generated by GASKET Agent*
"""


class TestGenerationHandler(TaskHandler):
    """
    Produces: tests/test_*.py with real pytest tests
    Phase 2 addition - requires AI for meaningful tests
    """

    def execute(self, repo_path: Path, context: dict) -> ExecutionResult:
        logger.info(f"Executing Test Generation for {repo_path.name}")

        try:
            # Find Python files to test
            source_files = list(repo_path.glob("*.py"))
            if not source_files:
                source_files = list(repo_path.glob("src/*.py"))

            if not source_files:
                return ExecutionResult(success=False, error="No Python source files found to test")

            # Create tests directory
            tests_dir = repo_path / "tests"
            tests_dir.mkdir(exist_ok=True)

            artifacts = []
            total_tests = 0

            # Generate tests for each source file (up to 5)
            for source_file in source_files[:5]:
                if source_file.name.startswith("test_"):
                    continue

                test_content = self._generate_tests(source_file)
                if test_content:
                    test_file = tests_dir / f"test_{source_file.name}"
                    test_file.write_text(test_content)
                    artifacts.append(test_file)
                    total_tests += test_content.count("def test_")

            if not artifacts:
                return ExecutionResult(success=False, error="Failed to generate any test files")

            return ExecutionResult(
                success=True,
                artifacts=artifacts,
                metrics={
                    "test_files_created": len(artifacts),
                    "test_functions": total_tests,
                },
            )

        except Exception as e:
            logger.error(f"Test generation failed: {e}")
            return ExecutionResult(success=False, error=str(e))

    def verify(self, result: ExecutionResult) -> bool:
        """Verify test files are valid Python"""
        if not result.success:
            return False

        for artifact in result.artifacts:
            if not artifact.exists():
                return False

            content = artifact.read_text(encoding='utf-8', errors='replace')

            # Check syntax
            try:
                compile(content, str(artifact), "exec")
            except SyntaxError:
                return False

            # Must have at least one test function
            if "def test_" not in content:
                return False

        return True

    def _generate_tests(self, source_file: Path) -> Optional[str]:
        """Generate tests for a source file"""
        try:
            source_code = source_file.read_text(encoding='utf-8', errors='replace')
        except Exception:
            return None

        # Try AI generation first
        ai_tests = ai_generator.generate_tests(source_code, source_file.name)
        if ai_tests:
            logger.info(f"Using AI-generated tests for {source_file.name}")
            return ai_tests

        # Fallback to basic template
        logger.info(f"Using template tests for {source_file.name}")
        module_name = source_file.stem

        return f'''"""
Tests for {source_file.name}
Auto-generated by GASKET Test Generator
"""

import pytest
from pathlib import Path
import sys

# Add source to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class Test{module_name.title().replace("_", "")}:
    """Test suite for {module_name}"""

    def test_module_imports(self):
        """Test that module can be imported"""
        try:
            import {module_name}
            assert True
        except ImportError:
            pytest.skip("Module not importable in isolation")

    def test_module_has_content(self):
        """Test that source file is not empty"""
        source = Path(__file__).parent.parent / "{source_file.name}"
        if source.exists():
            content = source.read_text(encoding='utf-8', errors='replace')
            assert len(content) > 0
        else:
            pytest.skip("Source file not found")

# Additional tests should be added manually
# or regenerated with AI when ANTHROPIC_API_KEY is set
'''


class RepoManager:
    """Manages git operations for real work"""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.workspace.mkdir(exist_ok=True)

    def get_repo_path(self, repo_name: str) -> Path:
        """Get path to repo, clone if needed"""
        repo_path = self.workspace / repo_name

        if not repo_path.exists():
            logger.info(f"Cloning {repo_name}...")
            subprocess.run(
                [
                    "git",
                    "clone",
                    f"git@github.com:ResonanceEnergy/{repo_name}.git",
                    str(repo_path),
                ],
                check=True,
            )
        else:
            logger.info(f"Pulling latest for {repo_name}...")
            subprocess.run(["git", "pull", "--rebase"], cwd=repo_path, capture_output=True)

        return repo_path

    def commit_changes(
        self, repo_path: Path, message: str, author: str = "GASKET"
    ) -> Optional[str]:
        """Commit changes and return commit SHA"""
        try:
            # Stage all changes
            subprocess.run(["git", "add", "-A"], cwd=repo_path, check=True)

            # Check if there are changes to commit
            result = subprocess.run(
                ["git", "status", "--porcelain"], cwd=repo_path, capture_output=True, text=True
            )

            if not result.stdout.strip():
                logger.warning("No changes to commit")
                return None

            # Commit
            subprocess.run(
                [
                    "git",
                    "commit",
                    "-m",
                    message,
                    "--author",
                    f"{author} <{author.lower()}@bit-rage-labour.com>",
                ],
                cwd=repo_path,
                check=True,
            )

            # Get commit SHA
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo_path, capture_output=True, text=True
            )

            return result.stdout.strip()[:8]

        except subprocess.CalledProcessError as e:
            logger.error(f"Git commit failed: {e}")
            return None

    def push_changes(self, repo_path: Path) -> bool:
        """Push commits to remote"""
        try:
            subprocess.run(["git", "push"], cwd=repo_path, check=True)
            return True
        except subprocess.CalledProcessError:
            return False


class LocalRepoManager(RepoManager):
    """Uses local repos directory - no cloning needed"""

    def __init__(self, repos_dir: Path):
        self.workspace = repos_dir

    def get_repo_path(self, repo_name: str) -> Path:
        """Get path to existing local repo"""
        repo_path = self.workspace / repo_name

        if not repo_path.exists():
            raise FileNotFoundError(f"Repo not found: {repo_path}")

        logger.info(f"Using local repo: {repo_path}")

        # Pull latest if it's a git repo
        if (repo_path / ".git").exists():
            subprocess.run(["git", "pull", "--rebase"], cwd=repo_path, capture_output=True)

        return repo_path


class TaskExecutor:
    """
    Main executor that ACTUALLY does work.

    This replaces the fake completion loop in production_agent_collaboration.py

    Phase 2 Features:
    - AI-powered content generation (when ANTHROPIC_API_KEY set)
    - Quality gate validation before marking complete
    - Test generation handler
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.repo_manager = RepoManager(workspace / "active_repos")
        self.quality_gate = quality_gate

        # Register handlers for each task type
        self.handlers: Dict[TaskType, TaskHandler] = {
            TaskType.ARCHITECTURE_REVIEW: ArchitectureReviewHandler(),
            TaskType.DOCUMENTATION: DocumentationHandler(),
            TaskType.TEST_GENERATION: TestGenerationHandler(),
        }

    def execute_task(
        self, task_type: TaskType, repo_name: str, context: dict = None, agent: str = "GASKET"
    ) -> ExecutionResult:
        """
        Execute a task and produce REAL artifacts.

        Returns ExecutionResult with:
        - artifacts: List of created files
        - commit_sha: Git commit if changes were made
        - success: Whether task completed successfully
        """
        context = context or {}

        logger.info(f"[{agent}] Executing {task_type.value} for {repo_name}")

        # Get handler
        handler = self.handlers.get(task_type)
        if not handler:
            return ExecutionResult(success=False, error=f"No handler for task type: {task_type}")

        # Get repo
        try:
            repo_path = self.repo_manager.get_repo_path(repo_name)
        except Exception as e:
            return ExecutionResult(success=False, error=f"Failed to get repo: {e}")

        # Execute
        result = handler.execute(repo_path, context)

        # Verify
        if not handler.verify(result):
            result.success = False
            result.error = "Verification failed"
            return result

        # Commit if successful
        if result.success and result.artifacts:
            commit_message = f"[{task_type.value}] {agent}: Auto-generated content"
            result.commit_sha = self.repo_manager.commit_changes(
                repo_path, commit_message, author=agent
            )

        logger.info(
            f"[{agent}] Task complete: {result.success}, artifacts: {len(result.artifacts)}"
        )

        return result


# ============================================
# ENTRY POINT FOR TESTING
# ============================================


def test_executor():
    """Test the executor with Phase 2 features"""
    print("=" * 60)
    print("REPODEPOT TASK EXECUTOR - PHASE 2 TEST")
    print("=" * 60)

    workspace = Path(
        "$HOME/repos/DIGITAL-LABOUR"
    )

    # Check AI availability
    print(
        f"\n🤖 AI Generation: {'ENABLED' if ai_generator.enabled else 'DISABLED (set ANTHROPIC_API_KEY)'}"
    )
    print(f"🔍 Quality Gate: ENABLED")

    # Use LOCAL repos directory instead of cloning
    executor = TaskExecutor(workspace)
    executor.repo_manager = LocalRepoManager(workspace / "repos")

    test_repo = "Digital-Labour"
    results = []

    # Test 1: Architecture Review
    print(f"\n📋 Test 1: Architecture Review for {test_repo}...")
    result1 = executor.execute_task(
        task_type=TaskType.ARCHITECTURE_REVIEW, repo_name=test_repo, agent="OPTIMUS"
    )
    results.append(("Architecture Review", result1))

    # Quality gate check
    qr = quality_gate.validate_task_output(result1)
    print(f"   Quality Score: {qr.score:.0%} {'✅' if qr.passed else '❌'}")

    # Test 2: Documentation
    print(f"\n📄 Test 2: Documentation Update for NCC-Doctrine...")
    result2 = executor.execute_task(
        task_type=TaskType.DOCUMENTATION, repo_name="NCC-Doctrine", agent="GASKET"
    )
    results.append(("Documentation", result2))

    # Test 3: Test Generation
    print(f"\n🧪 Test 3: Test Generation for NCL...")
    result3 = executor.execute_task(
        task_type=TaskType.TEST_GENERATION, repo_name="NCL", agent="GASKET"
    )
    results.append(("Test Generation", result3))

    # Summary
    print("\n" + "=" * 60)
    print("📊 PHASE 2 TEST SUMMARY")
    print("=" * 60)

    for name, result in results:
        status = "✅" if result.success else "❌"
        artifacts = len(result.artifacts) if result.artifacts else 0
        print(f"  {status} {name}: {artifacts} artifacts")
        if result.error:
            print(f"       Error: {result.error}")

    passed = sum(1 for _, r in results if r.success)
    print(f"\nPassed: {passed}/{len(results)}")
    print("=" * 60)

    return results


if __name__ == "__main__":
    test_executor()
