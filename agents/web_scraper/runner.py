"""Web Scraper Agent — Extract structured data from web page content.

2-step pipeline:
    1. Extractor Agent — parses page content and extracts structured records
    2. QA Agent — validates accuracy, completeness, and data quality

Handles: contact directories, product catalogs, job boards, review sites,
         company directories, pricing pages, article indexes, event listings.

Usage:
    python -m agents.web_scraper.runner --file page.html --target contacts
    python -m agents.web_scraper.runner --text "..." --target products --url "https://example.com"
    python -m agents.web_scraper.runner --file directory.html --target company_info
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.super_agent import make_bridge  # noqa: E402
call_llm = make_bridge("web_scraper")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "web_scraper"


# ── Pydantic Models ────────────────────────────────────────────

class PaginationInfo(BaseModel):
    current_page: int = 1
    total_pages: int = 1
    next_page_url: str = ""


class DataQuality(BaseModel):
    complete_records: int = 0
    partial_records: int = 0
    fields_with_highest_fill_rate: list[str] = Field(default_factory=list)
    fields_with_lowest_fill_rate: list[str] = Field(default_factory=list)


class ExtractorOutput(BaseModel):
    source_url: str = ""
    extraction_target: str = ""
    page_title: str = ""
    records_extracted: int = 0
    data: list[dict] = Field(default_factory=list)
    schema_detected: list[str] = Field(default_factory=list)
    extraction_confidence: int = 0
    pagination_info: PaginationInfo = Field(default_factory=PaginationInfo)
    data_quality: DataQuality = Field(default_factory=DataQuality)


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class WebScraperOutput(BaseModel):
    extracted: ExtractorOutput = Field(default_factory=ExtractorOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


# ── Agent Functions ─────────────────────────────────────────────

def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def extractor_agent(
    page_content: str,
    source_url: str = "",
    extraction_target: str = "company_info",
    schema: str = "",
    provider: str = "openai",
) -> ExtractorOutput:
    """Step 1: Extract structured data from page content."""
    system = _load_prompt("extractor_prompt")
    user_msg = (
        f"Source URL: {source_url}\n"
        f"Extraction Target: {extraction_target}\n"
        f"Schema: {schema or 'auto-detect'}\n\n"
        f"Page Content:\n{page_content[:15000]}"  # Truncate very large pages
    )
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return ExtractorOutput(**json.loads(raw))


def qa_agent(extracted: ExtractorOutput, provider: str = "openai") -> QAResult:
    """Step 2: Validate extraction quality."""
    system = _load_prompt("qa_prompt")
    user_msg = f"Extracted data to validate:\n{json.dumps(extracted.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return QAResult(**json.loads(raw))


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    page_content: str,
    source_url: str = "",
    extraction_target: str = "company_info",
    schema: str = "",
    provider: str = "openai",
    max_retries: int = 2,
) -> WebScraperOutput:
    """Run the full web scraper pipeline: Extract → QA."""
    print(f"\n[WEB_SCRAPER] Starting pipeline — {extraction_target}")
    print(f"  URL: {source_url or 'N/A'} | Provider: {provider}")

    # Step 1: Extract
    print("\n  [1/2] Extracting data...")
    extracted = extractor_agent(page_content, source_url, extraction_target,
                                schema, provider)
    print(f"  → {extracted.records_extracted} records (confidence: {extracted.extraction_confidence}%)")

    # Step 2: QA (with retries)
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(extracted, provider)
        print(f"  → {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print(f"  → Re-extracting with revision notes...")
            extracted = extractor_agent(
                page_content, source_url, extraction_target,
                schema + f"\n\nQA FEEDBACK:\n{qa.revision_notes}", provider)

    output = WebScraperOutput(
        extracted=extracted,
        qa=qa,
        meta={
            "source_url": source_url,
            "extraction_target": extraction_target,
            "provider": provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return output


def save_output(output: WebScraperOutput) -> Path:
    """Save pipeline output to JSON file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"scrape_{ts}_{run_id}.json"
    path.write_text(json.dumps(output.model_dump(), indent=2, default=str),
                    encoding="utf-8")
    print(f"\n  [SAVED] {path}")
    return path


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Web Scraper Agent")
    parser.add_argument("--text", default="", help="Page content as text")
    parser.add_argument("--file", default="", help="File containing page content")
    parser.add_argument("--url", default="", help="Source URL for attribution")
    parser.add_argument("--target", default="company_info",
                        choices=["contacts", "products", "job_listings", "reviews",
                                 "company_info", "pricing", "directory", "articles", "events"])
    parser.add_argument("--schema", default="", help="Expected output fields")
    parser.add_argument("--provider", default="openai", help="LLM provider")
    args = parser.parse_args()

    if args.file:
        content = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        content = args.text
    else:
        print("Error: provide --text or --file")
        sys.exit(1)

    result = run_pipeline(
        page_content=content,
        source_url=args.url,
        extraction_target=args.target,
        schema=args.schema,
        provider=args.provider,
    )
    save_output(result)
