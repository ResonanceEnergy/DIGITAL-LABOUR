#!/usr/bin/env python3
"""
Research Scheduler — 24/7 Autonomous Intelligence Cycle
========================================================
Implements a persistent scheduler that drives the full
intelligence cycle on configurable intervals:

  - FAST cycle (every 30 min): metrics snapshot, system health
  - STANDARD cycle (every 4 hours): parallel research, idea gen
  - DEEP cycle (every 24 hours): full intel report, trend analysis
  - WEEKLY cycle: cross-pollination deep-dive, watchlist refresh

The scheduler runs as a daemon thread inside run_super_agency.py
or standalone for testing.

Usage::

    python tools/research_scheduler.py              # run once
    python tools/research_scheduler.py daemon        # 24/7 loop
    python tools/research_scheduler.py status        # show state
"""

from __future__ import annotations

import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
import sys
from typing import Any, cast

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "agents"))

from agents.common import (  # noqa: E402
    Log, ensure_dir, now_iso,
)

SCHEDULER_STATE = ROOT / "config" / "scheduler_state.json"
ensure_dir(ROOT / "config")

# Message bus (best-effort)
_bus: Any = None
try:
    from agents.message_bus import bus
    _bus = bus
except Exception:
    pass


def _emit(topic: str, payload: Any = None):
    if _bus:
        _bus.publish(  # type: ignore[union-attr]
            topic, payload or {}, source="research_scheduler",
        )


# ── Cycle Definitions ──────────────────────────────────────

CYCLES = {
    "fast": {
        "interval_minutes": 30,
        "description": "Quick health snapshot",
        "stages": ["metrics_snapshot"],
    },
    "standard": {
        "interval_minutes": 240,  # 4 hours
        "description": "Research cycle + idea generation",
        "stages": [
            "parallel_research",
            "intelligence_products",
            "idea_generation",
            "metrics_dashboard",
        ],
    },
    "deep": {
        "interval_minutes": 1440,  # 24 hours
        "description": "Full intelligence report with trends",
        "stages": [
            "parallel_research",
            "intelligence_products",
            "idea_generation",
            "metrics_dashboard",
        ],
    },
    "weekly": {
        "interval_minutes": 10080,  # 7 days
        "description": "Deep cross-pollination analysis",
        "stages": [
            "parallel_research",
            "intelligence_products",
            "idea_generation",
            "metrics_dashboard",
        ],
    },
}


# ── State Management ───────────────────────────────────────

def _load_state() -> dict[str, Any]:
    if SCHEDULER_STATE.exists():
        try:
            return cast(
                dict,
                json.loads(
                    SCHEDULER_STATE.read_text(
                        encoding="utf-8",
                    )
                ),
            )
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "last_run": {},
        "run_count": {},
        "errors": [],
    }


def _save_state(state: dict):
    SCHEDULER_STATE.write_text(
        json.dumps(state, indent=2, default=str),
        encoding="utf-8",
    )


def _is_cycle_due(
    cycle_name: str, state: dict,
) -> bool:
    """Check if a cycle is due to run."""
    cycle = CYCLES[cycle_name]
    interval = timedelta(
        minutes=float(cycle["interval_minutes"]),
    )
    last_run_str = state.get("last_run", {}).get(
        cycle_name
    )

    if not last_run_str:
        return True

    try:
        last_run = datetime.fromisoformat(last_run_str)
        return datetime.now().astimezone() - last_run >= interval
    except (ValueError, TypeError):
        return True


# ── Stage Executors ────────────────────────────────────────

def _run_metrics_snapshot():
    """Run quick metrics snapshot."""
    from research_metrics import generate_dashboard
    return generate_dashboard()


def _run_parallel_research():
    """Execute parallel research across all projects."""
    from parallel_research import run_parallel_research
    return run_parallel_research(
        max_project_workers=4,
        max_repo_workers=4,
    )


def _run_intelligence_products():
    """Generate intelligence products (trends, correlations)."""
    from intelligence_products import generate_full_report
    return generate_full_report()


def _run_idea_generation():
    """Generate ideas, hypotheses, and research questions."""
    from idea_engine import generate_ideas
    return generate_ideas()


def _run_metrics_dashboard():
    """Generate full metrics dashboard."""
    from research_metrics import generate_dashboard
    d = generate_dashboard()
    from research_metrics import render_dashboard_md
    md = render_dashboard_md(d)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    md_path = (
        ROOT / "reports" / "metrics"
        / f"dashboard_{stamp}.md"
    )
    md_path.write_text(md, encoding="utf-8")
    return d


STAGE_RUNNERS = {
    "metrics_snapshot": _run_metrics_snapshot,
    "parallel_research": _run_parallel_research,
    "intelligence_products": _run_intelligence_products,
    "idea_generation": _run_idea_generation,
    "metrics_dashboard": _run_metrics_dashboard,
}


# ── Cycle Executor ─────────────────────────────────────────

