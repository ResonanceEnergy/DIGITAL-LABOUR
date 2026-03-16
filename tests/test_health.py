"""Tests for /health, /agents, and / endpoints."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from api.rapidapi import rapid_app

client = TestClient(rapid_app)


def test_health_returns_200():
    resp = client.get("/health")
    assert resp.status_code == 200


def test_health_returns_healthy():
    resp = client.get("/health")
    data = resp.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_agents_returns_200():
    resp = client.get("/agents")
    assert resp.status_code == 200


def test_agents_lists_all_24():
    resp = client.get("/agents")
    data = resp.json()
    assert "agents" in data
    assert data["total"] == 24
    assert "endpoint" in data


def test_root_returns_200():
    resp = client.get("/")
    assert resp.status_code == 200


def test_root_contains_agents_list():
    resp = client.get("/")
    data = resp.json()
    assert "agents" in data
    assert "endpoints" in data


def test_v1_errors_returns_200():
    resp = client.get("/v1/errors")
    assert resp.status_code == 200
    data = resp.json()
    assert "errors" in data
    assert "count" in data


def test_v1_metrics_returns_200():
    resp = client.get("/v1/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "metrics" in data
    assert "timestamp" in data
