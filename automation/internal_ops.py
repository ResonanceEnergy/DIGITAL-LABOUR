"""Autonomous Internal Operations Engine — Makes Bit Rage build itself.

Instead of waiting for external clients, this module generates real internal
tasks that agents execute to build Bit Rage Labour as a company:
- Portfolio samples for each division
- Market research and competitive analysis
- SEO content and marketing materials
- Compliance audits and quality benchmarks
- Business development materials

Usage:
    from automation.internal_ops import generate_daily_tasks, generate_weekly_tasks

    # Called by NERVE daemon or NCL daily push
    daily_results = generate_daily_tasks()
    weekly_results = generate_weekly_tasks()  # Only on Mondays

CLI:
    python -m automation.internal_ops --daily
    python -m automation.internal_ops --weekly
    python -m automation.internal_ops --status
    python -m automation.internal_ops --full    # Both daily + weekly
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

STATE_FILE = PROJECT_ROOT / "data" / "internal_ops_state.json"
LOG_DIR = PROJECT_ROOT / "data" / "internal_ops_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

API_PORT = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
API_BASE = os.getenv("INTERNAL_OPS_API", f"http://localhost:{API_PORT}")
CLIENT_ID = "bitrage_internal"

# ── Logging ────────────────────────────────────────────────────────────────

_LOG_FMT = logging.Formatter("%(asctime)s [%(levelname)s] internal_ops — %(message)s")
logger = logging.getLogger("internal_ops")
if not logger.handlers:
    _sh = logging.StreamHandler()
    _sh.setFormatter(_LOG_FMT)
    logger.addHandler(_sh)
    _fh = logging.FileHandler(LOG_DIR / "internal_ops.log", encoding="utf-8")
    _fh.setFormatter(_LOG_FMT)
    logger.addHandler(_fh)
    logger.setLevel(logging.INFO)
logger.propagate = False


# ── Task Catalog ───────────────────────────────────────────────────────────

INTERNAL_TASK_CATALOG: dict[str, list[dict[str, Any]]] = {

    # ── INS-OPS Division ───────────────────────────────────────────
    "INS-OPS": [
        {
            "task_type": "insurance_appeals",
            "division": "INS-OPS",
            "inputs": {
                "content": "Generate a sample insurance appeal letter for a denied cardiac rehabilitation claim. "
                           "Use realistic clinical language and cite relevant CMS LCD/NCD references. "
                           "This is for the Bit Rage portfolio — demonstrate maximum persuasive quality.",
                "doc_type": "appeal_letter",
                "purpose": "portfolio_sample",
            },
            "priority": 3,
            "frequency": "weekly",
            "category": "company_building",
            "description": "Portfolio sample: insurance appeal letter",
        },
        {
            "task_type": "insurance_qa",
            "division": "INS-OPS",
            "inputs": {
                "content": "Review the latest batch of insurance appeal outputs for quality benchmarking. "
                           "Score on: clinical accuracy, CMS guideline adherence, persuasive structure, "
                           "and professional tone. Flag any outputs below threshold.",
                "doc_type": "qa_review",
            },
            "priority": 2,
            "frequency": "weekly",
            "category": "operations",
            "description": "QA review of appeal outputs",
        },
        {
            "task_type": "insurance_compliance",
            "division": "INS-OPS",
            "inputs": {
                "content": "Audit current appeal letter templates against the latest CMS guidelines, "
                           "LCD/NCD updates, and payer-specific policy changes. Identify any templates "
                           "that need updating and recommend specific revisions.",
                "doc_type": "compliance_audit",
            },
            "priority": 4,
            "frequency": "monthly",
            "category": "compliance",
            "description": "Compliance audit: CMS guideline alignment",
        },
        {
            "task_type": "market_research",
            "division": "INS-OPS",
            "inputs": {
                "content": "Research the latest insurance denial trends, top denial codes by volume, "
                           "and emerging payer policy changes. Focus on codes most relevant to our "
                           "appeal letter service: prior auth denials, medical necessity, and coding disputes.",
                "focus": "insurance denial trends and common denial codes",
            },
            "priority": 2,
            "frequency": "daily",
            "category": "market_research",
            "description": "Daily research: insurance denial trends",
        },
    ],

    # ── GRANT-OPS Division ─────────────────────────────────────────
    "GRANT-OPS": [
        {
            "task_type": "grant_writer",
            "division": "GRANT-OPS",
            "inputs": {
                "content": "Write a sample SBIR Phase I proposal for Bit Rage's AI-powered document "
                           "automation technology. Topic area: AI/ML for business process automation. "
                           "Include technical approach, commercialization plan, and team qualifications. "
                           "This is for portfolio demonstration — maximum quality.",
                "doc_type": "sbir_proposal",
                "purpose": "portfolio_sample",
            },
            "priority": 3,
            "frequency": "weekly",
            "category": "company_building",
            "description": "Portfolio sample: SBIR proposal",
        },
        {
            "task_type": "grant_qa",
            "division": "GRANT-OPS",
            "inputs": {
                "content": "Review the latest grant proposal outputs for quality benchmarking. "
                           "Score on: adherence to funding agency format, technical merit clarity, "
                           "budget justification quality, and overall competitiveness.",
                "doc_type": "qa_review",
            },
            "priority": 2,
            "frequency": "weekly",
            "category": "operations",
            "description": "QA review of grant proposal quality",
        },
        {
            "task_type": "grant_compliance",
            "division": "GRANT-OPS",
            "inputs": {
                "content": "Check current grant proposal templates against latest federal grant "
                           "regulations including 2 CFR 200, agency-specific FOA requirements, "
                           "and SAM.gov registration requirements. Flag any non-compliant elements.",
                "doc_type": "compliance_check",
            },
            "priority": 4,
            "frequency": "monthly",
            "category": "compliance",
            "description": "Compliance check: federal grant regulations",
        },
        {
            "task_type": "market_research",
            "division": "GRANT-OPS",
            "inputs": {
                "content": "Research new grant opportunities relevant to AI technology companies: "
                           "SBIR, STTR, state innovation grants, and private foundation funding. "
                           "Include deadlines, eligibility requirements, and award amounts.",
                "focus": "grant opportunities for AI technology companies",
            },
            "priority": 2,
            "frequency": "daily",
            "category": "market_research",
            "description": "Daily research: new grant opportunities",
        },
    ],

    # ── CTR-SVC Division ───────────────────────────────────────────
    "CTR-SVC": [
        {
            "task_type": "contractor_doc_writer",
            "division": "CTR-SVC",
            "inputs": {
                "content": "Generate a sample contractor proposal for a commercial HVAC installation "
                           "project. Include scope of work, timeline, materials list, cost breakdown, "
                           "and warranty terms. Portfolio-quality deliverable.",
                "doc_type": "contractor_proposal",
                "purpose": "portfolio_sample",
            },
            "priority": 3,
            "frequency": "weekly",
            "category": "company_building",
            "description": "Portfolio sample: contractor proposal",
        },
        {
            "task_type": "safety_plan",
            "division": "CTR-SVC",
            "inputs": {
                "content": "Generate a sample site-specific safety plan for a mid-rise commercial "
                           "construction project. Include hazard analysis, PPE requirements, "
                           "emergency procedures, and OSHA compliance checklist.",
                "doc_type": "safety_plan",
                "purpose": "portfolio_sample",
            },
            "priority": 3,
            "frequency": "weekly",
            "category": "company_building",
            "description": "Portfolio sample: safety plan template",
        },
        {
            "task_type": "contractor_compliance",
            "division": "CTR-SVC",
            "inputs": {
                "content": "Review contractor document templates against latest OSHA updates, "
                           "state licensing requirements, and industry best practices. "
                           "Flag any templates needing revision for current regulatory compliance.",
                "doc_type": "compliance_review",
            },
            "priority": 4,
            "frequency": "monthly",
            "category": "compliance",
            "description": "Compliance review: OSHA and regulatory updates",
        },
        {
            "task_type": "market_research",
            "division": "CTR-SVC",
            "inputs": {
                "content": "Research construction permit trends by state, focusing on residential "
                           "and commercial building activity. Include permit volume changes, "
                           "hot markets, and implications for contractor documentation demand.",
                "focus": "construction permit trends by state",
            },
            "priority": 2,
            "frequency": "daily",
            "category": "market_research",
            "description": "Daily research: construction permit trends",
        },
    ],

    # ── MUN-SVC Division ───────────────────────────────────────────
    "MUN-SVC": [
        {
            "task_type": "meeting_minutes",
            "division": "MUN-SVC",
            "inputs": {
                "content": "Generate sample city council meeting minutes for a fictional town of "
                           "approximately 25,000 residents. Include realistic agenda items: zoning "
                           "variance, budget amendment, public safety report, and citizen comment period. "
                           "Portfolio-quality demonstration piece.",
                "doc_type": "meeting_minutes",
                "purpose": "portfolio_sample",
            },
            "priority": 3,
            "frequency": "weekly",
            "category": "company_building",
            "description": "Portfolio sample: meeting minutes",
        },
        {
            "task_type": "public_notice",
            "division": "MUN-SVC",
            "inputs": {
                "content": "Generate a sample public notice template for a municipal zoning hearing. "
                           "Include all legally required elements: date, time, location, description "
                           "of action, affected parcels, and comment submission instructions.",
                "doc_type": "public_notice",
                "purpose": "portfolio_sample",
            },
            "priority": 3,
            "frequency": "weekly",
            "category": "company_building",
            "description": "Portfolio sample: public notice template",
        },
        {
            "task_type": "municipal_compliance",
            "division": "MUN-SVC",
            "inputs": {
                "content": "Audit municipal document templates against open meeting law updates, "
                           "state sunshine laws, public records requirements, and ADA compliance "
                           "for digital document accessibility. Flag any non-compliant templates.",
                "doc_type": "compliance_audit",
            },
            "priority": 4,
            "frequency": "monthly",
            "category": "compliance",
            "description": "Compliance audit: open meeting law updates",
        },
        {
            "task_type": "market_research",
            "division": "MUN-SVC",
            "inputs": {
                "content": "Research active municipal RFP opportunities for document management, "
                           "meeting minutes, and administrative services. Include bid deadlines, "
                           "estimated contract values, and eligibility requirements.",
                "focus": "municipal RFP opportunities",
            },
            "priority": 2,
            "frequency": "daily",
            "category": "market_research",
            "description": "Daily research: municipal RFP opportunities",
        },
    ],

    # ── Cross-Division (company-wide) ──────────────────────────────
    "CROSS": [
        {
            "task_type": "market_research",
            "division": "CROSS",
            "inputs": {
                "content": "Comprehensive market research on the AI document automation industry. "
                           "Cover market size, growth rate, key players, pricing models, and "
                           "technology trends. Position Bit Rage Labour within the landscape.",
                "focus": "AI document automation industry landscape",
            },
            "priority": 2,
            "frequency": "daily",
            "category": "market_research",
            "description": "Daily: AI document automation market research",
        },
        {
            "task_type": "seo_content",
            "division": "CROSS",
            "inputs": {
                "content": "Write an SEO-optimized blog post about one of Bit Rage's service verticals. "
                           "Rotate through: insurance appeals automation, grant writing AI, contractor "
                           "document generation, and municipal document services. "
                           "Target 1200-1800 words with proper heading structure.",
                "doc_type": "blog_post",
                "purpose": "seo_content",
            },
            "priority": 3,
            "frequency": "weekly",
            "category": "content",
            "description": "Weekly SEO content piece",
        },
        {
            "task_type": "business_plan",
            "division": "CROSS",
            "inputs": {
                "content": "Update the Bit Rage Labour business plan with latest market data, "
                           "revenue projections, competitive analysis, and strategic priorities. "
                           "Focus on the four-division model and autonomous operations differentiator.",
                "plan_type": "startup",
                "focus": "Bit Rage Labour AI document automation",
            },
            "priority": 3,
            "frequency": "weekly",
            "category": "company_building",
            "description": "Weekly business plan update",
        },
        {
            "task_type": "press_release",
            "division": "CROSS",
            "inputs": {
                "content": "Draft a press release highlighting Bit Rage Labour's AI-powered document "
                           "automation capabilities. Focus on the autonomous multi-division architecture "
                           "and how it delivers faster, more accurate documents than traditional services.",
                "doc_type": "press_release",
            },
            "priority": 2,
            "frequency": "monthly",
            "category": "content",
            "description": "Monthly press release: Bit Rage capabilities",
        },
        {
            "task_type": "market_research",
            "division": "CROSS",
            "inputs": {
                "content": "Competitive analysis of AI document automation services. Analyze pricing, "
                           "features, customer reviews, and market positioning of top competitors. "
                           "Identify Bit Rage's differentiation opportunities and competitive gaps.",
                "focus": "competitive analysis of AI document services",
            },
            "priority": 2,
            "frequency": "daily",
            "category": "market_research",
            "description": "Daily: competitive analysis",
        },
    ],
}


# ── State Management ───────────────────────────────────────────────────────

def _load_state() -> dict:
    """Load internal ops state from disk."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Corrupt state file, resetting: %s", exc)
    return {
        "last_daily": None,
        "last_weekly": None,
        "tasks_dispatched": 0,
        "tasks_succeeded": 0,
        "tasks_failed": 0,
        "history": [],
    }


