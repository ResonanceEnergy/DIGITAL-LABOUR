#!/usr/bin/env python3
"""
Autonomous Brain -- Self-Directing Intelligence Core
=====================================================
Reads mandates and goals, assesses system state,
identifies gaps, prioritizes actions, executes them,
validates results, and learns from outcomes.

Think Cycle (every 15 min):
  1. ASSESS  -- read system state, metrics, health
  2. ANALYZE -- find gaps (mandates vs reality)
  3. DECIDE  -- prioritize gap-closing actions
  4. ACT     -- execute top-priority actions
  5. CHECK   -- validate action results
  6. LEARN   -- update priorities from outcomes

Usage::

    python tools/autonomous_brain.py          # one cycle
    python tools/autonomous_brain.py daemon    # 24/7 loop
    python tools/autonomous_brain.py status    # show state
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import threading
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "agents"))

from agents.common import (  # noqa: E402
    Log, ensure_dir, now_iso,
)

# ── Paths ──────────────────────────────────────────────────

BRAIN_STATE = ROOT / "config" / "brain_state.json"
MANDATES = ROOT / "agent_mandates.json"
LOG_DIR = ROOT / "logs" / "brain"
ensure_dir(ROOT / "config")
ensure_dir(LOG_DIR)

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
            topic, payload or {},
            source="autonomous_brain",
        )


# ── Action Registry ───────────────────────────────────────
# Maps gap-recommended actions to executable scripts.
# cooldown_minutes prevents spamming the same action.

ACTION_REGISTRY: dict[str, dict[str, Any]] = {
    "run_research": {
        "script": "tools/parallel_research.py",
        "args": [],
        "description": (
            "Parallel research across all projects"
        ),
        "cooldown_minutes": 30,
    },
    "run_ideas": {
        "script": "tools/idea_engine.py",
        "args": ["all"],
        "description": (
            "Cross-pollination and idea generation"
        ),
        "cooldown_minutes": 60,
    },
    "run_metrics": {
        "script": "tools/research_metrics.py",
        "args": ["dashboard"],
        "description": "Metrics dashboard refresh",
        "cooldown_minutes": 15,
    },
    "run_validation": {
        "script": "tools/self_check_validator.py",
        "args": [],
        "description": "System integrity validation",
        "cooldown_minutes": 30,
    },
    "run_gap_analysis": {
        "script": "tools/gap_analyzer.py",
        "args": [],
        "description": "Deep gap analysis",
        "cooldown_minutes": 60,
    },
    "run_integrations": {
        "script": "tools/system_integrations.py",
        "args": ["sync"],
        "description": (
            "NCC/NCL/AAC subsystem sync"
        ),
        "cooldown_minutes": 120,
    },
    "run_sentry": {
        "script": (
            "departments/operations_command/"
            "system_monitoring/repo_sentry.py"
        ),
        "args": [],
        "description": "Repository health scan",
        "cooldown_minutes": 60,
    },
    "run_brief": {
        "script": (
            "departments/operations_command/"
            "system_monitoring/daily_brief.py"
        ),
        "args": [],
        "description": "Daily operational brief",
        "cooldown_minutes": 240,
    },
    "run_selfheal": {
        "script": "agents/portfolio_selfheal.py",
        "args": [],
        "description": "Portfolio self-healing",
        "cooldown_minutes": 60,
    },
    "run_portfolio_sync": {
        "script": "tools/portfolio_sync.py",
        "args": ["sync"],
        "description": "Portfolio sync from GitHub",
        "cooldown_minutes": 120,
    },
    "run_intel_products": {
        "script": "tools/intelligence_products.py",
        "args": [],
        "description": (
            "Intelligence product generation"
        ),
        "cooldown_minutes": 240,
    },
}

# ── Think interval (modifiable for tests) ─────────────────

THINK_INTERVAL_S = 900  # 15 minutes
MAX_ACTIONS_PER_CYCLE = 3
MAX_HISTORY = 200


# ── State Management ──────────────────────────────────────

def _load_state() -> dict[str, Any]:
    """Load brain state from disk."""
    if BRAIN_STATE.exists():
        try:
            return cast(
                dict,
                json.loads(
                    BRAIN_STATE.read_text(
                        encoding="utf-8",
                    ),
                ),
            )
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "cycle_count": 0,
        "last_cycle": None,
        "action_history": [],
        "gap_trends": {},
        "last_actions": {},
        "learnings": [],
    }


def _save_state(state: dict[str, Any]):
    """Persist brain state to disk."""
    ensure_dir(BRAIN_STATE.parent)
    BRAIN_STATE.write_text(
        json.dumps(state, indent=2, default=str),
        encoding="utf-8",
    )


# ── AutonomousBrain ────────────────────────────────────────

class AutonomousBrain:
    """Self-directing intelligence core."""

    def __init__(self):
        self.state = _load_state()
        self.mandates = {}
        self._load_mandates()

    def _load_mandates(self):
        """Load mandates and goals."""
        if MANDATES.exists():
            try:
                self.mandates = json.loads(
                    MANDATES.read_text(encoding="utf-8"),
                )
            except (json.JSONDecodeError, OSError):
                self.mandates = {}

    # ── Think Cycle ────────────────────────────────────────

    def think(self) -> dict[str, Any]:
        """
        One autonomous think cycle:
        ASSESS -> ANALYZE -> DECIDE -> ACT ->
        CHECK -> LEARN
        """
        cycle_start = time.time()
        _emit("brain.cycle.start", {
            "cycle": self.state["cycle_count"] + 1,
        })

        Log.info(
            "=== Autonomous Brain: Think Cycle "
            f"#{self.state['cycle_count'] + 1} ==="
        )

        # 1. ASSESS
        Log.info("[1/6] ASSESS: reading system state")
        validation = self._assess()

        # 2. ANALYZE
        Log.info("[2/6] ANALYZE: finding gaps")
        gaps = self._analyze()

        # 3. DECIDE
        Log.info("[3/6] DECIDE: prioritizing actions")
        actions = self._decide(gaps)

        # 4. ACT
        Log.info("[4/6] ACT: executing actions")
        results = self._act(actions)

        # 5. CHECK
        Log.info("[5/6] CHECK: validating results")
        valid = self._check(results)

        # 6. LEARN
        Log.info("[6/6] LEARN: updating from outcomes")
        self._learn(gaps, results, valid)

        elapsed = time.time() - cycle_start
        cycle_result = {
            "cycle": self.state["cycle_count"],
            "elapsed_s": round(elapsed, 2),
            "gaps_found": gaps.get(
                "summary", {},
            ).get("total_gaps", 0),
            "actions_taken": len(results),
            "actions_succeeded": sum(
                1 for r in results
                if r.get("success")
            ),
            "integrity_score": validation.get(
                "integrity_score", 0,
            ),
        }

        _emit("brain.cycle.done", cycle_result)
        Log.info(
            f"Think cycle complete in "
            f"{elapsed:.1f}s: "
            f"{cycle_result['gaps_found']} gaps, "
            f"{cycle_result['actions_taken']} actions"
        )

        return cycle_result

    # ── ASSESS ─────────────────────────────────────────────

    def _assess(self) -> dict[str, Any]:
        """Run system validation to read state."""
        try:
            from self_check_validator import (
                SystemValidator,
            )
            validator = SystemValidator()
            return validator.validate_all()
        except Exception as exc:
            Log.warn(
                f"Validation failed: {exc}"
            )
            return {"integrity_score": 0, "issues": []}

    # ── ANALYZE ────────────────────────────────────────────

    def _analyze(self) -> dict[str, Any]:
        """Run gap analysis."""
        try:
            from gap_analyzer import GapAnalyzer
            analyzer = GapAnalyzer()
            return analyzer.analyze()
        except Exception as exc:
            Log.warn(
                f"Gap analysis failed: {exc}"
            )
            return {"summary": {"total_gaps": 0}}

    # ── DECIDE ─────────────────────────────────────────────

    def _decide(
        self,
        gaps: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Pick the best actions to close gaps.
        Respects action cooldowns and priorities.
        """
        top_actions = gaps.get(
            "summary", {},
        ).get("top_actions", [])

        selected: list[dict[str, Any]] = []
        now_ts = time.time()

        for entry in top_actions:
            action_id = entry.get("action", "")
            if action_id not in ACTION_REGISTRY:
                continue

            reg = ACTION_REGISTRY[action_id]
            cooldown = reg.get(
                "cooldown_minutes", 60,
            )

            # Check cooldown (stored as epoch float)
            last_run = self.state.get(
                "last_actions", {},
            ).get(action_id)
            if last_run is not None:
                try:
                    elapsed_min = (
                        now_ts - float(last_run)
                    ) / 60
                    if elapsed_min < cooldown:
                        Log.info(
                            f"  {action_id}: cooldown "
                            f"({elapsed_min:.0f}/"
                            f"{cooldown}min)"
                        )
                        continue
                except (ValueError, TypeError):
                    pass

            selected.append({
                "action_id": action_id,
                "priority": entry.get(
                    "priority_score", 0,
                ),
                "description": reg.get(
                    "description", "",
                ),
            })

            if len(selected) >= MAX_ACTIONS_PER_CYCLE:
                break

        if not selected:
            Log.info("  No actions needed (all clear)")

        for s in selected:
            Log.info(
                f"  -> {s['action_id']} "
                f"(priority: {s['priority']})"
            )

        return selected

    # ── ACT ────────────────────────────────────────────────

    def _act(
        self,
        actions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Execute selected actions via subprocess."""
        results: list[dict[str, Any]] = []

        for action in actions:
            aid = action["action_id"]
            reg = ACTION_REGISTRY[aid]
            script = ROOT / reg["script"]
            args = reg.get("args", [])

            if not script.exists():
                Log.warn(
                    f"  {aid}: script not found "
                    f"({reg['script']})"
                )
                results.append({
                    "action_id": aid,
                    "success": False,
                    "error": "script_not_found",
                })
                continue

            Log.info(
                f"  Running {aid}: "
                f"{reg['description']}"
            )
            _emit("brain.action.start", {
                "action": aid,
            })

            try:
                cmd = [
                    sys.executable, str(script),
                ] + args
                cp = subprocess.run(
                    cmd,
                    cwd=str(ROOT),
                    capture_output=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=300,
                )
                success = cp.returncode == 0

                if success:
                    Log.info(f"  {aid}: OK")
                else:
                    # Log last few lines of stderr
                    err_tail = (
                        cp.stderr.strip()
                        .splitlines()[-3:]
                    )
                    Log.warn(
                        f"  {aid}: exit code "
                        f"{cp.returncode}"
                    )
                    for ln in err_tail:
                        Log.warn(
                            f"    {ln[:75]}"
                        )

                results.append({
                    "action_id": aid,
                    "success": success,
                    "returncode": cp.returncode,
                })
                _emit("brain.action.done", {
                    "action": aid,
                    "success": success,
                })
            except subprocess.TimeoutExpired:
                Log.warn(
                    f"  {aid}: timed out (300s)"
                )
                results.append({
                    "action_id": aid,
                    "success": False,
                    "error": "timeout",
                })
            except Exception as exc:
                Log.error(
                    f"  {aid}: {exc}"
                )
                results.append({
                    "action_id": aid,
                    "success": False,
                    "error": str(exc),
                })

            # Record execution time (epoch float)
            self.state.setdefault(
                "last_actions", {},
            )[aid] = time.time()

        return results

    # ── CHECK ──────────────────────────────────────────────

    def _check(
        self,
        results: list[dict[str, Any]],
    ) -> bool:
        """Validate action results."""
        if not results:
            return True

        succeeded = sum(
            1 for r in results if r.get("success")
        )
        total = len(results)
        rate = succeeded / total if total else 1.0

        if rate < 0.5:
            Log.warn(
                f"  Low success rate: "
                f"{succeeded}/{total} "
                f"({rate:.0%})"
            )
            return False

        Log.info(
            f"  Success rate: {succeeded}/{total} "
            f"({rate:.0%})"
        )
        return True

    # ── LEARN ──────────────────────────────────────────────

    def _learn(
        self,
        gaps: dict[str, Any],
        results: list[dict[str, Any]],
        valid: bool,
    ):
        """Update state from cycle outcomes."""
        self.state["cycle_count"] += 1
        self.state["last_cycle"] = now_iso()

        # Track gap trends
        all_gaps: list[dict] = []
        for cat in (
            "mandate_gaps", "research_gaps",
            "pipeline_gaps", "knowledge_gaps",
            "integration_gaps",
        ):
            all_gaps.extend(gaps.get(cat, []))

        trends = self.state.setdefault(
            "gap_trends", {},
        )
        for gap in all_gaps:
            gid = gap.get("id", "unknown")
            if gid not in trends:
                trends[gid] = {
                    "first_seen": now_iso(),
                    "times_seen": 0,
                    "severity": gap.get(
                        "severity", "LOW",
                    ),
                }
            trends[gid]["times_seen"] += 1
            trends[gid]["last_seen"] = now_iso()

        # Record action outcomes
        history = self.state.setdefault(
            "action_history", [],
        )
        for r in results:
            history.append({
                "action": r.get("action_id", "?"),
                "success": r.get("success", False),
                "timestamp": now_iso(),
            })

        # Trim history
        if len(history) > MAX_HISTORY:
            self.state["action_history"] = (
                history[-MAX_HISTORY:]
            )

        # Purge old gap trends (not seen in 50 cycles)
        cycle = self.state["cycle_count"]
        stale_ids = []
        for gid, info in trends.items():
            if (
                info["times_seen"] == 1
                and cycle > 50
            ):
                stale_ids.append(gid)
        for gid in stale_ids:
            del trends[gid]

        # Save
        _save_state(self.state)

        # Write cycle log
        cycle_log = LOG_DIR / (
            f"cycle_{self.state['cycle_count']:04d}"
            ".json"
        )
        cycle_log.write_text(
            json.dumps({
                "cycle": self.state["cycle_count"],
                "timestamp": now_iso(),
                "gap_count": len(all_gaps),
                "actions": results,
                "valid": valid,
            }, indent=2, default=str),
            encoding="utf-8",
        )

    # ── Daemon ─────────────────────────────────────────────

    def daemon(self):
        """Run think cycles continuously."""
        Log.info(
            "Autonomous Brain daemon starting "
            f"(interval: {THINK_INTERVAL_S}s)"
        )
        while True:
            try:
                self.think()
            except Exception as exc:
                Log.error(
                    f"Think cycle error: {exc}"
                )
                _emit("brain.cycle.error", {
                    "error": str(exc),
                })
            time.sleep(THINK_INTERVAL_S)

    # ── Status ─────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        """Return current brain status."""
        history = self.state.get(
            "action_history", [],
        )
        recent = history[-10:]
        success_rate = (
            sum(1 for h in recent if h.get("success"))
            / len(recent) if recent else 0
        )

        trends = self.state.get("gap_trends", {})
        persistent = {
            gid: info
            for gid, info in trends.items()
            if info.get("times_seen", 0) >= 3
        }

        return {
            "cycle_count": self.state.get(
                "cycle_count", 0,
            ),
            "last_cycle": self.state.get(
                "last_cycle",
            ),
            "recent_success_rate": round(
                success_rate, 2,
            ),
            "persistent_gaps": len(persistent),
            "total_actions_taken": len(history),
            "top_persistent_gaps": sorted(
                persistent.items(),
                key=lambda x: x[1].get(
                    "times_seen", 0,
                ),
                reverse=True,
            )[:5],
        }


# ── Daemon Thread Entry Point ─────────────────────────────

def start_daemon_thread(
    interval_s: int = 300,
):
    """Start the brain as a daemon thread.

    Called from ``run_super_agency.py`` during boot.
    """
    global THINK_INTERVAL_S
    THINK_INTERVAL_S = interval_s

    brain = AutonomousBrain()
    t = threading.Thread(
        target=brain.daemon,
        daemon=True,
        name="AutonomousBrain",
    )
    t.start()
    return t


# ── CLI ────────────────────────────────────────────────────

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "cycle"
    brain = AutonomousBrain()

    if cmd == "daemon":
        brain.daemon()
    elif cmd == "status":
        st = brain.status()
        Log.info("=== Autonomous Brain Status ===")
        Log.info(
            f"Cycles: {st['cycle_count']}"
        )
        Log.info(
            f"Last cycle: {st['last_cycle']}"
        )
        Log.info(
            f"Recent success: "
            f"{st['recent_success_rate']:.0%}"
        )
        Log.info(
            f"Persistent gaps: "
            f"{st['persistent_gaps']}"
        )
        if st["top_persistent_gaps"]:
            Log.info("Top persistent gaps:")
            for gid, info in (
                st["top_persistent_gaps"]
            ):
                Log.info(
                    f"  {gid}: seen "
                    f"{info['times_seen']}x "
                    f"({info['severity']})"
                )
    else:
        brain.think()


if __name__ == "__main__":
    main()
