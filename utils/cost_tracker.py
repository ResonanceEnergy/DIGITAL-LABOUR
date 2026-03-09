"""LLM cost estimator — calculates cost per task based on provider pricing.

Pricing is per 1M tokens (input/output) as of 2025.

Usage:
    from utils.cost_tracker import estimate_cost, PROVIDER_PRICING
    cost = estimate_cost("openai", tokens_in=2000, tokens_out=500)
"""

# Pricing per 1M tokens (USD)
PROVIDER_PRICING = {
    "openai": {
        "model": "gpt-4o",
        "input_per_1m": 2.50,
        "output_per_1m": 10.00,
    },
    "anthropic": {
        "model": "claude-sonnet-4-20250514",
        "input_per_1m": 3.00,
        "output_per_1m": 15.00,
    },
    "gemini": {
        "model": "gemini-2.0-flash",
        "input_per_1m": 0.10,
        "output_per_1m": 0.40,
    },
    "grok": {
        "model": "grok-3",
        "input_per_1m": 3.00,
        "output_per_1m": 15.00,
    },
}

# Average token usage per task type (estimated from test runs)
TASK_TOKEN_ESTIMATES = {
    "sales_outreach": {"tokens_in": 3000, "tokens_out": 1500, "calls": 3},  # research + copy + QA
    "support_ticket": {"tokens_in": 2000, "tokens_out": 1000, "calls": 2},  # resolve + QA
    "content_repurpose": {"tokens_in": 4000, "tokens_out": 2000, "calls": 3},  # analyze + write + QA
    "doc_extract": {"tokens_in": 5000, "tokens_out": 1500, "calls": 2},  # extract + QA
}


def estimate_cost(provider: str, tokens_in: int = 0, tokens_out: int = 0) -> float:
    """Calculate USD cost for a given provider and token count."""
    pricing = PROVIDER_PRICING.get(provider)
    if not pricing:
        return 0.0

    input_cost = (tokens_in / 1_000_000) * pricing["input_per_1m"]
    output_cost = (tokens_out / 1_000_000) * pricing["output_per_1m"]
    return round(input_cost + output_cost, 6)


def estimate_task_cost(task_type: str, provider: str = "openai") -> dict:
    """Estimate the total LLM cost for a task type on a given provider."""
    task = TASK_TOKEN_ESTIMATES.get(task_type)
    if not task:
        return {"task_type": task_type, "provider": provider, "cost_usd": 0.0, "error": "Unknown task type"}

    total_in = task["tokens_in"] * task["calls"]
    total_out = task["tokens_out"] * task["calls"]
    cost = estimate_cost(provider, total_in, total_out)

    return {
        "task_type": task_type,
        "provider": provider,
        "tokens_in": total_in,
        "tokens_out": total_out,
        "llm_calls": task["calls"],
        "cost_usd": cost,
    }


def margin_analysis(task_type: str, provider: str = "openai") -> dict:
    """Calculate profit margin for a task type."""
    from billing.tracker import PRICING as CLIENT_PRICING
    
    est = estimate_task_cost(task_type, provider)
    client_charge = CLIENT_PRICING.get(task_type, {}).get("per_task", 0.0)

    return {
        "task_type": task_type,
        "provider": provider,
        "client_charge": client_charge,
        "llm_cost": est["cost_usd"],
        "margin": round(client_charge - est["cost_usd"], 4),
        "margin_pct": f"{((client_charge - est['cost_usd']) / client_charge * 100):.1f}%" if client_charge else "N/A",
    }


def full_margin_report() -> list[dict]:
    """Generate margin report for all task types across all providers."""
    results = []
    for task_type in TASK_TOKEN_ESTIMATES:
        for provider in PROVIDER_PRICING:
            results.append(margin_analysis(task_type, provider))
    return results


if __name__ == "__main__":
    import json
    print("=== Margin Report ===")
    for item in full_margin_report():
        print(f"  {item['task_type']:20s} | {item['provider']:10s} | "
              f"charge=${item['client_charge']:.2f} | cost=${item['llm_cost']:.4f} | "
              f"margin=${item['margin']:.4f} ({item['margin_pct']})")
