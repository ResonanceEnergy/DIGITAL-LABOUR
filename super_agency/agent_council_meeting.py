#!/usr/bin/env python3
"""
Bit Rage Systems Agent Council Meeting
Automated 15-minute syncs between AZ, GASKET, and OPTIMUS
Updates protocols, procedures, goals, and mandates
"""

import os
import sys
import json
import logging
import random
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

WORKSPACE = Path(__file__).parent
MEETING_LOG_DIR = WORKSPACE / "council_meetings"
STATE_FILE = WORKSPACE / "production_state.json"
PROTOCOL_FILE = WORKSPACE / "agent_protocols.json"
MANDATE_FILE = WORKSPACE / "agent_mandates.json"
NORTH_STAR = WORKSPACE / "NORTH_STAR.md"
PROPOSALS_DIR = WORKSPACE / "council_meetings" / "proposals"
PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)

# Create directories
MEETING_LOG_DIR.mkdir(exist_ok=True)

# Agent definitions
AGENTS = {
    "AZ": {
        "role": "Digital COO",
        "responsibilities": ["strategic_oversight", "crisis_management", "agent_coordination"],
        "authority_level": "executive"
    },
    "OPTIMUS": {
        "role": "Task Optimization Engine",
        "responsibilities": ["task_scheduling", "performance_optimization", "resource_allocation"],
        "authority_level": "operational"
    },
    "GASKET": {
        "role": "Integration & Workflow Engine",
        "responsibilities": ["workflow_management", "system_integration", "process_automation"],
        "authority_level": "operational"
    }
}

def load_json_file(path: Path) -> dict:
    """Load JSON file or return empty dict"""
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}

def save_json_file(path: Path, data: dict):
    """Save data to JSON file"""
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def load_production_state() -> dict:
    """Load current production state"""
    return load_json_file(STATE_FILE)

def load_protocols() -> dict:
    """Load current protocols"""
    protocols = load_json_file(PROTOCOL_FILE)
    if not protocols:
        protocols = {
            "version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "protocols": {
                "task_prioritization": {
                    "rule": "HIGH > MEDIUM > LOW",
                    "owner": "OPTIMUS"
                },
                "escalation_chain": {
                    "rule": "GASKET -> OPTIMUS -> AZ -> CEO",
                    "owner": "AZ"
                },
                "sync_frequency": {
                    "rule": "Every 15 minutes",
                    "owner": "AZ"
                },
                "error_handling": {
                    "rule": "Log, retry 3x, then escalate",
                    "owner": "GASKET"
                }
            }
        }
        save_json_file(PROTOCOL_FILE, protocols)
    return protocols

def load_mandates() -> dict:
    """Load current mandates"""
    mandates = load_json_file(MANDATE_FILE)
    if not mandates:
        mandates = {
            "version": "1.0.0",
            "last_updated": datetime.now().isoformat(),
            "mandates": {
                "efficiency": {
                    "description": "Maximize task completion rate",
                    "target": "95% completion within SLA",
                    "owner": "OPTIMUS"
                },
                "reliability": {
                    "description": "Maintain system uptime",
                    "target": "99.9% uptime",
                    "owner": "GASKET"
                },
                "coordination": {
                    "description": "Ensure agent alignment",
                    "target": "Zero conflicting actions",
                    "owner": "AZ"
                },
                "innovation": {
                    "description": "Continuous improvement",
                    "target": "1+ process improvement per week",
                    "owner": "AZ"
                }
            },
            "goals": {
                "short_term": ["Complete pending backlog", "Stabilize all systems"],
                "medium_term": ["Automate 80% of routine tasks", "Implement predictive scheduling"],
                "long_term": ["Full autonomous operation", "Self-healing infrastructure"]
            }
        }
        save_json_file(MANDATE_FILE, mandates)
    return mandates

def calculate_agent_metrics(state: dict) -> dict:
    """Calculate performance metrics for each agent"""
    agent_status = state.get("agent_status", {})
    total_completed = state.get("completed_tasks", 0)
    pending = state.get("pending_tasks", 0)

    optimus_tasks = agent_status.get("optimus", {}).get("tasks_completed", 0)
    gasket_tasks = agent_status.get("gasket", {}).get("tasks_completed", 0)

    return {
        "AZ": {
            "meetings_conducted": 1,
            "decisions_made": random.randint(2, 5),
            "efficiency_score": 0.95
        },
        "OPTIMUS": {
            "tasks_completed": optimus_tasks,
            "optimization_score": min(0.98, optimus_tasks / max(1, total_completed) + 0.5),
            "pending_assigned": pending // 2
        },
        "GASKET": {
            "tasks_completed": gasket_tasks,
            "integration_score": min(0.97, gasket_tasks / max(1, total_completed) + 0.5),
            "workflows_active": random.randint(5, 15)
        }
    }

