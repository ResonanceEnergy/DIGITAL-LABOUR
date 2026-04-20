"""NCL Operations Commander — The Lead Brain for Bit Rage + DIGITAL LABOUR.

NCL is the strategic intelligence layer that LEADS daily operations:
  1. Pushes daily ops cadence to NERVE and C-Suite
  2. Has each division head produce weekly goals + roadmap
  3. Delegates task lists to respective agents
  4. Runs autonomously — only escalates BIG decisions and payments to human owner
  5. Monitors all 4 divisions and intervenes when metrics slip

NCL doesn't just observe — it COMMANDS.

Usage:
    python -m NCL.ncl_operations_commander                    # Run daily ops push
    python -m NCL.ncl_operations_commander --weekly-goals     # Force weekly goal generation
    python -m NCL.ncl_operations_commander --full-cycle       # Daily push + weekly if due
    python -m NCL.ncl_operations_commander --status           # Current ops status
    python -m NCL.ncl_operations_commander --daemon           # 24/7 ops commander
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# ── State Files ───────────────────────────────────────────────────
STATE_DIR = PROJECT_ROOT / "data"
STATE_DIR.mkdir(parents=True, exist_ok=True)

NCL_STATE_FILE = STATE_DIR / "ncl_ops_state.json"
WEEKLY_GOALS_DIR = STATE_DIR / "weekly_goals"
WEEKLY_GOALS_DIR.mkdir(parents=True, exist_ok=True)

ESCALATION_THRESHOLDS = {
    "payment_approval_usd": 500,       # Notify human for payments > $500
    "new_client_onboarding": True,      # Always notify for new clients
    "agent_pause_count": 3,             # Notify if 3+ agents paused
    "division_degraded": True,          # Notify if any division goes RED
    "daily_spend_ceiling_usd": 50,      # Notify if daily LLM spend > $50
    "revenue_milestone_usd": 1000,      # Notify on revenue milestones
    "failed_task_streak": 5,            # Notify if 5+ consecutive failures
}

# ── Division Definitions ──────────────────────────────────────────
DIVISIONS = {
    "ins_ops": {
        "name": "Insurance Operations Division",
        "head": "AXIOM",
        "code": "INS-OPS",
        "agents": ["insurance_appeals", "insurance_qa", "insurance_compliance_checker"],
        "services": [
            "insurance_appeal", "prior_auth", "denial_overturn",
            "external_review", "medical_necessity", "erisa_appeal",
            "state_insurance_complaint",
        ],
        "tam": "$500B",
        "priority": 1,
        "max_daily": 25,
        "cost_ceiling": 0.40,
        "qa_gate": True,
        "bus_topic": "bit_rage_labour.division.ins_ops.*",
    },
    "grant_ops": {
        "name": "Grant Operations Division",
        "head": "AXIOM",
        "code": "GRANT-OPS",
        "agents": ["grant_writer", "grant_qa", "grant_researcher"],
        "services": [
            "grant_proposal", "sbir_proposal", "rfa_response",
            "budget_justification", "compliance_matrix", "technical_narrative",
            "commercialization_plan", "grant_amendment",
        ],
        "tam": "$150B",
        "priority": 2,
        "max_daily": 20,
        "cost_ceiling": 0.50,
        "qa_gate": True,
        "bus_topic": "bit_rage_labour.division.grant_ops.*",
    },
    "ctr_svc": {
        "name": "Contractor Services Division",
        "head": "VECTIS",
        "code": "CTR-SVC",
        "agents": ["contractor_doc_writer", "contractor_qa", "contractor_compliance"],
        "services": [
            "permit_application", "inspection_report", "contractor_proposal",
            "lien_waiver", "safety_plan", "change_order",
            "progress_report", "bid_document",
        ],
        "tam": "$2T",
        "priority": 3,
        "max_daily": 30,
        "cost_ceiling": 0.35,
        "qa_gate": True,
        "bus_topic": "bit_rage_labour.division.ctr_svc.*",
    },
    "mun_svc": {
        "name": "Municipal Services Division",
        "head": "VECTIS",
        "code": "MUN-SVC",
        "agents": ["municipal_doc_writer", "municipal_qa", "municipal_compliance"],
        "services": [
            "meeting_minutes", "public_notice", "ordinance", "resolution",
            "municipal_grant", "budget_summary", "annual_report",
            "municipal_rfp", "agenda", "staff_report",
        ],
        "tam": "$400B",
        "priority": 4,
        "max_daily": 30,
        "cost_ceiling": 0.30,
        "qa_gate": True,
        "bus_topic": "bit_rage_labour.division.mun_svc.*",
    },
}

# Map division service types to router-compatible task_types
SERVICE_TO_TASKTYPE = {
    # INS-OPS
    "insurance_appeal": "insurance_appeals",
    "prior_auth": "insurance_appeals",
    "denial_overturn": "insurance_appeals",
    "external_review": "insurance_appeals",
    "medical_necessity": "insurance_qa",
    "erisa_appeal": "insurance_compliance",
    "state_insurance_complaint": "insurance_compliance",
    # GRANT-OPS
    "grant_proposal": "grant_writer",
    "sbir_proposal": "grant_writer",
    "rfa_response": "grant_writer",
    "budget_justification": "grant_writer",
    "compliance_matrix": "grant_compliance",
    "technical_narrative": "grant_writer",
    "commercialization_plan": "grant_writer",
    "grant_amendment": "grant_writer",
    # CTR-SVC — these are directly routable
    "permit_application": "permit_application",
    "inspection_report": "inspection_report",
    "contractor_proposal": "contractor_proposal",
    "lien_waiver": "lien_waiver",
    "safety_plan": "safety_plan",
    "change_order": "change_order",
    "progress_report": "progress_report",
    "bid_document": "bid_document",
    # MUN-SVC — these are directly routable
    "meeting_minutes": "meeting_minutes",
    "public_notice": "public_notice",
    "ordinance": "ordinance",
    "resolution": "resolution",
    "municipal_grant": "municipal_grant",
    "budget_summary": "budget_summary",
    "annual_report": "annual_report",
    "municipal_rfp": "municipal_rfp",
    "agenda": "agenda",
    "staff_report": "staff_report",
}


# ── State Management ──────────────────────────────────────────────

def _load_state() -> dict:
    if NCL_STATE_FILE.exists():
        return json.loads(NCL_STATE_FILE.read_text(encoding="utf-8"))
    return {
        "last_daily_push": None,
        "last_weekly_goals": None,
        "cycle_count": 0,
        "divisions_status": {},
        "escalations_sent": 0,
        "tasks_fired_today": 0,
    }


def _save_state(state: dict):
    NCL_STATE_FILE.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def _hours_since(iso_ts: str | None) -> float:
    if not iso_ts:
        return 999
    then = datetime.fromisoformat(iso_ts)
    now = datetime.now(timezone.utc)
    return (now - then).total_seconds() / 3600


# ── Notification Helpers ──────────────────────────────────────────

def _notify(title: str, message: str, priority: str = "MEDIUM",
            ntype: str = "STATUS_UPDATE", action_url: str = None):
    """Send notification to workstation dashboard."""
    try:
        from notifications.models import (
            NotificationStore, NotificationType, NotificationPriority
        )
        store = NotificationStore(db_path=str(STATE_DIR / "notifications.db"))
        store.create(
            notification_type=NotificationType(ntype),
            title=title,
            message=message,
            priority=NotificationPriority(priority),
            source="ncl-ops-commander",
            action_url=action_url,
        )
        print(f"  [NOTIFY] {priority}: {title}")
    except Exception as e:
        print(f"  [NOTIFY ERROR] {e}")


def _escalate(title: str, message: str, action_url: str = None):
    """Escalate to human owner — CRITICAL priority, DECISION_NEEDED type."""
    _notify(title, message, priority="CRITICAL", ntype="DECISION_NEEDED", action_url=action_url)
    # Also log to escalations file
    try:
        from automation.decision_log import log_escalation
        log_escalation(
            issue=title,
            severity="HIGH",
            details=message,
            suggested_action="Review in workstation dashboard",
        )
    except Exception:
        pass


def _notify_payment(title: str, amount: float, details: str):
    """Payment notification — always HIGH priority."""
    _notify(
        title,
        f"${amount:.2f} — {details}",
        priority="HIGH",
        ntype="PAYMENT_REQUIRED",
        action_url="/workstation#alerts",
    )


def _notify_milestone(title: str, message: str):
    """Revenue or ops milestone — celebrate wins."""
    _notify(title, message, priority="MEDIUM", ntype="MILESTONE")


# ── Division Health Check ─────────────────────────────────────────

def check_division_health() -> dict:
    """Check all 4 divisions via division_hub and return status."""
    print("\n[NCL OPS] Checking division health...")
    results = {}
    try:
        from super_agency.division_hub import DivisionHub
        hub = DivisionHub()
        health = hub.health_report()
        for div_code, div_status in health.get("divisions", {}).items():
            status = div_status.get("status", "UNKNOWN")
            results[div_code] = status
            if status in ("DEGRADED", "RED"):
                _escalate(
                    f"Division {div_code} is {status}",
                    f"Division health check returned {status}. "
                    f"Tasks today: {div_status.get('tasks_today', 'N/A')}. "
                    f"Circuit breaker: {'OPEN' if div_status.get('breaker_open') else 'closed'}",
                )
            print(f"  {div_code}: {status}")
    except Exception as e:
        print(f"  [DIVISION CHECK ERROR] {e}")
        # Fallback: mark all as unknown
        for div_id in DIVISIONS:
            results[div_id] = "UNKNOWN"
    return results


# ── C-Suite Executive Orders ──────────────────────────────────────

def push_csuite_cadence() -> dict:
    """NCL pushes C-Suite to run their cadence — standup or board meeting."""
    print("\n[NCL OPS] Pushing C-Suite cadence...")
    try:
        from c_suite.scheduler import run_due_actions
        actions = run_due_actions()
        if actions:
            print(f"  C-Suite ran: {', '.join(actions)}")
            _notify("C-Suite Cadence Complete", f"Actions: {', '.join(actions)}")
        else:
            print("  No C-Suite actions due this cycle.")
        return {"actions": actions}
    except Exception as e:
        print(f"  [C-SUITE ERROR] {e}")
        return {"error": str(e)}


# ── Weekly Goals Generator ────────────────────────────────────────

def generate_weekly_goals(force: bool = False) -> dict:
    """Have each division head write their weekly goals, roadmap, and task list.

    Each division head (AXIOM or VECTIS) produces:
    - 3-5 weekly goals with success metrics
    - A 7-day roadmap with milestones
    - Concrete task list for their agents
    """
    state = _load_state()

    if not force and _hours_since(state.get("last_weekly_goals")) < 144:  # 6 days
        print("[NCL OPS] Weekly goals already generated this week. Use --weekly-goals to force.")
        return {"status": "skipped", "reason": "generated_this_week"}

    print("\n" + "=" * 70)
    print("  NCL OPERATIONS COMMANDER — WEEKLY GOALS GENERATION")
    print("=" * 70)

    week_id = datetime.now(timezone.utc).strftime("%Y-W%V")
    all_goals = {}

    for div_id, div_info in DIVISIONS.items():
        print(f"\n[NCL OPS] Generating weekly goals for {div_info['name']}...")
        goals = _generate_division_goals(div_id, div_info, week_id)
        all_goals[div_id] = goals

        # Save to file
        goal_file = WEEKLY_GOALS_DIR / f"{week_id}_{div_id}_goals.json"
        goal_file.write_text(json.dumps(goals, indent=2, default=str), encoding="utf-8")
        print(f"  Saved: {goal_file.name}")

    # Save combined weekly plan
    combined = {
        "week": week_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": "NCL Operations Commander",
        "divisions": all_goals,
    }
    combined_file = WEEKLY_GOALS_DIR / f"{week_id}_combined_plan.json"
    combined_file.write_text(json.dumps(combined, indent=2, default=str), encoding="utf-8")

    state["last_weekly_goals"] = datetime.now(timezone.utc).isoformat()
    _save_state(state)

    _notify_milestone(
        f"Weekly Goals Generated — {week_id}",
        f"All 4 division heads have submitted goals and roadmaps. "
        f"Task lists dispatched to agents.",
    )

    print(f"\n[NCL OPS] Weekly goals saved to {WEEKLY_GOALS_DIR}/")
    return combined


def _generate_division_goals(div_id: str, div_info: dict, week_id: str) -> dict:
    """Use LLM to have each division head write their weekly goals."""
    try:
        from utils.dl_agent import call_llm

        head = div_info["head"]
        division_name = div_info["name"]
        div_code = div_info["code"]
        agents = div_info["agents"]
        services = div_info["services"]
        tam = div_info["tam"]
        max_daily = div_info.get("max_daily", 20)
        cost_ceiling = div_info.get("cost_ceiling", 0.40)

        prompt = f"""You are {head}, the executive head of the {division_name} ({div_code}) at Bit Rage Labour.

