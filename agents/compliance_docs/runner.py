"""Compliance Document Generator Agent — handbooks, policies, ToS, safety docs, SOPs.

2-step pipeline:
    1. Writer Agent — produces structured compliance documentation
    2. QA Agent — validates legal completeness, jurisdiction accuracy, plain language

Handles: employee_handbook, privacy_policy, terms_of_service, safety_manual,
         sop, acceptable_use, data_retention, incident_response.

Usage:
    python -m agents.compliance_docs.runner --text "50-person SaaS company in California..." --type privacy_policy
    python -m agents.compliance_docs.runner --file company_info.txt --type employee_handbook --company "Acme Corp" --jurisdiction us_federal
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
call_llm = make_bridge("compliance_docs")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "compliance_docs"


class SubSection(BaseModel):
    number: str = ""
    heading: str = ""
    content: str = ""


class PolicySection(BaseModel):
    section_number: str = ""
    heading: str = ""
    content: str = ""
    subsections: list[SubSection] = Field(default_factory=list)
    effective_date: str = ""
    review_date: str = ""


class Definition(BaseModel):
    term: str = ""
    definition: str = ""


class LegalDisclaimer(BaseModel):
    text: str = ""
    jurisdiction: str = ""


class AcknowledgmentBlock(BaseModel):
    text: str = ""
    signature_line: bool = False
    date_line: bool = False


class WriterOutput(BaseModel):
    doc_type: str = ""
    title: str = ""
    company_name: str = ""
    effective_date: str = ""
    version: str = ""
    jurisdiction: str = ""
    definitions: list[Definition] = Field(default_factory=list)
    sections: list[PolicySection] = Field(default_factory=list)
    disclaimers: list[LegalDisclaimer] = Field(default_factory=list)
    acknowledgment: AcknowledgmentBlock = Field(default_factory=AcknowledgmentBlock)
    revision_history: list[dict] = Field(default_factory=list)
    compliance_frameworks: list[str] = Field(default_factory=list)
    full_markdown: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class ComplianceOutput(BaseModel):
    docs: WriterOutput = Field(default_factory=WriterOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def writer_agent(content: str, doc_type: str = "employee_handbook",
                 company: str = "", jurisdiction: str = "us_federal",
                 framework: str = "", revision_notes: str = "",
                 provider: str = "openai") -> WriterOutput:
    system = _load_prompt("writer_prompt")
    user_msg = (
        f"Doc Type: {doc_type}\nCompany: {company or 'Not specified'}\n"
        f"Jurisdiction: {jurisdiction}\n"
        f"Compliance Frameworks: {framework or 'Auto-detect'}\n"
    )
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nSource Material:\n{content}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(WriterOutput, data, agent_name="compliance_docs.writer")


def qa_agent(docs: WriterOutput, provider: str = "openai") -> QAResult:
    system = _load_prompt("qa_prompt")
    user_msg = f"Compliance document to validate:\n{json.dumps(docs.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(QAResult, data, agent_name="compliance_docs.qa")


def run_pipeline(content: str, doc_type: str = "employee_handbook",
                 company: str = "", jurisdiction: str = "us_federal",
                 framework: str = "", provider: str = "openai",
                 max_retries: int = 2) -> ComplianceOutput:
    print(f"\n[COMPLIANCE DOCS] Starting pipeline — {doc_type}")

    print("\n  [1/2] Generating compliance document...")
    docs = writer_agent(content, doc_type, company, jurisdiction, framework,
                        provider=provider)
    print(f"  → {docs.title}")
    print(f"  → {len(docs.sections)} sections, "
          f"{len(docs.definitions)} definitions, "
          f"{len(docs.disclaimers)} disclaimers")

    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(docs, provider)
        print(f"  → {qa.status} (score: {qa.score})")
        if qa.status == "PASS":
            break
        if attempt <= max_retries and qa.revision_notes:
            print("  → Revising document...")
            docs = writer_agent(content, doc_type, company, jurisdiction,
                                framework, qa.revision_notes, provider)

    return ComplianceOutput(
        docs=docs, qa=qa,
        meta={"doc_type": doc_type, "company": company,
              "jurisdiction": jurisdiction, "provider": provider,
              "timestamp": datetime.now(timezone.utc).isoformat()},
    )


def save_output(output: ComplianceOutput) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    # Save JSON
    json_path = OUTPUT_DIR / f"compliance_{ts}_{run_id}.json"
    json_path.write_text(
        json.dumps(output.model_dump(), indent=2, default=str),
        encoding="utf-8")
    # Also save rendered Markdown if available
    if output.docs.full_markdown:
        md_path = OUTPUT_DIR / f"compliance_{ts}_{run_id}.md"
        md_path.write_text(output.docs.full_markdown, encoding="utf-8")
        print(f"  [SAVED] {md_path}")
    print(f"  [SAVED] {json_path}")
    return json_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Compliance Document Generator Agent")
    parser.add_argument("--text", default="")
    parser.add_argument("--file", default="")
    parser.add_argument("--type", default="employee_handbook",
                        choices=["employee_handbook", "privacy_policy",
                                 "terms_of_service", "safety_manual",
                                 "sop", "acceptable_use",
                                 "data_retention", "incident_response"],
                        dest="doc_type")
    parser.add_argument("--company", default="")
    parser.add_argument("--jurisdiction", default="us_federal",
                        choices=["us_federal", "california", "new_york",
                                 "texas", "florida", "illinois",
                                 "eu_gdpr", "uk", "canada", "australia"])
    parser.add_argument("--framework", default="")
    parser.add_argument("--provider", default="openai")
    args = parser.parse_args()

    if args.file:
        data = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        data = args.text
    else:
        print("Error: provide --text or --file"); sys.exit(1)

    result = run_pipeline(data, args.doc_type, args.company,
                          args.jurisdiction, args.framework, args.provider)
    save_output(result)
