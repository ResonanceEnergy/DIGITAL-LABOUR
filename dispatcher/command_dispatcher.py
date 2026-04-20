"""Bit Rage Command Dispatcher — Internal command routing for the BRL agent fleet.

Dispatches directives to the BRL agent fleet via adapters.

Supported directive types:
  - agent.pause / agent.resume  — control individual agents
  - csuite.run / csuite.quick   — trigger C-Suite meetings
  - nerve.restart / nerve.stop  — control NERVE daemon
  - resonance.sync              — trigger cross-pillar sync
  - outreach.push / outreach.followups — email pipeline
  - system.check                — full diagnostic
  - relay.publish               — publish event to relay
"""
from __future__ import annotations

import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_log = logging.getLogger("brl.command_dispatcher")

DISPATCHER_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = DISPATCHER_ROOT.parent
ADAPTERS_DIR = DISPATCHER_ROOT / "adapters"
DECISION_LOG = PROJECT_ROOT / "data" / "command_decisions.jsonl"

# ── Directive routing table ─────────────────────────────────────

_ROUTES: dict[str, callable] = {}


def _register(dtype: str):
    """Decorator to register a directive handler."""
    def wrapper(fn):
        _ROUTES[dtype] = fn
        return fn
    return wrapper


@_register("agent.pause")
def _agent_pause(d: dict) -> dict:
    pause_file = PROJECT_ROOT / "data" / "paused_agents.json"
    paused = json.loads(pause_file.read_text("utf-8")) if pause_file.exists() else []
    target = d.get("target", "")
    if target and target not in paused:
        paused.append(target)
        pause_file.parent.mkdir(parents=True, exist_ok=True)
        pause_file.write_text(json.dumps(paused), "utf-8")
    return {"executed": True, "action": "agent.pause", "target": target}


@_register("agent.resume")
def _agent_resume(d: dict) -> dict:
    pause_file = PROJECT_ROOT / "data" / "paused_agents.json"
    paused = json.loads(pause_file.read_text("utf-8")) if pause_file.exists() else []
    target = d.get("target", "")
    if target in paused:
        paused.remove(target)
        pause_file.write_text(json.dumps(paused), "utf-8")
    return {"executed": True, "action": "agent.resume", "target": target}


@_register("csuite.run")
def _csuite_run(d: dict) -> dict:
    exec_name = d.get("target", "boardroom")
    script = {"axiom": "c_suite/axiom.py", "vectis": "c_suite/vectis.py",
              "ledgr": "c_suite/ledgr.py", "boardroom": "c_suite/boardroom.py"}.get(exec_name, "c_suite/boardroom.py")
    try:
        proc = subprocess.Popen(
            [sys.executable, script], cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        return {"executed": True, "action": "csuite.run", "target": exec_name, "pid": proc.pid}
    except Exception as e:
        return {"executed": False, "error": str(e)}


@_register("csuite.quick")
def _csuite_quick(d: dict) -> dict:
    try:
        proc = subprocess.Popen(
            [sys.executable, "c_suite/boardroom.py", "--quick"], cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        return {"executed": True, "action": "csuite.quick", "pid": proc.pid}
    except Exception as e:
        return {"executed": False, "error": str(e)}


@_register("nerve.restart")
def _nerve_restart(d: dict) -> dict:
    stop_flag = PROJECT_ROOT / "data" / "watchdog_stop.flag"
    if stop_flag.exists():
        stop_flag.unlink()
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "automation.watchdog"], cwd=str(PROJECT_ROOT),
            start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return {"executed": True, "action": "nerve.restart", "pid": proc.pid}
    except Exception as e:
        return {"executed": False, "error": str(e)}


@_register("nerve.stop")
def _nerve_stop(d: dict) -> dict:
    stop_flag = PROJECT_ROOT / "data" / "watchdog_stop.flag"
    stop_flag.parent.mkdir(parents=True, exist_ok=True)
    stop_flag.write_text(datetime.now(timezone.utc).isoformat(), "utf-8")
    return {"executed": True, "action": "nerve.stop"}


@_register("resonance.sync")
def _resonance_sync(d: dict) -> dict:
    try:
        from resonance.sync import run_all
        run_all()
        return {"executed": True, "action": "resonance.sync"}
    except Exception as e:
        return {"executed": False, "error": str(e)}


@_register("outreach.push")
def _outreach_push(d: dict) -> dict:
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "automation.outreach_push", "--count", "50"],
            cwd=str(PROJECT_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        return {"executed": True, "action": "outreach.push", "pid": proc.pid}
    except Exception as e:
        return {"executed": False, "error": str(e)}


@_register("outreach.followups")
def _outreach_followups(d: dict) -> dict:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "automation.outreach", "--followups"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=60,
        )
        return {"executed": True, "action": "outreach.followups", "output": result.stdout[:500]}
    except Exception as e:
        return {"executed": False, "error": str(e)}


