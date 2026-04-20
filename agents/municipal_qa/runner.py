"""Municipal QA Agent — Review any municipal document for accuracy, legal compliance, and format.

2-step pipeline:
    1. Writer Agent — produces a structured review with findings
    2. QA Agent — validates the review itself for thoroughness and accuracy

Handles: meeting minutes, public notices, ordinances, resolutions, municipal grants,
         budget summaries, annual reports, RFPs, agendas, staff reports

Usage:
    python -m agents.municipal_qa.runner --file document.txt --review-type legal_compliance
    python -m agents.municipal_qa.runner --text "Minutes of the regular meeting..." --review-type format
    python -m agents.municipal_qa.runner --file ordinance.md --review-type general --provider anthropic
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
call_llm = make_bridge("municipal_qa")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "municipal_qa"

REVIEW_TYPES = [
    "general", "legal_compliance", "format", "accuracy",
    "public_records", "open_meeting", "procedural",
]


# ── Pydantic Models ────────────────────────────────────────────

class Finding(BaseModel):
    category: str = ""
    severity: str = Field(default="", description="critical | major | minor | informational")
    description: str = ""
    recommendation: str = ""
    legal_reference: str = ""


class WriterOutput(BaseModel):
    review_type: str = ""
    document_reviewed: str = Field(default="", description="Brief description of the document under review")
    findings: list[Finding] = Field(default_factory=list)
    legal_compliance: str = Field(default="", description="Overall legal compliance assessment")
    public_records_compliance: str = Field(default="", description="Public records act compliance status")
    overall_assessment: str = ""
    recommendations: str = ""
    full_markdown: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class MunicipalQAOutput(BaseModel):
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
    """Step 1: Generate the municipal document review."""
    system = _load_prompt("writer_prompt")
    user_msg = f"Review Type: {review_type}\n"
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nDocument to Review:\n{document_content}"

    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(WriterOutput, data, agent_name="municipal_qa.writer")


def qa_agent(review: WriterOutput, provider: str = "openai") -> QAResult:
    """Step 2: Validate the review quality and thoroughness."""
    system = _load_prompt("qa_prompt")
    user_msg = f"Municipal document review to validate:\n{json.dumps(review.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(QAResult, data, agent_name="municipal_qa.qa")


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    document_content: str,
    review_type: str = "general",
    provider: str = "openai",
    max_retries: int = 2,
) -> MunicipalQAOutput:
    """Run the full municipal QA pipeline: Review -> QA."""
    print(f"\n[MUN-QA] Starting pipeline — review type: {review_type}")
    print(f"  Provider: {provider}")

    # Step 1: Review
    print("\n  [1/2] Generating document review...")
    review = writer_agent(document_content, review_type, provider=provider)
    print(f"  -> Review type: {review.review_type}")
    print(f"  -> Findings: {len(review.findings)}")

    # Step 2: QA (with retries)
    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(review, provider)
        print(f"  -> {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print("  -> Rewriting with revision notes...")
            review = writer_agent(
                document_content, review_type,
                revision_notes=qa.revision_notes, provider=provider)

    output = MunicipalQAOutput(
        review=review,
        qa=qa,
        meta={
            "review_type": review_type,
            "provider": provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return output


def save_output(output: MunicipalQAOutput) -> Path:
    """Save pipeline output to JSON and standalone Markdown review."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # JSON
    json_path = OUTPUT_DIR / f"mun_qa_{ts}_{run_id}.json"
    json_path.write_text(
        json.dumps(output.model_dump(), indent=2, default=str),
        encoding="utf-8")

    # Markdown
    r = output.review
    md_lines = [
        f"# Municipal Document Review\n",
        f"**Review Type:** {r.review_type}  ",
        f"**Document:** {r.document_reviewed}  ",
        f"**Date:** {datetime.now(timezone.utc).strftime('%B %d, %Y')}\n",
        "---\n",
    ]

    md_lines.append("## Overall Assessment\n")
    md_lines.append(f"{r.overall_assessment}\n")

    md_lines.append("## Legal Compliance\n")
    md_lines.append(f"{r.legal_compliance}\n")

    md_lines.append("## Public Records Compliance\n")
    md_lines.append(f"{r.public_records_compliance}\n")

    if r.findings:
        md_lines.append("## Findings\n")
        md_lines.append("| # | Category | Severity | Description | Recommendation |")
        md_lines.append("|---|----------|----------|-------------|----------------|")
        for i, f in enumerate(r.findings, 1):
            md_lines.append(
                f"| {i} | {f.category} | {f.severity} | {f.description} | {f.recommendation} |"
            )
        md_lines.append("")

    md_lines.append("## Recommendations\n")
    md_lines.append(f"{r.recommendations}\n")

    md_path = OUTPUT_DIR / f"mun_qa_{ts}_{run_id}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\n  [SAVED] {json_path}")
    print(f"  [SAVED] {md_path}")
    return json_path


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Municipal QA Agent")
    parser.add_argument("--text", default="", help="Document content as text")
    parser.add_argument("--file", default="", help="File containing document to review")
    parser.add_argument("--review-type", default="general",
                        choices=REVIEW_TYPES,
                        dest="review_type")
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
