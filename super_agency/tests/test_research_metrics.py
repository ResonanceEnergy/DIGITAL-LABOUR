"""Tests for tools.research_metrics"""

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
def metrics_env(tmp_path, monkeypatch):
    """Isolate metrics from the real filesystem."""
    import tools.research_metrics as rm

    monkeypatch.setattr(rm, "ROOT", tmp_path)
    monkeypatch.setattr(rm, "_bus", None)

    # Populate minimal config
    cfg = tmp_path / "config"
    cfg.mkdir(parents=True)

    (cfg / "research_projects.json").write_text(
        json.dumps({
            "projects": [
                {
                    "id": "test-proj",
                    "name": "Test Project",
                    "status": "active",
                    "priority": "high",
                    "repos": ["repo-a", "repo-b"],
                    "goals": ["G1"],
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
                }
            ]
        }),
        encoding="utf-8",
    )

    (cfg / "portfolio.json").write_text(
        json.dumps({"repos": [
            {"name": "repo-a"},
            {"name": "repo-b"},
        ]}),
        encoding="utf-8",
    )

    (cfg / "intelligence_watchlist.json").write_text(
        json.dumps({"sources": [
            {"id": "src-1", "name": "Source 1"},
        ]}),
        encoding="utf-8",
    )

    # Create dirs
    (tmp_path / "knowledge" / "secondbrain").mkdir(
        parents=True,
    )
    (tmp_path / "reports" / "intelligence").mkdir(
        parents=True,
    )
    (tmp_path / "reports" / "metrics").mkdir(
        parents=True,
    )
    (tmp_path / "reports" / "research").mkdir(
        parents=True,
    )

    # Topic index
    (tmp_path / "knowledge").mkdir(exist_ok=True)
    (tmp_path / "knowledge" / "topic_index.json").write_text(
        json.dumps({
            "entries": {
                "topic-a": {
                    "keywords": ["energy", "plasma"],
                }
            },
            "total_entries": 1,
            "total_keywords": 2,
        }),
        encoding="utf-8",
    )

    # Create repo directories
    repos = tmp_path / "repos"
    repos.mkdir()
    (repos / "repo-a").mkdir()
    (repos / "repo-b").mkdir()

    return tmp_path


def test_generate_dashboard(metrics_env):
    from tools.research_metrics import generate_dashboard
    dashboard = generate_dashboard()
    assert "generated_at" in dashboard
    assert "health_score" in dashboard
    assert 0 <= dashboard["health_score"] <= 100
    ic = dashboard["intelligence_cycle"]
    assert "1_collection" in ic
    assert "2_processing" in ic
    assert "3_analysis" in ic


def test_render_dashboard_md(metrics_env):
    from tools.research_metrics import (
        generate_dashboard, render_dashboard_md,
    )
    dashboard = generate_dashboard()
    md = render_dashboard_md(dashboard)
    assert "Research Intelligence Dashboard" in md
    assert "Overall Health" in md


def test_dashboard_has_kpi_sections(metrics_env):
    from tools.research_metrics import generate_dashboard
    d = generate_dashboard()
    ic = d["intelligence_cycle"]
    for section in [
        "1_collection", "2_processing",
        "3_analysis", "4_synthesis",
        "5_dissemination",
    ]:
        assert section in ic, (
            f"Missing section: {section}"
        )
    assert "system" in d


def test_history_appended(metrics_env, monkeypatch):
    import tools.research_metrics as rm

    hist_file = (
        metrics_env / "reports" / "metrics"
        / "metrics_history.json"
    )
    monkeypatch.setattr(
        rm, "METRICS_HISTORY",
        hist_file,
    )

    from tools.research_metrics import generate_dashboard
    generate_dashboard()

    assert hist_file.exists()
    data = json.loads(
        hist_file.read_text(encoding="utf-8")
    )
    assert len(data) >= 1
    assert "health_score" in data[0]
