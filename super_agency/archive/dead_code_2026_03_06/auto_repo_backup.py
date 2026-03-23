#!/usr/bin/env python3
"""
DIGITAL LABOUR Auto Repo Backup
Backs up all portfolio repositories every 15 minutes
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(__file__).parent
BACKUP_DIR = WORKSPACE / "repo_backups"
BACKUP_LOG_DIR = WORKSPACE / "backup_logs"
PORTFOLIO_FILE = WORKSPACE / "portfolio.json"

# Create directories
BACKUP_DIR.mkdir(exist_ok=True)
BACKUP_LOG_DIR.mkdir(exist_ok=True)


def load_portfolio():
    """Load repository list from portfolio.json"""
    if not PORTFOLIO_FILE.exists():
        return []
    with open(PORTFOLIO_FILE) as f:
        data = json.load(f)
    return data.get("repositories", [])


def get_org():
    """Get organization name from portfolio"""
    if not PORTFOLIO_FILE.exists():
        return "ResonanceEnergy"
    with open(PORTFOLIO_FILE) as f:
        data = json.load(f)
    return data.get("org", "ResonanceEnergy")


def backup_repo(org: str, repo_name: str) -> dict:
    """Clone or pull a repository"""
    repo_path = BACKUP_DIR / repo_name
    result = {
        "repo": repo_name,
        "status": "unknown",
        "message": "",
        "timestamp": datetime.now().isoformat(),
    }

    try:
        if repo_path.exists():
            # Pull latest changes
            cmd = ["git", "-C", str(repo_path), "pull", "--ff-only"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if proc.returncode == 0:
                if "Already up to date" in proc.stdout:
                    result["status"] = "current"
                    result["message"] = "Already up to date"
                else:
                    result["status"] = "updated"
                    result["message"] = proc.stdout.strip()[:100]
            else:
                result["status"] = "pull_error"
                result["message"] = proc.stderr.strip()[:200]
        else:
            # Clone repository
            repo_url = f"https://github.com/{org}/{repo_name}.git"
            cmd = ["git", "clone", "--depth", "1", repo_url, str(repo_path)]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if proc.returncode == 0:
                result["status"] = "cloned"
                result["message"] = "Successfully cloned"
            else:
                result["status"] = "clone_error"
                result["message"] = proc.stderr.strip()[:200]
    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
        result["message"] = "Operation timed out"
    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)[:200]

    return result


def get_backup_stats():
    """Get stats about current backups"""
    stats = {"total_repos": 0, "total_size_mb": 0, "last_backup": None}

    if BACKUP_DIR.exists():
        repos = [d for d in BACKUP_DIR.iterdir() if d.is_dir()]
        stats["total_repos"] = len(repos)

        total_size = 0
        for repo in repos:
            for f in repo.rglob("*"):
                if f.is_file():
                    total_size += f.stat().st_size
        stats["total_size_mb"] = round(total_size / (1024 * 1024), 2)

    # Get last backup log
    logs = sorted(BACKUP_LOG_DIR.glob("backup_*.json"))
    if logs:
        stats["last_backup"] = logs[-1].stem.replace("backup_", "")

    return stats


def run_backup():
    """Run full backup of all repositories"""
    timestamp = datetime.now().isoformat()
    org = get_org()
    repos = load_portfolio()

    backup_result = {
        "timestamp": timestamp,
        "org": org,
        "total_repos": len(repos),
        "results": [],
        "summary": {"cloned": 0, "updated": 0, "current": 0, "errors": 0},
    }

    print(f"=" * 60)
    print(f"🔄 DIGITAL LABOUR REPO BACKUP - {timestamp}")
    print(f"=" * 60)
    print(f"📂 Organization: {org}")
    print(f"📊 Repositories: {len(repos)}")
    print(f"📁 Backup dir: {BACKUP_DIR}")
    print()

    for repo_info in repos:
        repo_name = repo_info["name"]
        print(f"📦 {repo_name}...", end=" ", flush=True)

        result = backup_repo(org, repo_name)
        backup_result["results"].append(result)

        # Update summary
        if result["status"] == "cloned":
            backup_result["summary"]["cloned"] += 1
            print("✅ Cloned")
        elif result["status"] == "updated":
            backup_result["summary"]["updated"] += 1
            print("⬆️ Updated")
        elif result["status"] == "current":
            backup_result["summary"]["current"] += 1
            print("✓ Current")
        else:
            backup_result["summary"]["errors"] += 1
            print(f"❌ {result['status']}: {result['message'][:50]}")

    # Get final stats
    stats = get_backup_stats()
    backup_result["stats"] = stats

    # Save backup log
    log_file = (
        BACKUP_LOG_DIR / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(log_file, "w") as f:
        json.dump(backup_result, f, indent=2)

    # Keep only last 50 backup logs
    logs = sorted(BACKUP_LOG_DIR.glob("backup_*.json"))
    for old_log in logs[:-50]:
        old_log.unlink()

    # Print summary
    print()
    print(f"=" * 60)
    print(f"📊 BACKUP SUMMARY")
    print(f"=" * 60)
    print(f"   ✅ Cloned:  {backup_result['summary']['cloned']}")
    print(f"   ⬆️  Updated: {backup_result['summary']['updated']}")
    print(f"   ✓  Current: {backup_result['summary']['current']}")
    print(f"   ❌ Errors:  {backup_result['summary']['errors']}")
    print(f"   📁 Total Size: {stats['total_size_mb']} MB")
    print(f"=" * 60)

    return backup_result


if __name__ == "__main__":
    run_backup()
