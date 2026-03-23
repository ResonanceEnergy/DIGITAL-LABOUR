"""End-to-end pipeline test — validates the full task lifecycle.

Exercises: create_event → route_task → QA → delivery → KPI logging → billing
Tests all 4 agent types with a single task each.

Usage:
    python tests/pipeline_test.py
    python tests/pipeline_test.py --agent sales_outreach
    python tests/pipeline_test.py --provider openai
"""

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from dispatcher.router import create_event, route_task
from delivery.sender import deliver
from billing.tracker import BillingTracker
from kpi.logger import log_task_event

# ── Test Payloads ───────────────────────────────────────────────────────────

TEST_INPUTS = {
    "sales_outreach": {
        "company": "TestCorp",
        "role": "VP Engineering",
        "product": "AI-powered process automation for mid-market SaaS companies.",
        "tone": "direct",
    },
    "support_ticket": {
        "ticket": "I can't log in to my account. I've tried resetting my password 3 times but the reset email never arrives. My email is user@example.com. Urgent — I have a demo in 1 hour.",
        "kb": "Password resets are sent via SendGrid. Check spam folder first. If still failing, verify email is in Auth0. Manual reset available in admin panel.",
        "policies": "SLA: respond within 15 minutes for urgent tickets. Offer workaround first, then escalate to engineering if auth system issue.",
    },
    "content_repurpose": {
        "source_text": (
            "How We Cut Our Cloud Bill by 40% in 3 Months\n\n"
            "Our team of 12 engineers was spending $45,000/month on AWS. After a systematic audit, "
            "we identified three categories of waste: oversized instances (30% of spend), unused EBS volumes "
            "(8% of spend), and unoptimized data transfer (12% of spend). By rightsizing instances with AWS "
            "Compute Optimizer, cleaning up 200+ orphaned volumes, and implementing CloudFront for static "
            "assets, we reduced our monthly bill to $27,000. The entire project took 3 sprints and zero downtime."
        ),
    },
    "doc_extract": {
        "document_text": (
            "INVOICE #INV-2025-0042\n"
            "Date: January 15, 2025\n"
            "Due: February 14, 2025\n\n"
            "From: DIGITAL LABOUR LLC\n"
            "123 Innovation Drive, Austin TX 78701\n\n"
            "To: Acme Widgets Inc.\n"
            "456 Commerce Blvd, Denver CO 80202\n\n"
            "Description                    Qty    Rate      Amount\n"
            "Sales Lead Enrichment          50     $2.40     $120.00\n"
            "Support Ticket Resolution      30     $1.00     $30.00\n\n"
            "Subtotal: $150.00\n"
            "Tax (0%): $0.00\n"
            "Total: $150.00\n\n"
            "Payment Terms: Net 30\n"
            "Bank: Chase | Acct: XXXX-1234 | Routing: XXXX-5678"
        ),
        "doc_type": "invoice",
    },
}


# ── Pipeline Test ───────────────────────────────────────────────────────────

