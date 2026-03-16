#!/usr/bin/env python3
"""
Repo Onboarding CLI.

Single command to add a new GitHub repo to the portfolio:
clone, classify, tier, integrate, and add to daily
brief rotation.

Usage::

    python tools/onboard_repo.py <github_url>
    python tools/onboard_repo.py https://github.com/owner/repo
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REPOS_DIR = ROOT / "repos"
PORTFOLIO = ROOT / "portfolio.json"


def _run_git(*args: str, cwd: Path | None = None) -> str:
    r = subprocess.run(
        ["git", *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(cwd) if cwd else None,
    )
    return r.stdout.strip()


def _load_portfolio() -> dict[str, Any]:
    if PORTFOLIO.exists():
        return json.loads(
            PORTFOLIO.read_text(encoding="utf-8"),
        )
    return {"repositories": []}


def _save_portfolio(data: dict):
    PORTFOLIO.write_text(json.dumps(data, indent=2), encoding="utf-8")


def onboard(url: str) -> dict[str, Any]:
    """Onboard a repo: clone, classify, tier, integrate."""
    # Parse owner/name from URL
    parts = url.rstrip("/").split("/")
    owner = parts[-2] if len(parts) >= 2 else "unknown"
    name = parts[-1].removesuffix(".git")
    local_path = REPOS_DIR / name

    steps: list[dict[str, Any]] = []
    report: dict[str, Any] = {
        "repo": name, "owner": owner,
        "url": url, "steps": steps,
    }

    # 1) Clone if needed
    if local_path.exists():
        steps.append({"clone": "already exists"})
    else:
        REPOS_DIR.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "clone", "--depth", "1",
             url, str(local_path)],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            err = result.stderr.strip()
            steps.append(
                {"clone": f"FAILED: {err}"},
            )
            return report
        steps.append({"clone": "success"})

    # 2) Auto-classify (language, has CI, has tests)
    if local_path.exists():
        files = [f.name for f in local_path.iterdir()]
    else:
        files = []
    has_ci = any(p.exists() for p in [
        local_path / ".github" / "workflows",
        local_path / ".gitlab-ci.yml",
    ])
    has_tests = (
        (local_path / "tests").is_dir()
        or (local_path / "test").is_dir()
    )
    lang = "unknown"
    _sigs = [
        ("package.json", "javascript"),
        ("Cargo.toml", "rust"),
        ("go.mod", "go"),
        ("setup.py", "python"),
        ("pyproject.toml", "python"),
        ("Gemfile", "ruby"),
        ("pom.xml", "java"),
    ]
    for sig, detected in _sigs:
        if sig in files:
            lang = detected
            break

    classification = {
        "language": lang,
        "has_ci": has_ci,
        "has_tests": has_tests,
    }
    steps.append({"classify": classification})

    # 3) Add to portfolio.json
    portfolio = _load_portfolio()
    existing = [
        r for r in portfolio["repositories"]
        if r.get("name") == name
    ]
    if existing:
        steps.append({"portfolio": "already registered"})
    else:
        entry = {
            "name": name,
            "url": url,
            "owner": owner,
            "language": lang,
            "tier": "C",
            "risk_tier": "medium",
            "autonomy_level": "L0",
            "has_ci": has_ci,
            "has_tests": has_tests,
            "local_path": str(local_path),
        }
        portfolio["repositories"].append(entry)
        _save_portfolio(portfolio)
        steps.append({
            "portfolio": "added",
            "tier": "C",
            "autonomy": "L0",
        })

    # 4) Run autotier if available
    autotier = ROOT / "agents" / "portfolio_autotier.py"
    if autotier.exists():
        try:
            subprocess.run(
                [sys.executable, str(autotier)],
                capture_output=True, timeout=60,
            )
            steps.append({"autotier": "executed"})
        except Exception as exc:
            steps.append({"autotier": f"skipped: {exc}"})

    # 5) Summary
    report["status"] = "onboarded"
    return report


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/onboard_repo.py <github_url>")
        sys.exit(1)

    url = sys.argv[1]
    result = onboard(url)
    print(json.dumps(result, indent=2))

    if result.get("status") == "onboarded":
        name = result['repo']
        print(
            f"\n[OK] {name} onboarded "
            "— tier C / L0 autonomy. "
            "Will appear in next daily brief.",
        )
    else:
        print(
            "\n[WARN] Onboarding incomplete "
            "— check steps above.",
        )


if __name__ == "__main__":
    main()
