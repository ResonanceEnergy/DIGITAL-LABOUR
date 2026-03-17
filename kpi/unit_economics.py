"""Unit economics calculator — revenue, cost, margin, break-even for all 24 agents.

Pulls actual realized data from data/kpi.db (if available) and supplements with
pricing estimates from billing.tracker + utils.cost_tracker.

Usage:
    python -m kpi.unit_economics            # rich CLI table
    python -m kpi.unit_economics --json     # JSON dump to stdout
    python -m kpi.unit_economics --save     # write data/unit_economics.json
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "kpi.db"
OUTPUT_PATH = PROJECT_ROOT / "data" / "unit_economics.json"

# ── Extended token estimates for all 24 agents ────────────────────────────────
# Format: {tokens_in, tokens_out, calls} — per task (calls = LLM round-trips)
# Derived from observed usage; 4 core agents match utils/cost_tracker.py

AGENT_TOKEN_ESTIMATES: dict[str, dict] = {
    "sales_outreach":     {"tokens_in": 3000, "tokens_out": 1500, "calls": 3},
    "support_ticket":     {"tokens_in": 2000, "tokens_out": 1000, "calls": 2},
    "content_repurpose":  {"tokens_in": 4000, "tokens_out": 2000, "calls": 3},
    "doc_extract":        {"tokens_in": 5000, "tokens_out": 1500, "calls": 2},
    "ad_copy":            {"tokens_in": 2000, "tokens_out": 1000, "calls": 2},
    "bookkeeping":        {"tokens_in": 3000, "tokens_out": 800,  "calls": 2},
    "business_plan":      {"tokens_in": 8000, "tokens_out": 4000, "calls": 4},
    "context_manager":    {"tokens_in": 1500, "tokens_out": 500,  "calls": 1},
    "crm_ops":            {"tokens_in": 2000, "tokens_out": 800,  "calls": 2},
    "data_entry":         {"tokens_in": 2000, "tokens_out": 600,  "calls": 1},
    "email_marketing":    {"tokens_in": 3000, "tokens_out": 1500, "calls": 3},
    "lead_gen":           {"tokens_in": 4000, "tokens_out": 1000, "calls": 2},
    "market_research":    {"tokens_in": 6000, "tokens_out": 2500, "calls": 3},
    "press_release":      {"tokens_in": 3000, "tokens_out": 1500, "calls": 2},
    "product_desc":       {"tokens_in": 2000, "tokens_out": 1000, "calls": 2},
    "proposal_writer":    {"tokens_in": 5000, "tokens_out": 3000, "calls": 3},
    "qa":                 {"tokens_in": 2000, "tokens_out": 800,  "calls": 2},
    "qa_manager":         {"tokens_in": 1500, "tokens_out": 500,  "calls": 1},
    "resume_writer":      {"tokens_in": 3500, "tokens_out": 2000, "calls": 2},
    "seo_content":        {"tokens_in": 4000, "tokens_out": 2500, "calls": 3},
    "social_media":       {"tokens_in": 2000, "tokens_out": 1200, "calls": 2},
    "tech_docs":          {"tokens_in": 5000, "tokens_out": 2500, "calls": 3},
    "web_scraper":        {"tokens_in": 2000, "tokens_out": 800,  "calls": 1},
    "automation_manager": {"tokens_in": 3000, "tokens_out": 1000, "calls": 2},
}

# Provider pricing — per 1M tokens (USD), kept in sync with utils/cost_tracker.py
PROVIDER_PRICING: dict[str, dict] = {
    "openai":    {"model": "gpt-4o",                     "input_per_1m": 2.50,  "output_per_1m": 10.00},
    "anthropic": {"model": "claude-sonnet-4-20250514",   "input_per_1m": 3.00,  "output_per_1m": 15.00},
    "gemini":    {"model": "gemini-2.0-flash",           "input_per_1m": 0.10,  "output_per_1m": 0.40},
    "grok":      {"model": "grok-3",                     "input_per_1m": 3.00,  "output_per_1m": 15.00},
}

# Monthly COGS assumptions (fixed overhead, split across tasks)
MONTHLY_FIXED_COSTS = {
    "railway_hosting":    20.00,   # Railway server
    "zoho_email":          5.00,   # Zoho Mail
    "stripe_fees_est":    10.00,   # ~2.9% on ~$350 MRR est.
    "misc_saas":           5.00,   # misc tooling
}
TOTAL_FIXED_MONTHLY = sum(MONTHLY_FIXED_COSTS.values())


def _estimate_llm_cost(agent: str, provider: str) -> float:
    """Estimate LLM cost for one task of agent type on given provider."""
    est = AGENT_TOKEN_ESTIMATES.get(agent)
    if not est:
        return 0.0
    pricing = PROVIDER_PRICING.get(provider)
    if not pricing:
        return 0.0
    tokens_in   = est["tokens_in"]  * est["calls"]
    tokens_out  = est["tokens_out"] * est["calls"]
    cost_in  = (tokens_in  / 1_000_000) * pricing["input_per_1m"]
    cost_out = (tokens_out / 1_000_000) * pricing["output_per_1m"]
    return round(cost_in + cost_out, 6)


def _load_realized_data() -> dict[str, dict]:
    """Load actual task costs + counts from kpi.db. Returns {} if db missing."""
    if not DB_PATH.exists():
        return {}
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT task_type,
                      COUNT(*) as count,
                      AVG(COALESCE(cost_usd, 0)) as avg_llm_cost,
                      AVG(COALESCE(duration_s, 0)) as avg_duration_s,
                      SUM(CASE WHEN qa_status='pass' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as qa_pass_rate
               FROM events
               WHERE status = 'complete'
               GROUP BY task_type"""
        ).fetchall()
        conn.close()
        return {
            r["task_type"]: {
                "count":        r["count"],
                "avg_llm_cost": round(r["avg_llm_cost"] or 0, 6),
                "avg_duration": round(r["avg_duration_s"] or 0, 1),
                "qa_pass_rate": round((r["qa_pass_rate"] or 0) * 100, 1),
            }
            for r in rows
        }
    except Exception:
        return {}


