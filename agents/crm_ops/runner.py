"""CRM Operations Agent — Clean, enrich, deduplicate, and manage CRM data.

2-step pipeline:
    1. Manager Agent — processes CRM data (clean/enrich/dedup/segment/audit)
    2. QA Agent — validates data integrity and processing accuracy

Usage:
    python -m agents.crm_ops.runner --file contacts.csv --task clean --crm hubspot
    python -m agents.crm_ops.runner --file deals.json --task pipeline_update
    python -m agents.crm_ops.runner --file crm_export.csv --task audit
    python -m agents.crm_ops.runner --text "..." --task deduplicate --crm salesforce
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.dl_agent import make_bridge  # noqa: E402
call_llm = make_bridge("crm_ops")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "crm_ops"


# ── Pydantic Models ────────────────────────────────────────────

class ContactUpdate(BaseModel):
    contact_id: str = ""
    field: str = ""
    old_value: str = ""
    new_value: str = ""
    action: str = ""


class StageUpdate(BaseModel):
    deal_id: str = ""
    deal_name: str = ""
    old_stage: str = ""
    new_stage: str = ""
    reason: str = ""


class StaleDeal(BaseModel):
    deal_id: str = ""
    deal_name: str = ""
    days_stale: int = 0
    last_activity: str = ""
    recommendation: str = ""


class DuplicateGroup(BaseModel):
    primary_id: str = ""
    duplicate_ids: list[str] = Field(default_factory=list)
    match_reason: str = ""
    merge_action: str = ""


class Segment(BaseModel):
    name: str = ""
    criteria: str = ""
    count: int = 0
    contact_ids: list[str] = Field(default_factory=list)


class DataHealth(BaseModel):
    completeness_score: float = 0.0
    fields_with_gaps: list[str] = Field(default_factory=list)
    stale_contacts: int = 0
    invalid_emails: int = 0
    missing_deal_owners: int = 0
    recommendations: list[str] = Field(default_factory=list)


class ContactsSummary(BaseModel):
    total: int = 0
    cleaned: int = 0
    merged: int = 0
    flagged: int = 0
    updates: list[ContactUpdate] = Field(default_factory=list)


class DealsSummary(BaseModel):
    total: int = 0
    stage_updates: list[StageUpdate] = Field(default_factory=list)
    stale_deals: list[StaleDeal] = Field(default_factory=list)


class CRMManagerOutput(BaseModel):
    task_type: str = ""
    crm_platform: str = ""
    records_processed: int = 0
    contacts: ContactsSummary = Field(default_factory=ContactsSummary)
    deals: DealsSummary = Field(default_factory=DealsSummary)
    duplicates: list[DuplicateGroup] = Field(default_factory=list)
    segments: list[Segment] = Field(default_factory=list)
    data_health: DataHealth = Field(default_factory=DataHealth)


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class CRMOpsOutput(BaseModel):
    managed: CRMManagerOutput = Field(default_factory=CRMManagerOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


# ── Agent Functions ─────────────────────────────────────────────

def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def manager_agent(
    crm_data: str,
    task_type: str = "clean",
    crm_platform: str = "hubspot",
    rules: str = "",
    provider: str = "openai",
) -> CRMManagerOutput:
    """Step 1: Process CRM data."""
    system = _load_prompt("manager_prompt")
    user_msg = (
        f"Task Type: {task_type}\n"
        f"CRM Platform: {crm_platform}\n"
        f"Rules: {rules or 'Standard CRM hygiene'}\n\n"
        f"CRM Data:\n{crm_data[:15000]}"
    )
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return CRMManagerOutput(**json.loads(raw))


def qa_agent(managed: CRMManagerOutput, provider: str = "openai") -> QAResult:
    """Step 2: Validate CRM processing accuracy."""
    system = _load_prompt("qa_prompt")
    user_msg = f"CRM output to validate:\n{json.dumps(managed.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return QAResult(**json.loads(raw))


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    crm_data: str,
    task_type: str = "clean",
    crm_platform: str = "hubspot",
    rules: str = "",
    provider: str = "openai",
    max_retries: int = 2,
) -> CRMOpsOutput:
    """Run the full CRM operations pipeline: Manage → QA."""
    print(f"\n[CRM_OPS] Starting pipeline — {task_type}")
    print(f"  CRM: {crm_platform} | Provider: {provider}")

    # Step 1: Process
    print("\n  [1/2] Processing CRM data...")
    managed = manager_agent(crm_data, task_type, crm_platform, rules, provider)
    print(f"  → {managed.records_processed} records processed")
    if managed.duplicates:
        print(f"  → {len(managed.duplicates)} duplicate groups found")
    if managed.deals.stale_deals:
        print(f"  → {len(managed.deals.stale_deals)} stale deals flagged")

    # Step 2: QA (with retries)
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(managed, provider)
        print(f"  → {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print(f"  → Reprocessing with revision notes...")
            managed = manager_agent(
                crm_data, task_type, crm_platform,
                rules + f"\n\nQA REVISION:\n{qa.revision_notes}", provider)

    output = CRMOpsOutput(
        managed=managed,
        qa=qa,
        meta={
            "task_type": task_type,
            "crm_platform": crm_platform,
            "provider": provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return output


def save_output(output: CRMOpsOutput) -> Path:
    """Save pipeline output to JSON file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"crm_{ts}_{run_id}.json"
    path.write_text(json.dumps(output.model_dump(), indent=2, default=str),
                    encoding="utf-8")
    print(f"\n  [SAVED] {path}")
    return path


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CRM Operations Agent")
    parser.add_argument("--text", default="", help="CRM data as text")
    parser.add_argument("--file", default="", help="File containing CRM data")
    parser.add_argument("--task", default="clean",
                        choices=["clean", "enrich", "deduplicate", "segment",
                                 "pipeline_update", "import_prep", "audit"])
    parser.add_argument("--crm", default="hubspot",
                        choices=["hubspot", "salesforce", "pipedrive", "zoho",
                                 "notion", "spreadsheet"])
    parser.add_argument("--provider", default="openai", help="LLM provider")
    args = parser.parse_args()

    if args.file:
        data = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        data = args.text
    else:
        print("Error: provide --text or --file")
        sys.exit(1)

    result = run_pipeline(
        crm_data=data,
        task_type=args.task,
        crm_platform=args.crm,
        provider=args.provider,
    )
    save_output(result)
