"""Tests for tools.research_scheduler"""

import os
import sys
import json

root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
sys.path.insert(0, root)
sys.path.insert(0, os.path.join(root, "tools"))

import pytest
from datetime import datetime, timedelta, timezone


@pytest.fixture
def sched_env(tmp_path, monkeypatch):
    """Isolate scheduler state and report paths."""
    import tools.research_scheduler as rs

    state_file = tmp_path / "config" / "scheduler_state.json"
    state_file.parent.mkdir(parents=True)
    monkeypatch.setattr(rs, "SCHEDULER_STATE", state_file)
    monkeypatch.setattr(rs, "ROOT", tmp_path)
    monkeypatch.setattr(rs, "_bus", None)

    # Create reports dir
    (tmp_path / "reports" / "metrics").mkdir(
        parents=True
    )

    return tmp_path, state_file


def test_load_state_empty(sched_env):
    from tools.research_scheduler import _load_state
    state = _load_state()
    assert "last_run" in state
    assert "run_count" in state


def test_save_and_load_state(sched_env):
    from tools.research_scheduler import (
        _load_state, _save_state,
    )
    state = _load_state()
    state["last_run"]["fast"] = "2025-01-01T00:00:00"
    state["run_count"]["fast"] = 5
    _save_state(state)

    loaded = _load_state()
    assert loaded["last_run"]["fast"] == (
        "2025-01-01T00:00:00"
    )
    assert loaded["run_count"]["fast"] == 5


def test_is_cycle_due_never_run(sched_env):
    from tools.research_scheduler import _is_cycle_due
    state = {"last_run": {}, "run_count": {}}
    assert _is_cycle_due("fast", state) is True
    assert _is_cycle_due("standard", state) is True


def test_is_cycle_due_recently_run(sched_env):
    from tools.research_scheduler import _is_cycle_due
    now = datetime.now(timezone.utc).isoformat()
    state = {"last_run": {"fast": now}, "run_count": {}}
    assert _is_cycle_due("fast", state) is False


def test_is_cycle_due_old_run(sched_env):
    from tools.research_scheduler import _is_cycle_due
    old = (
        datetime.now(timezone.utc) - timedelta(hours=2)
    ).isoformat()
    state = {"last_run": {"fast": old}, "run_count": {}}
    assert _is_cycle_due("fast", state) is True


def test_run_cycle_with_stub_stages(
    sched_env, monkeypatch,
):
    import tools.research_scheduler as rs

    called = []

    def stub_runner():
        called.append("stub")
        return {"ok": True}

    # Replace all stage runners with stubs
    for key in rs.STAGE_RUNNERS:
        monkeypatch.setitem(
            rs.STAGE_RUNNERS, key, stub_runner,
        )

    result = rs.run_cycle("fast")
    assert result["status"] == "ok"
    assert result["cycle"] == "fast"
    assert len(called) > 0


def test_run_cycle_handles_errors(
    sched_env, monkeypatch,
):
    import tools.research_scheduler as rs

    def failing_runner():
        raise RuntimeError("test failure")

    for key in rs.STAGE_RUNNERS:
        monkeypatch.setitem(
            rs.STAGE_RUNNERS, key, failing_runner,
        )

    result = rs.run_cycle("fast")
    assert result["status"] == "partial"
    assert len(result["errors"]) > 0


def test_get_status(sched_env):
    from tools.research_scheduler import get_status

    status = get_status()
    assert "cycles" in status
    assert "fast" in status["cycles"]
    assert "standard" in status["cycles"]
    assert "deep" in status["cycles"]
    assert "weekly" in status["cycles"]

    fast = status["cycles"]["fast"]
    assert fast["is_due"] is True
    assert fast["last_run"] == "never"


def test_run_all_due_with_stubs(
    sched_env, monkeypatch,
):
    import tools.research_scheduler as rs

    monkeypatch.setitem(
        rs.STAGE_RUNNERS,
        "metrics_snapshot",
        lambda: {"ok": True},
    )
    for key in rs.STAGE_RUNNERS:
        monkeypatch.setitem(
            rs.STAGE_RUNNERS, key, lambda: {},
        )

    results = rs.run_all_due()
    # All cycles should be due on first run
    assert len(results) == 4
    cycle_names = [r["cycle"] for r in results]
    assert "fast" in cycle_names
    assert "standard" in cycle_names


def test_cycles_config_valid(sched_env):
    from tools.research_scheduler import CYCLES

    for name, cycle in CYCLES.items():
        assert "interval_minutes" in cycle
        assert "stages" in cycle
        assert "description" in cycle
        assert cycle["interval_minutes"] > 0
        assert len(cycle["stages"]) > 0


def test_state_error_capping(sched_env, monkeypatch):
    """Errors list is capped at 50 entries."""
    import tools.research_scheduler as rs

    def failing():
        raise RuntimeError("boom")

    for key in rs.STAGE_RUNNERS:
        monkeypatch.setitem(
            rs.STAGE_RUNNERS, key, failing,
        )

    # Run many cycles to accumulate errors
    for _ in range(20):
        rs.run_cycle("fast")

    state = rs._load_state()
    assert len(state.get("errors", [])) <= 50