def compute_unit_economics(default_provider: str = "openai") -> dict:
    """Build unit economics report for all 24 agents."""
    from billing.tracker import PRICING  # noqa: PLC0415

    realized = _load_realized_data()
    agents = sorted(PRICING.keys())
    rows = []

    for agent in agents:
        client_charge = PRICING[agent]["per_task"]
        realized_data = realized.get(agent, {})

        # Use realized avg cost if available, else estimate
        if realized_data:
            avg_llm_cost   = realized_data["avg_llm_cost"]
            task_count     = realized_data["count"]
            avg_duration_s = realized_data["avg_duration"]
            qa_pass_rate   = realized_data["qa_pass_rate"]
            source         = "realized"
        else:
            avg_llm_cost   = _estimate_llm_cost(agent, default_provider)
            task_count     = 0
            avg_duration_s = 0.0
            qa_pass_rate   = 0.0
            source         = "estimated"

        margin_usd = round(client_charge - avg_llm_cost, 4)
        margin_pct = round((margin_usd / client_charge) * 100, 1) if client_charge > 0 else 0.0

        # Break-even: how many tasks/month cover fixed overhead for this agent
        # (allocate fixed costs equally across all 24 agents)
        fixed_per_agent = TOTAL_FIXED_MONTHLY / len(agents)
        break_even = (
            round(fixed_per_agent / margin_usd)
            if margin_usd > 0
            else None
        )

        # Cheapest provider for this agent
        provider_costs = {
            p: _estimate_llm_cost(agent, p)
            for p in PROVIDER_PRICING
        }
        cheapest_provider = min(provider_costs, key=lambda p: provider_costs[p])
        cheapest_cost     = provider_costs[cheapest_provider]

        rows.append({
            "agent":               agent,
            "client_charge_usd":   client_charge,
            "avg_llm_cost_usd":    avg_llm_cost,
            "margin_usd":          margin_usd,
            "margin_pct":          margin_pct,
            "break_even_tasks_mo": break_even,
            "task_count_realized": task_count,
            "avg_duration_s":      avg_duration_s,
            "qa_pass_rate_pct":    qa_pass_rate,
            "cheapest_provider":   cheapest_provider,
            "cheapest_cost_usd":   cheapest_cost,
            "cost_source":         source,
        })

    # Portfolio-level summary
    total_charges   = sum(r["client_charge_usd"] for r in rows)
    total_llm_costs = sum(r["avg_llm_cost_usd"]  for r in rows)
    avg_margin_pct  = round(
        (sum(r["margin_pct"] for r in rows) / len(rows)) if rows else 0, 1
    )

    # Monthly P&L projection (assuming 1 task/agent/day = ~30 tasks/mo/agent)
    assumed_monthly_tasks_per_agent = 30
    projected_revenue = total_charges * assumed_monthly_tasks_per_agent
    projected_llm     = total_llm_costs * assumed_monthly_tasks_per_agent
    projected_margin  = projected_revenue - projected_llm - TOTAL_FIXED_MONTHLY

    return {
        "meta": {
            "default_provider":         default_provider,
            "fixed_costs_monthly_usd":  MONTHLY_FIXED_COSTS,
            "assumed_tasks_per_agent_mo": assumed_monthly_tasks_per_agent,
            "total_agents":             len(rows),
            "agents_with_realized_data": sum(1 for r in rows if r["cost_source"] == "realized"),
        },
        "portfolio_summary": {
            "avg_margin_pct":              avg_margin_pct,
            "projected_monthly_revenue":   round(projected_revenue, 2),
            "projected_monthly_llm_cost":  round(projected_llm, 4),
            "projected_monthly_fixed":     round(TOTAL_FIXED_MONTHLY, 2),
            "projected_monthly_net":       round(projected_margin, 2),
        },
        "agents": rows,
        "provider_comparison": {
            agent: {
                p: _estimate_llm_cost(agent, p)
                for p in PROVIDER_PRICING
            }
            for agent in sorted(AGENT_TOKEN_ESTIMATES.keys())
        },
    }


