"""Grant Compliance Agent — Check grant proposals against agency-specific requirements,
OMB circulars, FAR/DFARS, and cost principles.

2-step pipeline:
    1. Writer Agent — produces compliance audit of a grant proposal
    2. QA Agent — validates the audit for regulatory accuracy and completeness

Handles: Agency requirements (NIH, NSF, DOE, DOD), cost principles (2 CFR 200),
         FAR/DFARS compliance, OMB circulars, export control, data management.

Usage:
    python -m agents.grant_compliance.runner --file proposal.md --agency nsf --compliance-type agency_requirements
    python -m agents.grant_compliance.runner --text "Grant text..." --agency nih --compliance-type cost_principles
    python -m agents.grant_compliance.runner --file proposal.md --agency dod --compliance-type full_audit --provider anthropic
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
call_llm = make_bridge("grant_compliance")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "grant_compliance"


# ── Pydantic Models ────────────────────────────────────────────

class Violation(BaseModel):
    regulation_reference: str = Field(default="", description="Specific regulation, circular, or policy section")
    description: str = ""
    severity: str = Field(default="", description="critical | major | minor")
    remediation: str = ""
    agency_requirement: str = Field(default="", description="The specific agency rule being violated")
    deadline: str = Field(default="", description="When remediation must be completed")


class WriterOutput(BaseModel):
    compliance_type: str = ""
    agency: str = ""
    document_reviewed: str = ""
    violations: list[Violation] = Field(default_factory=list)
    compliance_score: int = Field(default=0, description="0-100 compliance score")
    applicable_regulations: list[str] = Field(default_factory=list)
    cost_principle_compliance: str = ""
    far_compliance: str = ""
    remediation_steps: list[str] = Field(default_factory=list)
    certification_status: str = Field(
        default="",
        description="compliant | conditionally_compliant | non_compliant | requires_legal_review"
    )
    full_markdown: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class GrantComplianceOutput(BaseModel):
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
    compliance_type: str = "agency_requirements",
    agency: str = "nsf",
    revision_notes: str = "",
    provider: str = "openai",
) -> WriterOutput:
    """Step 1: Generate the compliance audit of the grant proposal."""
    system = _load_prompt("writer_prompt")
    user_msg = (
        f"Compliance Type: {compliance_type}\n"
        f"Target Agency: {agency}\n"
    )
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nGrant Proposal Document:\n{document_content}"

    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(WriterOutput, data, agent_name="grant_compliance.writer")


def qa_agent(compliance: WriterOutput, provider: str = "openai") -> QAResult:
    """Step 2: Validate the accuracy and completeness of the compliance audit."""
    system = _load_prompt("qa_prompt")
    user_msg = f"Grant compliance audit to validate:\n{json.dumps(compliance.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(QAResult, data, agent_name="grant_compliance.qa")


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    document_content: str,
    compliance_type: str = "agency_requirements",
    agency: str = "nsf",
    provider: str = "openai",
    max_retries: int = 2,
) -> GrantComplianceOutput:
    """Run the full grant compliance pipeline: Audit -> QA."""
    print(f"\n[GRANT-COMPLIANCE] Starting pipeline — {compliance_type} ({agency})")
    print(f"  Provider: {provider}")

    # Step 1: Generate compliance audit
    print("\n  [1/2] Generating compliance audit...")
    compliance = writer_agent(document_content, compliance_type, agency, provider=provider)
    print(f"  -> {len(compliance.violations)} violations found, score: {compliance.compliance_score}")
    print(f"  -> Certification status: {compliance.certification_status}")

    critical_count = sum(1 for v in compliance.violations if v.severity == "critical")
    major_count = sum(1 for v in compliance.violations if v.severity == "major")
    print(f"  -> {critical_count} critical, {major_count} major violations")

    # Step 2: QA (with retries)
    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(compliance, provider)
        print(f"  -> {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print("  -> Rewriting audit with revision notes...")
            compliance = writer_agent(
                document_content, compliance_type, agency,
                revision_notes=qa.revision_notes, provider=provider)

    output = GrantComplianceOutput(
        compliance=compliance,
        qa=qa,
        meta={
            "compliance_type": compliance_type,
            "agency": agency,
            "provider": provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return output


def save_output(output: GrantComplianceOutput) -> Path:
    """Save pipeline output to JSON and standalone Markdown compliance report."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # JSON
    json_path = OUTPUT_DIR / f"grant_compliance_{ts}_{run_id}.json"
    json_path.write_text(
        json.dumps(output.model_dump(), indent=2, default=str),
        encoding="utf-8")

    # Markdown
    c = output.compliance
    md_lines = [
        f"# Grant Compliance Audit Report\n",
        f"**Compliance Type:** {c.compliance_type}  ",
        f"**Agency:** {c.agency.upper()}  ",
        f"**Date:** {datetime.now(timezone.utc).strftime('%B %d, %Y')}  ",
        f"**Compliance Score:** {c.compliance_score}/100  ",
        f"**Certification Status:** {c.certification_status}\n",
    ]

    # Document Reviewed
    if c.document_reviewed:
        md_lines.append(f"**Document Reviewed:** {c.document_reviewed}\n")

    # Applicable Regulations
    if c.applicable_regulations:
        md_lines.append("## Applicable Regulations\n")
        for reg in c.applicable_regulations:
            md_lines.append(f"- {reg}")
        md_lines.append("")

    # Violations
    if c.violations:
        md_lines.append("## Violations\n")
        md_lines.append("| # | Regulation | Severity | Description | Remediation | Deadline |")
        md_lines.append("|---|-----------|----------|-------------|-------------|----------|")
        for i, v in enumerate(c.violations, 1):
            md_lines.append(
                f"| {i} | {v.regulation_reference} | {v.severity.upper()} | "
                f"{v.description} | {v.remediation} | {v.deadline} |"
            )
        md_lines.append("")
    else:
        md_lines.append("## Violations\n")
        md_lines.append("No violations found.\n")

    # Cost Principle Compliance
    md_lines.append("## Cost Principle Compliance\n")
    md_lines.append(f"{c.cost_principle_compliance}\n")

    # FAR Compliance
    md_lines.append("## FAR/DFARS Compliance\n")
    md_lines.append(f"{c.far_compliance}\n")

    # Remediation Steps
    if c.remediation_steps:
        md_lines.append("## Remediation Steps\n")
        for i, step in enumerate(c.remediation_steps, 1):
            md_lines.append(f"{i}. {step}")
        md_lines.append("")

    # QA Status
    md_lines.append("## QA Verification\n")
    md_lines.append(f"- **Status:** {output.qa.status}  ")
    md_lines.append(f"- **Score:** {output.qa.score}/100\n")
    if output.qa.issues:
        for issue in output.qa.issues:
            md_lines.append(f"- {issue}")
        md_lines.append("")

    md_path = OUTPUT_DIR / f"grant_compliance_{ts}_{run_id}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\n  [SAVED] {json_path}")
    print(f"  [SAVED] {md_path}")
    return json_path


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Grant Compliance Agent")
    parser.add_argument("--text", default="", help="Grant proposal text to audit")
    parser.add_argument("--file", default="", help="File containing the grant proposal")
    parser.add_argument("--compliance-type", default="agency_requirements",
                        choices=["agency_requirements", "cost_principles", "far_compliance",
                                 "omb_circulars", "data_management", "export_control",
                                 "human_subjects", "full_audit"],
                        dest="compliance_type")
    parser.add_argument("--agency", default="nsf",
                        choices=["nih", "nsf", "doe", "dod", "usda", "sba",
                                 "state", "foundation", "other"],
                        help="Target funding agency")
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
        compliance_type=args.compliance_type,
        agency=args.agency,
        provider=args.provider,
    )
    save_output(result)
