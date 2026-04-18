"""Data Reporter Agent — Transform raw data into narrative business reports.

2-step pipeline:
    1. Writer Agent — produces narrative report with insights, trends, comparisons
    2. QA Agent — validates data consistency, claims, and actionability

The middleman between spreadsheets and executives.

Usage:
    python -m agents.data_reporter.runner --text "Revenue Q1: $2.3M..." --type quarterly_review
    python -m agents.data_reporter.runner --file metrics.txt --type monthly_performance --period "Q1 2026"
    python -m agents.data_reporter.runner --file sales_data.txt --type sales_pipeline --audience executive
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.dl_agent import make_bridge, safe_validate  # noqa: E402
call_llm = make_bridge("data_reporter")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "data_reporter"


# ── Pydantic Models ────────────────────────────────────────────

class DataSummary(BaseModel):
    total_records: int = 0
    date_range: str = ""
    key_metrics: dict[str, float] = Field(default_factory=dict)


class Insight(BaseModel):
    category: str = ""
    finding: str = ""
    significance: str = ""  # high / medium / low
    supporting_data: str = ""
    recommendation: str = ""


class TrendAnalysis(BaseModel):
    metric_name: str = ""
    direction: str = ""  # up / down / flat
    magnitude: str = ""
    period: str = ""
    context: str = ""


class Comparison(BaseModel):
    metric: str = ""
    current_value: float = 0.0
    previous_value: float = 0.0
    change_pct: float = 0.0
    interpretation: str = ""


class Section(BaseModel):
    heading: str = ""
    narrative: str = ""
    data_points: list[dict] = Field(default_factory=list)
    insights: list[Insight] = Field(default_factory=list)


class WriterOutput(BaseModel):
    report_type: str = ""  # monthly_performance / quarterly_review / client_report / board_update / marketing_report / financial_summary / sales_pipeline / custom
    title: str = ""
    period: str = ""
    prepared_for: str = ""
    executive_summary: str = ""
    sections: list[Section] = Field(default_factory=list)
    key_findings: list[Insight] = Field(default_factory=list)
    trends: list[TrendAnalysis] = Field(default_factory=list)
    comparisons: list[Comparison] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    methodology_notes: str = ""
    full_markdown: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class ReportOutput(BaseModel):
    report: WriterOutput = Field(default_factory=WriterOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


# ── Agent Functions ─────────────────────────────────────────────

def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def writer_agent(raw_data: str, report_type: str = "monthly_performance",
                 period: str = "", audience: str = "executive",
                 revision_notes: str = "",
                 provider: str = "openai") -> WriterOutput:
    """Step 1: Transform raw data into narrative report."""
    system = _load_prompt("writer_prompt")
    user_msg = (
        f"Report Type: {report_type}\n"
        f"Period: {period or 'Extract from data'}\n"
        f"Audience: {audience}\n"
    )
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nRaw Data:\n{raw_data}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(WriterOutput, data, agent_name="data_reporter.writer")


def qa_agent(report: WriterOutput, provider: str = "openai") -> QAResult:
    """Step 2: Validate report accuracy and consistency."""
    system = _load_prompt("qa_prompt")
    user_msg = f"Report to validate:\n{json.dumps(report.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(QAResult, data, agent_name="data_reporter.qa")


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(raw_data: str, report_type: str = "monthly_performance",
                 period: str = "", audience: str = "executive",
                 provider: str = "openai",
                 max_retries: int = 2) -> ReportOutput:
    """Run the full data reporter pipeline: Writer -> QA."""
    print(f"\n[DATA_REPORTER] Starting pipeline — {report_type}")
    print(f"  Period: {period or 'auto-detect'} | Audience: {audience} | Provider: {provider}")

    # Step 1: Generate report
    print("\n  [1/2] Generating narrative report...")
    report = writer_agent(raw_data, report_type, period, audience,
                          provider=provider)
    print(f"  → Title: {report.title}")
    print(f"  → {len(report.sections)} sections, "
          f"{len(report.key_findings)} key findings, "
          f"{len(report.trends)} trends")

    # Step 2: QA (with retries)
    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(report, provider)
        print(f"  → {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print("  → Revising report...")
            report = writer_agent(raw_data, report_type, period, audience,
                                  qa.revision_notes, provider)

    return ReportOutput(
        report=report, qa=qa,
        meta={"report_type": report_type, "period": period,
              "audience": audience, "provider": provider,
              "timestamp": datetime.now(timezone.utc).isoformat()},
    )


def save_output(output: ReportOutput) -> Path:
    """Save pipeline output to JSON file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"report_{ts}_{run_id}.json"
    path.write_text(json.dumps(output.model_dump(), indent=2, default=str),
                    encoding="utf-8")
    print(f"\n  [SAVED] {path}")
    return path


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Data Reporter Agent")
    parser.add_argument("--text", default="")
    parser.add_argument("--file", default="")
    parser.add_argument("--type", default="monthly_performance",
                        choices=["monthly_performance", "quarterly_review",
                                 "client_report", "board_update",
                                 "marketing_report", "financial_summary",
                                 "sales_pipeline", "custom"],
                        dest="report_type")
    parser.add_argument("--period", default="", help="e.g. 'Q1 2026'")
    parser.add_argument("--audience", default="executive",
                        choices=["executive", "operational", "client",
                                 "investor"])
    parser.add_argument("--provider", default="openai")
    args = parser.parse_args()

    if args.file:
        data = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        data = args.text
    else:
        print("Error: provide --text or --file"); sys.exit(1)

    result = run_pipeline(data, args.report_type, args.period, args.audience,
                          args.provider)
    save_output(result)
