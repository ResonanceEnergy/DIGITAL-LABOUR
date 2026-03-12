"""Production Manager Agent -- Supervisory agent for capacity planning,
queue management, SLA compliance, and production reporting.

Usage:
    python runner.py --action capacity_check
    python runner.py --action schedule --tasks '[{"task_type":"seo_content","client_id":"acme"}]'
    python runner.py --action report
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv(PROJECT_ROOT / ".env")

from utils.llm_client import call_llm as llm_call


# -- Data paths ---------------------------------------------------------------

DATA_DIR = PROJECT_ROOT / "data" / "production_manager"
LOG_DIR = DATA_DIR / "logs"
STATE_FILE = DATA_DIR / "production_state.json"
KPI_LOG_DIR = PROJECT_ROOT / "kpi" / "logs"

for d in [DATA_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# -- Constants ----------------------------------------------------------------

DAILY_LIMITS = {
    "sales_outreach": 50, "support_ticket": 100,
    "content_repurpose": 40, "doc_extract": 60,
    "lead_gen": 40, "email_marketing": 30,
    "seo_content": 25, "social_media": 50,
    "data_entry": 80, "web_scraper": 30,
    "crm_ops": 40, "bookkeeping": 20,
    "proposal_writer": 15, "product_desc": 30,
    "resume_writer": 25, "ad_copy": 30,
    "market_research": 10, "business_plan": 8,
    "press_release": 20, "tech_docs": 15,
}

# USD cost estimates per 1K tokens by provider
PROVIDER_COSTS = {
    "openai": {"input": 0.005, "output": 0.015},
    "anthropic": {"input": 0.003, "output": 0.015},
    "gemini": {"input": 0.00035, "output": 0.0014},
    "grok": {"input": 0.005, "output": 0.015},
}

# Complexity tiers for provider routing
SIMPLE_TASKS = {"data_entry", "web_scraper", "doc_extract"}
COMPLEX_TASKS = {"business_plan", "market_research", "proposal_writer"}

SLA_TARGETS = {
    "basic": 24,      # hours
    "standard": 48,
    "premium": 72,
}


# -- Models -------------------------------------------------------------------

class CapacityStatus(BaseModel):
    available_slots: dict = {}
    at_risk_agents: list[str] = []
    token_budget_remaining: dict = {}
    utilization_pct: dict = {}


class SLAStatus(BaseModel):
    on_track: list[dict] = []
    at_risk: list[dict] = []
    breached: list[dict] = []


class ProductionMetrics(BaseModel):
    tasks_today: int = 0
    revenue_today: float = 0.0
    avg_quality_score: float = 0.0
    qa_pass_rate: float = 0.0
    busiest_agents: list[str] = []
    idle_agents: list[str] = []


class ScheduleEntry(BaseModel):
    task_id: str = ""
    task_type: str
    client_id: str = ""
    priority: int = 50
    recommended_provider: str = "gemini"
    estimated_cost_usd: float = 0.0
    sla_deadline_hours: int = 48


class ProductionOutput(BaseModel):
    schedule: list[ScheduleEntry] = []
    capacity: CapacityStatus = CapacityStatus()
    sla: SLAStatus = SLAStatus()
    metrics: ProductionMetrics = ProductionMetrics()
    throttle_actions: list[str] = []
    recommendations: list[str] = []


class ProductionState(BaseModel):
    daily_counts: dict = {}
    daily_token_usage: dict = {}
    date: str = ""
    active_tasks: list[dict] = []


# -- State Persistence --------------------------------------------------------

def load_state() -> ProductionState:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if STATE_FILE.exists():
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        state = ProductionState.model_validate(data)
        if state.date != today:
            # Reset daily counters
            state.daily_counts = {}
            state.daily_token_usage = {}
            state.date = today
        return state
    return ProductionState(date=today)


def save_state(state: ProductionState) -> None:
    STATE_FILE.write_text(state.model_dump_json(indent=2), encoding="utf-8")


# -- Core Functions -----------------------------------------------------------

def check_capacity() -> CapacityStatus:
    """Check current capacity across all agents."""
    state = load_state()
    available = {}
    at_risk = []
    utilization = {}

    for agent, limit in DAILY_LIMITS.items():
        used = state.daily_counts.get(agent, 0)
        remaining = max(0, limit - used)
        available[agent] = remaining
        pct = round(used / limit * 100, 1) if limit else 0
        utilization[agent] = pct
        if pct >= 80:
            at_risk.append(f"{agent} ({pct}% used, {remaining} remaining)")

    return CapacityStatus(
        available_slots=available,
        at_risk_agents=at_risk,
        utilization_pct=utilization,
    )


def recommend_provider(task_type: str) -> str:
    """Recommend optimal LLM provider based on task complexity."""
    if task_type in SIMPLE_TASKS:
        return "gemini"  # cheapest
    if task_type in COMPLEX_TASKS:
        return "anthropic"  # best reasoning
    return "openai"  # balanced default


def estimate_cost(task_type: str, provider: str) -> float:
    """Estimate cost for a task based on typical token usage."""
    # Rough estimates of tokens per task type
    token_estimates = {
        "data_entry": 500, "doc_extract": 800,
        "web_scraper": 600, "support_ticket": 1000,
        "sales_outreach": 2000, "lead_gen": 1500,
        "email_marketing": 1500, "seo_content": 2500,
        "social_media": 1200, "content_repurpose": 1800,
        "crm_ops": 800, "bookkeeping": 1000,
        "proposal_writer": 3000, "product_desc": 1200,
        "resume_writer": 2000, "ad_copy": 1500,
        "market_research": 4000, "business_plan": 5000,
        "press_release": 1500, "tech_docs": 3000,
    }
    tokens = token_estimates.get(task_type, 1500)
    costs = PROVIDER_COSTS.get(provider, PROVIDER_COSTS["openai"])
    # Assume 40% input, 60% output
    input_cost = (tokens * 0.4 / 1000) * costs["input"]
    output_cost = (tokens * 0.6 / 1000) * costs["output"]
    return round(input_cost + output_cost, 4)


def schedule_tasks(tasks: list[dict],
                   provider: str | None = None) -> ProductionOutput:
    """Schedule and prioritize a batch of tasks."""
    capacity = check_capacity()
    state = load_state()
    schedule = []
    throttle_actions = []
    recommendations = []

    for task in tasks:
        task_type = task.get("task_type", "")
        client_id = task.get("client_id", "")
        priority = task.get("priority", 50)
        sla_tier = task.get("sla_tier", "standard")

        available = capacity.available_slots.get(task_type, 0)
        if available <= 0:
            throttle_actions.append(
                f"THROTTLED: {task_type} at daily limit. "
                f"Queued for tomorrow."
            )
            continue

        rec_provider = provider or recommend_provider(task_type)
        cost = estimate_cost(task_type, rec_provider)

        entry = ScheduleEntry(
            task_id=uuid4().hex[:8],
            task_type=task_type,
            client_id=client_id,
            priority=priority,
            recommended_provider=rec_provider,
            estimated_cost_usd=cost,
            sla_deadline_hours=SLA_TARGETS.get(sla_tier, 48),
        )
        schedule.append(entry)

        # Update counts
        state.daily_counts[task_type] = (
            state.daily_counts.get(task_type, 0) + 1
        )

    # Sort by priority (higher = more urgent)
    schedule.sort(key=lambda x: x.priority, reverse=True)

    # Recommendations
    idle = [
        a for a, slots in capacity.available_slots.items()
        if slots == DAILY_LIMITS.get(a, 0) and DAILY_LIMITS.get(a, 0) > 0
    ]
    if idle:
        recommendations.append(
            f"Idle agents with zero tasks today: {idle[:5]}. "
            f"Consider marketing these services."
        )

    total_cost = sum(e.estimated_cost_usd for e in schedule)
    if total_cost > 10:
        recommendations.append(
            f"Batch cost estimate: ${total_cost:.2f}. "
            f"Consider routing simple tasks to Gemini to save."
        )

    save_state(state)

    return ProductionOutput(
        schedule=schedule,
        capacity=capacity,
        throttle_actions=throttle_actions,
        recommendations=recommendations,
    )


def record_completion(task_type: str, revenue: float = 0.0,
                      quality_score: int = 0) -> None:
    """Record a completed task for metrics tracking."""
    state = load_state()
    state.daily_counts[task_type] = (
        state.daily_counts.get(task_type, 0) + 1
    )
    save_state(state)
    _log_action("completion", task_type, {
        "revenue": revenue,
        "quality_score": quality_score,
    })


def generate_report(provider: str | None = None) -> dict:
    """Generate a production report."""
    state = load_state()
    capacity = check_capacity()

    total_tasks = sum(state.daily_counts.values())
    busiest = sorted(
        state.daily_counts.items(), key=lambda x: x[1], reverse=True
    )[:5]
    idle = [
        a for a in DAILY_LIMITS
        if state.daily_counts.get(a, 0) == 0
    ]

    return {
        "report_date": datetime.now(timezone.utc).isoformat(),
        "total_tasks_today": total_tasks,
        "busiest_agents": [
            f"{k}: {v}" for k, v in busiest
        ],
        "idle_agents": idle,
        "at_risk_capacity": capacity.at_risk_agents,
        "utilization": capacity.utilization_pct,
        "daily_counts": state.daily_counts,
    }


# -- Logging ------------------------------------------------------------------

def _log_action(action: str, task_type: str, data: dict) -> None:
    log_file = LOG_DIR / (
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
    )
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "task_type": task_type,
        "data": data,
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


# -- Pipeline (for dispatcher integration) ------------------------------------

def run_pipeline(
    action: str = "capacity_check",
    tasks: list | None = None,
    task_type: str = "",
    provider: str | None = None,
    **kwargs,
) -> ProductionOutput | dict:
    """Main entry point for dispatcher routing."""
    if action == "capacity_check":
        cap = check_capacity()
        return ProductionOutput(capacity=cap)
    elif action == "schedule":
        return schedule_tasks(tasks or [], provider)
    elif action == "report":
        return generate_report(provider)
    elif action == "recommend_provider":
        rec = recommend_provider(task_type)
        cost = estimate_cost(task_type, rec)
        return {
            "task_type": task_type,
            "recommended_provider": rec,
            "estimated_cost_usd": cost,
        }
    else:
        return ProductionOutput(
            recommendations=[f"Unknown action: {action}"],
        )


# -- CLI -----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Production Manager -- Supervisory Agent"
    )
    parser.add_argument(
        "--action", required=True,
        choices=["capacity_check", "schedule", "report",
                 "recommend_provider"],
    )
    parser.add_argument("--task-type", default="")
    parser.add_argument(
        "--tasks", default="[]",
        help="JSON array of tasks to schedule",
    )
    parser.add_argument(
        "--provider", default=None,
        choices=["openai", "anthropic", "gemini", "grok"],
    )
    args = parser.parse_args()

    tasks = json.loads(args.tasks)
    result = run_pipeline(
        action=args.action,
        tasks=tasks,
        task_type=args.task_type,
        provider=args.provider,
    )

    if isinstance(result, dict):
        print(json.dumps(result, indent=2, default=str))
    else:
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
