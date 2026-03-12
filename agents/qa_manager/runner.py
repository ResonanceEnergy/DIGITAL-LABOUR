"""QA Manager Agent -- Supervisory agent for quality assurance across
all 20 worker agents.

Usage:
    python runner.py --action verify --task-type sales_outreach --deliverable '{"key":"value"}'
    python runner.py --action audit --task-type seo_content
    python runner.py --action report
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv(PROJECT_ROOT / ".env")

from utils.llm_client import call_llm as llm_call


# -- Data paths ---------------------------------------------------------------

DATA_DIR = PROJECT_ROOT / "data" / "qa_manager"
METRICS_DIR = DATA_DIR / "metrics"
LOG_DIR = DATA_DIR / "logs"
BANNED_FILE = PROJECT_ROOT / "config" / "banned_phrases.txt"

for d in [DATA_DIR, METRICS_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# -- Models -------------------------------------------------------------------

class AgentHealth(BaseModel):
    agent_type: str = ""
    pass_rate_7d: float = 0.0
    total_checked_7d: int = 0
    common_failures: list[str] = []
    suspension_recommended: bool = False


class QAVerdict(BaseModel):
    verdict: str = Field(pattern=r"^(APPROVED|REJECTED|REVISION_REQUIRED)$")
    issues: list[str] = []
    revision_instructions: str = ""
    quality_score: int = 0
    banned_phrase_violations: list[str] = []
    systemic_flags: list[str] = []
    agent_health: AgentHealth | None = None
    escalations: list[str] = []


class QAMetricsEntry(BaseModel):
    ts: str
    task_type: str
    client_id: str = ""
    verdict: str
    quality_score: int
    issues: list[str] = []


# -- Prompt Loading -----------------------------------------------------------

AGENT_DIR = Path(__file__).parent


def load_prompt() -> str:
    path = AGENT_DIR / "system_prompt.md"
    return path.read_text(encoding="utf-8")


# -- Banned Phrases -----------------------------------------------------------

def load_banned_phrases() -> list[str]:
    if BANNED_FILE.exists():
        return [
            line.strip() for line in
            BANNED_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
    return []


def check_banned_phrases(text: str) -> list[str]:
    banned = load_banned_phrases()
    text_lower = text.lower()
    return [p for p in banned if p.lower() in text_lower]


# -- Metrics Persistence ------------------------------------------------------

def _metrics_file(task_type: str) -> Path:
    return METRICS_DIR / f"{task_type}.jsonl"


def record_metric(entry: QAMetricsEntry) -> None:
    path = _metrics_file(entry.task_type)
    with open(path, "a", encoding="utf-8") as f:
        f.write(entry.model_dump_json() + "\n")


def load_metrics(task_type: str, days: int = 7) -> list[QAMetricsEntry]:
    path = _metrics_file(task_type)
    if not path.exists():
        return []

    cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = QAMetricsEntry.model_validate_json(line)
        try:
            ts = datetime.fromisoformat(entry.ts).timestamp()
            if ts >= cutoff:
                entries.append(entry)
        except (ValueError, TypeError):
            entries.append(entry)
    return entries


def compute_agent_health(task_type: str) -> AgentHealth:
    entries = load_metrics(task_type, days=7)
    if not entries:
        return AgentHealth(agent_type=task_type)

    total = len(entries)
    passed = sum(1 for e in entries if e.verdict == "APPROVED")
    pass_rate = round(passed / total, 3) if total else 0.0

    # Common failures
    all_issues: dict[str, int] = {}
    for e in entries:
        for issue in e.issues:
            all_issues[issue] = all_issues.get(issue, 0) + 1
    common = sorted(all_issues.items(), key=lambda x: x[1], reverse=True)[:5]

    return AgentHealth(
        agent_type=task_type,
        pass_rate_7d=pass_rate,
        total_checked_7d=total,
        common_failures=[f"{k} ({v}x)" for k, v in common],
        suspension_recommended=pass_rate < 0.7 and total >= 3,
    )


# -- Core Functions -----------------------------------------------------------

def verify_deliverable(
    task_type: str,
    deliverable: dict,
    qa_result: dict | None = None,
    client_id: str = "",
    provider: str | None = None,
) -> QAVerdict:
    """Final QA pass on a deliverable."""
    # Check banned phrases first
    text_blob = json.dumps(deliverable, default=str)
    banned_hits = check_banned_phrases(text_blob)

    # Auto-reject if banned phrases found
    if banned_hits:
        verdict = QAVerdict(
            verdict="REJECTED",
            issues=[f"Banned phrase detected: '{p}'" for p in banned_hits],
            revision_instructions=(
                "Remove all banned phrases and regenerate. "
                f"Violations: {banned_hits}"
            ),
            quality_score=0,
            banned_phrase_violations=banned_hits,
        )
        _record_and_log(task_type, client_id, verdict)
        return verdict

    # LLM-based quality assessment
    prompt = load_prompt()
    user_msg = json.dumps({
        "action": "verify",
        "task_type": task_type,
        "deliverable": deliverable,
        "worker_qa_result": qa_result,
        "client_id": client_id,
    }, indent=2, default=str)

    raw = llm_call(prompt, user_msg, provider=provider,
                    temperature=0.2, json_mode=True)
    verdict = QAVerdict.model_validate_json(raw)

    # Enforce score thresholds
    if verdict.quality_score < 70:
        verdict.verdict = "REJECTED"
        verdict.revision_instructions = (
            "Score below 70 -- full re-run required, not revision. "
            + verdict.revision_instructions
        )
    elif verdict.quality_score < 85:
        verdict.verdict = "REVISION_REQUIRED"

    # Get agent health
    verdict.agent_health = compute_agent_health(task_type)

    # Check for systemic issues
    if (verdict.agent_health.pass_rate_7d < 0.7
            and verdict.agent_health.total_checked_7d >= 3):
        verdict.systemic_flags.append(
            f"Agent {task_type} pass rate critically low: "
            f"{verdict.agent_health.pass_rate_7d:.0%}"
        )
        verdict.escalations.append(
            f"ESCALATE to Production Manager: {task_type} "
            f"suspension recommended"
        )

    _record_and_log(task_type, client_id, verdict)
    return verdict


def audit_agent(task_type: str) -> AgentHealth:
    """Audit an agent type's QA history."""
    health = compute_agent_health(task_type)
    _log_action("audit", task_type, "", health.model_dump())
    return health


