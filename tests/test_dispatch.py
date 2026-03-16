"""Tests for /v1/run dispatching all 24 agent types.

Uses mocked route_task to avoid making real LLM calls.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from api.rapidapi import rapid_app, ALL_AGENTS

client = TestClient(rapid_app)

_MOCK_EVENT = {
    "event_id": "test-task-id",
    "task_type": "sales_outreach",
    "outputs": {"result": "mocked output"},
    "qa": {"status": "PASS", "issues": []},
    "metrics": {"latency_ms": 42},
    "billing": {"amount": 0.0, "status": "unbilled"},
}


def _mock_event(agent: str) -> dict:
    return {**_MOCK_EVENT, "task_type": agent}


# ── Validation tests ────────────────────────────────────────────

def test_run_invalid_agent_returns_422():
    """Unknown agent name must return 422 Unprocessable Entity."""
    resp = client.post("/v1/run", json={"agent": "not_a_real_agent", "inputs": {}})
    assert resp.status_code == 422


def test_run_missing_agent_field_returns_422():
    """Missing required agent field must return 422."""
    resp = client.post("/v1/run", json={"inputs": {"company": "Test"}})
    assert resp.status_code == 422


def test_run_empty_body_returns_422():
    """Empty body must return 422."""
    resp = client.post("/v1/run", json={})
    assert resp.status_code == 422


# ── Dispatch tests (mocked, all 24 agents) ─────────────────────

@pytest.mark.parametrize("agent", ALL_AGENTS)
def test_run_all_agents_dispatched(agent: str):
    """Every agent in ALL_AGENTS must route correctly and return 200."""
    mock_event = _mock_event(agent)
    with patch("dispatcher.router.route_task", return_value=mock_event), \
         patch("dispatcher.router.create_event", return_value=mock_event):
        resp = client.post("/v1/run", json={"agent": agent, "inputs": {"company": "TestCo"}})

    assert resp.status_code == 200, f"Agent {agent!r} returned {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["agent"] == agent
    assert data["status"] == "completed"
    assert "task_id" in data
    assert "processing_time_ms" in data


def test_run_returns_agent_response_schema():
    """Verify /v1/run returns the full AgentResponse schema keys."""
    mock_event = _mock_event("sales_outreach")
    with patch("dispatcher.router.route_task", return_value=mock_event), \
         patch("dispatcher.router.create_event", return_value=mock_event):
        resp = client.post("/v1/run", json={"agent": "sales_outreach", "inputs": {"company": "Stripe"}})

    data = resp.json()
    for key in ("task_id", "agent", "status", "processing_time_ms", "result", "qa_status"):
        assert key in data, f"Missing key: {key}"
