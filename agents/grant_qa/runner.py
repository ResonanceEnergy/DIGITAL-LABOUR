"""Grant QA Review Agent — Review grant proposals for completeness, budget accuracy,
compliance, technical merit, and competitive readiness.

2-step pipeline:
    1. Writer Agent — produces comprehensive QA review of a grant proposal
    2. QA Agent — validates the review itself for thoroughness and calibration

Handles: SBIR proposals, federal RFP responses, state grants, foundation grants,
         grant budgets, grant narratives, compliance checks, grant renewals.

Usage:
    python -m agents.grant_qa.runner --file proposal.md --review-type full_review --grant-type sbir_proposal
    python -m agents.grant_qa.runner --text "Grant proposal text..." --review-type budget_review
    python -m agents.grant_qa.runner --file proposal.md --grant-type federal_rfp --provider anthropic
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
call_llm = make_bridge("grant_qa")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "grant_qa"


# ── Pydantic Models ────────────────────────────────────────────

class Finding(BaseModel):
    category: str = Field(default="", description="technical | budget | compliance | narrative | format")
    severity: str = Field(default="", description="critical | major | minor")
    description: str = ""
    recommendation: str = ""
    reference: str = Field(default="", description="Section or page reference in the reviewed document")


class BudgetCheck(BaseModel):
    line_items_valid: bool = False
    totals_match: bool = False
    justification_adequate: bool = False
    discrepancies: list[str] = Field(default_factory=list)


class WriterOutput(BaseModel):
    review_type: str = ""
    grant_type_reviewed: str = ""
    findings: list[Finding] = Field(default_factory=list)
    budget_validation: BudgetCheck = Field(default_factory=BudgetCheck)
    compliance_status: str = Field(default="", description="compliant | partial | non_compliant")
    competitive_score: int = Field(default=0, description="0-100 competitive readiness score")
    overall_assessment: str = ""
    recommendations: list[str] = Field(default_factory=list)
    full_markdown: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class GrantQAOutput(BaseModel):
    review: WriterOutput = Field(default_factory=WriterOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


# ── Agent Functions ─────────────────────────────────────────────

def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def writer_agent(
    document_content: str,
    review_type: str = "full_review",
    grant_type: str = "sbir_proposal",
    revision_notes: str = "",
    provider: str = "openai",
) -> WriterOutput:
    """Step 1: Generate the comprehensive QA review of the grant proposal."""
    system = _load_prompt("writer_prompt")
    user_msg = (
        f"Review Type: {review_type}\n"
        f"Grant Type: {grant_type}\n"
    )
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nGrant Proposal Document:\n{document_content}"

    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(WriterOutput, data, agent_name="grant_qa.writer")


def qa_agent(review: WriterOutput, provider: str = "openai") -> QAResult:
    """Step 2: Validate the quality and accuracy of the QA review."""
    system = _load_prompt("qa_prompt")
    user_msg = f"Grant QA review to validate:\n{json.dumps(review.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(QAResult, data, agent_name="grant_qa.qa")


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    document_content: str,
    review_type: str = "full_review",
    grant_type: str = "sbir_proposal",
    provider: str = "openai",
    max_retries: int = 2,
) -> GrantQAOutput:
    """Run the full grant QA pipeline: Review -> QA."""
    print(f"\n[GRANT-QA] Starting pipeline — {review_type} ({grant_type})")
    print(f"  Provider: {provider}")

    # Step 1: Generate review
    print("\n  [1/2] Generating grant QA review...")
    review = writer_agent(document_content, review_type, grant_type, provider=provider)
    print(f"  -> {len(review.findings)} findings, competitive score: {review.competitive_score}")
    print(f"  -> Compliance status: {review.compliance_status}")

    critical_count = sum(1 for f in review.findings if f.severity == "critical")
    major_count = sum(1 for f in review.findings if f.severity == "major")
    print(f"  -> {critical_count} critical, {major_count} major findings")

    # Step 2: QA (with retries)
    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(review, provider)
        print(f"  -> {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print("  -> Rewriting review with revision notes...")
            review = writer_agent(
                document_content, review_type, grant_type,
                revision_notes=qa.revision_notes, provider=provider)

    output = GrantQAOutput(
        review=review,
        qa=qa,
        meta={
            "review_type": review_type,
            "grant_type": grant_type,
            "provider": provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return output


def save_output(output: GrantQAOutput) -> Path:
    """Save pipeline output to JSON and standalone Markdown review report."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # JSON
    json_path = OUTPUT_DIR / f"grant_qa_{ts}_{run_id}.json"
    json_path.write_text(
        json.dumps(output.model_dump(), indent=2, default=str),
        encoding="utf-8")

    # Markdown
    r = output.review
    md_lines = [
        f"# Grant QA Review Report\n",
        f"**Review Type:** {r.review_type}  ",
        f"**Grant Type Reviewed:** {r.grant_type_reviewed}  ",
        f"**Date:** {datetime.now(timezone.utc).strftime('%B %d, %Y')}  ",
        f"**Competitive Score:** {r.competitive_score}/100  ",
        f"**Compliance Status:** {r.compliance_status}\n",
    ]

    # Overall Assessment
    md_lines.append("## Overall Assessment\n")
    md_lines.append(f"{r.overall_assessment}\n")

    # Findings
    if r.findings:
        md_lines.append("## Findings\n")
        md_lines.append("| # | Category | Severity | Description | Recommendation |")
        md_lines.append("|---|----------|----------|-------------|----------------|")
        for i, f in enumerate(r.findings, 1):
            severity_icon = {"critical": "RED", "major": "YELLOW", "minor": "BLUE"}.get(f.severity, "")
            md_lines.append(
                f"| {i} | {f.category} | {f.severity.upper()} {severity_icon} | "
                f"{f.description} | {f.recommendation} |"
            )
        md_lines.append("")

    # Budget Validation
    md_lines.append("## Budget Validation\n")
    bv = r.budget_validation
    md_lines.append(f"- **Line Items Valid:** {'Yes' if bv.line_items_valid else 'No'}  ")
    md_lines.append(f"- **Totals Match:** {'Yes' if bv.totals_match else 'No'}  ")
    md_lines.append(f"- **Justification Adequate:** {'Yes' if bv.justification_adequate else 'No'}\n")
    if bv.discrepancies:
        md_lines.append("### Discrepancies\n")
        for d in bv.discrepancies:
            md_lines.append(f"- {d}")
        md_lines.append("")

    # Recommendations
    if r.recommendations:
        md_lines.append("## Recommendations\n")
        for i, rec in enumerate(r.recommendations, 1):
            md_lines.append(f"{i}. {rec}")
        md_lines.append("")

    # QA Status
    md_lines.append("## QA Verification\n")
    md_lines.append(f"- **Status:** {output.qa.status}  ")
    md_lines.append(f"- **Score:** {output.qa.score}/100\n")
    if output.qa.issues:
        for issue in output.qa.issues:
            md_lines.append(f"- {issue}")
        md_lines.append("")

    md_path = OUTPUT_DIR / f"grant_qa_{ts}_{run_id}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\n  [SAVED] {json_path}")
    print(f"  [SAVED] {md_path}")
    return json_path


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Grant QA Review Agent")
    parser.add_argument("--text", default="", help="Grant proposal text to review")
    parser.add_argument("--file", default="", help="File containing the grant proposal")
    parser.add_argument("--review-type", default="full_review",
                        choices=["full_review", "budget_review", "compliance_review",
                                 "technical_review", "narrative_review"],
                        dest="review_type")
    parser.add_argument("--grant-type", default="sbir_proposal",
                        choices=["sbir_proposal", "federal_rfp", "state_grant",
                                 "foundation_grant", "grant_budget", "grant_narrative",
                                 "grant_compliance_check", "grant_renewal"],
                        dest="grant_type")
    parser.add_argument("--provider", default="openai", help="LLM provider")
    args = parser.parse_args()

    if args.file:
        document_content = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        document_content = args.text
    else:
        print("Error: provide --text or --file")
        sys.exit(1)

    result = run_pipeline(
        document_content=document_content,
        review_type=args.review_type,
        grant_type=args.grant_type,
        provider=args.provider,
    )
    save_output(result)
