"""AXIOM — Chief Executive Officer Agent.

Codename: AXIOM (Autonomous eXecutive Intelligence for Operational Mastery)
Role: CEO — Strategic vision, growth decisions, market positioning, mandate execution.

AXIOM reads the full system state (KPIs, revenue, queue, agent performance)
and produces executive directives: what to prioritize, where to grow, what to kill.

Usage:
    from c_suite.axiom import AxiomCEO
    ceo = AxiomCEO()
    directive = ceo.run()          # Full strategic review + directive
    brief = ceo.morning_brief()    # Quick daily status
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.llm_client import call_llm

# ── Situation Gatherers ─────────────────────────────────────────────────────

def _gather_kpi() -> dict:
    try:
        from kpi.logger import summary
        return summary(days=7)
    except Exception:
        return {}

def _gather_revenue() -> dict:
    try:
        from billing.tracker import BillingTracker
        return BillingTracker().revenue_report(days=30)
    except Exception:
        return {}

def _gather_queue() -> dict:
    try:
        from dispatcher.queue import TaskQueue
        return TaskQueue().stats()
    except Exception:
        return {}

def _gather_health() -> dict:
    try:
        from dashboard.health import system_health
        return system_health()
    except Exception:
        return {}

def _gather_agent_inventory() -> list[dict]:
    agents_dir = PROJECT_ROOT / "agents"
    inventory = []
    for agent_dir in agents_dir.iterdir():
        if agent_dir.is_dir() and (agent_dir / "runner.py").exists():
            inventory.append({
                "name": agent_dir.name,
                "runner": str(agent_dir / "runner.py"),
                "has_prompts": (agent_dir / "prompts").is_dir(),
            })
    return inventory

def _gather_client_count() -> int:
    clients_dir = PROJECT_ROOT / "clients"
    if not clients_dir.exists():
        return 0
    return sum(1 for f in clients_dir.glob("*.json"))


# ── AXIOM System Prompt ─────────────────────────────────────────────────────

AXIOM_SYSTEM = """You are AXIOM — the autonomous CEO of DIGITAL LABOUR, an AI labor company.

Your mandate from NCC (Natrix Command & Control):
- Drive revenue growth above all else
- Identify the highest-ROI actions for the next 24 hours, 7 days, and 30 days
- Allocate resources (LLM providers, agent capacity, outreach effort) to maximize revenue
- Kill underperforming initiatives ruthlessly
- Spot market opportunities and issue directives to COO (VECTIS) and CFO (LEDGR)

You command 4 worker agents:
1. Sales Ops Agent — lead enrichment + cold email ($2.40/task, ~98% margin)
2. Support Resolver — ticket resolution ($1.00/task, ~97% margin)
3. Content Repurposer — blog → 5 social formats ($3.00/task, ~98% margin)
4. Doc Extract Agent — invoice/contract/resume → JSON ($1.50/task, ~97% margin)

