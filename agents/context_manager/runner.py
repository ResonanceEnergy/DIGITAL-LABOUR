"""Context Manager Agent -- Supervisory agent for cross-agent context,
client tracking, and task enrichment.

Usage:
    python runner.py --action enrich --task-type sales_outreach --client "acme_corp"
    python runner.py --action query --client "acme_corp"
    python runner.py --action coordinate --task-type seo_content --client "acme_corp"
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

from utils.dl_agent import make_bridge
llm_call = make_bridge("context_manager", default_temperature=0.3)


# -- Data paths ---------------------------------------------------------------

DATA_DIR = PROJECT_ROOT / "data" / "context_manager"
CLIENT_DIR = DATA_DIR / "clients"
STATE_FILE = DATA_DIR / "active_state.json"
LOG_DIR = DATA_DIR / "logs"

for d in [DATA_DIR, CLIENT_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# -- Models -------------------------------------------------------------------

class ClientProfile(BaseModel):
    client_id: str
    preferences: dict = {}
    history_summary: str = ""
    active_jobs: list[str] = []
    agents_used: list[str] = []
    first_seen: str = ""
    last_seen: str = ""
    warnings: list[str] = []


class ContextEnrichment(BaseModel):
    enriched_inputs: dict = {}
    client_profile: ClientProfile | None = None
    coordination_notes: list[str] = []
    context_injections: list[str] = []
    deny: bool = False
    deny_reason: str = ""


class ActiveState(BaseModel):
    active_jobs: list[dict] = []
    queued_jobs: list[dict] = []
    last_updated: str = ""


# -- Prompt Loading -----------------------------------------------------------

AGENT_DIR = Path(__file__).parent


def load_prompt() -> str:
    path = AGENT_DIR / "system_prompt.md"
    return path.read_text(encoding="utf-8")


# -- Client Persistence -------------------------------------------------------

def load_client(client_id: str) -> ClientProfile | None:
    path = CLIENT_DIR / f"{client_id}.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return ClientProfile.model_validate(data)
    return None


def save_client(profile: ClientProfile) -> None:
    path = CLIENT_DIR / f"{profile.client_id}.json"
    path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")


def load_active_state() -> ActiveState:
    if STATE_FILE.exists():
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return ActiveState.model_validate(data)
    return ActiveState()


def save_active_state(state: ActiveState) -> None:
    state.last_updated = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(state.model_dump_json(indent=2), encoding="utf-8")


# -- Core Functions -----------------------------------------------------------

def enrich_task(task_type: str, client_id: str,
                inputs: dict, provider: str | None = None) -> ContextEnrichment:
    """Enrich a task with client context before worker agent execution."""
    profile = load_client(client_id)
    state = load_active_state()

    # Check for conflicts
    if profile:
        active_same_type = [
            j for j in state.active_jobs
            if j.get("client_id") == client_id
            and j.get("task_type") == task_type
        ]
        if active_same_type:
            return ContextEnrichment(
                enriched_inputs=inputs,
                client_profile=profile,
                deny=True,
                deny_reason=(
                    f"Client {client_id} already has active "
                    f"{task_type} job(s): "
                    f"{[j.get('job_id') for j in active_same_type]}"
                ),
            )

    # Build context for LLM enrichment
    prompt = load_prompt()
    user_msg = json.dumps({
        "action": "enrich",
        "task_type": task_type,
        "client_id": client_id,
        "inputs": inputs,
        "history": profile.model_dump() if profile else None,
        "active_state_summary": {
            "active_jobs": len(state.active_jobs),
            "queued_jobs": len(state.queued_jobs),
        },
    }, indent=2, default=str)

    raw = llm_call(prompt, user_msg, provider=provider,
                    temperature=0.3, json_mode=True)
    enrichment = ContextEnrichment.model_validate_json(raw)

    # Update client profile
    now = datetime.now(timezone.utc).isoformat()
    if not profile:
        profile = ClientProfile(
            client_id=client_id,
            first_seen=now,
            last_seen=now,
        )
    profile.last_seen = now
    if task_type not in profile.agents_used:
        profile.agents_used.append(task_type)
    enrichment.client_profile = profile
    save_client(profile)

    # Track active job
    job_entry = {
        "job_id": uuid4().hex[:8],
        "client_id": client_id,
        "task_type": task_type,
        "started": now,
    }
    state.active_jobs.append(job_entry)
    save_active_state(state)

    _log_action("enrich", client_id, task_type, enrichment)
    return enrichment


def query_client(client_id: str) -> ClientProfile | None:
    """Query a client's full context profile."""
    profile = load_client(client_id)
    if profile:
        _log_action("query", client_id, "N/A", {"found": True})
    return profile


