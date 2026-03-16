"""Tests for tools.parallel_research"""

import os
import sys
import json

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, "tools"))

import pytest
from tools.parallel_research import (
    _load_projects,
    _load_topic_index,
    _research_repo,
    _research_project,
    run_parallel_research,
)


@pytest.fixture
def mock_dirs(tmp_path, monkeypatch):
    """Set up temp dirs for research tests."""
    import tools.parallel_research as pr

    projects_file = tmp_path / "config" / "research_projects.json"
    projects_file.parent.mkdir(parents=True)
    projects_file.write_text(json.dumps({
        "projects": [
            {
                "id": "test-proj",
                "name": "Test Project",
                "status": "active",
                "priority": "high",
                "description": "A test project",
                "repos": ["repo-alpha", "repo-beta"],
                "goals": ["Test goal"],
                "milestones": [
                    {"name": "M1", "status": "done"},
                    {"name": "M2", "status": "not-started"},
                ],
            },
            {
                "id": "test-proj-2",
                "name": "Second Project",
                "status": "planned",
                "priority": "medium",
                "description": "Another project",
                "repos": ["repo-gamma"],
                "goals": [],
                "milestones": [],
            },
        ]
    }), encoding="utf-8")

    repos_base = tmp_path / "repos"
    repos_base.mkdir()
    # Create repo-alpha with files
    alpha = repos_base / "repo-alpha"
    alpha.mkdir()
    (alpha / "README.md").write_text("# Alpha\nenergy research")
    (alpha / "main.py").write_text("print('hello')\n")
    tests_dir = alpha / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_main.py").write_text("def test_ok(): pass\n")
    # Create repo-beta (sparse)
    beta = repos_base / "repo-beta"
    beta.mkdir()
    (beta / "app.js").write_text("console.log('hi');\n")
    # Create repo-gamma
    gamma = repos_base / "repo-gamma"
    gamma.mkdir()
    (gamma / "README.md").write_text("# Gamma project\n")

    research_dir = tmp_path / "reports" / "research"
    research_dir.mkdir(parents=True)

    topic_index = tmp_path / "knowledge" / "secondbrain" / "topic_index.json"
    topic_index.parent.mkdir(parents=True)
    topic_index.write_text(json.dumps({
        "entries": {
            "vid1": {"keywords": ["energy", "research", "plasma"]},
        }
    }), encoding="utf-8")

    monkeypatch.setattr(pr, "PROJECTS_FILE", projects_file)
    monkeypatch.setattr(pr, "REPOS_BASE", repos_base)
    monkeypatch.setattr(pr, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(pr, "RESEARCH_DIR", research_dir)
    monkeypatch.setattr(pr, "TOPIC_INDEX", topic_index)

    return tmp_path


class TestLoadProjects:
    def test_loads_projects(self, mock_dirs):
        projects = _load_projects()
        assert len(projects) == 2
        assert projects[0]["id"] == "test-proj"

    def test_empty_when_missing(self, tmp_path, monkeypatch):
        import tools.parallel_research as pr
        monkeypatch.setattr(
            pr, "PROJECTS_FILE", tmp_path / "nope.json",
        )
        assert _load_projects() == []


class TestLoadTopicIndex:
    def test_loads_index(self, mock_dirs):
        idx = _load_topic_index()
        assert "entries" in idx
        assert "vid1" in idx["entries"]

    def test_empty_when_missing(self, tmp_path, monkeypatch):
        import tools.parallel_research as pr
        monkeypatch.setattr(
            pr, "TOPIC_INDEX", tmp_path / "nope.json",
        )
        assert _load_topic_index() == {}


class TestResearchRepo:
    def test_existing_repo(self, mock_dirs):
        import tools.parallel_research as pr
        rp = pr.REPOS_BASE / "repo-alpha"
        result = _research_repo(
            "repo-alpha", rp, {"energy", "research"},
        )
        assert result["status"] == "ok"
        assert result["health"]["score"] >= 1
        assert result["metrics"]["files"] >= 2
        assert "energy" in result["knowledge_links"]

    def test_missing_repo(self, mock_dirs):
        import tools.parallel_research as pr
        rp = pr.REPOS_BASE / "nonexistent"
        result = _research_repo("nonexistent", rp, set())
        assert result["status"] == "missing"

    def test_sparse_repo(self, mock_dirs):
        import tools.parallel_research as pr
        rp = pr.REPOS_BASE / "repo-beta"
        result = _research_repo("repo-beta", rp, set())
        assert result["status"] == "ok"
        assert "missing README" in result["health"]["issues"]
        assert result["knowledge_links"] == []


class TestResearchProject:
    def test_runs_project(self, mock_dirs):
        import tools.parallel_research as pr
        projects = _load_projects()
        result = _research_project(
            projects[0], {"energy", "research"}, 2,
        )
        assert result["project_id"] == "test-proj"
        assert result["repos_analysed"] == 2
        assert result["progress_pct"] == 50
        assert result["aggregate"]["total_files"] > 0

    def test_single_repo_project(self, mock_dirs):
        projects = _load_projects()
        result = _research_project(projects[1], set(), 2)
        assert result["project_id"] == "test-proj-2"
        assert result["repos_analysed"] == 1


class TestRunParallelResearch:
    def test_full_run(self, mock_dirs):
        path = run_parallel_research(
            max_project_workers=2,
            max_repo_workers=2,
        )
        assert path
        assert "parallel_research_" in path
        # Check both files exist
        import tools.parallel_research as pr
        md_files = list(
            pr.RESEARCH_DIR.glob("parallel_research_*.md")
        )
        json_files = list(
            pr.RESEARCH_DIR.glob("parallel_research_*.json")
        )
        assert len(md_files) >= 1
        assert len(json_files) >= 1
        # Verify JSON content
        data = json.loads(
            json_files[0].read_text(encoding="utf-8")
        )
        assert data["projects_analysed"] == 2

    def test_filter_project(self, mock_dirs):
        path = run_parallel_research(
            project_filter="test-proj-2",
        )
        import tools.parallel_research as pr
        json_files = list(
            pr.RESEARCH_DIR.glob("parallel_research_*.json")
        )
        data = json.loads(
            json_files[0].read_text(encoding="utf-8")
        )
        assert data["projects_analysed"] == 1
        assert data["projects"][0]["project_id"] == "test-proj-2"

    def test_no_projects(self, mock_dirs):
        path = run_parallel_research(
            project_filter="nonexistent",
        )
        assert path == ""
