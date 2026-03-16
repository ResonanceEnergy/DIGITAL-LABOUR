"""Tests for agents.message_bus"""

import os
import sys
import threading
import time

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root)

import pytest
from agents.message_bus import MessageBus


@pytest.fixture
def bus(tmp_path, monkeypatch):
    """Create an isolated MessageBus with a temp log dir."""
    monkeypatch.setattr("agents.message_bus.LOG_DIR", tmp_path)
    return MessageBus(max_history=50)


class TestMessageBus:
    def test_publish_no_subscribers(self, bus):
        """Publishing without subscribers should not error."""
        bus.publish("test.topic", {"key": "value"}, source="test")
        msgs = bus.recent()
        assert len(msgs) == 1
        assert msgs[0]["topic"] == "test.topic"

    def test_subscribe_and_receive(self, bus):
        received = []
        bus.subscribe("test.topic", lambda m: received.append(m.to_dict()))
        bus.publish("test.topic", {"x": 1}, source="tester")
        assert len(received) == 1
        assert received[0]["payload"]["x"] == 1

    def test_glob_subscribe(self, bus):
        received = []
        bus.subscribe("orchestrator.*", lambda m: received.append(m.topic))
        bus.publish("orchestrator.stage.start", {}, source="orch")
        bus.publish("orchestrator.run.done", {}, source="orch")
        bus.publish("unrelated.topic", {}, source="other")
        assert len(received) == 2
        assert "orchestrator.stage.start" in received
        assert "orchestrator.run.done" in received

    def test_unsubscribe(self, bus):
        received = []
        handler = lambda m: received.append(m.topic)
        bus.subscribe("a.b", handler)
        bus.publish("a.b", {})
        assert len(received) == 1
        bus.unsubscribe("a.b", handler)
        bus.publish("a.b", {})
        assert len(received) == 1  # no new messages after unsubscribe

    def test_recent_limit(self, bus):
        for i in range(10):
            bus.publish(f"t.{i}", {"i": i})
        msgs = bus.recent(limit=3)
        assert len(msgs) == 3

    def test_recent_topic_filter(self, bus):
        bus.publish("alpha.one", {"v": 1})
        bus.publish("beta.two", {"v": 2})
        bus.publish("alpha.three", {"v": 3})
        msgs = bus.recent(topic="alpha.*")
        assert len(msgs) == 2

    def test_stats(self, bus):
        bus.subscribe("x", lambda m: None)
        bus.publish("x", {})
        bus.publish("y", {})
        stats = bus.stats()
        assert stats["total_messages"] == 2
        assert len(stats["subscribers"]) >= 1

    def test_thread_safety(self, bus):
        """Concurrent publishes should not corrupt state."""
        results = []

        def publisher(n):
            for i in range(10):
                bus.publish(f"thread.{n}", {"i": i})
            results.append(n)

        threads = [threading.Thread(target=publisher, args=(i,))
                                    for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(results) == 4
        assert bus.stats()["total_messages"] == 40

    def test_persistence(self, bus, tmp_path):
        """Messages should be persisted to disk."""
        bus.publish("persist.test", {"data": "hello"})
        log_files = list(tmp_path.glob("bus_*.ndjson"))
        assert len(log_files) == 1
        content = log_files[0].read_text()
        assert "persist.test" in content
