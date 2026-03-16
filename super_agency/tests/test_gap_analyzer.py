"""Tests for tools.gap_analyzer"""

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
def gap_env(tmp_path, monkeypatch):
    """Isolate gap analyzer from real filesystem."""
    import tools.gap_analyzer as ga

    # Config files
    cfg = tmp_path / "config"
    cfg.mkdir()

    mandates = {
        "mandates": {
            "efficiency": {
                "description": "test",
                "target": "95%",
            },
            "reliability": {
                "description": "test",
                "target": "99.9%",
            },
            "innovation": {
                "description": "test",
                "target": "1/wk",
            },
        },
        "goals": {
            "short_term": ["Complete backlog"],
            "medium_term": ["Automate 80%"],
            "long_term": [
                "Full autonomous operation",
            ],
        },
    }

    protocols = {
        "protocols": {
            "task_prioritization": {
                "rule": "HIGH > MEDIUM > LOW",
            },
        },
    }

    settings = {
        "name": "Test-Agency",
        "version": "0.1.0",
        "tier": "L",
    }

    skills = {
        "agents": {
            "repo_sentry": {
                "capabilities": ["scan"],
            },
            "daily_brief": {
                "capabilities": ["brief"],
            },
        },
    }

    projects = {
        "projects": [
            {
                "name": "Test Project",
                "repos": [
                    {"name": "test-repo"},
                ],
                "milestones": [
                    {"name": "m1", "status": "todo"},
                    {"name": "m2", "status": "todo"},
                    {"name": "m3", "status": "todo"},
                ],
            },
        ],
    }

    watchlist = {
        "sources": [
            {"name": "TestChannel", "type": "yt"},
        ],
    }

    # Write all config files
    (tmp_path / "agent_mandates.json").write_text(
        json.dumps(mandates), encoding="utf-8",
    )
    (tmp_path / "agent_protocols.json").write_text(
        json.dumps(protocols), encoding="utf-8",
    )
    (cfg / "settings.json").write_text(
        json.dumps(settings), encoding="utf-8",
    )
    (cfg / "skill_registry.json").write_text(
        json.dumps(skills), encoding="utf-8",
    )
    (cfg / "research_projects.json").write_text(
        json.dumps(projects), encoding="utf-8",
    )
    (cfg / "intelligence_watchlist.json").write_text(
        json.dumps(watchlist), encoding="utf-8",
    )

    # Create empty directories
    (tmp_path / "reports" / "ideas").mkdir(
        parents=True,
    )
    (tmp_path / "reports" / "research").mkdir(
        parents=True,
    )
    (tmp_path / "reports" / "intelligence").mkdir(
        parents=True,
    )
    (tmp_path / "reports" / "metrics").mkdir(
        parents=True,
    )
    (tmp_path / "reports" / "gaps").mkdir(
        parents=True,
    )
    (tmp_path / "knowledge" / "secondbrain").mkdir(
        parents=True,
    )
    (tmp_path / "logs").mkdir(parents=True)

    # Monkeypatch paths
    monkeypatch.setattr(ga, "ROOT", tmp_path)
    monkeypatch.setattr(
        ga, "MANDATES",
        tmp_path / "agent_mandates.json",
    )
    monkeypatch.setattr(
        ga, "PROTOCOLS",
        tmp_path / "agent_protocols.json",
    )
    monkeypatch.setattr(
        ga, "SETTINGS_FILE",
        cfg / "settings.json",
    )
    monkeypatch.setattr(
        ga, "SKILLS",
        cfg / "skill_registry.json",
    )
    monkeypatch.setattr(
        ga, "PROJECTS",
        cfg / "research_projects.json",
    )
    monkeypatch.setattr(
        ga, "WATCHLIST",
        cfg / "intelligence_watchlist.json",
    )
    monkeypatch.setattr(
        ga, "SCHED_STATE",
        cfg / "scheduler_state.json",
    )
    monkeypatch.setattr(
        ga, "METRICS_HIST",
        tmp_path / "reports" / "metrics"
        / "metrics_history.json",
    )
    monkeypatch.setattr(
        ga, "KNOWLEDGE_DIR",
        tmp_path / "knowledge" / "secondbrain",
    )
    monkeypatch.setattr(
        ga, "REPORTS_DIR",
        tmp_path / "reports",
    )
    monkeypatch.setattr(
        ga, "IDEAS_DIR",
        tmp_path / "reports" / "ideas",
    )
    monkeypatch.setattr(
        ga, "RESEARCH_DIR",
        tmp_path / "reports" / "research",
    )
    monkeypatch.setattr(
        ga, "INTEL_DIR",
        tmp_path / "reports" / "intelligence",
    )
    monkeypatch.setattr(
        ga, "GAPS_DIR",
        tmp_path / "reports" / "gaps",
    )
    monkeypatch.setattr(
        ga, "BRAIN_STATE",
        cfg / "brain_state.json",
    )
    monkeypatch.setattr(ga, "_bus", None)

    return tmp_path


