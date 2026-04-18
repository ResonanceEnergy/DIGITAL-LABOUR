"""Insurance Appeals Agent — Appeal letters, prior auth narratives, denial responses.

2-step pipeline:
    1. Writer Agent — produces appeal letter with clinical justification
    2. QA Agent — validates completeness, regulatory citations, HIPAA compliance

Handles: prior authorization, first/second level appeals, external review,
         peer-to-peer preparation.

Usage:
    python -m agents.insurance_appeals.runner --text "Patient denied coverage..." --type first_level_appeal
    python -m agents.insurance_appeals.runner --file denial_letter.txt --type prior_auth --urgency urgent
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.dl_agent import make_bridge, safe_validate  # noqa: E402
call_llm = make_bridge("insurance_appeals")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "insurance_appeals"


# ── Pydantic Models ────────────────────────────────────────────

class PatientInfo(BaseModel):
    initials: str = ""
    age_range: str = ""
    policy_type: str = ""  # commercial / medicare / medicaid


class DenialDetails(BaseModel):
    denial_date: str = ""
    denial_reason: str = ""
    denial_code: str = ""
    service_denied: str = ""
    original_claim_amount: str = ""


class ClinicalJustification(BaseModel):
    diagnosis: str = ""
    icd10_codes: list[str] = Field(default_factory=list)
    medical_necessity_rationale: str = ""
    treatment_history: str = ""
    alternative_treatments_tried: str = ""
    provider_recommendation: str = ""
    supporting_evidence: list[str] = Field(default_factory=list)


class AppealArguments(BaseModel):
    regulatory_basis: list[str] = Field(default_factory=list)
    plan_language_citations: list[str] = Field(default_factory=list)
    clinical_guidelines_cited: list[str] = Field(default_factory=list)
    precedent_notes: str = ""


class WriterOutput(BaseModel):
    letter_type: str = ""  # prior_auth / first_level_appeal / second_level_appeal / external_review / peer_to_peer_prep
    patient_info: PatientInfo = Field(default_factory=PatientInfo)
    denial_details: DenialDetails = Field(default_factory=DenialDetails)
    clinical_justification: ClinicalJustification = Field(
        default_factory=ClinicalJustification)
    appeal_arguments: AppealArguments = Field(default_factory=AppealArguments)
    letter_body: str = ""
    urgency_level: str = ""  # routine / urgent / expedited
    deadline_date: str = ""
    recommended_attachments: list[str] = Field(default_factory=list)
    full_markdown: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class AppealOutput(BaseModel):
    appeal: WriterOutput = Field(default_factory=WriterOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


# ── Agent Functions ─────────────────────────────────────────────

def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def writer_agent(case_text: str, letter_type: str = "first_level_appeal",
                 urgency: str = "routine", provider_name: str = "",
                 revision_notes: str = "",
                 provider: str = "openai") -> WriterOutput:
    """Step 1: Draft the appeal letter."""
    system = _load_prompt("writer_prompt")
    user_msg = (
        f"Letter Type: {letter_type}\n"
        f"Urgency: {urgency}\n"
        f"Requesting Provider: {provider_name or 'Extract from case details'}\n"
    )
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nCase Details:\n{case_text}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(WriterOutput, data, agent_name="insurance_appeals.writer")


def qa_agent(appeal: WriterOutput, provider: str = "openai") -> QAResult:
    """Step 2: Validate appeal letter quality and compliance."""
    system = _load_prompt("qa_prompt")
    user_msg = f"Appeal letter to validate:\n{json.dumps(appeal.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(QAResult, data, agent_name="insurance_appeals.qa")


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(case_text: str, letter_type: str = "first_level_appeal",
                 urgency: str = "routine", provider_name: str = "",
                 provider: str = "openai",
                 max_retries: int = 2) -> AppealOutput:
    """Run the full insurance appeals pipeline: Writer -> QA."""
    print(f"\n[INSURANCE_APPEALS] Starting pipeline — {letter_type}")
    print(f"  Urgency: {urgency} | Provider: {provider}")

    # Step 1: Draft appeal
    print("\n  [1/2] Drafting appeal letter...")
    appeal = writer_agent(case_text, letter_type, urgency, provider_name,
                          provider=provider)
    print(f"  → Type: {appeal.letter_type}")
    print(f"  → Urgency: {appeal.urgency_level}")
    print(f"  → ICD-10 codes: {len(appeal.clinical_justification.icd10_codes)}")

    # Step 2: QA (with retries)
    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(appeal, provider)
        print(f"  → {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print("  → Revising appeal letter...")
            appeal = writer_agent(case_text, letter_type, urgency,
                                  provider_name, qa.revision_notes, provider)

    return AppealOutput(
        appeal=appeal, qa=qa,
        meta={"letter_type": letter_type, "urgency": urgency,
              "provider": provider,
              "timestamp": datetime.now(timezone.utc).isoformat()},
    )


def save_output(output: AppealOutput) -> Path:
    """Save pipeline output to JSON file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"appeal_{ts}_{run_id}.json"
    path.write_text(json.dumps(output.model_dump(), indent=2, default=str),
                    encoding="utf-8")
    print(f"\n  [SAVED] {path}")
    return path


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Insurance Appeals Agent")
    parser.add_argument("--text", default="")
    parser.add_argument("--file", default="")
    parser.add_argument("--type", default="first_level_appeal",
                        choices=["prior_auth", "first_level_appeal",
                                 "second_level_appeal", "external_review",
                                 "peer_to_peer_prep"],
                        dest="letter_type")
    parser.add_argument("--urgency", default="routine",
                        choices=["routine", "urgent", "expedited"])
    parser.add_argument("--provider", default="openai")
    args = parser.parse_args()

    if args.file:
        data = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        data = args.text
    else:
        print("Error: provide --text or --file"); sys.exit(1)

    result = run_pipeline(data, args.letter_type, args.urgency,
                          provider=args.provider)
    save_output(result)
