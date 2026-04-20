"""DEPRECATED — Moved to dispatcher/command_dispatcher.py.

This file is a backward-compatibility shim. All new code should import from:
    from dispatcher.command_dispatcher import dispatch, health, pending_decisions

See RESONANCE_ENERGY_SOT.md — NCC code does not belong in the Bit Rage repo.
This file will be removed in a future cleanup.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Re-export everything from the new canonical location
from dispatcher.command_dispatcher import (  # noqa: F401
    dispatch,
    health,
    pending_decisions,
)

if __name__ == "__main__":
    import json
    print(json.dumps(health(), indent=2))
