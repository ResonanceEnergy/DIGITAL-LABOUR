"""LEDGR — Chief Financial Officer Agent.

Codename: LEDGR (Lattice Engine for Dynamic Growth & Revenue)
Role: CFO — Revenue tracking, cost analysis, margin optimization, financial projections.

LEDGR reads billing data, LLM costs, client revenue, and produces financial
intelligence: P&L analysis, margin alerts, pricing recommendations, and forecasts.

Usage:
    from c_suite.ledgr import LedgrCFO
    cfo = LedgrCFO()
    report = cfo.run()              # Full financial review
    snapshot = cfo.cash_check()     # Quick revenue snapshot
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.llm_client import call_llm


# ── Financial Data Gatherers ────────────────────────────────────────────────

def _revenue_data(days: int = 30) -> dict:
    try:
        from billing.tracker import BillingTracker
        return BillingTracker().revenue_report(days=days)
    except Exception:
        return {}


def _client_economics() -> list[dict]:
    """Per-client financial summary."""
    try:
        from billing.tracker import BillingTracker
        bt = BillingTracker()
        import sqlite3
        conn = bt._conn()
        clients = conn.execute("SELECT DISTINCT client FROM usage").fetchall()
        conn.close()

        summaries = []
        for row in clients:
            client = row["client"]
            s = bt.client_summary(client, days=30)
            summaries.append(s)
        return summaries
    except Exception:
        return []


def _cost_breakdown(days: int = 30) -> dict:
    """LLM cost analysis by provider and task type."""
    try:
        from kpi.logger import get_events
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        events = get_events(start=cutoff, limit=10000)

        by_provider: dict[str, float] = {}
        by_type: dict[str, float] = {}
        total_cost = 0.0

        for e in events:
            cost = e.get("cost_usd", 0)
            provider = e.get("provider", "unknown")
            task_type = e.get("task_type", "unknown")
            by_provider[provider] = by_provider.get(provider, 0) + cost
            by_type[task_type] = by_type.get(task_type, 0) + cost
            total_cost += cost

        return {
            "total_llm_cost": round(total_cost, 4),
            "by_provider": {k: round(v, 4) for k, v in by_provider.items()},
            "by_type": {k: round(v, 4) for k, v in by_type.items()},
        }
    except Exception:
        return {}


def _invoice_history() -> dict:
    """Recent invoice summary."""
    try:
        from billing.tracker import BillingTracker
        bt = BillingTracker()
        conn = bt._conn()
        rows = conn.execute(
            "SELECT * FROM invoices ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
        conn.close()

        invoices = [dict(r) for r in rows]
        total_invoiced = sum(r.get("total", 0) for r in invoices)
        return {"count": len(invoices), "total_invoiced": round(total_invoiced, 2), "recent": invoices[:5]}
    except Exception:
        return {"count": 0, "total_invoiced": 0, "recent": []}


def _pricing_table() -> dict:
    """Current pricing and margin structure."""
    from billing.tracker import PRICING, RETAINER_TIERS

    # Estimated LLM costs per task type
    llm_costs = {
        "sales_outreach": 0.03,
        "support_ticket": 0.02,
        "content_repurpose": 0.04,
        "doc_extract": 0.02,
    }

    margins = {}
    for task_type, p in PRICING.items():
        price = p["per_task"]
        cost = llm_costs.get(task_type, 0.03)
        margin = price - cost
        margins[task_type] = {
            "price": price,
            "est_cost": cost,
            "margin": round(margin, 2),
            "margin_pct": f"{margin/price*100:.0f}%",
        }

    return {"per_task": margins, "retainer_tiers": RETAINER_TIERS}


def _runway_estimate() -> dict:
    """Estimate financial runway based on current burn/revenue."""
    try:
        rev_30 = _revenue_data(30)
        costs_30 = _cost_breakdown(30)

        monthly_revenue = rev_30.get("total_revenue", 0)
        monthly_cost = costs_30.get("total_llm_cost", 0)
        monthly_profit = monthly_revenue - monthly_cost

        return {
            "monthly_revenue": round(monthly_revenue, 2),
            "monthly_cost": round(monthly_cost, 4),
            "monthly_profit": round(monthly_profit, 2),
            "profitable": monthly_profit > 0,
            "margin_pct": f"{monthly_profit/monthly_revenue*100:.0f}%" if monthly_revenue else "N/A",
        }
    except Exception:
        return {}


# ── LEDGR System Prompt ─────────────────────────────────────────────────────

LEDGR_SYSTEM = """You are LEDGR — the autonomous CFO of BIT RAGE LABOUR, an AI labor company.

Your mandate from NCC (Natrix Command & Control):
- Track every dollar in, every dollar out
- Maximize gross margin (currently ~97% on per-task billing)
- Identify unprofitable clients or task types and recommend corrections
- Model revenue growth scenarios and set financial targets
- Issue pricing recommendations to AXIOM (CEO) and cost alerts to VECTIS (COO)
- Generate P&L analysis and financial projections

Revenue model:
- Per-task billing: Sales $2.40, Support $1.00, Content $3.00, Doc Extract $1.50
- Retainer tiers: Sales Starter $750/mo (50 tasks) through Support Scale $1,400/mo (1,000 tasks)
- LLM costs: ~$0.02-0.04 per task depending on provider and complexity

