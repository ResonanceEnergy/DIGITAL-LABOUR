"""Monitoring API endpoints for the Operations Dashboard.

Provides JSON endpoints for real-time ops monitoring, KPI trends,
agent/provider performance, cost breakdown, and C-Suite status.

Mounted as a sub-router on the main FastAPI app.
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

router = APIRouter(prefix="/monitor", tags=["monitoring"])

DATA_DIR = PROJECT_ROOT / "data"
KPI_DB = DATA_DIR / "kpi.db"
BILLING_DB = DATA_DIR / "billing.db"
QUEUE_DB = DATA_DIR / "task_queue.db"


def _kpi_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(KPI_DB))
    conn.row_factory = sqlite3.Row
    return conn


def _billing_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(BILLING_DB))
    conn.row_factory = sqlite3.Row
    return conn


def _queue_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(QUEUE_DB))
    conn.row_factory = sqlite3.Row
    return conn


# ── Unified Overview ────────────────────────────────────────────────────────

@router.get("/overview")
def overview():
    """Single payload with everything the dashboard needs for the top-level view."""
    from dashboard.health import system_health, queue_status, kpi_summary, revenue_summary, client_count
    health = system_health()
    queue = queue_status()
    kpi = kpi_summary()
    rev = revenue_summary()

    # C-Suite latest verdicts
    csuite = _csuite_status()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "health": health,
        "queue": queue,
        "kpi_7d": kpi,
        "revenue_30d": rev,
        "active_clients": client_count(),
        "c_suite": csuite,
    }


# ── KPI Trends ──────────────────────────────────────────────────────────────

@router.get("/kpi/trend")
def kpi_trend(days: int = 14):
    """Daily task counts and pass rates for trending charts."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    if not KPI_DB.exists():
        return {"days": [], "tasks": [], "passed": [], "failed": [], "pass_rate": []}

    conn = _kpi_conn()
    rows = conn.execute(
        """SELECT DATE(timestamp) as day,
                  COUNT(*) as total,
                  SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as passed,
                  SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed
           FROM events WHERE timestamp >= ?
           GROUP BY DATE(timestamp) ORDER BY day""",
        (cutoff,),
    ).fetchall()
    conn.close()

    days_list, tasks, passed, failed, pass_rate = [], [], [], [], []
    for r in rows:
        days_list.append(r["day"])
        tasks.append(r["total"])
        passed.append(r["passed"])
        failed.append(r["failed"])
        rate = round(r["passed"] / r["total"] * 100, 1) if r["total"] else 0
        pass_rate.append(rate)

    return {"days": days_list, "tasks": tasks, "passed": passed, "failed": failed, "pass_rate": pass_rate}


@router.get("/kpi/latency")
def kpi_latency(days: int = 14):
    """Daily avg/p50/p95 latency in seconds."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    if not KPI_DB.exists():
        return {"days": [], "avg": [], "p50": [], "p95": []}

    conn = _kpi_conn()
    rows = conn.execute(
        "SELECT DATE(timestamp) as day, duration_s FROM events WHERE timestamp >= ? AND status='completed' ORDER BY day",
        (cutoff,),
    ).fetchall()
    conn.close()

    by_day: dict[str, list[float]] = {}
    for r in rows:
        by_day.setdefault(r["day"], []).append(r["duration_s"])

    days_list, avg_list, p50_list, p95_list = [], [], [], []
    for day in sorted(by_day):
        durations = sorted(by_day[day])
        n = len(durations)
        days_list.append(day)
        avg_list.append(round(sum(durations) / n, 2))
        p50_list.append(round(durations[n // 2], 2))
        p95_list.append(round(durations[int(n * 0.95)], 2) if n >= 2 else round(durations[-1], 2))

    return {"days": days_list, "avg": avg_list, "p50": p50_list, "p95": p95_list}


# ── Agent Performance ───────────────────────────────────────────────────────

@router.get("/agents")
def agent_performance(days: int = 7):
    """Per-agent task counts, pass rates, avg latency."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    if not KPI_DB.exists():
        return {"agents": []}

    conn = _kpi_conn()
    rows = conn.execute(
        """SELECT task_type,
                  COUNT(*) as total,
                  SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as passed,
                  SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
                  AVG(duration_s) as avg_duration,
                  SUM(cost_usd) as total_cost
           FROM events WHERE timestamp >= ?
           GROUP BY task_type""",
        (cutoff,),
    ).fetchall()
    conn.close()

    agents = []
    for r in rows:
        rate = round(r["passed"] / r["total"] * 100, 1) if r["total"] else 0
        grade = "A" if rate >= 95 else "B" if rate >= 85 else "C" if rate >= 70 else "D" if rate >= 50 else "F"
        agents.append({
            "name": r["task_type"],
            "total": r["total"],
            "passed": r["passed"],
            "failed": r["failed"],
            "pass_rate": rate,
            "grade": grade,
            "avg_duration_s": round(r["avg_duration"] or 0, 2),
            "total_cost": round(r["total_cost"] or 0, 4),
        })

    return {"agents": agents, "period_days": days}


# ── Provider Health ─────────────────────────────────────────────────────────

