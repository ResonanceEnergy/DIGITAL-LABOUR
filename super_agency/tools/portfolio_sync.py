#!/usr/bin/env python3
"""
Portfolio Sync — discovers and onboards ResonanceEnergy repos.

Queries GitHub for all repos under the org, adds missing ones
to portfolio.json, clones them locally, and runs scaffold.

Usage::

    python tools/portfolio_sync.py discover   # show new repos
    python tools/portfolio_sync.py sync       # add + clone new
    python tools/portfolio_sync.py refresh    # update timestamps
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agents"))

from agents.common import (  # noqa: E402
    get_portfolio, Log, ensure_dir, CONFIG,
)

PORTFOLIO_FILE = ROOT / "portfolio.json"
PROJECTS_FILE = ROOT / "config" / "research_projects.json"
REPOS_BASE = Path(CONFIG.get("repos_base", "./repos"))
if not REPOS_BASE.is_absolute():
    REPOS_BASE = (ROOT / REPOS_BASE).resolve()
COMPANIES_DIR = ROOT / "companies"
GITHUB_ORG = "ResonanceEnergy"

# Message bus (best-effort)
try:
    from agents.message_bus import bus as _bus
except Exception:
    _bus = None


def _emit(topic: str, payload: dict | None = None):
    if _bus:
        _bus.publish(
            topic, payload or {},
            source="portfolio_sync",
        )


def _gh_list_repos() -> list[dict[str, Any]]:
    """Query GitHub CLI for all org repos."""
    cmd = [
        "gh", "repo", "list", GITHUB_ORG,
        "--limit", "200",
        "--json",
        "name,visibility,primaryLanguage,"
        "updatedAt,description",
    ]
    try:
        cp = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=30,
        )
        if cp.returncode == 0:
            return json.loads(cp.stdout)
    except Exception as exc:
        Log.warn(f"gh CLI failed: {exc}")
    return []


def _load_portfolio() -> dict[str, Any]:
    if PORTFOLIO_FILE.exists():
        return json.loads(
            PORTFOLIO_FILE.read_text(encoding="utf-8"),
        )
    return {"repositories": [], "generated": ""}


def _save_portfolio(data: dict[str, Any]):
    data["generated"] = datetime.now().isoformat()
    PORTFOLIO_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def discover() -> list[dict[str, Any]]:
    """Find repos on GitHub not yet in portfolio."""
    gh_repos = _gh_list_repos()
    if not gh_repos:
        Log.warn("No repos from GitHub — check gh auth")
        return []

    portfolio = _load_portfolio()
    tracked = {
        r["name"] for r in portfolio.get("repositories", [])
    }

    new_repos = []
    for r in gh_repos:
        if r["name"] not in tracked:
            lang = None
            if r.get("primaryLanguage"):
                lang = r["primaryLanguage"].get("name")
            new_repos.append({
                "name": r["name"],
                "visibility": r.get(
                    "visibility", "PRIVATE",
                ),
                "language_hint": lang,
                "updatedAt": r.get("updatedAt", ""),
                "description": r.get("description", ""),
                "tier": "M",
                "autonomy_level": "L1",
                "risk_tier": "HIGH",
                "clean_scans": 0,
            })

    return new_repos


def sync() -> dict[str, Any]:
    """Add new repos to portfolio, clone, and scaffold."""
    new_repos = discover()
    result: dict[str, Any] = {
        "action": "sync",
        "new_repos": [],
        "cloned": [],
        "errors": [],
    }

    if not new_repos:
        Log.info("Portfolio is up to date — no new repos")
        result["status"] = "up_to_date"
        return result

    portfolio = _load_portfolio()

    for repo in new_repos:
        name = repo["name"]
        # Remove description before saving to portfolio
        desc = repo.pop("description", "")
        portfolio["repositories"].append(repo)
        result["new_repos"].append(name)
        Log.info(
            f"Added to portfolio: {name} ({desc})"
        )

    # Sort and save
    portfolio["repositories"].sort(
        key=lambda x: x["name"].lower(),
    )
    _save_portfolio(portfolio)

    # Clone repos
    for name in result["new_repos"]:
        repo_dir = REPOS_BASE / name
        if repo_dir.exists():
            continue
        url = (
            f"https://github.com/"
            f"{GITHUB_ORG}/{name}.git"
        )
        try:
            subprocess.run(
                ["git", "clone", url, str(repo_dir)],
                capture_output=True, text=True,
                timeout=120,
            )
            result["cloned"].append(name)
            Log.info(f"Cloned {name}")
        except Exception as exc:
            result["errors"].append(
                f"{name}: {exc}",
            )
            Log.warn(f"Clone failed: {name}: {exc}")

        # Create companies/ mirror
        company_dir = COMPANIES_DIR / name
        if not company_dir.exists():
            company_dir.mkdir(parents=True, exist_ok=True)

    # Run self-heal scaffold
    try:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "agents" / "portfolio_selfheal.py"),
            ],
            cwd=str(ROOT),
            timeout=120,
        )
        Log.info("Self-heal scaffold complete")
    except Exception as exc:
        result["errors"].append(f"selfheal: {exc}")

    result["status"] = "synced"
    _emit("portfolio.sync.done", {
        "new": len(result["new_repos"]),
        "cloned": len(result["cloned"]),
    })

    return result


def refresh() -> dict[str, Any]:
    """Update portfolio timestamps from GitHub."""
    gh_repos = _gh_list_repos()
    if not gh_repos:
        return {"status": "no_data"}

    gh_map = {r["name"]: r for r in gh_repos}
    portfolio = _load_portfolio()
    updated = 0

    for repo in portfolio.get("repositories", []):
        gh = gh_map.get(repo["name"])
        if not gh:
            continue

        new_ts = gh.get("updatedAt", "")
        if new_ts and new_ts != repo.get("updatedAt"):
            repo["updatedAt"] = new_ts
            updated += 1

        lang = None
        if gh.get("primaryLanguage"):
            lang = gh["primaryLanguage"].get("name")
        if lang and lang != repo.get("language_hint"):
            repo["language_hint"] = lang

        vis = gh.get("visibility", "")
        if vis and vis != repo.get("visibility"):
            repo["visibility"] = vis

    if updated:
        _save_portfolio(portfolio)
        Log.info(f"Refreshed {updated} repo timestamps")

    return {
        "status": "refreshed",
        "updated": updated,
        "total": len(portfolio.get("repositories", [])),
    }


# ── CLI ──────────────────────────────────────────────────────

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "discover"

    if cmd == "discover":
        found = discover()
        if found:
            print(f"Found {len(found)} new repos:")
            for r in found:
                print(f"  {r['name']} ({r['visibility']})")
        else:
            print("No new repos found")
    elif cmd == "sync":
        out = sync()
        print(json.dumps(out, indent=2))
    elif cmd == "refresh":
        out = refresh()
        print(json.dumps(out, indent=2))
    else:
        print(f"Unknown command: {cmd}")
        print(
            "Usage: portfolio_sync.py "
            "[discover|sync|refresh]"
        )
        sys.exit(1)
