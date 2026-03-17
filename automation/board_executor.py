"""Board Executor — Executes dispatched C-Suite directives.

Processes directives from board_dispatcher, invokes the target modules,
tracks completion status, and reports results back to the C-Suite.

Usage:
    python -m automation.board_executor --run           # Execute all pending directives
    python -m automation.board_executor --run-one ID    # Execute a specific directive
    python -m automation.board_executor --status        # Show execution history
    python -m automation.board_executor --report        # Generate execution report for C-Suite
"""

import argparse
import importlib
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from automation.decision_log import log_decision

STATE_FILE = PROJECT_ROOT / "data" / "board_executor_state.json"

# Module → callable function mapping for auto-execution
EXECUTABLE_MODULES = {
    "automation.outreach": ("automation.outreach", "run_outreach_cycle"),
    "automation.cold_email_spray": ("automation.cold_email_spray", "run_spray"),
    "automation.autobidder": ("automation.autobidder", "run_scan"),
    "automation.prospect_engine": ("automation.prospect_engine", "run_discovery"),
    "automation.x_poster": ("automation.x_poster", "post_next"),
    "automation.linkedin_poster": ("automation.linkedin_poster", "post_next"),
    "automation.crm_tracker": ("automation.crm_tracker", "sync_from_sent_log"),
    "automation.revenue_daemon": ("automation.revenue_daemon", "run_cycle"),
    "automation.nerve": ("automation.nerve", "run_phase"),
    "billing.tracker": ("billing.tracker", "get_summary"),
    "kpi.tracker": ("kpi.tracker", "get_kpi"),
    "dispatcher.router": ("dispatcher.router", "route_task"),
}


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {
        "executions": [],
        "total_executed": 0,
        "total_success": 0,
        "total_failed": 0,
        "last_run": None,
    }


def _save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def execute_directive(directive: dict) -> dict:
    """Execute a single dispatched directive.

    Args:
        directive: Dict with dispatch_id, target_module, action, priority etc.

    Returns execution result dict.
    """
    dispatch_id = directive.get("dispatch_id", "unknown")
    target = directive.get("target_module", "")
    action = directive.get("action", "")
    now = datetime.now(timezone.utc).isoformat()

    result = {
        "dispatch_id": dispatch_id,
        "target_module": target,
        "action": action,
        "started_at": now,
        "completed_at": None,
        "status": "running",
        "output": None,
        "error": None,
    }

    print(f"  [EXEC] {action[:55]}")
    print(f"         Target: {target}")

    # Check if we have an auto-executable mapping
    if target in EXECUTABLE_MODULES:
        module_path, func_name = EXECUTABLE_MODULES[target]
        try:
            mod = importlib.import_module(module_path)
            func = getattr(mod, func_name, None)
            if func and callable(func):
                output = func()
                result["status"] = "completed"
                result["output"] = str(output)[:500] if output else "executed"
                print(f"         Result: completed")
            else:
                result["status"] = "skipped"
                result["output"] = f"Function {func_name} not found in {module_path}"
                print(f"         Result: function not found")
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            print(f"         Result: FAILED — {e}")
    else:
        # No auto-executable mapping — log as "manual" requiring human action
        result["status"] = "manual"
        result["output"] = f"No auto-executor for {target}. Requires manual execution."
        print(f"         Result: queued for manual execution")

    result["completed_at"] = datetime.now(timezone.utc).isoformat()

    log_decision(
        actor="BOARD_EXECUTOR",
        action="execute_directive",
        reasoning=f"Directive {dispatch_id}: {action[:60]}",
        outcome=f"Status: {result['status']}",
    )

    return result


