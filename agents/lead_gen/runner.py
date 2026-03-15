"""Lead Generation Agent — Research, score, and qualify B2B prospects.

3-step pipeline:
    1. Research Agent — identifies companies matching ICP criteria
    2. Scorer Agent — scores and segments leads by outreach priority
    3. QA Agent — validates completeness, accuracy, and actionability

Usage:
    python -m agents.lead_gen.runner --industry "SaaS" --icp "mid-market scaling sales"
    python -m agents.lead_gen.runner --industry "ecommerce" --count 20 --provider anthropic
    python -m agents.lead_gen.runner --industry "healthcare" --geo "US" --size "50-500"
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

from utils.super_agent import make_bridge  # noqa: E402
call_llm = make_bridge("lead_gen")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "lead_gen"


# ── Pydantic Models ────────────────────────────────────────────

class Lead(BaseModel):
    company_name: str
    industry: str
    website: str = ""
    estimated_size: str = ""
    location: str = ""
    decision_maker_title: str = ""
    pain_points: list[str] = Field(default_factory=list)
    buying_signals: list[str] = Field(default_factory=list)
    relevance_score: int = 0
    outreach_angle: str = ""
    sources: list[str] = Field(default_factory=list)


class ResearchOutput(BaseModel):
    leads: list[Lead] = Field(default_factory=list)
    icp_summary: str = ""
    total_addressable: int = 0
    recommended_priority: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    icp_fit: int = 0
    buying_signals: int = 0
    budget_likelihood: int = 0
    timing: int = 0
    accessibility: int = 0


class ScoredLead(BaseModel):
    company_name: str
    final_score: int = 0
    tier: str = "cold"
    score_breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    recommended_action: str = ""
    recommended_channel: str = ""
    recommended_offer: str = ""
    notes: str = ""


class ScoringOutput(BaseModel):
    scored_leads: list[ScoredLead] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    batch_recommendation: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class LeadGenOutput(BaseModel):
    research: ResearchOutput = Field(default_factory=ResearchOutput)
    scoring: ScoringOutput = Field(default_factory=ScoringOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


# ── Agent Functions ─────────────────────────────────────────────

def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def research_agent(
    industry: str,
    icp: str,
    geo: str = "global",
    company_size: str = "",
    count: int = 10,
    context: str = "",
    provider: str = "openai",
) -> ResearchOutput:
    """Step 1: Research and identify qualified leads."""
    system = _load_prompt("researcher_prompt")
    user_msg = (
        f"Industry: {industry}\n"
        f"ICP: {icp}\n"
        f"Geography: {geo}\n"
        f"Company Size: {company_size}\n"
        f"Count: {count}\n"
        f"Additional Context: {context}"
    )
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return ResearchOutput(**json.loads(raw))


def scorer_agent(
    research: ResearchOutput,
    budget_tier: str = "growth",
    provider: str = "openai",
) -> ScoringOutput:
    """Step 2: Score, rank, and segment leads."""
    system = _load_prompt("scorer_prompt")
    user_msg = (
        f"Leads to score:\n{json.dumps([l.model_dump() for l in research.leads], indent=2)}\n\n"
        f"ICP Summary: {research.icp_summary}\n"
        f"Budget Tier Target: {budget_tier}"
    )
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return ScoringOutput(**json.loads(raw))


def qa_agent(
    research: ResearchOutput,
    scoring: ScoringOutput,
    provider: str = "openai",
) -> QAResult:
    """Step 3: Validate lead quality and scoring integrity."""
    system = _load_prompt("qa_prompt")
    user_msg = (
        f"Research Output:\n{json.dumps(research.model_dump(), indent=2)}\n\n"
        f"Scoring Output:\n{json.dumps(scoring.model_dump(), indent=2)}"
    )
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return QAResult(**json.loads(raw))


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    industry: str,
    icp: str,
    geo: str = "global",
    company_size: str = "",
    count: int = 10,
    context: str = "",
    budget_tier: str = "growth",
    provider: str = "openai",
    max_retries: int = 2,
) -> LeadGenOutput:
    """Run the full lead generation pipeline: Research → Score → QA."""
    print(f"\n[LEAD_GEN] Starting pipeline — {industry} / {icp}")
    print(f"  Provider: {provider} | Count: {count} | Geo: {geo}")

    # Step 1: Research
    print("\n  [1/3] Researching leads...")
    research = research_agent(industry, icp, geo, company_size,
                              count, context, provider)
    print(f"  → Found {len(research.leads)} leads")

    # Step 2: Score
    print("\n  [2/3] Scoring and ranking...")
    scoring = scorer_agent(research, budget_tier, provider)
    hot = sum(1 for s in scoring.scored_leads if s.tier == "hot")
    warm = sum(1 for s in scoring.scored_leads if s.tier == "warm")
    print(f"  → {hot} hot, {warm} warm, {len(scoring.scored_leads) - hot - warm} cold")

    # Step 3: QA (with retries)
    for attempt in range(1, max_retries + 2):
        print(f"\n  [3/3] QA verification (attempt {attempt})...")
        qa = qa_agent(research, scoring, provider)
        print(f"  → {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print(f"  → Retrying with revision notes...")
            revision_context = f"\n\nPREVIOUS QA FEEDBACK:\n{qa.revision_notes}\nFix the issues above."
            research = research_agent(industry, icp, geo, company_size,
                                      count, context + revision_context, provider)
            scoring = scorer_agent(research, budget_tier, provider)

    output = LeadGenOutput(
        research=research,
        scoring=scoring,
        qa=qa,
        meta={
            "industry": industry,
            "icp": icp,
            "geo": geo,
            "provider": provider,
            "count": count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return output


def save_output(output: LeadGenOutput) -> Path:
    """Save pipeline output to JSON file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"leads_{ts}_{run_id}.json"
    path.write_text(json.dumps(output.model_dump(), indent=2, default=str),
                    encoding="utf-8")
    print(f"\n  [SAVED] {path}")
    return path


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Lead Generation Agent")
    parser.add_argument("--industry", required=True, help="Target industry")
    parser.add_argument("--icp", default="", help="Ideal customer profile description")
    parser.add_argument("--geo", default="global", help="Geographic focus")
    parser.add_argument("--size", default="", help="Company size range")
    parser.add_argument("--count", type=int, default=10, help="Number of leads")
    parser.add_argument("--tier", default="growth", help="Budget tier target")
    parser.add_argument("--provider", default="openai", help="LLM provider")
    args = parser.parse_args()

    result = run_pipeline(
        industry=args.industry,
        icp=args.icp or f"Companies in {args.industry} needing AI automation",
        geo=args.geo,
        company_size=args.size,
        count=args.count,
        budget_tier=args.tier,
        provider=args.provider,
    )
    save_output(result)