def run_cycle(cycle_name: str) -> dict[str, Any]:
    """Execute all stages of a named cycle."""
    cycle = CYCLES[cycle_name]
    state = _load_state()

    Log.info(
        f"[Scheduler] Running {cycle_name} cycle: "
        f"{cycle['description']}"
    )
    _emit("scheduler.cycle.start", {
        "cycle": cycle_name,
    })

    results: dict[str, Any] = {}
    errors: list[str] = []

    for stage_name in list(cycle["stages"]):
        runner = STAGE_RUNNERS.get(stage_name)
        if not runner:
            Log.warn(
                f"[Scheduler] Unknown stage: {stage_name}"
            )
            continue

        try:
            Log.info(f"[Scheduler]   → {stage_name}")
            runner()
            results[stage_name] = "ok"
        except Exception as exc:
            msg = f"{stage_name}: {exc}"
            Log.error(f"[Scheduler]   ✗ {msg}")
            errors.append(msg)
            results[stage_name] = f"error: {exc}"

    # Update state
    state.setdefault("last_run", {})[cycle_name] = (
        now_iso()
    )
    state.setdefault("run_count", {})[cycle_name] = (
        state.get("run_count", {}).get(cycle_name, 0) + 1
    )
    if errors:
        state.setdefault("errors", []).extend(errors)
        # Keep last 50 errors
        state["errors"] = state["errors"][-50:]
    _save_state(state)

    status = "ok" if not errors else "partial"
    _emit("scheduler.cycle.done", {
        "cycle": cycle_name,
        "status": status,
        "stages": list(results.keys()),
        "errors": errors,
    })

    Log.info(
        f"[Scheduler] {cycle_name} cycle {status} — "
        f"{len(results)} stages, {len(errors)} errors"
    )

    return {
        "cycle": cycle_name,
        "status": status,
        "results": results,
        "errors": errors,
    }


# ── Daemon Loop ────────────────────────────────────────────

def _daemon_tick():
    """Check all cycles and run any that are due."""
    state = _load_state()

    for cycle_name in CYCLES:
        if _is_cycle_due(cycle_name, state):
            try:
                run_cycle(cycle_name)
            except Exception as exc:
                Log.error(
                    f"[Scheduler] {cycle_name} failed: {exc}"
                )
            # Reload state after each cycle
            state = _load_state()


def daemon_loop(check_interval_s: int = 60):
    """Run the scheduler daemon forever.

    Checks every `check_interval_s` seconds whether any
    cycle is due, and runs it if so.
    """
    Log.info(
        "[Scheduler] Daemon started — checking every "
        f"{check_interval_s}s"
    )
    _emit("scheduler.daemon.start", {})

    while True:
        try:
            _daemon_tick()
        except Exception as exc:
            Log.error(f"[Scheduler] Tick error: {exc}")

        time.sleep(check_interval_s)


def start_daemon_thread(
    check_interval_s: int = 60,
) -> threading.Thread:
    """Start daemon loop in a background thread.

    Called by run_super_agency.py to integrate the scheduler
    into the main runtime.
    """
    t = threading.Thread(
        target=daemon_loop,
        args=(check_interval_s,),
        daemon=True,
        name="ResearchScheduler",
    )
    t.start()
    Log.info("[Scheduler] Daemon thread started")
    return t


# ── Run Once ───────────────────────────────────────────────

def run_all_due() -> list[dict]:
    """Run all due cycles once (non-daemon mode)."""
    state = _load_state()
    results = []

    for cycle_name in CYCLES:
        if _is_cycle_due(cycle_name, state):
            result = run_cycle(cycle_name)
            results.append(result)
            state = _load_state()

    if not results:
        Log.info("[Scheduler] No cycles due")

    return results


# ── Status ─────────────────────────────────────────────────

def get_status() -> dict[str, Any]:
    """Get scheduler status overview."""
    state = _load_state()
    now = datetime.now().astimezone()

    cycle_status = {}
    for name, cycle in CYCLES.items():
        last_str = state.get("last_run", {}).get(name)
        count = state.get("run_count", {}).get(name, 0)

        if last_str:
            try:
                last = datetime.fromisoformat(last_str)
                age_min = round(
                    (now - last).total_seconds() / 60
                )
                due = _is_cycle_due(name, state)
            except (ValueError, TypeError):
                age_min = -1
                due = True
        else:
            age_min = -1
            due = True

        cycle_status[name] = {
            "interval_min": cycle["interval_minutes"],
            "last_run": last_str or "never",
            "age_minutes": age_min,
            "is_due": due,
            "run_count": count,
            "description": cycle["description"],
        }

    return {
        "generated_at": now_iso(),
        "cycles": cycle_status,
        "recent_errors": state.get("errors", [])[-5:],
    }


# ── CLI ──────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Research Scheduler — 24/7 Intelligence",
    )
    parser.add_argument(
        "command", nargs="?", default="run",
        choices=["run", "daemon", "status", "force"],
    )
    parser.add_argument(
        "--cycle", default=None,
        help="Force a specific cycle (with 'force')",
    )
    args = parser.parse_args()

    if args.command == "run":
        results = run_all_due()
        for r in results:
            s = r["status"]
            c = r["cycle"]
            print(f"  {c}: {s}")
        if not results:
            print("No cycles due.")
    elif args.command == "daemon":
        daemon_loop()
    elif args.command == "status":
        status = get_status()
        print("Research Scheduler Status")
        print("=" * 40)
        for name, info in status["cycles"].items():
            due = "DUE" if info["is_due"] else "ok"
            lr = info["last_run"]
            last = lr[:19] if lr != "never" else "never"
            print(
                f"  {name:10s} | {due:4s} | "
                f"runs: {info['run_count']:3d} | "
                f"last: {last}"
            )
        errs = status["recent_errors"]
        if errs:
            print(f"\nRecent errors: {len(errs)}")
            for e in errs:
                print(f"  - {e}")
    elif args.command == "force":
        cycle = args.cycle or "standard"
        if cycle not in CYCLES:
            print(f"Unknown cycle: {cycle}")
            sys.exit(1)
        result = run_cycle(cycle)
        print(
            f"{cycle}: {result['status']} "
            f"({len(result['errors'])} errors)"
        )


if __name__ == "__main__":
    main()
