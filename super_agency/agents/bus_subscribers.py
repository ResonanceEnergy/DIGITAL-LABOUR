#!/usr/bin/env python3
"""
Bus Subscribers — wires handlers to message bus topics.

Called once at boot from run_bit_rage_labour.py to connect the pub/sub plumbing.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from agents.message_bus import bus

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
_EVENTS_LOG = ROOT / "logs" / "events.ndjson"
_EVENTS_LOG.parent.mkdir(parents=True, exist_ok=True)
_ALERTS_LOG = ROOT / "logs" / "alerts.ndjson"


# ── Handlers ────────────────────────────────────────────────────────────

def _log_event(msg):
    """Append every event to a single NDJSON file for auditability."""
    try:
        with open(_EVENTS_LOG, "a") as fh:
            fh.write(json.dumps(msg.to_dict()) + "\n")
    except Exception as exc:
        logger.debug(f"event log write failed: {exc}")


def _on_stage_fail(msg):
    """Log warnings for failed orchestrator stages."""
    stage = msg.payload.get("stage", "?")
    code = msg.payload.get("code", "?")
    logger.warning(
        f"[BUS] Orchestrator stage FAILED: "
        f"{stage} (exit code {code})"
    )
    _write_alert(
        "stage_failure",
        f"Orchestrator stage '{stage}' failed "
        f"with exit code {code}",
        severity="HIGH",
        stage=stage,
    )


def _on_stage_skip(msg):
    """Log when a stage is skipped due to circuit breaker."""
    stage = msg.payload.get("stage", "?")
    reason = msg.payload.get("reason", "?")
    logger.warning(
        f"[BUS] Stage SKIPPED: {stage} ({reason})"
    )
    _write_alert(
        "stage_skipped",
        f"Stage '{stage}' skipped: {reason}",
        severity="MEDIUM",
        stage=stage,
    )


def _on_run_done(msg):
    """Log when a full orchestrator run completes."""
    logger.info(f"[BUS] Orchestrator run completed at {msg.ts}")


def _on_run_start(msg):
    """Log when orchestrator starts a new run."""
    logger.info(
        f"[BUS] Orchestrator run starting at {msg.ts}"
    )


# ── Integration event handlers ──────────────────────────────

def _on_integration_sync(msg):
    """Log integration sync events (NCC/NCL/AAC)."""
    src = msg.payload.get("source", msg.topic)
    logger.info(f"[BUS] Integration sync: {src}")


# ── BIT RAGE LABOUR event handlers (primary mission) ─────────

_DL_KPI_LOG = ROOT / "logs" / "dl_events.ndjson"


def _persist_dl_event(event_type: str, payload: dict):
    """Append DL event to dedicated KPI log."""
    try:
        _DL_KPI_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now().isoformat(),
            "event_type": event_type,
            **payload,
        }
        with open(_DL_KPI_LOG, "a") as fh:
            fh.write(json.dumps(entry, default=str) + "\n")
    except Exception as exc:
        logger.debug(f"DL event log write failed: {exc}")


def _on_dl_task_completed(msg):
    """Handle DL task completion — log KPI, update metrics."""
    task_type = msg.payload.get("task_type", "unknown")
    client_id = msg.payload.get("client_id", "")
    cost = msg.payload.get("cost_usd", 0)
    logger.info(
        f"[DL] Task completed: {task_type} "
        f"client={client_id} cost=${cost:.3f}"
    )
    _persist_dl_event("task_completed", msg.payload)


def _on_dl_task_failed(msg):
    """Handle DL task failure — alert, log for VECTIS review."""
    task_type = msg.payload.get("task_type", "unknown")
    reason = msg.payload.get("reason", "unknown")
    logger.warning(
        f"[DL] Task FAILED: {task_type} — {reason}"
    )
    _persist_dl_event("task_failed", msg.payload)
    _write_alert(
        "dl_task_failure",
        f"DL task '{task_type}' failed: {reason}",
        severity="HIGH",
    )


def _on_dl_revenue(msg):
    """Handle DL revenue events — track for LEDGR/AAC."""
    amount = msg.payload.get("amount", 0)
    client = msg.payload.get("client_id", "")
    logger.info(
        f"[DL] Revenue: ${amount:.2f} from {client}"
    )
    _persist_dl_event("revenue", msg.payload)


def _on_dl_fleet_status(msg):
    """Handle DL fleet status updates."""
    agent_count = msg.payload.get("agent_count", 0)
    active = msg.payload.get("active_tasks", 0)
    logger.info(
        f"[DL] Fleet: {agent_count} agents, "
        f"{active} active tasks"
    )
    _persist_dl_event("fleet_status", msg.payload)


def _on_dl_nerve_cycle(msg):
    """Handle NERVE daemon cycle events."""
    phase = msg.payload.get("phase", "unknown")
    logger.info(f"[DL] NERVE cycle: {phase}")
    _persist_dl_event("nerve_cycle", msg.payload)


def _on_dl_csuite_report(msg):
    """Handle C-Suite board meeting reports."""
    verdict = msg.payload.get("overall_status", "")
    logger.info(
        f"[DL] C-Suite report: {verdict}"
    )
    _persist_dl_event("csuite_report", msg.payload)


def _on_dl_qa_alert(msg):
    """Handle DL QA failures — escalate to Operations."""
    agent = msg.payload.get("agent", "unknown")
    rate = msg.payload.get("pass_rate", "?")
    logger.warning(
        f"[DL] QA alert: {agent} pass_rate={rate}"
    )
    _persist_dl_event("qa_alert", msg.payload)
    _write_alert(
        "dl_qa_alert",
        f"DL agent '{agent}' QA rate: {rate}",
        severity="HIGH",
    )


def _on_dl_client_event(msg):
    """Handle DL client events (onboard, churn, etc)."""
    event = msg.payload.get("event", "unknown")
    client = msg.payload.get("client_id", "")
    logger.info(
        f"[DL] Client event: {event} — {client}"
    )
    _persist_dl_event("client_event", msg.payload)


def _on_parallel_research(msg):
    """Log parallel research events."""
    if "elapsed_s" in msg.payload:
        n = msg.payload.get("projects", 0)
        t = msg.payload.get("elapsed_s", 0)
        logger.info(
            f"[BUS] Parallel research done: "
            f"{n} projects in {t}s"
        )
    else:
        logger.info(
            f"[BUS] Parallel research: {msg.topic}"
        )


def _on_budget_alert(msg):
    """Escalate AAC budget alerts."""
    logger.warning(
        f"[BUS] Budget alert: {msg.payload}"
    )
    _write_alert(
        "budget_alert",
        json.dumps(msg.payload),
        severity="HIGH",
    )


def _on_scheduler_cycle(msg):
    """Log research scheduler cycle events."""
    cycle = msg.payload.get("cycle", "?")
    status = msg.payload.get("status", "?")
    logger.info(
        f"[BUS] Scheduler cycle {cycle}: {status}"
    )


def _on_ideas_generated(msg):
    """Log idea engine output."""
    logger.info(
        f"[BUS] Ideas generated at {msg.ts}"
    )


def _on_metrics_dashboard(msg):
    """Log metrics dashboard generation."""
    logger.info(
        f"[BUS] Metrics dashboard generated at {msg.ts}"
    )


def _on_brain_event(msg):
    """Log autonomous brain events."""
    topic = msg.topic
    if "error" in topic:
        logger.warning(
            f"[BUS] Brain error: "
            f"{msg.payload.get('error', '?')}"
        )
    elif "cycle.done" in topic:
        p = msg.payload
        logger.info(
            f"[BUS] Brain cycle #{p.get('cycle', '?')}"
            f": {p.get('gaps_found', 0)} gaps, "
            f"{p.get('actions_succeeded', 0)}/"
            f"{p.get('actions_taken', 0)} actions OK"
        )
    else:
        logger.info(f"[BUS] Brain: {topic}")


def _on_gaps_analyzed(msg):
    """Log gap analysis results."""
    p = msg.payload
    logger.info(
        f"[BUS] Gaps: {p.get('total_gaps', 0)} "
        f"(C:{p.get('critical', 0)} "
        f"H:{p.get('high', 0)})"
    )


def _on_validation_complete(msg):
    """Log validation results."""
    p = msg.payload
    score = p.get("score", 0)
    issues = p.get("issues", 0)
    level = (
        "WARNING" if score < 70
        else "INFO"
    )
    logger.log(
        logging.WARNING if level == "WARNING"
        else logging.INFO,
        f"[BUS] Validation: score={score}/100, "
        f"issues={issues}",
    )


# ── Research Intelligence handlers ──────────────────────────

def _on_research_intel(msg):
    """Log research intelligence cycle events."""
    p = msg.payload
    if "anomaly" in msg.topic:
        logger.warning(
            f"[BUS] Research anomaly: "
            f"score={p.get('score', '?')}"
        )
        _write_alert(
            "research_anomaly",
            f"Research velocity anomaly "
            f"(score={p.get('score')})",
            severity="MEDIUM",
        )
    else:
        logger.info(
            f"[BUS] ResearchIntel cycle "
            f"#{p.get('cycle', '?')} "
            f"strategy={p.get('strategy', '?')}"
        )


def _on_alignment_event(msg):
    """Log alignment monitor results."""
    p = msg.payload
    if "violation" in msg.topic:
        logger.warning(
            f"[BUS] Alignment violations: "
            f"{p.get('count', 0)} checks failed"
        )
        _write_alert(
            "alignment_violation",
            f"{p.get('count', 0)} alignment "
            f"checks failed: {p.get('checks', [])}",
            severity="HIGH",
        )
    else:
        logger.info(
            f"[BUS] Alignment check: "
            f"passed={p.get('passed', 0)} "
            f"failed={p.get('failed', 0)}"
        )


def _on_learning_event(msg):
    """Log learning agent cycle events."""
    p = msg.payload
    logger.info(
        f"[BUS] Learning cycle #{p.get('cycle', '?')}"
        f": {p.get('new_lessons', 0)} new lessons"
        f" (total {p.get('total_lessons', 0)})"
    )


def _on_hierarchy_event(msg):
    """Log hierarchy routing and registration."""
    p = msg.payload
    if "routed" in msg.topic:
        logger.info(
            f"[BUS] Task routed: "
            f"{p.get('task', '?')} → "
            f"{p.get('agent', '?')} "
            f"(tier {p.get('tier', '?')})"
        )
    elif "registered" in msg.topic:
        logger.info(
            f"[BUS] Agent registered: "
            f"{p.get('agent', '?')} "
            f"at tier {p.get('tier', '?')}"
        )


def _on_context_mgr(msg):
    """Handle context manager events."""
    p = msg.payload
    if "stale_alert" in msg.topic:
        logger.warning(
            f"[BUS] Context stale alert: "
            f"{p.get('stale_count', 0)} entries"
        )
    elif "cycle" in msg.topic:
        logger.info(
            f"[BUS] Context cycle "
            f"{p.get('cycle', '?')}"
        )


def _on_qa_mgr(msg):
    """Handle QA manager events."""
    p = msg.payload
    if "below_threshold" in msg.topic:
        logger.warning(
            f"[BUS] QA below threshold: "
            f"{p.get('score', '?')}"
        )
        _write_alert(
            "qa_below_threshold",
            f"Quality score {p.get('score', '?')} "
            f"below {p.get('threshold', '?')}",
            severity="HIGH",
        )
    elif "cycle" in msg.topic:
        logger.info(
            f"[BUS] QA cycle {p.get('cycle', '?')} "
            f"— {'PASS' if p.get('passed') else 'FAIL'}"
        )


def _on_production_mgr(msg):
    """Handle production manager events."""
    p = msg.payload
    if "degraded" in msg.topic:
        logger.warning(
            f"[BUS] Production DEGRADED: "
            f"{p.get('issues', [])}"
        )
        _write_alert(
            "production_degraded",
            f"Production health degraded: "
            f"{p.get('issues', [])}",
            severity="HIGH",
        )
    elif "cycle" in msg.topic:
        logger.info(
            f"[BUS] Production cycle "
            f"{p.get('cycle', '?')} — "
            f"{p.get('health', '?')}"
        )


def _on_automation_mgr(msg):
    """Handle automation manager events."""
    p = msg.payload
    if "stale" in msg.topic:
        logger.warning(
            f"[BUS] Automation stale workflows: "
            f"{p.get('stale', 0)}"
        )
    elif "cycle" in msg.topic:
        logger.info(
            f"[BUS] Automation cycle "
            f"{p.get('cycle', '?')}"
        )


def _write_alert(
    alert_type: str, message: str,
    severity: str = "MEDIUM", **extra,
):
    """Write a structured alert to the NDJSON alert log."""
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "type": alert_type,
        "severity": severity,
        "message": message,
        **extra,
    }
    try:
        with open(_ALERTS_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError:
        pass


# ── Registration ────────────────────────────────────────────────────────

def register_all():
    """Wire all standard subscribers. Call once at startup."""
    bus.subscribe("orchestrator.*", _log_event)
    bus.subscribe("orchestrator.stage.fail", _on_stage_fail)
    bus.subscribe("orchestrator.stage.skip", _on_stage_skip)
    bus.subscribe("orchestrator.run.done", _on_run_done)
    bus.subscribe("orchestrator.run.start", _on_run_start)

    # Integration subsystem events (NCC, NCL, AAC, DL)
    bus.subscribe("ncc.sync.*", _on_integration_sync)
    bus.subscribe("ncl.sync.*", _on_integration_sync)
    bus.subscribe("aac.sync.*", _on_integration_sync)
    bus.subscribe("aac.budget.alert", _on_budget_alert)
    bus.subscribe(
        "integrations.sync.*", _on_integration_sync,
    )
    bus.subscribe(
        "portfolio.sync.*", _on_integration_sync,
    )

    # ── BIT RAGE LABOUR events (primary mission) ──
    bus.subscribe(
        "bit_rage_labour.task.completed",
        _on_dl_task_completed,
    )
    bus.subscribe(
        "bit_rage_labour.task.failed",
        _on_dl_task_failed,
    )
    bus.subscribe(
        "bit_rage_labour.revenue.*",
        _on_dl_revenue,
    )
    bus.subscribe(
        "bit_rage_labour.fleet.status",
        _on_dl_fleet_status,
    )
    bus.subscribe(
        "bit_rage_labour.nerve.*",
        _on_dl_nerve_cycle,
    )
    bus.subscribe(
        "bit_rage_labour.csuite.report",
        _on_dl_csuite_report,
    )
    bus.subscribe(
        "bit_rage_labour.qa.alert",
        _on_dl_qa_alert,
    )
    bus.subscribe(
        "bit_rage_labour.client.*",
        _on_dl_client_event,
    )
    # Legacy catch-all for any DL sync events
    bus.subscribe(
        "bit_rage_labour.sync.*",
        _on_integration_sync,
    )
    bus.subscribe(
        "research.parallel.*", _on_parallel_research,
    )

    # Research enterprise events
    bus.subscribe(
        "scheduler.cycle.*", _on_scheduler_cycle,
    )
    bus.subscribe(
        "ideas.generated", _on_ideas_generated,
    )
    bus.subscribe(
        "metrics.dashboard.*", _on_metrics_dashboard,
    )

    # Autonomous brain events
    bus.subscribe("brain.*", _on_brain_event)
    bus.subscribe("gaps.analyzed", _on_gaps_analyzed)
    bus.subscribe(
        "validation.complete", _on_validation_complete,
    )

    # Research intelligence events
    bus.subscribe(
        "research.intelligence.*",
        _on_research_intel,
    )

    # Alignment monitor events
    bus.subscribe(
        "alignment.*", _on_alignment_event,
    )

    # Learning agent events
    bus.subscribe(
        "learning.*", _on_learning_event,
    )

    # Hierarchy events
    bus.subscribe(
        "hierarchy.*", _on_hierarchy_event,
    )

    # Manager agents events
    bus.subscribe(
        "context.manager.*", _on_context_mgr,
    )
    bus.subscribe(
        "qa.*", _on_qa_mgr,
    )
    bus.subscribe(
        "production.*", _on_production_mgr,
    )
    bus.subscribe(
        "automation.*", _on_automation_mgr,
    )

    # GASKET bridge (best-effort — only if agent_gasket importable)
    try:
        from agents.agent_gasket import register_gasket_bus_bridge
        register_gasket_bus_bridge()
        logger.info("[BUS] GASKET bus bridge registered")
    except Exception as exc:
        logger.debug(f"[BUS] GASKET bridge not available: {exc}")

    logger.info(
        "[BUS] Subscribers registered "
        "(event log, stages, integrations, "
        "brain, research intel, alignment, "
        "learning, hierarchy, managers, "
        "GASKET bridge)"
    )