Your division has TAM of {tam}, max {max_daily} tasks/day, cost ceiling ${cost_ceiling}/task.
Your agents: {', '.join(agents)} (all have QA gate enforcement).
Your services: {', '.join(services)}.

It is {week_id}. As division head, produce your WEEKLY OPERATIONS PLAN:

1. **WEEKLY GOALS** (3-5 goals, each with measurable success metric):
   - What specific outcomes will your division achieve this week?
   - Each goal must have a KPI (e.g., "Process 10 insurance appeals with >80% approval rate")

2. **7-DAY ROADMAP** (day-by-day milestones):
   - Monday: what happens
   - Tuesday-Friday: progressive milestones
   - Weekend: monitoring/cleanup
   - Key decision points and checkpoints

3. **AGENT TASK LIST** (specific tasks assigned to each agent):
   For each agent ({', '.join(agents)}), list:
   - 3-5 concrete tasks for the week
   - Priority (P0 = critical, P1 = high, P2 = standard)
   - Estimated completions per day
   - Dependencies or blockers

4. **ESCALATION TRIGGERS** (what should NCL flag to the human owner):
   - Revenue milestones worth celebrating
   - Decisions that need human approval
   - Risks that need human awareness

5. **REVENUE TARGET** for the week:
   - Realistic revenue goal based on current pipeline
   - Number of deliverables to produce
   - Client acquisition target