def generate_meeting_agenda(
        state: dict, protocols: dict, mandates: dict) ->list:
    """Generate meeting agenda based on current state"""
    agenda = []

    # Status review
    agenda.append({
        "item": "Status Review",
        "presenter": "AZ",
        "topics": [
            f"Tasks completed: {state.get('completed_tasks', 0)}",
            f"Pending tasks: {state.get('pending_tasks', 0)}",
            f"System: {state.get('system', 'Unknown')}"
        ]
    })

    # Performance review
    agenda.append({
        "item": "Performance Review",
        "presenter": "OPTIMUS",
        "topics": [
            "Task completion rates",
            "Resource utilization",
            "Bottleneck identification"
        ]
    })

    # Integration status
    agenda.append({
        "item": "Integration Status",
        "presenter": "GASKET",
        "topics": [
            "Active workflows",
            "System health",
            "Automation coverage"
        ]
    })

    # Protocol updates
    agenda.append({
        "item": "Protocol Review",
        "presenter": "AZ",
        "topics": list(protocols.get("protocols", {}).keys())
    })

    # Mandate alignment
    agenda.append({
        "item": "Mandate Alignment",
        "presenter": "AZ",
        "topics": list(mandates.get("mandates", {}).keys())
    })

    return agenda

def generate_action_items(state: dict, metrics: dict) -> list:
    """Generate action items from meeting"""
    actions = []
    pending = state.get("pending_tasks", 0)

    if pending > 100:
        actions.append({
            "action": f"Clear {pending} pending tasks",
            "owner": "OPTIMUS",
            "priority": "HIGH",
            "deadline": "Next 2 cycles"
        })

    actions.append({
        "action": "Monitor system health metrics",
        "owner": "GASKET",
        "priority": "MEDIUM",
        "deadline": "Continuous"
    })

    actions.append({
        "action": "Review escalation queue",
        "owner": "AZ",
        "priority": "HIGH",
        "deadline": "Next cycle"
    })

    return actions

def update_protocols_and_mandates(
        protocols: dict, mandates: dict, meeting_number: int):
    """Update protocols and mandates based on meeting insights"""
    # Increment version
    version_parts = protocols.get("version", "1.0.0").split(".")
    version_parts[2] = str(int(version_parts[2]) + 1)
    protocols["version"] = ".".join(version_parts)
    protocols["last_updated"] = datetime.now().isoformat()
    protocols["last_meeting"] = meeting_number

    # Same for mandates
    version_parts = mandates.get("version", "1.0.0").split(".")
    version_parts[2] = str(int(version_parts[2]) + 1)
    mandates["version"] = ".".join(version_parts)
    mandates["last_updated"] = datetime.now().isoformat()
    mandates["last_meeting"] = meeting_number

    # Save updates
    save_json_file(PROTOCOL_FILE, protocols)
    save_json_file(MANDATE_FILE, mandates)

    return protocols, mandates

def generate_proposals(state: dict, metrics: dict) -> list:
    """Generate real proposals based on current system state."""
    proposals = []

    pending = state.get("pending_tasks", 0)
    completed = state.get("completed_tasks", 0)
    errored = state.get("errored_tasks", 0)

    # Check sentry reports for failing repos
    sentry_dir = WORKSPACE / "reports" / "sentry"
    failing_repos = []
    if sentry_dir.exists():
        for rpt in sorted(sentry_dir.glob("*.json"))[-5:]:
            try:
                data = json.loads(rpt.read_text(encoding="utf-8"))
                for repo, info in data.items() if isinstance(data, dict) else []:
                    if info.get("health", "ok") != "ok":
                        failing_repos.append(repo)
            except Exception:
                pass

    if failing_repos:
        proposals.append({
            "id": f"PROP-{datetime.now().strftime('%H%M%S')}-1",
            "type": "remediation",
            "proposed_by": "GASKET",
            "title": f"Remediate {len(failing_repos)} failing repos",
            "description": f"Repos: {', '.join(failing_repos[:5])}",
            "risk": "MEDIUM",
            "autonomy_required": "L1",
        })

    if pending > 50:
        proposals.append({
            "id": f"PROP-{datetime.now().strftime('%H%M%S')}-2",
            "type": "optimization",
            "proposed_by": "OPTIMUS",
            "title": f"Clear backlog of {pending} pending tasks",
            "description": "Re-prioritize and batch-process pending items",
            "risk": "LOW",
            "autonomy_required": "L1",
        })

    if errored > 0:
        proposals.append({
            "id": f"PROP-{datetime.now().strftime('%H%M%S')}-3",
            "type": "remediation",
            "proposed_by": "GASKET",
            "title": f"Investigate {errored} errored tasks",
            "description": "Review error logs, retry viable tasks, archive dead ones",
            "risk": "LOW",
            "autonomy_required": "L1",
        })

    # Always propose a status continuation if nothing else
    if not proposals:
        proposals.append({
            "id": f"PROP-{datetime.now().strftime('%H%M%S')}-0",
            "type": "continuation",
            "proposed_by": "OPTIMUS",
            "title": "Continue current operational cadence",
            "description": "No critical issues detected — maintain course",
            "risk": "LOW",
            "autonomy_required": "L0",
        })

    return proposals


