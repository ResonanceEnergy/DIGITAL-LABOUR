"""Tests for tools.self_check_validator"""

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
def validator_env(tmp_path, monkeypatch):
    """Isolate validator from real filesystem."""
    import tools.self_check_validator as sv

    cfg = tmp_path / "config"
    cfg.mkdir()

    # Write required config files
    (cfg / "settings.json").write_text(
        json.dumps({
            "name": "Test",
            "version": "0.1",
            "tier": "L",
        }),
        encoding="utf-8",
    )
    (tmp_path / "agent_mandates.json").write_text(
        json.dumps({
            "mandates": {},
            "goals": {},
        }),
        encoding="utf-8",
    )
    (tmp_path / "agent_protocols.json").write_text(
        json.dumps({"protocols": {}}),
        encoding="utf-8",
    )
    (cfg / "skill_registry.json").write_text(
        json.dumps({"agents": {}}),
        encoding="utf-8",
    )
    (cfg / "research_projects.json").write_text(
        json.dumps({"projects": []}),
        encoding="utf-8",
    )
    (cfg / "intelligence_watchlist.json").write_text(
        json.dumps({"sources": []}),
        encoding="utf-8",
    )

    # Create directories
    (tmp_path / "reports" / "research").mkdir(
        parents=True,
    )
    (tmp_path / "reports" / "ideas").mkdir(
        parents=True,
    )
    (tmp_path / "reports" / "intelligence").mkdir(
        parents=True,
    )
    (tmp_path / "reports" / "metrics").mkdir(
        parents=True,
    )
    (tmp_path / "reports" / "validation").mkdir(
        parents=True,
    )
    (tmp_path / "logs").mkdir(parents=True)

    # Portfolio file
    (tmp_path / "portfolio.json").write_text(
        json.dumps({
            "repositories": [
                {"name": "test-repo"},
            ],
        }),
        encoding="utf-8",
    )

    monkeypatch.setattr(sv, "ROOT", tmp_path)
    monkeypatch.setattr(
        sv, "VALIDATION_DIR",
        tmp_path / "reports" / "validation",
    )
    monkeypatch.setattr(sv, "_bus", None)

    # Patch REQUIRED_CONFIGS paths
    monkeypatch.setattr(sv, "REQUIRED_CONFIGS", [
        (
            "config/settings.json",
            ["name", "version", "tier"],
        ),
        (
            "agent_mandates.json",
            ["mandates", "goals"],
        ),
        (
            "agent_protocols.json",
            ["protocols"],
        ),
        (
            "config/skill_registry.json",
            ["agents"],
        ),
        (
            "config/research_projects.json",
            ["projects"],
        ),
        (
            "config/intelligence_watchlist.json",
            ["sources"],
        ),
    ])

    return tmp_path


def test_validate_all_produces_result(
    validator_env,
):
    """Validator produces a result dict."""
    from tools.self_check_validator import (
        SystemValidator,
    )

    v = SystemValidator()
    result = v.validate_all()

    assert "integrity_score" in result
    assert "issues" in result
    assert isinstance(result["issues"], list)

    out = (
        validator_env / "reports" / "validation"
        / "latest_validation.json"
    )
    assert out.exists()


def test_config_validation_passes(validator_env):
    """All required config files pass validation."""
    from tools.self_check_validator import (
        SystemValidator,
    )

    v = SystemValidator()
    ok = v.validate_config()
    assert ok is True


def test_config_validation_detects_missing(
    validator_env,
):
    """Detects missing config file."""
    import tools.self_check_validator as sv

    # Remove a config file
    (validator_env / "agent_protocols.json").unlink()

    v = sv.SystemValidator()
    ok = v.validate_config()
    assert ok is False

    issues = [
        i for i in v.issues
        if "agent_protocols" in i.get("file", "")
    ]
    assert len(issues) >= 1


def test_pipeline_validation_empty_dirs(
    validator_env,
):
    """Detects empty pipeline output dirs."""
    from tools.self_check_validator import (
        SystemValidator,
    )

    v = SystemValidator()
    v.validate_pipeline()

    # All dirs exist but are empty
    pipeline_issues = [
        i for i in v.issues
        if i["category"] == "pipeline"
    ]
    assert len(pipeline_issues) >= 1


def test_health_no_log_file(validator_env):
    """Detects missing log file."""
    from tools.self_check_validator import (
        SystemValidator,
    )

    v = SystemValidator()
    v.validate_health()

    health_issues = [
        i for i in v.issues
        if i["category"] == "health"
    ]
    assert len(health_issues) >= 1


def test_data_portfolio_valid(validator_env):
    """Portfolio validation passes with data."""
    from tools.self_check_validator import (
        SystemValidator,
    )

    v = SystemValidator()
    ok = v.validate_data()
    assert ok is True


def test_score_decreases_with_issues(
    validator_env,
):
    """Score drops when issues are found."""
    from tools.self_check_validator import (
        SystemValidator,
    )

    v = SystemValidator()
    result = v.validate_all()

    # There should be some issues (empty pipeline etc)
    # so score should be < 100
    assert result["integrity_score"] <= 100
    if result["issue_count"] > 0:
        assert result["integrity_score"] < 100


def test_runtime_no_scheduler_state(
    validator_env,
):
    """Detects missing scheduler state."""
    from tools.self_check_validator import (
        SystemValidator,
    )

    v = SystemValidator()
    v.validate_runtime()

    runtime_issues = [
        i for i in v.issues
        if i["category"] == "runtime"
    ]
    assert len(runtime_issues) >= 1
