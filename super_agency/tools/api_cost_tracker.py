#!/usr/bin/env python3
"""
API Cost Tracker
Logs OpenAI / LLM token usage per agent run and emits daily cost summaries.
Stores entries in a local SQLite database (memory/api_costs.db).
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

DB_PATH = Path(__file__).resolve().parent.parent / "memory" / "api_costs.db"

_conn: Optional[sqlite3.Connection] = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                agent TEXT NOT NULL,
                model TEXT,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0.0,
                metadata TEXT
            )
        """)
        _conn.commit()
    return _conn


# Approximate pricing per 1K tokens (USD) – update as models change
MODEL_COSTS = {
    "gpt-4o": {"prompt": 0.005, "completion": 0.015},
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
    "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
    "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
}


def estimate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Estimate USD cost for a call."""
    rates = MODEL_COSTS.get(
        model, MODEL_COSTS["gpt-4o-mini"],
    )
    return (
        (prompt_tokens / 1000) * rates["prompt"]
        + (completion_tokens / 1000) * rates["completion"]
    )


def log_usage(
    agent: str,
    model: str = "gpt-4o-mini",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    metadata: dict | None = None,
):
    """Record a single API call's token usage."""
    total = prompt_tokens + completion_tokens
    cost = estimate_cost(model, prompt_tokens, completion_tokens)
    conn = _get_conn()
    conn.execute(
        "INSERT INTO usage (agent, model, prompt_tokens, completion_tokens, total_tokens, cost_usd, metadata) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (agent, model, prompt_tokens, completion_tokens,
         total, cost, json.dumps(metadata or {})),
    )
    conn.commit()


def daily_summary(date: str | None = None) -> dict:
    """Return a cost summary for a given date (YYYY-MM-DD), default today."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    conn = _get_conn()
    cur = conn.execute(
        "SELECT agent, model, SUM(prompt_tokens), SUM(completion_tokens), SUM(total_tokens), SUM(cost_usd), COUNT(*) "
        "FROM usage WHERE DATE(ts) = ? GROUP BY agent, model ORDER BY SUM(cost_usd) DESC",
        (date,),)
    rows = cur.fetchall()
    agents = []
    total_cost = 0.0
    total_tokens = 0
    for agent, model, pt, ct, tt, cost, calls in rows:
        agents.append({
            "agent": agent, "model": model,
            "prompt_tokens": pt, "completion_tokens": ct,
            "total_tokens": tt, "cost_usd": round(cost, 6), "calls": calls,
        })
        total_cost += cost
        total_tokens += tt
    return {
        "date": date,
        "total_cost_usd": round(total_cost, 6),
        "total_tokens": total_tokens,
        "by_agent": agents,
    }


def weekly_summary() -> dict:
    """Return cost summaries for the last 7 days."""
    days = []
    for i in range(7):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        days.append(daily_summary(d))
    return {"weekly": days, "total_cost_usd": round(sum(d["total_cost_usd"] for d in days), 6)}


if __name__ == "__main__":
    # Quick smoke test
    log_usage("daily_brief", "gpt-4o-mini",
              prompt_tokens=500, completion_tokens=200)
    log_usage("research_agent", "gpt-4o",
              prompt_tokens=2000, completion_tokens=800)
    print(json.dumps(daily_summary(), indent=2))
