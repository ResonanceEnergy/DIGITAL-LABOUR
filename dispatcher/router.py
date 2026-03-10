"""Dispatcher — Routes tasks to the correct agent, enforces budgets, logs results.

Usage:
    python router.py                          # Interactive mode
    python router.py --task task.json         # Process a single task file
    python router.py --queue queue/           # Process all tasks in queue directory
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")


# ── Config ──────────────────────────────────────────────────────────────────

DAILY_LIMITS = {
    "sales_outreach": 50,
    "support_ticket": 100,
    "content_repurpose": 40,
    "ops_brief": 10,
    "doc_extract": 30,
}

TOKEN_BUDGETS = {
    "sales_outreach": 25000,
    "support_ticket": 15000,
    "content_repurpose": 20000,
    "ops_brief": 20000,
    "doc_extract": 15000,
}


# ── Task Tracking ───────────────────────────────────────────────────────────

class DailyTracker:
    """Tracks daily task counts per type."""

    def __init__(self):
        self._counts: dict[str, int] = {}
        self._date: str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _reset_if_new_day(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._date:
            self._counts = {}
            self._date = today

    def can_accept(self, task_type: str) -> bool:
        self._reset_if_new_day()
        limit = DAILY_LIMITS.get(task_type, 20)
        return self._counts.get(task_type, 0) < limit

    def increment(self, task_type: str):
        self._reset_if_new_day()
        self._counts[task_type] = self._counts.get(task_type, 0) + 1

    def status(self) -> dict:
        self._reset_if_new_day()
        return {k: f"{self._counts.get(k, 0)}/{v}" for k, v in DAILY_LIMITS.items()}


tracker = DailyTracker()


# ── Event Creation ──────────────────────────────────────────────────────────

def create_event(task_type: str, inputs: dict, client_id: str = "direct") -> dict:
    return {
        "event_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "client_id": client_id,
        "task_type": task_type,
        "inputs": inputs,
        "constraints": {
            "time_budget_sec": 300,
            "max_retries": 1,
            "token_budget": TOKEN_BUDGETS.get(task_type, 20000),
        },
        "outputs": {},
        "qa": {"status": "PENDING", "issues": [], "revision_notes": ""},
        "billing": {
            "pricing_unit": "per_workflow",
            "amount": 0,
            "currency": "USD",
            "status": "unbilled",
        },
        "metrics": {"latency_ms": 0, "cost_estimate": 0, "tokens_used": 0},
    }


# ── Agent Routing ───────────────────────────────────────────────────────────

def route_task(event: dict) -> dict:
    """Route a task to the correct agent and return the completed event."""
    task_type = event["task_type"]
    inputs = event["inputs"]
    start = time.time()

    if not tracker.can_accept(task_type):
        event["qa"]["status"] = "FAIL"
        event["qa"]["issues"] = [f"Daily limit reached for {task_type}"]
        print(f"[LIMIT] Daily limit reached for {task_type}")
        return event

    tracker.increment(task_type)

    provider = inputs.get("provider") or event.get("provider")

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

        else:
            event["qa"]["status"] = "FAIL"
            event["qa"]["issues"] = [f"Unknown task type: {task_type}"]
            print(f"[ERROR] Unknown task type: {task_type}")

    except Exception as e:
        event["qa"]["status"] = "FAIL"
        event["qa"]["issues"] = [str(e)]
        print(f"[ERROR] {e}")

    elapsed_ms = int((time.time() - start) * 1000)
    event["metrics"]["latency_ms"] = elapsed_ms

    # Log the event (legacy JSONL)
    log_event(event)

    # Structured KPI log
    try:
        from kpi.logger import log_task_event
        log_task_event(
            task_id=event.get("event_id", ""),
            task_type=task_type,
            status="completed" if event["qa"]["status"] == "PASS" else "failed",
            client=event.get("client", ""),
            provider=provider or "",
            qa_status=event["qa"]["status"],
            duration_s=elapsed_ms / 1000,
        )
    except Exception:
        pass  # Don't let logging failures break the pipeline

    # C-Suite event feed — executives consume this for real-time awareness
    try:
        _csuite_notify(event)
    except Exception:
        pass  # Never let executive hooks break task delivery

    # NCC Relay — publish task event to Resonance Energy governance
    try:
        from resonance.ncc_bridge import ncc
        ncc.publish_task_event(event)
    except Exception:
        pass  # Never let relay hooks break task delivery

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
            pass


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
    print("=== DIGITAL LABOUR DISPATCHER ===")
    print(f"Daily limits: {tracker.status()}\n")

    task_type = input("Task type (sales_outreach / support_ticket): ").strip()
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
