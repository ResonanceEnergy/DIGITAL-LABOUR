#!/usr/bin/env python3
"""
Departmental Operations Orchestrator
Coordinates all system operations: sentry,
brief, research, council, audit, autotier.
Runs scripts from the project root so relative
paths in config resolve correctly.

Also checks for pending Second Brain ingests
and processes them.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
_OPS_CMD = (
    ROOT / "departments" / "operations_command"
    / "system_monitoring"
)
SENTRY = _OPS_CMD / "repo_sentry.py"
DAILY = _OPS_CMD / "daily_brief.py"
RESEARCH = ROOT / "agents" / "research_manager.py"
PARALLEL_RESEARCH = (
    ROOT / "tools" / "parallel_research.py"
)
COUNCIL = ROOT / "agent_council_meeting.py"
AUDIT = ROOT / "auto_system_audit.py"
AUTOTIER = ROOT / "agents" / "portfolio_autotier.py"

# Intelligence scheduler
INTEL_SCHEDULER = ROOT / "intelligence_scheduler.py"

# Research enterprise modules
RESEARCH_METRICS = (
    ROOT / "tools" / "research_metrics.py"
)
IDEA_ENGINE = ROOT / "tools" / "idea_engine.py"

# System integrations (NCC, NCL, AAC, DL)
INTEGRATIONS = (
    ROOT / "tools" / "system_integrations.py"
)

# DIGITAL LABOUR sync bridge
DL_BRIDGE = ROOT / "agents" / "dl_bridge.py"

# Autonomous brain modules
GAP_ANALYZER = ROOT / "tools" / "gap_analyzer.py"
SELF_CHECK = (
    ROOT / "tools" / "self_check_validator.py"
)

# Portfolio sync & self-heal
PORTFOLIO_SYNC = (
    ROOT / "tools" / "portfolio_sync.py"
)
PORTFOLIO_HEAL = (
    ROOT / "agents" / "portfolio_selfheal.py"
)

# Second Brain pending queue
SECONDBRAIN_QUEUE = (
    ROOT / "knowledge" / "secondbrain"
    / "pending.json"
)

# Message bus (best-effort import; works inside
# run_bit_rage_labour, no-op standalone)
_bus: Any = None
try:
    from agents.message_bus import bus
    _bus = bus
except Exception:
    pass

# Circuit breakers (best-effort)
try:
    from agents.resilience import (
        get_breaker,
        _emit_alert,
    )
except Exception:
    get_breaker = None  # type: ignore[assignment]
    _emit_alert = None  # type: ignore[assignment]


def _emit(
    topic: str,
    payload: Optional[dict] = None,
):
    """Publish an event to the message bus."""
    if _bus:
        _bus.publish(  # type: ignore[union-attr]
            topic, payload or {},
            source="orchestrator",
        )


def log(message: str, level: str = "INFO"):
    """Log a timestamped message to stdout."""
    import datetime
    ts = datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S",
    )
    print(f"[{ts}] [{level}] {message}")


def _run_stage(
    label: str, script: Path, cwd: str,
):
    """Run a single orchestrator stage."""
    cb = None
    if get_breaker is not None:
        cb = get_breaker(
            f"stage.{label}",
            threshold=3,
            recovery_timeout=600.0,
        )
        if not cb.allow():
            log(
                f"{label} SKIPPED \u2014 circuit "
                "breaker OPEN",
                "WARN",
            )
            _emit("orchestrator.stage.skip", {
                "stage": label,
                "reason": "circuit_breaker_open",
            })
            return

    log(f"Running {label}\u2026")
    _emit(
        "orchestrator.stage.start",
        {"stage": label},
    )
    cp = subprocess.run(
        [sys.executable, str(script)], cwd=cwd,
    )
    if cp.returncode != 0:
        log(
            f"{label} exited with non-zero code",
            "WARN",
        )
        _emit("orchestrator.stage.fail", {
            "stage": label,
            "code": cp.returncode,
        })
        if cb:
            cb.record_failure()
    else:
        log(
            f"\u2705 {label} completed successfully",
        )
        _emit(
            "orchestrator.stage.done",
            {"stage": label},
        )
        if cb:
            cb.record_success()


def _process_secondbrain_queue():
    """Process any pending Second Brain ingests."""
    if not SECONDBRAIN_QUEUE.exists():
        return
    try:
        pending = json.loads(
            SECONDBRAIN_QUEUE.read_text(
                encoding="utf-8",
            ),
        )
    except (json.JSONDecodeError, OSError):
        return
    if not pending:
        return

    log(
        f"Processing {len(pending)} pending "
        "Second Brain ingests\u2026"
    )
    sys.path.insert(0, str(ROOT / "tools"))
    from secondbrain_pipeline import (  # type: ignore[import-not-found]
        run_full_pipeline,
    )

    completed = []
    for item in pending:
        url = item.get("url", "")
        if not url:
            completed.append(item)
            continue
        log(f"  Ingesting: {url}")
        result = run_full_pipeline(url)
        ok = result.get("stopped_at") is None
        vid = result.get("video_id", "?")
        tag = "\u2705" if ok else "\u26a0\ufe0f"
        log(f"  {tag} {url} \u2192 {vid}")
        completed.append(item)

    remaining = [
        i for i in pending if i not in completed
    ]
    SECONDBRAIN_QUEUE.write_text(
        json.dumps(remaining, indent=2),
        encoding="utf-8",
    )
    log(
        f"Second Brain queue: processed "
        f"{len(completed)}, remaining "
        f"{len(remaining)}"
    )


def _run_stage_with_args(
    label: str, script: Path,
    args: list, cwd: str,
):
    """Run an orchestrator stage with extra args."""
    cb = None
    if get_breaker is not None:
        cb = get_breaker(
            f"stage.{label}",
            threshold=3,
            recovery_timeout=600.0,
        )
        if not cb.allow():
            log(
                f"{label} SKIPPED \u2014 circuit "
                "breaker OPEN",
                "WARN",
            )
            _emit("orchestrator.stage.skip", {
                "stage": label,
                "reason": "circuit_breaker_open",
            })
            return

    log(f"Running {label}\u2026")
    _emit(
        "orchestrator.stage.start",
        {"stage": label},
    )
    cmd = [sys.executable, str(script)] + args
    cp = subprocess.run(cmd, cwd=cwd)
    if cp.returncode != 0:
        log(
            f"{label} exited with non-zero code",
            "WARN",
        )
        _emit("orchestrator.stage.fail", {
            "stage": label,
            "code": cp.returncode,
        })
        if cb:
            cb.record_failure()
    else:
        log(
            f"\u2705 {label} completed successfully",
        )
        _emit("orchestrator.stage.done", {
            "stage": label,
        })
        if cb:
            cb.record_success()


def main():
    """Run the full orchestration pipeline."""
    log(
        "Running DIGITAL LABOUR Orchestrator — "
        "DIGITAL LABOUR Primary\u2026"
    )
    log(
        "Pipeline: DL-Sync \u2192 PortfolioSync "
        "\u2192 SelfHeal \u2192 Sentry \u2192 Brief "
        "\u2192 Research \u2192 ParallelResearch "
        "\u2192 Intel \u2192 SecondBrain "
        "\u2192 IdeaEngine \u2192 Metrics "
        "\u2192 Council \u2192 Audit "
        "\u2192 AutoTier \u2192 Integrations "
        "\u2192 GapAnalysis \u2192 SelfCheck"
    )
    _emit("orchestrator.run.start", {
        "primary_mission": "DIGITAL_LABOUR",
    })

    cwd = str(ROOT)

    # ── DIGITAL LABOUR sync (first — it's the mission) ──
    if DL_BRIDGE.exists():
        _run_stage(
            "DL Bridge Sync", DL_BRIDGE, cwd,
        )
    else:
        log(
            "DL Bridge not yet installed — "
            "skipping DL sync stage",
            "WARN",
        )

    # Discover & onboard new repos from GitHub
    _run_stage_with_args(
        "Portfolio Sync", PORTFOLIO_SYNC,
        ["sync"], cwd,
    )
    _run_stage(
        "Portfolio Self-Heal",
        PORTFOLIO_HEAL, cwd,
    )

    _run_stage("Repo Sentry", SENTRY, cwd)
    _run_stage("Daily Ops Brief", DAILY, cwd)
    _run_stage("Research Report", RESEARCH, cwd)

    # Parallel research
    _run_stage(
        "Parallel Research",
        PARALLEL_RESEARCH, cwd,
    )

    # Weekly intelligence scan
    _run_stage(
        "Intelligence Scheduler",
        INTEL_SCHEDULER, cwd,
    )

    # Second Brain ingests before council
    _process_secondbrain_queue()

    # Rebuild topic index after ingests
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        from topic_index import (  # type: ignore[import-not-found]
            build_index,
        )
        idx = build_index()
        log(
            f"Topic index rebuilt: "
            f"{idx['total_entries']} entries, "
            f"{idx['total_keywords']} keywords"
        )
    except Exception as exc:
        log(f"Topic index rebuild skipped: {exc}")

    # Idea generation engine
    _run_stage_with_args(
        "Idea Engine", IDEA_ENGINE,
        ["all"], cwd,
    )

    # Research metrics dashboard
    _run_stage_with_args(
        "Research Metrics", RESEARCH_METRICS,
        ["dashboard"], cwd,
    )

    _run_stage(
        "Agent Council Meeting", COUNCIL, cwd,
    )
    _run_stage("System Audit", AUDIT, cwd)
    _run_stage(
        "Portfolio AutoTier", AUTOTIER, cwd,
    )

    # System integrations: NCC, NCL, AAC, DL
    _run_stage_with_args(
        "System Integrations", INTEGRATIONS,
        ["sync"], cwd,
    )

    # Autonomous brain: gap analysis + self-check
    _run_stage(
        "Gap Analysis", GAP_ANALYZER, cwd,
    )
    _run_stage(
        "Self-Check Validator", SELF_CHECK, cwd,
    )

    log(
        "DIGITAL LABOUR orchestration complete — "
        "DIGITAL LABOUR primary."
    )
    _emit("orchestrator.run.done", {})


if __name__ == '__main__':
    main()
