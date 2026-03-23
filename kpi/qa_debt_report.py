"""P3.4 — Weekly QA Debt Report Generator.

Scans QA failure data and produces a structured report:
  - Failure counts by rule_id and agent
  - Repeat offenders (3+ failures) flagged for doctrine review
  - Output to kpi/reports/qa_debt_YYYY-MM-DD.json

Usage:
    python -m kpi.qa_debt_report            # Generate report for last 7 days
    python -m kpi.qa_debt_report --days 14  # Custom window
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from kpi.logger import get_qa_failure_counts, get_repeat_offenders

REPORTS_DIR = PROJECT_ROOT / "kpi" / "reports"


def generate_qa_debt_report(days: int = 7) -> dict:
    """Generate a QA debt report for the last N days."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    failure_counts = get_qa_failure_counts(days=days)
    offenders = get_repeat_offenders(days=days, min_count=3)

    # Build per-agent summary
    agent_summary: dict[str, dict] = {}
    for key, count in failure_counts.items():
        rule_id, agent = key.split("|", 1)
        if agent not in agent_summary:
            agent_summary[agent] = {"total_failures": 0, "rules_failed": {}}
        agent_summary[agent]["total_failures"] += count
        agent_summary[agent]["rules_failed"][rule_id] = count

    # Build per-rule summary
    rule_summary: dict[str, int] = {}
    for key, count in failure_counts.items():
        rule_id = key.split("|")[0]
        rule_summary[rule_id] = rule_summary.get(rule_id, 0) + count

    report = {
        "_meta": {
            "doctrine_version": "2.0",
            "report_type": "qa_debt",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "window_days": days,
        },
        "total_qa_failures": sum(failure_counts.values()),
        "unique_rule_agent_combos": len(failure_counts),
        "doctrine_review_flags": len(offenders),
        "repeat_offenders": offenders,
        "by_agent": agent_summary,
        "by_rule": dict(sorted(rule_summary.items(), key=lambda x: x[1], reverse=True)),
        "raw_counts": failure_counts,
    }

    # Write report
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_path = REPORTS_DIR / f"qa_debt_{date_str}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


def main():
    parser = argparse.ArgumentParser(description="QA Debt Report Generator")
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days")
    args = parser.parse_args()

    report = generate_qa_debt_report(days=args.days)
    print(f"QA Debt Report ({args.days}d window)")
    print(f"  Total failures: {report['total_qa_failures']}")
    print(f"  Doctrine review flags: {report['doctrine_review_flags']}")
    if report["repeat_offenders"]:
        print("  Repeat offenders (3+):")
        for o in report["repeat_offenders"]:
            print(f"    {o['rule_id']} | {o['agent']}: {o['count']}x")
    else:
        print("  No repeat offenders")
    print(f"  Report: kpi/reports/qa_debt_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json")


if __name__ == "__main__":
    main()
