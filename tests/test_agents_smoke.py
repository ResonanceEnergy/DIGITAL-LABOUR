"""Smoke tests — verify every agent runner module is importable and exposes run_pipeline or run.

These tests do not make real LLM or HTTP calls; they only verify module structure.
If an agent has an optional dependency not installed, the test is skipped.
"""
import sys
import importlib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

AGENTS_DIR = PROJECT_ROOT / "agents"
AGENT_NAMES: list[str] = sorted(
    d.name
    for d in AGENTS_DIR.iterdir()
    if d.is_dir() and not d.name.startswith("_") and (d / "runner.py").exists()
)


def _load(agent_name: str):
    """Import and return the runner module, or skip/fail appropriately."""
    try:
        return importlib.import_module(f"agents.{agent_name}.runner")
    except ImportError as exc:
        pytest.skip(f"Optional dependency not installed: {exc}")
    except Exception as exc:
        pytest.fail(f"Unexpected import error in agents.{agent_name}.runner: {exc}")


@pytest.mark.parametrize("agent_name", AGENT_NAMES)
def test_agent_runner_importable(agent_name: str):
    """Each agent runner must import without an unexpected exception."""
    runner = _load(agent_name)
    assert runner is not None


@pytest.mark.parametrize("agent_name", AGENT_NAMES)
def test_agent_runner_has_entry_point(agent_name: str):
    """Each agent runner must expose run_pipeline() or run() as an entry point."""
    runner = _load(agent_name)
    has_entry = hasattr(runner, "run_pipeline") or hasattr(runner, "run")
    assert has_entry, (
        f"agents.{agent_name}.runner is missing both run_pipeline() and run(). "
        "Add one of these as the public entry point."
    )