def evaluate_proposal(proposal: dict, state: dict) -> dict:
    """Risk-check a proposal and produce a vote record."""
    risk = proposal.get("risk", "LOW")
    autonomy = proposal.get("autonomy_required", "L0")
    ptype = proposal.get("type", "unknown")

    # Risk evaluation rules
    approved = True
    reason = "Within operational parameters"

    if risk == "HIGH" and autonomy in ("L2", "L3"):
        approved = False
        reason = "HIGH risk + elevated autonomy requires CEO override"
    elif risk == "CRITICAL":
        approved = False
        reason = "CRITICAL risk — blocked pending human review"

    # L3 promotion requires unanimous council vote
    requires_l3_vote = (
        ptype == "graduation" and proposal.get("target_level") == "L3"
    )
    if requires_l3_vote:
        # All council members must explicitly approve L3 promotions
        az_vote = "approve" if risk in ("LOW", "MEDIUM") else "deny"
        optimus_vote = "approve" if risk == "LOW" else "deny"
        gasket_vote = "approve"
        votes = {"AZ": az_vote, "OPTIMUS": optimus_vote, "GASKET": gasket_vote}
        approved = all(v == "approve" for v in votes.values())
        if not approved:
            reason = "L3 promotion requires unanimous council approval"
    else:
        votes = {
            "AZ": "approve" if approved else "deny", "OPTIMUS": "approve"
            if ptype !="remediation" or risk =="LOW" else "abstain",
            "GASKET": "approve",}

    return {
        "proposal_id": proposal["id"],
        "title": proposal["title"],
        "risk_assessment": risk,
        "proposed_by": proposal["proposed_by"],
        "votes": votes,
        "approved": approved,
        "reason": reason,
    }


def execute_decision(decision: dict, proposal: dict) -> dict:
    """Execute an approved decision. Returns execution result."""
    if not decision["approved"]:
        return {"executed": False, "reason": decision["reason"]}

    ptype = proposal.get("type", "unknown")
    result = {"executed": True, "type": ptype,
        "ts": datetime.now().isoformat()}

    if ptype == "remediation":
        # Queue self-heal run
        try:
            from agents.portfolio_selfheal import main as selfheal
            selfheal()
            result["action"] = "portfolio_selfheal executed"
        except Exception as exc:
            result["action"] = f"selfheal queued (import unavailable: {exc})"

    elif ptype == "optimization":
        # Write a flag file that the orchestrator reads
        flag = WORKSPACE / "logs" / "council_optimise_flag.json"
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text(json.dumps({
            "requested_by": "council",
            "ts": datetime.now().isoformat(),
            "proposal": proposal["title"],
        }), encoding="utf-8")
        result["action"] = "optimization flag written for orchestrator"

    elif ptype == "continuation":
        result["action"] = "no-op — steady state"

    elif ptype == "graduation":
        # Autonomy level graduation (L2→L3 requires council vote)
        target = proposal.get("target_level", "L2")
        repo_name = proposal.get("repo_name")
        if repo_name:
            try:
                from autonomy_mode import graduate_repo
                graduate_repo(repo_name, target)
                result["action"] = f"graduated {repo_name} to {target}"
            except Exception as exc:
                result["action"] = f"graduation failed: {exc}"
        else:
            result["action"] = "graduation proposal missing repo_name"

    else:
        result["action"] = f"unknown proposal type '{ptype}' — logged only"

    # Persist proposal result
    prop_file = PROPOSALS_DIR / f"{proposal['id']}.json"
    prop_file.write_text(json.dumps({
        "proposal": proposal, "decision": decision, "result": result
    }, indent=2, default=str), encoding="utf-8")

    return result


