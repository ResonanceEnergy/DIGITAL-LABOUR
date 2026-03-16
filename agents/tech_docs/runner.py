"""Technical Documentation Writer Agent — API docs, guides, READMEs, runbooks.

2-step pipeline:
    1. Writer Agent — produces structured technical documentation
    2. QA Agent — validates accuracy, completeness, runnability

Handles: api_reference, user_guide, readme, how_to, tutorial, architecture,
         changelog, runbook, sdk_guide.

Usage:
    python -m agents.tech_docs.runner --text "FastAPI app with /users endpoint..." --type api_reference
    python -m agents.tech_docs.runner --file codebase.txt --type readme --audience developers
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.dl_agent import make_bridge  # noqa: E402
call_llm = make_bridge("tech_docs")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "tech_docs"


class CodeExample(BaseModel):
    language: str = ""
    label: str = ""
    code: str = ""
    output: str = ""


class Section(BaseModel):
    heading: str = ""
    content: str = ""
    code_examples: list[CodeExample] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class Parameter(BaseModel):
    name: str = ""
    type: str = ""
    required: bool = False
    description: str = ""


class APIEndpoint(BaseModel):
    method: str = ""
    path: str = ""
    description: str = ""
    parameters: list[Parameter] = Field(default_factory=list)
    request_body: dict = Field(default_factory=dict)
    response_200: dict = Field(default_factory=dict)
    response_errors: list[dict] = Field(default_factory=list)


class EnvVar(BaseModel):
    name: str = ""
    description: str = ""
    required: bool = False
    example: str = ""


class Configuration(BaseModel):
    environment_variables: list[EnvVar] = Field(default_factory=list)
    config_file_example: str = ""


class TroubleshootItem(BaseModel):
    problem: str = ""
    cause: str = ""
    solution: str = ""


class GlossaryItem(BaseModel):
    term: str = ""
    definition: str = ""


class ChangelogEntry(BaseModel):
    version: str = ""
    date: str = ""
    changes: list[str] = Field(default_factory=list)


class WriterOutput(BaseModel):
    doc_type: str = ""
    title: str = ""
    overview: str = ""
    prerequisites: list[str] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    api_endpoints: list[APIEndpoint] = Field(default_factory=list)
    configuration: Configuration = Field(default_factory=Configuration)
    troubleshooting: list[TroubleshootItem] = Field(default_factory=list)
    glossary: list[GlossaryItem] = Field(default_factory=list)
    changelog_entries: list[ChangelogEntry] = Field(default_factory=list)
    full_markdown: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class TechDocsOutput(BaseModel):
    docs: WriterOutput = Field(default_factory=WriterOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def writer_agent(content: str, doc_type: str = "api_reference",
                 audience: str = "developers", framework: str = "",
                 revision_notes: str = "",
                 provider: str = "openai") -> WriterOutput:
    system = _load_prompt("writer_prompt")
    user_msg = (
        f"Doc Type: {doc_type}\nAudience: {audience}\n"
        f"Framework: {framework or 'Auto-detect'}\n"
    )
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nSource Material:\n{content}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return WriterOutput(**json.loads(raw))


def qa_agent(docs: WriterOutput, provider: str = "openai") -> QAResult:
    system = _load_prompt("qa_prompt")
    user_msg = f"Documentation to validate:\n{json.dumps(docs.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return QAResult(**json.loads(raw))


def run_pipeline(content: str, doc_type: str = "api_reference",
                 audience: str = "developers", framework: str = "",
                 provider: str = "openai",
                 max_retries: int = 2) -> TechDocsOutput:
    print(f"\n[TECH DOCS] Starting pipeline — {doc_type}")

    print("\n  [1/2] Generating documentation...")
    docs = writer_agent(content, doc_type, audience, framework,
                        provider=provider)
    print(f"  → {docs.title}")
    print(f"  → {len(docs.sections)} sections, "
          f"{len(docs.api_endpoints)} endpoints, "
          f"{len(docs.troubleshooting)} troubleshoot items")

    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(docs, provider)
        print(f"  → {qa.status} (score: {qa.score})")
        if qa.status == "PASS":
            break
        if attempt <= max_retries and qa.revision_notes:
            print("  → Revising documentation...")
            docs = writer_agent(content, doc_type, audience, framework,
                                qa.revision_notes, provider)

    return TechDocsOutput(
        docs=docs, qa=qa,
        meta={"doc_type": doc_type, "audience": audience,
              "provider": provider,
              "timestamp": datetime.now(timezone.utc).isoformat()},
    )


def save_output(output: TechDocsOutput) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    # Save JSON
    json_path = OUTPUT_DIR / f"techdocs_{ts}_{run_id}.json"
    json_path.write_text(
        json.dumps(output.model_dump(), indent=2, default=str),
        encoding="utf-8")
    # Also save rendered Markdown if available
    if output.docs.full_markdown:
        md_path = OUTPUT_DIR / f"techdocs_{ts}_{run_id}.md"
        md_path.write_text(output.docs.full_markdown, encoding="utf-8")
        print(f"  [SAVED] {md_path}")
    print(f"  [SAVED] {json_path}")
    return json_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Technical Documentation Writer Agent")
    parser.add_argument("--text", default="")
    parser.add_argument("--file", default="")
    parser.add_argument("--type", default="api_reference",
                        choices=["api_reference", "user_guide", "readme",
                                 "how_to", "tutorial", "architecture",
                                 "changelog", "runbook", "sdk_guide"],
                        dest="doc_type")
    parser.add_argument("--audience", default="developers",
                        choices=["developers", "devops", "end_users",
                                 "stakeholders", "mixed"])
    parser.add_argument("--framework", default="")
    parser.add_argument("--provider", default="openai")
    args = parser.parse_args()

    if args.file:
        data = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        data = args.text
    else:
        print("Error: provide --text or --file"); sys.exit(1)

    result = run_pipeline(data, args.doc_type, args.audience, args.framework,
                          args.provider)
    save_output(result)
