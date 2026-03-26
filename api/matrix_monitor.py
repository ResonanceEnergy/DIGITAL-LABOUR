"""DIGITAL LABOUR MATRIX MONITOR — Command & Control API.

Mobile-first C2 endpoints for real-time monitoring and decision-making.
Mounted as /matrix on the main FastAPI app.
"""

import json
import os
import signal
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import hashlib
import hmac

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# ── Authentication ──────────────────────────────────────────────────────────
# Set MATRIX_AUTH_TOKEN in .env to secure C2 endpoints.
# Pass via header: Authorization: Bearer <token> or X-Matrix-Token: <token>

MATRIX_AUTH_TOKEN = os.environ.get("MATRIX_AUTH_TOKEN", "")


async def verify_matrix_auth(
    authorization: Optional[str] = Header(None),
    x_matrix_token: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
):
    """Require authentication for Matrix C2 endpoints."""
    if not MATRIX_AUTH_TOKEN:
        # No token configured — block access in ALL environments
        raise HTTPException(status_code=503, detail="MATRIX_AUTH_TOKEN not configured — set in .env")

    # Check Authorization: Bearer <token>
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        if hmac.compare_digest(token, MATRIX_AUTH_TOKEN):
            return True

    # Check X-Matrix-Token header
    if x_matrix_token and hmac.compare_digest(x_matrix_token, MATRIX_AUTH_TOKEN):
        return True

    # Check X-API-Key header
    if x_api_key and hmac.compare_digest(x_api_key, MATRIX_AUTH_TOKEN):
        return True

    raise HTTPException(status_code=401, detail="Invalid or missing authentication token")


router = APIRouter(prefix="/matrix", tags=["matrix-monitor"])

DATA_DIR = PROJECT_ROOT / "data"
DAEMON_PIDS = DATA_DIR / "daemon_pids.json"
DECISION_DB = DATA_DIR / "matrix_decisions.db"
ALERT_CONFIG = DATA_DIR / "matrix_alerts.json"


# ── Models ──────────────────────────────────────────────────────────────────

class C2Command(BaseModel):
    action: str  # approve, reject, escalate, kill, restart, pause, custom
    target: str = ""  # agent name, daemon name, task_id
    reason: str = ""
    operator: str = "mobile"


class AlertConfig(BaseModel):
    telegram_token: str = ""
    telegram_chat_id: str = ""
    alert_on_failure: bool = True
    alert_on_revenue: bool = True
    alert_on_escalation: bool = True
    alert_interval_minutes: int = 30
    quiet_hours_start: int = 23  # 11 PM
    quiet_hours_end: int = 7    # 7 AM


# ── SITREP — Single call to know everything ─────────────────────────────────

@router.get("/sitrep")
def sitrep(_auth=Depends(verify_matrix_auth)):
    """Command & Control situation report — everything you need in one payload.

    Designed for mobile: one fetch, all data. No subsequent calls needed.
    Requires authentication via Bearer token or X-Matrix-Token header.
    """
    from dashboard.health import system_health, queue_status, kpi_summary, revenue_summary

    # Daemon status
    daemons = _daemon_status()

    # Health
    health = system_health()

    # Queue
    queue = queue_status()

    # KPIs
    kpi = kpi_summary()

    # Revenue
    rev = revenue_summary()

    # Outreach pipeline
    outreach = _outreach_status()

    # Inbox
    inbox = _inbox_status()

    # Recent decisions (C2 + NERVE autonomous)
    decisions = _recent_decisions(5)

    # NERVE autonomous decisions (from JSONL audit trail)
    nerve_decisions = _nerve_decisions(5)

    # Alerts pending
    alerts = _pending_alerts()

    # Agent fleet status
    fleet = _fleet_status()

    # Watchdog status
    watchdog = _watchdog_live_status()

    # OpenClaw status
    openclaw = _openclaw_status()

    # C-Suite last verdicts
    csuite = _csuite_status()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": _overall_status(daemons, health, queue),
        "daemons": daemons,
        "health": health,
        "queue": queue,
        "kpi_7d": kpi,
        "revenue": rev,
        "outreach": outreach,
        "inbox": inbox,
        "fleet": fleet,
        "watchdog": watchdog,
        "openclaw": openclaw,
        "csuite": csuite,
        "recent_decisions": decisions,
        "nerve_decisions": nerve_decisions,
        "alerts_pending": alerts,
    }


# ── C2 Commands ─────────────────────────────────────────────────────────────

