"""Tests for tools.idea_engine"""

import os
import sys
import json

root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, "tools"))

import pytest  # noqa: E402


@pytest.fixture
def idea_env(tmp_path, monkeypatch):
    """Isolate idea engine from real filesystem."""
    import tools.idea_engine as ie

    monkeypatch.setattr(ie, "ROOT", tmp_path)
    monkeypatch.setattr(ie, "_bus", None)

    # Config
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True)

    (cfg / "research_projects.json").write_text(
        json.dumps({
            "projects": [
                {
                    "id": "proj-alpha",
                    "name": "Alpha Project",
                    "status": "active",
                    "priority": "high",
                    "repos": ["repo-a", "repo-b"],
                    "goals": ["Goal A"],
                    "milestones": [
                        {
                            "name": "M1",
                            "status": "done",
                        },
                        {
                            "name": "M2",
                            "status": "not-started",
                        },
                    ],
                },
                {
                    "id": "proj-beta",
                    "name": "Beta Project",
                    "status": "active",
                    "priority": "medium",
                    "repos": ["repo-c"],
                    "goals": [],
                    "milestones": [
                        {
                            "name": "M3",
                            "status": "not-started",
                        },
                    ],
                },
            ]
        }),
        encoding="utf-8",
    )

    (cfg / "portfolio.json").write_text(
        json.dumps({"repos": [
            {"name": "repo-a"},
            {"name": "repo-b"},
            {"name": "repo-c"},
        ]}),
        encoding="utf-8",
    )

    (cfg / "settings.json").write_text(
        json.dumps({"repos_base": "repos"}),
        encoding="utf-8",
    )

    # Knowledge index
    know = tmp_path / "knowledge"
    know.mkdir(parents=True)
    (know / "topic_index.json").write_text(
        json.dumps({
            "entries": {},
            "total_entries": 0,
            "total_keywords": 0,
        }),
        encoding="utf-8",
    )

    # Repos with README files containing keywords
    repos = tmp_path / "repos"
    repos.mkdir()
    ra = repos / "repo-a"
    ra.mkdir()
    (ra / "README.md").write_text(
        "# Repo A\nPlasma energy vortex research\n"
        "Tesla coil experiments with resonance\n"
    )

    rb = repos / "repo-b"
    rb.mkdir()
    (rb / "README.md").write_text(
        "# Repo B\nElectric field experiments\n"
        "Plasma dynamics and vortex flow\n"
    )

    rc = repos / "repo-c"
    rc.mkdir()
    (rc / "README.md").write_text(
        "# Repo C\nHealth longevity protocols\n"
    )

    # Reports dir
    (tmp_path / "reports" / "ideas").mkdir(
        parents=True,
    )

    return tmp_path


def test_cross_pollinate(idea_env):
    from tools.idea_engine import cross_pollinate
    links = cross_pollinate()
    assert isinstance(links, list)


def test_analyse_gaps(idea_env):
    from tools.idea_engine import analyse_gaps
    gaps = analyse_gaps()
    assert isinstance(gaps, list)
    # Should find incomplete milestones
    gap_types = [g["type"] for g in gaps]
    assert "incomplete_milestones" in gap_types


def test_generate_hypotheses(idea_env):
    from tools.idea_engine import generate_hypotheses
    hyps = generate_hypotheses()
    assert isinstance(hyps, list)


def test_generate_research_questions(idea_env):
    from tools.idea_engine import (
        generate_research_questions,
    )
    qs = generate_research_questions()
    assert isinstance(qs, list)


def test_generate_ideas_full(idea_env):
    from tools.idea_engine import generate_ideas
    report = generate_ideas()
    assert "generated_at" in report
    assert "cross_pollinations" in report
    assert "gaps" in report
    assert "hypotheses" in report
    assert "research_questions" in report


def test_repo_keywords(idea_env, monkeypatch):
    import tools.idea_engine as ie
    monkeypatch.setattr(
        ie, "REPOS_BASE", idea_env / "repos",
    )
    kw = ie._repo_keywords("repo-a")
    assert isinstance(kw, set)
    # Should have extracted some keywords
    assert len(kw) > 0