def coordinate_agents(task_type: str, client_id: str,
                      provider: str | None = None) -> ContextEnrichment:
    """Check if other agents have relevant context for this task."""
    profile = load_client(client_id)
    if not profile or len(profile.agents_used) < 2:
        return ContextEnrichment(
            coordination_notes=[
                "No cross-agent coordination needed (single agent history)."
            ],
        )

    prompt = load_prompt()
    user_msg = json.dumps({
        "action": "coordinate",
        "task_type": task_type,
        "client_id": client_id,
        "agents_used_previously": profile.agents_used,
        "history": profile.model_dump(),
    }, indent=2, default=str)

    raw = llm_call(prompt, user_msg, provider=provider,
                    temperature=0.3, json_mode=True)
    enrichment = ContextEnrichment.model_validate_json(raw)
    _log_action("coordinate", client_id, task_type, enrichment)
    return enrichment


def complete_job(client_id: str, job_id: str) -> None:
    """Mark a job as completed in active state."""
    state = load_active_state()
    state.active_jobs = [
        j for j in state.active_jobs if j.get("job_id") != job_id
    ]
    save_active_state(state)
    _log_action("complete", client_id, "N/A", {"job_id": job_id})


def generate_report(provider: str | None = None) -> dict:
    """Generate a context status report."""
    state = load_active_state()
    client_files = list(CLIENT_DIR.glob("*.json"))
    clients = []
    for cf in client_files:
        data = json.loads(cf.read_text(encoding="utf-8"))
        clients.append({
            "client_id": data.get("client_id"),
            "agents_used": data.get("agents_used", []),
            "active_jobs": len([
                j for j in state.active_jobs
                if j.get("client_id") == data.get("client_id")
            ]),
            "last_seen": data.get("last_seen", ""),
        })

    return {
        "total_clients": len(clients),
        "active_jobs": len(state.active_jobs),
        "queued_jobs": len(state.queued_jobs),
        "clients": clients,
        "last_updated": state.last_updated,
    }


# -- Logging ------------------------------------------------------------------

def _log_action(action: str, client_id: str, task_type: str, data: object) -> None:
    log_file = LOG_DIR / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "client_id": client_id,
        "task_type": task_type,
        "data": data if isinstance(data, dict) else (
            data.model_dump() if hasattr(data, "model_dump") else str(data)
        ),
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


# -- Pipeline (for dispatcher integration) ------------------------------------

def run_pipeline(
    action: str = "enrich",
    task_type: str = "",
    client_id: str = "",
    inputs: dict | None = None,
    provider: str | None = None,
    **kwargs,
) -> ContextEnrichment | dict:
    """Main entry point for dispatcher routing."""
    if action == "enrich":
        return enrich_task(task_type, client_id, inputs or {}, provider)
    elif action == "query":
        profile = query_client(client_id)
        if profile:
            return ContextEnrichment(client_profile=profile)
        return ContextEnrichment(
            deny=True,
            deny_reason=f"No profile found for client {client_id}",
        )
    elif action == "coordinate":
        return coordinate_agents(task_type, client_id, provider)
    elif action == "report":
        return generate_report(provider)
    else:
        return ContextEnrichment(
            deny=True,
            deny_reason=f"Unknown action: {action}",
        )


# -- CLI -----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Context Manager -- Supervisory Agent"
    )
    parser.add_argument(
        "--action", required=True,
        choices=["enrich", "query", "coordinate", "report"],
    )
    parser.add_argument("--task-type", default="")
    parser.add_argument("--client", default="")
    parser.add_argument("--inputs", default="{}", help="JSON string of inputs")
    parser.add_argument(
        "--provider", default=None,
        choices=["openai", "anthropic", "gemini", "grok"],
    )
    args = parser.parse_args()

    inputs = json.loads(args.inputs)
    result = run_pipeline(
        action=args.action,
        task_type=args.task_type,
        client_id=args.client,
        inputs=inputs,
        provider=args.provider,
    )

    if isinstance(result, dict):
        print(json.dumps(result, indent=2, default=str))
    else:
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
