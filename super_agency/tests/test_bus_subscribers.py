"""Tests for agents.bus_subscribers"""

import os
import sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root)

import pytest
from agents.message_bus import MessageBus, Message


@pytest.fixture
def fresh_bus(tmp_path, monkeypatch):
    monkeypatch.setattr("agents.message_bus.LOG_DIR", tmp_path)
    import agents.message_bus as mb
    original = mb.bus
    mb.bus = MessageBus(max_history=50)
    monkeypatch.setattr("agents.bus_subscribers.bus", mb.bus)
    yield mb.bus
    mb.bus = original


def test_register_all_wires_subscribers(fresh_bus):
    from agents.bus_subscribers import register_all
    register_all()
    # After registration there should be subscribers for these patterns
    assert len(fresh_bus._subs) >= 3


def test_stage_fail_logged(fresh_bus, caplog):
    import logging
    from agents.bus_subscribers import register_all
    register_all()
    with caplog.at_level(logging.WARNING):
        fresh_bus.publish("orchestrator.stage.fail", {
                          "stage": "sentry", "code": 1}, source="test")
    assert "sentry" in caplog.text
    assert "FAILED" in caplog.text


def test_event_log_written(fresh_bus, tmp_path, monkeypatch):
    import agents.bus_subscribers as bs
    monkeypatch.setattr(bs, "_EVENTS_LOG", tmp_path / "events.ndjson")
    from agents.bus_subscribers import register_all
    register_all()
    fresh_bus.publish("orchestrator.run.start", {}, source="test")
    log_content = (tmp_path / "events.ndjson").read_text()
    assert "orchestrator.run.start" in log_content
