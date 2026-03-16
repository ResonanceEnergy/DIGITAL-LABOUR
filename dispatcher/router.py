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

    # ── BILLING — record usage and calculate charge ──
    if event["qa"]["status"] == "PASS":
        try:
            from billing.tracker import BillingTracker
            bt = BillingTracker()
            billing_result = bt.record_and_bill(
                client=event.get("client_id", "direct"),
                task_type=task_type,
                task_id=event.get("event_id", ""),
                llm_cost=event.get("metrics", {}).get("cost_estimate", 0.0),
            )
            event["billing"]["amount"] = billing_result.get("charge", 0.0)
            event["billing"]["status"] = "billed"
        except Exception:
            pass  # Never let billing failures break task delivery

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
