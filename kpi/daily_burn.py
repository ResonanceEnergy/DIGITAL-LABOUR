"""Daily burn monitor — Phase 5 Financial Observability.

Compares today's LLM spend against economics.json thresholds and
writes a daily report to kpi/reports/burn_YYYY-MM-DD.json.

Usage:
    python kpi/daily_burn.py            # print today's burn
    python kpi/daily_burn.py --report   # write JSON report file
"""
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("kpi.daily_burn")

_ECONOMICS_PATH = PROJECT_ROOT / "config" / "economics.json"
_REPORTS_DIR = PROJECT_ROOT / "kpi" / "reports"


def _load_economics() -> dict:
    if _ECONOMICS_PATH.exists():
        try:
            return json.loads(_ECONOMICS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "min_margin_pct": 85.0,
        "max_daily_burn_usd": 50.0,
        "cost_explosion_multiplier": 2.0,
        "per_agent_alert_ceiling_usd": 5.0,
    }


def run_burn_check(write_report: bool = False) -> dict:
    """Compute today's burn, compare to thresholds, optionally write report.

    Returns a dict with keys: date, total_cost_usd, status, alerts, per_agent.
    """
    from billing.tracker import BillingTracker

    economics = _load_economics()
    max_burn = economics.get("max_daily_burn_usd", 50.0)
    explode_mult = economics.get("cost_explosion_multiplier", 2.0)
    per_agent_ceiling = economics.get("per_agent_alert_ceiling_usd", 5.0)
    min_margin = economics.get("min_margin_pct", 85.0)

    bt = BillingTracker()
    today_str = date.today().isoformat()
    yesterday_str = str(date.fromordinal(date.today().toordinal() - 1))

    # Per-agent P&L for today and yesterday
    today_data = bt.per_agent_economics(days=1)
    yesterday_data = bt.per_agent_economics(days=2)  # 2-day window to get yesterday

    total_cost_today = sum(v.get("llm_cost", 0.0) for v in today_data.values())
    total_revenue_today = sum(v.get("revenue", 0.0) for v in today_data.values())
    total_cost_yesterday = max(
        sum(v.get("llm_cost", 0.0) for v in yesterday_data.values()) - total_cost_today, 0.0
    )

    alerts: list[str] = []

    # Alert: burn over daily ceiling
    if total_cost_today >= max_burn:
        msg = f"[BURN_CEILING] Daily cost ${total_cost_today:.4f} >= max ${max_burn:.2f}"
        logger.critical(msg)
        alerts.append(msg)

    # Alert: cost explosion vs yesterday
    if total_cost_yesterday > 0 and total_cost_today >= total_cost_yesterday * explode_mult:
        msg = (
            f"[COST_EXPLOSION] Today ${total_cost_today:.4f} "
            f">= {explode_mult}× yesterday ${total_cost_yesterday:.4f}"
        )
        logger.critical(msg)
        alerts.append(msg)

    # Alert: per-agent ceiling breaches
    per_agent_alerts: list[str] = []
    for agent, metrics in today_data.items():
        agent_cost = metrics.get("llm_cost", 0.0)
        if agent_cost >= per_agent_ceiling:
            msg = f"[AGENT_CEILING] {agent} cost ${agent_cost:.4f} >= ${per_agent_ceiling:.2f}"
            logger.warning(msg)
            per_agent_alerts.append(msg)

    # Alert: margin below threshold
    if total_revenue_today > 0:
        margin_pct = (total_revenue_today - total_cost_today) / total_revenue_today * 100
        if margin_pct < min_margin:
            msg = f"[MARGIN_ALERT] Margin {margin_pct:.1f}% < target {min_margin:.1f}%"
            logger.warning(msg)
            alerts.append(msg)
    else:
        margin_pct = 0.0

    overall_status = "CRITICAL" if any("[BURN_CEILING]" in a or "[COST_EXPLOSION]" in a for a in alerts) else (
        "WARNING" if alerts or per_agent_alerts else "OK"
    )

    report = {
        "date": today_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_cost_usd": round(total_cost_today, 6),
        "total_revenue_usd": round(total_revenue_today, 6),
        "margin_pct": round(margin_pct, 2),
        "cost_yesterday_usd": round(total_cost_yesterday, 6),
        "status": overall_status,
        "alerts": alerts + per_agent_alerts,
        "per_agent": {
            agent: {
                "tasks": m.get("tasks", 0),
                "llm_cost": round(m.get("llm_cost", 0.0), 6),
                "revenue": round(m.get("revenue", 0.0), 6),
                "margin_pct": round(m.get("margin_pct", 0.0), 2),
            }
            for agent, m in today_data.items()
        },
        "thresholds": {
            "max_daily_burn_usd": max_burn,
            "cost_explosion_multiplier": explode_mult,
            "per_agent_alert_ceiling_usd": per_agent_ceiling,
            "min_margin_pct": min_margin,
        },
    }

    if write_report:
        _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = _REPORTS_DIR / f"burn_{today_str}.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        logger.info("Burn report written: %s", report_path)

    return report


if __name__ == "__main__":
    write = "--report" in sys.argv
    result = run_burn_check(write_report=write)
    print(json.dumps(result, indent=2))
