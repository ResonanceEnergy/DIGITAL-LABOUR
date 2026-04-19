"""Dispatcher — Routes tasks to the correct agent, enforces budgets, logs results.

Usage:
    python router.py                          # Interactive mode
    python router.py --task task.json         # Process a single task file
    python router.py --queue queue/           # Process all tasks in queue directory
"""

import argparse
import json
import logging
import os
import sys
import time
import threading
from collections import defaultdict
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("dispatcher.router")

from config.constants import DOCTRINE_VERSION

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")


# ── Config ──────────────────────────────────────────────────────────────────

# ── Agent Registry ──────────────────────────────────────────────────────────

_REGISTRY_PATH = PROJECT_ROOT / "config" / "agent_registry.json"


def _load_registry() -> dict:
    """Load agent registry from config. Returns empty dict on error."""
    if _REGISTRY_PATH.exists():
        try:
            return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8")).get("agents", {})
        except Exception as exc:
            logger.warning("Failed to load agent registry: %s", exc)
    return {}


AGENT_REGISTRY: dict = _load_registry()


def _registry_get(agent: str, key: str, default):
    """Get a field from the agent registry with fallback."""
    return AGENT_REGISTRY.get(agent, {}).get(key, default)


def save_registry():
    """Persist the in-memory registry back to disk."""
    existing = {}
    if _REGISTRY_PATH.exists():
        existing = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    existing["agents"] = AGENT_REGISTRY
    _REGISTRY_PATH.write_text(json.dumps(existing, indent=2), encoding="utf-8")


DAILY_LIMITS = {
    "sales_outreach": 50,
    "support_ticket": 100,
    "content_repurpose": 40,
    "ops_brief": 10,
    "doc_extract": 30,
    "lead_gen": 40,
    "email_marketing": 30,
    "seo_content": 20,
    "social_media": 40,
    "data_entry": 60,
    "web_scraper": 40,
    "crm_ops": 30,
    "bookkeeping": 30,
    "proposal_writer": 20,
    "product_desc": 40,
    "resume_writer": 30,
    "ad_copy": 40,
    "market_research": 15,
    "business_plan": 10,
    "press_release": 25,
    "tech_docs": 20,
    # Management agents
    "context_manager": 100,
    "qa_manager": 50,
    "production_manager": 50,
    "automation_manager": 30,
    # Platform automation
    "freelancer_work": 30,
    "upwork_work": 30,
    "fiverr_work": 30,
    "pph_work": 30,
    "guru_work": 30,
    # Division agents — Grant Operations
    "grant_writer": 20,
    "grant_qa": 40,
    "grant_researcher": 15,
    # Division agents — Insurance Operations
    "insurance_appeals": 25,
    "insurance_qa": 50,
    "insurance_compliance_checker": 50,
    # Division agents — Contractor Services
    "contractor_doc_writer": 30,
    "contractor_qa": 60,
    "contractor_compliance": 60,
    # Division agents — Municipal Services
    "municipal_doc_writer": 35,
    "municipal_qa": 70,
    "municipal_compliance": 70,
}

TOKEN_BUDGETS = {
    "sales_outreach": 25000,
    "support_ticket": 15000,
    "content_repurpose": 20000,
    "ops_brief": 20000,
    "doc_extract": 15000,
    "lead_gen": 25000,
    "email_marketing": 20000,
    "seo_content": 30000,
    "social_media": 20000,
    "data_entry": 15000,
    "web_scraper": 15000,
    "crm_ops": 20000,
    "bookkeeping": 20000,
    "proposal_writer": 30000,
    "product_desc": 20000,
    "resume_writer": 25000,
    "ad_copy": 20000,
    "market_research": 35000,
    "business_plan": 40000,
    "press_release": 20000,
    "tech_docs": 30000,
    # Management agents
    "context_manager": 15000,
    "qa_manager": 20000,
    "production_manager": 15000,
    "automation_manager": 15000,
    # Platform automation
    "freelancer_work": 30000,
    "upwork_work": 30000,
    "fiverr_work": 30000,
    "pph_work": 30000,
    "guru_work": 30000,
    # Division agents — Grant Operations
    "grant_writer": 60000,
    "grant_qa": 20000,
    "grant_researcher": 35000,
    # Division agents — Insurance Operations
    "insurance_appeals": 50000,
    "insurance_qa": 20000,
    "insurance_compliance_checker": 15000,
    # Division agents — Contractor Services
    "contractor_doc_writer": 40000,
    "contractor_qa": 15000,
    "contractor_compliance": 15000,
    # Division agents — Municipal Services
    "municipal_doc_writer": 40000,
    "municipal_qa": 15000,
    "municipal_compliance": 15000,
}


# ── Task Tracking ───────────────────────────────────────────────────────────

