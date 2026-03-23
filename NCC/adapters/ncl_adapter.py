"""NCL Adapter — bridges BRAIN cognition events to BRS orchestrator."""
from __future__ import annotations

import json
import logging
from pathlib import Path

_log = logging.getLogger("brs.adapter.ncl")

NCL_EVENTS_FILE = Path(__file__).resolve().parent.parent / "NCL" / "events.ndjson"


def ingest_events(limit: int = 100) -> list[dict]:
    """Read recent NCL events for BRS processing."""
    if not NCL_EVENTS_FILE.exists():
        _log.warning("NCL events file not found: %s", NCL_EVENTS_FILE)
        return []
    events = []
    for line in NCL_EVENTS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events[-limit:]


def health() -> dict:
    return {"adapter": "ncl", "events_file": NCL_EVENTS_FILE.exists()}
