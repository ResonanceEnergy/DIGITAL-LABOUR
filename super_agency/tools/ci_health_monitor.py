#!/usr/bin/env python3
"""
CI/CD Health Monitor — checks GitHub Actions workflow status across
all portfolio repos, alerts on broken builds, and logs trends.

Uses GitHub CLI (gh) for API access to avoid direct token handling.

Usage::

    python tools/ci_health_monitor.py              # scan all repos
    python tools/ci_health_monitor.py <repo>        # scan specific repo
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

from agents.common import get_portfolio, Log, ensure_dir, now_iso  # noqa: E402

REPORTS_DIR = ROOT / "reports" / "ci_health"
ALERT_LOG = ROOT / "logs" / "alerts.ndjson"
ensure_dir(REPORTS_DIR)
ensure_dir(ALERT_LOG.parent)


def _gh_api(endpoint: str) -> Any:
    """Call GitHub API via gh CLI."""
    try:
        cp = subprocess.run(
            ["gh", "api", endpoint, "--paginate"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30,
        )
        if cp.returncode != 0:
            return None
        return json.loads(cp.stdout) if cp.stdout.strip() else None
    except (
        FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError,
    ):
        return None


def _get_repo_owner() -> str:
    """Get GitHub owner from gh CLI config."""
    try:
        cp = subprocess.run(
            ["gh", "repo", "view", "--json", "owner", "-q", ".owner.login"],
            capture_output=True, text=True, cwd=str(ROOT), timeout=10,
        )
        return cp.stdout.strip() if cp.returncode == 0 else "ResonanceEnergy"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "ResonanceEnergy"


def _emit_alert(
    alert_type: str, message: str,
    severity: str = "MEDIUM", **extra,
):
    """Write a structured alert."""
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "type": alert_type, "severity": severity,
        "message": message, "component": "ci_health_monitor",
        **extra,
    }
    try:
        with open(ALERT_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def check_repo_ci(repo_name: str, owner: str | None = None) -> dict[str, Any]:
    """Check CI/CD health for a single repo."""
    if owner is None:
        owner = _get_repo_owner()

    result: dict[str, Any] = {
        "repo": repo_name, "owner": owner, "checked_at": now_iso(),
        "has_workflows": False, "workflows": [], "status": "unknown",
        "failing": [], "passing": [],
    }

    # Get workflow runs (last 5)
    runs_data = _gh_api(f"/repos/{owner}/{repo_name}/actions/runs?per_page=5")
    if runs_data is None:
        result["status"] = "no_access"
        return result

    runs = runs_data.get("workflow_runs", [])
    if not runs:
        result["status"] = "no_runs"
        return result

    result["has_workflows"] = True
    seen_workflows: dict[str, dict] = {}

    for run in runs:
        wf_name = run.get("name", "unknown")
        if wf_name in seen_workflows:
            continue
        status = run.get("conclusion") or run.get("status", "unknown")
        wf_info = {
            "name": wf_name,
            "status": status,
            "branch": run.get("head_branch", "?"),
            "updated_at": run.get("updated_at", ""),
            "run_number": run.get("run_number", 0),
            "html_url": run.get("html_url", ""),
        }
        seen_workflows[wf_name] = wf_info
        if status == "failure":
            result["failing"].append(wf_info)
        elif status == "success":
            result["passing"].append(wf_info)

    result["workflows"] = list(seen_workflows.values())
    if result["failing"]:
        result["status"] = "failing"
    elif result["passing"]:
        result["status"] = "passing"
    else:
        result["status"] = "pending"

    return result


def scan_all() -> dict[str, Any]:
    """Scan CI health across all portfolio repos."""
    owner = _get_repo_owner()
    results = []
    failing_repos = []

    for repo in get_portfolio().get("repositories", []):
        name = repo["name"]
        ci = check_repo_ci(name, owner)
        results.append(ci)
        if ci["status"] == "failing":
            failing_repos.append(name)
            for wf in ci["failing"]:
                _emit_alert(
                    "ci_build_failure",
                    f"CI failing in {name}: {wf['name']}"
                    f" (run #{wf['run_number']})",
                    severity="HIGH", repo=name, workflow=wf["name"],
                )

    summary = {
        "scanned_at": now_iso(),
        "total_repos": len(results),
        "passing": sum(1 for r in results if r["status"] == "passing"),
        "failing": sum(1 for r in results if r["status"] == "failing"),
        "no_ci": sum(
            1 for r in results
            if r["status"] in ("no_runs", "no_access")
        ),
        "failing_repos": failing_repos,
        "repos": results,
    }

    # Save report
    stamp = datetime.now().strftime("%Y%m%d")
    report_path = REPORTS_DIR / f"ci_health_{stamp}.json"
    report_path.write_text(
        json.dumps(summary, indent=2), encoding="utf-8",
    )
    p, f_, n = summary["passing"], summary["failing"], summary["no_ci"]
    Log.info(f"CI health: {p} pass, {f_} fail, {n} no CI")

    if failing_repos:
        Log.warn(f"Failing repos: {', '.join(failing_repos)}")

    return summary


if __name__ == "__main__":
    if len(sys.argv) > 1:
        result = check_repo_ci(sys.argv[1])
        print(json.dumps(result, indent=2))
    else:
        summary = scan_all()
        p, f_ = summary["passing"], summary["failing"]
        print(f"\nCI Health: {p} passing, {f_} failing")
        if summary["failing_repos"]:
            print(f"Failing: {', '.join(summary['failing_repos'])}")
