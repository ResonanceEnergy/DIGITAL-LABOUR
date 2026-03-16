import os
import json
import subprocess
from pathlib import Path

import pytest

# import path hack
import sys
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root)
sys.path.append(os.path.join(root, "agents"))

import agents.daily_brief as daily_brief
from agents import common
import agents.repo_sentry as repo_sentry


def init_git_repo(path: Path, files=None):
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, check=True)
    if files:
        for name, content in files.items():
            p = path / name
            p.write_text(content)
            subprocess.run(["git", "add", name], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=path, check=True)


def test_build_portfolio_brief(tmp_path, monkeypatch):
    # set up a fake portfolio and repo base, create a repo with a commit
    monkeypatch.setattr(common, "CONFIG", {"repos_base": str(
        tmp_path), "reports_dir": str(tmp_path / "reports")})
    monkeypatch.setattr(repo_sentry, "REPOS_BASE", Path(str(tmp_path)))
    monkeypatch.setattr(daily_brief, "REPOS_BASE", Path(str(tmp_path)))

    monkeypatch.setattr(repo_sentry, "PORTFOLIO", {
                        "repositories": [{"name": "X"}]})
    monkeypatch.setattr(daily_brief, "PORTFOLIO", {
                        "repositories": [{"name": "X"}]})
    # recompute BRI EFS_DIR after changing config
    daily_brief.BRIEFS_DIR = Path(common.CONFIG["reports_dir"]) / "daily"
    daily_brief.ensure_dir(daily_brief.BRIEFS_DIR)

    repo_root = tmp_path / "X"
    init_git_repo(repo_root, {"foo.py": "print('hi')"})

    # generate a delta plan for the repo
    repo_sentry.process_repo("X")

    # run brief builder
    daily_brief.build_portfolio_brief()

    import datetime
    brief_file = Path(common.CONFIG["reports_dir"]) / "daily" / \
                      f"brief_{datetime.date.today().isoformat()}.md"
    assert brief_file.exists()
    text = brief_file.read_text()
    assert "X" in text
    assert "Changes" in text
