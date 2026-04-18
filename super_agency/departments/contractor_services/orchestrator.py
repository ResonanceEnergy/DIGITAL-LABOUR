"""Contractor Services Division Orchestrator.

Autonomous intake → dispatch → QA → delivery pipeline for contractor
documentation: permits, inspection reports, proposals, lien waivers,
safety plans, and compliance paperwork.

Circuit breaker pattern + self-healing NERVE integration.

Usage:
    from super_agency.departments.contractor_services.orchestrator import ContractorDivision
    division = ContractorDivision()
    result = await division.process(request_data)
"""

import json
import logging
import time
import threading
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from uuid import uuid4

logger = logging.getLogger("division.ctr_svc")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

def _load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to load contractor_services config: %s", e)
        return {}

CONFIG = _load_config()
AUTONOMY = CONFIG.get("autonomy_controls", {})
PRICING = CONFIG.get("pricing_tiers", {})

# ── Document type routing ──────────────────────────────────────────────────
DOC_TYPES = {
    "permit_application": {"agent": "compliance_docs", "template": "permit"},
    "inspection_report": {"agent": "data_reporter", "template": "inspection"},
    "project_proposal": {"agent": "proposal_writer", "template": "contractor_proposal"},
    "lien_waiver": {"agent": "compliance_docs", "template": "lien_waiver"},
    "safety_plan": {"agent": "compliance_docs", "template": "safety_plan"},
    "change_order": {"agent": "compliance_docs", "template": "change_order"},
    "progress_report": {"agent": "data_reporter", "template": "progress"},
    "bid_document": {"agent": "proposal_writer", "template": "bid"},
}


