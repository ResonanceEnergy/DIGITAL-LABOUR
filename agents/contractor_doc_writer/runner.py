"""Contractor Document Writer Agent — Generate permit applications, inspection reports,
proposals, lien waivers, safety plans, change orders, progress reports, and bid documents.

2-step pipeline:
    1. Writer Agent — produces full contractor document from project details
    2. QA Agent — validates completeness, compliance, and professional quality

Handles: permit_application, inspection_report, contractor_proposal, lien_waiver,
         safety_plan, change_order, progress_report, bid_document

Usage:
    python -m agents.contractor_doc_writer.runner --file project_details.txt --doc-type contractor_proposal --project "Main St Renovation" --contractor "ABC Construction"
    python -m agents.contractor_doc_writer.runner --text "Scope of work..." --doc-type permit_application
    python -m agents.contractor_doc_writer.runner --file scope.md --doc-type safety_plan --provider anthropic
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
call_llm = make_bridge("contractor_doc_writer")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "contractor_doc_writer"

DOC_TYPES = [
    "permit_application", "inspection_report", "contractor_proposal",
    "lien_waiver", "safety_plan", "change_order", "progress_report",
    "bid_document",
]


# ── Pydantic Models ────────────────────────────────────────────

class Section(BaseModel):
    name: str = ""
    content: str = ""


class WriterOutput(BaseModel):
    doc_type: str = ""
    project_name: str = ""
    contractor_name: str = ""
    project_address: str = ""
    document_body: str = Field(default="", description="Main narrative content of the document")
    sections: list[Section] = Field(default_factory=list, description="Named sections of the document")
    regulatory_references: list[str] = Field(default_factory=list)
    attachments_needed: list[str] = Field(default_factory=list)
    full_markdown: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class ContractorDocOutput(BaseModel):
    document: WriterOutput = Field(default_factory=WriterOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


# ── Agent Functions ─────────────────────────────────────────────

def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def writer_agent(
    content: str,
    doc_type: str = "contractor_proposal",
    project_name: str = "",
    contractor_name: str = "",
    revision_notes: str = "",
    provider: str = "openai",
) -> WriterOutput:
    """Step 1: Generate the contractor document."""
    system = _load_prompt("writer_prompt")
    user_msg = (
        f"Document Type: {doc_type}\n"
        f"Project Name: {project_name}\n"
        f"Contractor Name: {contractor_name}\n"
    )
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nProject Details / Scope of Work:\n{content}"

    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(WriterOutput, data, agent_name="contractor_doc_writer.writer")


def qa_agent(document: WriterOutput, provider: str = "openai") -> QAResult:
    """Step 2: Validate contractor document quality and compliance."""
    system = _load_prompt("qa_prompt")
    user_msg = f"Contractor document to validate:\n{json.dumps(document.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(QAResult, data, agent_name="contractor_doc_writer.qa")


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    content: str,
    doc_type: str = "contractor_proposal",
    project_name: str = "",
    contractor_name: str = "",
    provider: str = "openai",
    max_retries: int = 2,
) -> ContractorDocOutput:
    """Run the full contractor document pipeline: Writer -> QA."""
    print(f"\n[CTR-DOC] Starting pipeline — {doc_type}")
    print(f"  Project: {project_name}")
    print(f"  Contractor: {contractor_name}")
    print(f"  Provider: {provider}")

    # Step 1: Write
    print("\n  [1/2] Generating contractor document...")
    document = writer_agent(content, doc_type, project_name, contractor_name,
                            provider=provider)
    print(f"  -> Type: {document.doc_type}")
    print(f"  -> {len(document.sections)} sections, "
          f"{len(document.regulatory_references)} regulatory references")

    # Step 2: QA (with retries)
    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(document, provider)
        print(f"  -> {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print("  -> Rewriting with revision notes...")
            document = writer_agent(
                content, doc_type, project_name, contractor_name,
                revision_notes=qa.revision_notes, provider=provider)

    output = ContractorDocOutput(
        document=document,
        qa=qa,
        meta={
            "doc_type": doc_type,
            "project_name": project_name,
            "contractor_name": contractor_name,
            "provider": provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return output


def save_output(output: ContractorDocOutput) -> Path:
    """Save pipeline output to JSON and standalone Markdown document."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # JSON
    json_path = OUTPUT_DIR / f"ctr_doc_{ts}_{run_id}.json"
    json_path.write_text(
        json.dumps(output.model_dump(), indent=2, default=str),
        encoding="utf-8")

    # Markdown
    d = output.document
    md_lines = [
        f"# {d.project_name}\n",
        f"**Document Type:** {d.doc_type}  ",
        f"**Contractor:** {d.contractor_name}  ",
        f"**Project Address:** {d.project_address}  ",
        f"**Date:** {datetime.now(timezone.utc).strftime('%B %d, %Y')}\n",
    ]

    # Document Body
    if d.document_body:
        md_lines.append("## Overview\n")
        md_lines.append(f"{d.document_body}\n")

    # Sections
    for section in d.sections:
        md_lines.append(f"## {section.name}\n")
        md_lines.append(f"{section.content}\n")

    # Regulatory References
    if d.regulatory_references:
        md_lines.append("## Regulatory References\n")
        for ref in d.regulatory_references:
            md_lines.append(f"- {ref}")
        md_lines.append("")

    # Attachments Needed
    if d.attachments_needed:
        md_lines.append("## Required Attachments\n")
        for att in d.attachments_needed:
            md_lines.append(f"- [ ] {att}")
        md_lines.append("")

    md_path = OUTPUT_DIR / f"ctr_doc_{ts}_{run_id}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\n  [SAVED] {json_path}")
    print(f"  [SAVED] {md_path}")
    return json_path


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Contractor Document Writer Agent")
    parser.add_argument("--text", default="", help="Project details as text")
    parser.add_argument("--file", default="", help="File containing project details/scope")
    parser.add_argument("--doc-type", default="contractor_proposal",
                        choices=DOC_TYPES,
                        dest="doc_type",
                        help="Type of contractor document to generate")
    parser.add_argument("--project", default="", help="Project name")
    parser.add_argument("--contractor", default="", help="Contractor name")
    parser.add_argument("--provider", default="openai", help="LLM provider")
    parser.add_argument("--max-retries", type=int, default=2, help="Max QA retry attempts")
    args = parser.parse_args()

    if args.file:
        content = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        content = args.text
    else:
        print("Error: provide --text or --file")
        sys.exit(1)

    result = run_pipeline(
        content=content,
        doc_type=args.doc_type,
        project_name=args.project,
        contractor_name=args.contractor,
        provider=args.provider,
        max_retries=args.max_retries,
    )
    save_output(result)