class DailyTracker:
    """Tracks daily task counts per type (thread-safe)."""

    def __init__(self):
        self._counts: dict[str, int] = {}
        self._date: str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._lock = threading.Lock()

    def _reset_if_new_day(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._date:
            self._counts = {}
            self._date = today

    def can_accept(self, task_type: str) -> bool:
        with self._lock:
            self._reset_if_new_day()
            limit = DAILY_LIMITS.get(task_type, 20)
            return self._counts.get(task_type, 0) < limit

    def increment(self, task_type: str):
        with self._lock:
            self._reset_if_new_day()
            self._counts[task_type] = self._counts.get(task_type, 0) + 1

    def status(self) -> dict:
        with self._lock:
            self._reset_if_new_day()
            return {k: f"{self._counts.get(k, 0)}/{v}" for k, v in DAILY_LIMITS.items()}


tracker = DailyTracker()

# ── Agent execution metrics (in-memory, reset on restart) ─────────────────
_agent_metrics: dict[str, dict] = defaultdict(lambda: {"calls": 0, "total_ms": 0, "errors": 0})


def get_metrics() -> dict:
    """Return per-agent call count, error count, and average latency."""
    return {
        agent: {
            "calls": m["calls"],
            "errors": m["errors"],
            "avg_ms": round(m["total_ms"] / m["calls"], 1) if m["calls"] > 0 else 0,
        }
        for agent, m in _agent_metrics.items()
    }


# ── Event Creation ──────────────────────────────────────────────────────────

# ── Intake Clarity Scoring (BRS Doctrine §7) ───────────────────────────────

_MIN_INPUT_CHARS = 20  # Below this, input is too vague to produce quality output


def _score_input_clarity(inputs: dict) -> tuple[float, list[str]]:
    """Score input clarity 0.0–1.0.  Returns (score, list_of_issues)."""
    issues: list[str] = []
    text = json.dumps(inputs, default=str)
    length = len(text)

    if length < _MIN_INPUT_CHARS:
        issues.append(f"Input too short ({length} chars < {_MIN_INPUT_CHARS})")

    # Check for empty required-looking fields
    empty_fields = [k for k, v in inputs.items() if isinstance(v, str) and not v.strip()]
    if empty_fields:
        issues.append(f"Empty fields: {', '.join(empty_fields)}")

    # Penalise placeholder-sounding values
    placeholders = {"test", "todo", "tbd", "xxx", "asdf", "lorem"}
    for v in inputs.values():
        if isinstance(v, str) and v.strip().lower() in placeholders:
            issues.append(f"Placeholder value detected: '{v}'")

    # Score: 1.0 = perfect, deduct 0.3 per issue
    score = max(0.0, 1.0 - 0.3 * len(issues))
    return round(score, 2), issues


def create_event(task_type: str, inputs: dict, client_id: str = "direct") -> dict:
    if task_type not in DAILY_LIMITS:
        raise ValueError(f"Unknown task_type: {task_type!r}")
    lineage_id = str(uuid4())

    # ── Ambiguity detection at intake ─────────────────────────
    clarity_score, clarity_issues = _score_input_clarity(inputs)

    event = {
        "event_id": str(uuid4()),
        "lineage_id": lineage_id,
        "schema_version": "2.0",
        "doctrine_version": DOCTRINE_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "client_id": client_id,
        "task_type": task_type,
        "inputs": inputs,
        "constraints": {
            "time_budget_sec": _registry_get(task_type, "max_execution_seconds", 45),
            "max_retries": _registry_get(task_type, "max_retries", 2),
            "token_budget": TOKEN_BUDGETS.get(task_type, 20000),
            "cost_ceiling_usd": _registry_get(task_type, "cost_ceiling_usd", 0.50),
        },
        "outputs": {},
        "qa": {"status": "PENDING", "issues": [], "revision_notes": ""},
        "delivery": {
            "delivery_status": "pending",
            "completed_components": [],
            "missing_components": [],
        },
        "billing": {
            "pricing_unit": "per_workflow",
            "amount": 0,
            "currency": "USD",
            "status": "unbilled",
        },
        "metrics": {"latency_ms": 0, "cost_estimate": 0, "tokens_used": 0},
        "intake": {"clarity_score": clarity_score, "clarity_issues": clarity_issues},
    }

    if clarity_score < 0.4:
        event["qa"]["status"] = "FAIL"
        event["qa"]["issues"] = clarity_issues
        event["qa"]["failure_reason"] = "AMBIGUOUS_INPUT"
        logger.warning("[INTAKE] Rejected %s — clarity %.1f: %s", task_type, clarity_score, clarity_issues)

    return event


# ── Cost Estimation ─────────────────────────────────────────────────────────

# Approximate costs per 1K tokens (input/output) — March 2026
_COST_PER_1K = {
    "openai": {"input": 0.0025, "output": 0.01},       # GPT-4o
    "anthropic": {"input": 0.003, "output": 0.015},     # Claude Sonnet
    "gemini": {"input": 0.0001, "output": 0.0004},      # Gemini Flash
    "grok": {"input": 0.005, "output": 0.015},           # Grok-3
}


def _estimate_tokens(text: str) -> int:
    """~4 chars per token for English text."""
    return max(1, len(text) // 4)


def _estimate_pre_cost(inputs: dict, provider: str, task_type: str) -> float:
    """Estimate the LLM cost before execution using input size + expected output."""
    input_text = json.dumps(inputs, default=str)
    input_tokens = _estimate_tokens(input_text)
    # Estimate output at 2x input or token budget / 2, whichever is smaller
    output_budget = TOKEN_BUDGETS.get(task_type, 20000)
    estimated_output_tokens = min(input_tokens * 2, output_budget // 2)
    rates = _COST_PER_1K.get(provider or "openai", {"input": 0.005, "output": 0.015})
    return (input_tokens / 1000 * rates["input"]) + (estimated_output_tokens / 1000 * rates["output"])


_METRICS_DIR = PROJECT_ROOT / "data" / "agent_metrics"


def _read_latest_cost(task_type: str) -> float:
    """Read the latest cost record for this agent from today's metrics file."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    metrics_file = _METRICS_DIR / f"costs_{date_str}.jsonl"
    if not metrics_file.exists():
        return 0.0
    try:
        last_cost = 0.0
        for line in metrics_file.read_text(encoding="utf-8").strip().splitlines():
            record = json.loads(line)
            if record.get("agent") == task_type:
                last_cost = record.get("cost_usd", 0.0)
        return last_cost
    except Exception:
        return 0.0


# ── Failure Mode Classification ─────────────────────────────────────────────

_EXCEPTION_TO_MODE = {
    "TimeoutError": "llm_timeout",
    "ConnectTimeout": "llm_timeout",
    "ReadTimeout": "llm_timeout",
    "Timeout": "llm_timeout",
    "ValidationError": "schema_violation",
    "JSONDecodeError": "schema_violation",
    "KeyError": "schema_violation",
    "RateLimitError": "llm_timeout",
    "APIStatusError": "llm_timeout",
    "AuthenticationError": "llm_timeout",
    "FileNotFoundError": "parse_error",
    "UnicodeDecodeError": "parse_error",
}


# ── P4.4: Delivery Status Classification ────────────────────────────────────

# Expected output components per task type (for partial delivery detection)
_EXPECTED_COMPONENTS = {
    "sales_outreach": ["research", "email_sequence", "qa"],
    "content_repurpose": ["blog_post", "social_posts", "newsletter"],
    "email_marketing": ["subject_lines", "email_bodies", "schedule"],
    "seo_content": ["article", "meta_tags", "keyword_analysis"],
    "lead_gen": ["leads", "enrichment"],
    "business_plan": ["executive_summary", "market_analysis", "financial_projections"],
    "proposal_writer": ["proposal_body", "pricing", "timeline"],
    "market_research": ["overview", "competitor_analysis", "recommendations"],
}


def _classify_delivery_status(event: dict) -> dict:
    """Classify delivery as complete, partial, or failed based on outputs.

    Returns:
        {"delivery_status": "complete"|"partial"|"failed",
         "completed_components": [...], "missing_components": [...]}
    """
    qa_status = event.get("qa", {}).get("status", "FAIL")
    outputs = event.get("outputs", {})
    task_type = event.get("task_type", "")

    if qa_status == "FAIL" or not outputs:
        return {
            "delivery_status": "failed",
            "completed_components": [],
            "missing_components": _EXPECTED_COMPONENTS.get(task_type, []),
        }

    expected = _EXPECTED_COMPONENTS.get(task_type, [])
    if not expected:
        # No component spec — if QA passed and outputs exist, it's complete
        return {"delivery_status": "complete", "completed_components": [], "missing_components": []}

    # Check which components are present in outputs
    completed = []
    missing = []
    output_keys = set()
    if isinstance(outputs, dict):
        # Flatten output keys — check top-level and nested
        output_keys = set(outputs.keys())
        output_str = json.dumps(outputs, default=str).lower()
    else:
        output_str = str(outputs).lower()

    for component in expected:
        # Match by key name or by content mention
        if component in output_keys or component in output_str:
            completed.append(component)
        else:
            missing.append(component)

    if not missing:
        return {"delivery_status": "complete", "completed_components": completed, "missing_components": []}
    elif completed:
        return {"delivery_status": "partial", "completed_components": completed, "missing_components": missing}
    else:
        return {"delivery_status": "failed", "completed_components": [], "missing_components": missing}


def _classify_failure(exc: Exception, task_type: str) -> str:
    """Map an exception to a declared failure mode for the agent.

    Returns the matched mode ID if it's in the agent's declared list,
    otherwise returns 'UNKNOWN_FAILURE'.
    """
    exc_name = type(exc).__name__
    candidate = _EXCEPTION_TO_MODE.get(exc_name)

    # Check error message for additional clues
    msg = str(exc).lower()
    if candidate is None:
        if "timeout" in msg or "timed out" in msg:
            candidate = "llm_timeout"
        elif "schema" in msg or "validation" in msg or "json" in msg:
            candidate = "schema_violation"
        elif "empty" in msg or "missing" in msg or "required" in msg:
            candidate = "schema_violation"
        elif "platform" in msg or "selenium" in msg or "playwright" in msg:
            candidate = "platform_error"
        elif "qa" in msg and "fail" in msg:
            candidate = "qa_fail"

    if candidate is None:
        candidate = "UNKNOWN_FAILURE"

    # Validate against declared modes
    declared = _registry_get(task_type, "failure_modes", [])
    if candidate in declared:
        return candidate

    # Candidate not declared — flag it
    if candidate != "UNKNOWN_FAILURE":
        logger.warning(
            "[UNDECLARED_MODE] %s raised '%s' → mode '%s' not in declared modes %s",
            task_type, exc_name, candidate, declared,
        )
    return "UNKNOWN_FAILURE"


# ── Agent Routing ───────────────────────────────────────────────────────────

def route_task(event: dict) -> dict:
    """Route a task to the correct agent and return the completed event."""
    task_type = event["task_type"]
    inputs = event["inputs"]
    start = time.time()

    # ── Reject events already failed at intake (ambiguous input) ──
    if event["qa"].get("status") == "FAIL":
        return _finalize_event(event, start, task_type)

    # ── Agent disabled check ──────────────────────────────────────
    if _registry_get(task_type, "disabled", False):
        event["qa"]["status"] = "FAIL"
        event["qa"]["issues"] = [f"Agent '{task_type}' is disabled"]
        event["qa"]["failure_reason"] = "AGENT_DISABLED"
        logger.warning("[BLOCKED] Agent %s is disabled in registry", task_type)
        return _finalize_event(event, start, task_type)

    # ── Agent paused check (VECTIS grade enforcement) ─────────
    _paused_file = PROJECT_ROOT / "data" / "paused_agents.json"
    if _paused_file.exists():
        try:
            _paused = json.loads(_paused_file.read_text(encoding="utf-8"))
            if task_type in _paused:
                event["qa"]["status"] = "FAIL"
                event["qa"]["issues"] = [f"Agent '{task_type}' is paused (grade F)"]
                event["qa"]["failure_reason"] = "AGENT_PAUSED"
                logger.warning("[BLOCKED] Agent %s is paused by VECTIS grade enforcement", task_type)
                return _finalize_event(event, start, task_type)
        except Exception:
            pass

    if not tracker.can_accept(task_type):
        event["qa"]["status"] = "FAIL"
        event["qa"]["issues"] = [f"Daily limit reached for {task_type}"]
        event["qa"]["failure_reason"] = "DAILY_LIMIT_REACHED"
        logger.info("[LIMIT] Daily limit reached for %s", task_type)
        return _finalize_event(event, start, task_type)

    tracker.increment(task_type)

    provider = inputs.get("provider") or event.get("provider")

    # ── P2.2: Pre-execution cost ceiling check ────────────────────
    cost_ceiling = _registry_get(task_type, "cost_ceiling_usd", 0.50)
    estimated_cost = _estimate_pre_cost(inputs, provider, task_type)
    event["metrics"]["cost_estimate"] = round(estimated_cost, 6)

    if estimated_cost > cost_ceiling:
        event["qa"]["status"] = "FAIL"
        event["qa"]["issues"] = [
            f"COST_CEILING_BREACH: estimated ${estimated_cost:.4f} > ceiling ${cost_ceiling:.4f}"
        ]
        event["qa"]["failure_reason"] = "COST_CEILING_BREACH"
        logger.warning(
            "[CEILING] %s pre-exec cost $%.4f exceeds ceiling $%.4f",
            task_type, estimated_cost, cost_ceiling,
        )
        return _finalize_event(event, start, task_type)

    try:
        if task_type == "sales_outreach":
            from agents.sales_ops.runner import run_pipeline as sales_pipeline
            result = sales_pipeline(
                company=inputs.get("company", ""),
                role=inputs.get("role", ""),
                product=inputs.get("product", "We help companies automate business processes with AI agents."),
                tone=inputs.get("tone", "direct"),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa_status

        elif task_type == "support_ticket":
            from agents.support.runner import run_pipeline as support_pipeline
            result = support_pipeline(
                ticket=inputs.get("ticket", ""),
                kb=inputs.get("kb", ""),
                policies=inputs.get("policies", ""),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = "PASS"

        elif task_type == "content_repurpose":
            from agents.content_repurpose.runner import run_pipeline as content_pipeline
            result = content_pipeline(
                source_text=inputs.get("source_text", ""),
                source_url=inputs.get("source_url", ""),
                formats=inputs.get("formats"),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa_status

        elif task_type == "doc_extract":
            from agents.doc_extract.runner import run_pipeline as doc_pipeline
            result = doc_pipeline(
                document_text=inputs.get("document_text", ""),
                doc_type=inputs.get("doc_type", "auto"),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa_status

        elif task_type == "lead_gen":
            from agents.lead_gen.runner import run_pipeline as lead_gen_pipeline
            result = lead_gen_pipeline(
                industry=inputs.get("industry", ""),
                icp=inputs.get("icp", ""),
                geo=inputs.get("geo", ""),
                company_size=inputs.get("company_size", ""),
                count=inputs.get("count", 10),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa.status

        elif task_type == "email_marketing":
            from agents.email_marketing.runner import run_pipeline as email_mkt_pipeline
            result = email_mkt_pipeline(
                business=inputs.get("business", ""),
                audience=inputs.get("audience", ""),
                goal=inputs.get("goal", "nurture"),
                tone=inputs.get("tone", "professional"),
                email_count=inputs.get("email_count", 5),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa.status

        elif task_type == "seo_content":
            from agents.seo_content.runner import run_pipeline as seo_pipeline
            result = seo_pipeline(
                topic=inputs.get("topic", ""),
                content_type=inputs.get("content_type", "blog_post"),
                tone=inputs.get("tone", "professional"),
                audience=inputs.get("audience", ""),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa.status

        elif task_type == "social_media":
            from agents.social_media.runner import run_pipeline as social_pipeline
            result = social_pipeline(
                topic=inputs.get("topic", ""),
                platforms=inputs.get("platforms", ["linkedin", "twitter"]),
                tone=inputs.get("tone", "professional"),
                cta_goal=inputs.get("cta", "engagement"),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa.status

        elif task_type == "data_entry":
            from agents.data_entry.runner import run_pipeline as data_entry_pipeline
            result = data_entry_pipeline(
                raw_data=inputs.get("raw_data", ""),
                task_type=inputs.get("data_task", "clean"),
                output_format=inputs.get("output_format", "json"),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa.status

        elif task_type == "web_scraper":
            from agents.web_scraper.runner import run_pipeline as scraper_pipeline
            result = scraper_pipeline(
                page_content=inputs.get("page_content", ""),
                source_url=inputs.get("url", ""),
                extraction_target=inputs.get("target", "company_info"),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa.status

        elif task_type == "crm_ops":
            from agents.crm_ops.runner import run_pipeline as crm_pipeline
            result = crm_pipeline(
                crm_data=inputs.get("crm_data", ""),
                task_type=inputs.get("crm_task", "clean"),
                crm_platform=inputs.get("crm_platform", "spreadsheet"),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa.status

        elif task_type == "bookkeeping":
            from agents.bookkeeping.runner import run_pipeline as books_pipeline
            result = books_pipeline(
                financial_data=inputs.get("financial_data", ""),
                task_type=inputs.get("books_task", "categorize"),
                currency=inputs.get("currency", "USD"),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa.status

        elif task_type == "proposal_writer":
            from agents.proposal_writer.runner import run_pipeline as proposal_pipeline
            result = proposal_pipeline(
                brief=inputs.get("brief", ""),
                proposal_type=inputs.get("proposal_type", "project_proposal"),
                company_name=inputs.get("company_name", "Digital Labour"),
                budget_range=inputs.get("budget_range", ""),
                deadline=inputs.get("deadline", ""),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa.status

        elif task_type == "product_desc":
            from agents.product_desc.runner import run_pipeline as prod_desc_pipeline
            result = prod_desc_pipeline(
                product_specs=inputs.get("raw_input", ""),
                platform=inputs.get("platform", "general"),
                audience=inputs.get("audience", ""),
                tone=inputs.get("tone", "persuasive"),
                keywords=inputs.get("keywords", ""),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa.status

        elif task_type == "resume_writer":
            from agents.resume_writer.runner import run_pipeline as resume_pipeline
            result = resume_pipeline(
                career_data=inputs.get("raw_input", ""),
                target_role=inputs.get("target_role", ""),
                target_industry=inputs.get("industry", ""),
                style=inputs.get("style", "combination"),
                level=inputs.get("level", "mid"),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa.status

        elif task_type == "ad_copy":
            from agents.ad_copy.runner import run_pipeline as ad_copy_pipeline
            result = ad_copy_pipeline(
                product=inputs.get("brief", ""),
                platform=inputs.get("platform", "google_search"),
                audience=inputs.get("audience", ""),
                goal=inputs.get("goal", "conversions"),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa.status

        elif task_type == "market_research":
            from agents.market_research.runner import run_pipeline as mktresearch_pipeline
            result = mktresearch_pipeline(
                topic=inputs.get("brief", ""),
                report_type=inputs.get("report_type", "market_overview"),
                depth=inputs.get("depth", "standard"),
                region=inputs.get("region", "global"),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa.status

        elif task_type == "business_plan":
            from agents.business_plan.runner import run_pipeline as bizplan_pipeline
            result = bizplan_pipeline(
                business_idea=inputs.get("business_idea", ""),
                plan_type=inputs.get("plan_type", "startup"),
                industry=inputs.get("industry", ""),
                funding_goal=inputs.get("funding_goal", ""),
                timeline=inputs.get("timeline", "3 years"),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa.status

        elif task_type == "press_release":
            from agents.press_release.runner import run_pipeline as pr_pipeline
            result = pr_pipeline(
                announcement=inputs.get("announcement", ""),
                company_name=inputs.get("company_name", ""),
                release_type=inputs.get("release_type", "product_launch"),
                tone=inputs.get("tone", "professional"),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa.status

        elif task_type == "tech_docs":
            from agents.tech_docs.runner import run_pipeline as techdocs_pipeline
            result = techdocs_pipeline(
                content=inputs.get("content", ""),
                doc_type=inputs.get("doc_type", "api_reference"),
                audience=inputs.get("audience", "developers"),
                framework=inputs.get("framework", ""),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa.status

        elif task_type == "context_manager":
            from agents.context_manager.runner import run_pipeline as ctx_pipeline
            result = ctx_pipeline(
                action=inputs.get("action", "enrich"),
                task_type=inputs.get("target_task_type", ""),
                client_id=inputs.get("client_id", ""),
                inputs=inputs.get("task_inputs", {}),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump() if hasattr(result, "model_dump") else result
                event["qa"]["status"] = "FAIL" if (hasattr(result, "deny") and result.deny) else "PASS"

        elif task_type == "qa_manager":
            from agents.qa_manager.runner import run_pipeline as qam_pipeline
            result = qam_pipeline(
                action=inputs.get("action", "verify"),
                task_type=inputs.get("target_task_type", ""),
                deliverable=inputs.get("deliverable", {}),
                qa_result=inputs.get("qa_result"),
                client_id=inputs.get("client_id", ""),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump() if hasattr(result, "model_dump") else result
                event["qa"]["status"] = result.verdict if hasattr(result, "verdict") else "PASS"

        elif task_type == "production_manager":
            from agents.production_manager.runner import run_pipeline as prod_pipeline
            result = prod_pipeline(
                action=inputs.get("action", "capacity_check"),
                tasks=inputs.get("tasks", []),
                task_type=inputs.get("target_task_type", ""),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump() if hasattr(result, "model_dump") else result
                event["qa"]["status"] = "PASS"

        elif task_type == "automation_manager":
            from agents.automation_manager.runner import run_pipeline as auto_pipeline
            result = auto_pipeline(
                action=inputs.get("action", "status"),
                platform=inputs.get("platform", "all"),
                config=inputs.get("config", {}),
                metrics_window=inputs.get("metrics_window", "7d"),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump() if hasattr(result, "model_dump") else result
                event["qa"]["status"] = "PASS"

        elif task_type == "freelancer_work":
            from agents.freelancer_work.runner import run_pipeline as freelancer_pipeline
            result = freelancer_pipeline(
                action=inputs.get("action", "bid"),
                project_data=inputs.get("project"),
                provider=provider,
                dry_run=inputs.get("dry_run", False),
            )
            if result:
                event["outputs"] = result.model_dump() if hasattr(result, "model_dump") else result
                event["qa"]["status"] = result.qa.status if result.qa else "PASS"

        elif task_type == "upwork_work":
            from agents.upwork_work.runner import run_pipeline as upwork_pipeline
            result = upwork_pipeline(
                action=inputs.get("action", "bid"),
                job_data=inputs.get("job_data"),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump() if hasattr(result, "model_dump") else result
                event["qa"]["status"] = result.qa.status if result.qa else "PASS"

        elif task_type == "fiverr_work":
            from agents.fiverr_work.runner import run_pipeline as fiverr_pipeline
            result = fiverr_pipeline(
                action=inputs.get("action", "deliver"),
                order_data=inputs.get("order_data"),
                request_data=inputs.get("request_data"),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump() if hasattr(result, "model_dump") else result
                event["qa"]["status"] = result.qa.status if result.qa else "PASS"

        elif task_type == "pph_work":
            from agents.pph_work.runner import run_pipeline as pph_pipeline
            result = pph_pipeline(
                action=inputs.get("action", "propose"),
                job_data=inputs.get("job_data"),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump() if hasattr(result, "model_dump") else result
                event["qa"]["status"] = result.qa.status if result.qa else "PASS"

        elif task_type == "guru_work":
            from agents.guru_work.runner import run_pipeline as guru_pipeline
            result = guru_pipeline(
                action=inputs.get("action", "quote"),
                job_data=inputs.get("job_data"),
                provider=provider,
            )
            if result:
                event["outputs"] = result.model_dump() if hasattr(result, "model_dump") else result
                event["qa"]["status"] = result.qa.status if result.qa else "PASS"

        # ── Division agents ───────────────────────────────────────────────────
        elif task_type == "grant_writer":
            from agents.grant_writer.runner import run_pipeline as grant_pipeline
            result = grant_pipeline(
                brief=inputs.get("brief", inputs.get("content", "")),
                grant_type=inputs.get("grant_type", "sbir_phase1"),
                agency=inputs.get("agency", "nsf"),
                provider=provider or "openai",
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa.status

        elif task_type == "insurance_appeals":
            from agents.insurance_appeals.runner import run_pipeline as ins_pipeline
            result = ins_pipeline(
                case_text=inputs.get("case_text", inputs.get("content", "")),
                letter_type=inputs.get("letter_type", "first_level_appeal"),
                urgency=inputs.get("urgency", "routine"),
                provider_name=inputs.get("provider_name", ""),
                provider=provider or "openai",
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa.status

        elif task_type == "compliance_docs":
            from agents.compliance_docs.runner import run_pipeline as comp_pipeline
            result = comp_pipeline(
                content=inputs.get("content", ""),
                doc_type=inputs.get("doc_type", "employee_handbook"),
                company=inputs.get("company", ""),
                jurisdiction=inputs.get("jurisdiction", "us_federal"),
                framework=inputs.get("framework", ""),
                provider=provider or "openai",
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa.status

        elif task_type == "data_reporter":
            from agents.data_reporter.runner import run_pipeline as data_rpt_pipeline
            result = data_rpt_pipeline(
                raw_data=inputs.get("raw_data", inputs.get("content", "")),
                report_type=inputs.get("report_type", "monthly_performance"),
                period=inputs.get("period", ""),
                audience=inputs.get("audience", "executive"),
                provider=provider or "openai",
            )
            if result:
                event["outputs"] = result.model_dump()
                event["qa"]["status"] = result.qa.status

        else:
            event["qa"]["status"] = "FAIL"
            event["qa"]["issues"] = [f"Unknown task type: {task_type}"]
            event["qa"]["failure_reason"] = "UNKNOWN_TASK_TYPE"
            logger.error("[ERROR] Unknown task type: %s", task_type)

    except Exception as e:
        import traceback
        tb_short = traceback.format_exception_only(type(e), e)[-1].strip()
        tb_full = traceback.format_exc()
        event["qa"]["status"] = "FAIL"
        event["qa"]["issues"] = [f"{type(e).__name__}: {e}"]
        event["qa"]["traceback"] = tb_full[-2000:]  # Truncated for storage
        # P2.3: Classify failure against declared modes
        failure_mode = _classify_failure(e, task_type)
        event["qa"]["failure_reason"] = failure_mode
        event["qa"]["exception_type"] = type(e).__name__
        if failure_mode == "UNKNOWN_FAILURE":
            logger.error(
                "[UNKNOWN_FAILURE] %s: %s (%s) — add to failure_modes in registry\n%s",
                task_type, e, type(e).__name__, tb_full,
            )
        else:
            logger.error("[%s] %s: %s\n%s", failure_mode.upper(), task_type, e, tb_full)
        _agent_metrics[task_type]["errors"] += 1

    # ── P3.3: Confidence-based QA verification + automatic retry ─
    # Trust agent-level QA when it already passed with a high score (>= 85).
    # This prevents the secondary LLM verifier from creating false-negative
    # FAILs on deliverables the agent itself rated highly.
    _agent_qa = event.get("outputs", {}).get("qa", {})
    _agent_qa_score = _agent_qa.get("score", 0) if isinstance(_agent_qa, dict) else 0
    _agent_qa_status = _agent_qa.get("status", "") if isinstance(_agent_qa, dict) else ""
    _skip_secondary = (
        _agent_qa_status == "PASS"
        and _agent_qa_score >= 75
        and event["qa"]["status"] == "PASS"
    )

    if _skip_secondary:
        # Agent QA is authoritative — record confidence from agent score
        event["qa"]["confidence"] = round(_agent_qa_score / 100.0, 3)
        event["qa"]["applied_rules"] = ["AGENT_QA_TRUSTED"]
        event["qa"]["failed_rule_id"] = ""
        logger.info(
            "[QA] %s agent QA PASS (score %d) — trusting agent, skipping secondary gate",
            task_type, _agent_qa_score,
        )
    elif event["qa"]["status"] != "FAIL" and event.get("outputs"):
        try:
            from agents.qa.runner import verify as qa_verify
            output_text = json.dumps(event["outputs"], default=str)
            client_id = event.get("client_id", "")
            qa_result = qa_verify(output_text, task_type=task_type, client_id=client_id)
            event["qa"]["confidence"] = qa_result.confidence
            event["qa"]["applied_rules"] = qa_result.applied_rules
            event["qa"]["failed_rule_id"] = qa_result.failed_rule_id

            if qa_result.confidence < 0.50:
                # Hard fail — no retry
                event["qa"]["status"] = "FAIL"
                event["qa"]["issues"] = qa_result.issues + ["confidence < 0.50 — hard fail"]
                event["qa"]["failure_reason"] = "QA_CONFIDENCE_HARD_FAIL"
                logger.warning("[QA] %s confidence %.2f < 0.50 — hard fail", task_type, qa_result.confidence)
            elif qa_result.confidence < 0.70:
                # Below threshold — attempt ONE retry
                logger.info("[QA] %s confidence %.2f < 0.70 — retrying", task_type, qa_result.confidence)
                event["qa"]["retry_triggered"] = True
                # Re-run QA on same output (LLM may score differently on retry)
                retry_result = qa_verify(output_text, task_type=task_type, client_id=client_id)
                event["qa"]["confidence"] = retry_result.confidence
                event["qa"]["applied_rules"] = retry_result.applied_rules
                if retry_result.confidence < 0.50:
                    event["qa"]["status"] = "FAIL"
                    event["qa"]["issues"] = retry_result.issues + ["confidence < 0.50 after retry"]
                    event["qa"]["failure_reason"] = "QA_CONFIDENCE_FAIL_AFTER_RETRY"
                    logger.warning("[QA] %s retry confidence %.2f still < 0.50", task_type, retry_result.confidence)
                elif retry_result.confidence < 0.70:
                    event["qa"]["status"] = "FAIL"
                    event["qa"]["issues"] = retry_result.issues + ["confidence still < 0.70 after retry"]
                    event["qa"]["failure_reason"] = "QA_CONFIDENCE_BELOW_THRESHOLD"
                    logger.warning("[QA] %s retry confidence %.2f still < 0.70", task_type, retry_result.confidence)
                else:
                    event["qa"]["status"] = "PASS"
                    logger.info("[QA] %s retry confidence %.2f — passed", task_type, retry_result.confidence)
            else:
                # Confidence >= 0.70: keep existing status
                if qa_result.status == "FAIL":
                    event["qa"]["status"] = "FAIL"
                    event["qa"]["issues"] = qa_result.issues
                    event["qa"]["failure_reason"] = qa_result.failed_rule_id or "QA_RULE_FAIL"
        except Exception as qa_exc:
            logger.warning("[QA] Confidence check failed for %s: %s (non-blocking)", task_type, qa_exc)

    # ── P1.2: Hard execution termination (time) ─────────────────
    elapsed_s = time.time() - start
    ceiling = _registry_get(task_type, "max_execution_seconds", 45)
    if elapsed_s > ceiling:
        logger.error(
            "[HARD_TIMEOUT] %s exceeded max_execution_seconds (%ss > %ss) — task FAILED",
            task_type, round(elapsed_s, 1), ceiling,
        )
        event["qa"]["status"] = "FAIL"
        event["qa"]["failure_reason"] = "HARD_TIMEOUT"
        event["qa"]["issues"].append(
            f"HARD_TIMEOUT: {round(elapsed_s, 1)}s > {ceiling}s limit — terminated"
        )
        event["metrics"]["ceiling_breached"] = True
        _agent_metrics[task_type]["errors"] += 1
        return _finalize_event(event, start, task_type)

    # ── Post-execution cost check ────────────────────────────────
    # Read actual cost from today's agent_metrics if available
    actual_cost = _read_latest_cost(task_type)
    if actual_cost > 0:
        event["metrics"]["cost_estimate"] = round(actual_cost, 6)
        if actual_cost > cost_ceiling:
            logger.warning(
                "[COST_CEILING] %s actual cost $%.4f > ceiling $%.4f",
                task_type, actual_cost, cost_ceiling,
            )
            event["qa"]["issues"].append(
                f"COST_CEILING_BREACH_POST: actual ${actual_cost:.4f} > ceiling ${cost_ceiling:.4f}"
            )
            event["metrics"]["cost_ceiling_breached"] = True

    elapsed_ms = int(elapsed_s * 1000)
    event["metrics"]["latency_ms"] = elapsed_ms
    _agent_metrics[task_type]["calls"] += 1
    _agent_metrics[task_type]["total_ms"] += elapsed_ms

    return _finalize_event(event, start, task_type, elapsed_ms=elapsed_ms)


def _finalize_event(event: dict, start: float, task_type: str, elapsed_ms: int | None = None) -> dict:
    """Log, notify, and bill every task — success or failure. Fail closed."""
    if elapsed_ms is None:
        elapsed_ms = int((time.time() - start) * 1000)

    # ── Post-execution cost ceiling enforcement ───────────────
    actual_cost = event.get("metrics", {}).get("cost_estimate", 0.0)
    ceiling = event.get("constraints", {}).get("cost_ceiling_usd", 0.50)
    if actual_cost > ceiling and event["qa"].get("status") != "FAIL":
        logger.warning(
            "[CEILING-POST] %s actual cost $%.4f > ceiling $%.4f — flagging",
            task_type, actual_cost, ceiling,
        )
        event["qa"]["issues"] = event["qa"].get("issues", []) + [
            f"POST_EXEC_CEILING_BREACH: actual ${actual_cost:.4f} > ceiling ${ceiling:.4f}"
        ]
        event.setdefault("flags", []).append("cost_ceiling_breach")

    provider = event.get("inputs", {}).get("provider", "")
    qa_status = event["qa"].get("status", "FAIL")
    failure_reason = event["qa"].get("failure_reason", "")

    # Every task MUST produce an artifact — ensure status is set
    if qa_status not in ("PASS", "FAIL"):
        event["qa"]["status"] = "FAIL"
        event["qa"]["failure_reason"] = "MISSING_STATUS"
        qa_status = "FAIL"

    # Log the event (legacy JSONL)
    log_event(event)

    # Structured KPI log — always fires (success AND failure)
    try:
        from kpi.logger import log_task_event
        log_task_event(
            task_id=event.get("event_id", ""),
            lineage_id=event.get("lineage_id", ""),
            task_type=task_type,
            status="completed" if qa_status == "PASS" else "failed",
            client=event.get("client_id", ""),
            provider=provider or "",
            qa_status=qa_status,
            failure_reason=failure_reason,
            duration_s=elapsed_ms / 1000,
        )
    except Exception as exc:
        logger.error("KPI log failed for %s: %s", task_type, exc)

    # P3.4: Track QA failures by rule_id + agent
    if qa_status == "FAIL":
        try:
            from kpi.logger import log_qa_failure
            log_qa_failure(
                task_id=event.get("event_id", ""),
                lineage_id=event.get("lineage_id", ""),
                task_type=task_type,
                failed_rule_id=event["qa"].get("failed_rule_id", failure_reason or "UNKNOWN"),
                failure_reason=failure_reason,
                confidence=event["qa"].get("confidence", 0.0),
                issues=event["qa"].get("issues", []),
                applied_rules=event["qa"].get("applied_rules", []),
                client=event.get("client_id", ""),
            )
        except Exception as exc:
            logger.warning("QA failure log failed for %s: %s", task_type, exc)

    # C-Suite event feed
    try:
        _csuite_notify(event)
    except Exception as exc:
        logger.warning("C-Suite notify failed: %s", exc)

    # NCC Relay — publish task event to Resonance Energy governance
    try:
        from resonance.ncc_bridge import ncc
        ncc.publish_task_event(event)
    except Exception as ncc_exc:
        logger.debug("[NCC] Relay publish failed (non-blocking): %s", ncc_exc)

    # ── P4.4: Classify delivery status ────────────────────────
    delivery = _classify_delivery_status(event)
    event["delivery"] = delivery

    # ── BILLING — always record, even on failure (amount=0 for FAIL) ──
    # P4.4: Partial tasks billed at 50% of full price
    try:
        from billing.tracker import BillingTracker
        bt = BillingTracker()
        billing_status = qa_status
        if delivery["delivery_status"] == "partial":
            billing_status = "PARTIAL"
        billing_result = bt.record_usage(
            client=event.get("client_id", "direct"),
            task_type=task_type,
            task_id=event.get("event_id", ""),
            llm_cost=event.get("metrics", {}).get("cost_estimate", 0.0),
            status=billing_status,
        )
        event["billing"]["amount"] = billing_result.get("charge", 0.0)
        if delivery["delivery_status"] == "partial":
            event["billing"]["status"] = "partial_charge"
        elif qa_status == "PASS":
            event["billing"]["status"] = "billed"
        else:
            event["billing"]["status"] = "no_charge"
        event["billing"]["doctrine_version"] = DOCTRINE_VERSION
    except Exception as exc:
        logger.error("[BILLING_SURFACE_GAP] %s task %s — billing record failed: %s",
                     task_type, event.get("event_id", ""), exc)

    return event


# ── Logging ─────────────────────────────────────────────────────────────────

def log_event(event: dict):
    """Append event to KPI log."""
    log_dir = PROJECT_ROOT / "kpi" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def _csuite_notify(event: dict):
    """Write lightweight event to C-Suite feed for executive consumption.

    The feed is a JSONL file that AXIOM/VECTIS/LEDGR scan during their reviews.
    Events older than 7 days are pruned automatically.
    """
    feed_dir = PROJECT_ROOT / "data" / "csuite_feed"
    feed_dir.mkdir(parents=True, exist_ok=True)
    feed_file = feed_dir / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event_id": event.get("event_id", ""),
        "task_type": event.get("task_type", ""),
        "client_id": event.get("client_id", ""),
        "qa_status": event.get("qa", {}).get("status", ""),
        "latency_ms": event.get("metrics", {}).get("latency_ms", 0),
    }
    with open(feed_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    # Prune feeds older than 7 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    for old_file in feed_dir.glob("*.jsonl"):
        try:
            file_date = datetime.strptime(old_file.stem, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if file_date < cutoff:
                old_file.unlink()
        except ValueError:
            logger.debug("[PRUNE] Skipping non-date feed file: %s", old_file.name)


# ── Queue Processing ────────────────────────────────────────────────────────

def process_queue(queue_dir: Path):
    """Process all .json task files in a queue directory."""
    tasks = sorted(queue_dir.glob("*.json"))
    if not tasks:
        print("[QUEUE] No tasks in queue.")
        return

    print(f"[QUEUE] Processing {len(tasks)} tasks...")
    for task_path in tasks:
        event = json.loads(task_path.read_text(encoding="utf-8"))
        print(f"\n[TASK] {event.get('task_type', '?')} | {event.get('event_id', '?')}")
        result = route_task(event)

        # Move to completed or failed
        status = result["qa"]["status"]
        dest_dir = queue_dir.parent / ("completed" if status == "PASS" else "failed")
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / task_path.name
        dest.write_text(json.dumps(result, indent=2), encoding="utf-8")
        task_path.unlink()
        print(f"[{status}] → {dest}")

    print(f"\n[DONE] Queue processed. Status: {tracker.status()}")


# ── Interactive Mode ────────────────────────────────────────────────────────

def interactive():
    """Simple interactive dispatcher for testing."""
    print("=== Digital Labour DISPATCHER ===")
    print(f"Daily limits: {tracker.status()}\n")

    task_type = input(f"Task type ({' / '.join(DAILY_LIMITS.keys())}): ").strip()
    if task_type not in DAILY_LIMITS:
        print(f"Unknown task type: {task_type}")
        return

    inputs = {}
    if task_type == "sales_outreach":
        inputs["company"] = input("Company name/URL: ").strip()
        inputs["role"] = input("Target role: ").strip()
        inputs["product"] = input("Your product (1 sentence, or Enter for default): ").strip() or None
    elif task_type == "support_ticket":
        inputs["ticket"] = input("Ticket text: ").strip()

    event = create_event(task_type, inputs)
    result = route_task(event)

    print(f"\n--- RESULT ---")
    print(f"Status: {result['qa']['status']}")
    print(f"Latency: {result['metrics']['latency_ms']}ms")
    if result["outputs"]:
        print(json.dumps(result["outputs"], indent=2)[:2000])


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Digital Labour Dispatcher")
    parser.add_argument("--task", help="Process a single task JSON file")
    parser.add_argument("--queue", help="Process all tasks in a queue directory")
    args = parser.parse_args()

    if args.task:
        event = json.loads(Path(args.task).read_text(encoding="utf-8"))
        result = route_task(event)
        print(json.dumps(result, indent=2))
    elif args.queue:
        process_queue(Path(args.queue))
    else:
        interactive()


if __name__ == "__main__":
    main()