def test_full_analysis_produces_output(gap_env):
    """Gap analyzer produces a result dict."""
    from tools.gap_analyzer import GapAnalyzer

    analyzer = GapAnalyzer()
    result = analyzer.analyze()

    assert "summary" in result
    assert "total_gaps" in result["summary"]
    assert result["summary"]["total_gaps"] >= 0

    # Report file written
    out = gap_env / "reports" / "gaps" / "latest_gaps.json"
    assert out.exists()


def test_mandate_gaps_found(gap_env):
    """Detects mandate-related gaps."""
    from tools.gap_analyzer import GapAnalyzer

    analyzer = GapAnalyzer()
    gaps = analyzer.mandate_gaps()

    # Should find efficiency (no metrics) and
    # innovation (no ideas) and autonomy (no brain)
    ids = [g["id"] for g in gaps]
    assert "mandate_efficiency_untracked" in ids
    assert "goal_autonomy_not_active" in ids


def test_pipeline_gaps_no_scheduler(gap_env):
    """Detects missing scheduler state."""
    from tools.gap_analyzer import GapAnalyzer

    analyzer = GapAnalyzer()
    gaps = analyzer.pipeline_gaps()

    ids = [g["id"] for g in gaps]
    assert "pipeline_scheduler_no_state" in ids


def test_knowledge_gaps_no_ingests(gap_env):
    """Detects empty knowledge base."""
    from tools.gap_analyzer import GapAnalyzer

    analyzer = GapAnalyzer()
    gaps = analyzer.knowledge_gaps()

    ids = [g["id"] for g in gaps]
    assert "knowledge_no_ingests" in ids


def test_integration_gaps_sparse_skills(gap_env):
    """Detects underpopulated skill registry."""
    from tools.gap_analyzer import GapAnalyzer

    analyzer = GapAnalyzer()
    gaps = analyzer.integration_gaps()

    ids = [g["id"] for g in gaps]
    assert "integration_sparse_skills" in ids


def test_top_actions_ranked(gap_env):
    """Top actions are ranked by severity score."""
    from tools.gap_analyzer import GapAnalyzer

    analyzer = GapAnalyzer()
    result = analyzer.analyze()

    top = result["summary"]["top_actions"]
    if len(top) >= 2:
        assert (
            top[0]["priority_score"]
            >= top[1]["priority_score"]
        )


def test_research_gaps_incomplete_milestones(
    gap_env,
):
    """Detects projects with mostly incomplete milestones."""
    from tools.gap_analyzer import GapAnalyzer

    analyzer = GapAnalyzer()
    gaps = analyzer.research_gaps()

    # Test project has 3/3 milestones incomplete
    milestone_gaps = [
        g for g in gaps
        if "milestones" in g.get("id", "")
    ]
    assert len(milestone_gaps) >= 1
