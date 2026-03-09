"""Document Extraction Agent — extracts structured data from unstructured text.

Pipeline: Extract → QA (with retry)

Usage:
    python -m agents.doc_extract.runner --text "Invoice #1234..."
    python -m agents.doc_extract.runner --file invoice.txt --type invoice
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.llm_client import call_llm

PROMPT_DIR = Path(__file__).resolve().parent


# ── Models ──────────────────────────────────────────────────────────────────

class RawEntity(BaseModel):
    type: str = ""
    value: str = ""
    context: str = ""


class Extraction(BaseModel):
    doc_type: str = "other"
    confidence: float = 0.0
    extracted: dict = Field(default_factory=dict)
    raw_entities: list[RawEntity] = Field(default_factory=list)
    summary: str = ""
    warnings: list[str] = Field(default_factory=list)


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    checks: dict = Field(default_factory=dict)
    missed_entities: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class DocExtractOutput(BaseModel):
    extraction: Extraction
    qa: QAResult
    qa_status: str = "FAIL"
    provider: str = ""
    duration_s: float = 0.0
    timestamp: str = ""


# ── Agents ──────────────────────────────────────────────────────────────────

def extractor_agent(document_text: str, doc_type: str = "auto", provider: str | None = None) -> Extraction:
    """Extract structured data from document text."""
    prompt = (PROMPT_DIR / "extractor_prompt.md").read_text(encoding="utf-8")
    user_msg = json.dumps({"document_text": document_text, "doc_type": doc_type})
    raw = call_llm(prompt, user_msg, provider=provider)
    data = json.loads(raw)
    return Extraction(**data)


def qa_agent(document_text: str, extraction: Extraction, provider: str | None = None) -> QAResult:
    """Verify extraction accuracy."""
    prompt = (PROMPT_DIR / "qa_prompt.md").read_text(encoding="utf-8")
    user_msg = json.dumps({
        "document_text": document_text,
        "extraction": extraction.model_dump(),
    })
    raw = call_llm(prompt, user_msg, provider=provider)
    data = json.loads(raw)
    return QAResult(**data)


# ── Pipeline ────────────────────────────────────────────────────────────────

def run_pipeline(
    document_text: str = "",
    doc_type: str = "auto",
    provider: str | None = None,
    max_retries: int = 1,
) -> Optional[DocExtractOutput]:
    """Run the full document extraction pipeline."""
    start = time.time()

    if not document_text:
        print("[DOC] No document text provided.")
        return None

    for attempt in range(1 + max_retries):
        print(f"[DOC] Extracting (attempt {attempt + 1}, type={doc_type})...")
        extraction = extractor_agent(document_text, doc_type=doc_type, provider=provider)
        print(f"  → Type: {extraction.doc_type} (confidence: {extraction.confidence})")
        print(f"  → {len(extraction.raw_entities)} entities found")

        print("[DOC] QA check...")
        qa = qa_agent(document_text, extraction, provider=provider)
        print(f"  → QA: {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break
        if qa.errors:
            print(f"  → Errors: {', '.join(qa.errors[:3])}")

    elapsed = round(time.time() - start, 2)
    output = DocExtractOutput(
        extraction=extraction,
        qa=qa,
        qa_status=qa.status,
        provider=provider or "default",
        duration_s=elapsed,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    save_output(output)
    return output


def save_output(output: DocExtractOutput):
    """Save extraction output."""
    out_dir = PROJECT_ROOT / "output" / "doc_extract"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filepath = out_dir / f"{output.extraction.doc_type}_{ts}.json"
    filepath.write_text(json.dumps(output.model_dump(), indent=2), encoding="utf-8")
    print(f"[DOC] Saved: {filepath}")


# ── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Document Extraction Agent")
    parser.add_argument("--text", type=str, default="", help="Document text to extract from")
    parser.add_argument("--file", type=str, default="", help="Path to document text file")
    parser.add_argument("--type", type=str, default="auto", help="Document type hint: invoice, contract, resume, report, form, auto")
    parser.add_argument("--provider", type=str, default="", help="LLM provider")
    args = parser.parse_args()

    source = args.text
    if args.file:
        source = Path(args.file).read_text(encoding="utf-8")

    if not source:
        print("Provide --text or --file")
        sys.exit(1)

    result = run_pipeline(document_text=source, doc_type=args.type, provider=args.provider or None)

    if result:
        print(f"\n{'=' * 50}")
        print(f"Type: {result.extraction.doc_type} | QA: {result.qa_status} | Score: {result.qa.score}")
        print(f"Entities: {len(result.extraction.raw_entities)} | Time: {result.duration_s}s")
        print(f"Summary: {result.extraction.summary}")
