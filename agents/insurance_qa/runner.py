"""Insurance QA Agent — Review insurance documents for quality, accuracy, and regulatory compliance.

2-step pipeline:
    1. Writer Agent — produces structured quality review of insurance documents
    2. QA Agent — validates the review itself for completeness and accuracy

Handles: appeal reviews, prior auth reviews, denial response reviews, policy reviews,
         coverage analysis reviews, claims report reviews.

Usage:
    python -m agents.insurance_qa.runner --file appeal_letter.txt --type appeal_review
    python -m agents.insurance_qa.runner --text "Prior auth for..." --type prior_auth_review --provider anthropic
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
call_llm = make_bridge("insurance_qa")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "insurance_qa"


# -- Pydantic Models ────────────────────────────────────────────

class Finding(BaseModel):
    category: str = ""  # clinical / regulatory / procedural / formatting
    severity: str = ""  # critical / major / minor
    description: str = ""
    recommendation: str = ""
    regulation_reference: str = ""


class WriterOutput(BaseModel):
    review_type: str = ""
    document_reviewed: str = ""
    findings: list[Finding] = Field(default_factory=list)
    regulatory_compliance: str = ""
    hipaa_compliance: str = ""
    medical_accuracy: str = ""
    overall_assessment: str = ""
    recommendations: list[str] = Field(default_factory=list)
    full_markdown: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class InsuranceQAOutput(BaseModel):
    review: WriterOutput = Field(default_factory=WriterOutput)
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
    review_type: str = "appeal_review",
    provider: str = "openai",
    revision_notes: str = "",
) -> WriterOutput:
    """Step 1: Generate the quality review of the insurance document."""
    system = _load_prompt("writer_prompt")
    user_msg = (
        f"Review Type: {review_type}\n"
    )
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nDocument to Review:\n{document_content}"

    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(WriterOutput, data, agent_name="insurance_qa.writer")


def qa_agent(review: WriterOutput, provider: str = "openai") -> QAResult:
    """Step 2: Validate the quality review for completeness and accuracy."""
    system = _load_prompt("qa_prompt")
    user_msg = f"Insurance QA review to validate:\n{json.dumps(review.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(QAResult, data, agent_name="insurance_qa.qa")


# -- Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    document_content: str,
    review_type: str = "appeal_review",
    provider: str = "openai",
    max_retries: int = 2,
) -> InsuranceQAOutput:
    """Run the full insurance QA pipeline: Writer -> QA."""
    print(f"\n[INSURANCE_QA] Starting pipeline -- {review_type}")
    print(f"  Provider: {provider}")

    # Step 1: Generate review
    print("\n  [1/2] Generating document review...")
    review = writer_agent(document_content, review_type, provider=provider)
    print(f"  -> Review type: {review.review_type}")
    print(f"  -> Findings: {len(review.findings)}")
    critical = sum(1 for f in review.findings if f.severity == "critical")
    if critical:
        print(f"  -> Critical findings: {critical}")

    # Step 2: QA (with retries)
    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(review, provider)
        print(f"  -> {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print("  -> Revising review with notes...")
            review = writer_agent(
                document_content, review_type,
                provider=provider, revision_notes=qa.revision_notes)

    return InsuranceQAOutput(
        review=review,
        qa=qa,
        meta={
            "review_type": review_type,
            "provider": provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


def save_output(output: InsuranceQAOutput) -> Path:
    """Save pipeline output to JSON file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"insurance_qa_{ts}_{run_id}.json"
    path.write_text(
        json.dumps(output.model_dump(), indent=2, default=str),
        encoding="utf-8")
    print(f"\n  [SAVED] {path}")
    return path


# -- CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Insurance QA Agent")
    parser.add_argument("--text", default="", help="Document content as text")
    parser.add_argument("--file", default="", help="File containing document to review")
    parser.add_argument("--type", default="appeal_review",
                        choices=["appeal_review", "prior_auth_review",
                                 "denial_response_review", "policy_review",
                                 "coverage_analysis_review", "claims_report_review"],
                        dest="review_type")
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
        review_type=args.review_type,
        provider=args.provider,
    )
    save_output(result)
