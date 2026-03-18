"""4-agent stress test — 40 mixed tasks across all providers.

Validates system stability, provider fallback, QA rates, and throughput
under sustained load.

Usage:
    python tests/stress_test.py
    python tests/stress_test.py --count 10          # 10 tasks instead of 40
    python tests/stress_test.py --provider openai    # Force one provider
"""

import argparse
import json
import random
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from dispatcher.router import create_event, route_task

# ── Task Templates ──────────────────────────────────────────────────────────

PROVIDERS = ["openai", "grok", "anthropic", "gemini"]

SALES_VARIANTS = [
    {"company": "FinWise Analytics", "role": "CTO", "tone": "direct"},
    {"company": "GreenPulse Energy", "role": "VP Sales", "tone": "consultative"},
    {"company": "MediSync Health", "role": "Head of Growth", "tone": "direct"},
    {"company": "CloudForge AI", "role": "CEO", "tone": "casual"},
    {"company": "UrbanNest Realty", "role": "Marketing Director", "tone": "direct"},
]

SUPPORT_VARIANTS = [
    {"ticket": "Can't export my data to CSV. The export button spins forever. Tried Chrome and Firefox."},
    {"ticket": "I was charged twice for my subscription this month. Transaction IDs: TXN-4401 and TXN-4402."},
    {"ticket": "The API returns 500 errors intermittently. Happens about 20% of requests. No pattern I can see."},
    {"ticket": "I need to add 3 new team members but the invite feature says 'limit reached'. We're on the Growth plan."},
    {"ticket": "My dashboard shows stale data from 2 days ago. Normally refreshes every hour. Other team members see the same."},
]

CONTENT_VARIANTS = [
    {"source_text": "5 Lessons From Scaling a SaaS to $1M ARR\n\nLesson 1: Focus beats features. We grew fastest when we said no to 80% of feature requests and doubled down on the 3 things our power users loved. Lesson 2: Pricing is a feature. Switching from flat to usage-based pricing increased expansion revenue 3x. Lesson 3: Support is marketing. Our NPS went from 32 to 71 when we committed to 1-hour response times."},
    {"source_text": "The Death of Manual Data Entry\n\nPaper invoices, handwritten forms, and manual spreadsheet entry cost US businesses $4.7 trillion annually in labor. AI document extraction now achieves 99% accuracy on structured documents and 94% on handwritten text. The ROI is immediate: a 10-person accounts payable team can process 5x the volume with 2 people and an AI extraction pipeline."},
    {"source_text": "Why We Switched From Kubernetes to Serverless\n\nAfter 18 months of K8s operations, our 4-person DevOps team was spending 60% of their time on cluster maintenance. We migrated 23 microservices to AWS Lambda over 6 weeks. Monthly infra cost dropped from $12,000 to $3,200. On-call incidents went from 8/month to 1/month. The team now builds features instead of babysitting nodes."},
]

EXTRACT_VARIANTS = [
    {"document_text": "PURCHASE ORDER #PO-2025-0099\nDate: Feb 1, 2025\nVendor: Steel Solutions Ltd\nItem: Structural Steel Beams I-100\nQty: 500\nUnit Price: $45.00\nTotal: $22,500.00\nDelivery: March 15, 2025\nTerms: Net 45", "doc_type": "invoice"},
    {"document_text": "EMPLOYMENT AGREEMENT\nThis agreement between TechFlow Inc. and Jordan Rivera\nPosition: Senior Software Engineer\nStart Date: March 1, 2025\nBase Salary: $175,000/year\nEquity: 0.05% vesting over 4 years with 1-year cliff\nBenefits: Medical, dental, vision, 401k match 4%\nNon-compete: 12 months, 50-mile radius\nGoverning Law: State of California", "doc_type": "contract"},
    {"document_text": "RESUME\nSamira Chen\nData Science Lead | san.chen@email.com | San Francisco, CA\n\nExperience:\n- Lead Data Scientist, NovaTech (2022-present): Built ML pipeline for fraud detection, reduced false positives 45%\n- Senior Analyst, DataCorp (2019-2022): Developed customer churn model, saved $2.1M annually\n\nEducation: MS Statistics, Stanford University (2019)\nSkills: Python, R, TensorFlow, Spark, SQL, A/B Testing", "doc_type": "resume"},
]


def generate_task(task_type: str, provider: str | None = None) -> dict:
    """Generate a random task variant for the given type."""
    if task_type == "sales_outreach":
        inputs = random.choice(SALES_VARIANTS).copy()
        inputs["product"] = "AI-powered business automation agents that handle sales, support, content, and data extraction."
    elif task_type == "support_ticket":
        inputs = random.choice(SUPPORT_VARIANTS).copy()
        inputs["kb"] = "Standard troubleshooting: check browser cache, verify account status, check system status page."
        inputs["policies"] = "SLA: 15-min response for urgent, 1-hour for normal. Escalate to engineering after 2 failed workarounds."
    elif task_type == "content_repurpose":
        inputs = random.choice(CONTENT_VARIANTS).copy()
    elif task_type == "doc_extract":
        inputs = random.choice(EXTRACT_VARIANTS).copy()
    else:
        raise ValueError(f"Unknown task type: {task_type}")

    if provider:
        inputs["provider"] = provider

    return inputs


