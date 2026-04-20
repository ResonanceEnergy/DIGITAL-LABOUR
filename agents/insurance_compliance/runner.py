"""Insurance Compliance Agent — Check insurance documents against regulatory frameworks.

2-step pipeline:
    1. Writer Agent — produces structured compliance audit of insurance documents
    2. QA Agent — validates the compliance audit for thoroughness and accuracy

Handles: HIPAA reviews, ERISA audits, ACA compliance checks, state regulation audits,
         CMS guideline reviews, rate analysis compliance.

Usage:
    python -m agents.insurance_compliance.runner --file policy_doc.txt --type hipaa_review
    python -m agents.insurance_compliance.runner --text "Claims process..." --type erisa_audit --jurisdiction ca_state
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
call_llm = make_bridge("insurance_compliance")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "insurance_compliance"


# -- Pydantic Models ────────────────────────────────────────────

class Violation(BaseModel):
    regulation_reference: str = ""
    description: str = ""
    severity: str = ""  # critical / major / minor
    remediation: str = ""
    regulatory_body: str = ""
    deadline: str = ""


class WriterOutput(BaseModel):
    compliance_type: str = ""
    jurisdiction: str = ""
    document_reviewed: str = ""
    violations: list[Violation] = Field(default_factory=list)
    compliance_score: int = 0
    regulatory_framework: str = ""
    hipaa_status: str = ""
    erisa_status: str = ""
    remediation_steps: list[str] = Field(default_factory=list)
    certification_status: str = ""
    full_markdown: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class InsuranceComplianceOutput(BaseModel):
    compliance: WriterOutput = Field(default_factory=WriterOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


# -- Agent Functions ─────────────────────────────────────────────

def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def writer_agent(
    document_content: str,
    compliance_type: str = "hipaa_review",
    jurisdiction: str = "us_federal",
    provider: str = "openai",
    revision_notes: str = "",
) -> WriterOutput:
    """Step 1: Generate the compliance audit of the insurance document."""
    system = _load_prompt("writer_prompt")
    user_msg = (
        f"Compliance Type: {compliance_type}\n"
        f"Jurisdiction: {jurisdiction}\n"
    )
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nDocument to Audit:\n{document_content}"

    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(WriterOutput, data, agent_name="insurance_compliance.writer")


def qa_agent(compliance: WriterOutput, provider: str = "openai") -> QAResult:
    """Step 2: Validate the compliance audit for thoroughness and accuracy."""
    system = _load_prompt("qa_prompt")
    user_msg = f"Compliance audit to validate:\n{json.dumps(compliance.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(QAResult, data, agent_name="insurance_compliance.qa")


# -- Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    document_content: str,
    compliance_type: str = "hipaa_review",
    jurisdiction: str = "us_federal",
    provider: str = "openai",
    max_retries: int = 2,
) -> InsuranceComplianceOutput:
    """Run the full insurance compliance pipeline: Writer -> QA."""
    print(f"\n[INSURANCE_COMPLIANCE] Starting pipeline -- {compliance_type}")
    print(f"  Jurisdiction: {jurisdiction} | Provider: {provider}")

    # Step 1: Generate compliance audit
    print("\n  [1/2] Generating compliance audit...")
    compliance = writer_agent(document_content, compliance_type, jurisdiction,
                              provider=provider)
    print(f"  -> Compliance type: {compliance.compliance_type}")
    print(f"  -> Violations found: {len(compliance.violations)}")
    critical = sum(1 for v in compliance.violations if v.severity == "critical")
    if critical:
        print(f"  -> Critical violations: {critical}")
    print(f"  -> Compliance score: {compliance.compliance_score}")

    # Step 2: QA (with retries)
    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(compliance, provider)
        print(f"  -> {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print("  -> Revising compliance audit...")
            compliance = writer_agent(
                document_content, compliance_type, jurisdiction,
                provider=provider, revision_notes=qa.revision_notes)

    return InsuranceComplianceOutput(
        compliance=compliance,
        qa=qa,
        meta={
            "compliance_type": compliance_type,
            "jurisdiction": jurisdiction,
            "provider": provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


def save_output(output: InsuranceComplianceOutput) -> Path:
    """Save pipeline output to JSON file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"insurance_compliance_{ts}_{run_id}.json"
    path.write_text(
        json.dumps(output.model_dump(), indent=2, default=str),
        encoding="utf-8")
    print(f"\n  [SAVED] {path}")
    return path


# -- CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Insurance Compliance Agent")
    parser.add_argument("--text", default="", help="Document content as text")
    parser.add_argument("--file", default="", help="File containing document to audit")
    parser.add_argument("--type", default="hipaa_review",
                        choices=["hipaa_review", "erisa_audit", "aca_compliance",
                                 "state_regulation_audit", "cms_guideline_review",
                                 "rate_analysis_compliance", "full_compliance_audit"],
                        dest="compliance_type")
    parser.add_argument("--jurisdiction", default="us_federal",
                        help="Jurisdiction (us_federal, state code, etc.)")
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
        document_content=data,
        compliance_type=args.compliance_type,
        jurisdiction=args.jurisdiction,
        provider=args.provider,
    )
    save_output(result)
