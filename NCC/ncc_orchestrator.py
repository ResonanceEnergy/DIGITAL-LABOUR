"""NCC Orchestrator — BRS command chain entry point.

Bridges NCC governance to BitRageSystems execution layer.
Dispatches directives from NCC → BRS agent fleet via adapters.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

_log = logging.getLogger("brs.orchestrator")

NCC_ROOT = Path(__file__).resolve().parent
ADAPTERS_DIR = NCC_ROOT / "adapters"


def dispatch(directive: dict) -> dict:
    """Dispatch a governance directive to the BRS fleet."""
    _log.info("Orchestrator received directive: %s", directive.get("type", "unknown"))
    return {"status": "received", "directive": directive.get("type")}


def health() -> dict:
    """Return orchestrator health status."""
    adapters = list(ADAPTERS_DIR.glob("*_adapter.py"))
    return {
        "orchestrator": "online",
        "adapters_loaded": len(adapters),
        "adapter_names": [a.stem for a in adapters],
    }


if __name__ == "__main__":
    print(json.dumps(health(), indent=2))
