#!/usr/bin/env python3
"""
DIGITAL LABOUR Message Bus — lightweight in-process event bus.

Provides pub/sub messaging between agents running inside run_digital_labour.py.
Messages are also persisted to disk for cross-process / post-mortem inspection.

Usage:
    from agents.message_bus import bus

    # Subscribe
    bus.subscribe("research.complete", my_handler)

    # Publish
    bus.publish("research.complete", {"project": "energy-research", "status": "ok"})

    # Get recent messages
    bus.recent(topic="research.*", limit=10)
"""

import json
import re
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs" / "message_bus"
LOG_DIR.mkdir(parents=True, exist_ok=True)


class Message:
    __slots__ = ("topic", "payload", "ts", "source")

    def __init__(self, topic: str, payload: dict, source: str = "unknown"):
        self.topic = topic
        self.payload = payload
        self.ts = datetime.now().isoformat(timespec="seconds")
        self.source = source

    def to_dict(self) -> dict:
        return {"topic": self.topic, "payload": self.payload, "ts": self.ts, "source": self.source}


class MessageBus:
    """Thread-safe in-process pub/sub message bus."""

    def __init__(self, max_history: int = 500):
        self._lock = threading.Lock()
        self._subs: Dict[str, List[Callable]] = {}  # topic_pattern → [handler]
        self._history: deque = deque(maxlen=max_history)
        self._log_file = LOG_DIR / \
            f"bus_{datetime.now().strftime('%Y-%m-%d')}.ndjson"

    # ── Pub / Sub ────────────────────────────────────────────────────────

    def subscribe(self, topic_pattern: str, handler: Callable):
        """Subscribe to messages matching topic_pattern (supports * glob)."""
        with self._lock:
            self._subs.setdefault(topic_pattern, []).append(handler)

    def unsubscribe(self, topic_pattern: str, handler: Callable):
        """Remove a specific handler."""
        with self._lock:
            handlers = self._subs.get(topic_pattern, [])
            if handler in handlers:
                handlers.remove(handler)

    def publish(self, topic: str, payload: dict = None, source: str = "unknown"):
        """Publish a message. Handlers are called synchronously in the publisher's thread."""
        msg = Message(topic, payload or {}, source)
        with self._lock:
            self._history.append(msg)
            matched = self._match_handlers(topic)

        # Persist (best-effort, outside lock)
        self._persist(msg)

        # Dispatch
        for handler in matched:
            try:
                handler(msg)
            except Exception:
                pass  # handlers must not crash the bus

    def _match_handlers(self, topic: str) -> list:
        """Return handlers whose pattern matches the topic."""
        out = []
        for pat, handlers in self._subs.items():
            regex = "^" + pat.replace(".", r"\.").replace("*", ".*") + "$"
            if re.match(regex, topic):
                out.extend(handlers)
        return out

    # ── Query ────────────────────────────────────────────────────────────

    def recent(self, topic: str = "*", limit: int = 20) -> List[dict]:
        """Return recent messages matching topic glob."""
        regex = "^" + topic.replace(".", r"\.").replace("*", ".*") + "$"
        with self._lock:
            matches = [m.to_dict()
                                 for m in self._history if re.match(regex, m.topic)]
        return matches[-limit:]

    def stats(self) -> dict:
        """Return bus statistics."""
        with self._lock:
            return {
                "total_messages": len(self._history),
                "subscribers": {k: len(v) for k, v in self._subs.items()},
                "log_file": str(self._log_file),
            }

    # ── Persistence ──────────────────────────────────────────────────────

    def _persist(self, msg: Message):
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(msg.to_dict()) + "\n")
        except OSError:
            pass


# ── Singleton ────────────────────────────────────────────────────────────
bus = MessageBus()
