"""
REPO DEPOT Test Setup
======================
Validates test environment and dependencies before running test suite.
"""
import sys
import subprocess
from pathlib import Path


def check_python_version():
    """Ensure Python 3.10+"""
    assert sys.version_info >= (3, 10), f"Python 3.10+ required, got {sys.version}"
    print(f"Python {sys.version} OK")


def check_dependencies():
    """Check required packages are installed."""
    required = ["pytest", "pathlib", "json"]
    for pkg in required:
        try:
            __import__(pkg)
            print(f"{pkg} OK")
        except ImportError:
            print(f"MISSING: {pkg} - run: pip install {pkg}")


def check_workspace():
    """Validate workspace structure."""
    workspace = Path(__file__).parent.parent
    checks = [
        workspace / "portfolio.json",
        workspace / "repos",
        workspace / "state" / "flywheel",
    ]
    for p in checks:
        status = "OK" if p.exists() else "MISSING"
        print(f"{status}: {p.name}")


if __name__ == "__main__":
    print("=== REPO DEPOT Test Setup ===")
    check_python_version()
    check_dependencies()
    check_workspace()
    print("Setup check complete.")
