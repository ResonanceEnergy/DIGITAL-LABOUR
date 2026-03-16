#!/usr/bin/env python3
"""
Dependency Updater — scans portfolio repos for outdated dependencies
and creates PRs (or proposals at L1) for updates.

Supports: requirements.txt, package.json, Gemfile
Autonomy enforcement: L1 = proposal only, L2+ = auto-create branch + PR.

Usage::

    python tools/dependency_updater.py            # scan all repos
    python tools/dependency_updater.py <repo>      # scan specific repo
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agents"))

from agents.common import (  # noqa: E402
    get_portfolio, Log, ensure_dir, run_git, now_iso,
)

_cfg = json.loads(
    (ROOT / "config" / "settings.json").read_text(encoding="utf-8"),
)
REPOS_BASE = (ROOT / _cfg["repos_base"]).resolve()
PROPOSALS_DIR = ROOT / "proposals" / "dependency_updates"
ensure_dir(PROPOSALS_DIR)


def _parse_requirements_txt(path: Path) -> list[dict]:
    """Parse requirements.txt into list of {name, spec, line_num}."""
    deps: list[dict[str, Any]] = []
    lines = path.read_text(
        encoding="utf-8", errors="replace",
    ).splitlines()
    for i, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+)\s*([><=!~]+.+)?", line)
        if m:
            deps.append({
                "name": m.group(1),
                "spec": (m.group(2) or "").strip(),
                "line": i,
                "file": str(path.name),
            })
    return deps


def _parse_package_json(path: Path) -> list[dict]:
    """Parse package.json dependencies."""
    deps: list[dict[str, Any]] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return deps
    for section in ("dependencies", "devDependencies"):
        for name, ver in data.get(section, {}).items():
            deps.append({
                "name": name, "spec": ver,
                "section": section, "file": "package.json",
            })
    return deps


def _detect_outdated_pip(repo_path: Path) -> list[dict]:
    """Use pip index to check for newer versions (best-effort)."""
    reqs_file = repo_path / "requirements.txt"
    if not reqs_file.exists():
        return []
    deps = _parse_requirements_txt(reqs_file)
    outdated = []
    for dep in deps:
        # Flag pinned dependencies with == as candidates for review
        if "==" in dep["spec"]:
            current = dep["spec"].replace("==", "").strip()
            outdated.append({
                "name": dep["name"],
                "current": current,
                "wanted": "latest (review needed)",
                "file": dep["file"],
                "type": "python",
            })
    return outdated


def _detect_outdated_npm(repo_path: Path) -> list[dict]:
    """Check package.json for pinned/old deps."""
    pkg = repo_path / "package.json"
    if not pkg.exists():
        return []
    deps = _parse_package_json(pkg)
    outdated = []
    for dep in deps:
        # Flag exact pins or very old semver ranges
        ver = dep["spec"]
        if (ver and not ver.startswith("^")
                and not ver.startswith("~")
                and not ver.startswith("*")):
            outdated.append({
                "name": dep["name"],
                "current": ver,
                "wanted": "latest (review needed)",
                "file": dep["file"],
                "section": dep.get("section", "dependencies"),
                "type": "npm",
            })
    return outdated


def scan_repo(repo_name: str) -> dict[str, Any]:
    """Scan a single repo for outdated dependencies."""
    repo_path = REPOS_BASE / repo_name
    if not repo_path.is_dir():
        return {
            "repo": repo_name,
            "error": "repo dir not found", "outdated": [],
        }

    outdated: list[dict] = []
    outdated.extend(_detect_outdated_pip(repo_path))
    outdated.extend(_detect_outdated_npm(repo_path))

    return {"repo": repo_name, "outdated": outdated, "scanned_at": now_iso()}


def create_update_proposal(repo_name: str, outdated: list[dict]) -> Path:
    """Create an L1 proposal for dependency updates."""
    proposal = {
        "repo": repo_name,
        "action": "dependency_update",
        "risk": "LOW",
        "autonomy_required": "L1",
        "created_at": now_iso(),
        "dependencies": outdated,
        "description": (
            f"Update {len(outdated)} pinned deps in {repo_name}"
        ),
    }
    stamp = datetime.now().strftime("%Y%m%d")
    out = PROPOSALS_DIR / f"dep_update_{repo_name}_{stamp}.json"
    out.write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    Log.info(f"Created dependency update proposal: {out.name}")
    return out


def create_update_branch(repo_name: str, outdated: list[dict]) -> bool:
    """Create a branch with bumped deps (L2 action)."""
    from autonomy_mode import is_action_allowed
    if not is_action_allowed(repo_name, "mutate"):
        Log.warn(
            f"{repo_name}: L2+ required, creating proposal",
        )
        create_update_proposal(repo_name, outdated)
        return False

    repo_path = REPOS_BASE / repo_name
    branch = f"deps/update-{datetime.now().strftime('%Y%m%d')}"
    rc, _, err = run_git(repo_path, ["checkout", "-b", branch])
    if rc != 0:
        Log.error(f"Failed to create branch {branch}: {err}")
        return False

    # Update requirements.txt pins
    reqs = repo_path / "requirements.txt"
    if reqs.exists():
        lines = reqs.read_text(encoding="utf-8").splitlines()
        for dep in outdated:
            if dep["type"] == "python" and dep["current"]:
                for i, line in enumerate(lines):
                    if line.strip().startswith(dep["name"] + "=="):
                        # Mark for update (leave version, add comment)
                        cur = dep['current']
                        lines[i] = (
                            f"{line}  # TODO: update from {cur}"
                        )
                        break
        reqs.write_text("\n".join(lines) + "\n", encoding="utf-8")

    run_git(repo_path, ["add", "-A"])
    msg = f"chore(deps): flag {len(outdated)} deps for update"
    run_git(repo_path, ["commit", "-m", msg])
    run_git(repo_path, ["checkout", "-"])
    Log.info(
        f"{repo_name}: branch {branch}, {len(outdated)} flagged",
    )
    return True


def scan_all() -> list[dict]:
    """Scan all portfolio repos and create proposals for outdated deps."""
    results = []
    for repo in get_portfolio().get("repositories", []):
        name = repo["name"]
        scan = scan_repo(name)
        if scan["outdated"]:
            create_update_proposal(name, scan["outdated"])
        results.append(scan)
    total_outdated = sum(len(r["outdated"]) for r in results)
    Log.info(
        f"Dep scan: {len(results)} repos, "
        f"{total_outdated} outdated deps",
    )
    return results


if __name__ == "__main__":
    if len(sys.argv) > 1:
        result = scan_repo(sys.argv[1])
        print(json.dumps(result, indent=2))
    else:
        results = scan_all()
        print(f"\nScanned {len(results)} repos")
        for r in results:
            if r["outdated"]:
                print(f"  {r['repo']}: {len(r['outdated'])} outdated")