Respond in strict JSON format with keys: weekly_goals, roadmap, agent_tasks, escalation_triggers, revenue_target"""

        result = call_llm(
            prompt=prompt,
            system="You are a division head at an AI labour company. Be aggressive, specific, and metric-driven. Output valid JSON only.",
            provider=os.environ.get("DEFAULT_PROVIDER", "openai"),
            max_tokens=2000,
        )

        # Try to parse as JSON
        try:
            # Clean up markdown fencing if present
            text = result.get("text", "") if isinstance(result, dict) else str(result)
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            if text.startswith("json"):
                text = text[4:]
            goals_data = json.loads(text.strip())
        except (json.JSONDecodeError, AttributeError):
            goals_data = {
                "weekly_goals": [
                    {"goal": f"Establish {division_name} pipeline", "metric": "5+ tasks processed", "priority": "P0"},
                    {"goal": "Achieve 80%+ QA pass rate", "metric": "QA score > 0.8", "priority": "P0"},
                    {"goal": "Generate first revenue", "metric": "$100+ billed", "priority": "P1"},
                ],
                "roadmap": {"monday": "Pipeline setup", "tuesday": "First task execution", "wednesday": "QA calibration", "thursday": "Client outreach", "friday": "Revenue push"},
                "agent_tasks": {agent: [{"task": f"Execute {services[0]} tasks", "priority": "P1", "per_day": 3}] for agent in agents},
                "escalation_triggers": ["Revenue > $500 in a day", "QA failure rate > 30%", "New enterprise client inquiry"],
                "revenue_target": {"weekly_goal_usd": 500, "deliverables": 15, "new_clients": 2},
                "raw_response": str(result),
            }

        goals_data["division"] = division_name
        goals_data["head"] = head
        goals_data["week"] = week_id
        goals_data["generated_at"] = datetime.now(timezone.utc).isoformat()
        return goals_data

    except Exception as e:
        print(f"    [LLM ERROR] {e}")
        return {
            "division": div_info["name"],
            "head": div_info["head"],
            "week": week_id,
            "error": str(e),
            "weekly_goals": [{"goal": "Establish operations", "metric": "System online", "priority": "P0"}],
            "agent_tasks": {},
        }


# ── Daily Operations Push ─────────────────────────────────────────

def daily_ops_push() -> dict:
    """NCL's daily operations push — the core autonomous loop.

    1. Check all division health
    2. Push C-Suite cadence
    3. Fire tasks to underperforming divisions
    4. Check NERVE status
    5. Review escalations
    6. Notify human of anything requiring attention
    """
    state = _load_state()
    state["cycle_count"] = state.get("cycle_count", 0) + 1
    cycle = state["cycle_count"]

    print("\n" + "=" * 70)
    print(f"  NCL OPERATIONS COMMANDER — DAILY PUSH (Cycle #{cycle})")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    report = {"cycle": cycle, "timestamp": datetime.now(timezone.utc).isoformat()}

    # Phase 1: Division Health
    print("\n[PHASE 1] Division Health Check")
    div_health = check_division_health()
    report["division_health"] = div_health
    state["divisions_status"] = div_health

    # Phase 2: C-Suite Cadence
    print("\n[PHASE 2] C-Suite Executive Cadence")
    csuite = push_csuite_cadence()
    report["csuite"] = csuite

    # Phase 3: NERVE Status Check
    print("\n[PHASE 3] NERVE Daemon Status")
    nerve_status = _check_nerve_status()
    report["nerve"] = nerve_status

    # Phase 4: Check Pending Escalations
    print("\n[PHASE 4] Escalation Review")
    escalations = _review_escalations()
    report["escalations"] = escalations

    # Phase 5: Queue Health
    print("\n[PHASE 5] Task Queue Health")
    queue_health = _check_queue_health()
    report["queue"] = queue_health

    # Phase 6: Revenue Check
    print("\n[PHASE 6] Revenue Snapshot")
    revenue = _check_revenue()
    report["revenue"] = revenue

    # Phase 7: Output Intelligence Brief — check what's already been produced
    print("\n[PHASE 7] Output Intelligence Brief")
    output_brief = {}
    try:
        from utils.output_awareness import get_intelligence_brief, get_output_gaps
        output_brief = get_intelligence_brief()
        gaps = get_output_gaps(DIVISIONS)
        output_brief["gaps"] = gaps
        print(f"  Total outputs in store: {output_brief.get('total_outputs', 0)}")
        print(f"  Completions last 6h: {output_brief.get('recent_6h', 0)}")
        if gaps:
            for div_id, gap_info in gaps.items():
                print(f"  GAP [{gap_info['code']}]: Missing outputs from {gap_info['missing_agent_outputs']}")
        else:
            print("  All divisions have agent outputs — no gaps detected.")
    except Exception as e:
        print(f"  [OUTPUT BRIEF ERROR] {e}")
        output_brief["error"] = str(e)
    report["output_brief"] = output_brief

    # Phase 8: Fire tasks to divisions that need activity
    print("\n[PHASE 8] Division Task Dispatch")
    dispatched = _auto_dispatch_division_tasks(div_health)
    report["dispatched"] = dispatched

    # Phase 9: Internal Ops Engine — Self-building tasks
    print("\n[PHASE 9] Internal Operations Engine")
    internal_ops_result = {}
    try:
        from automation.internal_ops import generate_daily_tasks, generate_weekly_tasks
        internal_ops_result["daily"] = generate_daily_tasks()
        # Weekly tasks on Mondays or if never run
        from datetime import date
        if date.today().weekday() == 0 or not state.get("last_weekly_internal"):
            internal_ops_result["weekly"] = generate_weekly_tasks(force=True)
            state["last_weekly_internal"] = datetime.now(timezone.utc).isoformat()
        print(f"  Internal ops: {internal_ops_result.get('daily', {}).get('dispatched', 0)} daily tasks fired")
    except Exception as e:
        print(f"  [INTERNAL OPS ERROR] {e}")
        internal_ops_result["error"] = str(e)
    report["internal_ops"] = internal_ops_result

    # Phase 10: Weekly goals check (if due)
    if _hours_since(state.get("last_weekly_goals")) > 144:  # > 6 days
        print("\n[PHASE 10] Weekly Goals Due — Generating...")
        generate_weekly_goals(force=True)

    # Save state
    state["last_daily_push"] = datetime.now(timezone.utc).isoformat()
    state["tasks_fired_today"] = dispatched.get("total_fired", 0) + internal_ops_result.get("daily", {}).get("dispatched", 0)
    _save_state(state)

    # Summary notification
    green_count = sum(1 for s in div_health.values() if s == "GREEN")
    _notify(
        f"Daily Ops Push Complete — Cycle #{cycle}",
        f"Divisions: {green_count}/4 GREEN | "
        f"C-Suite: {len(csuite.get('actions', []))} actions | "
        f"Tasks fired: {dispatched.get('total_fired', 0)} | "
        f"Escalations: {len(escalations.get('pending', []))}",
        priority="LOW",
    )

    print("\n" + "=" * 70)
    print(f"  DAILY PUSH COMPLETE — {green_count}/4 divisions GREEN")
    print("=" * 70)

    return report


def _check_nerve_status() -> dict:
    """Check if NERVE daemon is running and healthy."""
    nerve_state_file = STATE_DIR / "nerve_state.json"
    if nerve_state_file.exists():
        data = json.loads(nerve_state_file.read_text(encoding="utf-8"))
        last_cycle = data.get("last_cycle_end")
        hours_ago = _hours_since(last_cycle) if last_cycle else 999

        if hours_ago > 2:
            print(f"  NERVE last cycle: {hours_ago:.1f}h ago — STALE")
            _escalate("NERVE Daemon Stale", f"Last cycle was {hours_ago:.1f} hours ago. May need restart.")
            return {"status": "STALE", "hours_since_last": hours_ago}
        else:
            print(f"  NERVE last cycle: {hours_ago:.1f}h ago — ACTIVE")
            return {"status": "ACTIVE", "hours_since_last": hours_ago, "cycles": data.get("cycle_count", 0)}
    else:
        print("  NERVE state not found — NOT RUNNING")
        _escalate("NERVE Daemon Not Running", "No nerve_state.json found. Start with: python -m automation.nerve --daemon")
        return {"status": "NOT_RUNNING"}


def _review_escalations() -> dict:
    """Check for unacknowledged escalations."""
    try:
        from automation.decision_log import get_escalations
        pending = get_escalations()
        recent = [e for e in pending if _hours_since(e.get("timestamp", "")) < 24]
        print(f"  Pending escalations (24h): {len(recent)}")
        for esc in recent[:5]:
            print(f"    - {esc.get('issue', 'Unknown')}")
        return {"pending": recent, "count": len(recent)}
    except Exception as e:
        print(f"  [ESCALATION CHECK ERROR] {e}")
        return {"error": str(e), "pending": [], "count": 0}


def _check_queue_health() -> dict:
    """Check task queue depth and status."""
    try:
        from dispatcher.queue import TaskQueue
        q = TaskQueue()
        stats = q.stats()
        print(f"  Queue: {stats.get('queued', 0)} queued, {stats.get('running', 0)} running, "
              f"{stats.get('completed', 0)} completed, {stats.get('failed', 0)} failed")
        return stats
    except Exception as e:
        print(f"  [QUEUE CHECK ERROR] {e}")
        return {"error": str(e)}


def _check_revenue() -> dict:
    """Quick revenue snapshot."""
    try:
        billing_db = STATE_DIR / "billing.db"
        if billing_db.exists():
            import sqlite3
            conn = sqlite3.connect(str(billing_db))
            cursor = conn.cursor()
            # Get today's revenue
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            cursor.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) FROM tasks WHERE date(created_at) = ?",
                (today,)
            )
            daily_cost = cursor.fetchone()[0]
            conn.close()
            print(f"  Daily LLM spend: ${daily_cost:.2f}")

            if daily_cost > ESCALATION_THRESHOLDS["daily_spend_ceiling_usd"]:
                _escalate(
                    "Daily Spend Ceiling Hit",
                    f"LLM spend today: ${daily_cost:.2f} (ceiling: ${ESCALATION_THRESHOLDS['daily_spend_ceiling_usd']})",
                )
            return {"daily_spend_usd": daily_cost}
        else:
            print("  Billing DB not found")
            return {"status": "no_billing_db"}
    except Exception as e:
        print(f"  [REVENUE CHECK ERROR] {e}")
        return {"error": str(e)}


def _auto_dispatch_division_tasks(div_health: dict) -> dict:
    """Fire warm-up tasks to divisions that need activity."""
    fired = {}
    total = 0

    for div_id, div_info in DIVISIONS.items():
        status = div_health.get(div_id, "UNKNOWN")
        if status in ("GREEN", "UNKNOWN"):
            # Fire a lightweight test task using the division's first service type
            service_name = div_info["services"][0]  # Lead service
            task_type = SERVICE_TO_TASKTYPE.get(service_name, service_name)
            lead_agent = div_info["agents"][0]    # Lead agent
            print(f"  Dispatching warm-up task to {div_info['name']} [{div_info['code']}] ({task_type} → {lead_agent})")
            try:
                import urllib.request
                payload = json.dumps({
                    "task_type": task_type,
                    "client": "ncl-ops-commander",
                    "provider": os.environ.get("DEFAULT_PROVIDER", "openai"),
                    "priority": 3,
                    "division": div_info["code"],
                    "inputs": {
                        "content": f"Generate a weekly operations report for {div_info['name']} [{div_info['code']}]. Cover current status, recent deliverables, upcoming priorities, and resource utilization. Division TAM: {div_info['tam']}. Max daily tasks: {div_info.get('max_daily', 'N/A')}.",
                        "doc_type": service_name,
                    },
                    "sync": False,
                    "schema_version": "2.0",
                }).encode()

                req = urllib.request.Request(
                    f"http://localhost:{os.environ.get('PORT', '8000')}/tasks",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    result = json.loads(resp.read().decode())
                    fired[div_id] = result.get("task_id", "unknown")
                    total += 1
                    print(f"    Task queued: {result.get('task_id', 'N/A')}")
            except Exception as e:
                print(f"    [DISPATCH ERROR] {e}")
                fired[div_id] = f"error: {e}"

    fired["total_fired"] = total
    return fired


# ── Operations Status Report ──────────────────────────────────────

def ops_status() -> dict:
    """Full operational status report for NCL."""
    state = _load_state()

    print("\n" + "=" * 70)
    print("  NCL OPERATIONS COMMANDER — STATUS REPORT")
    print("=" * 70)
    print(f"  Cycles completed : {state.get('cycle_count', 0)}")
    print(f"  Last daily push  : {state.get('last_daily_push', 'Never')}")
    print(f"  Last weekly goals : {state.get('last_weekly_goals', 'Never')}")
    print(f"  Tasks fired today : {state.get('tasks_fired_today', 0)}")
    print(f"  Escalations sent  : {state.get('escalations_sent', 0)}")
    print()

    # Division status
    print("  DIVISION STATUS:")
    for div_id, div_info in DIVISIONS.items():
        status = state.get("divisions_status", {}).get(div_id, "UNKNOWN")
        code = div_info["code"]
        agents = ", ".join(div_info["agents"])
        svc_count = len(div_info["services"])
        print(f"    {div_info['name']:35s} [{code}] [{status}]")
        print(f"      Head: {div_info['head']}  TAM: {div_info['tam']}  "
              f"Max: {div_info.get('max_daily', 'N/A')}/day  "
              f"Ceiling: ${div_info.get('cost_ceiling', 'N/A')}/task")
        print(f"      Agents: {agents}")
        print(f"      Services: {svc_count} types  QA Gate: {'ON' if div_info.get('qa_gate') else 'OFF'}")

    # Weekly goals files
    print(f"\n  WEEKLY GOALS: {len(list(WEEKLY_GOALS_DIR.glob('*.json')))} files")
    for f in sorted(WEEKLY_GOALS_DIR.glob("*_combined_plan.json"))[-3:]:
        print(f"    {f.name}")

    print("=" * 70)
    return state


# ── Daemon Mode ───────────────────────────────────────────────────

def run_daemon():
    """Run NCL Operations Commander as a 24/7 daemon.

    Cycle: every 4 hours
    - Daily ops push
    - Weekly goals (if due)
    - Continuous health monitoring
    """
    print("[NCL OPS COMMANDER] Starting daemon mode...")
    print("[NCL OPS COMMANDER] Cycle interval: 4 hours")
    print("[NCL OPS COMMANDER] Press Ctrl+C to stop\n")

    _notify(
        "NCL Operations Commander Started",
        "Daemon mode active. Pushing daily ops every 4 hours. "
        "Division heads generating weekly goals on schedule.",
        priority="LOW",
    )

    while True:
        try:
            daily_ops_push()
        except Exception as e:
            print(f"\n[NCL OPS ERROR] {e}")
            _escalate("NCL Ops Commander Error", str(e))

        # Sleep 4 hours
        print(f"\n[NCL OPS] Next cycle in 4 hours. Sleeping...")
        time.sleep(4 * 3600)


# ── CLI Entry Point ───────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="NCL Operations Commander")
    parser.add_argument("--weekly-goals", action="store_true", help="Force weekly goal generation")
    parser.add_argument("--full-cycle", action="store_true", help="Daily push + weekly goals if due")
    parser.add_argument("--status", action="store_true", help="Show operational status")
    parser.add_argument("--daemon", action="store_true", help="Run as 24/7 daemon")
    args = parser.parse_args()

    if args.status:
        ops_status()
    elif args.weekly_goals:
        generate_weekly_goals(force=True)
    elif args.daemon:
        run_daemon()
    elif args.full_cycle:
        daily_ops_push()
    else:
        daily_ops_push()


if __name__ == "__main__":
    main()
