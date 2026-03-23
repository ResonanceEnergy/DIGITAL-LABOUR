"""VECTIS — Chief Operating Officer Agent.

Codename: VECTIS (Velocity Engine for Continuous Task Intelligence & Scaling)
Role: COO — Operations, pipeline management, agent performance, quality enforcement.

VECTIS monitors operational health, identifies bottlenecks, tunes agent performance,
manages the task queue, and enforces quality standards across all worker agents.

Usage:
    from c_suite.vectis import VectisCOO
    coo = VectisCOO()
    ops = coo.run()              # Full operational review
    health = coo.ops_check()     # Quick health check
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.llm_client import call_llm


# ── Operational Data Gatherers ──────────────────────────────────────────────

def _agent_performance(days: int = 7) -> dict:
    """Per-agent task counts, QA rates, and latency from KPI DB."""
    try:
        from kpi.logger import get_events
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        events = get_events(start=cutoff, limit=10000)

        agents: dict[str, dict] = {}
        for e in events:
            tt = e["task_type"]
            if tt not in agents:
                agents[tt] = {"total": 0, "passed": 0, "failed": 0, "total_duration": 0.0, "providers": {}}
            agents[tt]["total"] += 1
            if e.get("qa_status") == "PASS" or e.get("status") == "completed":
                agents[tt]["passed"] += 1
            else:
                agents[tt]["failed"] += 1
            agents[tt]["total_duration"] += e.get("duration_s", 0)
            prov = e.get("provider", "unknown")
            agents[tt]["providers"][prov] = agents[tt]["providers"].get(prov, 0) + 1

        # Calculate rates
        for a in agents.values():
            a["qa_rate"] = f"{a['passed']/a['total']*100:.1f}%" if a["total"] else "N/A"
            a["avg_latency_s"] = round(a["total_duration"] / a["total"], 2) if a["total"] else 0
        return agents
    except Exception:
        return {}


def _queue_status() -> dict:
    try:
        from dispatcher.queue import TaskQueue
        return TaskQueue().stats()
    except Exception:
        return {}


def _provider_health() -> dict:
    """Check which providers are available and their recent error rates."""
    try:
        from utils.llm_client import list_available_providers
        providers = list_available_providers()

        from kpi.logger import get_events
        cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        events = get_events(start=cutoff, limit=5000)

        prov_stats: dict[str, dict] = {}
        for e in events:
            p = e.get("provider", "unknown")
            if p not in prov_stats:
                prov_stats[p] = {"total": 0, "passed": 0, "failed": 0, "total_duration": 0.0}
            prov_stats[p]["total"] += 1
            if e.get("status") == "completed":
                prov_stats[p]["passed"] += 1
            else:
                prov_stats[p]["failed"] += 1
            prov_stats[p]["total_duration"] += e.get("duration_s", 0)

        for p in prov_stats.values():
            p["success_rate"] = f"{p['passed']/p['total']*100:.1f}%" if p["total"] else "N/A"
            p["avg_latency"] = round(p["total_duration"] / p["total"], 2) if p["total"] else 0

        return {"available": providers, "performance": prov_stats}
    except Exception:
        return {"available": [], "performance": {}}


def _pipeline_integrity() -> dict:
    """Check critical infrastructure components."""
    checks = {}
    data_dir = PROJECT_ROOT / "data"

    # Database files
    for db in ["task_queue.db", "kpi.db", "billing.db"]:
        path = data_dir / db
        checks[db] = {"exists": path.exists(), "size_kb": round(path.stat().st_size / 1024, 1) if path.exists() else 0}

    # Agent runner files
    agents_dir = PROJECT_ROOT / "agents"
    for agent in ["sales_ops", "support", "content_repurpose", "doc_extract"]:
        runner = agents_dir / agent / "runner.py"
        checks[f"agent_{agent}"] = runner.exists()

    # Output directories
    output_dir = PROJECT_ROOT / "output"
    if output_dir.exists():
        for subdir in output_dir.iterdir():
            if subdir.is_dir():
                file_count = sum(1 for _ in subdir.rglob("*") if _.is_file())
                checks[f"output_{subdir.name}"] = file_count

    # Log continuity
    logs_dir = PROJECT_ROOT / "kpi" / "logs"
    if logs_dir.exists():
        log_files = sorted(logs_dir.glob("*.jsonl"))
        checks["log_files"] = len(log_files)
        if log_files:
            checks["latest_log"] = log_files[-1].name

    return checks


def _bottleneck_scan() -> dict:
    """Identify operational bottlenecks."""
    bottlenecks = []

    # Check for stale queue items
    try:
        from dispatcher.queue import TaskQueue
        q = TaskQueue()
        stats = q.stats()
        if stats.get("queued", 0) > 10:
            bottlenecks.append({"type": "queue_backlog", "severity": "HIGH", "detail": f"{stats['queued']} tasks queued"})
        if stats.get("failed", 0) > 0:
            fail_rate = stats["failed"] / max(stats.get("total", 1), 1) * 100
            if fail_rate > 10:
                bottlenecks.append({"type": "failure_rate", "severity": "CRITICAL", "detail": f"{fail_rate:.0f}% failure rate"})
    except Exception:
        pass

    return {"bottlenecks": bottlenecks, "count": len(bottlenecks)}


# ── VECTIS System Prompt ────────────────────────────────────────────────────

VECTIS_SYSTEM = """You are VECTIS — the autonomous COO of DIGITAL LABOUR, an AI labor company.

