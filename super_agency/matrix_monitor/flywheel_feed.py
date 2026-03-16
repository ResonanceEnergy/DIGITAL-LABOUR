#!/usr/bin/env python3
"""
MATRIX MONITOR - Flywheel Feed
================================
Live feed of RepoDepot flywheel status into the Matrix Monitor.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path

SHARED = Path(__file__).parent.parent
FLYWHEEL_STATE = SHARED / "state" / "flywheel"
REPOS_DIR = SHARED / "repos"
PORTFOLIO_FILE = SHARED / "portfolio.json"
OUTPUT_FILE = SHARED / "state" / "matrix_flywheel_status.json"


def get_cycle_log():
    log = FLYWHEEL_STATE / "cycle_log.jsonl"
    if not log.exists():
        return []
    cycles = []
    for line in log.read_text(
        encoding="utf-8", errors="replace").strip().splitlines():
        try:
            cycles.append(json.loads(line))
        except Exception:
            pass
    return cycles


def get_cycle_count():
    f = FLYWHEEL_STATE / "cycle_count.txt"
    if f.exists():
        try:
            return int(f.read_text().strip())
        except Exception:
            pass
    return 0


def get_repo_stats():
    if not PORTFOLIO_FILE.exists():
        return {}
    with open(PORTFOLIO_FILE, encoding="utf-8") as f:
        data = json.load(f)
    repos = data.get("repositories", [])
    total = len(repos)
    tiers = {"L": 0, "M": 0, "S": 0}
    for r in repos:
        t = r.get("tier", "S")
        tiers[t] = tiers.get(t, 0) + 1
    with_arch = sum(
        1 for r in repos
        if (REPOS_DIR / r["name"] / "docs" / "ARCHITECTURE.md").exists()
    )
    return {
        "total": total,
        "tiers": tiers,
        "with_architecture": with_arch,
        "arch_coverage_pct": round(with_arch / total * 100) if total else 0,
    }


def get_recent_commits(limit=10):
    commits = []
    if not REPOS_DIR.exists():
        return commits
    for repo_path in sorted(REPOS_DIR.iterdir()):
        if not (repo_path / ".git").exists():
            continue
        try:
            result = subprocess.run(
                ["git", "log", "-2", "--format=%h|%s|%ci|%an",
                 "--author=OPTIMUS", "--author=GASKET",
                 "--author=ResonanceEnergy", "--author=re-repo-bot"],
                cwd=repo_path, capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.strip().splitlines():
                parts = line.split("|", 3)
                if len(parts) == 4:
                    commits.append(
                        {"repo": repo_path.name, "sha": parts[0],
                         "message": parts[1] [: 80],
                         "time": parts[2] [: 19],
                         "author": parts[3]})
        except Exception:
            pass
    commits.sort(key=lambda c: c["time"], reverse=True)
    return commits[:limit]


def build_status():
    cycles = get_cycle_log()
    cycle_count = get_cycle_count()
    repo_stats = get_repo_stats()
    recent_commits = get_recent_commits()

    total_tasks = sum(c.get("tasks_dispatched", 0) for c in cycles)
    total_succeeded = sum(c.get("tasks_succeeded", 0) for c in cycles)
    total_artifacts = sum(c.get("artifacts_created", 0) for c in cycles)
    total_commits_made = sum(c.get("commits_made", 0) for c in cycles)
    total_failed = sum(c.get("tasks_failed", 0) for c in cycles)
    last_cycle = cycles[-1] if cycles else {}
    success_rate = round(total_succeeded / total_tasks * \
                         100) if total_tasks else 0

    return {
        "generated_at": datetime.now().isoformat(),
        "system": "REPO DEPOT FLYWHEEL",
        "operator": "OPTIMUS (Agent Y) on QUANTUM FORGE",
        "flywheel": {
            "cycle_count": cycle_count,
            "status": "idle",
            "success_rate_pct": success_rate,
            "total_tasks_dispatched": total_tasks,
            "total_tasks_succeeded": total_succeeded,
            "total_tasks_failed": total_failed,
            "total_artifacts_created": total_artifacts,
            "total_commits_made": total_commits_made,
        },
        "last_cycle": last_cycle,
        "repos": repo_stats,
        "recent_agent_commits": recent_commits,
        "health": {
            "encoding_fix": "applied",
            "git_author_tracking": "fixed",
            "cycle_log_retry": "enabled",
            "scheduler": "Windows Task Scheduler - every 6h",
            "cooldown_hours": 6,
        },
    }


def write_status():
    status = build_status()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(status, indent=2), encoding="utf-8")
    return status


def print_status(status):
    fw = status["flywheel"]
    repos = status["repos"]
    print("")
    print("=" * 60)
    print("  MATRIX MONITOR - REPO DEPOT FLYWHEEL FEED")
    print("=" * 60)
    print(f"  Generated: {status['generated_at'][:19]}")
    print(f"  Operator:  {status['operator']}")
    print("")
    print("  FLYWHEEL STATUS")
    print(f"    Cycles completed:   {fw['cycle_count']}")
    print(f"    Success rate:       {fw['success_rate_pct']}%")
    print(f"    Tasks dispatched:   {fw['total_tasks_dispatched']}")
    print(f"    Tasks succeeded:    {fw['total_tasks_succeeded']}")
    print(f"    Artifacts created:  {fw['total_artifacts_created']}")
    print(f"    Commits made:       {fw['total_commits_made']}")
    print("")
    print("  REPO PORTFOLIO")
    print(f"    Total repos:        {repos.get('total', 0)}")
    t = repos.get("tiers", {})
    print(
        f"    Tiers:              L={t.get('L',0)}  M={t.get('M',0)}  S={t.get('S',0)}")
    print(
        f"    Architecture docs:  {repos.get('with_architecture',0)}/{repos.get('total',0)} ({repos.get('arch_coverage_pct',0)}%)")
    print("")
    print("  RECENT AGENT COMMITS")
    for c in status.get("recent_agent_commits", [])[:5]:
        print(
            f"    [{c['time'][5:16]}] {c['repo'][:25].ljust(25)} {c['message'][:40]}")
    print("")
    print("  HEALTH")
    for k, v in status["health"].items():
        print(f"    {k.replace('_',' ').ljust(28)} {v}")
    print("=" * 60)
    print("")


if __name__ == "__main__":
    status = write_status()
    print_status(status)
    print(f"Status written to: {OUTPUT_FILE}")
