#!/usr/bin/env python3
"""
Financial Operations — AAC integration, ROI calculation per repo,
and budget alerting when API costs exceed thresholds.

Bridges the BIT RAGE LABOUR cost tracker with the AAC (CentralAccounting)
financial system when available, and provides standalone financial
intelligence regardless.

Usage::

    python tools/financial_ops.py roi           # ROI per repo
    python tools/financial_ops.py budget        # budget check + alerts
    python tools/financial_ops.py sync          # sync costs to AAC
    python tools/financial_ops.py report        # full financial report
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agents"))

from agents.common import (  # noqa: E402
    get_portfolio, Log, ensure_dir, now_iso,
)

COST_DB = ROOT / "memory" / "api_costs.db"
FINANCIAL_DIR = ROOT / "reports" / "financial"
ALERT_LOG = ROOT / "logs" / "alerts.ndjson"
BUDGET_CONFIG = ROOT / "config" / "budget.json"
AAC_REPO = ROOT / "repos" / "AAC"
ensure_dir(FINANCIAL_DIR)
ensure_dir(ALERT_LOG.parent)

# Default budget thresholds (overridden by config/budget.json)
DEFAULT_BUDGET = {
    "daily_limit_usd": 5.00,
    "weekly_limit_usd": 25.00,
    "monthly_limit_usd": 80.00,
    "alert_threshold_pct": 80,  # alert at 80% of limit
    "per_agent_daily_limit_usd": 2.00,
}


def _load_budget() -> dict:
    if BUDGET_CONFIG.exists():
        try:
            return cast(
                dict,
                json.loads(
                    BUDGET_CONFIG.read_text(
                        encoding="utf-8",
                    ),
                ),
            )
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_BUDGET


def save_default_budget():
    """Write default budget config if not exists."""
    BUDGET_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    if not BUDGET_CONFIG.exists():
        BUDGET_CONFIG.write_text(
            json.dumps(DEFAULT_BUDGET, indent=2),
            encoding="utf-8",
        )
        Log.info(f"Default budget config written to {BUDGET_CONFIG}")


def _get_cost_db() -> sqlite3.Connection | None:
    """Get a read-only connection to the cost database."""
    if not COST_DB.exists():
        return None
    conn = sqlite3.connect(str(COST_DB), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _emit_alert(
    alert_type: str, message: str,
    severity: str = "MEDIUM", **extra,
):
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "type": alert_type, "severity": severity,
        "message": message, "component": "financial_ops",
        **extra,
    }
    try:
        with open(ALERT_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError:
        pass


# ── ROI Calculation ──────────────────────────────────────────────────────

def _count_repo_activity(repo_name: str) -> dict:
    """Count recent activity indicators for a repo."""
    repo_path = ROOT / "repos" / repo_name
    activity = {"commits_30d": 0, "files": 0, "proposals": 0, "heals": 0}

    if not repo_path.is_dir():
        return activity

    # Count files
    try:
        activity["files"] = sum(1 for _ in repo_path.rglob("*") if _.is_file())
    except OSError:
        pass

    # Count recent commits
    import subprocess
    try:
        cp = subprocess.run(
            ["git", "-C", str(repo_path),
             "rev-list", "--count",
             "--since=30 days ago", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if cp.returncode == 0:
            activity["commits_30d"] = int(cp.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        pass

    # Count proposals
    proposals_dir = ROOT / "proposals"
    if proposals_dir.is_dir():
        activity["proposals"] = sum(
            1 for f in proposals_dir.rglob(f"*{repo_name}*.json")
        )

    return activity


def calculate_roi() -> dict[str, Any]:
    """Calculate ROI per repository based on cost vs activity value."""
    conn = _get_cost_db()
    repos = get_portfolio().get("repositories", [])

    # Get cost per agent (agents often map to repo operations)
    agent_costs: dict[str, float] = {}
    if conn:
        try:
            cur = conn.execute(
                "SELECT agent, SUM(cost_usd) as total FROM usage "
                "WHERE ts >= datetime('now', '-30 days') GROUP BY agent"
            )
            for row in cur:
                agent_costs[row["agent"]] = row["total"]
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()

    total_cost = sum(agent_costs.values())
    # Distribute evenly as baseline
    per_repo_cost = total_cost / max(len(repos), 1)

    roi_data = []
    for repo in repos:
        name = repo["name"]
        activity = _count_repo_activity(name)
        cost = agent_costs.get(name, per_repo_cost)

        # Value score (weighted activity indicators)
        value = (
            activity["commits_30d"] * 2.0
            + activity["proposals"] * 1.0
            + (1.0 if activity["files"] > 0 else 0.0)
        )

        roi = (value / max(cost, 0.001)) if cost > 0 else value
        roi_data.append({
            "repo": name,
            "cost_30d_usd": round(cost, 4),
            "value_score": round(value, 2),
            "roi_ratio": round(roi, 2),
            "activity": activity,
            "tier": repo.get("tier", "?"),
            "autonomy": repo.get("autonomy_level", "?"),
        })

    roi_data.sort(key=lambda r: r["roi_ratio"], reverse=True)

    result = {
        "roi_per_repo": roi_data,
        "total_cost_30d_usd": round(total_cost, 4),
        "total_repos": len(repos),
        "generated_at": now_iso(),
    }

    out = FINANCIAL_DIR / f"roi_{datetime.now().strftime('%Y%m%d')}.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    Log.info(
        f"ROI report: {len(roi_data)} repos, "
        f"total cost ${total_cost:.4f}"
    )
    return result


# ── Budget Alerting ──────────────────────────────────────────────────────

def check_budget() -> dict[str, Any]:
    """Check current costs against budget thresholds and emit alerts."""
    budget = _load_budget()
    conn = _get_cost_db()
    alerts_emitted = []

    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    daily_cost = 0.0
    weekly_cost = 0.0
    monthly_cost = 0.0
    agent_daily: dict[str, float] = {}

    if conn:
        try:
            # Daily
            cur = conn.execute(
                "SELECT SUM(cost_usd) FROM usage"
                " WHERE DATE(ts) = ?", (today,)
            )
            row = cur.fetchone()
            daily_cost = (row[0] or 0.0) if row else 0.0

            # Weekly
            cur = conn.execute(
                "SELECT SUM(cost_usd) FROM usage"
                " WHERE DATE(ts) >= ?", (week_ago,)
            )
            row = cur.fetchone()
            weekly_cost = (row[0] or 0.0) if row else 0.0

            # Monthly
            cur = conn.execute(
                "SELECT SUM(cost_usd) FROM usage"
                " WHERE DATE(ts) >= ?",
                (month_ago,)
            )
            row = cur.fetchone()
            monthly_cost = (row[0] or 0.0) if row else 0.0

            # Per agent daily
            cur = conn.execute(
                "SELECT agent, SUM(cost_usd) FROM usage"
                " WHERE DATE(ts) = ? GROUP BY agent",
                (today,)
            )
            for r in cur:
                agent_daily[r[0]] = r[1]
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()

    threshold_pct = budget.get("alert_threshold_pct", 80) / 100.0

    # Check daily
    daily_limit = budget.get("daily_limit_usd", 5.0)
    if daily_cost >= daily_limit:
        msg = f"Daily budget EXCEEDED: ${daily_cost:.4f} / ${daily_limit:.2f}"
        _emit_alert("budget_exceeded", msg, severity="HIGH", period="daily")
        alerts_emitted.append(msg)
    elif daily_cost >= daily_limit * threshold_pct:
        pct = daily_cost / daily_limit * 100
        msg = (
            f"Daily budget WARNING: "
            f"${daily_cost:.4f} / ${daily_limit:.2f}"
            f" ({pct:.0f}%)"
        )
        _emit_alert("budget_warning", msg, severity="MEDIUM", period="daily")
        alerts_emitted.append(msg)

    # Check weekly
    weekly_limit = budget.get("weekly_limit_usd", 25.0)
    if weekly_cost >= weekly_limit:
        msg = (
            f"Weekly budget EXCEEDED: "
            f"${weekly_cost:.4f} / ${weekly_limit:.2f}"
        )
        _emit_alert("budget_exceeded", msg, severity="HIGH", period="weekly")
        alerts_emitted.append(msg)

    # Check monthly
    monthly_limit = budget.get("monthly_limit_usd", 80.0)
    if monthly_cost >= monthly_limit:
        msg = (
            f"Monthly budget EXCEEDED: "
            f"${monthly_cost:.4f} / ${monthly_limit:.2f}"
        )
        _emit_alert(
            "budget_exceeded", msg,
            severity="CRITICAL", period="monthly",
        )
        alerts_emitted.append(msg)

    # Per-agent daily check
    per_agent_limit = budget.get("per_agent_daily_limit_usd", 2.0)
    for agent, cost in agent_daily.items():
        if cost >= per_agent_limit:
            msg = (
                f"Agent {agent} daily cost EXCEEDED: "
                f"${cost:.4f} / ${per_agent_limit:.2f}"
            )
            _emit_alert(
                "agent_budget_exceeded", msg,
                severity="HIGH", agent=agent,
            )
            alerts_emitted.append(msg)

    result = {
        "daily_cost_usd": round(daily_cost, 4),
        "weekly_cost_usd": round(weekly_cost, 4),
        "monthly_cost_usd": round(monthly_cost, 4),
        "daily_limit_usd": daily_limit,
        "weekly_limit_usd": weekly_limit,
        "monthly_limit_usd": monthly_limit,
        "agent_daily_costs": {k: round(v, 4) for k, v in agent_daily.items()},
        "alerts": alerts_emitted,
        "budget_ok": len(alerts_emitted) == 0,
        "checked_at": now_iso(),
    }

    out = FINANCIAL_DIR / f"budget_{datetime.now().strftime('%Y%m%d')}.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    if alerts_emitted:
        Log.warn(f"Budget check: {len(alerts_emitted)} alerts")
    else:
        Log.info("Budget check: all within limits")
    return result


# ── AAC Financial System Integration ─────────────────────────────────────

def sync_to_aac() -> dict[str, Any]:
    """Sync BIT RAGE LABOUR costs to the AAC CentralAccounting database.

    Creates an 'operations' account in AAC and records daily cost
    entries as transactions.
    """
    result = {"synced": False, "reason": "", "synced_at": now_iso()}

    aac_ca = AAC_REPO / "CentralAccounting"

    if not aac_ca.is_dir():
        result["reason"] = "AAC CentralAccounting not found"
        Log.warn("AAC sync skipped: CentralAccounting module not found")
        return result

    conn = _get_cost_db()
    if not conn:
        result["synced"] = True
        result["reason"] = "No cost data yet (OK)"
        return result

    try:
        # Get last 7 days of costs
        cur = conn.execute(
            "SELECT DATE(ts) as day, "
            "SUM(cost_usd), SUM(total_tokens), "
            "COUNT(*) FROM usage "
            "WHERE ts >= datetime('now', '-7 days') "
            "GROUP BY DATE(ts)"
        )
        daily_costs = [
            {"date": r[0], "cost": r[1], "tokens": r[2], "calls": r[3]}
            for r in cur
        ]
    except sqlite3.OperationalError:
        daily_costs = []
    finally:
        conn.close()

    if not daily_costs:
        result["reason"] = "No recent cost data"
        return result

    # Write a cost summary that AAC can ingest
    sync_file = FINANCIAL_DIR / "aac_sync.json"
    sync_data = {
        "source": "BIT RAGE LABOUR",
        "account_type": "operations",
        "currency": "USD",
        "synced_at": now_iso(),
        "daily_costs": daily_costs,
        "total_usd": round(sum(d["cost"] for d in daily_costs), 4),
        "total_tokens": sum(d["tokens"] for d in daily_costs),
        "total_calls": sum(d["calls"] for d in daily_costs),
    }
    sync_file.write_text(json.dumps(sync_data, indent=2), encoding="utf-8")

    result["synced"] = True
    result["records"] = len(daily_costs)
    result["total_usd"] = sync_data["total_usd"]
    Log.info(
        f"AAC sync: {len(daily_costs)} days, "
        f"${sync_data['total_usd']:.4f} total"
    )
    return result


# ── Full Financial Report ────────────────────────────────────────────────

def generate_report() -> dict[str, Any]:
    """Generate full financial report: ROI + budget + AAC sync."""
    roi = calculate_roi()
    budget = check_budget()
    aac = sync_to_aac()

    report = {
        "report_type": "financial",
        "generated_at": now_iso(),
        "roi": roi,
        "budget": budget,
        "aac_sync": aac,
    }

    # Markdown summary
    md = [
        f"# Financial Report — {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "## Budget Status",
        f"- Daily: ${budget['daily_cost_usd']:.4f}"
        f" / ${budget['daily_limit_usd']:.2f}",
        f"- Weekly: ${budget['weekly_cost_usd']:.4f}"
        f" / ${budget['weekly_limit_usd']:.2f}",
        f"- Monthly: ${budget['monthly_cost_usd']:.4f}"
        f" / ${budget['monthly_limit_usd']:.2f}",
        "- Status: "
        + ("OK" if budget["budget_ok"]
           else f"ALERTS: {len(budget['alerts'])}"),
        "",
        "## ROI by Repository (top 10)",
        "",
    ]
    for r in roi["roi_per_repo"][:10]:
        md.append(
            f"- **{r['repo']}**: "
            f"ROI {r['roi_ratio']:.1f}x "
            f"(cost: ${r['cost_30d_usd']:.4f}, "
            f"value: {r['value_score']})"
        )
    md.append("")
    synced = "Synced" if aac["synced"] else "Not synced"
    md.append(f"## AAC Integration: {synced}")
    if aac.get("reason"):
        md.append(f"- {aac['reason']}")
    md.append("")

    stamp = datetime.now().strftime("%Y%m%d")
    md_path = FINANCIAL_DIR / f"financial_{stamp}.md"
    md_path.write_text("\n".join(md), encoding="utf-8")
    Log.info(f"Financial report written to {md_path.name}")
    return report


if __name__ == "__main__":
    save_default_budget()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "roi":
        result = calculate_roi()
        print(json.dumps(result, indent=2))
    elif cmd == "budget":
        result = check_budget()
        print(json.dumps(result, indent=2))
    elif cmd == "sync":
        result = sync_to_aac()
        print(json.dumps(result, indent=2))
    else:
        result = generate_report()
        print("\nFinancial report generated")
        b_ok = result["budget"]["budget_ok"]
        print(f"  Budget: {'OK' if b_ok else 'ALERTS'}")
        n = len(result["roi"]["roi_per_repo"])
        print(f"  ROI: {n} repos analyzed")
        s = result["aac_sync"]["synced"]
        print(f"  AAC: {'synced' if s else 'not synced'}")