def run_test(task_type: str, provider: str | None = None) -> dict:
    """Run a single end-to-end pipeline test for one agent type."""
    print(f"\n{'='*60}")
    print(f"  PIPELINE TEST: {task_type}")
    print(f"  Provider: {provider or 'default'}")
    print(f"{'='*60}")

    inputs = TEST_INPUTS[task_type].copy()
    if provider:
        inputs["provider"] = provider

    # 1. Create event
    print("\n[1/5] Creating event...")
    event = create_event(task_type, inputs, client_id="pipeline-test")
    event_id = event["event_id"]
    print(f"  Event ID: {event_id}")

    # 2. Route to agent (runs the full agent pipeline)
    print("[2/5] Routing to agent...")
    start = time.time()
    result = route_task(event)
    elapsed = time.time() - start

    qa_status = result.get("qa", {}).get("status", "UNKNOWN")
    print(f"  QA Status: {qa_status}")
    print(f"  Latency: {elapsed:.1f}s")

    # 3. Deliver output
    print("[3/5] Delivering output...")
    delivery = deliver(
        task_id=event_id,
        task_type=task_type,
        outputs=result.get("outputs", {}),
        client="pipeline-test",
        method="file",
    )
    print(f"  Delivery: {delivery.get('status', 'unknown')} → {delivery.get('path', 'N/A')}")

    # 4. Log to KPI
    print("[4/5] Logging to KPI...")
    try:
        log_task_event(
            task_id=event_id,
            task_type=task_type,
            status="completed" if qa_status == "PASS" else "failed",
            client="pipeline-test",
            provider=provider or "default",
            qa_status=qa_status,
            duration_s=elapsed,
        )
        print("  KPI logged ✓")
    except Exception as e:
        print(f"  KPI log error: {e}")

    # 5. Bill the task
    print("[5/5] Recording billing...")
    try:
        bt = BillingTracker()
        bt.record_usage("pipeline-test", task_type, llm_cost=0.03)
        print("  Billing recorded ✓")
    except Exception as e:
        print(f"  Billing error: {e}")

    # Summary
    passed = qa_status == "PASS"
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n  RESULT: {status} | {task_type} | {elapsed:.1f}s")

    if not passed:
        issues = result.get("qa", {}).get("issues", [])
        if issues:
            print(f"  Issues: {issues}")

    return {
        "task_type": task_type,
        "event_id": event_id,
        "qa_status": qa_status,
        "latency_s": round(elapsed, 2),
        "delivery": delivery.get("status"),
        "passed": passed,
    }


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="DIGITAL LABOUR Pipeline Test")
    parser.add_argument("--agent", choices=list(TEST_INPUTS.keys()), help="Test a specific agent only")
    parser.add_argument("--provider", help="Force a specific LLM provider")
    parser.add_argument("--live", action="store_true",
                        help="Required flag to confirm real API calls and spend.")
    args = parser.parse_args()

    if not args.live:
        print("\n[PIPELINE TEST] Dry-run mode — no API calls made.")
        print("  This test fires real LLM calls across all 4 agent types.")
        print("  Each run costs ~$0.15-0.50 depending on provider.")
        print("\n  To actually run: python tests/pipeline_test.py --live")
        print("  Single agent:   python tests/pipeline_test.py --live --agent sales_outreach")
        return 0

    agents = [args.agent] if args.agent else list(TEST_INPUTS.keys())

    print("\n" + "=" * 60)
    print("  DIGITAL LABOUR — END-TO-END PIPELINE TEST")
    print(f"  Agents: {', '.join(agents)}")
    print("=" * 60)

    results = []
    for agent_type in agents:
        try:
            result = run_test(agent_type, provider=args.provider)
            results.append(result)
        except Exception as e:
            print(f"\n  ❌ CRASH: {agent_type} — {e}")
            results.append({
                "task_type": agent_type,
                "qa_status": "CRASH",
                "latency_s": 0,
                "passed": False,
                "error": str(e),
            })

    # Final report
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    total_time = sum(r.get("latency_s", 0) for r in results)

    print("\n" + "=" * 60)
    print("  PIPELINE TEST REPORT")
    print("=" * 60)
    print(f"\n  {'Agent':<25} {'Status':<10} {'Time':>8}")
    print(f"  {'-'*25} {'-'*10} {'-'*8}")
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  {r['task_type']:<25} {status:<10} {r.get('latency_s', 0):>6.1f}s")

    print(f"\n  Total: {passed}/{total} passed | {total_time:.1f}s total")

    if passed == total:
        print("\n  ✅ ALL PIPELINE TESTS PASSED")
    else:
        print(f"\n  ❌ {total - passed} PIPELINE TEST(S) FAILED")

    # Save results
    results_dir = PROJECT_ROOT / "tests" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    results_file = results_dir / "pipeline_test_results.json"
    results_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n  Results saved → {results_file}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