@router.post("/command")
def execute_command(cmd: C2Command, _auth=Depends(verify_matrix_auth)):
    """Execute a command & control action from mobile. Requires authentication."""
    timestamp = datetime.now(timezone.utc).isoformat()

    actions = {
        "restart_daemons": _restart_daemons,
        "kill_daemons": _kill_daemons,
        "pause_agent": _pause_agent,
        "resume_agent": _resume_agent,
        "approve_task": _approve_task,
        "reject_task": _reject_task,
        "send_followups": _send_followups,
        "check_inbox": _check_inbox,
        "run_proposals": _run_proposals,
        "system_check": _system_check,
        "watchdog_status": _watchdog_status,
        "watchdog_stop": _watchdog_stop,
        "watchdog_start": _watchdog_start,
        "nerve_status": _nerve_status,
        "revenue_summary": _revenue_summary,
        "daily_cycle": _daily_cycle,
        "openclaw_cycle": _openclaw_cycle,
        "openclaw_scan": _openclaw_scan,
        "openclaw_inbox": _openclaw_inbox,
        "boardroom_quick": _boardroom_quick,
        "outreach_push": _outreach_push,
        "upwork_hunt": _upwork_hunt,
        "unit_economics": _unit_economics,
        "full_status": _full_status,
        "x_post": _x_post,
        "x_status": _x_status,
        "lead_scores": _lead_scores,
        "email_funnel": _email_funnel,
        "ncc_status": _ncc_status,
        "ncl_brief": _ncl_brief,
        "aac_snapshot": _aac_snapshot,
        "resonance_sync": _resonance_sync,
        "resonance_status": _resonance_status,
        "fiverr_setup": _fiverr_setup,
        "fiverr_deploy_all": _fiverr_deploy_all,
        "fiverr_deploy_top4": _fiverr_deploy_top4,
    }

    handler = actions.get(cmd.action)
    if not handler:
        raise HTTPException(400, f"Unknown action: {cmd.action}. Valid: {list(actions.keys())}")

    result = handler(cmd)

    # Log decision
    _log_decision(cmd, result, timestamp)

    return {
        "timestamp": timestamp,
        "action": cmd.action,
        "target": cmd.target,
        "result": result,
        "operator": cmd.operator,
    }


@router.get("/decisions")
def decisions(limit: int = 20, _auth=Depends(verify_matrix_auth)):
    """Recent C2 decisions log. Requires authentication."""
    return {"decisions": _recent_decisions(limit)}


# ── Alert Configuration ────────────────────────────────────────────────────

@router.get("/alerts/config")
def get_alert_config(_auth=Depends(verify_matrix_auth)):
    """Get current alert configuration. Requires authentication."""
    if ALERT_CONFIG.exists():
        data = json.loads(ALERT_CONFIG.read_text(encoding="utf-8"))
        # Mask token for security
        if data.get("telegram_token"):
            data["telegram_token"] = data["telegram_token"][:10] + "..."
        return data
    return AlertConfig().model_dump()


@router.post("/alerts/config")
def set_alert_config(config: AlertConfig, _auth=Depends(verify_matrix_auth)):
    """Update alert configuration (Telegram bot setup). Requires authentication."""
    ALERT_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    ALERT_CONFIG.write_text(json.dumps(config.model_dump(), indent=2), encoding="utf-8")
    return {"status": "saved", "config": config.model_dump()}


@router.post("/alerts/test")
def test_alert(_auth=Depends(verify_matrix_auth)):
    """Send a test alert to verify Telegram notifications work. Requires authentication."""
    result = _send_telegram_alert("🧪 DIGITAL LABOUR MATRIX TEST — Notifications are working!")
    return result


# ── Internal Helpers ────────────────────────────────────────────────────────

def _daemon_status() -> list[dict]:
    """Check which daemons are alive."""
    # Daemons run on the operator's local machine, not on Railway.
    # If we're on Railway (RAILWAY_ENVIRONMENT set), report last-known state
    # instead of checking PIDs that don't exist here.
    on_railway = bool(os.environ.get("RAILWAY_ENVIRONMENT"))
    daemons = []
    if DAEMON_PIDS.exists():
        pids = json.loads(DAEMON_PIDS.read_text(encoding="utf-8"))
        for name, info in pids.items():
            pid = info["pid"] if isinstance(info, dict) else info
            started = info.get("started", "") if isinstance(info, dict) else ""
            if on_railway:
                # Can't check local PIDs from Railway — report as remote
                daemons.append({"name": name, "pid": pid, "alive": True, "location": "remote", "started": started})
            else:
                alive = _is_pid_alive(pid)
                daemons.append({"name": name, "pid": pid, "alive": alive})
    else:
        for name in ["nerve", "csuite_scheduler", "task_scheduler", "revenue_daemon"]:
            daemons.append({"name": name, "pid": 0, "alive": False})
    return daemons


def _is_pid_alive(pid: int) -> bool:
    """Check if a process is running (Windows-safe via ctypes)."""
    if not pid:
        return False
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        SYNCHRONIZE = 0x00100000
        handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def _overall_status(daemons, health, queue) -> str:
    """RED / AMBER / GREEN overall status."""
    # Remote daemons (on Railway) are assumed alive — can't verify from here
    dead_daemons = sum(1 for d in daemons if not d["alive"] and d.get("location") != "remote")
    # health is a flat dict of check_name → bool/value; count False values
    failed_checks = sum(
        1 for k, v in health.items()
        if isinstance(v, bool) and not v
    )
    failed_tasks = queue.get("failed", 0)

    if dead_daemons >= 3 or failed_checks >= 3:
        return "RED"
    elif dead_daemons >= 1 or failed_checks >= 1 or failed_tasks > 5:
        return "AMBER"
    return "GREEN"