Your output must be valid JSON:
{
    "codename": "LEDGR",
    "role": "CFO",
    "timestamp": "<ISO timestamp>",
    "financial_status": "HEALTHY|CAUTION|CRITICAL",
    "pnl_summary": {
        "revenue_30d": "<amount>",
        "costs_30d": "<amount>",
        "gross_margin": "<amount>",
        "margin_pct": "<percentage>",
        "trend": "GROWING|FLAT|DECLINING"
    },
    "client_analysis": [
        {
            "client": "<name>",
            "revenue_30d": "<amount>",
            "margin": "<amount>",
            "status": "PROFITABLE|MARGINAL|UNPROFITABLE",
            "action": "<recommendation>"
        }
    ],
    "pricing_recommendations": [
        {
            "task_type": "<agent>",
            "current_price": "<amount>",
            "recommended_price": "<amount>",
            "rationale": "<why>"
        }
    ],
    "cost_alerts": [
        {
            "area": "<what's costing too much>",
            "severity": "HIGH|MEDIUM|LOW",
            "amount": "<how much>",
            "fix": "<how to reduce>"
        }
    ],
    "revenue_forecast": {
        "current_monthly": "<amount>",
        "projected_next_month": "<amount>",
        "projected_quarter": "<amount>",
        "assumptions": ["<assumption>"]
    },
    "financial_directives": [
        {
            "id": "FIN-001",
            "priority": "CRITICAL|HIGH|MEDIUM",
            "target": "AXIOM|VECTIS|ALL",
            "directive": "<specific financial action>",
            "expected_impact": "<revenue or savings estimate>"
        }
    ],
    "cfo_verdict": "<1-2 sentence financial status>"
}
"""


# ── LEDGR Agent ─────────────────────────────────────────────────────────────

class LedgrCFO:
    """LEDGR — the CFO agent. Tracks revenue, optimizes margins, projects growth."""

    codename = "LEDGR"
    role = "CFO"
    title = "Chief Financial Officer"
    full_name = "Lattice Engine for Dynamic Growth & Revenue"

    def __init__(self, provider: str | None = None):
        self.provider = provider

    def _financial_report(self) -> dict:
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "revenue_30d": _revenue_data(30),
            "revenue_7d": _revenue_data(7),
            "cost_breakdown": _cost_breakdown(30),
            "client_economics": _client_economics(),
            "invoice_history": _invoice_history(),
            "pricing": _pricing_table(),
            "runway": _runway_estimate(),
        }

        # AAC BANK pillar — cross-pillar financial intelligence
        try:
            cache_file = PROJECT_ROOT / "data" / "resonance_cache" / "aac_snapshot.json"
            if cache_file.exists():
                import json as _json
                report["aac_bank_pillar"] = _json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            report["aac_bank_pillar"] = None

        return report

    def run(self) -> dict:
        """Execute a full CFO financial review."""
        fin_data = self._financial_report()

        user_msg = (
            "FINANCIAL REPORT — BIT RAGE LABOUR\n"
            f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"{json.dumps(fin_data, indent=2, default=str)}\n\n"
            "Full financial analysis. P&L, per-client profitability, pricing optimization, "
            "cost alerts, and 30/60/90 day revenue projections. "
            "Be specific with dollar amounts. Flag any financial risks."
        )

        raw = call_llm(
            system_prompt=LEDGR_SYSTEM,
            user_message=user_msg,
            provider=self.provider,
            temperature=0.3,
            json_mode=True,
        )

        report = json.loads(raw)
        self._save(report)
        return report

    def cash_check(self) -> dict:
        """Quick financial snapshot — revenue, costs, margin."""
        fin_data = self._financial_report()

        user_msg = (
            "QUICK CASH CHECK\n"
            f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"{json.dumps(fin_data, indent=2, default=str)}\n\n"
            "Quick financial snapshot. Revenue, costs, margin, top risk. Max 3 directives."
        )

        raw = call_llm(
            system_prompt=LEDGR_SYSTEM,
            user_message=user_msg,
            provider=self.provider,
            temperature=0.2,
            json_mode=True,
        )

        check = json.loads(raw)
        self._save(check, suffix="cash_check")
        return check

    def _save(self, data: dict, suffix: str = "financial_review"):
        out_dir = PROJECT_ROOT / "output" / "c_suite" / "ledgr"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"ledgr_{suffix}_{ts}.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"[LEDGR] {suffix.upper()} saved → {path.name}")


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="LEDGR — CFO Agent")
    parser.add_argument("--check", action="store_true", help="Quick cash check instead of full review")
    parser.add_argument("--provider", help="Force LLM provider")
    args = parser.parse_args()

    cfo = LedgrCFO(provider=args.provider)

    if args.check:
        result = cfo.cash_check()
    else:
        result = cfo.run()

    status = result.get("financial_status", "UNKNOWN")
    color = {"HEALTHY": "✅", "CAUTION": "⚠️", "CRITICAL": "🔴"}.get(status, "❓")

    print(f"\n{'='*60}")
    print(f"  LEDGR — CFO FINANCIAL REPORT")
    print(f"{'='*60}")
    print(f"\n  Status: {color} {status}")
    print(f"  Verdict: {result.get('cfo_verdict', 'N/A')}")

    pnl = result.get("pnl_summary", {})
    print(f"\n  Revenue (30d): {pnl.get('revenue_30d', 'N/A')}")
    print(f"  Costs (30d):   {pnl.get('costs_30d', 'N/A')}")
    print(f"  Margin:        {pnl.get('gross_margin', 'N/A')} ({pnl.get('margin_pct', 'N/A')})")
    print(f"  Trend:         {pnl.get('trend', 'N/A')}")

    print(f"\n  Cost Alerts: {len(result.get('cost_alerts', []))}")
    print(f"  Directives:  {len(result.get('financial_directives', []))}")

    for d in result.get("financial_directives", []):
        print(f"\n  [{d.get('priority', '?')}] {d.get('id', '?')} → {d.get('target', '?')}")
        print(f"    {d.get('directive', '')}")


if __name__ == "__main__":
    main()
