"""Market Research Agent — Comprehensive market analysis and competitive intelligence.

2-step pipeline:
    1. Analyst Agent — produces structured research report
    2. QA Agent — validates rigor, honesty, and actionability

Handles: market overviews, competitive analysis, industry trends, SWOT,
         customer analysis, market sizing, feasibility studies.

Usage:
    python -m agents.market_research.runner --text "AI sales automation market" --type market_overview
    python -m agents.market_research.runner --text "Shopify vs WooCommerce" --type competitive_analysis
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
OUTPUT_DIR = PROJECT_ROOT / "output" / "market_research"


class MarketOverview(BaseModel):
    market_size: str = ""
    growth_rate: str = ""
    key_drivers: list[str] = Field(default_factory=list)
    key_barriers: list[str] = Field(default_factory=list)


class Competitor(BaseModel):
    company: str = ""
    positioning: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    estimated_market_share: str = ""


class CompetitiveLandscape(BaseModel):
    market_leaders: list[Competitor] = Field(default_factory=list)
    emerging_players: list[Competitor] = Field(default_factory=list)
    market_gaps: list[str] = Field(default_factory=list)


class CustomerSegment(BaseModel):
    segment: str = ""
    size: str = ""
    pain_points: list[str] = Field(default_factory=list)
    willingness_to_pay: str = ""
    acquisition_channels: list[str] = Field(default_factory=list)


class CustomerAnalysis(BaseModel):
    segments: list[CustomerSegment] = Field(default_factory=list)
    buying_criteria: list[str] = Field(default_factory=list)
    decision_makers: list[str] = Field(default_factory=list)


class Trend(BaseModel):
    trend: str = ""
    impact: str = ""
    timeframe: str = ""
    description: str = ""


class SWOT(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    threats: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    recommendation: str = ""
    rationale: str = ""
    priority: str = ""
    timeframe: str = ""


class AnalystOutput(BaseModel):
    report_type: str = ""
    title: str = ""
    executive_summary: str = ""
    market_overview: MarketOverview = Field(default_factory=MarketOverview)
    competitive_landscape: CompetitiveLandscape = Field(
        default_factory=CompetitiveLandscape)
    customer_analysis: CustomerAnalysis = Field(
        default_factory=CustomerAnalysis)
    trends: list[Trend] = Field(default_factory=list)
    swot: SWOT = Field(default_factory=SWOT)
    recommendations: list[Recommendation] = Field(default_factory=list)
    methodology: str = ""
    limitations: list[str] = Field(default_factory=list)


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class MarketResearchOutput(BaseModel):
    report: AnalystOutput = Field(default_factory=AnalystOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def analyst_agent(topic: str, report_type: str = "market_overview",
                  depth: str = "standard", region: str = "global",
                  revision_notes: str = "",
                  provider: str = "openai") -> AnalystOutput:
    system = _load_prompt("analyst_prompt")
    user_msg = (
        f"Report Type: {report_type}\nDepth: {depth}\nRegion: {region}\n"
    )
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nResearch Topic:\n{topic}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return AnalystOutput(**json.loads(raw))


def qa_agent(report: AnalystOutput, provider: str = "openai") -> QAResult:
    system = _load_prompt("qa_prompt")
    user_msg = f"Report to validate:\n{json.dumps(report.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return QAResult(**json.loads(raw))


def run_pipeline(topic: str, report_type: str = "market_overview",
                 depth: str = "standard", region: str = "global",
                 provider: str = "openai",
                 max_retries: int = 2) -> MarketResearchOutput:
    print(f"\n[MARKET RESEARCH] Starting pipeline — {report_type}")

    print("\n  [1/2] Conducting research...")
    report = analyst_agent(topic, report_type, depth, region, provider=provider)
    print(f"  → \"{report.title}\"")
    print(f"  → {len(report.competitive_landscape.market_leaders)} competitors, "
          f"{len(report.trends)} trends, {len(report.recommendations)} recs")

    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(report, provider)
        print(f"  → {qa.status} (score: {qa.score})")
        if qa.status == "PASS":
            break
        if attempt <= max_retries and qa.revision_notes:
            print("  → Revising report...")
            report = analyst_agent(topic, report_type, depth, region,
                                   qa.revision_notes, provider)

    return MarketResearchOutput(
        report=report, qa=qa,
        meta={"report_type": report_type, "depth": depth, "region": region,
              "provider": provider,
              "timestamp": datetime.now(timezone.utc).isoformat()},
    )


def save_output(output: MarketResearchOutput) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"research_{ts}_{run_id}.json"
    path.write_text(json.dumps(output.model_dump(), indent=2, default=str),
                    encoding="utf-8")
    print(f"\n  [SAVED] {path}")
    return path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Market Research Agent")
    parser.add_argument("--text", default="")
    parser.add_argument("--file", default="")
    parser.add_argument("--type", default="market_overview",
                        choices=["market_overview", "competitive_analysis",
                                 "industry_trends", "customer_analysis",
                                 "swot", "market_sizing", "feasibility"],
                        dest="report_type")
    parser.add_argument("--depth", default="standard",
                        choices=["quick", "standard", "comprehensive"])
    parser.add_argument("--region", default="global")
    parser.add_argument("--provider", default="openai")
    args = parser.parse_args()

    if args.file:
        data = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        data = args.text
    else:
        print("Error: provide --text or --file"); sys.exit(1)

    result = run_pipeline(data, args.report_type, args.depth, args.region,
                          args.provider)
    save_output(result)
