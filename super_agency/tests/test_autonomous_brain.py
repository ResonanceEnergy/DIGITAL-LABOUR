"""Tests for tools.autonomous_brain"""

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
def brain_env(tmp_path, monkeypatch):
    """Isolate brain from real filesystem."""
    import tools.autonomous_brain as ab

    cfg = tmp_path / "config"
    cfg.mkdir()

    mandates = {
        "mandates": {
            "efficiency": {
                "description": "test",
                "target": "95%",
            },
        },
        "goals": {
            "short_term": [],
            "medium_term": [],
            "long_term": [
                "Full autonomous operation",
            ],
        },
    }

    (tmp_path / "agent_mandates.json").write_text(
        json.dumps(mandates), encoding="utf-8",
    )

    # Create required dirs
    (tmp_path / "logs" / "brain").mkdir(
        parents=True,
    )

    monkeypatch.setattr(ab, "ROOT", tmp_path)
    monkeypatch.setattr(
        ab, "BRAIN_STATE",
        cfg / "brain_state.json",
    )
    monkeypatch.setattr(
        ab, "MANDATES",
        tmp_path / "agent_mandates.json",
    )
    monkeypatch.setattr(
        ab, "LOG_DIR",
        tmp_path / "logs" / "brain",
    )
    monkeypatch.setattr(ab, "_bus", None)
    monkeypatch.setattr(
        ab, "MAX_ACTIONS_PER_CYCLE", 2,
    )

    return tmp_path


def test_brain_initializes(brain_env):
    """Brain loads mandates on init."""
    from tools.autonomous_brain import (
        AutonomousBrain,
    )

    brain = AutonomousBrain()
    assert brain.mandates.get("mandates")
    assert brain.state["cycle_count"] == 0


def test_brain_state_persistence(brain_env):
    """Brain state persists to disk."""
    from tools.autonomous_brain import (
        _save_state, _load_state,
    )

    state = {
        "cycle_count": 5,
        "last_cycle": "2026-03-11T10:00:00",
        "action_history": [],
        "gap_trends": {},
        "last_actions": {},
        "learnings": [],
    }
    _save_state(state)

    loaded = _load_state()
    assert loaded["cycle_count"] == 5


def test_brain_decide_respects_cooldown(brain_env):
    """DECIDE phase skips actions on cooldown."""
    import time as _time
    from tools.autonomous_brain import (
        AutonomousBrain,
    )

    brain = AutonomousBrain()
    brain.state["last_actions"] = {
        "run_metrics": _time.time(),
    }

    gaps = {
        "summary": {
            "top_actions": [
                {
                    "action": "run_metrics",
                    "priority_score": 10,
                },
                {
                    "action": "run_research",
                    "priority_score": 5,
                },
            ],
        },
    }

    selected = brain._decide(gaps)

    # run_metrics should be on cooldown
    action_ids = [s["action_id"] for s in selected]
    assert "run_metrics" not in action_ids
    assert "run_research" in action_ids


def test_brain_decide_unknown_action(brain_env):
    """DECIDE phase ignores unknown actions."""
    from tools.autonomous_brain import (
        AutonomousBrain,
    )

    brain = AutonomousBrain()
    gaps = {
        "summary": {
            "top_actions": [
                {
                    "action": "nonexistent_action",
                    "priority_score": 99,
                },
            ],
        },
    }

    selected = brain._decide(gaps)
    assert len(selected) == 0


def test_brain_act_missing_script(brain_env):
    """ACT phase handles missing scripts."""
    from tools.autonomous_brain import (
        AutonomousBrain,
    )

    brain = AutonomousBrain()
    actions = [
        {
            "action_id": "run_research",
            "priority": 5,
            "description": "test",
        },
    ]

    results = brain._act(actions)
    assert len(results) == 1
    assert results[0]["success"] is False
    assert results[0]["error"] == "script_not_found"


def test_brain_check_success(brain_env):
    """CHECK phase validates success rate."""
    from tools.autonomous_brain import (
        AutonomousBrain,
    )

    brain = AutonomousBrain()

    # All succeed
    results = [
        {"action_id": "a", "success": True},
        {"action_id": "b", "success": True},
    ]
    assert brain._check(results) is True

    # All fail
    results = [
        {"action_id": "a", "success": False},
        {"action_id": "b", "success": False},
    ]
    assert brain._check(results) is False


def test_brain_learn_updates_state(brain_env):
    """LEARN phase updates cycle count and trends."""
    from tools.autonomous_brain import (
        AutonomousBrain,
    )

    brain = AutonomousBrain()
    gaps = {
        "mandate_gaps": [
            {
                "id": "test_gap_1",
                "severity": "HIGH",
                "action": "run_research",
            },
        ],
        "research_gaps": [],
        "pipeline_gaps": [],
        "knowledge_gaps": [],
        "integration_gaps": [],
    }
    results = [
        {"action_id": "run_research", "success": True},
    ]

    brain._learn(gaps, results, True)

    assert brain.state["cycle_count"] == 1
    assert "test_gap_1" in brain.state["gap_trends"]
    assert len(brain.state["action_history"]) == 1

    # Check cycle log written
    logs = list(
        (brain_env / "logs" / "brain").glob("*.json")
    )
    assert len(logs) == 1


def test_brain_status(brain_env):
    """Status returns structured data."""
    from tools.autonomous_brain import (
        AutonomousBrain,
    )

    brain = AutonomousBrain()
    st = brain.status()

    assert "cycle_count" in st
    assert "recent_success_rate" in st
    assert "persistent_gaps" in st


def test_brain_think_with_stubs(brain_env):
    """Full think cycle with stubbed assess/analyze."""
    from tools.autonomous_brain import (
        AutonomousBrain,
    )

    brain = AutonomousBrain()

    # Stub the subprocess-heavy methods
    brain._assess = lambda: {
        "integrity_score": 85,
        "issues": [],
    }
    brain._analyze = lambda: {
        "summary": {"total_gaps": 0, "top_actions": []},
        "mandate_gaps": [],
        "research_gaps": [],
        "pipeline_gaps": [],
        "knowledge_gaps": [],
        "integration_gaps": [],
    }

    result = brain.think()

    assert result["cycle"] == 1
    assert result["actions_taken"] == 0
    assert result["integrity_score"] == 85