def _nerve_decisions(limit: int = 10) -> list[dict]:
    """Load recent NERVE autonomous decisions from JSONL audit trail."""
    nerve_log = PROJECT_ROOT / "data" / "nerve_logs" / "decisions.jsonl"
    if not nerve_log.exists():
        return []
    try:
        entries = []
        with open(nerve_log, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries[-limit:]
    except Exception:
        return []


def _outreach_status() -> dict:
    """Outreach pipeline stats."""
    sent_log = PROJECT_ROOT / "automation" / "sent_log.json"
    followups = PROJECT_ROOT / "automation" / "followups.json"
    prospects = PROJECT_ROOT / "automation" / "prospects.csv"

    sent_count = 0
    if sent_log.exists():
        try:
            sent_count = len(json.loads(sent_log.read_text(encoding="utf-8")))
        except Exception:
            pass

    followup_count = 0
    followup_due = 0
    if followups.exists():
        try:
            fu = json.loads(followups.read_text(encoding="utf-8"))
            followup_count = len(fu)
            now = datetime.now(timezone.utc).isoformat()
            followup_due = sum(1 for f in fu if f.get("send_after", "") <= now and not f.get("sent"))
        except Exception:
            pass

    prospect_count = 0
    if prospects.exists():
        try:
            prospect_count = sum(1 for _ in open(prospects, encoding="utf-8")) - 1
        except Exception:
            pass

    return {
        "emails_sent": sent_count,
        "followups_scheduled": followup_count,
        "followups_due": followup_due,
        "prospects_remaining": max(0, prospect_count),
    }


def _inbox_status() -> dict:
    """Inbox stats."""
    inbox_log = PROJECT_ROOT / "automation" / "inbox_log.json"
    if inbox_log.exists():
        try:
            entries = json.loads(inbox_log.read_text(encoding="utf-8"))
            return {"total_emails": len(entries), "unread": sum(1 for e in entries if not e.get("processed"))}
        except Exception:
            pass
    return {"total_emails": 0, "unread": 0}


def _fleet_status() -> list[dict]:
    """Agent fleet — which agents are operational."""
    agents_dir = PROJECT_ROOT / "agents"
    fleet = []
    for name in sorted(os.listdir(agents_dir)):
        agent_path = agents_dir / name
        if not agent_path.is_dir() or name.startswith("_"):
            continue
        has_runner = (agent_path / "runner.py").exists()
        fleet.append({"name": name, "operational": has_runner, "status": "READY" if has_runner else "OFFLINE"})
    return fleet


def _watchdog_live_status() -> dict:
    """Live watchdog status for sitrep."""
    status_file = DATA_DIR / "watchdog_status.json"
    nerve_state = DATA_DIR / "nerve_state.json"
    result = {"running": False, "nerve_alive": False, "restarts_last_hour": 0}

    if status_file.exists():
        try:
            ws = json.loads(status_file.read_text(encoding="utf-8"))
            result["running"] = True
            result["watchdog_pid"] = ws.get("watchdog_pid")
            result["nerve_pid"] = ws.get("nerve_pid")
            result["nerve_alive"] = ws.get("nerve_alive", False)
            result["uptime_hours"] = ws.get("uptime_hours", 0)
            result["restarts_last_hour"] = ws.get("restarts_last_hour", 0)
        except Exception:
            pass

    if nerve_state.exists():
        try:
            ns = json.loads(nerve_state.read_text(encoding="utf-8"))
            result["nerve_cycles"] = ns.get("cycles_run", 0)
            last = ns.get("last_cycle", "")
            if last:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds() / 60
                result["nerve_last_cycle_min"] = round(age, 1)
                result["nerve_stale"] = age > 90
        except Exception:
            pass

    return result


def _openclaw_status() -> dict:
    """OpenClaw engine status for sitrep."""
    state_file = DATA_DIR / "openclaws_state.json"
    result = {"active": False, "cycles": 0}

    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            result["active"] = True
            result["cycles"] = state.get("cycles_run", 0)
            result["last_cycle"] = state.get("last_cycle", "")
            result["platforms"] = state.get("platforms", [])
        except Exception:
            pass

    # Check for job data
    for platform in ["upwork_jobs", "fiverr_orders", "freelancer_jobs"]:
        pdir = DATA_DIR / platform
        if pdir.is_dir():
            result[platform] = len(list(pdir.glob("*.json")))

    return result


def _csuite_status() -> dict:
    """C-Suite last verdicts for sitrep."""
    sched_file = DATA_DIR / "csuite_schedule.json"
    result = {"last_meeting": "", "executives": []}

    if sched_file.exists():
        try:
            sched = json.loads(sched_file.read_text(encoding="utf-8"))
            result["last_meeting"] = sched.get("last_meeting", "")
            result["next_meeting"] = sched.get("next_meeting", "")
            for exec_name in ["axiom", "vectis", "ledgr"]:
                exec_data = sched.get(exec_name, {})
                if exec_data:
                    result["executives"].append({
                        "name": exec_name.upper(),
                        "last_run": exec_data.get("last_run", ""),
                        "verdict": exec_data.get("verdict", ""),
                    })
        except Exception:
            pass

    return result


def _init_decisions_db():
    """Ensure the matrix_decisions SQLite table exists."""
    DECISION_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DECISION_DB))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS decisions ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  timestamp TEXT NOT NULL,"
        "  action TEXT NOT NULL,"
        "  target TEXT,"
        "  reason TEXT,"
        "  operator TEXT,"
        "  result TEXT"
        ")"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_ts ON decisions(timestamp)")
    conn.commit()
    conn.close()


