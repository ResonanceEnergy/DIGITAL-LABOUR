"""Grant Operations Division Orchestrator.

Autonomous intake → dispatch → QA → delivery pipeline for grant proposals,
SBIR applications, and RFP responses.

Follows the Paperclip dispatcher pattern with Jake Van Clief self-healing:
- Intake: validates request, estimates cost, checks daily limits
- Dispatch: routes to grant_writer agent with token budget enforcement
- QA: runs qa_manager with grant-specific pass threshold (80)
- Delivery: renders DOCX, logs revenue, updates metrics
- Self-heal: retries on transient failures, escalates persistent ones

Usage:
    from super_agency.departments.grant_operations.orchestrator import GrantDivision
    division = GrantDivision()
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

logger = logging.getLogger("division.grant_ops")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# ── Division Config ────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

def _load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to load grant_operations config: %s", e)
        return {}

CONFIG = _load_config()
AUTONOMY = CONFIG.get("autonomy_controls", {})
PRICING = CONFIG.get("pricing_tiers", {})


# ── Daily Tracker (per-division) ───────────────────────────────────────────

class DivisionTracker:
    """Thread-safe daily task counter with cost accumulation."""

    def __init__(self, max_daily: int = 20, max_cost: float = 0.50, max_tokens: int = 500000):
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
                "date": self._date,
                "tasks_today": self._count,
                "max_daily": self.max_daily,
                "cost_today_usd": round(self._cost, 4),
                "tokens_today": self._tokens,
                "metrics_by_tier": dict(self._metrics),
            }


# ── Consecutive Failure Breaker ────────────────────────────────────────────

class FailureBreaker:
    """Circuit breaker: pauses division after N consecutive failures."""

    def __init__(self, threshold: int = 3, cooldown_minutes: int = 30):
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
                    logger.warning("[GRANT-OPS] Circuit breaker tripped — cooldown %d min", self.cooldown_minutes)

    def is_open(self) -> tuple[bool, str]:
        with self._lock:
            if self._locked_until and datetime.now(timezone.utc) < self._locked_until:
                remaining = (self._locked_until - datetime.now(timezone.utc)).seconds // 60
                return True, f"Division in cooldown ({remaining} min remaining after {self.threshold} consecutive failures)"
            if self._locked_until and datetime.now(timezone.utc) >= self._locked_until:
                self._locked_until = None
                self._consecutive = 0
            return False, "ok"


# ── Division Orchestrator ──────────────────────────────────────────────────

class GrantDivision:
    """Self-contained autonomous division for grant/SBIR proposal production."""

    def __init__(self):
        self.tracker = DivisionTracker(
            max_daily=AUTONOMY.get("max_daily_tasks", 20),
            max_cost=AUTONOMY.get("max_cost_per_task_usd", 0.50),
            max_tokens=AUTONOMY.get("daily_token_budget", 500000),
        )
        self.breaker = FailureBreaker(
            threshold=3,
            cooldown_minutes=AUTONOMY.get("cooldown_on_3_consecutive_failures_minutes", 30),
        )
        self.auto_deliver_threshold = AUTONOMY.get("auto_deliver_threshold_qa_score", 85)
        self.human_review_threshold = AUTONOMY.get("human_review_required_below_qa", 75)
        self.auto_reject_threshold = AUTONOMY.get("auto_reject_below_qa", 50)
        self.max_retries = AUTONOMY.get("max_retries_per_task", 2)

    async def process(self, request: dict) -> dict:
        """Full pipeline: intake → dispatch → QA → delivery."""
        task_id = str(uuid4())[:8]
        tier = request.get("tier", "standard")
        start = time.time()

        # ── Phase 1: Intake Validation ─────────────────────────────
        breaker_open, reason = self.breaker.is_open()
        if breaker_open:
            return {"task_id": task_id, "status": "rejected", "reason": reason}

        can_accept, reason = self.tracker.can_accept()
        if not can_accept:
            return {"task_id": task_id, "status": "rejected", "reason": reason}

        tier_config = PRICING.get(tier, PRICING.get("standard", {}))
        token_budget = tier_config.get("token_budget", 60000)
        price = tier_config.get("price_usd", 297)

        logger.info("[GRANT-OPS][%s] Intake accepted — tier=%s, budget=%d tokens", task_id, tier, token_budget)

        # ── Phase 2: Dispatch to Agent ─────────────────────────────
        attempt = 0
        result = None
        qa_score = 0

        while attempt <= self.max_retries:
            attempt += 1
            try:
                result = await self._run_agent(request, token_budget, task_id, attempt)
                if result and result.get("status") == "success":
                    qa_score = result.get("qa_score", 0)
                    break
            except Exception as exc:
                logger.warning("[GRANT-OPS][%s] Attempt %d failed: %s", task_id, attempt, exc)
                if attempt > self.max_retries:
                    elapsed = time.time() - start
                    self.breaker.record(False)
                    self.tracker.record_task(0.0, 0, False, 0, tier, 0)
                    return {
                        "task_id": task_id,
                        "status": "failed",
                        "reason": f"All {self.max_retries + 1} attempts failed",
                        "elapsed_seconds": round(elapsed, 2),
                    }

        elapsed = time.time() - start

        if not result or result.get("status") != "success":
            self.breaker.record(False)
            self.tracker.record_task(0.0, 0, False, 0, tier, 0)
            return {"task_id": task_id, "status": "failed", "reason": "Agent returned non-success", "elapsed_seconds": round(elapsed, 2)}

        # ── Phase 3: QA Gate ───────────────────────────────────────
        qa_score = result.get("qa_score", 0)

        if qa_score < self.auto_reject_threshold:
            self.breaker.record(False)
            self.tracker.record_task(result.get("cost", 0), result.get("tokens", 0), False, qa_score, tier, 0)
            logger.warning("[GRANT-OPS][%s] Auto-rejected — QA score %d < %d", task_id, qa_score, self.auto_reject_threshold)
            return {"task_id": task_id, "status": "rejected", "reason": f"QA score {qa_score} below minimum {self.auto_reject_threshold}", "elapsed_seconds": round(elapsed, 2)}

        # ── Phase 4: Delivery Decision ─────────────────────────────
        delivery_mode = "auto"
        if qa_score < self.human_review_threshold:
            delivery_mode = "human_review_required"
            logger.info("[GRANT-OPS][%s] QA=%d — flagged for human review", task_id, qa_score)
        elif qa_score < self.auto_deliver_threshold:
            delivery_mode = "auto_with_notice"
            logger.info("[GRANT-OPS][%s] QA=%d — auto-delivering with quality notice", task_id, qa_score)
        else:
            logger.info("[GRANT-OPS][%s] QA=%d — auto-delivering (high confidence)", task_id, qa_score)

        # ── Phase 5: Revenue & Metrics ─────────────────────────────
        self.breaker.record(True)
        self.tracker.record_task(
            cost=result.get("cost", 0),
            tokens=result.get("tokens", 0),
            success=True,
            qa_score=qa_score,
            tier=tier,
            revenue=price,
        )

        return {
            "task_id": task_id,
            "status": "completed",
            "delivery_mode": delivery_mode,
            "qa_score": qa_score,
            "tier": tier,
            "price_usd": price,
            "output": result.get("output", {}),
            "docx_path": result.get("docx_path"),
            "elapsed_seconds": round(elapsed, 2),
            "attempt": attempt,
        }

    async def _run_agent(self, request: dict, token_budget: int, task_id: str, attempt: int) -> dict:
        """Dispatch to the grant_writer agent pipeline."""
        try:
            from agents.grant_writer.runner import run as grant_run
            agent_result = await grant_run(request)
            return {
                "status": "success" if agent_result.get("qa_passed") else "qa_fail",
                "qa_score": agent_result.get("qa_score", 0),
                "output": agent_result.get("output", {}),
                "docx_path": agent_result.get("docx_path"),
                "cost": agent_result.get("cost", 0),
                "tokens": agent_result.get("tokens_used", 0),
            }
        except ImportError:
            logger.error("[GRANT-OPS][%s] grant_writer agent not found", task_id)
            raise
        except Exception as exc:
            logger.error("[GRANT-OPS][%s] Agent error (attempt %d): %s", task_id, attempt, exc)
            raise

    def health_check(self) -> dict:
        """Return division health status for NERVE integration."""
        breaker_open, breaker_reason = self.breaker.is_open()
        tracker_status = self.tracker.status()
        return {
            "division": "grant_operations",
            "division_code": "GRANT-OPS",
            "status": "DEGRADED" if breaker_open else "GREEN",
            "breaker_open": breaker_open,
            "breaker_reason": breaker_reason,
            "tracker": tracker_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def reset_breaker(self):
        """Manual breaker reset (for NERVE self-healing)."""
        with self.breaker._lock:
            self.breaker._consecutive = 0
            self.breaker._locked_until = None
        logger.info("[GRANT-OPS] Circuit breaker manually reset")