def _save_state(state: dict):
    """Persist state to disk."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Keep history bounded — last 500 entries
    if len(state.get("history", [])) > 500:
        state["history"] = state["history"][-500:]
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Task Dispatch ──────────────────────────────────────────────────────────

def dispatch_internal_task(task_template: dict, dry_run: bool = False) -> dict:
    """Send a single internal task to the API for processing.

    Returns a result dict with task_id, status, and any error info.
    """
    payload = {
        "task_type": task_template["task_type"],
        "client": CLIENT_ID,
        "inputs": task_template["inputs"],
        "priority": task_template.get("priority", 2),
        "sync": False,
        "schema_version": "2.0",
    }

    result = {
        "task_type": task_template["task_type"],
        "division": task_template.get("division", "CROSS"),
        "description": task_template.get("description", ""),
        "dispatched_at": _now_iso(),
        "dry_run": dry_run,
    }

    if dry_run:
        result["status"] = "dry_run"
        result["task_id"] = "dry-run-no-id"
        logger.info("[DRY RUN] Would dispatch: %s — %s",
                    task_template["task_type"], task_template.get("description", ""))
        return result

    try:
        resp = requests.post(
            f"{API_BASE}/tasks",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        result["task_id"] = data.get("task_id", "unknown")
        result["status"] = "dispatched"
        logger.info("Dispatched %s (ID: %s) — %s",
                    task_template["task_type"], result["task_id"],
                    task_template.get("description", ""))
    except requests.ConnectionError:
        result["status"] = "failed"
        result["error"] = f"Cannot connect to API at {API_BASE}/tasks"
        logger.error("Connection failed for %s: API not reachable at %s",
                     task_template["task_type"], API_BASE)
    except requests.HTTPError as exc:
        result["status"] = "failed"
        result["error"] = f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
        logger.error("HTTP error dispatching %s: %s", task_template["task_type"], result["error"])
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)[:200]
        logger.error("Unexpected error dispatching %s: %s", task_template["task_type"], exc)

    return result


# ── Task Selection ─────────────────────────────────────────────────────────

def _select_tasks(frequency: str, state: dict) -> list[dict]:
    """Select tasks from the catalog matching the given frequency.

    Applies TWO layers of deduplication:
    1. Dispatch history — skips tasks already dispatched today/this week
    2. Output store — skips tasks that already have recent completed outputs
       (closes the feedback loop so agents don't redo finished work)
    """
    today = _today_str()
    now = datetime.now(timezone.utc)
    selected = []

    # Build a set of (task_type, division) already dispatched today
    dispatched_today = set()
    for entry in state.get("history", []):
        if entry.get("dispatched_at", "").startswith(today):
            dispatched_today.add((entry.get("task_type"), entry.get("division")))

    # Output store awareness — check what's already been completed
    try:
        from utils.output_awareness import should_dispatch as _should_dispatch
        output_aware = True
    except ImportError:
        output_aware = False
        logger.debug("Output awareness not available — skipping output dedup")

    # Cooldown windows: daily tasks 20h, weekly 6 days, monthly 25 days
    cooldown_map = {"daily": 20, "weekly": 144, "monthly": 600}
    cooldown_hours = cooldown_map.get(frequency, 20)

    for division, tasks in INTERNAL_TASK_CATALOG.items():
        for task in tasks:
            if task["frequency"] != frequency:
                continue

            task_key = (task["task_type"], task.get("division", division))

            # Layer 1: Dispatch history dedup
            if frequency == "daily" and task_key in dispatched_today:
                logger.debug("Skipping %s/%s — already dispatched today", *task_key)
                continue

            # Weekly tasks: only on Mondays (0 = Monday) unless forced
            if frequency == "weekly" and now.weekday() != 0:
                continue

            # Monthly tasks: only on 1st of month unless forced
            if frequency == "monthly" and now.day != 1:
                continue

            # Layer 2: Output store dedup — skip if recent output exists
            if output_aware:
                try:
                    ok, reason = _should_dispatch(
                        task["task_type"],
                        division=task.get("division", division),
                        cooldown_hours=cooldown_hours,
                    )
                    if not ok:
                        logger.info("Skipping %s/%s — output store: %s",
                                    task["task_type"], division, reason)
                        continue
                except Exception as e:
                    logger.debug("Output check failed for %s: %s (proceeding)", task["task_type"], e)

            selected.append(task)

    return selected


# ── Batch Generators ───────────────────────────────────────────────────────

def generate_daily_tasks(dry_run: bool = False, force: bool = False) -> dict:
    """Generate and dispatch the daily batch of internal tasks.

    Args:
        dry_run: If True, log what would be dispatched without calling the API.
        force: If True, skip deduplication checks.

    Returns:
        Summary dict with counts and individual task results.
    """
    state = _load_state()
    today = _today_str()

    if not force and state.get("last_daily") == today:
        logger.info("Daily tasks already dispatched today (%s). Use --force to override.", today)
        return {"status": "skipped", "reason": "already_run_today", "date": today}

    logger.info("=" * 60)
    logger.info("INTERNAL OPS — Daily Task Generation (%s)", today)
    logger.info("=" * 60)

    tasks = _select_tasks("daily", state if not force else {"history": []})
    results = []

    for task in tasks:
        result = dispatch_internal_task(task, dry_run=dry_run)
        results.append(result)
        state["history"].append(result)
        if result["status"] == "dispatched":
            state["tasks_dispatched"] = state.get("tasks_dispatched", 0) + 1
            state["tasks_succeeded"] = state.get("tasks_succeeded", 0) + 1
        elif result["status"] == "failed":
            state["tasks_failed"] = state.get("tasks_failed", 0) + 1
        # Brief pause between dispatches to avoid flooding
        if not dry_run:
            time.sleep(0.5)

    state["last_daily"] = today
    _save_state(state)

    succeeded = sum(1 for r in results if r["status"] in ("dispatched", "dry_run"))
    failed = sum(1 for r in results if r["status"] == "failed")

    summary = {
        "status": "completed",
        "batch": "daily",
        "date": today,
        "total": len(results),
        "succeeded": succeeded,
        "failed": failed,
        "tasks": results,
    }

    logger.info("Daily batch complete: %d dispatched, %d failed out of %d total",
                succeeded, failed, len(results))
    return summary


def generate_weekly_tasks(dry_run: bool = False, force: bool = False) -> dict:
    """Generate and dispatch the weekly strategic batch.

    Only runs on Mondays unless force=True.

    Args:
        dry_run: If True, log what would be dispatched without calling the API.
        force: If True, run regardless of day-of-week and dedup.

    Returns:
        Summary dict with counts and individual task results.
    """
    state = _load_state()
    today = _today_str()
    now = datetime.now(timezone.utc)

    if not force and now.weekday() != 0:
        logger.info("Weekly tasks only run on Mondays (today is %s). Use --force to override.",
                     now.strftime("%A"))
        return {"status": "skipped", "reason": "not_monday", "day": now.strftime("%A")}

    if not force and state.get("last_weekly") == today:
        logger.info("Weekly tasks already dispatched this week (%s). Use --force to override.", today)
        return {"status": "skipped", "reason": "already_run_this_week", "date": today}

    logger.info("=" * 60)
    logger.info("INTERNAL OPS — Weekly Strategic Batch (%s)", today)
    logger.info("=" * 60)

    # Weekly tasks + monthly tasks (if it's the 1st)
    weekly_tasks = []
    for division, tasks in INTERNAL_TASK_CATALOG.items():
        for task in tasks:
            if task["frequency"] == "weekly":
                weekly_tasks.append(task)
            elif task["frequency"] == "monthly" and (force or now.day <= 7):
                # Run monthly tasks in the first week of the month
                weekly_tasks.append(task)

    results = []
    for task in weekly_tasks:
        result = dispatch_internal_task(task, dry_run=dry_run)
        results.append(result)
        state["history"].append(result)
        if result["status"] == "dispatched":
            state["tasks_dispatched"] = state.get("tasks_dispatched", 0) + 1
            state["tasks_succeeded"] = state.get("tasks_succeeded", 0) + 1
        elif result["status"] == "failed":
            state["tasks_failed"] = state.get("tasks_failed", 0) + 1
        if not dry_run:
            time.sleep(1.0)  # Longer pause for heavier weekly tasks

    state["last_weekly"] = today
    _save_state(state)

    succeeded = sum(1 for r in results if r["status"] in ("dispatched", "dry_run"))
    failed = sum(1 for r in results if r["status"] == "failed")

    summary = {
        "status": "completed",
        "batch": "weekly",
        "date": today,
        "total": len(results),
        "succeeded": succeeded,
        "failed": failed,
        "tasks": results,
    }

    logger.info("Weekly batch complete: %d dispatched, %d failed out of %d total",
                succeeded, failed, len(results))
    return summary


# ── Status Report ──────────────────────────────────────────────────────────

def get_status() -> dict:
    """Return current internal ops status and recent history."""
    state = _load_state()
    today = _today_str()

    today_tasks = [e for e in state.get("history", [])
                   if e.get("dispatched_at", "").startswith(today)]
    today_succeeded = sum(1 for t in today_tasks if t.get("status") in ("dispatched", "dry_run"))
    today_failed = sum(1 for t in today_tasks if t.get("status") == "failed")

    # Count tasks in catalog by frequency
    catalog_counts = {"daily": 0, "weekly": 0, "monthly": 0}
    for tasks in INTERNAL_TASK_CATALOG.values():
        for task in tasks:
            freq = task.get("frequency", "once")
            if freq in catalog_counts:
                catalog_counts[freq] += 1

    return {
        "last_daily": state.get("last_daily"),
        "last_weekly": state.get("last_weekly"),
        "lifetime_dispatched": state.get("tasks_dispatched", 0),
        "lifetime_succeeded": state.get("tasks_succeeded", 0),
        "lifetime_failed": state.get("tasks_failed", 0),
        "today_dispatched": len(today_tasks),
        "today_succeeded": today_succeeded,
        "today_failed": today_failed,
        "catalog_daily_tasks": catalog_counts["daily"],
        "catalog_weekly_tasks": catalog_counts["weekly"],
        "catalog_monthly_tasks": catalog_counts["monthly"],
        "divisions": list(INTERNAL_TASK_CATALOG.keys()),
        "recent_history": state.get("history", [])[-10:],
    }


def print_status():
    """Print a formatted status report to stdout."""
    status = get_status()
    print("\n" + "=" * 60)
    print("  INTERNAL OPS ENGINE — Status Report")
    print("=" * 60)
    print(f"  Last daily run:    {status['last_daily'] or 'never'}")
    print(f"  Last weekly run:   {status['last_weekly'] or 'never'}")
    print(f"  Divisions:         {', '.join(status['divisions'])}")
    print()
    print(f"  Catalog size:      {status['catalog_daily_tasks']} daily / "
          f"{status['catalog_weekly_tasks']} weekly / "
          f"{status['catalog_monthly_tasks']} monthly")
    print()
    print(f"  Today:             {status['today_dispatched']} dispatched "
          f"({status['today_succeeded']} ok, {status['today_failed']} failed)")
    print(f"  Lifetime:          {status['lifetime_dispatched']} dispatched "
          f"({status['lifetime_succeeded']} ok, {status['lifetime_failed']} failed)")

    recent = status.get("recent_history", [])
    if recent:
        print(f"\n  Recent tasks (last {len(recent)}):")
        for entry in recent:
            marker = "OK" if entry.get("status") in ("dispatched", "dry_run") else "FAIL"
            print(f"    [{marker}] {entry.get('task_type', '?'):25s} "
                  f"{entry.get('division', '?'):10s} "
                  f"{entry.get('dispatched_at', '?')[:16]}")

    print("=" * 60 + "\n")


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="internal_ops",
        description="Autonomous Internal Operations Engine — Makes Bit Rage build itself.",
    )
    parser.add_argument("--daily", action="store_true", help="Run daily task batch")
    parser.add_argument("--weekly", action="store_true", help="Run weekly strategic batch")
    parser.add_argument("--full", action="store_true", help="Run both daily and weekly batches")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--force", action="store_true", help="Skip dedup and day-of-week checks")
    parser.add_argument("--dry-run", action="store_true", help="Log tasks without dispatching")
    args = parser.parse_args()

    if not any([args.daily, args.weekly, args.full, args.status]):
        parser.print_help()
        sys.exit(1)

    if args.status:
        print_status()
        return

    results = []

    if args.daily or args.full:
        r = generate_daily_tasks(dry_run=args.dry_run, force=args.force)
        results.append(r)
        print(json.dumps(r, indent=2, default=str))

    if args.weekly or args.full:
        r = generate_weekly_tasks(dry_run=args.dry_run, force=args.force)
        results.append(r)
        print(json.dumps(r, indent=2, default=str))

    # Exit code: 0 if all batches completed, 1 if any failed tasks
    total_failed = sum(r.get("failed", 0) for r in results if isinstance(r.get("failed"), int))
    sys.exit(1 if total_failed > 0 else 0)


if __name__ == "__main__":
    main()
