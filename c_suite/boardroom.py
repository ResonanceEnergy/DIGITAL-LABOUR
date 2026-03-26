"""C-Suite Orchestrator — Convenes AXIOM, VECTIS, and LEDGR for coordinated execution.

The Board Room. All three executives run, their outputs are synthesized
into a unified execution plan with no conflicting directives.

Usage:
    python c_suite/boardroom.py                # Full board meeting
    python c_suite/boardroom.py --quick        # Quick standup
    python c_suite/boardroom.py --exec axiom   # Run one executive only
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.llm_client import call_llm
from c_suite.axiom import AxiomCEO
from c_suite.vectis import VectisCOO
from c_suite.ledgr import LedgrCFO


# ── Board Synthesis Prompt ──────────────────────────────────────────────────

SYNTHESIS_SYSTEM = """You are the NCC Board Synthesizer for DIGITAL LABOUR.

You receive reports from three autonomous C-suite agents:
- AXIOM (CEO): Strategic directives, growth plays, resource allocation
- VECTIS (COO): Operational grades, bottlenecks, pipeline optimization
- LEDGR (CFO): Financial analysis, pricing, margins, cost alerts

Your job:
1. Resolve any conflicts between the three executives
2. Prioritize directives into a single ranked execution queue
3. Detect if any executive's recommendation would hurt another's domain
4. Produce one unified execution plan with clear ownership and deadlines

