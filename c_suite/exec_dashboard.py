"""DEPRECATED as CLI — Use bitrage_monitor.py --exec or 'DIGITAL LABOUR MATRIX MONITOR.exe' instead.

This module is still imported as a library by bitrage_monitor.py.
Do NOT delete it. The CLI entry point (__main__ block) is superseded.

Replacement commands:
    bitrage_monitor.py --exec      # replaces: python c_suite/exec_dashboard.py
    bitrage_monitor.py --json      # replaces: python c_suite/exec_dashboard.py --json

Original description:
    Executive Dashboard — C-Suite command view of DIGITAL LABOUR.
    Unified console output showing all three executives' status,
    the execution queue, and system vitals at a glance.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _latest_report(exec_name: str, subfolder: str) -> dict | None:
    """Load the most recent report for an executive."""
    report_dir = PROJECT_ROOT / "output" / "c_suite" / subfolder
    if not report_dir.exists():
        return None
    files = sorted(report_dir.glob("*.json"), reverse=True)
    if not files:
        return None
    return json.loads(files[0].read_text(encoding="utf-8"))


def _latest_board() -> dict | None:
    board_dir = PROJECT_ROOT / "output" / "c_suite" / "board"
    if not board_dir.exists():
        return None
    files = sorted(board_dir.glob("board_*.json"), reverse=True)
    if not files:
        return None
    return json.loads(files[0].read_text(encoding="utf-8"))


def gather_dashboard() -> dict:
    """Gather all executive data for dashboard display."""
    # System vitals
    try:
        from dashboard.health import full_dashboard
        vitals = full_dashboard()
    except Exception:
        vitals = {}

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "axiom_latest": _latest_report("AXIOM", "axiom"),
        "vectis_latest": _latest_report("VECTIS", "vectis"),
        "ledgr_latest": _latest_report("LEDGR", "ledgr"),
        "last_board": _latest_board(),
        "vitals": vitals,
    }


def print_exec_dashboard():
    """Print the executive command dashboard."""
    data = gather_dashboard()
    vitals = data.get("vitals", {})

    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║           NCC — DIGITAL LABOUR EXECUTIVE COMMAND CENTER              ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print(f"║  Timestamp: {data['timestamp']:<56} ║")
    print("╠══════════════════════════════════════════════════════════════════════╣")

    # C-Suite Status Row
    print("║                                                                      ║")
    print("║  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐      ║")

    # AXIOM
    axiom = data.get("axiom_latest") or {}
    axiom_verdict = axiom.get("ceo_verdict", "No report")[:40]
    axiom_priority = axiom.get("top_priority", "—")[:40]

    # VECTIS
    vectis = data.get("vectis_latest") or {}
    vectis_status = vectis.get("ops_status", "—")
    vectis_verdict = vectis.get("coo_verdict", "No report")[:40]

    # LEDGR
    ledgr = data.get("ledgr_latest") or {}
    ledgr_status = ledgr.get("financial_status", "—")
    ledgr_verdict = ledgr.get("cfo_verdict", "No report")[:40]

    print("║  │   ⚡ AXIOM       │ │   ⚙️ VECTIS      │ │   💰 LEDGR       │      ║")
    print("║  │   CEO            │ │   COO            │ │   CFO            │      ║")
    print(f"║  │   Ops: {'ACTIVE':<10}│ │   Ops: {vectis_status:<10}│ │   Fin: {ledgr_status:<10}│      ║")
    print("║  └──────────────────┘ └──────────────────┘ └──────────────────┘      ║")
    print("║                                                                      ║")

    # Verdicts
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║  EXECUTIVE VERDICTS                                                  ║")
    print(f"║  AXIOM:  {axiom_verdict:<61}║")
    print(f"║  VECTIS: {vectis_verdict:<61}║")
    print(f"║  LEDGR:  {ledgr_verdict:<61}║")

    # System Vitals
    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║  SYSTEM VITALS                                                       ║")

    health = vitals.get("health", {})
    providers = health.get("llm_providers", [])
    queue = vitals.get("queue", {})
    kpi = vitals.get("kpi_7d", {})
    rev = vitals.get("revenue_30d", {})

    print(f"║  Providers: {', '.join(providers) if providers else 'NONE':<57} ║")
    print(f"║  Queue: {queue.get('queued', 0)} queued | {queue.get('completed', 0)} completed | {queue.get('failed', 0)} failed{' ':<26}║")
    print(f"║  Tasks (7d): {kpi.get('total_tasks', 0)} total | {kpi.get('pass_rate', 'N/A')} pass rate{' ':<31}║")
    print(f"║  Revenue (30d): ${rev.get('total_revenue', 0):.2f} | Margin: ${rev.get('gross_margin', 0):.2f}{' ':<26}║")
    print(f"║  Clients: {vitals.get('active_clients', 0):<59} ║")

    # Last Board Meeting
    board = data.get("last_board")
    if board:
        synthesis = board.get("synthesis", {})
        board_status = synthesis.get("overall_status", "—")
        board_verdict = synthesis.get("board_verdict", "No board meeting yet")[:55]
        queue_items = synthesis.get("execution_queue", [])

        print("╠══════════════════════════════════════════════════════════════════════╣")
        print(f"║  LAST BOARD MEETING — {board_status:<48}║")
        print(f"║  {board_verdict:<68} ║")

        if queue_items:
            print("║                                                                      ║")
            print("║  EXECUTION QUEUE:                                                     ║")
            for item in queue_items[:5]:
                action = item.get("action", "")[:45]
                owner = item.get("owner", "?")
                print(f"║   {item.get('rank', '?')}. [{owner:<6}] {action:<53}║")

    print("╠══════════════════════════════════════════════════════════════════════╣")
    print("║  COMMANDS                                                            ║")
    print("║    python c_suite/boardroom.py           # Full board meeting        ║")
    print("║    python c_suite/boardroom.py --quick   # Quick standup             ║")
    print("║    python c_suite/boardroom.py --exec axiom   # CEO only             ║")
    print("║    python c_suite/boardroom.py --exec vectis  # COO only             ║")
    print("║    python c_suite/boardroom.py --exec ledgr   # CFO only             ║")
    print("║    python c_suite/exec_dashboard.py      # This dashboard            ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")


def main():
    parser = argparse.ArgumentParser(description="Executive Dashboard — C-Suite Command Center")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of formatted dashboard")
    args = parser.parse_args()

    if args.json:
        data = gather_dashboard()
        print(json.dumps(data, indent=2, default=str))
    else:
        print_exec_dashboard()


if __name__ == "__main__":
    main()
