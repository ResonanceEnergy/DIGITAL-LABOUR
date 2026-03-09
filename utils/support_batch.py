"""Support batch runner — process multiple tickets for testing and production.

Usage:
    python utils/support_batch.py                       # run default 10-ticket test batch
    python utils/support_batch.py --provider anthropic  # force provider
    python utils/support_batch.py --export-csv results.csv
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.support.runner import run_pipeline, save_output

# ── Default 10 test tickets (diverse categories) ───────────────────────────
DEFAULT_TICKETS = [
    {
        "id": "T001",
        "category": "billing",
        "ticket": "I was charged $49.99 twice this month for the same subscription. "
                  "My bank statement shows two identical charges on March 1 and March 3. "
                  "I need the duplicate charge refunded immediately.",
    },
    {
        "id": "T002",
        "category": "bug",
        "ticket": "The export to CSV feature is broken since your last update. "
                  "When I click Export, the page just spins for 30 seconds and then "
                  "shows a blank white screen. I'm using Chrome 122 on Windows 11. "
                  "This was working fine last week.",
    },
    {
        "id": "T003",
        "category": "shipping",
        "ticket": "I ordered a wireless keyboard (order #8847) on February 25 and "
                  "the tracking hasn't updated since March 1. It still says 'In Transit' "
                  "to Denver, CO. It's been 7 days with no movement. Where is my package?",
    },
    {
        "id": "T004",
        "category": "refund_threat",
        "ticket": "This is the third time I'm reaching out about order #4521. "
                  "I received a damaged monitor and nobody has responded to my emails. "
                  "If I don't get a full refund by end of day, I'm filing a chargeback "
                  "with my credit card company and leaving a review on every site I can find.",
    },
    {
        "id": "T005",
        "category": "onboarding",
        "ticket": "Hi, I just signed up for the Pro plan and I'm trying to set up "
                  "my team workspace. I've invited 3 team members but they say they "
                  "never received the invitation emails. I've double-checked the email "
                  "addresses and they're correct. How do I get them access?",
    },
    {
        "id": "T006",
        "category": "password_reset",
        "ticket": "I can't log into my account. I've tried resetting my password "
                  "3 times but I never receive the reset email. I've checked spam. "
                  "My email is sarah@example.com. I need access urgently because "
                  "I have a presentation tomorrow using your platform.",
    },
    {
        "id": "T007",
        "category": "feature_request",
        "ticket": "Would it be possible to add dark mode to the dashboard? "
                  "I work late nights and the bright white interface is really hard "
                  "on my eyes. I know several other users have asked for this too. "
                  "Even a simple toggle would be great.",
    },
    {
        "id": "T008",
        "category": "complaint",
        "ticket": "Your customer service has been absolutely terrible. I've been "
                  "a paying customer for 2 years and every time I have an issue it "
                  "takes 3-5 days to get a response. My competitors use tools with "
                  "instant chat support. Why am I paying premium prices for this?",
    },
    {
        "id": "T009",
        "category": "upgrade",
        "ticket": "I'm currently on the Starter plan but I'm hitting the 1000 record "
                  "limit constantly. Can you tell me the difference between Pro and "
                  "Enterprise plans? Specifically, I need to know about API rate limits, "
                  "SSO support, and whether I can add custom fields. We have about 50 users.",
    },
    {
        "id": "T010",
        "category": "cancellation",
        "ticket": "I'd like to cancel my subscription effective immediately. "
                  "I've found an alternative that better fits our needs. Please confirm "
                  "cancellation and let me know if there will be any charges. Also, "
                  "how long will I have access to download my data after cancellation?",
    },
]


def run_batch(
    tickets: list[dict] | None = None,
    provider: str | None = None,
) -> list[dict]:
    """Process all tickets and return results."""
    tickets = tickets or DEFAULT_TICKETS
    results = []
    total_start = time.time()

    print(f"\n{'='*60}")
    print(f"  SUPPORT BATCH — {len(tickets)} tickets — provider: {provider or 'default'}")
    print(f"{'='*60}\n")

    for i, t in enumerate(tickets, 1):
        tid = t.get("id", f"T{i:03d}")
        cat = t.get("category", "unknown")
        ticket_text = t["ticket"]

        print(f"[{i}/{len(tickets)}] {tid} ({cat}) — {ticket_text[:60]}...")
        start = time.time()

        try:
            output = run_pipeline(ticket_text, provider=provider)
            elapsed = round(time.time() - start, 1)

            if output:
                # Save output
                save_output(output)
                qa_status = "PASS"
                result = {
                    "ticket_id": tid,
                    "category_expected": cat,
                    "category_actual": output.category,
                    "severity": output.severity,
                    "sentiment": output.sentiment,
                    "qa_status": qa_status,
                    "escalation": output.escalation.required,
                    "confidence": output.confidence,
                    "time_s": elapsed,
                    "provider": provider or "default",
                    "reply_preview": output.draft_reply[:100] + "..." if len(output.draft_reply) > 100 else output.draft_reply,
                }
                print(f"  → {qa_status} | {output.category} | sev={output.severity} | {elapsed}s")
                if output.escalation.required:
                    print(f"  → ESCALATION: {output.escalation.team} — {output.escalation.reason}")
            else:
                elapsed = round(time.time() - start, 1)
                result = {
                    "ticket_id": tid,
                    "category_expected": cat,
                    "category_actual": "",
                    "severity": "",
                    "sentiment": "",
                    "qa_status": "FAIL",
                    "escalation": False,
                    "confidence": 0.0,
                    "time_s": elapsed,
                    "provider": provider or "default",
                    "reply_preview": "FAILED — no output",
                }
                print(f"  → FAIL | {elapsed}s")
        except Exception as e:
            elapsed = round(time.time() - start, 1)
            result = {
                "ticket_id": tid,
                "category_expected": cat,
                "category_actual": "",
                "severity": "",
                "sentiment": "",
                "qa_status": "ERROR",
                "escalation": False,
                "confidence": 0.0,
                "time_s": elapsed,
                "provider": provider or "default",
                "reply_preview": f"ERROR: {e}",
            }
            print(f"  → ERROR: {e} | {elapsed}s")

        results.append(result)

    # Summary
    total_time = round(time.time() - total_start, 1)
    passed = sum(1 for r in results if r["qa_status"] == "PASS")
    failed = sum(1 for r in results if r["qa_status"] == "FAIL")
    errors = sum(1 for r in results if r["qa_status"] == "ERROR")
    escalations = sum(1 for r in results if r.get("escalation"))
    avg_time = round(sum(r["time_s"] for r in results) / len(results), 1) if results else 0
    pass_rate = round(passed / len(results) * 100, 1) if results else 0

    print(f"\n{'='*60}")
    print(f"  RESULTS: {passed} PASS / {failed} FAIL / {errors} ERROR")
    print(f"  Pass rate: {pass_rate}%")
    print(f"  Escalations: {escalations}")
    print(f"  Avg time: {avg_time}s | Total: {total_time}s")
    print(f"{'='*60}\n")

    # Save summary
    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total_tickets": len(results),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "pass_rate_pct": pass_rate,
        "escalations": escalations,
        "avg_time_s": avg_time,
        "total_time_s": total_time,
        "provider": provider or "default",
    }
    summary_path = PROJECT_ROOT / "output" / "support_batch_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[SAVED] Summary → {summary_path}")

    return results


def export_csv(results: list[dict], path: str):
    if not results:
        return
    fieldnames = list(results[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"[CSV] Exported → {path}")


def main():
    parser = argparse.ArgumentParser(description="Support Agent Batch Runner")
    parser.add_argument("--provider", default=None,
                        choices=["openai", "anthropic", "gemini", "grok"],
                        help="Force LLM provider")
    parser.add_argument("--export-csv", default=None, help="Export results to CSV")
    args = parser.parse_args()

    results = run_batch(provider=args.provider)

    csv_path = args.export_csv or str(PROJECT_ROOT / "output" / "support_batch_results.csv")
    export_csv(results, csv_path)


if __name__ == "__main__":
    main()