class DivisionTracker:
    def __init__(self, max_daily: int = 30, max_cost: float = 0.35, max_tokens: int = 450000):
        self.max_daily = max_daily
        self.max_cost = max_cost
        self.max_tokens = max_tokens
        self._count = 0
        self._cost = 0.0
        self._tokens = 0
        self._date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._lock = threading.Lock()
        self._metrics = defaultdict(lambda: {"completed": 0, "failed": 0, "revenue": 0.0, "avg_qa": 0.0, "qa_scores": []})

    def _reset_if_new_day(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._date:
            self._count = 0
            self._cost = 0.0
            self._tokens = 0
            self._date = today

    def can_accept(self) -> tuple[bool, str]:
        with self._lock:
            self._reset_if_new_day()
            if self._count >= self.max_daily:
                return False, f"Daily task limit reached ({self.max_daily})"
            return True, "ok"

    def record_task(self, cost: float, tokens: int, success: bool, qa_score: float, tier: str, revenue: float):
        with self._lock:
            self._reset_if_new_day()
            self._count += 1
            self._cost += cost
            self._tokens += tokens
            m = self._metrics[tier]
            if success:
                m["completed"] += 1
                m["revenue"] += revenue
            else:
                m["failed"] += 1
            m["qa_scores"].append(qa_score)
            m["avg_qa"] = sum(m["qa_scores"]) / len(m["qa_scores"])

    def status(self) -> dict:
        with self._lock:
            self._reset_if_new_day()
            return {
                "date": self._date, "tasks_today": self._count,
                "max_daily": self.max_daily, "cost_today_usd": round(self._cost, 4),
                "tokens_today": self._tokens, "metrics_by_tier": dict(self._metrics),
            }


class FailureBreaker:
    def __init__(self, threshold: int = 3, cooldown_minutes: int = 20):
        self.threshold = threshold
        self.cooldown_minutes = cooldown_minutes
        self._consecutive = 0
        self._locked_until: Optional[datetime] = None
        self._lock = threading.Lock()

    def record(self, success: bool):
        with self._lock:
            if success:
                self._consecutive = 0
                self._locked_until = None
            else:
                self._consecutive += 1
                if self._consecutive >= self.threshold:
                    self._locked_until = datetime.now(timezone.utc) + timedelta(minutes=self.cooldown_minutes)
                    logger.warning("[CTR-SVC] Circuit breaker tripped — cooldown %d min", self.cooldown_minutes)

    def is_open(self) -> tuple[bool, str]:
        with self._lock:
            if self._locked_until and datetime.now(timezone.utc) < self._locked_until:
                remaining = (self._locked_until - datetime.now(timezone.utc)).seconds // 60
                return True, f"Division in cooldown ({remaining} min remaining)"
            if self._locked_until and datetime.now(timezone.utc) >= self._locked_until:
                self._locked_until = None
                self._consecutive = 0
            return False, "ok"


class ContractorDivision:
    """Self-contained autonomous division for contractor document production."""

    def __init__(self):
        self.tracker = DivisionTracker(
            max_daily=AUTONOMY.get("max_daily_tasks", 30),
            max_cost=AUTONOMY.get("max_cost_per_task_usd", 0.35),
            max_tokens=AUTONOMY.get("daily_token_budget", 450000),
        )
        self.breaker = FailureBreaker(
            threshold=3,
            cooldown_minutes=AUTONOMY.get("cooldown_on_3_consecutive_failures_minutes", 20),
        )
        self.auto_deliver_threshold = AUTONOMY.get("auto_deliver_threshold_qa_score", 80)
        self.human_review_threshold = AUTONOMY.get("human_review_required_below_qa", 70)
        self.auto_reject_threshold = AUTONOMY.get("auto_reject_below_qa", 50)
        self.max_retries = AUTONOMY.get("max_retries_per_task", 2)

    async def process(self, request: dict) -> dict:
        """Full pipeline: intake → route → dispatch → QA → delivery."""
        task_id = str(uuid4())[:8]
        tier = request.get("tier", "standard")
        doc_type = request.get("doc_type", "project_proposal")
        start = time.time()

        breaker_open, reason = self.breaker.is_open()
        if breaker_open:
            return {"task_id": task_id, "status": "rejected", "reason": reason}

        can_accept, reason = self.tracker.can_accept()
        if not can_accept:
            return {"task_id": task_id, "status": "rejected", "reason": reason}

        # Route to correct agent based on doc_type
        route = DOC_TYPES.get(doc_type)
        if not route:
            return {"task_id": task_id, "status": "rejected", "reason": f"Unknown doc_type: {doc_type}. Supported: {list(DOC_TYPES.keys())}"}

        tier_config = PRICING.get(tier, PRICING.get("standard", {}))
        token_budget = tier_config.get("token_budget", 35000)
        price = tier_config.get("price_usd", 47)

        logger.info("[CTR-SVC][%s] Intake accepted — doc_type=%s, agent=%s, tier=%s", task_id, doc_type, route["agent"], tier)

        # ── Dispatch ───────────────────────────────────────────────
        attempt = 0
        result = None

        while attempt <= self.max_retries:
            attempt += 1
            try:
                result = await self._run_agent(route["agent"], request, token_budget, task_id, attempt)
                if result and result.get("status") == "success":
                    break
            except Exception as exc:
                logger.warning("[CTR-SVC][%s] Attempt %d failed: %s", task_id, attempt, exc)
                if attempt > self.max_retries:
                    elapsed = time.time() - start
                    self.breaker.record(False)
                    self.tracker.record_task(0.0, 0, False, 0, tier, 0)
                    return {"task_id": task_id, "status": "failed", "reason": f"All attempts failed", "elapsed_seconds": round(elapsed, 2)}

        elapsed = time.time() - start

        if not result or result.get("status") != "success":
            self.breaker.record(False)
            self.tracker.record_task(0.0, 0, False, 0, tier, 0)
            return {"task_id": task_id, "status": "failed", "reason": "Agent returned non-success", "elapsed_seconds": round(elapsed, 2)}

        qa_score = result.get("qa_score", 0)

        if qa_score < self.auto_reject_threshold:
            self.breaker.record(False)
            self.tracker.record_task(result.get("cost", 0), result.get("tokens", 0), False, qa_score, tier, 0)
            return {"task_id": task_id, "status": "rejected", "reason": f"QA score {qa_score} below minimum", "elapsed_seconds": round(elapsed, 2)}

        delivery_mode = "auto"
        if qa_score < self.human_review_threshold:
            delivery_mode = "human_review_required"
        elif qa_score < self.auto_deliver_threshold:
            delivery_mode = "auto_with_notice"

        self.breaker.record(True)
        self.tracker.record_task(
            cost=result.get("cost", 0), tokens=result.get("tokens", 0),
            success=True, qa_score=qa_score, tier=tier, revenue=price,
        )

        return {
            "task_id": task_id, "status": "completed", "delivery_mode": delivery_mode,
            "qa_score": qa_score, "doc_type": doc_type, "tier": tier, "price_usd": price,
            "output": result.get("output", {}), "docx_path": result.get("docx_path"),
            "elapsed_seconds": round(elapsed, 2), "attempt": attempt,
        }

    async def _run_agent(self, agent_name: str, request: dict, token_budget: int, task_id: str, attempt: int) -> dict:
        """Route to the appropriate agent based on doc_type."""
        try:
            if agent_name == "compliance_docs":
                from agents.compliance_docs.runner import run as compliance_run
                agent_result = await compliance_run(request)
            elif agent_name == "data_reporter":
                from agents.data_reporter.runner import run as report_run
                agent_result = await report_run(request)
            elif agent_name == "proposal_writer":
                from agents.proposal_writer.runner import run as proposal_run
                agent_result = await proposal_run(request)
            else:
                raise ValueError(f"Unknown agent: {agent_name}")

            return {
                "status": "success" if agent_result.get("qa_passed") else "qa_fail",
                "qa_score": agent_result.get("qa_score", 0),
                "output": agent_result.get("output", {}),
                "docx_path": agent_result.get("docx_path"),
                "cost": agent_result.get("cost", 0),
                "tokens": agent_result.get("tokens_used", 0),
            }
        except ImportError as exc:
            logger.error("[CTR-SVC][%s] Agent %s not found: %s", task_id, agent_name, exc)
            raise
        except Exception as exc:
            logger.error("[CTR-SVC][%s] Agent %s error (attempt %d): %s", task_id, agent_name, attempt, exc)
            raise

    def health_check(self) -> dict:
        breaker_open, breaker_reason = self.breaker.is_open()
        return {
            "division": "contractor_services", "division_code": "CTR-SVC",
            "status": "DEGRADED" if breaker_open else "GREEN",
            "breaker_open": breaker_open, "breaker_reason": breaker_reason,
            "tracker": self.tracker.status(),
            "supported_doc_types": list(DOC_TYPES.keys()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def reset_breaker(self):
        with self.breaker._lock:
            self.breaker._consecutive = 0
            self.breaker._locked_until = None
        logger.info("[CTR-SVC] Circuit breaker manually reset")
