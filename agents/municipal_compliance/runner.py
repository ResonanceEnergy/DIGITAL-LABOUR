"""Municipal Compliance Agent — Check municipal documents against legal requirements.

2-step pipeline:
    1. Writer Agent — produces compliance analysis with violations and remediation
    2. QA Agent — validates the compliance check itself for thoroughness

Checks against: open meeting laws, public records requirements, state municipal codes,
                Roberts Rules of Order, Brown Act, Sunshine Laws

Usage:
    python -m agents.municipal_compliance.runner --file minutes.txt --type open_meeting
    python -m agents.municipal_compliance.runner --text "Notice is hereby given..." --type public_records
    python -m agents.municipal_compliance.runner --file ordinance.md --type municipal_code --jurisdiction california
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
call_llm = make_bridge("municipal_compliance")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "municipal_compliance"

COMPLIANCE_TYPES = [
    "open_meeting", "public_records", "municipal_code",
    "roberts_rules", "budget_compliance", "procurement",
    "ethics", "comprehensive",
]

JURISDICTIONS = [
    "us_general", "california", "texas", "new_york", "florida",
    "illinois", "ohio", "pennsylvania", "other",
]


# ── Pydantic Models ────────────────────────────────────────────

class Violation(BaseModel):
    statute_reference: str = ""
    description: str = ""
    severity: str = Field(default="", description="critical | major | minor | advisory")
    remediation: str = ""
    deadline: str = Field(default="", description="Remediation deadline if applicable")


class WriterOutput(BaseModel):
    compliance_type: str = ""
    jurisdiction: str = ""
    document_reviewed: str = Field(default="", description="Brief description of the document under review")
    violations: list[Violation] = Field(default_factory=list)
    compliance_score: int = Field(default=0, description="0-100 compliance score")
    applicable_statutes: str = Field(default="", description="List of applicable laws and statutes")
    remediation_steps: str = Field(default="", description="Ordered remediation plan")
    certification_status: str = Field(default="", description="compliant | conditionally_compliant | non_compliant")
    full_markdown: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class MunicipalComplianceOutput(BaseModel):
    compliance: WriterOutput = Field(default_factory=WriterOutput)
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
    compliance_type: str = "open_meeting",
    jurisdiction: str = "us_general",
    revision_notes: str = "",
    provider: str = "openai",
) -> WriterOutput:
    """Step 1: Generate the compliance analysis."""
    system = _load_prompt("writer_prompt")
    user_msg = (
        f"Compliance Type: {compliance_type}\n"
        f"Jurisdiction: {jurisdiction}\n"
    )
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nDocument to Analyze:\n{document_content}"

    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(WriterOutput, data, agent_name="municipal_compliance.writer")


def qa_agent(compliance: WriterOutput, provider: str = "openai") -> QAResult:
    """Step 2: Validate the compliance analysis quality."""
    system = _load_prompt("qa_prompt")
    user_msg = f"Compliance analysis to validate:\n{json.dumps(compliance.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(QAResult, data, agent_name="municipal_compliance.qa")


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    document_content: str,
    compliance_type: str = "open_meeting",
    jurisdiction: str = "us_general",
    provider: str = "openai",
    max_retries: int = 2,
) -> MunicipalComplianceOutput:
    """Run the full compliance check pipeline: Analysis -> QA."""
    print(f"\n[MUN-COMPLIANCE] Starting pipeline — {compliance_type} ({jurisdiction})")
    print(f"  Provider: {provider}")

    # Step 1: Compliance Analysis
    print("\n  [1/2] Generating compliance analysis...")
    compliance = writer_agent(document_content, compliance_type, jurisdiction,
                              provider=provider)
    print(f"  -> Type: {compliance.compliance_type}")
    print(f"  -> Violations: {len(compliance.violations)}, "
          f"Score: {compliance.compliance_score}/100")
    print(f"  -> Status: {compliance.certification_status}")

    # Step 2: QA (with retries)
    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(compliance, provider)
        print(f"  -> {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print("  -> Rewriting with revision notes...")
            compliance = writer_agent(
                document_content, compliance_type, jurisdiction,
                revision_notes=qa.revision_notes, provider=provider)

    output = MunicipalComplianceOutput(
        compliance=compliance,
        qa=qa,
        meta={
            "compliance_type": compliance_type,
            "jurisdiction": jurisdiction,
            "provider": provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return output


def save_output(output: MunicipalComplianceOutput) -> Path:
    """Save pipeline output to JSON and standalone Markdown report."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # JSON
    json_path = OUTPUT_DIR / f"mun_compliance_{ts}_{run_id}.json"
    json_path.write_text(
        json.dumps(output.model_dump(), indent=2, default=str),
        encoding="utf-8")

    # Markdown
    c = output.compliance
    md_lines = [
        f"# Municipal Compliance Report\n",
        f"**Compliance Type:** {c.compliance_type}  ",
        f"**Jurisdiction:** {c.jurisdiction}  ",
        f"**Document:** {c.document_reviewed}  ",
        f"**Score:** {c.compliance_score}/100  ",
        f"**Status:** {c.certification_status}  ",
        f"**Date:** {datetime.now(timezone.utc).strftime('%B %d, %Y')}\n",
        "---\n",
    ]

    md_lines.append("## Applicable Statutes\n")
    md_lines.append(f"{c.applicable_statutes}\n")

    if c.violations:
        md_lines.append("## Violations\n")
        md_lines.append("| # | Statute | Severity | Description | Remediation | Deadline |")
        md_lines.append("|---|---------|----------|-------------|-------------|----------|")
        for i, v in enumerate(c.violations, 1):
            md_lines.append(
                f"| {i} | {v.statute_reference} | {v.severity} | "
                f"{v.description} | {v.remediation} | {v.deadline or 'N/A'} |"
            )
        md_lines.append("")

    md_lines.append("## Remediation Steps\n")
    md_lines.append(f"{c.remediation_steps}\n")

    md_path = OUTPUT_DIR / f"mun_compliance_{ts}_{run_id}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\n  [SAVED] {json_path}")
    print(f"  [SAVED] {md_path}")
    return json_path


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Municipal Compliance Agent")
    parser.add_argument("--text", default="", help="Document content as text")
    parser.add_argument("--file", default="", help="File containing document to check")
    parser.add_argument("--type", default="open_meeting",
                        choices=COMPLIANCE_TYPES,
                        dest="compliance_type")
    parser.add_argument("--jurisdiction", default="us_general",
                        choices=JURISDICTIONS,
                        help="Legal jurisdiction for compliance check")
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
        compliance_type=args.compliance_type,
        jurisdiction=args.jurisdiction,
        provider=args.provider,
        max_retries=args.max_retries,
    )
    save_output(result)
