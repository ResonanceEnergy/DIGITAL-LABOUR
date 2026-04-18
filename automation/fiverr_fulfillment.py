"""FIVERR FULFILLMENT PIPELINE -- Automated gig delivery with QA.

Monitors for incoming Fiverr orders (via webhook or polling), dispatches
work to the appropriate BRL agent based on gig type, runs QA verification,
packages output for delivery, and tracks fulfillment metrics.

Integrates with:
- agents.<type>.runner for content generation
- agents.qa_manager for quality verification
- automation.decision_log for audit trail
- delivery/ for output packaging

Supported gig types and their agent mappings:
    product_description  -> agents.product_desc.runner
    seo_blog_post        -> agents.seo_content.runner
    resume_writing       -> agents.resume_writer.runner
    ad_copy              -> agents.ad_copy.runner
    email_sequence       -> agents.email_marketing.runner
    press_release        -> agents.press_release.runner
    tech_docs            -> agents.tech_docs.runner
    proposal_writing     -> agents.proposal_writer.runner

Usage:
    python -m automation.fiverr_fulfillment --poll           # Poll for new orders
    python -m automation.fiverr_fulfillment --daemon         # Continuous polling
    python -m automation.fiverr_fulfillment --status         # Fulfillment metrics
    python -m automation.fiverr_fulfillment --fulfill <id>   # Process a specific order
    python -m automation.fiverr_fulfillment --history        # Recent deliveries
"""

import argparse
import importlib
import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# ── Logging ───────────────────────────────────────────────────
logger = logging.getLogger("fiverr_fulfillment")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(_handler)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from automation.decision_log import log_decision

# ── Config ────────────────────────────────────────────────────
POLL_INTERVAL_SECONDS = 300       # 5 minutes between order checks
MAX_CONCURRENT_ORDERS = 3         # Don't overload agents
QA_RETRY_LIMIT = 2               # Max QA re-runs before escalation
DELIVERY_DIR = PROJECT_ROOT / "delivery" / "fiverr"
DELIVERY_DIR.mkdir(parents=True, exist_ok=True)

# ── Paths ─────────────────────────────────────────────────────
DATA_DIR = PROJECT_ROOT / "data" / "fiverr_fulfillment"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ORDER_LOG_FILE = DATA_DIR / "order_log.jsonl"
METRICS_FILE = DATA_DIR / "fulfillment_metrics.json"
STATE_FILE = DATA_DIR / "fulfillment_state.json"
WEBHOOK_QUEUE_FILE = DATA_DIR / "webhook_queue.json"

