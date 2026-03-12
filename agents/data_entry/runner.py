"""Data Entry & Processing Agent — Clean, normalize, and structure raw data.

2-step pipeline:
    1. Processor Agent — cleans, normalizes, deduplicates, and structures data
    2. QA Agent — validates accuracy, completeness, and format compliance

Handles: contact lists, form submissions, CSV cleanup, email dumps,
         product catalogs, invoice data, survey responses, CRM imports.

Usage:
    python -m agents.data_entry.runner --file data.csv --format json --task clean
    python -m agents.data_entry.runner --text "John Smith, john@acme.com, 5550123" --format csv
    python -m agents.data_entry.runner --file contacts.txt --task deduplicate
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.llm_client import call_llm  # noqa: E402

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "data_entry"


# ── Pydantic Models ────────────────────────────────────────────

class DropReason(BaseModel):
    record_index: int = 0
    reason: str = ""


class SchemaDetected(BaseModel):
    columns: list[str] = Field(default_factory=list)
    types: list[str] = Field(default_factory=list)


class DataQualityReport(BaseModel):
    completeness: float = 0.0
    duplicates_found: int = 0
    format_errors_fixed: int = 0
    fields_normalized: list[str] = Field(default_factory=list)


class ProcessedRecord(BaseModel):
    row: int = 0
    fields: dict = Field(default_factory=dict)


class ProcessorOutput(BaseModel):
    task_type: str = ""
    records_input: int = 0
    records_output: int = 0
    records_dropped: int = 0
    drop_reasons: list[DropReason] = Field(default_factory=list)
    processed_data: list[ProcessedRecord] = Field(default_factory=list)
    schema_detected: SchemaDetected = Field(default_factory=SchemaDetected)
    data_quality_report: DataQualityReport = Field(default_factory=DataQualityReport)
    export_ready: bool = False


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class DataEntryOutput(BaseModel):
    processed: ProcessorOutput = Field(default_factory=ProcessorOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


# ── Agent Functions ─────────────────────────────────────────────

def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def processor_agent(
    raw_data: str,
    output_format: str = "json",
    schema: str = "",
    task_type: str = "clean",
    rules: str = "",
    provider: str = "openai",
) -> ProcessorOutput:
    """Step 1: Process and structure raw data."""
    system = _load_prompt("processor_prompt")
    user_msg = (
        f"Task Type: {task_type}\n"
        f"Output Format: {output_format}\n"
        f"Schema: {schema or 'auto-detect'}\n"
        f"Rules: {rules or 'Standard normalization (emails, phones, names, dates)'}\n\n"
        f"Raw Data:\n{raw_data}"
    )
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return ProcessorOutput(**json.loads(raw))


def qa_agent(processed: ProcessorOutput, provider: str = "openai") -> QAResult:
    """Step 2: Validate processing accuracy."""
    system = _load_prompt("qa_prompt")
    user_msg = f"Processed data to validate:\n{json.dumps(processed.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return QAResult(**json.loads(raw))


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    raw_data: str,
    output_format: str = "json",
    schema: str = "",
    task_type: str = "clean",
    rules: str = "",
    provider: str = "openai",
    max_retries: int = 2,
) -> DataEntryOutput:
    """Run the full data entry pipeline: Process → QA."""
    print(f"\n[DATA_ENTRY] Starting pipeline — {task_type}")
    print(f"  Format: {output_format} | Provider: {provider}")

    # Step 1: Process
    print("\n  [1/2] Processing data...")
    processed = processor_agent(raw_data, output_format, schema,
                                task_type, rules, provider)
    print(f"  → {processed.records_input} in → {processed.records_output} out "
          f"({processed.records_dropped} dropped)")

    # Step 2: QA (with retries)
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(processed, provider)
        print(f"  → {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print(f"  → Reprocessing with revision notes...")
            processed = processor_agent(
                raw_data, output_format, schema, task_type,
                rules + f"\n\nQA REVISION:\n{qa.revision_notes}", provider)

    output = DataEntryOutput(
        processed=processed,
        qa=qa,
        meta={
            "task_type": task_type,
            "output_format": output_format,
            "provider": provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return output


def save_output(output: DataEntryOutput) -> Path:
    """Save pipeline output — JSON + CSV export if applicable."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Full JSON output
    json_path = OUTPUT_DIR / f"data_{ts}_{run_id}.json"
    json_path.write_text(json.dumps(output.model_dump(), indent=2, default=str),
                         encoding="utf-8")

    # CSV export
    if output.processed.processed_data and output.processed.export_ready:
        csv_path = OUTPUT_DIR / f"data_{ts}_{run_id}.csv"
        records = output.processed.processed_data
        if records:
            headers = list(records[0].fields.keys())
            lines = [",".join(headers)]
            for rec in records:
                row = []
                for h in headers:
                    val = str(rec.fields.get(h, ""))
                    if "," in val or '"' in val:
                        val = f'"{val}"'
                    row.append(val)
                lines.append(",".join(row))
            csv_path.write_text("\n".join(lines), encoding="utf-8")
            print(f"  [SAVED] {csv_path}")

    print(f"  [SAVED] {json_path}")
    return json_path


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Data Entry Agent")
    parser.add_argument("--text", default="", help="Raw data as text")
    parser.add_argument("--file", default="", help="File containing raw data")
    parser.add_argument("--format", default="json", dest="output_format",
                        choices=["csv", "json", "spreadsheet_rows", "database_records",
                                 "contact_list", "product_catalog"])
    parser.add_argument("--task", default="clean",
                        choices=["categorize", "clean", "transform", "merge",
                                 "deduplicate", "validate", "enrich"])
    parser.add_argument("--schema", default="", help="Column definitions")
    parser.add_argument("--provider", default="openai", help="LLM provider")
    args = parser.parse_args()

    if args.file:
        raw = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        raw = args.text
    else:
        print("Error: provide --text or --file")
        sys.exit(1)

    result = run_pipeline(
        raw_data=raw,
        output_format=args.output_format,
        task_type=args.task,
        schema=args.schema,
        provider=args.provider,
    )
    save_output(result)
