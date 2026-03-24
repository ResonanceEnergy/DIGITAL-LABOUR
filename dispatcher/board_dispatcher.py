"""Board Dispatcher — Converts C-Suite board directives into executable tasks.

Reads board meeting output from boardroom.py, parses the execution_queue,
and dispatches each directive to the appropriate Digital Labour subsystem:
NERVE phases, automation modules, dispatcher queue, or alert channels.

Usage:
    python -m dispatcher.board_dispatcher --latest       # Dispatch from latest board output
    python -m dispatcher.board_dispatcher --file FILE    # Dispatch from specific board JSON
    python -m dispatcher.board_dispatcher --status       # Show dispatch history
    python -m dispatcher.board_dispatcher --pending      # Show pending directives
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from automation.decision_log import log_decision

STATE_FILE = PROJECT_ROOT / "data" / "board_dispatch_state.json"
BOARD_OUTPUT_DIR = PROJECT_ROOT / "output" / "c_suite" / "board"

# Map board directive owners/actions to internal dispatch targets
DISPATCH_ROUTES = {
    # C-Suite owner → subsystem
    "AXIOM": "strategy",
    "VECTIS": "operations",
    "LEDGR": "finance",
    # Action keyword → module
    "outreach": "automation.outreach",
    "email": "automation.cold_email_spray",
    "bid": "automation.autobidder",
    "prospect": "automation.prospect_engine",
    "post": "automation.x_poster",
    "linkedin": "automation.linkedin_poster",
    "crm": "automation.crm_tracker",
    "invoice": "billing.tracker",
    "pricing": "billing.payments",
    "pipeline": "dispatcher.router",
    "agent": "dispatcher.router",
    "kpi": "kpi.tracker",
    "revenue": "automation.revenue_daemon",
    "nerve": "automation.nerve",
}


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {
        "dispatched": [],
        "pending": [],
        "total_dispatched": 0,
        "last_session": None,
    }


def _save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _find_latest_board_output() -> dict | None:
    """Find the most recent board meeting output JSON."""
    if not BOARD_OUTPUT_DIR.exists():
        return None
    files = sorted(BOARD_OUTPUT_DIR.glob("board_*.json"), reverse=True)
    if not files:
        return None
    return json.loads(files[0].read_text(encoding="utf-8"))


def _resolve_target(directive: dict) -> str:
    """Determine which subsystem should execute this directive."""
    action = directive.get("action", "").lower()
    owner = directive.get("owner", "").upper()

    # Check action keywords for specific module routing
    for keyword, module in DISPATCH_ROUTES.items():
        if keyword in action:
            return module

    # Fall back to owner-based routing
    return DISPATCH_ROUTES.get(owner, "dispatcher.router")


def dispatch_directives(board_output: dict) -> dict:
    """Parse board synthesis and dispatch each directive.

    Takes a full board meeting output dict (from boardroom.py)
    and routes each execution_queue item to the appropriate subsystem.
    """
    synthesis = board_output.get("synthesis", board_output)
    session_id = synthesis.get("session", board_output.get("session_id", "unknown"))
    queue = synthesis.get("execution_queue", [])

    if not queue:
        return {"session": session_id, "dispatched": 0, "error": "No execution queue in board output"}

    state = _load_state()
    dispatched = []
    now = datetime.now(timezone.utc).isoformat()

    for directive in queue:
        dispatch_id = str(uuid4())[:8]
        target = _resolve_target(directive)
        priority = directive.get("priority", "MEDIUM")

        entry = {
            "dispatch_id": dispatch_id,
            "board_session": session_id,
            "rank": directive.get("rank", 0),
            "directive_id": directive.get("id", ""),
            "owner": directive.get("owner", ""),
            "action": directive.get("action", ""),
            "priority": priority,
            "target_module": target,
            "deadline": directive.get("deadline", ""),
            "kpi": directive.get("kpi", ""),
            "dependencies": directive.get("dependencies", []),
            "status": "dispatched",
            "dispatched_at": now,
            "completed_at": None,
            "result": None,
        }

        dispatched.append(entry)

        log_decision(
            actor="BOARD_DISPATCHER",
            action="dispatch_directive",
            reasoning=f"Board directive #{directive.get('rank', '?')} from {directive.get('owner', '?')}: {directive.get('action', '')[:60]}",
            outcome=f"Dispatched {dispatch_id} → {target} [{priority}]",
        )

        print(f"  [#{directive.get('rank', '?')}] {directive.get('action', '')[:55]}")
        print(f"       → {target} [{priority}] (id={dispatch_id})")

    # Update state
    state["dispatched"].extend(dispatched)
    state["total_dispatched"] += len(dispatched)
    state["last_session"] = session_id

    # Keep pending list: directives with unmet dependencies
    completed_ids = {d["directive_id"] for d in state["dispatched"] if d.get("status") == "completed"}
    state["pending"] = [
        d for d in state["dispatched"]
        if d.get("status") == "dispatched"
        and any(dep not in completed_ids for dep in d.get("dependencies", []))
    ]

    _save_state(state)

    return {
        "session": session_id,
        "dispatched": len(dispatched),
        "directives": dispatched,
    }


def get_pending() -> list[dict]:
    """Get directives not yet completed."""
    state = _load_state()
    return [d for d in state.get("dispatched", []) if d.get("status") != "completed"]


def mark_complete(dispatch_id: str, result: str = ""):
    """Mark a dispatched directive as completed."""
    state = _load_state()
    for d in state.get("dispatched", []):
        if d["dispatch_id"] == dispatch_id:
            d["status"] = "completed"
            d["completed_at"] = datetime.now(timezone.utc).isoformat()
            d["result"] = result
            break
    _save_state(state)


def get_status() -> dict:
    """Get dispatch statistics."""
    state = _load_state()
    dispatched = state.get("dispatched", [])
    return {
        "total_dispatched": state.get("total_dispatched", 0),
        "pending": len([d for d in dispatched if d.get("status") == "dispatched"]),
        "completed": len([d for d in dispatched if d.get("status") == "completed"]),
        "last_session": state.get("last_session"),
    }


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Board Dispatcher — C-Suite → Execution")
    parser.add_argument("--latest", action="store_true", help="Dispatch from latest board output")
    parser.add_argument("--file", help="Dispatch from specific board JSON file")
    parser.add_argument("--status", action="store_true", help="Show dispatch stats")
    parser.add_argument("--pending", action="store_true", help="Show pending directives")
    args = parser.parse_args()

    if args.status:
        st = get_status()
        print(f"\n  Board Dispatch Status:")
        print(f"    Total dispatched: {st['total_dispatched']}")
        print(f"    Pending:          {st['pending']}")
        print(f"    Completed:        {st['completed']}")
        print(f"    Last session:     {st['last_session']}")
    elif args.pending:
        pending = get_pending()
        if not pending:
            print("\n  No pending directives.")
        else:
            print(f"\n  Pending Directives ({len(pending)}):")
            for d in pending:
                print(f"    [{d['priority']}] {d['action'][:55]} → {d['target_module']}")
    elif args.file:
        board = json.loads(Path(args.file).read_text(encoding="utf-8"))
        result = dispatch_directives(board)
        print(f"\n  Dispatched {result['dispatched']} directives from {result['session']}")
    elif args.latest:
        board = _find_latest_board_output()
        if not board:
            print("\n  No board output found in output/c_suite/board/")
            return
        result = dispatch_directives(board)
        print(f"\n  Dispatched {result['dispatched']} directives from {result['session']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
