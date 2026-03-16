import os
import json
import subprocess
from pathlib import Path

import pytest

# ensure agents can be imported
import sys
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root)
sys.path.append(os.path.join(root, "agents"))

import agents.repo_sentry as repo_sentry
from agents import common


def init_git_repo(path: Path, files=None):
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, check=True)
    if files:
        for name, content in files.items():
            p = path / name
            p.write_text(content)
            subprocess.run(["git", "add", name], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=path, check=True)


def test_process_repo_creates_reports(tmp_path, monkeypatch):
    # configure portfolio & repo base
    monkeypatch.setattr(common, "CONFIG", {"repos_base": str(tmp_path)})
    monkeypatch.setattr(repo_sentry, "REPOS_BASE", Path(str(tmp_path)))
    monkeypatch.setattr(repo_sentry, "PORTFOLIO", {
                        "repositories": [{"name": "X"}]})

    repo_root = tmp_path / "X"
    init_git_repo(repo_root, {"foo.py": "print('hi')"})

    # run once, should produce report and state file
    repo_sentry.process_repo("X")
    reports = list((repo_root / "reports").glob("delta_plan_*.json"))
    assert len(reports) == 1
    plan = json.loads(reports[0].read_text())
    assert plan["repo"] == "X"
    assert plan["summary"]["code"] == 1

    # run again without change; logic writes same filename so count remains 1
    repo_sentry.process_repo("X")
    reports = list((repo_root / "reports").glob("delta_plan_*.json"))
    assert len(reports) == 1
    # file updated; check that head commit still exists
    plan2 = json.loads(reports[0].read_text())
    assert plan2["repo"] == "X"


def test_process_repo_handles_missing(tmp_path, monkeypatch, caplog, capsys):
    monkeypatch.setattr(common, "CONFIG", {"repos_base": str(tmp_path)})
    monkeypatch.setattr(repo_sentry, "REPOS_BASE", Path(str(tmp_path)))
    monkeypatch.setattr(repo_sentry, "PORTFOLIO", {
                        "repositories": [{"name": "MISSING"}]})

    # capture stdout from Log.warn
    repo_sentry.process_repo("MISSING")
    out = capsys.readouterr().out
    assert "Repo not found locally" in out
