"""
REPO DEPOT Test Configuration
==============================
Shared pytest fixtures and configuration for all test suites.
"""
import pytest
import sys
from pathlib import Path

# Add repo_depot to path
WORKSPACE = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE))


@pytest.fixture
def workspace():
    """Return the Bit Rage Labour workspace path."""
    return WORKSPACE


@pytest.fixture
def repos_dir(workspace):
    """Return the repos directory."""
    return workspace / "repos"


@pytest.fixture
def portfolio_data(workspace):
    """Load portfolio.json as a fixture."""
    import json
    pf = workspace / "portfolio.json"
    if pf.exists():
        with open(pf, encoding="utf-8") as f:
            return json.load(f)
    return {"repositories": []}


@pytest.fixture
def sample_repo(repos_dir):
    """Return path to first available local repo."""
    if repos_dir.exists():
        for d in repos_dir.iterdir():
            if d.is_dir() and (d / ".git").exists():
                return d
    return None


@pytest.fixture
def flywheel_state(workspace):
    """Return flywheel state directory."""
    return workspace / "state" / "flywheel"