Output valid JSON:
{
    "session": "BOARD-<YYYYMMDD-HHMMSS>",
    "timestamp": "<ISO>",
    "executive_summary": "<3-4 sentence synthesis of all three reports>",
    "overall_status": "GREEN|YELLOW|RED",
    "conflicts_resolved": [
        {
            "between": ["<exec1>", "<exec2>"],
            "issue": "<what conflicted>",
            "resolution": "<how you resolved it>",
            "winner": "<whose position prevailed>"
        }
    ],
    "execution_queue": [
        {
            "rank": 1,
            "id": "<directive ID>",
            "owner": "AXIOM|VECTIS|LEDGR",
            "action": "<specific action>",
            "priority": "CRITICAL|HIGH|MEDIUM",
            "deadline": "<timeframe>",
            "dependencies": ["<other directive IDs>"],
            "kpi": "<measurable success metric>"
        }
    ],
    "risk_register": [
        {
            "risk": "<what could go wrong>",
            "probability": "HIGH|MEDIUM|LOW",
            "impact": "HIGH|MEDIUM|LOW",
            "mitigation": "<how to prevent/handle>",
            "owner": "AXIOM|VECTIS|LEDGR"
        }
    ],
    "next_board_meeting": "<when to reconvene>",
    "board_verdict": "<1-2 sentence mandate>"
}
"""


# ── Directive-to-dispatch mapping ───────────────────────────────────────────

_KEYWORD_MAP = {
    "outreach": "outreach.push",
    "followup": "outreach.followups",
    "follow-up": "outreach.followups",
    "sync": "resonance.sync",
    "board": "csuite.run",
    "meeting": "csuite.run",
    "nerve": "nerve.restart",
    "health": "system.check",
    "diagnostic": "system.check",
    "pause": "agent.pause",
    "resume": "agent.resume",
}


def _map_directive_to_dispatch(action: str, owner: str) -> str | None:
    """Best-effort mapping of a board directive action string to an NCC dispatch type."""
    action_lower = action.lower()
    for keyword, dtype in _KEYWORD_MAP.items():
        if keyword in action_lower:
            return dtype
    # Owner-based fallback
    if owner == "VECTIS":
        return "system.check"
    return None


# ── Board Room ──────────────────────────────────────────────────────────────

class BoardRoom:
    """Orchestrates all three C-suite agents and produces unified execution plans."""

    def __init__(self, provider: str | None = None):
        self.provider = provider
        self.ceo = AxiomCEO(provider=provider)
        self.coo = VectisCOO(provider=provider)
        self.cfo = LedgrCFO(provider=provider)

    def convene(self, quick: bool = False) -> dict:
        """Run a full board meeting — all 3 executives report, then synthesize."""
        session_id = f"BOARD-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        print(f"\n{'='*70}")
        print(f"  NCC BOARD MEETING — {session_id}")
        print(f"  {'Quick Standup' if quick else 'Full Strategic Review'}")
        print(f"{'='*70}")

        start = time.time()
        reports = {}

        # Run each executive
        print("\n[1/4] AXIOM (CEO) presenting...")
        t0 = time.time()
        try:
            if quick:
                reports["axiom"] = self.ceo.morning_brief()
            else:
                reports["axiom"] = self.ceo.run()
            print(f"  Done ({time.time()-t0:.1f}s)")
        except Exception as e:
            reports["axiom"] = {"error": str(e), "codename": "AXIOM"}
            print(f"  ERROR: {e}")

        print("\n[2/4] VECTIS (COO) presenting...")
        t0 = time.time()
        try:
            if quick:
                reports["vectis"] = self.coo.ops_check()
            else:
                reports["vectis"] = self.coo.run()
            print(f"  Done ({time.time()-t0:.1f}s)")
        except Exception as e:
            reports["vectis"] = {"error": str(e), "codename": "VECTIS"}
            print(f"  ERROR: {e}")

        print("\n[3/4] LEDGR (CFO) presenting...")
        t0 = time.time()
        try:
            if quick:
                reports["ledgr"] = self.cfo.cash_check()
            else:
                reports["ledgr"] = self.cfo.run()
            print(f"  Done ({time.time()-t0:.1f}s)")
        except Exception as e:
            reports["ledgr"] = {"error": str(e), "codename": "LEDGR"}
            print(f"  ERROR: {e}")

        # Synthesize
        print("\n[4/4] Synthesizing board directives...")
        t0 = time.time()

        user_msg = (
            f"BOARD SESSION: {session_id}\n\n"
            f"CEO (AXIOM) REPORT:\n{json.dumps(reports.get('axiom', {}), indent=2, default=str)}\n\n"
            f"COO (VECTIS) REPORT:\n{json.dumps(reports.get('vectis', {}), indent=2, default=str)}\n\n"
            f"CFO (LEDGR) REPORT:\n{json.dumps(reports.get('ledgr', {}), indent=2, default=str)}\n\n"
            "Synthesize these three reports into a unified execution plan. "
            "Resolve conflicts. Rank directives. Assign ownership. Set deadlines. "
            "Revenue growth is the supreme objective."
        )

        raw = call_llm(
            system_prompt=SYNTHESIS_SYSTEM,
            user_message=user_msg,
            provider=self.provider,
            temperature=0.3,
            json_mode=True,
        )

        synthesis = json.loads(raw)
        print(f"  Done ({time.time()-t0:.1f}s)")

        total_time = time.time() - start

        # Package final output
        board_output = {
            "session_id": session_id,
            "mode": "quick" if quick else "full",
            "duration_s": round(total_time, 1),
            "individual_reports": reports,
            "synthesis": synthesis,
        }

        self._save(board_output, session_id)
        self._print_summary(synthesis, total_time)

        # Publish board results to NCC governance relay
        try:
            from resonance.ncc_bridge import ncc
            ncc.publish_csuite_report(synthesis)
            print("[BOARD] Report published → NCC Relay")
        except Exception:
            pass

        # Auto-execute CRITICAL/HIGH directives via NCC Orchestrator
        self._auto_execute(synthesis)

        return board_output

    def _auto_execute(self, synthesis: dict):
        """Feed CRITICAL/HIGH execution_queue items to NCC Orchestrator."""
        queue = synthesis.get("execution_queue", [])
        if not queue:
            return
        try:
            from NCC.ncc_orchestrator import dispatch
        except Exception:
            return

        executed = 0
        for item in queue:
            priority = (item.get("priority") or "").upper()
            if priority not in ("CRITICAL", "HIGH"):
                continue
            action = item.get("action", "")
            owner = (item.get("owner") or "").upper()
            # Map board directives to NCC dispatch types
            dtype = _map_directive_to_dispatch(action, owner)
            if not dtype:
                continue
            directive = {
                "type": dtype,
                "source": f"board/{synthesis.get('session', 'unknown')}",
                "target": item.get("id", ""),
                "payload": item,
            }
            result = dispatch(directive)
            if result.get("executed"):
                executed += 1
                print(f"  [AUTO-EXEC] #{item.get('rank')} {dtype} → OK")
            else:
                print(f"  [AUTO-EXEC] #{item.get('rank')} {dtype} → SKIP ({result.get('error', 'no handler')})")
        if executed:
            print(f"[BOARD] Auto-executed {executed} directive(s) via NCC Orchestrator")

    def run_single(self, executive: str) -> dict:
        """Run a single executive agent."""
        execs = {"axiom": self.ceo, "vectis": self.coo, "ledgr": self.cfo}
        agent = execs.get(executive.lower())
        if not agent:
            raise ValueError(f"Unknown executive: {executive}. Options: axiom, vectis, ledgr")

        print(f"\n[{agent.codename}] Running {agent.title}...")
        return agent.run()

    def _save(self, data: dict, session_id: str):
        out_dir = PROJECT_ROOT / "output" / "c_suite" / "board"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"board_{ts}.json"
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        print(f"\n[BOARD] Full session saved → {path.name}")

    def _print_summary(self, synthesis: dict, duration: float):
        status = synthesis.get("overall_status", "UNKNOWN")
        color = {"GREEN": "✅", "YELLOW": "⚠️", "RED": "🔴"}.get(status, "❓")

        print(f"\n{'='*70}")
        print(f"  NCC BOARD — UNIFIED EXECUTION PLAN")
        print(f"{'='*70}")
        print(f"\n  Overall: {color} {status} | Duration: {duration:.0f}s")
        print(f"  Verdict: {synthesis.get('board_verdict', 'N/A')}")
        print(f"\n  {synthesis.get('executive_summary', 'N/A')}")

        conflicts = synthesis.get("conflicts_resolved", [])
        if conflicts:
            print(f"\n  Conflicts Resolved: {len(conflicts)}")
            for c in conflicts:
                print(f"    • {c.get('between', [])} — {c.get('resolution', '')}")

        queue = synthesis.get("execution_queue", [])
        if queue:
            print(f"\n  EXECUTION QUEUE ({len(queue)} actions):")
            print(f"  {'#':<4} {'Owner':<8} {'Priority':<10} {'Action'}")
            print(f"  {'-'*4} {'-'*8} {'-'*10} {'-'*40}")
            for item in queue:
                print(f"  {item.get('rank', '?'):<4} {item.get('owner', '?'):<8} {item.get('priority', '?'):<10} {item.get('action', '')[:50]}")

        risks = synthesis.get("risk_register", [])
        if risks:
            print(f"\n  RISKS ({len(risks)}):")
            for r in risks:
                print(f"    [{r.get('probability', '?')}/{r.get('impact', '?')}] {r.get('risk', '')} → {r.get('owner', '?')}")

        print(f"\n  Next Board Meeting: {synthesis.get('next_board_meeting', 'N/A')}")


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="NCC Board Room — C-Suite Orchestrator")
    parser.add_argument("--quick", action="store_true", help="Quick standup instead of full board meeting")
    parser.add_argument("--exec", dest="executive", help="Run single executive: axiom, vectis, ledgr")
    parser.add_argument("--provider", help="Force LLM provider for all agents")
    args = parser.parse_args()

    board = BoardRoom(provider=args.provider)

    if args.executive:
        result = board.run_single(args.executive)
        print(json.dumps(result, indent=2, default=str))
    else:
        board.convene(quick=args.quick)


if __name__ == "__main__":
    main()