def run_all_pending() -> dict:
    """Execute all pending directives from the board dispatcher."""
    from dispatcher.board_dispatcher import get_pending, mark_complete

    pending = get_pending()
    if not pending:
        print("\n  No pending directives to execute.")
        return {"executed": 0, "results": []}

    state = _load_state()
    results = []

    # Sort by priority: CRITICAL > HIGH > MEDIUM > LOW
    priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    pending.sort(key=lambda d: priority_order.get(d.get("priority", "MEDIUM"), 2))

    print(f"\n{'='*60}")
    print(f"  BOARD EXECUTOR — {len(pending)} directives pending")
    print(f"{'='*60}\n")

    for directive in pending:
        # Check dependencies
        deps = directive.get("dependencies", [])
        completed_ids = {
            e["dispatch_id"] for e in state.get("executions", [])
            if e.get("status") == "completed"
        }
        unmet = [d for d in deps if d not in completed_ids]
        if unmet:
            print(f"  [SKIP] {directive.get('action', '')[:45]} — unmet deps: {unmet}")
            continue

        result = execute_directive(directive)
        results.append(result)

        state["executions"].append(result)
        state["total_executed"] += 1
        if result["status"] == "completed":
            state["total_success"] += 1
            mark_complete(directive["dispatch_id"], result.get("output", ""))
        elif result["status"] == "failed":
            state["total_failed"] += 1

    state["last_run"] = datetime.now(timezone.utc).isoformat()
    _save_state(state)

    success = sum(1 for r in results if r["status"] == "completed")
    failed = sum(1 for r in results if r["status"] == "failed")
    manual = sum(1 for r in results if r["status"] == "manual")
    print(f"\n  Summary: {success} completed, {failed} failed, {manual} manual")

    return {"executed": len(results), "success": success, "failed": failed, "manual": manual, "results": results}


def run_single(dispatch_id: str) -> dict:
    """Execute a specific directive by dispatch_id."""
    from dispatcher.board_dispatcher import get_pending, mark_complete

    pending = get_pending()
    directive = next((d for d in pending if d["dispatch_id"] == dispatch_id), None)
    if not directive:
        return {"error": f"Directive {dispatch_id} not found in pending queue"}

    result = execute_directive(directive)
    state = _load_state()
    state["executions"].append(result)
    state["total_executed"] += 1
    if result["status"] == "completed":
        state["total_success"] += 1
        mark_complete(dispatch_id, result.get("output", ""))
    elif result["status"] == "failed":
        state["total_failed"] += 1
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    _save_state(state)
    return result


def generate_report() -> dict:
    """Generate execution report for C-Suite review."""
    state = _load_state()
    executions = state.get("executions", [])

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_executed": state.get("total_executed", 0),
        "success_rate": f"{state.get('total_success', 0) / max(state.get('total_executed', 1), 1):.0%}",
        "recent_executions": executions[-20:],
        "failed": [e for e in executions if e.get("status") == "failed"],
        "manual_queue": [e for e in executions if e.get("status") == "manual"],
    }

    print(f"\n  Board Executor Report:")
    print(f"    Executed: {report['total_executed']}")
    print(f"    Success Rate: {report['success_rate']}")
    print(f"    Failed: {len(report['failed'])}")
    print(f"    Manual Queue: {len(report['manual_queue'])}")

    return report


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Board Executor — Execute C-Suite directives")
    parser.add_argument("--run", action="store_true", help="Execute all pending directives")
    parser.add_argument("--run-one", metavar="ID", help="Execute a specific directive by dispatch_id")
    parser.add_argument("--status", action="store_true", help="Show execution stats")
    parser.add_argument("--report", action="store_true", help="Generate execution report")
    args = parser.parse_args()

    if args.run:
        run_all_pending()
    elif args.run_one:
        result = run_single(args.run_one)
        print(f"\n  Result: {result.get('status')} — {result.get('output', result.get('error', ''))[:80]}")
    elif args.report:
        generate_report()
    elif args.status:
        state = _load_state()
        print(f"\n  Executor Status:")
        print(f"    Total Executed: {state.get('total_executed', 0)}")
        print(f"    Success:        {state.get('total_success', 0)}")
        print(f"    Failed:         {state.get('total_failed', 0)}")
        print(f"    Last Run:       {state.get('last_run', 'Never')}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