# ── Stress Test Runner ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Bit Rage Labour Stress Test")
    parser.add_argument("--count", type=int, default=40, help="Total tasks to run (default: 40)")
    parser.add_argument("--provider", help="Force a specific provider for all tasks")
    args = parser.parse_args()

    task_types = ["sales_outreach", "support_ticket", "content_repurpose", "doc_extract"]
    tasks_per_type = max(1, args.count // len(task_types))
    remainder = args.count - (tasks_per_type * len(task_types))

    # Build task schedule — round-robin with provider rotation
    schedule = []
    for i, tt in enumerate(task_types):
        extra = 1 if i < remainder else 0
        for j in range(tasks_per_type + extra):
            prov = args.provider or PROVIDERS[j % len(PROVIDERS)]
            schedule.append((tt, prov))

    random.shuffle(schedule)

    print("\n" + "=" * 70)
    print("  BIT RAGE LABOUR — 4-AGENT STRESS TEST")
    print(f"  Tasks: {len(schedule)} | Providers: {args.provider or 'rotating'}")
    print("=" * 70)

    results = []
    passed = 0
    failed = 0
    crashed = 0
    total_time = 0

    for idx, (task_type, provider) in enumerate(schedule, 1):
        print(f"\n[{idx}/{len(schedule)}] {task_type} via {provider}...", end=" ", flush=True)
        inputs = generate_task(task_type, provider=provider)
        event = create_event(task_type, inputs, client_id="stress-test")

        try:
            start = time.time()
            result = route_task(event)
            elapsed = time.time() - start
            total_time += elapsed

            qa = result.get("qa", {}).get("status", "UNKNOWN")
            ok = qa == "PASS"
            if ok:
                passed += 1
                print(f"✅ {qa} ({elapsed:.1f}s)")
            else:
                failed += 1
                issues = result.get("qa", {}).get("issues", [])
                print(f"❌ {qa} ({elapsed:.1f}s) {issues[:1]}")

            results.append({
                "index": idx,
                "task_type": task_type,
                "provider": provider,
                "qa_status": qa,
                "latency_s": round(elapsed, 2),
                "passed": ok,
            })

        except Exception as e:
            crashed += 1
            print(f"💥 CRASH: {e}")
            results.append({
                "index": idx,
                "task_type": task_type,
                "provider": provider,
                "qa_status": "CRASH",
                "latency_s": 0,
                "passed": False,
                "error": str(e),
            })

    # ── Report ──────────────────────────────────────────────────────────────

    total = len(schedule)
    print("\n" + "=" * 70)
    print("  STRESS TEST REPORT")
    print("=" * 70)

    # Per-agent breakdown
    print(f"\n  {'Agent':<25} {'Pass':>6} {'Fail':>6} {'Crash':>6} {'Rate':>8} {'Avg(s)':>8}")
    print(f"  {'-'*25} {'-'*6} {'-'*6} {'-'*6} {'-'*8} {'-'*8}")
    for tt in task_types:
        tt_results = [r for r in results if r["task_type"] == tt]
        tt_pass = sum(1 for r in tt_results if r["passed"])
        tt_fail = sum(1 for r in tt_results if not r["passed"] and r["qa_status"] != "CRASH")
        tt_crash = sum(1 for r in tt_results if r["qa_status"] == "CRASH")
        tt_total = len(tt_results)
        rate = f"{tt_pass / tt_total * 100:.0f}%" if tt_total else "N/A"
        avg = sum(r["latency_s"] for r in tt_results) / tt_total if tt_total else 0
        print(f"  {tt:<25} {tt_pass:>6} {tt_fail:>6} {tt_crash:>6} {rate:>8} {avg:>7.1f}s")

    # Per-provider breakdown
    print(f"\n  {'Provider':<25} {'Pass':>6} {'Fail':>6} {'Rate':>8} {'Avg(s)':>8}")
    print(f"  {'-'*25} {'-'*6} {'-'*6} {'-'*8} {'-'*8}")
    for prov in sorted(set(r["provider"] for r in results)):
        p_results = [r for r in results if r["provider"] == prov]
        p_pass = sum(1 for r in p_results if r["passed"])
        p_fail = sum(1 for r in p_results if not r["passed"])
        p_total = len(p_results)
        rate = f"{p_pass / p_total * 100:.0f}%" if p_total else "N/A"
        avg = sum(r["latency_s"] for r in p_results) / p_total if p_total else 0
        print(f"  {prov:<25} {p_pass:>6} {p_fail:>6} {rate:>8} {avg:>7.1f}s")

    # Totals
    print(f"\n  TOTAL: {passed}/{total} passed ({passed / total * 100:.0f}%)")
    print(f"  Failed: {failed} | Crashed: {crashed}")
    print(f"  Total time: {total_time:.1f}s | Avg: {total_time / total:.1f}s/task")

    if passed == total:
        print("\n  ✅ ALL STRESS TESTS PASSED")
    elif passed / total >= 0.8:
        print(f"\n  ⚠️  {passed / total * 100:.0f}% PASS RATE — ACCEPTABLE")
    else:
        print(f"\n  ❌ {passed / total * 100:.0f}% PASS RATE — BELOW THRESHOLD")

    # Save results
    results_dir = PROJECT_ROOT / "tests" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    results_file = results_dir / "stress_test_results.json"
    results_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n  Results saved → {results_file}")

    return 0 if passed / total >= 0.8 else 1


if __name__ == "__main__":
    sys.exit(main())