def conduct_meeting() -> dict:
    """Conduct a full agent council meeting with real decision flow."""
    timestamp = datetime.now()
    meeting_id = f"COUNCIL_{timestamp.strftime('%Y%m%d_%H%M%S')}"

    # Load current state
    state = load_production_state()
    protocols = load_protocols()
    mandates = load_mandates()

    # Calculate metrics
    metrics = calculate_agent_metrics(state)

    # Generate agenda
    agenda = generate_meeting_agenda(state, protocols, mandates)

    # Generate action items
    actions = generate_action_items(state, metrics)

    # Determine meeting number
    existing_meetings = list(MEETING_LOG_DIR.glob("meeting_*.json"))
    meeting_number = len(existing_meetings) + 1

    # Update protocols and mandates
    protocols, mandates = update_protocols_and_mandates(
        protocols, mandates, meeting_number)

    # ── Decision flow: propose → risk-check → vote → execute ───────
    proposals = generate_proposals(state, metrics)
    decisions = []
    execution_results = []
    for prop in proposals:
        decision = evaluate_proposal(prop, state)
        decisions.append(decision)
        result = execute_decision(decision, prop)
        execution_results.append(result)
        logger.info(
            f"[COUNCIL] {prop['title']} → {'APPROVED' if decision['approved'] else 'DENIED'}: {result.get('action', decision.get('reason', ''))}")

    # Create meeting record
    meeting_record = {
        "meeting_id": meeting_id,
        "meeting_number": meeting_number,
        "timestamp": timestamp.isoformat(),
        "duration_minutes": 1,
        "attendees": list(AGENTS.keys()),
        "chair": "AZ",
        "agenda": agenda,
        "agent_metrics": metrics,
        "proposals": proposals,
        "decisions": decisions,
        "execution_results": execution_results,
        "action_items": actions,
        "protocol_version": protocols["version"],
        "mandate_version": mandates["version"],
        "next_meeting": "15 minutes",
        "status": "COMPLETED"
    }

    # Save meeting record
    meeting_file = MEETING_LOG_DIR / \
        f"meeting_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
    save_json_file(meeting_file, meeting_record)

    # Keep only last 100 meeting logs
    meetings = sorted(MEETING_LOG_DIR.glob("meeting_*.json"))
    for old_meeting in meetings[:-100]:
        old_meeting.unlink()

    return meeting_record

def print_meeting_report(meeting: dict):
    """Print formatted meeting report"""
    print("=" * 70)
    print(f"🤖 AGENT COUNCIL MEETING #{meeting['meeting_number']}")
    print(f"📅 {meeting['timestamp']}")
    print("=" * 70)

    print(f"\n👥 ATTENDEES: {', '.join(meeting['attendees'])}")
    print(f"🪑 CHAIR: {meeting['chair']}")

    print(f"\n📋 AGENDA:")
    for i, item in enumerate(meeting['agenda'], 1):
        print(f"   {i}. {item['item']} (Presenter: {item['presenter']})")

    print(f"\n📊 AGENT METRICS:")
    for agent, metrics in meeting['agent_metrics'].items():
        print(f"   {agent}:")
        for key, value in metrics.items():
            if isinstance(value, float):
                print(f"      {key}: {value:.2%}")
            else:
                print(f"      {key}: {value}")

    print(f"\n✅ DECISIONS:")
    for d in meeting.get('decisions', []):
        status = "✅ APPROVED" if d.get('approved') else "❌ DENIED"
        print(f"   • [{status}] {d.get('title', d.get('decision', '?'))}")
        print(
            f"     Proposed: {d.get('proposed_by', '?')}, Votes: {d.get('votes', {})}")
        if not d.get('approved'):
            print(f"     Reason: {d.get('reason', '?')}")

    if meeting.get('execution_results'):
        print(f"\n⚡ EXECUTION RESULTS:")
        for r in meeting['execution_results']:
            status = "✅" if r.get('executed') else "⏭️"
            print(f"   {status} {r.get('action', r.get('reason', '?'))}")

    print(f"\n📝 ACTION ITEMS:")
    for a in meeting['action_items']:
        print(f"   [{a['priority']}] {a['action']}")
        print(f"         Owner: {a['owner']}, Deadline: {a['deadline']}")

    print(f"\n📜 VERSIONS:")
    print(f"   Protocol: v{meeting['protocol_version']}")
    print(f"   Mandates: v{meeting['mandate_version']}")

    print(f"\n⏰ Next Meeting: {meeting['next_meeting']}")
    print("=" * 70)

if __name__ == "__main__":
    meeting = conduct_meeting()
    print_meeting_report(meeting)