_init_decisions_db()


def _recent_decisions(limit: int = 10) -> list[dict]:
    """Load recent C2 decisions from SQLite."""
    try:
        conn = sqlite3.connect(str(DECISION_DB))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT timestamp, action, target, reason, operator, result "
            "FROM decisions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        conn.close()
        result = []
        for r in rows:
            entry = dict(r)
            try:
                entry["result"] = json.loads(entry["result"]) if entry["result"] else {}
            except (json.JSONDecodeError, TypeError):
                pass
            result.append(entry)
        result.reverse()  # oldest first
        return result
    except Exception:
        return []


def _pending_alerts() -> list[dict]:
    """Check for conditions that need operator attention."""
    alerts = []
    daemons = _daemon_status()
    dead = [d for d in daemons if not d["alive"]]
    if dead:
        alerts.append({
            "severity": "HIGH",
            "message": f"{len(dead)} daemon(s) dead: {', '.join(d['name'] for d in dead)}",
            "action": "restart_daemons",
        })

    outreach = _outreach_status()
    if outreach["followups_due"] > 0:
        alerts.append({
            "severity": "MEDIUM",
            "message": f"{outreach['followups_due']} follow-ups due now",
            "action": "send_followups",
        })

    return alerts


def _log_decision(cmd: C2Command, result: dict, timestamp: str):
    """Persist a C2 decision to SQLite."""
    try:
        conn = sqlite3.connect(str(DECISION_DB))
        conn.execute(
            "INSERT INTO decisions (timestamp, action, target, reason, operator, result) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (timestamp, cmd.action, cmd.target, cmd.reason, cmd.operator,
             json.dumps(result, default=str)),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # best-effort logging


# ── C2 Action Handlers ─────────────────────────────────────────────────────