def print_report(report: dict) -> None:
    """Print a human-readable unit economics report to stdout."""
    meta     = report["meta"]
    summary  = report["portfolio_summary"]
    agents   = report["agents"]

    print()
    print("=" * 80)
    print("  DIGITAL LABOUR — UNIT ECONOMICS REPORT")
    print(f"  Provider: {meta['default_provider'].upper()}  |  "
          f"Agents: {meta['total_agents']}  |  "
          f"Realized: {meta['agents_with_realized_data']}")
    print("=" * 80)

    # Header
    cols = f"{'AGENT':<22} {'CHARGE':>7} {'LLM COST':>9} {'MARGIN$':>8} {'MARGIN%':>8} "
    cols += f"{'B/E TASKS':>10} {'CHEAPEST':>10}"
    print(cols)
    print("-" * 80)

    for r in sorted(agents, key=lambda x: -x["margin_pct"]):
        be = str(r["break_even_tasks_mo"]) if r["break_even_tasks_mo"] else "—"
        src = "*" if r["cost_source"] == "realized" else " "
        print(
            f"{src}{r['agent']:<21} "
            f"${r['client_charge_usd']:>6.2f} "
            f"${r['avg_llm_cost_usd']:>8.4f} "
            f"${r['margin_usd']:>7.4f} "
            f"{r['margin_pct']:>7.1f}% "
            f"{be:>10} "
            f"{r['cheapest_provider']:>10}"
        )

    print("-" * 80)
    print(f"  * = realized from kpi.db")
    print()
    print("  MONTHLY PROJECTION (@ 30 tasks/agent/mo)")
    print(f"  Revenue  : ${summary['projected_monthly_revenue']:>10,.2f}")
    print(f"  LLM Cost : ${summary['projected_monthly_llm_cost']:>10,.4f}")
    print(f"  Fixed    : ${summary['projected_monthly_fixed']:>10,.2f}")
    print(f"  Net      : ${summary['projected_monthly_net']:>10,.2f}")
    print(f"  Avg Margin: {summary['avg_margin_pct']:.1f}%")
    print()
    print("  FIXED COSTS BREAKDOWN")
    for name, amt in meta["fixed_costs_monthly_usd"].items():
        print(f"    {name:<25} ${amt:.2f}/mo")
    print("=" * 80)
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Digital Labour unit economics calculator")
    parser.add_argument("--json",     action="store_true", help="Output JSON to stdout")
    parser.add_argument("--save",     action="store_true", help="Save JSON to data/unit_economics.json")
    parser.add_argument("--provider", default="openai", choices=list(PROVIDER_PRICING.keys()),
                        help="Default provider for estimates (default: openai)")
    args = parser.parse_args()

    report = compute_unit_economics(default_provider=args.provider)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)

    if args.save:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Saved → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
