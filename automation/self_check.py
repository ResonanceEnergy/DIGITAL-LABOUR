"""Self-Check & Healing Engine — deep system introspection and auto-repair.

Performs comprehensive system analysis every cycle:
- Health verification (LLM providers, databases, agents, directories)
- Gap detection (what's missing, broken, or underperforming)
- Auto-healing (restart services, fix broken state, clear stale data)
- Opportunity identification (untapped capacity, unused agents)

Usage:
    from automation.self_check import run_full_check, heal_issues
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from automation.decision_log import log_decision, log_escalation


# ── Deep System Check ──────────────────────────────────────────

def run_full_check() -> dict:
    """Run comprehensive system introspection. Returns categorized findings."""
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "GREEN",
        "checks": {},
        "issues": [],
        "opportunities": [],
        "metrics": {},
    }

    # 1. Core infrastructure
    report["checks"]["infrastructure"] = _check_infrastructure()

    # 2. LLM provider health
    report["checks"]["llm_providers"] = _check_providers()

    # 3. Pipeline state
    report["checks"]["pipeline"] = _check_pipeline()

    # 4. Outreach state
    report["checks"]["outreach"] = _check_outreach()

    # 5. C-Suite state
    report["checks"]["csuite"] = _check_csuite()

    # 6. Financial state
    report["checks"]["financials"] = _check_financials()

    # Determine overall status
    critical = [i for i in report["issues"] if i["severity"] == "CRITICAL"]
    warnings = [i for i in report["issues"] if i["severity"] == "WARNING"]
    if critical:
        report["status"] = "RED"
    elif warnings:
        report["status"] = "YELLOW"

    report["metrics"]["issue_count"] = len(report["issues"])
    report["metrics"]["opportunity_count"] = len(report["opportunities"])

    return report


def _check_infrastructure() -> dict:
    """Check core files, databases, directories."""
    result = {"status": "ok", "details": {}}

    # .env file
    env_path = PROJECT_ROOT / ".env"
    result["details"]["env_file"] = env_path.exists()
    if not env_path.exists():
        result["status"] = "critical"

    # Data directory and databases
    data_dir = PROJECT_ROOT / "data"
    for db in ["task_queue.db", "kpi.db", "billing.db"]:
        path = data_dir / db
        exists = path.exists()
        result["details"][db] = exists

    # Key directories
    for d in ["output", "agents", "automation", "c_suite", "dashboard"]:
        result["details"][f"dir_{d}"] = (PROJECT_ROOT / d).exists()

    return result


def _check_providers() -> dict:
    """Check LLM provider availability."""
    result = {"available": [], "down": [], "status": "ok"}
    try:
        from utils.llm_client import list_available_providers
        available = list_available_providers()
        result["available"] = available

        all_providers = ["openai", "anthropic", "gemini", "grok"]
        result["down"] = [p for p in all_providers if p not in available]

        if not available:
            result["status"] = "critical"
        elif len(available) < 2:
            result["status"] = "warning"
    except Exception as e:
        result["status"] = "critical"
        result["error"] = str(e)
    return result


def _check_pipeline() -> dict:
    """Check task queue and throughput."""
    result = {"status": "ok", "details": {}}
    try:
        from dispatcher.queue import TaskQueue
        q = TaskQueue()
        stats = q.stats()
        result["details"] = stats

        if stats.get("queued", 0) > 20:
            result["status"] = "warning"
        if stats.get("failed", 0) > 0:
            total = max(stats.get("total", 1), 1)
            fail_rate = stats["failed"] / total * 100
            if fail_rate > 20:
                result["status"] = "critical"
    except Exception:
        result["details"] = {"queued": 0, "running": 0, "completed": 0, "failed": 0}
    return result


def _check_outreach() -> dict:
    """Check outreach pipeline state."""
    result = {"status": "ok", "details": {}}

    # Prospects remaining
    try:
        from automation.outreach import load_prospects, _load_sent_log, _load_followups
        prospects = load_prospects()
        sent = _load_sent_log()
        followups = _load_followups()

        result["details"]["prospects_remaining"] = len(prospects)
        result["details"]["total_sent"] = len(sent)
        result["details"]["followups_pending"] = sum(
            1 for fu in followups
            if not fu.get("follow_up_1_sent") or not fu.get("follow_up_2_sent")
        )

        # Check for due follow-ups
        now = datetime.now(timezone.utc)
        due_followups = 0
        for fu in followups:
            if not fu.get("follow_up_1_sent"):
                due = datetime.fromisoformat(fu["follow_up_1_due"])
                if now >= due:
                    due_followups += 1
            if not fu.get("follow_up_2_sent") and fu.get("follow_up_1_sent"):
                due = datetime.fromisoformat(fu["follow_up_2_due"])
                if now >= due:
                    due_followups += 1
        result["details"]["followups_due_now"] = due_followups

        if len(prospects) == 0:
            result["status"] = "depleted"
        elif len(prospects) < 10:
            result["status"] = "low"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result


def _check_csuite() -> dict:
    """Check C-Suite scheduler state."""
    result = {"status": "ok", "details": {}}
    state_file = PROJECT_ROOT / "data" / "csuite_schedule.json"

    if state_file.exists():
        state = json.loads(state_file.read_text(encoding="utf-8"))
        now = datetime.now(timezone.utc)

        for key in ["last_standup", "last_cash_check", "last_ops_check", "last_full_board"]:
            ts = state.get(key, "")
            if ts:
                then = datetime.fromisoformat(ts)
                hours_ago = (now - then).total_seconds() / 3600
                result["details"][key] = {
                    "timestamp": ts,
                    "hours_ago": round(hours_ago, 1),
                }
            else:
                result["details"][key] = {"timestamp": None, "hours_ago": 999}
    else:
        result["status"] = "never_run"
    return result


def _check_financials() -> dict:
    """Check revenue and financial state."""
    result = {"status": "ok", "details": {}}
    try:
        from billing.tracker import BillingTracker
        bt = BillingTracker()
        rev = bt.revenue_report(days=30)
        result["details"] = rev
        if rev.get("total_revenue", 0) == 0:
            result["status"] = "no_revenue"
    except Exception:
        result["details"] = {"total_revenue": 0}
        result["status"] = "no_data"
    return result


# ── Gap Analysis ───────────────────────────────────────────────

def find_gaps(check_report: dict) -> list[dict]:
    """Analyze check report and identify actionable gaps."""
    gaps = []

    # Gap: Prospects depleted
    outreach = check_report.get("checks", {}).get("outreach", {})
    remaining = outreach.get("details", {}).get("prospects_remaining", 0)
    if remaining == 0:
        gaps.append({
            "id": "PROSPECTS_DEPLETED",
            "severity": "HIGH",
            "description": "Prospect list is empty. No new outreach can happen.",
            "action": "replenish_prospects",
            "auto_fixable": True,
        })
    elif remaining < 10:
        gaps.append({
            "id": "PROSPECTS_LOW",
            "severity": "MEDIUM",
            "description": f"Only {remaining} prospects remaining.",
            "action": "replenish_prospects",
            "auto_fixable": True,
        })

    # Gap: Follow-ups due
    due = outreach.get("details", {}).get("followups_due_now", 0)
    if due > 0:
        gaps.append({
            "id": "FOLLOWUPS_DUE",
            "severity": "MEDIUM",
            "description": f"{due} follow-up emails are due.",
            "action": "send_followups",
            "auto_fixable": True,
        })

    # Gap: LLM providers down
    providers = check_report.get("checks", {}).get("llm_providers", {})
    down = providers.get("down", [])
    if down:
        severity = "CRITICAL" if len(providers.get("available", [])) == 0 else "WARNING"
        gaps.append({
            "id": "PROVIDERS_DOWN",
            "severity": severity,
            "description": f"LLM providers down: {', '.join(down)}",
            "action": "check_api_keys",
            "auto_fixable": False,
        })

    # Gap: Queue backlog
    pipeline = check_report.get("checks", {}).get("pipeline", {})
    queued = pipeline.get("details", {}).get("queued", 0)
    if queued > 10:
        gaps.append({
            "id": "QUEUE_BACKLOG",
            "severity": "HIGH",
            "description": f"{queued} tasks stuck in queue.",
            "action": "process_queue",
            "auto_fixable": True,
        })

    # Gap: No revenue
    financials = check_report.get("checks", {}).get("financials", {})
    if financials.get("status") in ("no_revenue", "no_data"):
        gaps.append({
            "id": "NO_REVENUE",
            "severity": "HIGH",
            "description": "No revenue recorded in last 30 days.",
            "action": "intensify_outreach",
            "auto_fixable": True,
        })

    # Gap: C-Suite stale
    csuite = check_report.get("checks", {}).get("csuite", {})
    if csuite.get("status") == "never_run":
        gaps.append({
            "id": "CSUITE_NEVER_RUN",
            "severity": "MEDIUM",
            "description": "C-Suite executive cadence has never been run.",
            "action": "run_csuite",
            "auto_fixable": True,
        })

    return gaps


# ── Auto-Heal ──────────────────────────────────────────────────

def heal_issues(gaps: list[dict]) -> list[dict]:
    """Attempt to auto-fix identified gaps. Returns results."""
    results = []

    for gap in gaps:
        if not gap.get("auto_fixable"):
            log_escalation(
                source="SELF_CHECK",
                issue=gap["description"],
                severity=gap["severity"],
                recommended_action=gap.get("action", "manual review"),
            )
            results.append({"gap": gap["id"], "action": "escalated", "success": False})
            continue

        action = gap.get("action", "")

        if action == "send_followups":
            try:
                from automation.outreach import send_followups
                sent = send_followups()
                log_decision(
                    actor="SELF_CHECK",
                    action="send_followups",
                    reasoning=gap["description"],
                    outcome=f"Sent {len(sent)} follow-ups",
                )
                results.append({"gap": gap["id"], "action": "send_followups", "success": True, "count": len(sent)})
            except Exception as e:
                results.append({"gap": gap["id"], "action": "send_followups", "success": False, "error": str(e)})

        elif action == "replenish_prospects":
            try:
                from automation.prospect_engine import generate_prospects
                new_count = generate_prospects(count=25)
                log_decision(
                    actor="SELF_CHECK",
                    action="replenish_prospects",
                    reasoning=gap["description"],
                    outcome=f"Generated {new_count} new prospects",
                )
                results.append({"gap": gap["id"], "action": "replenish_prospects", "success": True, "count": new_count})
            except Exception as e:
                results.append({"gap": gap["id"], "action": "replenish_prospects", "success": False, "error": str(e)})

        elif action == "run_csuite":
            try:
                from c_suite.scheduler import run_due_actions
                actions = run_due_actions()
                log_decision(
                    actor="SELF_CHECK",
                    action="run_csuite",
                    reasoning=gap["description"],
                    outcome=f"Ran {len(actions)} C-Suite actions",
                )
                results.append({"gap": gap["id"], "action": "run_csuite", "success": True, "actions": actions})
            except Exception as e:
                results.append({"gap": gap["id"], "action": "run_csuite", "success": False, "error": str(e)})

        elif action == "intensify_outreach":
            # This is handled by the main NERVE loop — flag it for next cycle
            log_decision(
                actor="SELF_CHECK",
                action="flag_intensify_outreach",
                reasoning="No revenue — system needs more aggressive outreach",
                outcome="Flagged for NERVE priority cycle",
            )
            results.append({"gap": gap["id"], "action": "flagged_for_nerve", "success": True})

        elif action == "process_queue":
            try:
                from dispatcher.queue import TaskQueue
                q = TaskQueue()
                # Process next batch from queue
                processed = 0
                for _ in range(min(queued, 10)):
                    task = q.dequeue()
                    if task:
                        processed += 1
                log_decision(
                    actor="SELF_CHECK",
                    action="process_queue",
                    reasoning=gap["description"],
                    outcome=f"Dequeued {processed} tasks for processing",
                )
                results.append({"gap": gap["id"], "action": "process_queue", "success": True, "processed": processed})
            except Exception as e:
                results.append({"gap": gap["id"], "action": "process_queue", "success": False, "error": str(e)})

    return results
