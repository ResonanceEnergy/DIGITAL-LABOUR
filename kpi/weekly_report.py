"""KPI Logger + Weekly Report Generator.

Usage:
    python weekly_report.py                    # Report for current week
    python weekly_report.py --date 2026-03-07  # Report for week containing date
"""

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "kpi" / "logs"


def _qa_passed(event: dict) -> bool:
    """Check QA status — supports both old and new event formats."""
    # New format: top-level qa_status
    if event.get("qa_status") == "PASS":
        return True
    # Old format: nested qa.status
    qa = event.get("qa", {})
    if isinstance(qa, dict) and qa.get("status") == "PASS":
        return True
    return False


def load_events(start_date: str, end_date: str) -> list[dict]:
    """Load all events between start and end dates (inclusive)."""
    events = []
    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    while current <= end:
        log_file = LOG_DIR / f"{current.strftime('%Y-%m-%d')}.jsonl"
        if log_file.exists():
            for line in log_file.read_text(encoding="utf-8").strip().split("\n"):
                if line:
                    events.append(json.loads(line))
        current += timedelta(days=1)

    return events


def generate_report(events: list[dict], period: str) -> str:
    """Generate a markdown KPI report."""
    if not events:
        return f"# Weekly KPI Report — {period}\n\nNo events found for this period.\n"

    total = len(events)
    passed = sum(1 for e in events if _qa_passed(e))
    failed = total - passed
    pass_rate = (passed / total * 100) if total else 0

    # By type
    by_type = Counter(e.get("task_type", "unknown") for e in events)
    pass_by_type = Counter(
        e.get("task_type", "unknown")
        for e in events
        if _qa_passed(e)
    )

    # Latency — support both old (metrics.latency_ms) and new (duration_s) formats
    latencies = []
    for e in events:
        ms = e.get("metrics", {}).get("latency_ms", 0) if isinstance(e.get("metrics"), dict) else 0
        if not ms and e.get("duration_s"):
            ms = e["duration_s"] * 1000
        if ms:
            latencies.append(ms)
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    # Revenue — support both old (billing.amount) and new (cost_usd + charge) formats
    revenue_by_status = defaultdict(float)
    for e in events:
        billing = e.get("billing", {}) if isinstance(e.get("billing"), dict) else {}
        if billing:
            revenue_by_status[billing.get("status", "unbilled")] += billing.get("amount", 0)
        elif e.get("cost_usd"):
            status_key = "completed" if _qa_passed(e) else "failed"
            revenue_by_status[status_key] += e.get("cost_usd", 0)

    total_revenue = sum(revenue_by_status.values())

    report = f"""# Weekly KPI Report — {period}

## Summary
| Metric | Value |
|--------|-------|
| Total tasks | {total} |
| Passed QA | {passed} |
| Failed QA | {failed} |
| Pass rate | {pass_rate:.1f}% |
| Avg latency | {avg_latency:.0f}ms |
| Total revenue | ${total_revenue:.2f} |

## By Task Type
| Type | Total | Passed | Pass Rate |
|------|-------|--------|-----------|
"""

    for task_type, count in by_type.most_common():
        p = pass_by_type.get(task_type, 0)
        rate = (p / count * 100) if count else 0
        report += f"| {task_type} | {count} | {p} | {rate:.0f}% |\n"

    report += f"""
## Revenue by Status
| Status | Amount |
|--------|--------|
"""
    for status, amount in sorted(revenue_by_status.items()):
        report += f"| {status} | ${amount:.2f} |\n"

    report += f"""
## Action Items
"""
    if pass_rate < 80:
        report += f"- ⚠️ QA pass rate below 80% ({pass_rate:.0f}%). Fix prompts before scaling.\n"
    if avg_latency > 60000:
        report += f"- ⚠️ Average latency over 60s. Consider optimizing or caching.\n"
    if total_revenue == 0:
        report += f"- ⚠️ No revenue recorded. Update billing in event logs.\n"
    if pass_rate >= 80 and total_revenue > 0:
        report += f"- ✅ System healthy. Consider increasing volume.\n"

    report += f"\n---\n*Generated: {datetime.now(timezone.utc).isoformat()}*\n"
    return report


def main():
    parser = argparse.ArgumentParser(description="Weekly KPI Report")
    parser.add_argument("--date", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                        help="Any date in the target week (YYYY-MM-DD)")
    args = parser.parse_args()

    target = datetime.strptime(args.date, "%Y-%m-%d")
    start = target - timedelta(days=target.weekday())  # Monday
    end = start + timedelta(days=6)  # Sunday

    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    period = f"{start_str} to {end_str}"

    events = load_events(start_str, end_str)
    report = generate_report(events, period)

    # Save report
    report_dir = PROJECT_ROOT / "kpi" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"weekly_{start_str}.md"
    report_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"\n[SAVED] {report_path}")


if __name__ == "__main__":
    main()
