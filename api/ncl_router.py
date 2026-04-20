"""NCL Operations Commander — API Router.

Exposes the NCL Ops Commander functions as REST endpoints so the
workstation dashboard can trigger and display them.

Endpoints:
    GET  /api/v1/ncl/status          — Full ops status report
    GET  /api/v1/ncl/health          — Division health check
    POST /api/v1/ncl/daily-push      — Trigger daily ops push
    POST /api/v1/ncl/weekly-goals    — Force weekly goal generation
    GET  /api/v1/ncl/weekly-goals    — Read latest weekly goals
    GET  /api/v1/ncl/divisions       — Division definitions + live state
    GET  /api/v1/ncl/escalations     — Recent escalation log
    POST /api/v1/ncl/dispatch/:div   — Fire warm-up task to a division
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/ncl", tags=["NCL Operations Commander"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
WEEKLY_GOALS_DIR = DATA_DIR / "weekly_goals"
NCL_STATE_FILE = DATA_DIR / "ncl_ops_state.json"


# ── Helpers ──────────────────────────────────────────────────────

def _load_state() -> dict:
    if NCL_STATE_FILE.exists():
        return json.loads(NCL_STATE_FILE.read_text(encoding="utf-8"))
    return {
        "last_daily_push": None,
        "last_weekly_goals": None,
        "cycle_count": 0,
        "divisions_status": {},
        "escalations_sent": 0,
        "tasks_fired_today": 0,
    }


def _get_divisions() -> dict:
    """Import DIVISIONS from the ops commander."""
    try:
        from NCL.ncl_operations_commander import DIVISIONS
        return DIVISIONS
    except ImportError:
        return {}


# ── GET /status ──────────────────────────────────────────────────

@router.get("/status")
async def ncl_status():
    """Full NCL operational status."""
    state = _load_state()
    divisions = _get_divisions()

    div_summary = {}
    for div_id, div_info in divisions.items():
        div_summary[div_id] = {
            "name": div_info["name"],
            "code": div_info["code"],
            "head": div_info["head"],
            "tam": div_info["tam"],
            "agents": div_info["agents"],
            "services": div_info["services"],
            "max_daily": div_info.get("max_daily"),
            "cost_ceiling": div_info.get("cost_ceiling"),
            "qa_gate": div_info.get("qa_gate", False),
            "status": state.get("divisions_status", {}).get(div_id, "UNKNOWN"),
        }

    # Count weekly goal files
    goal_files = sorted(WEEKLY_GOALS_DIR.glob("*_combined_plan.json")) if WEEKLY_GOALS_DIR.exists() else []

    return {
        "commander": "NCL Operations Commander",
        "cycle_count": state.get("cycle_count", 0),
        "last_daily_push": state.get("last_daily_push"),
        "last_weekly_goals": state.get("last_weekly_goals"),
        "tasks_fired_today": state.get("tasks_fired_today", 0),
        "escalations_sent": state.get("escalations_sent", 0),
        "weekly_goal_plans": len(goal_files),
        "latest_plan": goal_files[-1].name if goal_files else None,
        "divisions": div_summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── GET /health ──────────────────────────────────────────────────

@router.get("/health")
async def ncl_health():
    """Run division health check."""
    try:
        from NCL.ncl_operations_commander import check_division_health
        results = check_division_health()
        return {
            "status": "ok",
            "divisions": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── POST /daily-push ─────────────────────────────────────────────

@router.post("/daily-push")
async def ncl_daily_push():
    """Trigger NCL daily operations push."""
    try:
        from NCL.ncl_operations_commander import daily_ops_push
        report = daily_ops_push()
        return {
            "status": "completed",
            "cycle": report.get("cycle"),
            "division_health": report.get("division_health", {}),
            "dispatched": report.get("dispatched", {}),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /weekly-goals ───────────────────────────────────────────

@router.post("/weekly-goals")
async def ncl_generate_weekly_goals():
    """Force weekly goal generation for all divisions."""
    try:
        from NCL.ncl_operations_commander import generate_weekly_goals
        result = generate_weekly_goals(force=True)
        return {
            "status": "generated",
            "week": result.get("week"),
            "divisions": list(result.get("divisions", {}).keys()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /weekly-goals ────────────────────────────────────────────

@router.get("/weekly-goals")
async def ncl_get_weekly_goals():
    """Get latest weekly goals."""
    if not WEEKLY_GOALS_DIR.exists():
        return {"status": "none", "plans": []}

    combined_files = sorted(WEEKLY_GOALS_DIR.glob("*_combined_plan.json"))
    if not combined_files:
        return {"status": "none", "plans": []}

    # Return latest plan
    latest = combined_files[-1]
    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
        return {
            "status": "ok",
            "latest_file": latest.name,
            "plan": data,
            "total_plans": len(combined_files),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── GET /divisions ───────────────────────────────────────────────

@router.get("/divisions")
async def ncl_divisions():
    """Get all division definitions with live state."""
    divisions = _get_divisions()
    state = _load_state()

    result = []
    for div_id, div_info in divisions.items():
        result.append({
            "id": div_id,
            "name": div_info["name"],
            "code": div_info["code"],
            "head": div_info["head"],
            "tam": div_info["tam"],
            "priority": div_info.get("priority"),
            "agents": div_info["agents"],
            "services": div_info["services"],
            "service_count": len(div_info["services"]),
            "agent_count": len(div_info["agents"]),
            "max_daily": div_info.get("max_daily"),
            "cost_ceiling": div_info.get("cost_ceiling"),
            "qa_gate": div_info.get("qa_gate", False),
            "bus_topic": div_info.get("bus_topic"),
            "status": state.get("divisions_status", {}).get(div_id, "UNKNOWN"),
        })

    return {"divisions": result, "total_agents": sum(d["agent_count"] for d in result),
            "total_services": sum(d["service_count"] for d in result)}


# ── GET /escalations ─────────────────────────────────────────────

@router.get("/escalations")
async def ncl_escalations():
    """Get recent escalations."""
    try:
        from automation.decision_log import get_escalations
        pending = get_escalations()
        return {"escalations": pending[:20], "count": len(pending)}
    except Exception:
        return {"escalations": [], "count": 0, "note": "decision_log not available"}


# ── POST /dispatch/{division} ────────────────────────────────────

class DispatchRequest(BaseModel):
    topic: str = "Operations warm-up task"
    priority: int = 3


@router.post("/dispatch/{division}")
async def ncl_dispatch_division(division: str, req: DispatchRequest):
    """Fire a task to a specific division."""
    divisions = _get_divisions()
    if division not in divisions:
        raise HTTPException(status_code=404, detail=f"Division '{division}' not found. Valid: {list(divisions.keys())}")

    div_info = divisions[division]
    service_name = div_info["services"][0]

    # Resolve service name to router-compatible task_type
    try:
        from NCL.ncl_operations_commander import SERVICE_TO_TASKTYPE
        task_type = SERVICE_TO_TASKTYPE.get(service_name, service_name)
    except ImportError:
        task_type = service_name

    try:
        import urllib.request
        import os
        payload = json.dumps({
            "task_type": task_type,
            "client": "ncl-workstation",
            "provider": os.environ.get("DEFAULT_PROVIDER", "openai"),
            "priority": req.priority,
            "division": div_info["code"],
            "inputs": {
                "content": req.topic,
                "doc_type": service_name,
            },
            "sync": False,
            "schema_version": "2.0",
        }).encode()

        api_req = urllib.request.Request(
            f"http://localhost:{os.environ.get('PORT', '8000')}/tasks",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(api_req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            return {
                "status": "dispatched",
                "division": div_info["code"],
                "task_type": task_type,
                "task_id": result.get("task_id"),
                "message": result.get("message", "queued"),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /internal-ops ──────────────────────────────────────────

@router.post("/internal-ops")
async def ncl_internal_ops(mode: str = "daily"):
    """Trigger internal operations engine — makes Bit Rage build itself."""
    try:
        from automation.internal_ops import generate_daily_tasks, generate_weekly_tasks, get_status
        if mode == "daily":
            result = generate_daily_tasks()
        elif mode == "weekly":
            result = generate_weekly_tasks(force=True)
        elif mode == "full":
            daily = generate_daily_tasks()
            weekly = generate_weekly_tasks(force=True)
            result = {"daily": daily, "weekly": weekly}
        elif mode == "status":
            result = get_status()
        else:
            raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}. Use: daily, weekly, full, status")
        return {"status": "ok", "mode": mode, "result": result,
                "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /output-brief ──────────────────────────────────────────

@router.get("/output-brief")
async def ncl_output_brief():
    """Intelligence brief from the output store — what's been produced."""
    try:
        from utils.output_awareness import get_intelligence_brief, get_output_gaps
        brief = get_intelligence_brief()
        brief["gaps"] = get_output_gaps(_get_divisions())
        return brief
    except Exception as e:
        return {"error": str(e), "total_outputs": 0}