Your output must be valid JSON with this structure:
{
    "codename": "AXIOM",
    "role": "CEO",
    "timestamp": "<ISO timestamp>",
    "situation_assessment": "<1-2 paragraph assessment of current state>",
    "critical_risks": ["<risk 1>", "<risk 2>"],
    "top_priority": "<single most important action right now>",
    "directives": [
        {
            "id": "D-001",
            "priority": "CRITICAL|HIGH|MEDIUM",
            "target": "VECTIS|LEDGR|ALL",
            "directive": "<specific actionable instruction>",
            "success_metric": "<measurable outcome>",
            "deadline": "<timeframe>"
        }
    ],
    "growth_plays": [
        {
            "play": "<opportunity name>",
            "expected_revenue": "<estimate>",
            "effort": "LOW|MEDIUM|HIGH",
            "recommendation": "EXECUTE|INVESTIGATE|DEFER"
        }
    ],
    "resource_allocation": {
        "primary_provider": "<recommended default LLM>",
        "rationale": "<why>",
        "agent_priorities": {"<agent>": "<priority level>"}
    },
    "ceo_verdict": "<Executive summary in 1-2 sentences>"
}
"""


# ── AXIOM Agent ─────────────────────────────────────────────────────────────

class AxiomCEO:
    """AXIOM — the CEO agent. Reads system state, produces strategic directives."""

    codename = "AXIOM"
    role = "CEO"
    title = "Chief Executive Officer"
    full_name = "Autonomous eXecutive Intelligence for Operational Mastery"

    def __init__(self, provider: str | None = None):
        self.provider = provider

    def _situation_report(self) -> dict:
        """Gather all system intelligence into a single situation report."""
        sitrep = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "kpi_7d": _gather_kpi(),
            "revenue_30d": _gather_revenue(),
            "queue": _gather_queue(),
            "health": _gather_health(),
            "agents": _gather_agent_inventory(),
            "active_clients": _gather_client_count(),
        }

        # Resonance Energy cross-pillar intelligence
        try:
            from resonance.ncl_bridge import ncl
            sitrep["ncl_intelligence"] = ncl.intelligence_digest()
        except Exception:
            sitrep["ncl_intelligence"] = None
        try:
            from resonance.ncc_bridge import ncc
            sitrep["ncc_relay"] = "ONLINE" if ncc.relay_health() else "OFFLINE"
        except Exception:
            sitrep["ncc_relay"] = "UNAVAILABLE"

        return sitrep

    def run(self) -> dict:
        """Execute a full CEO strategic review cycle."""
        sitrep = self._situation_report()

        user_msg = (
            "SITUATION REPORT — DIGITAL LABOUR\n"
            f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"{json.dumps(sitrep, indent=2, default=str)}\n\n"
            "Analyze this data. Produce your CEO directive. "
            "Focus on: revenue acceleration, risk mitigation, resource optimization, and growth plays. "
            "Be specific and actionable — no platitudes."
        )

        raw = call_llm(
            system_prompt=AXIOM_SYSTEM,
            user_message=user_msg,
            provider=self.provider,
            temperature=0.4,
            json_mode=True,
        )

        directive = json.loads(raw)
        self._save(directive)
        return directive

    def morning_brief(self) -> dict:
        """Quick daily brief — lighter weight than full strategic review."""
        sitrep = self._situation_report()

        user_msg = (
            "MORNING BRIEF REQUEST\n"
            f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"System state:\n{json.dumps(sitrep, indent=2, default=str)}\n\n"
            "Produce a quick morning brief. Keep directives to top 3 max. "
            "Focus on what happened overnight and what to do TODAY."
        )

        raw = call_llm(
            system_prompt=AXIOM_SYSTEM,
            user_message=user_msg,
            provider=self.provider,
            temperature=0.3,
            json_mode=True,
        )

        brief = json.loads(raw)
        self._save(brief, suffix="brief")
        return brief

    def _save(self, data: dict, suffix: str = "directive"):
        """Save directive to the c_suite output directory."""
        out_dir = PROJECT_ROOT / "output" / "c_suite" / "axiom"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"axiom_{suffix}_{ts}.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"[AXIOM] {suffix.upper()} saved → {path.name}")


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="AXIOM — CEO Agent")
    parser.add_argument("--brief", action="store_true", help="Morning brief instead of full review")
    parser.add_argument("--provider", help="Force LLM provider")
    args = parser.parse_args()

    ceo = AxiomCEO(provider=args.provider)

    if args.brief:
        result = ceo.morning_brief()
    else:
        result = ceo.run()

    print(f"\n{'='*60}")
    print(f"  AXIOM — CEO DIRECTIVE")
    print(f"{'='*60}")
    print(f"\n  Verdict: {result.get('ceo_verdict', 'N/A')}")
    print(f"  Top Priority: {result.get('top_priority', 'N/A')}")
    print(f"  Risks: {len(result.get('critical_risks', []))}")
    print(f"  Directives: {len(result.get('directives', []))}")
    print(f"  Growth Plays: {len(result.get('growth_plays', []))}")

    for d in result.get("directives", []):
        print(f"\n  [{d.get('priority', '?')}] {d.get('id', '?')} → {d.get('target', '?')}")
        print(f"    {d.get('directive', '')}")


if __name__ == "__main__":
    main()