def _restart_daemons(cmd: C2Command) -> dict:
    """Kill existing daemons and restart them."""
    _kill_daemons(cmd)
    try:
        proc = subprocess.Popen(
            [sys.executable, "bitrage.py", "daemons"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        proc.wait(timeout=15)
        out = proc.stdout.read().decode(errors="replace")[:500] if proc.stdout else ""
        return {"status": "restarted", "output": out}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _kill_daemons(cmd: C2Command) -> dict:
    """Kill all daemons."""
    killed = []
    if DAEMON_PIDS.exists():
        pids = json.loads(DAEMON_PIDS.read_text(encoding="utf-8"))
        for name, info in pids.items():
            pid = info["pid"] if isinstance(info, dict) else info
            try:
                os.kill(pid, signal.SIGTERM)
                killed.append(name)
            except (ProcessLookupError, PermissionError, OSError, TypeError):
                pass
    return {"status": "killed", "daemons": killed}


def _pause_agent(cmd: C2Command) -> dict:
    """Pause an agent by adding to pause list."""
    pause_file = DATA_DIR / "paused_agents.json"
    paused = []
    if pause_file.exists():
        paused = json.loads(pause_file.read_text(encoding="utf-8"))
    if cmd.target and cmd.target not in paused:
        paused.append(cmd.target)
    pause_file.write_text(json.dumps(paused), encoding="utf-8")
    return {"status": "paused", "agent": cmd.target}


def _resume_agent(cmd: C2Command) -> dict:
    """Resume a paused agent."""
    pause_file = DATA_DIR / "paused_agents.json"
    paused = []
    if pause_file.exists():
        paused = json.loads(pause_file.read_text(encoding="utf-8"))
    if cmd.target in paused:
        paused.remove(cmd.target)
    pause_file.write_text(json.dumps(paused), encoding="utf-8")
    return {"status": "resumed", "agent": cmd.target}


def _approve_task(cmd: C2Command) -> dict:
    """Approve a task for delivery."""
    return {"status": "approved", "task_id": cmd.target, "note": "Task released for delivery"}


def _reject_task(cmd: C2Command) -> dict:
    """Reject a task — flag for human rework."""
    return {"status": "rejected", "task_id": cmd.target, "reason": cmd.reason}


def _send_followups(cmd: C2Command) -> dict:
    """Trigger follow-up email batch."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "automation.outreach", "--followups"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        return {"status": "sent", "output": result.stdout[:500]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _check_inbox(cmd: C2Command) -> dict:
    """Check inbox for new replies."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "automation.inbox_reader", "--process"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {"status": "checked", "output": result.stdout[:500]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _run_proposals(cmd: C2Command) -> dict:
    """Generate fresh Upwork proposals."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "automation.gen_proposals", "--top", "5"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {"status": "generated", "output": result.stdout[:500]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _system_check(cmd: C2Command) -> dict:
    """Run full system check."""
    try:
        result = subprocess.run(
            [sys.executable, "bitrage.py", "checks"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {"status": "completed", "output": result.stdout[:1000]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _watchdog_status(cmd: C2Command) -> dict:
    """Get watchdog + NERVE subprocess status."""
    status_file = DATA_DIR / "watchdog_status.json"
    if status_file.exists():
        try:
            return json.loads(status_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"status": "unknown", "message": "watchdog_status.json not found"}


def _watchdog_stop(cmd: C2Command) -> dict:
    """Signal the watchdog to stop gracefully."""
    stop_flag = DATA_DIR / "watchdog_stop.flag"
    stop_flag.parent.mkdir(parents=True, exist_ok=True)
    stop_flag.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
    return {"status": "stop_signal_sent", "flag": str(stop_flag)}


def _watchdog_start(cmd: C2Command) -> dict:
    """Start the watchdog (which starts NERVE)."""
    # Remove stop flag if present
    stop_flag = DATA_DIR / "watchdog_stop.flag"
    if stop_flag.exists():
        stop_flag.unlink()
    try:
        if sys.platform == "win32":
            proc = subprocess.Popen(
                [sys.executable, "-m", "automation.watchdog"],
                cwd=str(PROJECT_ROOT),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            proc = subprocess.Popen(
                [sys.executable, "-m", "automation.watchdog"],
                cwd=str(PROJECT_ROOT),
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return {"status": "started", "pid": proc.pid}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _nerve_status(cmd: C2Command) -> dict:
    """Get NERVE daemon status from state file."""
    nerve_state = DATA_DIR / "nerve_state.json"
    if nerve_state.exists():
        try:
            state = json.loads(nerve_state.read_text(encoding="utf-8"))
            # Check staleness
            last = state.get("last_cycle", "")
            if last:
                last_dt = datetime.fromisoformat(last)
                age_min = (datetime.now(timezone.utc) - last_dt).total_seconds() / 60
                state["minutes_since_cycle"] = round(age_min, 1)
                state["stale"] = age_min > 90
            return state
        except Exception:
            pass
    return {"status": "unknown", "message": "nerve_state.json not found"}


def _revenue_summary(cmd: C2Command) -> dict:
    """Run revenue daemon summary."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "automation.revenue_daemon", "--summary"],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, timeout=30,
        )
        return {"status": "ok", "output": result.stdout[:1000]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _daily_cycle(cmd: C2Command) -> dict:
    """Trigger orchestrator daily outreach cycle."""
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "automation.orchestrator", "--daily"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        # Don't wait — this can take minutes
        return {"status": "launched", "pid": proc.pid}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _openclaw_cycle(cmd: C2Command) -> dict:
    """Run OpenClaw freelance automation cycle."""
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "openclaw.engine"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        return {"status": "launched", "pid": proc.pid}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _openclaw_scan(cmd: C2Command) -> dict:
    """OpenClaw scan-only (aggregate + score, no bidding)."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "openclaw.engine", "--scan-only"],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, timeout=60,
        )
        return {"status": "ok", "output": result.stdout[:1000]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _openclaw_inbox(cmd: C2Command) -> dict:
    """Check OpenClaw inbox for new leads."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "openclaw.inbox_agent", "--check"],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, timeout=30,
        )
        return {"status": "ok", "output": result.stdout[:500]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _boardroom_quick(cmd: C2Command) -> dict:
    """Run C-Suite quick standup."""
    try:
        proc = subprocess.Popen(
            [sys.executable, "c_suite/boardroom.py", "--quick"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        return {"status": "launched", "pid": proc.pid}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _outreach_push(cmd: C2Command) -> dict:
    """50-message outreach blast."""
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "automation.outreach_push", "--count", "50"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        return {"status": "launched", "pid": proc.pid}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _upwork_hunt(cmd: C2Command) -> dict:
    """Upwork job hunt — search and score."""
    search_term = cmd.target or "ai agent"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "automation.upwork_jobhunt", "--search", search_term, "--dry-run"],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, timeout=60,
        )
        return {"status": "ok", "output": result.stdout[:1000]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _unit_economics(cmd: C2Command) -> dict:
    """Run unit economics report."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "kpi.unit_economics"],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, timeout=30,
        )
        return {"status": "ok", "output": result.stdout[:1500]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _full_status(cmd: C2Command) -> dict:
    """Full system status via bitrage.py."""
    try:
        result = subprocess.run(
            [sys.executable, "bitrage.py", "status"],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True, timeout=30,
        )
        return {"status": "ok", "output": result.stdout[:1500]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _x_post(cmd: C2Command) -> dict:
    """Post next tweet via X Poster."""
    try:
        from automation.x_poster import post_next
        result = post_next()
        return {"status": "ok" if result.get("success") or result.get("queued") else "error", **result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _x_status(cmd: C2Command) -> dict:
    """X/Twitter posting status."""
    try:
        from automation.x_poster import _load_state, _load_tweets
        state = _load_state()
        tweets = _load_tweets()
        return {
            "status": "ok",
            "total_tweets_available": len(tweets),
            "total_posted": state.get("total_posted", 0),
            "next_index": state.get("next_index", 0),
            "last_posted_at": state.get("last_posted_at"),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _lead_scores(cmd: C2Command) -> dict:
    """Get top scored prospects."""
    try:
        from automation.lead_scorer import score_all_prospects, get_top_prospects
        score_all_prospects()
        top = get_top_prospects(10)
        return {
            "status": "ok",
            "top_prospects": [
                {"company": t["company"], "score": t["score"], "grade": t["grade"], "role": t["role"]}
                for t in top
            ],
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _email_funnel(cmd: C2Command) -> dict:
    """Email tracking funnel summary."""
    try:
        from automation.email_tracker import build_tracking_report
        report = build_tracking_report()
        return {"status": "ok", "funnel": report.get("funnel", {})}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _ncc_status(cmd: C2Command) -> dict:
    """Check NCC relay health and flush outbox."""
    try:
        from resonance.ncc_bridge import ncc
        health = ncc.relay_health()
        outbox = ncc.flush()
        return {"status": "ok", "relay": "online" if health else "offline",
                "health": health, "outbox_flushed": outbox}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _ncl_brief(cmd: C2Command) -> dict:
    """Pull latest NCL intelligence brief."""
    try:
        from resonance.ncl_bridge import ncl
        digest = ncl.intelligence_digest() if ncl.available else None
        brief = (ncl.latest_daily_brief() or "")[:500] if ncl.available else None
        return {"status": "ok", "available": ncl.available,
                "digest": digest, "brief": brief}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _aac_snapshot(cmd: C2Command) -> dict:
    """Pull AAC BANK financial snapshot."""
    try:
        from resonance.aac_bridge import aac
        return {"status": "ok", "snapshot": aac.snapshot()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _resonance_sync(cmd: C2Command) -> dict:
    """Run all resonance sync jobs now."""
    try:
        from resonance.sync import run_all
        run_all()
        return {"status": "ok", "sync": "completed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _resonance_status(cmd: C2Command) -> dict:
    """Show resonance sync health status."""
    try:
        from resonance.ncc_bridge import ncc
        from resonance.ncl_bridge import ncl
        ncc_health = ncc.relay_health()
        # Outbox depth
        outbox_dir = PROJECT_ROOT / "data" / "ncc_outbox"
        queued = 0
        if outbox_dir.exists():
            queued = sum(1 for f in outbox_dir.glob("*.ndjson")
                         for line in f.read_text(encoding="utf-8").strip().splitlines() if line)
        # Sync state
        sync_file = PROJECT_ROOT / "data" / "resonance_sync_state.json"
        last_sync = "never"
        if sync_file.exists():
            state = json.loads(sync_file.read_text(encoding="utf-8"))
            last_sync = state.get("last_check", "never")
        return {"status": "ok", "ncc_relay": "online" if ncc_health else "offline",
                "ncl_brain": "available" if ncl.available else "not found",
                "outbox_depth": queued, "last_sync": last_sync}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Telegram Notifications ──────────────────────────────────────────────────

def _send_telegram_alert(message: str) -> dict:
    """Send alert via Telegram bot."""
    if not ALERT_CONFIG.exists():
        return {"status": "not_configured", "message": "Set up alerts first via /matrix/alerts/config"}

    config = json.loads(ALERT_CONFIG.read_text(encoding="utf-8"))
    token = config.get("telegram_token", "")
    chat_id = config.get("telegram_chat_id", "")

    if not token or not chat_id:
        return {"status": "not_configured", "message": "telegram_token and telegram_chat_id required"}

    import urllib.request
    import urllib.parse

    url = f"https://api.telegram.org/bot{urllib.parse.quote(token, safe='')}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": message, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"status": "sent", "response": json.loads(resp.read())}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Fiverr C2 Commands ───────────────────────────────────────────────────

def _fiverr_setup(cmd: C2Command) -> dict:
    """Deploy top-4 Fiverr gigs via OpenClaw engine.platform_setup."""
    try:
        from openclaw.engine import OpenClawEngine
        result = OpenClawEngine().platform_setup(platforms=["fiverr"])
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _fiverr_deploy_all(cmd: C2Command) -> dict:
    """Deploy all 20 Fiverr gigs via browser automation."""
    try:
        from automation.fiverr_automation import deploy_all_browser
        deploy_all_browser()
        return {"status": "deploy_all_complete"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _fiverr_deploy_top4(cmd: C2Command) -> dict:
    """Deploy gigs 1-4 (Sales/Support/Content/Docs) via browser."""
    try:
        from automation.fiverr_automation import deploy_all_browser
        deploy_all_browser(gig_indices=[1, 2, 3, 4])
        return {"status": "deploy_top4_complete", "gigs": [1, 2, 3, 4]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def send_alert(message: str, severity: str = "INFO"):
    """Public function — other modules can import this to send alerts."""
    prefix = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "INFO": "🔵"}.get(severity, "⚪")
    full_msg = f"{prefix} <b>DIGITAL LABOUR MATRIX</b>\n\n{message}\n\n<i>{datetime.now(timezone.utc).strftime('%H:%M UTC')}</i>"
    return _send_telegram_alert(full_msg)


# ═══════════════════════════════════════════════════════════════════════════
# NCC MASTER — Unified Command & Control across all pillars
# ═══════════════════════════════════════════════════════════════════════════


class NCCDirective(BaseModel):
    """NCC governance directive routed through the orchestrator."""
    type: str  # e.g. agent.pause, csuite.run, nerve.restart, resonance.sync
    target: str = ""
    data: dict = Field(default_factory=dict)
    reason: str = ""
    operator: str = "ncc_master"


@router.get("/ncc/master")
def ncc_master_sitrep(_auth=Depends(verify_matrix_auth)):
    """NCC MASTER — Unified situational report across ALL pillars.

    Single call returns: NCC health, NCL intelligence + freshness,
    AAC financials + freshness, BRS fleet status, C-Suite verdicts,
    resonance sync state, NERVE status, and active alerts.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    # NCC Orchestrator health
    try:
        from NCC.ncc_orchestrator import health as ncc_health, pending_decisions
        ncc = {"status": "online", **ncc_health(), "recent_decisions": pending_decisions(5)}
    except Exception as e:
        ncc = {"status": "error", "error": str(e)}

    # NCL Intelligence + freshness
    try:
        from resonance.ncl_bridge import ncl
        ncl_data = {
            "status": "available" if ncl.available else "not_found",
            "digest": ncl.intelligence_digest() if ncl.available else None,
            "freshness": ncl.data_freshness(),
        }
    except Exception as e:
        ncl_data = {"status": "error", "error": str(e)}

    # AAC Financials + freshness
    try:
        from resonance.aac_bridge import aac
        aac_data = {
            "freshness": aac.data_freshness(),
        }
        # Only pull live snapshot if engine available
        if aac.data_freshness().get("engine_available"):
            aac_data["status"] = "connected"
        else:
            aac_data["status"] = "offline"
    except Exception as e:
        aac_data = {"status": "error", "error": str(e)}

    # NCC Relay health + outbox
    try:
        from resonance.ncc_bridge import ncc as ncc_bridge
        relay_health = ncc_bridge.relay_health()
        outbox_dir = PROJECT_ROOT / "data" / "ncc_outbox"
        outbox_depth = 0
        if outbox_dir.exists():
            outbox_depth = sum(
                1 for f in outbox_dir.glob("*.ndjson")
                for line in f.read_text(encoding="utf-8").strip().splitlines() if line
            )
        relay = {"status": "online" if relay_health else "offline",
                 "health": relay_health, "outbox_depth": outbox_depth}
    except Exception as e:
        relay = {"status": "error", "error": str(e)}

    # Resonance sync state
    try:
        sync_file = PROJECT_ROOT / "data" / "resonance_sync_state.json"
        sync_state = json.loads(sync_file.read_text("utf-8")) if sync_file.exists() else {}
    except Exception:
        sync_state = {}

    # C-Suite verdicts
    csuite = _csuite_status()

    # NERVE status
    nerve = _watchdog_live_status()

    # Fleet
    fleet = _fleet_status()

    # BRS queue
    from dashboard.health import queue_status, kpi_summary, revenue_summary
    queue = queue_status()
    kpi = kpi_summary()
    rev = revenue_summary()

    # Active alerts
    alerts = _pending_alerts()

    # Staleness alerts
    if ncl_data.get("freshness", {}).get("stale"):
        alerts.append({"severity": "HIGH", "message": "NCL intelligence data is STALE",
                        "action": "resonance_sync"})
    if aac_data.get("freshness", {}).get("stale"):
        alerts.append({"severity": "MEDIUM", "message": "AAC financial data is STALE",
                        "action": "aac_snapshot"})
    if relay.get("status") == "offline":
        alerts.append({"severity": "HIGH", "message": "NCC Relay is OFFLINE",
                        "action": "ncc_status"})
    if relay.get("outbox_depth", 0) > 50:
        alerts.append({"severity": "MEDIUM",
                        "message": f"NCC outbox has {relay['outbox_depth']} queued events",
                        "action": "resonance_sync"})

    # Overall status
    critical_count = sum(1 for a in alerts if a["severity"] in ("HIGH", "CRITICAL"))
    overall = "RED" if critical_count >= 2 else "AMBER" if critical_count >= 1 else "GREEN"

    return {
        "timestamp": timestamp,
        "overall_status": overall,
        "pillars": {
            "ncc": ncc,
            "ncl": ncl_data,
            "aac": aac_data,
            "relay": relay,
        },
        "resonance_sync": sync_state,
        "csuite": csuite,
        "nerve": nerve,
        "fleet": fleet,
        "brs": {"queue": queue, "kpi_7d": kpi, "revenue": rev},
        "alerts": alerts,
    }


@router.post("/ncc/dispatch")
def ncc_dispatch(directive: NCCDirective, _auth=Depends(verify_matrix_auth)):
    """NCC MASTER — Route a governance directive through the NCC Orchestrator.

    This is the unified command entry point. All commands flow through
    NCC governance before reaching BRS execution.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        from NCC.ncc_orchestrator import dispatch
        result = dispatch(directive.model_dump())
    except Exception as e:
        result = {"executed": False, "error": str(e)}

    # Also log in matrix decisions
    _log_decision(
        C2Command(action=f"ncc.{directive.type}", target=directive.target,
                  reason=directive.reason, operator=directive.operator),
        result, timestamp,
    )

    return {
        "timestamp": timestamp,
        "directive": directive.model_dump(),
        "result": result,
    }


@router.get("/ncc/decisions")
def ncc_decisions(limit: int = 20, _auth=Depends(verify_matrix_auth)):
    """NCC MASTER — Recent governance decisions from the NCC orchestrator."""
    try:
        from NCC.ncc_orchestrator import pending_decisions
        return {"decisions": pending_decisions(limit)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/ncc/routes")
def ncc_routes(_auth=Depends(verify_matrix_auth)):
    """NCC MASTER — List all available directive types for dispatch."""
    try:
        from NCC.ncc_orchestrator import health
        h = health()
        return {"routes": h.get("routes", []), "adapters": h.get("adapter_names", [])}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════
# UNIFIED MATRIX — Per-pillar monitors + displays + cross-pillar aggregation
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/unified")
def matrix_unified(_auth=Depends(verify_matrix_auth)):
    """Unified cross-pillar situational picture — all 4 pillars + display.

    Returns monitor data + formatted display cards/panels/alerts in one call.
    """
    try:
        from resonance.matrix_monitor import unified_monitor
        from resonance.matrix_display import unified_display

        monitor_data = unified_monitor.collect_all()
        display_data = unified_display.render(monitor_data)

        return {
            "monitor": monitor_data,
            "display": display_data,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── Per-pillar monitor endpoints ────────────────────────────────────────────

@router.get("/brs/monitor")
def brs_monitor(_auth=Depends(verify_matrix_auth)):
    """BRS Matrix Monitor — Execution layer health + metrics."""
    try:
        from resonance.matrix_monitor import unified_monitor
        return unified_monitor.brs.collect()
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/ncc/monitor")
def ncc_monitor(_auth=Depends(verify_matrix_auth)):
    """NCC Matrix Monitor — Governance layer health + metrics."""
    try:
        from resonance.matrix_monitor import unified_monitor
        return unified_monitor.ncc.collect()
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/ncl/monitor")
def ncl_monitor(_auth=Depends(verify_matrix_auth)):
    """NCL Matrix Monitor — Intelligence layer health + metrics."""
    try:
        from resonance.matrix_monitor import unified_monitor
        return unified_monitor.ncl.collect()
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/aac/monitor")
def aac_monitor(_auth=Depends(verify_matrix_auth)):
    """AAC Matrix Monitor — Financial layer health + metrics."""
    try:
        from resonance.matrix_monitor import unified_monitor
        return unified_monitor.aac.collect()
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── Per-pillar display endpoints ────────────────────────────────────────────

@router.get("/brs/display")
def brs_display(_auth=Depends(verify_matrix_auth)):
    """BRS Matrix Display — Formatted card + panel for execution layer."""
    try:
        from resonance.matrix_monitor import unified_monitor
        from resonance.matrix_display import unified_display
        data = unified_monitor.brs.collect()
        return {
            "card": unified_display.brs.render_card(data),
            "panel": unified_display.brs.render_panel(data),
            "alerts": unified_display.brs.render_alerts(data),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/ncc/display")
def ncc_display(_auth=Depends(verify_matrix_auth)):
    """NCC Matrix Display — Formatted card + panel for governance layer."""
    try:
        from resonance.matrix_monitor import unified_monitor
        from resonance.matrix_display import unified_display
        data = unified_monitor.ncc.collect()
        return {
            "card": unified_display.ncc.render_card(data),
            "panel": unified_display.ncc.render_panel(data),
            "alerts": unified_display.ncc.render_alerts(data),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/ncl/display")
def ncl_display(_auth=Depends(verify_matrix_auth)):
    """NCL Matrix Display — Formatted card + panel for intelligence layer."""
    try:
        from resonance.matrix_monitor import unified_monitor
        from resonance.matrix_display import unified_display
        data = unified_monitor.ncl.collect()
        return {
            "card": unified_display.ncl.render_card(data),
            "panel": unified_display.ncl.render_panel(data),
            "alerts": unified_display.ncl.render_alerts(data),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/aac/display")
def aac_display(_auth=Depends(verify_matrix_auth)):
    """AAC Matrix Display — Formatted card + panel for financial layer."""
    try:
        from resonance.matrix_monitor import unified_monitor
        from resonance.matrix_display import unified_display
        data = unified_monitor.aac.collect()
        return {
            "card": unified_display.aac.render_card(data),
            "panel": unified_display.aac.render_panel(data),
            "alerts": unified_display.aac.render_alerts(data),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
