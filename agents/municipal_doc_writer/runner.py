"""Municipal Document Writer Agent — Generate municipal documents for local government.

2-step pipeline:
    1. Writer Agent — produces full municipal document from content brief
    2. QA Agent — validates completeness, legal compliance, and proper format

Handles: meeting_minutes, public_notice, ordinance, resolution, municipal_grant,
         budget_summary, annual_report, municipal_rfp, agenda, staff_report

Usage:
    python -m agents.municipal_doc_writer.runner --file brief.txt --type meeting_minutes --municipality "Springfield"
    python -m agents.municipal_doc_writer.runner --text "Council discussed..." --type ordinance --department "Planning"
    python -m agents.municipal_doc_writer.runner --file notes.md --type resolution --provider anthropic
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
call_llm = make_bridge("municipal_doc_writer")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "municipal_doc_writer"

DOC_TYPES = [
    "meeting_minutes", "public_notice", "ordinance", "resolution",
    "municipal_grant", "budget_summary", "annual_report", "municipal_rfp",
    "agenda", "staff_report",
]


# ── Pydantic Models ────────────────────────────────────────────

class WriterOutput(BaseModel):
    doc_type: str = ""
    municipality_name: str = ""
    department: str = ""
    meeting_date: str = Field(default="", description="Date of meeting if applicable (ISO 8601)")
    document_body: str = ""
    sections: list[str] = Field(default_factory=list, description="Ordered list of section headings")
    legal_references: str = Field(default="", description="Applicable statutes, codes, or legal citations")
    action_items: list[str] = Field(default_factory=list, description="Action items or motions recorded")
    full_markdown: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class MunicipalDocOutput(BaseModel):
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
    doc_type: str = "meeting_minutes",
    municipality_name: str = "",
    department: str = "",
    revision_notes: str = "",
    provider: str = "openai",
) -> WriterOutput:
    """Step 1: Generate the municipal document."""
    system = _load_prompt("writer_prompt")
    user_msg = (
        f"Document Type: {doc_type}\n"
        f"Municipality: {municipality_name}\n"
        f"Department: {department}\n"
    )
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nContent / Brief:\n{content}"

    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(WriterOutput, data, agent_name="municipal_doc_writer.writer")


def qa_agent(document: WriterOutput, provider: str = "openai") -> QAResult:
    """Step 2: Validate municipal document quality and compliance."""
    system = _load_prompt("qa_prompt")
    user_msg = f"Municipal document to validate:\n{json.dumps(document.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(QAResult, data, agent_name="municipal_doc_writer.qa")


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    content: str,
    doc_type: str = "meeting_minutes",
    municipality_name: str = "",
    department: str = "",
    provider: str = "openai",
    max_retries: int = 2,
) -> MunicipalDocOutput:
    """Run the full municipal document pipeline: Writer -> QA."""
    print(f"\n[MUN-DOC] Starting pipeline — {doc_type}")
    print(f"  Municipality: {municipality_name}, Department: {department}")
    print(f"  Provider: {provider}")

    # Step 1: Write
    print("\n  [1/2] Generating municipal document...")
    document = writer_agent(content, doc_type, municipality_name, department,
                            provider=provider)
    print(f"  -> Type: {document.doc_type}")
    print(f"  -> Sections: {len(document.sections)}, Action Items: {len(document.action_items)}")

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
                content, doc_type, municipality_name, department,
                revision_notes=qa.revision_notes, provider=provider)

    output = MunicipalDocOutput(
        document=document,
        qa=qa,
        meta={
            "doc_type": doc_type,
            "municipality_name": municipality_name,
            "department": department,
            "provider": provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return output


def save_output(output: MunicipalDocOutput) -> Path:
    """Save pipeline output to JSON and standalone Markdown document."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # JSON
    json_path = OUTPUT_DIR / f"mun_doc_{ts}_{run_id}.json"
    json_path.write_text(
        json.dumps(output.model_dump(), indent=2, default=str),
        encoding="utf-8")

    # Markdown
    d = output.document
    md_lines = [
        f"# {d.doc_type.replace('_', ' ').title()}\n",
        f"**Municipality:** {d.municipality_name}  ",
        f"**Department:** {d.department}  ",
    ]
    if d.meeting_date:
        md_lines.append(f"**Meeting Date:** {d.meeting_date}  ")
    md_lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%B %d, %Y')}\n")
    md_lines.append("---\n")
    md_lines.append(d.document_body + "\n")

    if d.action_items:
        md_lines.append("## Action Items\n")
        for item in d.action_items:
            md_lines.append(f"- {item}")
        md_lines.append("")

    if d.legal_references:
        md_lines.append("## Legal References\n")
        md_lines.append(f"{d.legal_references}\n")

    md_path = OUTPUT_DIR / f"mun_doc_{ts}_{run_id}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\n  [SAVED] {json_path}")
    print(f"  [SAVED] {md_path}")
    return json_path


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Municipal Document Writer Agent")
    parser.add_argument("--text", default="", help="Content brief as text")
    parser.add_argument("--file", default="", help="File containing content brief")
    parser.add_argument("--type", default="meeting_minutes",
                        choices=DOC_TYPES,
                        dest="doc_type")
    parser.add_argument("--municipality", default="", help="Municipality name")
    parser.add_argument("--department", default="", help="Department name")
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
        municipality_name=args.municipality,
        department=args.department,
        provider=args.provider,
        max_retries=args.max_retries,
    )
    save_output(result)