def generate_report(provider: str | None = None) -> dict:
    """Generate a system-wide QA report."""
    agent_types = [
        "sales_outreach", "support_ticket", "content_repurpose",
        "doc_extract", "lead_gen", "email_marketing", "seo_content",
        "social_media", "data_entry", "web_scraper", "crm_ops",
        "bookkeeping", "proposal_writer", "product_desc",
        "resume_writer", "ad_copy", "market_research",
        "business_plan", "press_release", "tech_docs",
    ]

    agent_reports = []
    total_checked = 0
    total_passed = 0

    for at in agent_types:
        health = compute_agent_health(at)
        if health.total_checked_7d > 0:
            agent_reports.append(health.model_dump())
            total_checked += health.total_checked_7d
            total_passed += int(
                health.pass_rate_7d * health.total_checked_7d
            )

    overall_pass_rate = (
        round(total_passed / total_checked, 3) if total_checked else 0.0
    )

    at_risk = [
        r for r in agent_reports if r.get("suspension_recommended")
    ]

    return {
        "report_date": datetime.now(timezone.utc).isoformat(),
        "total_checked_7d": total_checked,
        "overall_pass_rate_7d": overall_pass_rate,
        "agents_checked": len(agent_reports),
        "at_risk_agents": at_risk,
        "agent_details": agent_reports,
    }


# -- Logging ------------------------------------------------------------------

def _record_and_log(task_type: str, client_id: str,
                    verdict: QAVerdict) -> None:
    entry = QAMetricsEntry(
        ts=datetime.now(timezone.utc).isoformat(),
        task_type=task_type,
        client_id=client_id,
        verdict=verdict.verdict,
        quality_score=verdict.quality_score,
        issues=verdict.issues,
    )
    record_metric(entry)
    _log_action("verify", task_type, client_id, verdict.model_dump())


def _log_action(action: str, task_type: str, client_id: str,
                data: dict) -> None:
    log_file = LOG_DIR / (
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
    )
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "task_type": task_type,
        "client_id": client_id,
        "data": data,
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


# -- Pipeline (for dispatcher integration) ------------------------------------

def run_pipeline(
    action: str = "verify",
    task_type: str = "",
    deliverable: dict | None = None,
    qa_result: dict | None = None,
    client_id: str = "",
    provider: str | None = None,
    **kwargs,
) -> QAVerdict | dict:
    """Main entry point for dispatcher routing."""
    if action == "verify":
        return verify_deliverable(
            task_type, deliverable or {}, qa_result, client_id, provider
        )
    elif action == "audit":
        health = audit_agent(task_type)
        return QAVerdict(
            verdict="APPROVED",
            quality_score=int(health.pass_rate_7d * 100),
            agent_health=health,
        )
    elif action == "report":
        return generate_report(provider)
    else:
        return QAVerdict(
            verdict="REJECTED",
            issues=[f"Unknown action: {action}"],
            quality_score=0,
        )


# -- CLI -----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="QA Manager -- Supervisory Agent"
    )
    parser.add_argument(
        "--action", required=True,
        choices=["verify", "audit", "report"],
    )
    parser.add_argument("--task-type", default="")
    parser.add_argument("--client", default="")
    parser.add_argument(
        "--deliverable", default="{}",
        help="JSON string of deliverable to verify",
    )
    parser.add_argument("--qa-result", default=None)
    parser.add_argument(
        "--provider", default=None,
        choices=["openai", "anthropic", "gemini", "grok"],
    )
    args = parser.parse_args()

    deliverable = json.loads(args.deliverable)
    qa_result = json.loads(args.qa_result) if args.qa_result else None

    result = run_pipeline(
        action=args.action,
        task_type=args.task_type,
        deliverable=deliverable,
        qa_result=qa_result,
        client_id=args.client,
        provider=args.provider,
    )

    if isinstance(result, dict):
        print(json.dumps(result, indent=2, default=str))
    else:
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
