"""Output Awareness — Intelligence layer for the output store.

Provides query functions that NCL Operations Commander and Internal Ops
use to check what has already been produced before dispatching new work.
This closes the feedback loop: outputs are no longer write-only.

Usage:
    from utils.output_awareness import (
        get_division_summary,
        has_recent_output,
        get_output_gaps,
        get_intelligence_brief,
    )
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger("output_awareness")


# ── Core Queries ──────────────────────────────────────────────────


def get_division_summary(division: Optional[str] = None) -> dict:
    """Get a summary of completed outputs for a division (or all).

    Returns counts by task_type, most recent output date, and total.
    NCL uses this to see which divisions are productive vs. stale.
    """
    try:
        from utils.output_store import list_outputs, get_stats
        stats = get_stats()

        if division:
            outputs = list_outputs(division=division, limit=200)
            by_type = {}
            latest_ts = None
            for o in outputs:
                tt = o.get("task_type", "unknown")
                by_type[tt] = by_type.get(tt, 0) + 1
                ts = o.get("created_at")
                if ts and (latest_ts is None or ts > latest_ts):
                    latest_ts = ts
            return {
                "division": division,
                "total_outputs": len(outputs),
                "by_task_type": by_type,
                "latest_output": latest_ts,
                "store_total": stats.get("total", 0),
            }
        else:
            return stats
    except Exception as e:
        logger.warning("output_awareness.get_division_summary failed: %s", e)
        return {"error": str(e), "total_outputs": 0}


def has_recent_output(task_type: str, division: str = "",
                      hours: int = 24) -> bool:
    """Check if a task_type has been completed recently.

    Internal ops uses this to avoid dispatching duplicate work.
    Returns True if a matching output exists within the time window.
    """
    try:
        from utils.output_store import list_outputs
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        outputs = list_outputs(
            task_type=task_type,
            division=division or None,
            limit=5,
        )
        for o in outputs:
            created = o.get("created_at", "")
            if created >= cutoff:
                return True
        return False
    except Exception as e:
        logger.warning("output_awareness.has_recent_output failed: %s", e)
        return False  # Fail open — allow dispatch if store is unreachable


def get_output_gaps(divisions: dict) -> dict:
    """Identify which divisions/task_types have NO completed outputs.

    NCL uses this to prioritize dispatching work to underserved areas.

    Args:
        divisions: The DIVISIONS dict from ncl_operations_commander.

    Returns:
        Dict mapping division_id -> list of task_types with zero outputs.
    """
    gaps = {}
    try:
        from utils.output_store import list_outputs

        for div_id, div_info in divisions.items():
            div_code = div_info.get("code", div_id)
            div_outputs = list_outputs(division=div_code, limit=200)

            # Build set of task_types that have outputs
            produced_types = set()
            for o in div_outputs:
                produced_types.add(o.get("task_type", ""))

            # Find agent types that have ZERO outputs
            missing = []
            for agent in div_info.get("agents", []):
                if agent not in produced_types:
                    missing.append(agent)

            if missing:
                gaps[div_id] = {
                    "code": div_code,
                    "total_outputs": len(div_outputs),
                    "missing_agent_outputs": missing,
                }
    except Exception as e:
        logger.warning("output_awareness.get_output_gaps failed: %s", e)

    return gaps


def get_intelligence_brief() -> dict:
    """Compile a brief for NCL's daily ops push.

    Returns a snapshot of output store state that NCL injects into
    its decision-making context:
    - Total outputs stored
    - Per-division counts
    - Recent completions (last 6 hours)
    - Identified gaps
    """
    try:
        from utils.output_store import get_stats, get_latest

        stats = get_stats()
        recent = get_latest(limit=10)

        # Count recent (last 6 hours)
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
        recent_count = sum(
            1 for o in recent
            if o.get("created_at", "") >= cutoff
        )

        brief = {
            "total_outputs": stats.get("total", 0),
            "by_division": stats.get("by_division", {}),
            "by_category": stats.get("by_category", {}),
            "recent_6h": recent_count,
            "latest_outputs": [
                {
                    "task_type": o.get("task_type"),
                    "division": o.get("division"),
                    "title": o.get("title", ""),
                    "created_at": o.get("created_at"),
                }
                for o in recent[:5]
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return brief
    except Exception as e:
        logger.warning("output_awareness.get_intelligence_brief failed: %s", e)
        return {"error": str(e), "total_outputs": 0}


def should_dispatch(task_type: str, division: str = "",
                    cooldown_hours: int = 20) -> tuple[bool, str]:
    """Decision helper: should we dispatch this task_type now?

    Returns (should_dispatch: bool, reason: str).
    Checks:
    1. Has a recent output been produced? (cooldown)
    2. Is there any output at all for this type? (priority boost)

    This is the primary dedup gate for internal ops.
    """
    try:
        from utils.output_store import list_outputs

        all_outputs = list_outputs(task_type=task_type,
                                   division=division or None, limit=5)

        if not all_outputs:
            return True, f"no_prior_output:{task_type}"

        # Check cooldown
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=cooldown_hours)).isoformat()
        recent = [o for o in all_outputs if o.get("created_at", "") >= cutoff]

        if recent:
            return False, f"recent_output_exists:{task_type}:{recent[0].get('created_at', '')}"

        return True, f"cooldown_expired:{task_type}"
    except Exception as e:
        logger.warning("output_awareness.should_dispatch failed: %s", e)
        return True, f"store_error_fail_open:{e}"
