"""Contractor QA Review Agent — Review any contractor document for quality, compliance,
completeness, and risk exposure.

2-step pipeline:
    1. Writer Agent — produces detailed QA review with findings
    2. QA Agent — validates the review itself for thoroughness and accuracy

Handles reviews of: permit applications, inspection reports, proposals, lien waivers,
safety plans, change orders, progress reports, bid documents, and any other contractor
documentation.

Usage:
    python -m agents.contractor_qa.runner --file proposal.txt --review-type general
    python -m agents.contractor_qa.runner --text "Document content..." --review-type safety
    python -m agents.contractor_qa.runner --file safety_plan.md --review-type compliance --provider anthropic
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
call_llm = make_bridge("contractor_qa")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "contractor_qa"

REVIEW_TYPES = [
    "general", "safety", "financial", "legal", "schedule", "compliance",
]


# ── Pydantic Models ────────────────────────────────────────────

class Finding(BaseModel):
    category: str = ""
    severity: str = Field(default="minor", description="critical | major | minor")
    description: str = ""
    recommendation: str = ""
    reference: str = ""


class WriterOutput(BaseModel):
    review_type: str = ""
    document_reviewed: str = ""
    findings: list[Finding] = Field(default_factory=list)
    compliance_status: str = Field(default="", description="compliant | conditional | non-compliant")
    risk_level: str = Field(default="", description="low | medium | high | critical")
    overall_assessment: str = ""
    recommendations: list[str] = Field(default_factory=list)
    full_markdown: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class ContractorQAOutput(BaseModel):
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
    review_type: str = "general",
    revision_notes: str = "",
    provider: str = "openai",
) -> WriterOutput:
    """Step 1: Generate the QA review of the contractor document."""
    system = _load_prompt("writer_prompt")
    user_msg = f"Review Type: {review_type}\n"
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nDocument to Review:\n{document_content}"

    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(WriterOutput, data, agent_name="contractor_qa.writer")


def qa_agent(review: WriterOutput, provider: str = "openai") -> QAResult:
    """Step 2: Validate the QA review for thoroughness and accuracy."""
    system = _load_prompt("qa_prompt")
    user_msg = f"QA review to validate:\n{json.dumps(review.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(QAResult, data, agent_name="contractor_qa.qa")


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    document_content: str,
    review_type: str = "general",
    provider: str = "openai",
    max_retries: int = 2,
) -> ContractorQAOutput:
    """Run the full contractor QA review pipeline: Review -> QA."""
    print(f"\n[CTR-QA] Starting pipeline — {review_type} review")
    print(f"  Provider: {provider}")

    # Step 1: Review
    print("\n  [1/2] Generating QA review...")
    review = writer_agent(document_content, review_type, provider=provider)
    critical_count = sum(1 for f in review.findings if f.severity == "critical")
    major_count = sum(1 for f in review.findings if f.severity == "major")
    minor_count = sum(1 for f in review.findings if f.severity == "minor")
    print(f"  -> {len(review.findings)} findings "
          f"({critical_count} critical, {major_count} major, {minor_count} minor)")
    print(f"  -> Compliance: {review.compliance_status}, Risk: {review.risk_level}")

    # Step 2: QA (with retries)
    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(review, provider)
        print(f"  -> {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print("  -> Revising review with QA notes...")
            review = writer_agent(
                document_content, review_type,
                revision_notes=qa.revision_notes, provider=provider)

    output = ContractorQAOutput(
        review=review,
        qa=qa,
        meta={
            "review_type": review_type,
            "document_reviewed": review.document_reviewed,
            "findings_count": len(review.findings),
            "critical_findings": critical_count,
            "provider": provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return output


def save_output(output: ContractorQAOutput) -> Path:
    """Save pipeline output to JSON and standalone Markdown review report."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # JSON
    json_path = OUTPUT_DIR / f"ctr_qa_{ts}_{run_id}.json"
    json_path.write_text(
        json.dumps(output.model_dump(), indent=2, default=str),
        encoding="utf-8")

    # Markdown
    r = output.review
    md_lines = [
        f"# QA Review: {r.document_reviewed}\n",
        f"**Review Type:** {r.review_type}  ",
        f"**Compliance Status:** {r.compliance_status}  ",
        f"**Risk Level:** {r.risk_level}  ",
        f"**Date:** {datetime.now(timezone.utc).strftime('%B %d, %Y')}\n",
    ]

    # Overall Assessment
    md_lines.append("## Overall Assessment\n")
    md_lines.append(f"{r.overall_assessment}\n")

    # Findings by Severity
    for severity in ["critical", "major", "minor"]:
        severity_findings = [f for f in r.findings if f.severity == severity]
        if severity_findings:
            md_lines.append(f"## {severity.capitalize()} Findings\n")
            for i, finding in enumerate(severity_findings, 1):
                md_lines.append(f"### {i}. [{finding.category.upper()}] {finding.description}\n")
                md_lines.append(f"**Reference:** {finding.reference}  ")
                md_lines.append(f"**Recommendation:** {finding.recommendation}\n")

    # Recommendations
    if r.recommendations:
        md_lines.append("## Recommendations\n")
        for i, rec in enumerate(r.recommendations, 1):
            md_lines.append(f"{i}. {rec}")
        md_lines.append("")

    md_path = OUTPUT_DIR / f"ctr_qa_{ts}_{run_id}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\n  [SAVED] {json_path}")
    print(f"  [SAVED] {md_path}")
    return json_path


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Contractor QA Review Agent")
    parser.add_argument("--text", default="", help="Document content as text")
    parser.add_argument("--file", default="", help="File containing document to review")
    parser.add_argument("--review-type", default="general",
                        choices=REVIEW_TYPES,
                        dest="review_type",
                        help="Type of review to perform")
    parser.add_argument("--provider", default="openai", help="LLM provider")
    parser.add_argument("--max-retries", type=int, default=2, help="Max QA retry attempts")
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
        provider=args.provider,
        max_retries=args.max_retries,
    )
    save_output(result)