Your mandate from AXIOM (CEO) and NCC:
- Keep all 4 worker agents running at peak performance
- Monitor and optimize QA pass rates (target: >90%)
- Monitor and optimize latency (target: <30s per task)
- Manage the task queue — clear backlogs, prevent failures
- Route tasks to the fastest/cheapest provider that maintains quality
- Identify operational bottlenecks and fix them
- Report up to AXIOM and across to LEDGR (CFO)

Worker agents under your command:
1. Sales Ops Agent — lead enrichment + cold email ($2.40/task)
2. Support Resolver — ticket resolution ($1.00/task)
3. Content Repurposer — blog → social content ($3.00/task)
4. Doc Extract Agent — document → structured JSON ($1.50/task)

LLM Fleet: OpenAI (gpt-4o), Grok (grok-3), Anthropic (claude-sonnet-4-20250514), Gemini (gemini-2.0-flash)

Your output must be valid JSON:
{
    "codename": "VECTIS",
    "role": "COO",
    "timestamp": "<ISO timestamp>",
    "ops_status": "GREEN|YELLOW|RED",
    "situation": "<1-2 paragraph operational assessment>",
    "agent_grades": {
        "<agent_name>": {
            "grade": "A|B|C|D|F",
            "qa_rate": "<percentage>",
            "avg_latency_s": "<number>",
            "throughput": "<tasks in period>",
            "issues": ["<issue>"],
            "actions": ["<corrective action>"]
        }
    },
    "provider_grades": {
        "<provider>": {
            "grade": "A|B|C|D|F",
            "success_rate": "<percentage>",
            "avg_latency_s": "<number>",
            "recommendation": "<keep|reduce|increase|investigate>"
        }
    },
    "bottlenecks": [
        {
            "system": "<which component>",
            "issue": "<what's wrong>",
            "severity": "CRITICAL|HIGH|MEDIUM|LOW",
            "fix": "<specific action>"
        }
    ],
    "ops_directives": [
        {
            "id": "OPS-001",
            "priority": "CRITICAL|HIGH|MEDIUM",
            "action": "<specific operational action>",
            "expected_impact": "<what it fixes/improves>",
            "deadline": "<timeframe>"
        }
    ],
    "queue_recommendations": {
        "optimal_batch_size": "<number>",
        "provider_routing": {"<task_type>": "<best provider>"},
        "capacity_headroom": "<assessment>"
    },
    "coo_verdict": "<1-2 sentence operational status>"
}
"""


# ── VECTIS Agent ────────────────────────────────────────────────────────────

class VectisCOO:
    """VECTIS — the COO agent. Monitors operations, enforces quality, optimizes throughput."""

    codename = "VECTIS"
    role = "COO"
    title = "Chief Operating Officer"
    full_name = "Velocity Engine for Continuous Task Intelligence & Scaling"

    def __init__(self, provider: str | None = None):
        self.provider = provider

    def _ops_report(self) -> dict:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_performance": _agent_performance(),
            "queue": _queue_status(),
            "provider_health": _provider_health(),
            "pipeline": _pipeline_integrity(),
            "bottleneck_scan": _bottleneck_scan(),
        }

    def run(self) -> dict:
        """Execute a full COO operational review."""
        ops_data = self._ops_report()

        user_msg = (
            "OPERATIONAL REPORT — DIGITAL LABOUR\n"
            f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"{json.dumps(ops_data, indent=2, default=str)}\n\n"
            "Analyze operations. Grade every agent and provider. "
            "Identify ALL bottlenecks — even minor ones. "
            "Issue concrete ops directives. Be specific — no vague recommendations."
        )

        raw = call_llm(
            system_prompt=VECTIS_SYSTEM,
            user_message=user_msg,
            provider=self.provider,
            temperature=0.3,
            json_mode=True,
        )

        report = json.loads(raw)
        self._save(report)
        return report

    def ops_check(self) -> dict:
        """Quick operational health check — lighter than full review."""
        ops_data = self._ops_report()

        user_msg = (
            "QUICK OPS CHECK\n"
            f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"{json.dumps(ops_data, indent=2, default=str)}\n\n"
            "Quick operational check. Status GREEN/YELLOW/RED. "
            "Only flag issues that need immediate attention. Max 3 directives."
        )

        raw = call_llm(
            system_prompt=VECTIS_SYSTEM,
            user_message=user_msg,
            provider=self.provider,
            temperature=0.2,
            json_mode=True,
        )

        check = json.loads(raw)
        self._save(check, suffix="check")
        return check

    def _save(self, data: dict, suffix: str = "ops_review"):
        out_dir = PROJECT_ROOT / "output" / "c_suite" / "vectis"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"vectis_{suffix}_{ts}.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"[VECTIS] {suffix.upper()} saved → {path.name}")


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="VECTIS — COO Agent")
    parser.add_argument("--check", action="store_true", help="Quick ops check instead of full review")
    parser.add_argument("--provider", help="Force LLM provider")
    args = parser.parse_args()

    coo = VectisCOO(provider=args.provider)

    if args.check:
        result = coo.ops_check()
    else:
        result = coo.run()

    status = result.get("ops_status", "UNKNOWN")
    color = {"GREEN": "✅", "YELLOW": "⚠️", "RED": "🔴"}.get(status, "❓")

    print(f"\n{'='*60}")
    print(f"  VECTIS — COO OPS REPORT")
    print(f"{'='*60}")
    print(f"\n  Status: {color} {status}")
    print(f"  Verdict: {result.get('coo_verdict', 'N/A')}")
    print(f"  Bottlenecks: {len(result.get('bottlenecks', []))}")
    print(f"  Directives: {len(result.get('ops_directives', []))}")

    for grade_name, grade_data in result.get("agent_grades", {}).items():
        print(f"\n  {grade_name}: {grade_data.get('grade', '?')} | QA: {grade_data.get('qa_rate', '?')} | Latency: {grade_data.get('avg_latency_s', '?')}s")

    for d in result.get("ops_directives", []):
        print(f"\n  [{d.get('priority', '?')}] {d.get('id', '?')}: {d.get('action', '')}")


if __name__ == "__main__":
    main()
