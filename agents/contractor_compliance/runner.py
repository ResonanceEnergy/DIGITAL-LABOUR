"""Contractor Compliance Agent — Check contractor documents against OSHA, state licensing,
building codes, insurance requirements, and bonding regulations.

2-step pipeline:
    1. Writer Agent — produces detailed compliance audit with violations
    2. QA Agent — validates the audit for accuracy and thoroughness

Handles: OSHA 29 CFR 1926, state licensing, IBC/IRC/NEC building codes,
         insurance requirements, bonding (Miller Act), environmental (EPA/NPDES),
         prevailing wage (Davis-Bacon).

Usage:
    python -m agents.contractor_compliance.runner --file safety_plan.txt --compliance-type osha --jurisdiction ca
    python -m agents.contractor_compliance.runner --text "Document content..." --compliance-type general
    python -m agents.contractor_compliance.runner --file proposal.md --compliance-type insurance --provider anthropic
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
call_llm = make_bridge("contractor_compliance")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "contractor_compliance"

COMPLIANCE_TYPES = [
    "general", "osha", "licensing", "building_code", "insurance",
    "bonding", "environmental", "prevailing_wage",
]

JURISDICTIONS = [
    "us_federal", "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl",
    "ga", "hi", "id", "il", "in", "ia", "ks", "ky", "la", "me", "md",
    "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv", "nh", "nj", "nm",
    "ny", "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc", "sd", "tn",
    "tx", "ut", "vt", "va", "wa", "wv", "wi", "wy", "dc",
]


# ── Pydantic Models ────────────────────────────────────────────

class Violation(BaseModel):
    code_reference: str = ""
    description: str = ""
    severity: str = Field(default="minor", description="critical | major | minor")
    remediation: str = ""
    deadline: str = ""


class WriterOutput(BaseModel):
    compliance_type: str = ""
    jurisdiction: str = ""
    document_reviewed: str = ""
    violations: list[Violation] = Field(default_factory=list)
    compliance_score: int = Field(default=0, description="0-100 compliance score")
    regulatory_framework: str = Field(default="", description="Applicable regulations and standards")
    remediation_steps: list[str] = Field(default_factory=list)
    certification_status: str = Field(
        default="",
        description="compliant | conditionally-compliant | non-compliant",
    )
    full_markdown: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class ComplianceOutput(BaseModel):
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
    compliance_type: str = "general",
    jurisdiction: str = "us_federal",
    revision_notes: str = "",
    provider: str = "openai",
) -> WriterOutput:
    """Step 1: Generate the compliance audit of the contractor document."""
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
    return safe_validate(WriterOutput, data, agent_name="contractor_compliance.writer")


def qa_agent(audit: WriterOutput, provider: str = "openai") -> QAResult:
    """Step 2: Validate the compliance audit for accuracy and thoroughness."""
    system = _load_prompt("qa_prompt")
    user_msg = f"Compliance audit to validate:\n{json.dumps(audit.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(QAResult, data, agent_name="contractor_compliance.qa")


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    document_content: str,
    compliance_type: str = "general",
    jurisdiction: str = "us_federal",
    provider: str = "openai",
    max_retries: int = 2,
) -> ComplianceOutput:
    """Run the full compliance check pipeline: Audit -> QA."""
    print(f"\n[CTR-COMPLIANCE] Starting pipeline — {compliance_type} ({jurisdiction})")
    print(f"  Provider: {provider}")

    # Step 1: Compliance Audit
    print("\n  [1/2] Generating compliance audit...")
    audit = writer_agent(document_content, compliance_type, jurisdiction,
                         provider=provider)
    critical_count = sum(1 for v in audit.violations if v.severity == "critical")
    major_count = sum(1 for v in audit.violations if v.severity == "major")
    minor_count = sum(1 for v in audit.violations if v.severity == "minor")
    print(f"  -> {len(audit.violations)} violations "
          f"({critical_count} critical, {major_count} major, {minor_count} minor)")
    print(f"  -> Compliance score: {audit.compliance_score}/100")
    print(f"  -> Status: {audit.certification_status}")

    # Step 2: QA (with retries)
    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(audit, provider)
        print(f"  -> {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print("  -> Revising audit with QA notes...")
            audit = writer_agent(
                document_content, compliance_type, jurisdiction,
                revision_notes=qa.revision_notes, provider=provider)

    output = ComplianceOutput(
        compliance=audit,
        qa=qa,
        meta={
            "compliance_type": compliance_type,
            "jurisdiction": jurisdiction,
            "violations_count": len(audit.violations),
            "critical_violations": critical_count,
            "compliance_score": audit.compliance_score,
            "certification_status": audit.certification_status,
            "provider": provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return output


def save_output(output: ComplianceOutput) -> Path:
    """Save pipeline output to JSON and standalone Markdown compliance report."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # JSON
    json_path = OUTPUT_DIR / f"ctr_compliance_{ts}_{run_id}.json"
    json_path.write_text(
        json.dumps(output.model_dump(), indent=2, default=str),
        encoding="utf-8")

    # Markdown
    c = output.compliance
    md_lines = [
        f"# Compliance Audit: {c.document_reviewed}\n",
        f"**Compliance Type:** {c.compliance_type}  ",
        f"**Jurisdiction:** {c.jurisdiction}  ",
        f"**Compliance Score:** {c.compliance_score}/100  ",
        f"**Certification Status:** {c.certification_status}  ",
        f"**Date:** {datetime.now(timezone.utc).strftime('%B %d, %Y')}\n",
    ]

    # Regulatory Framework
    if c.regulatory_framework:
        md_lines.append("## Regulatory Framework\n")
        md_lines.append(f"{c.regulatory_framework}\n")

    # Violations by Severity
    for severity in ["critical", "major", "minor"]:
        severity_violations = [v for v in c.violations if v.severity == severity]
        if severity_violations:
            md_lines.append(f"## {severity.capitalize()} Violations\n")
            for i, v in enumerate(severity_violations, 1):
                md_lines.append(f"### {i}. {v.code_reference}\n")
                md_lines.append(f"**Description:** {v.description}  ")
                md_lines.append(f"**Remediation:** {v.remediation}  ")
                md_lines.append(f"**Deadline:** {v.deadline}\n")

    # Remediation Steps
    if c.remediation_steps:
        md_lines.append("## Remediation Plan\n")
        for step in c.remediation_steps:
            md_lines.append(f"- {step}")
        md_lines.append("")

    md_path = OUTPUT_DIR / f"ctr_compliance_{ts}_{run_id}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\n  [SAVED] {json_path}")
    print(f"  [SAVED] {md_path}")
    return json_path


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Contractor Compliance Agent")
    parser.add_argument("--text", default="", help="Document content as text")
    parser.add_argument("--file", default="", help="File containing document to audit")
    parser.add_argument("--compliance-type", default="general",
                        choices=COMPLIANCE_TYPES,
                        dest="compliance_type",
                        help="Type of compliance check")
    parser.add_argument("--jurisdiction", default="us_federal",
                        help="Jurisdiction (us_federal, ca, tx, ny, etc.)")
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
