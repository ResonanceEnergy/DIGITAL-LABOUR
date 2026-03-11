"""Decision Logger — immutable audit trail for all autonomous actions.

Every decision NERVE makes gets logged here with context, reasoning, and outcome.
The human operator can review what the system did and why at any time.

Usage:
    from automation.decision_log import log_decision, get_decisions, get_escalations
"""

import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "data" / "nerve_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

DECISION_FILE = LOG_DIR / "decisions.jsonl"
ESCALATION_FILE = LOG_DIR / "escalations.jsonl"


def log_decision(
    actor: str,
    action: str,
    reasoning: str,
    outcome: str = "pending",
    severity: str = "INFO",
    data: dict | None = None,
):
    """Log an autonomous decision to the append-only audit trail."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "action": action,
        "reasoning": reasoning,
        "outcome": outcome,
        "severity": severity,
        "data": data or {},
    }
    with open(DECISION_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def log_escalation(
    source: str,
    issue: str,
    severity: str = "HIGH",
    recommended_action: str = "",
    data: dict | None = None,
):
    """Log an issue that needs human attention."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "issue": issue,
        "severity": severity,
        "recommended_action": recommended_action,
        "acknowledged": False,
        "data": data or {},
    }
    with open(ESCALATION_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"\n  *** ESCALATION [{severity}] {issue} ***")
    print(f"      Source: {source}")
    if recommended_action:
        print(f"      Recommended: {recommended_action}")
    return entry


def get_decisions(limit: int = 50) -> list[dict]:
    """Read recent decisions from the log."""
    if not DECISION_FILE.exists():
        return []
    lines = DECISION_FILE.read_text(encoding="utf-8").strip().split("\n")
    entries = [json.loads(line) for line in lines if line.strip()]
    return entries[-limit:]


def get_escalations(unacknowledged_only: bool = True) -> list[dict]:
    """Read escalations, optionally only unacknowledged ones."""
    if not ESCALATION_FILE.exists():
        return []
    lines = ESCALATION_FILE.read_text(encoding="utf-8").strip().split("\n")
    entries = [json.loads(line) for line in lines if line.strip()]
    if unacknowledged_only:
        entries = [e for e in entries if not e.get("acknowledged")]
    return entries


def decision_summary(hours: int = 24) -> dict:
    """Summarize decisions from the last N hours."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    decisions = get_decisions(limit=500)
    recent = [d for d in decisions if d["timestamp"] >= cutoff]

    by_actor = {}
    by_severity = {}
    for d in recent:
        by_actor[d["actor"]] = by_actor.get(d["actor"], 0) + 1
        by_severity[d["severity"]] = by_severity.get(d["severity"], 0) + 1

    return {
        "period_hours": hours,
        "total_decisions": len(recent),
        "by_actor": by_actor,
        "by_severity": by_severity,
        "escalations_pending": len(get_escalations(unacknowledged_only=True)),
    }