@router.get("/providers")
def provider_health(days: int = 7):
    """Per-provider success rates and usage."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    if not KPI_DB.exists():
        return {"providers": []}

    conn = _kpi_conn()
    rows = conn.execute(
        """SELECT provider,
                  COUNT(*) as total,
                  SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as passed,
                  AVG(duration_s) as avg_duration,
                  SUM(cost_usd) as total_cost
           FROM events WHERE timestamp >= ? AND provider != ''
           GROUP BY provider""",
        (cutoff,),
    ).fetchall()
    conn.close()

    providers = []
    for r in rows:
        rate = round(r["passed"] / r["total"] * 100, 1) if r["total"] else 0
        providers.append({
            "name": r["provider"],
            "total": r["total"],
            "passed": r["passed"],
            "pass_rate": rate,
            "avg_duration_s": round(r["avg_duration"] or 0, 2),
            "total_cost": round(r["total_cost"] or 0, 4),
        })

    return {"providers": providers, "period_days": days}


# ── Revenue & Cost Breakdown ────────────────────────────────────────────────

@router.get("/financials")
def financials(days: int = 30):
    """Revenue, cost, margin breakdown by client and task type."""
    try:
        from billing.tracker import BillingTracker, PRICING
        bt = BillingTracker()
        report = bt.revenue_report(days=days)
        report["pricing"] = PRICING
        return report
    except Exception:
        return {"total_revenue": 0, "total_cost": 0, "gross_margin": 0, "total_tasks": 0}


@router.get("/financials/trend")
def financial_trend(days: int = 30):
    """Daily revenue and cost trend."""
    if not BILLING_DB.exists():
        return {"days": [], "revenue": [], "cost": [], "margin": []}

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = _billing_conn()
    rows = conn.execute(
        """SELECT DATE(timestamp) as day,
                  SUM(charge) as revenue,
                  SUM(llm_cost) as cost
           FROM usage WHERE timestamp >= ?
           GROUP BY DATE(timestamp) ORDER BY day""",
        (cutoff,),
    ).fetchall()
    conn.close()

    days_list, rev, cost, margin = [], [], [], []
    for r in rows:
        days_list.append(r["day"])
        rev.append(round(r["revenue"] or 0, 2))
        cost.append(round(r["cost"] or 0, 4))
        margin.append(round((r["revenue"] or 0) - (r["cost"] or 0), 2))

    return {"days": days_list, "revenue": rev, "cost": cost, "margin": margin}


# ── Queue Live Status ───────────────────────────────────────────────────────

@router.get("/queue")
def queue_live():
    """Real-time queue depth and recent tasks."""
    try:
        from dispatcher.queue import TaskQueue
        q = TaskQueue()
        stats = q.stats()
    except Exception:
        stats = {"queued": 0, "running": 0, "completed": 0, "failed": 0, "total": 0}

    # Recent tasks (last 20)
    recent = []
    if QUEUE_DB.exists():
        conn = _queue_conn()
        rows = conn.execute(
            "SELECT task_id, task_type, client, status, qa_status, created_at, completed_at FROM tasks ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
        conn.close()
        recent = [dict(r) for r in rows]

    return {"stats": stats, "recent": recent}


# ── C-Suite Status ──────────────────────────────────────────────────────────

def _csuite_status() -> dict:
    """Gather latest C-Suite executive verdicts."""
    output_dir = PROJECT_ROOT / "output" / "c_suite"
    result = {}

    for exec_name in ["axiom", "vectis", "ledgr"]:
        exec_dir = output_dir / exec_name
        if not exec_dir.exists():
            result[exec_name] = {"status": "NO DATA", "verdict": "—", "last_run": "—"}
            continue
        reports = sorted(exec_dir.glob("*.json"), reverse=True)
        if not reports:
            result[exec_name] = {"status": "NO DATA", "verdict": "—", "last_run": "—"}
            continue
        try:
            data = json.loads(reports[0].read_text(encoding="utf-8"))
            verdict = data.get("ceo_verdict") or data.get("coo_verdict") or data.get("cfo_verdict") or "—"
            status = data.get("financial_status") or data.get("ops_status") or "ACTIVE"
            result[exec_name] = {
                "status": status,
                "verdict": verdict[:200],
                "last_run": reports[0].stem,
            }
        except Exception:
            result[exec_name] = {"status": "ERROR", "verdict": "—", "last_run": "—"}

    # Board
    board_dir = output_dir / "board"
    if board_dir.exists():
        boards = sorted(board_dir.glob("*.json"), reverse=True)
        if boards:
            try:
                data = json.loads(boards[0].read_text(encoding="utf-8"))
                result["board"] = {
                    "status": data.get("overall_status", "—"),
                    "verdict": (data.get("board_verdict") or "—")[:200],
                    "last_run": boards[0].stem,
                    "execution_queue": data.get("execution_queue", [])[:5],
                }
            except Exception:
                result["board"] = {"status": "ERROR", "verdict": "—", "last_run": "—"}

    return result


@router.get("/csuite")
def csuite_endpoint():
    """Get C-Suite executive status and latest directives."""
    return _csuite_status()


# ── Event Feed ──────────────────────────────────────────────────────────────

@router.get("/feed")
def event_feed(limit: int = 50):
    """Recent task events (for live activity feed)."""
    if not KPI_DB.exists():
        return {"events": []}

    conn = _kpi_conn()
    rows = conn.execute(
        "SELECT task_id, task_type, client, provider, status, qa_status, duration_s, cost_usd, timestamp FROM events ORDER BY timestamp DESC LIMIT ?",
        (min(limit, 200),),
    ).fetchall()
    conn.close()
    return {"events": [dict(r) for r in rows]}
