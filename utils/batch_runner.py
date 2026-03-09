"""Batch runner — process multiple leads from CSV or inline list.

Usage:
    python utils/batch_runner.py                          # run default 10-lead test batch
    python utils/batch_runner.py --csv leads.csv          # from CSV file
    python utils/batch_runner.py --provider gemini        # force provider
    python utils/batch_runner.py --export-csv results.csv # also export CSV
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.sales_ops.runner import run_pipeline, save_output

# ── Default 10-lead test batch ──────────────────────────────────────────────
DEFAULT_LEADS = [
    {"company": "Notion", "role": "Head of Growth", "vertical": "SaaS"},
    {"company": "Gymshark", "role": "Director of Marketing", "vertical": "DTC/eCommerce"},
    {"company": "Ramp", "role": "VP of Sales", "vertical": "Fintech"},
    {"company": "Deel", "role": "Head of Partnerships", "vertical": "B2B SaaS"},
    {"company": "ServiceTitan", "role": "Chief Revenue Officer", "vertical": "Vertical SaaS"},
    {"company": "Joe's Plumbing & HVAC", "role": "Owner", "vertical": "Local Service"},
    {"company": "Bishop & Associates Law", "role": "Managing Partner", "vertical": "Professional Services"},
    {"company": "Webflow", "role": "Head of Demand Gen", "vertical": "SaaS"},
    {"company": "Triple Whale", "role": "CEO", "vertical": "Agency/Analytics"},
    {"company": "Semrush", "role": "Director of Business Development", "vertical": "MarTech"},
]


def load_csv(path: str) -> list[dict]:
    leads = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            leads.append({
                "company": row.get("company", ""),
                "role": row.get("role", ""),
                "vertical": row.get("vertical", ""),
            })
    return leads


def export_csv(results: list[dict], path: str):
    if not results:
        return
    fieldnames = [
        "company", "role", "vertical", "qa_status", "provider", "time_s",
        "industry", "company_size", "recent_signal", "pain_point",
        "email_1_subject", "email_1_body",
        "email_2_subject", "email_2_body",
        "email_3_subject", "email_3_body",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)
    print(f"[CSV] Exported {len(results)} rows → {path}")


def run_batch(leads: list[dict], provider: str | None = None, csv_out: str | None = None):
    results = []
    passes = 0
    fails = 0
    total_time = 0
    start_all = time.time()

    print(f"\n{'='*60}")
    print(f"  BATCH RUN: {len(leads)} leads | Provider: {provider or 'default'}")
    print(f"{'='*60}\n")

    for i, lead in enumerate(leads, 1):
        company = lead["company"]
        role = lead["role"]
        vertical = lead.get("vertical", "")

        print(f"\n[{i}/{len(leads)}] {company} / {role} ({vertical})")
        print("-" * 50)

        t0 = time.time()
        try:
            output = run_pipeline(company, role, provider=provider)
            elapsed = round(time.time() - t0, 1)
            total_time += elapsed

            if output:
                save_output(output)
                status = output.qa_status
                if status == "PASS":
                    passes += 1
                else:
                    fails += 1

                row = {
                    "company": company,
                    "role": role,
                    "vertical": vertical,
                    "qa_status": status,
                    "provider": provider or "default",
                    "time_s": elapsed,
                    "industry": output.lead_enrichment.industry,
                    "company_size": output.lead_enrichment.company_size_estimate,
                    "recent_signal": output.lead_enrichment.recent_signal,
                    "pain_point": output.lead_enrichment.role_relevant_pain,
                    "email_1_subject": output.emails.primary_email.subject,
                    "email_1_body": output.emails.primary_email.body,
                    "email_2_subject": output.emails.follow_up_1.subject,
                    "email_2_body": output.emails.follow_up_1.body,
                    "email_3_subject": output.emails.follow_up_2.subject,
                    "email_3_body": output.emails.follow_up_2.body,
                }
                results.append(row)
            else:
                fails += 1
                results.append({"company": company, "role": role, "vertical": vertical, "qa_status": "ERROR", "provider": provider or "default", "time_s": elapsed})

        except Exception as e:
            elapsed = round(time.time() - t0, 1)
            fails += 1
            print(f"[ERROR] {e}")
            results.append({"company": company, "role": role, "vertical": vertical, "qa_status": "ERROR", "provider": provider or "default", "time_s": elapsed})

    # ── Summary ─────────────────────────────────────────────────────────────
    wall_time = round(time.time() - start_all, 1)
    pass_rate = round(passes / len(leads) * 100, 1) if leads else 0

    print(f"\n{'='*60}")
    print(f"  BATCH COMPLETE")
    print(f"{'='*60}")
    print(f"  Total:     {len(leads)}")
    print(f"  PASS:      {passes}")
    print(f"  FAIL/ERR:  {fails}")
    print(f"  Pass Rate: {pass_rate}%  {'✅ ABOVE 80%' if pass_rate >= 80 else '❌ BELOW 80% — FIX PROMPTS'}")
    print(f"  Avg Time:  {round(total_time / len(leads), 1)}s/lead")
    print(f"  Wall Time: {wall_time}s")
    print(f"{'='*60}\n")

    if csv_out:
        export_csv(results, csv_out)

    # Save summary
    summary_path = PROJECT_ROOT / "output" / "batch_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "total": len(leads),
        "passes": passes,
        "fails": fails,
        "pass_rate": pass_rate,
        "avg_time_s": round(total_time / len(leads), 1) if leads else 0,
        "wall_time_s": wall_time,
        "provider": provider or "default",
        "results": [{"company": r["company"], "role": r["role"], "qa_status": r.get("qa_status", "ERROR"), "time_s": r.get("time_s", 0)} for r in results],
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"[SUMMARY] {summary_path}")

    return results, summary


def main():
    parser = argparse.ArgumentParser(description="Batch Sales Ops Runner")
    parser.add_argument("--csv", help="CSV file with columns: company, role, vertical")
    parser.add_argument("--provider", choices=["openai", "anthropic", "gemini", "grok"], help="Force LLM provider")
    parser.add_argument("--export-csv", help="Export results to CSV")
    args = parser.parse_args()

    leads = load_csv(args.csv) if args.csv else DEFAULT_LEADS
    csv_out = args.export_csv or str(PROJECT_ROOT / "output" / "batch_results.csv")

    run_batch(leads, provider=args.provider, csv_out=csv_out)


if __name__ == "__main__":
    main()
