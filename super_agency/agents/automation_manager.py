#!/usr/bin/env python3
"""
Automation Manager Agent — Bit Rage Systems
=============================================
T2 Management agent responsible for pipeline
orchestration, scheduled task management, cron
coordination, and workflow automation across
the entire agent fleet.

Authority:
- Controls all scheduled/automated workflows
- Can start, stop, and reschedule daemon tasks
- Manages pipeline execution order and dependencies
- Owns the automation.* bus namespace

Reports to: CIO (T1)
Manages: research_scheduler (T2), orchestrator (T2)
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
AUTO_DIR = ROOT / "data" / "automation_manager"
AUTO_DIR.mkdir(parents=True, exist_ok=True)

# ── Message bus (best-effort) ──────────────────
_bus: Any = None
try:
    from agents.message_bus import bus
    _bus = bus
except Exception:
    pass


def _emit(
    topic: str,
    payload: Optional[dict[str, Any]] = None,
) -> None:
    if _bus:
        _bus.publish(  # type: ignore[union-attr]
            topic,
            payload or {},
            source="automation_manager",
        )


class AutomationManagerAgent:
    """Manages pipelines, schedules, and workflow
    automation for the agent fleet."""

    def __init__(self) -> None:
        self._cycle = 0
        self._workflows: dict[str, dict[str, Any]] = {}
        self._execution_log: list[dict[str, Any]] = []
        self._load_state()

    # ── Persistence ────────────────────────────
    def _state_path(self) -> Path:
        return AUTO_DIR / "automation_state.json"

    def _load_state(self) -> None:
        p = self._state_path()
        if p.exists():
            try:
                data = json.loads(
                    p.read_text(encoding="utf-8"),
                )
                self._cycle = data.get("cycle", 0)
                self._workflows = data.get(
                    "workflows", {},
                )
                self._execution_log = data.get(
                    "execution_log", [],
                )[-100:]
            except (json.JSONDecodeError, OSError):
                pass

    def _save_state(self) -> None:
        self._state_path().write_text(
            json.dumps(
                {
                    "cycle": self._cycle,
                    "workflows": self._workflows,
                    "execution_log": (
                        self._execution_log[-100:]
                    ),
                    "saved_at": datetime.now().isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    # ── Workflow Management ────────────────────
    def register_workflow(
        self,
        name: str,
        interval_s: int,
        agent: str,
        enabled: bool = True,
    ) -> None:
        """Register a recurring workflow."""
        self._workflows[name] = {
            "agent": agent,
            "interval_s": interval_s,
            "enabled": enabled,
            "last_run": None,
            "run_count": 0,
            "registered_at": (
                datetime.now().isoformat()
            ),
        }

    def _scan_daemon_configs(self) -> dict[str, Any]:
        """Discover daemon configurations in the
        codebase."""
        daemons: dict[str, Any] = {}

        # Check research scheduler
        sched_path = (
            ROOT / "tools" / "research_scheduler.py"
        )
        if sched_path.exists():
            daemons["research_scheduler"] = {
                "path": str(sched_path.name),
                "exists": True,
            }

        # Check autonomous brain
        brain_path = (
            ROOT / "tools" / "autonomous_brain.py"
        )
        if brain_path.exists():
            daemons["autonomous_brain"] = {
                "path": str(brain_path.name),
                "exists": True,
            }

        # Check orchestrator
        orch_path = ROOT / "agents" / "orchestrator.py"
        if orch_path.exists():
            daemons["orchestrator"] = {
                "path": str(orch_path.name),
                "exists": True,
            }

        return {
            "daemons_found": len(daemons),
            "daemons": daemons,
        }

    def _check_pipeline_stages(self) -> dict[str, Any]:
        """Check orchestrator pipeline stage status."""
        events_log = ROOT / "logs" / "events.ndjson"
        stages: dict[str, int] = {}

        if events_log.exists():
            try:
                with open(
                    events_log, "r",
                    encoding="utf-8",
                ) as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            ev = json.loads(line)
                            topic = ev.get("topic", "")
                            if "stage." in topic:
                                stage = topic.split(
                                    ".",
                                )[-1]
                                stages[stage] = (
                                    stages.get(stage, 0)
                                    + 1
                                )
                        except json.JSONDecodeError:
                            continue
            except OSError:
                pass

        return {
            "stages": stages,
            "total_events": sum(stages.values()),
        }

    def _check_workflow_health(self) -> dict[str, Any]:
        """Check health of registered workflows."""
        healthy = 0
        stale = 0
        disabled = 0
        now = time.time()

        for _name, wf in self._workflows.items():
            if not wf.get("enabled"):
                disabled += 1
                continue

            last_run = wf.get("last_run")
            if not last_run:
                stale += 1
                continue

            try:
                last_ts = datetime.fromisoformat(
                    last_run,
                ).timestamp()
                age = now - last_ts
                interval = wf.get("interval_s", 3600)
                if age > interval * 3:
                    stale += 1
                else:
                    healthy += 1
            except (ValueError, TypeError):
                stale += 1

        total = len(self._workflows)
        return {
            "total": total,
            "healthy": healthy,
            "stale": stale,
            "disabled": disabled,
        }

    # ── Main Cycle ─────────────────────────────
    def run_cycle(self) -> dict[str, Any]:
        """Run a full automation management cycle."""
        self._cycle += 1
        t0 = time.monotonic()

        daemons = self._scan_daemon_configs()
        pipeline = self._check_pipeline_stages()
        workflow_health = self._check_workflow_health()

        elapsed = round(time.monotonic() - t0, 3)

        report = {
            "cycle": self._cycle,
            "timestamp": datetime.now().isoformat(),
            "daemons": daemons,
            "pipeline": pipeline,
            "workflow_health": workflow_health,
            "registered_workflows": len(
                self._workflows
            ),
            "elapsed_s": elapsed,
        }

        self._execution_log.append({
            "cycle": self._cycle,
            "ts": datetime.now().isoformat(),
            "daemons": daemons["daemons_found"],
            "pipeline_events": pipeline["total_events"],
        })

        self._save_state()

        _emit("automation.cycle.complete", {
            "cycle": self._cycle,
            "daemons": daemons["daemons_found"],
            "workflows": len(self._workflows),
        })

        if workflow_health["stale"] > 0:
            _emit("automation.workflows.stale", {
                "stale": workflow_health["stale"],
            })
            logger.warning(
                "[AUTO_MGR] %d stale workflows",
                workflow_health["stale"],
            )

        logger.info(
            "[AUTO_MGR] Cycle %d — %d daemons, "
            "%d workflows (%.3fs)",
            self._cycle,
            daemons["daemons_found"],
            len(self._workflows),
            elapsed,
        )

        return report
