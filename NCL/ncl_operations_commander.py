"""DEPRECATED — Moved to dispatcher/ops_commander.py.

This file is a backward-compatibility shim. All new code should import from:
    from dispatcher.ops_commander import DIVISIONS, daily_ops_push, etc.

See RESONANCE_ENERGY_SOT.md — NCL code does not belong in the Bit Rage repo.
This file will be removed in a future cleanup.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Re-export everything from the new canonical location
from dispatcher.ops_commander import (  # noqa: F401
    DIVISIONS,
    SERVICE_TO_TASKTYPE,
    ESCALATION_THRESHOLDS,
    check_division_health,
    push_csuite_cadence,
    generate_weekly_goals,
    daily_ops_push,
    ops_status,
    run_daemon,
    main,
)

if __name__ == "__main__":
    main()