# ── Agent Dispatch Map ────────────────────────────────────────
# Maps Fiverr gig type slugs to their BRL agent module paths.
AGENT_DISPATCH = {
    "product_description": "agents.product_desc.runner",
    "seo_blog_post":       "agents.seo_content.runner",
    "resume_writing":      "agents.resume_writer.runner",
    "ad_copy":             "agents.ad_copy.runner",
    "email_sequence":      "agents.email_marketing.runner",
    "press_release":       "agents.press_release.runner",
    "tech_docs":           "agents.tech_docs.runner",
    "proposal_writing":    "agents.proposal_writer.runner",
    "grant_proposal":      "agents.grant_writer.runner",
    "compliance_document": "agents.compliance_docs.runner",
    "insurance_appeal":    "agents.insurance_appeals.runner",
    "data_report":         "agents.data_reporter.runner",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STATE MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _load_state() -> dict:
    """Load persisted fulfillment state from disk."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "active_orders": [],
        "polls_run": 0,
        "last_poll": None,
        "paused": False,
        "pause_reason": None,
    }


def _save_state(state: dict):
    """Atomically persist fulfillment state to disk."""
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(STATE_FILE))


def _load_metrics() -> dict:
    """Load fulfillment metrics."""
    if METRICS_FILE.exists():
        try:
            return json.loads(METRICS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "total_orders_received": 0,
        "total_delivered": 0,
        "total_failed": 0,
        "total_qa_retries": 0,
        "total_escalated": 0,
        "avg_fulfillment_seconds": 0,
        "by_gig_type": {},
        "daily_stats": {},
    }


def _save_metrics(metrics: dict):
    """Atomically persist fulfillment metrics."""
    tmp = METRICS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(METRICS_FILE))


def _update_metrics(order: dict, fulfillment_seconds: float):
    """Update metrics after a fulfillment attempt.

    Args:
        order: The completed order dict.
        fulfillment_seconds: Time taken to fulfill the order.
    """
    metrics = _load_metrics()
    status = order.get("status", "unknown")
    gig_type = order.get("gig_type", "unknown")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if status == "delivered":
        metrics["total_delivered"] += 1
    elif status == "failed":
        metrics["total_failed"] += 1
    elif status == "escalated":
        metrics["total_escalated"] += 1

    metrics["total_qa_retries"] += order.get("qa_retries", 0)

    # Update running average
    prev_total = metrics["total_delivered"] + metrics["total_failed"]
    if prev_total > 0:
        prev_avg = metrics["avg_fulfillment_seconds"]
        metrics["avg_fulfillment_seconds"] = round(
            (prev_avg * (prev_total - 1) + fulfillment_seconds) / prev_total, 2
        )
    else:
        metrics["avg_fulfillment_seconds"] = round(fulfillment_seconds, 2)

    # Per gig type
    if gig_type not in metrics["by_gig_type"]:
        metrics["by_gig_type"][gig_type] = {
            "delivered": 0, "failed": 0, "escalated": 0, "avg_seconds": 0
        }
    gt = metrics["by_gig_type"][gig_type]
    if status == "delivered":
        gt["delivered"] += 1
    elif status == "failed":
        gt["failed"] += 1
    elif status == "escalated":
        gt["escalated"] += 1
    gt_total = gt["delivered"] + gt["failed"]
    if gt_total > 0:
        gt["avg_seconds"] = round(
            (gt["avg_seconds"] * (gt_total - 1) + fulfillment_seconds) / gt_total, 2
        )

    # Daily stats
    if today not in metrics["daily_stats"]:
        metrics["daily_stats"][today] = {"delivered": 0, "failed": 0, "received": 0}
    if status == "delivered":
        metrics["daily_stats"][today]["delivered"] += 1
    elif status in ("failed", "escalated"):
        metrics["daily_stats"][today]["failed"] += 1

    _save_metrics(metrics)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ORDER INGESTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def ingest_webhook_order(payload: dict) -> dict:
    """Process an incoming Fiverr order from a webhook POST.

    Expected payload fields:
        order_id, gig_type, buyer_username, requirements, extras,
        delivery_deadline_utc, budget_usd

    Returns normalized order dict.
    """
    gig_type = payload.get("gig_type", "")
    if gig_type not in AGENT_DISPATCH:
        logger.error("Unknown gig type '%s' for order %s", gig_type, payload.get("order_id"))
        return {
            "status": "error",
            "message": f"Unknown gig type: {gig_type}. Supported: {', '.join(AGENT_DISPATCH.keys())}",
        }

    order = {
        "order_id": str(payload.get("order_id", "")),
        "gig_type": gig_type,
        "agent_module": AGENT_DISPATCH[gig_type],
        "buyer_username": payload.get("buyer_username", ""),
        "requirements": payload.get("requirements", ""),
        "extras": payload.get("extras", []),
        "delivery_deadline_utc": payload.get("delivery_deadline_utc", ""),
        "budget_usd": payload.get("budget_usd", 0),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "status": "received",
        "qa_retries": 0,
        "qa_passed": False,
    }

    # Append to webhook queue for processing
    queue = []
    if WEBHOOK_QUEUE_FILE.exists():
        try:
            queue = json.loads(WEBHOOK_QUEUE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            queue = []
    queue.append(order)
    WEBHOOK_QUEUE_FILE.write_text(json.dumps(queue, indent=2), encoding="utf-8")

    # Update metrics
    metrics = _load_metrics()
    metrics["total_orders_received"] += 1
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if today not in metrics["daily_stats"]:
        metrics["daily_stats"][today] = {"delivered": 0, "failed": 0, "received": 0}
    metrics["daily_stats"][today]["received"] += 1
    _save_metrics(metrics)

    logger.info("Ingested order %s: gig_type=%s, buyer=%s",
                order["order_id"], gig_type, order.get("buyer_username"))

    log_decision(
        actor="FIVERR_FULFILLMENT",
        action="ingest_order",
        reasoning=f"Received Fiverr order {order['order_id']} for {gig_type}",
        outcome=f"Queued for agent dispatch via {AGENT_DISPATCH[gig_type]}",
    )

    return order


def poll_for_orders() -> list[dict]:
    """Poll for new Fiverr orders from the webhook queue and scraped sources.

    Checks:
    1. Webhook queue (orders pushed via POST)
    2. Scraped order log from fiverr_automation.py

    Returns list of unprocessed orders.
    """
    orders = []

    # Source 1: Webhook queue
    if WEBHOOK_QUEUE_FILE.exists():
        try:
            queue = json.loads(WEBHOOK_QUEUE_FILE.read_text(encoding="utf-8"))
            pending = [o for o in queue if o.get("status") == "received"]
            orders.extend(pending)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read webhook queue: %s", e)

    # Source 2: Scraped order data from fiverr_automation
    scraped_log = PROJECT_ROOT / "data" / "fiverr_orders" / "order_log.jsonl"
    if scraped_log.exists():
        try:
            lines = scraped_log.read_text(encoding="utf-8").strip().split("\n")
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            for line in lines:
                if not line.strip():
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if raw.get("processed"):
                    continue
                if raw.get("received_at", raw.get("scraped_at", "")) < cutoff:
                    continue

                gig_type = raw.get("gig_type", "")
                if gig_type not in AGENT_DISPATCH:
                    continue

                orders.append({
                    "order_id": str(raw.get("order_id", raw.get("id", ""))),
                    "gig_type": gig_type,
                    "agent_module": AGENT_DISPATCH[gig_type],
                    "buyer_username": raw.get("buyer_username", raw.get("buyer", "")),
                    "requirements": raw.get("requirements", raw.get("description", "")),
                    "extras": raw.get("extras", []),
                    "delivery_deadline_utc": raw.get("delivery_deadline_utc", raw.get("due_date", "")),
                    "budget_usd": raw.get("budget_usd", raw.get("price", 0)),
                    "received_at": raw.get("received_at", raw.get("scraped_at", datetime.now(timezone.utc).isoformat())),
                    "status": "received",
                    "qa_retries": 0,
                    "qa_passed": False,
                    "source": "scraped",
                })
        except OSError as e:
            logger.warning("Failed to read scraped order log: %s", e)

    return orders


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  AGENT DISPATCH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def dispatch_to_agent(order: dict) -> dict:
    """Dispatch an order to the appropriate BRL agent for content generation.

    Dynamically imports the agent runner module and calls its run() function
    with the order requirements.

    Args:
        order: Normalized order dict with gig_type, requirements, extras.

    Returns:
        Agent result dict with 'output', 'status', and optional metadata.
    """
    agent_module_path = order.get("agent_module", "")
    if not agent_module_path:
        return {"status": "error", "message": "No agent_module specified in order"}

    logger.info("Dispatching order %s to agent %s", order["order_id"], agent_module_path)

    try:
        module = importlib.import_module(agent_module_path)
    except ImportError as e:
        logger.error("Failed to import agent module %s: %s", agent_module_path, e)
        return {
            "status": "error",
            "message": f"Agent module not found: {agent_module_path} ({e})",
        }

    run_fn = getattr(module, "run", None)
    if run_fn is None:
        logger.error("Agent module %s has no run() function", agent_module_path)
        return {
            "status": "error",
            "message": f"Agent module {agent_module_path} has no run() function",
        }

    try:
        result = run_fn(
            requirements=order.get("requirements", ""),
            extras=order.get("extras", []),
            order_id=order.get("order_id", ""),
            buyer=order.get("buyer_username", ""),
            budget_usd=order.get("budget_usd", 0),
        )
    except Exception as e:
        logger.error("Agent %s raised exception for order %s: %s",
                     agent_module_path, order["order_id"], e)
        return {
            "status": "error",
            "message": f"Agent execution failed: {e}",
            "traceback": traceback.format_exc(),
        }

    if not isinstance(result, dict):
        result = {"output": result, "status": "completed"}

    result.setdefault("status", "completed")
    logger.info("Agent %s completed order %s: status=%s",
                agent_module_path, order["order_id"], result["status"])
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  QA VERIFICATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_qa_check(order: dict, agent_result: dict) -> dict:
    """Run QA verification on the agent output.

    Attempts to import and run the QA manager agent. Falls back to
    basic structural checks if the QA agent is unavailable.

    Args:
        order: The order being fulfilled.
        agent_result: Output from dispatch_to_agent().

    Returns:
        QA result dict with 'passed' (bool), 'score', 'issues', 'details'.
    """
    output = agent_result.get("output", "")
    gig_type = order.get("gig_type", "")

    # Try QA agent first
    try:
        from agents.qa_manager import runner as qa_runner
        qa_result = qa_runner.run(
            content=output,
            content_type=gig_type,
            requirements=order.get("requirements", ""),
            order_id=order.get("order_id", ""),
        )
        if isinstance(qa_result, dict):
            qa_result.setdefault("passed", qa_result.get("score", 0) >= 0.7)
            return qa_result
    except (ImportError, AttributeError) as e:
        logger.info("QA agent unavailable (%s), using basic checks", e)
    except Exception as e:
        logger.warning("QA agent error: %s -- falling back to basic checks", e)

    # Fallback: basic structural QA
    issues = []
    score = 1.0

    if not output or (isinstance(output, str) and len(output.strip()) < 50):
        issues.append("Output is empty or too short (< 50 chars)")
        score -= 0.5

    if isinstance(output, str):
        # Check for placeholder text that agents sometimes leave in
        placeholders = ["[INSERT", "[TODO", "Lorem ipsum", "{placeholder}", "FIXME"]
        for ph in placeholders:
            if ph.lower() in output.lower():
                issues.append(f"Contains placeholder text: '{ph}'")
                score -= 0.2

        # Minimum word count by gig type
        min_words = {
            "product_description": 50,
            "seo_blog_post": 300,
            "resume_writing": 100,
            "ad_copy": 20,
            "email_sequence": 100,
            "press_release": 200,
            "tech_docs": 150,
            "proposal_writing": 200,
        }
        word_count = len(output.split())
        required = min_words.get(gig_type, 50)
        if word_count < required:
            issues.append(f"Word count {word_count} below minimum {required} for {gig_type}")
            score -= 0.3

    score = max(0.0, min(1.0, score))
    passed = score >= 0.7 and len(issues) == 0

    return {
        "passed": passed,
        "score": round(score, 2),
        "issues": issues,
        "details": f"Basic QA: {len(issues)} issue(s), score {score:.2f}",
        "method": "basic_structural",
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  OUTPUT PACKAGING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def package_delivery(order: dict, agent_result: dict, qa_result: dict) -> dict:
    """Package the agent output for Fiverr delivery.

    Creates a structured delivery directory with the output file(s),
    a manifest, and QA report.

    Args:
        order: The fulfilled order.
        agent_result: Output from the agent.
        qa_result: QA verification result.

    Returns:
        Delivery info dict with file paths and metadata.
    """
    order_id = order.get("order_id", "unknown")
    gig_type = order.get("gig_type", "unknown")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Create delivery directory
    delivery_path = DELIVERY_DIR / f"{order_id}_{timestamp}"
    delivery_path.mkdir(parents=True, exist_ok=True)

    output = agent_result.get("output", "")
    files_created = []

    # Determine output file extension based on gig type
    ext_map = {
        "product_description": ".txt",
        "seo_blog_post": ".md",
        "resume_writing": ".txt",
        "ad_copy": ".txt",
        "email_sequence": ".txt",
        "press_release": ".txt",
        "tech_docs": ".md",
        "proposal_writing": ".md",
    }
    ext = ext_map.get(gig_type, ".txt")
    output_filename = f"{gig_type}_output{ext}"

    # Write main output
    if isinstance(output, str):
        output_file = delivery_path / output_filename
        output_file.write_text(output, encoding="utf-8")
        files_created.append(str(output_file))
    elif isinstance(output, dict):
        # Agent returned structured output -- write as JSON + extract text
        json_file = delivery_path / f"{gig_type}_output.json"
        json_file.write_text(json.dumps(output, indent=2), encoding="utf-8")
        files_created.append(str(json_file))

        # Also write any text content
        if "text" in output or "content" in output:
            text_content = output.get("text", output.get("content", ""))
            text_file = delivery_path / output_filename
            text_file.write_text(str(text_content), encoding="utf-8")
            files_created.append(str(text_file))

    # Write any additional files from agent result
    for extra_file in agent_result.get("files", []):
        if isinstance(extra_file, dict) and "name" in extra_file and "content" in extra_file:
            ef_path = delivery_path / extra_file["name"]
            ef_path.write_text(str(extra_file["content"]), encoding="utf-8")
            files_created.append(str(ef_path))

    # Write QA report
    qa_report_file = delivery_path / "qa_report.json"
    qa_report_file.write_text(json.dumps(qa_result, indent=2), encoding="utf-8")
    files_created.append(str(qa_report_file))

    # Write delivery manifest
    manifest = {
        "order_id": order_id,
        "gig_type": gig_type,
        "buyer": order.get("buyer_username", ""),
        "agent": order.get("agent_module", ""),
        "delivered_at": datetime.now(timezone.utc).isoformat(),
        "qa_passed": qa_result.get("passed", False),
        "qa_score": qa_result.get("score", 0),
        "files": files_created,
        "delivery_path": str(delivery_path),
    }
    manifest_file = delivery_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    files_created.append(str(manifest_file))

    logger.info("Packaged delivery for order %s: %d file(s) in %s",
                order_id, len(files_created), delivery_path)

    return {
        "delivery_path": str(delivery_path),
        "files": files_created,
        "manifest": manifest,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ORDER LOG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _log_order(order: dict):
    """Append order record to JSONL log."""
    with open(ORDER_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(order) + "\n")


def get_order_history(limit: int = 20) -> list[dict]:
    """Get recent order fulfillment history."""
    if not ORDER_LOG_FILE.exists():
        return []
    lines = ORDER_LOG_FILE.read_text(encoding="utf-8").strip().split("\n")
    orders = []
    for line in lines:
        if not line.strip():
            continue
        try:
            orders.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return orders[-limit:]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FULFILLMENT PIPELINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def fulfill_order(order: dict) -> dict:
    """Execute the full fulfillment pipeline for a single order.

    Pipeline stages:
    1. Validate order and resolve agent
    2. Dispatch to BRL agent
    3. Run QA verification (with retries)
    4. Package output for delivery
    5. Update metrics and log

    Args:
        order: Normalized order dict.

    Returns:
        Fulfillment result dict with status, delivery info, and timing.
    """
    order_id = order.get("order_id", "unknown")
    gig_type = order.get("gig_type", "")
    start_time = time.monotonic()

    logger.info("Starting fulfillment for order %s (gig_type=%s)", order_id, gig_type)

    result = {
        "order_id": order_id,
        "gig_type": gig_type,
        "status": "processing",
        "stages": [],
    }

    # Stage 1: Validate
    if gig_type not in AGENT_DISPATCH:
        result["status"] = "failed"
        result["error"] = f"Unknown gig type: {gig_type}"
        result["stages"].append({"stage": "validate", "status": "failed", "error": result["error"]})
        elapsed = time.monotonic() - start_time
        result["fulfillment_seconds"] = round(elapsed, 2)
        order["status"] = "failed"
        _log_order(order)
        _update_metrics(order, elapsed)
        return result

    order["agent_module"] = AGENT_DISPATCH[gig_type]
    result["stages"].append({"stage": "validate", "status": "passed"})

    # Stage 2: Dispatch to agent
    agent_result = dispatch_to_agent(order)
    if agent_result.get("status") == "error":
        result["status"] = "failed"
        result["error"] = agent_result.get("message", "Agent dispatch failed")
        result["stages"].append({"stage": "dispatch", "status": "failed", "error": result["error"]})
        elapsed = time.monotonic() - start_time
        result["fulfillment_seconds"] = round(elapsed, 2)
        order["status"] = "failed"
        order["error"] = result["error"]
        _log_order(order)
        _update_metrics(order, elapsed)

        log_decision(
            actor="FIVERR_FULFILLMENT",
            action="dispatch_failed",
            reasoning=f"Agent dispatch failed for order {order_id}",
            outcome=result["error"],
            severity="ERROR",
        )
        return result

    result["stages"].append({"stage": "dispatch", "status": "completed"})

    # Stage 3: QA verification with retries
    qa_passed = False
    qa_result = {}
    for attempt in range(1, QA_RETRY_LIMIT + 1):
        qa_result = run_qa_check(order, agent_result)
        order["qa_retries"] = attempt

        if qa_result.get("passed"):
            qa_passed = True
            result["stages"].append({
                "stage": "qa",
                "status": "passed",
                "attempt": attempt,
                "score": qa_result.get("score", 0),
            })
            break

        logger.warning("QA failed for order %s (attempt %d/%d): %s",
                       order_id, attempt, QA_RETRY_LIMIT,
                       "; ".join(qa_result.get("issues", [])))

        if attempt < QA_RETRY_LIMIT:
            # Retry: re-dispatch to agent with QA feedback
            logger.info("Re-dispatching order %s with QA feedback", order_id)
            feedback = "QA issues found: " + "; ".join(qa_result.get("issues", []))
            order["requirements"] = order.get("requirements", "") + f"\n\n[QA FEEDBACK]: {feedback}"
            agent_result = dispatch_to_agent(order)
            if agent_result.get("status") == "error":
                break

    if not qa_passed:
        result["stages"].append({
            "stage": "qa",
            "status": "failed",
            "attempts": order.get("qa_retries", 0),
            "issues": qa_result.get("issues", []),
        })

        # Escalate: QA failed after all retries
        order["status"] = "escalated"
        result["status"] = "escalated"
        result["error"] = f"QA failed after {QA_RETRY_LIMIT} attempts"
        elapsed = time.monotonic() - start_time
        result["fulfillment_seconds"] = round(elapsed, 2)
        _log_order(order)
        _update_metrics(order, elapsed)

        log_decision(
            actor="FIVERR_FULFILLMENT",
            action="qa_escalation",
            reasoning=f"QA failed {QA_RETRY_LIMIT} times for order {order_id}: {qa_result.get('issues', [])}",
            outcome="Order escalated for human review",
            severity="WARN",
        )
        return result

    order["qa_passed"] = True

    # Stage 4: Package for delivery
    try:
        delivery = package_delivery(order, agent_result, qa_result)
        result["stages"].append({"stage": "package", "status": "completed"})
        result["delivery"] = delivery
    except Exception as e:
        logger.error("Packaging failed for order %s: %s", order_id, e)
        result["stages"].append({"stage": "package", "status": "failed", "error": str(e)})
        order["status"] = "failed"
        result["status"] = "failed"
        result["error"] = f"Packaging failed: {e}"
        elapsed = time.monotonic() - start_time
        result["fulfillment_seconds"] = round(elapsed, 2)
        _log_order(order)
        _update_metrics(order, elapsed)
        return result

    # Stage 5: Finalize
    elapsed = time.monotonic() - start_time
    order["status"] = "delivered"
    order["delivered_at"] = datetime.now(timezone.utc).isoformat()
    order["delivery_path"] = delivery.get("delivery_path", "")
    result["status"] = "delivered"
    result["fulfillment_seconds"] = round(elapsed, 2)

    _log_order(order)
    _update_metrics(order, elapsed)

    log_decision(
        actor="FIVERR_FULFILLMENT",
        action="order_delivered",
        reasoning=f"Fulfilled order {order_id} via {order.get('agent_module')}",
        outcome=f"Delivered in {elapsed:.1f}s, QA score {qa_result.get('score', 0):.2f}",
    )

    logger.info("Order %s fulfilled in %.1fs (QA score: %.2f)",
                order_id, elapsed, qa_result.get("score", 0))
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  POLL CYCLE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_poll_cycle() -> dict:
    """Execute one fulfillment poll cycle.

    Checks for new orders, dispatches up to MAX_CONCURRENT_ORDERS,
    and returns a cycle report.
    """
    state = _load_state()
    now = datetime.now(timezone.utc)

    report = {
        "poll_number": state.get("polls_run", 0) + 1,
        "timestamp": now.isoformat(),
        "orders_found": 0,
        "orders_processed": 0,
        "orders_delivered": 0,
        "orders_failed": 0,
        "orders_escalated": 0,
        "errors": [],
    }

    if state.get("paused"):
        report["status"] = "paused"
        report["pause_reason"] = state.get("pause_reason", "unknown")
        logger.warning("Fulfillment paused: %s", state.get("pause_reason"))
        return report

    # Get pending orders
    orders = poll_for_orders()
    report["orders_found"] = len(orders)

    if not orders:
        logger.info("No pending orders found")
        state["polls_run"] = state.get("polls_run", 0) + 1
        state["last_poll"] = now.isoformat()
        _save_state(state)
        report["status"] = "no_orders"
        return report

    logger.info("Found %d pending order(s)", len(orders))

    # Process up to MAX_CONCURRENT_ORDERS
    processed = 0
    for order in orders[:MAX_CONCURRENT_ORDERS]:
        try:
            result = fulfill_order(order)
            report["orders_processed"] += 1

            if result["status"] == "delivered":
                report["orders_delivered"] += 1
            elif result["status"] == "failed":
                report["orders_failed"] += 1
            elif result["status"] == "escalated":
                report["orders_escalated"] += 1

            processed += 1
        except Exception as e:
            logger.error("Unhandled error fulfilling order %s: %s",
                         order.get("order_id"), e)
            report["errors"].append(f"Order {order.get('order_id')}: {e}")

    # Mark processed orders in webhook queue
    _mark_orders_processed([o.get("order_id") for o in orders[:processed]])

    state["polls_run"] = state.get("polls_run", 0) + 1
    state["last_poll"] = now.isoformat()
    _save_state(state)

    report["status"] = "completed"
    return report


def _mark_orders_processed(order_ids: list[str]):
    """Mark orders as processed in the webhook queue to prevent re-processing."""
    if not WEBHOOK_QUEUE_FILE.exists():
        return
    try:
        queue = json.loads(WEBHOOK_QUEUE_FILE.read_text(encoding="utf-8"))
        for item in queue:
            if item.get("order_id") in order_ids:
                item["status"] = "processed"
        WEBHOOK_QUEUE_FILE.write_text(json.dumps(queue, indent=2), encoding="utf-8")
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to update webhook queue: %s", e)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DAEMON MODE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_daemon():
    """Run fulfillment engine in continuous polling mode."""
    logger.info("=" * 70)
    logger.info("  FIVERR FULFILLMENT DAEMON -- Polling every %ds", POLL_INTERVAL_SECONDS)
    logger.info("  Max concurrent: %d | QA retries: %d", MAX_CONCURRENT_ORDERS, QA_RETRY_LIMIT)
    logger.info("  Supported gig types: %s", ", ".join(AGENT_DISPATCH.keys()))
    logger.info("=" * 70)

    while True:
        try:
            report = run_poll_cycle()
            status = report.get("status", "unknown")
            logger.info(
                "Poll #%d: %s | Found: %d | Delivered: %d | Failed: %d | Escalated: %d",
                report["poll_number"], status,
                report["orders_found"], report["orders_delivered"],
                report["orders_failed"], report["orders_escalated"],
            )

            if status == "paused":
                logger.warning("Fulfillment paused. Sleeping 5 minutes...")
                time.sleep(300)
            else:
                time.sleep(POLL_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            logger.info("Fulfillment daemon stopped by user")
            break
        except Exception as e:
            logger.error("Poll cycle failed: %s", e)
            traceback.print_exc()
            time.sleep(60)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STATUS & HISTORY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def print_status():
    """Print fulfillment metrics and pipeline status."""
    state = _load_state()
    metrics = _load_metrics()

    print(f"\n{'='*70}")
    print(f"  FIVERR FULFILLMENT STATUS")
    print(f"{'='*70}")
    print(f"  Paused:             {'YES -- ' + state.get('pause_reason', '') if state.get('paused') else 'No'}")
    print(f"  Polls Run:          {state.get('polls_run', 0)}")
    print(f"  Last Poll:          {state.get('last_poll', 'Never')}")
    print(f"  Active Orders:      {len(state.get('active_orders', []))}")
    print()
    print(f"  --- Lifetime Metrics ---")
    print(f"  Orders Received:    {metrics.get('total_orders_received', 0)}")
    print(f"  Delivered:          {metrics.get('total_delivered', 0)}")
    print(f"  Failed:             {metrics.get('total_failed', 0)}")
    print(f"  Escalated:          {metrics.get('total_escalated', 0)}")
    print(f"  QA Retries:         {metrics.get('total_qa_retries', 0)}")
    print(f"  Avg Fulfillment:    {metrics.get('avg_fulfillment_seconds', 0):.1f}s")
    print()

    by_type = metrics.get("by_gig_type", {})
    if by_type:
        print(f"  --- By Gig Type ---")
        for gig_type, stats in sorted(by_type.items()):
            print(f"  {gig_type:25s} delivered={stats.get('delivered', 0)} "
                  f"failed={stats.get('failed', 0)} "
                  f"avg={stats.get('avg_seconds', 0):.1f}s")
        print()

    print(f"  --- Supported Gig Types ---")
    for gig_type, agent in sorted(AGENT_DISPATCH.items()):
        print(f"  {gig_type:25s} -> {agent}")

    print(f"{'='*70}\n")


def print_history(limit: int = 20):
    """Print recent order fulfillment history."""
    orders = get_order_history(limit)
    if not orders:
        print("\n  No orders recorded yet.\n")
        return

    print(f"\n{'='*70}")
    print(f"  RECENT ORDERS (last {len(orders)})")
    print(f"{'='*70}")
    for order in orders:
        status_icon = {
            "delivered": "[OK]",
            "failed": "[!!]",
            "escalated": "[??]",
            "processing": "[..]",
            "received": "[>>]",
        }.get(order.get("status", ""), "[??]")

        print(f"  {status_icon} Order {order.get('order_id', '?'):12s} | "
              f"{order.get('gig_type', '?'):20s} | "
              f"{order.get('status', '?')}")
        print(f"       Buyer: {order.get('buyer_username', '?')} | "
              f"${order.get('budget_usd', 0):.2f} | "
              f"{order.get('received_at', '')[:10]}")
    print(f"{'='*70}\n")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="FIVERR FULFILLMENT -- Automated gig delivery pipeline")
    parser.add_argument("--poll", action="store_true",
                        help="Run one poll cycle for new orders")
    parser.add_argument("--daemon", action="store_true",
                        help="Run in continuous polling mode")
    parser.add_argument("--status", action="store_true",
                        help="Show fulfillment metrics and status")
    parser.add_argument("--history", action="store_true",
                        help="Show recent order history")
    parser.add_argument("--fulfill", type=str, metavar="ORDER_ID",
                        help="Process a specific order by ID")
    parser.add_argument("--ingest", type=str, metavar="JSON_FILE",
                        help="Ingest an order from a JSON file (simulates webhook)")
    parser.add_argument("--limit", type=int, default=20,
                        help="Number of history items to show")

    args = parser.parse_args()

    if args.status:
        print_status()

    elif args.history:
        print_history(args.limit)

    elif args.fulfill:
        # Find order in queue or create a minimal one
        orders = poll_for_orders()
        target = None
        for o in orders:
            if o.get("order_id") == args.fulfill:
                target = o
                break
        if target is None:
            print(f"\n  Order {args.fulfill} not found in pending queue.\n")
            sys.exit(1)
        result = fulfill_order(target)
        print(f"\n  Fulfillment result: {result.get('status')}")
        if result.get("delivery"):
            print(f"  Delivery path: {result['delivery'].get('delivery_path', 'N/A')}")
        if result.get("error"):
            print(f"  Error: {result['error']}")
        print()

    elif args.ingest:
        ingest_path = Path(args.ingest)
        if not ingest_path.exists():
            print(f"\n  File not found: {args.ingest}\n")
            sys.exit(1)
        payload = json.loads(ingest_path.read_text(encoding="utf-8"))
        order = ingest_webhook_order(payload)
        print(f"\n  Ingested order: {order.get('order_id', 'N/A')}")
        print(f"  Status: {order.get('status')}")
        if order.get("message"):
            print(f"  Message: {order['message']}")
        print()

    elif args.daemon:
        run_daemon()

    elif args.poll:
        report = run_poll_cycle()
        print(f"\n  Poll result: {report.get('status', 'unknown')}")
        print(f"  Orders: {report['orders_found']} found | "
              f"{report['orders_delivered']} delivered | "
              f"{report['orders_failed']} failed | "
              f"{report['orders_escalated']} escalated")
        if report.get("errors"):
            print(f"  Errors: {len(report['errors'])}")
        print()

    else:
        parser.print_help()