@_register("system.check")
def _system_check(d: dict) -> dict:
    try:
        result = subprocess.run(
            [sys.executable, "bitrage.py", "checks"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=120,
        )
        return {"executed": True, "action": "system.check", "output": result.stdout[:1000]}
    except Exception as e:
        return {"executed": False, "error": str(e)}


@_register("relay.publish")
def _relay_publish(d: dict) -> dict:
    try:
        from resonance.ncc_bridge import ncc
        event_type = d.get("event_type", "ncl.sync.v1.alops.directive")
        data = d.get("data", {})
        ok = ncc.publish(event_type, data)
        return {"executed": True, "action": "relay.publish", "published": ok}
    except Exception as e:
        return {"executed": False, "error": str(e)}


# ── Core Dispatch ───────────────────────────────────────────────

def dispatch(directive: dict) -> dict:
    """Dispatch a command directive to the BRL fleet.

    Args:
        directive: dict with at minimum {"type": "<directive_type>"}
                   Optional: "target", "data", "reason", "operator"

    Returns:
        dict with execution result including "executed" bool.
    """
    dtype = directive.get("type", "unknown")
    _log.info("Command dispatcher routing: %s", dtype)

    handler = _ROUTES.get(dtype)
    if not handler:
        _log.warning("No route for directive type: %s (available: %s)", dtype, list(_ROUTES.keys()))
        return {"executed": False, "error": f"Unknown directive type: {dtype}",
                "available": list(_ROUTES.keys())}

    result = handler(directive)
    _log_decision(directive, result)
    return result


def _log_decision(directive: dict, result: dict):
    """Append directive + result to command decision audit trail."""
    DECISION_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "directive": directive,
        "result": result,
    }
    with open(DECISION_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def health() -> dict:
    """Return command dispatcher health status."""
    adapters = list(ADAPTERS_DIR.glob("*_adapter.py"))
    return {
        "dispatcher": "online",
        "adapters_loaded": len(adapters),
        "adapter_names": [a.stem for a in adapters],
        "routes": list(_ROUTES.keys()),
        "decision_log": str(DECISION_LOG),
    }


def pending_decisions(limit: int = 20) -> list[dict]:
    """Read recent command decisions from audit trail."""
    if not DECISION_LOG.exists():
        return []
    entries = []
    for line in DECISION_LOG.read_text("utf-8").strip().splitlines():
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries[-limit:]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Bit Rage Command Dispatcher")
    parser.add_argument("--health", action="store_true", help="Show health status")
    parser.add_argument("--dispatch", type=str, help="Dispatch directive JSON")
    parser.add_argument("--decisions", type=int, nargs="?", const=20, help="Show recent decisions")
    args = parser.parse_args()

    if args.dispatch:
        d = json.loads(args.dispatch)
        print(json.dumps(dispatch(d), indent=2))
    elif args.decisions is not None:
        for entry in pending_decisions(args.decisions):
            print(json.dumps(entry))
    else:
        print(json.dumps(health(), indent=2))
