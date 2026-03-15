"""Business Plan Writer Agent — Investor-ready business plans from concepts.

2-step pipeline:
    1. Planner Agent — produces full business plan with financials
    2. QA Agent — validates completeness, financial rigor, realism

Handles: startup plans, expansion plans, investor pitches, loan applications,
         lean canvas, internal strategic plans.

Usage:
    python -m agents.business_plan.runner --text "AI automation agency..." --type startup
    python -m agents.business_plan.runner --file idea.txt --type investor_pitch --funding "250000"
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
call_llm = make_bridge("business_plan")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "business_plans"


class CompanyDescription(BaseModel):
    mission: str = ""
    vision: str = ""
    values: list[str] = Field(default_factory=list)
    legal_structure: str = ""
    stage: str = ""


class ProblemSolution(BaseModel):
    problem: str = ""
    current_alternatives: list[str] = Field(default_factory=list)
    solution: str = ""
    unique_value_proposition: str = ""


class MarketAnalysis(BaseModel):
    tam: str = ""
    sam: str = ""
    som: str = ""
    target_customer: str = ""
    market_trends: list[str] = Field(default_factory=list)


class RevenueStream(BaseModel):
    stream: str = ""
    pricing: str = ""
    unit_economics: str = ""


class CostStructure(BaseModel):
    fixed_costs: list[str] = Field(default_factory=list)
    variable_costs: list[str] = Field(default_factory=list)


class BusinessModel(BaseModel):
    revenue_streams: list[RevenueStream] = Field(default_factory=list)
    cost_structure: CostStructure = Field(default_factory=CostStructure)
    margins: str = ""


class TeamMember(BaseModel):
    role: str = ""
    status: str = ""
    responsibility: str = ""


class Milestone(BaseModel):
    milestone: str = ""
    target_date: str = ""
    kpi: str = ""


class Operations(BaseModel):
    team: list[TeamMember] = Field(default_factory=list)
    technology: str = ""
    key_partnerships: list[str] = Field(default_factory=list)
    milestones: list[Milestone] = Field(default_factory=list)


class YearProjection(BaseModel):
    revenue: float = 0
    expenses: float = 0
    net: float = 0


class FinancialProjections(BaseModel):
    year_1: YearProjection = Field(default_factory=YearProjection)
    year_2: YearProjection = Field(default_factory=YearProjection)
    year_3: YearProjection = Field(default_factory=YearProjection)
    break_even: str = ""
    key_assumptions: list[str] = Field(default_factory=list)


class Funding(BaseModel):
    amount_sought: str = ""
    use_of_funds: dict = Field(default_factory=dict)
    expected_roi: str = ""


class Risk(BaseModel):
    risk: str = ""
    probability: str = ""
    impact: str = ""
    mitigation: str = ""


class PlannerOutput(BaseModel):
    plan_type: str = ""
    company_name: str = ""
    executive_summary: str = ""
    company_description: CompanyDescription = Field(
        default_factory=CompanyDescription)
    problem_and_solution: ProblemSolution = Field(
        default_factory=ProblemSolution)
    market_analysis: MarketAnalysis = Field(default_factory=MarketAnalysis)
    business_model: BusinessModel = Field(default_factory=BusinessModel)
    go_to_market: dict = Field(default_factory=dict)
    operations: Operations = Field(default_factory=Operations)
    financial_projections: FinancialProjections = Field(
        default_factory=FinancialProjections)
    funding: Funding = Field(default_factory=Funding)
    risks_and_mitigation: list[Risk] = Field(default_factory=list)
    appendix_notes: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class BusinessPlanOutput(BaseModel):
    plan: PlannerOutput = Field(default_factory=PlannerOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def planner_agent(business_idea: str, plan_type: str = "startup",
                  industry: str = "", funding_goal: str = "",
                  timeline: str = "3 years", revision_notes: str = "",
                  provider: str = "openai") -> PlannerOutput:
    system = _load_prompt("planner_prompt")
    user_msg = (
        f"Plan Type: {plan_type}\nIndustry: {industry or 'Auto-detect'}\n"
        f"Funding Goal: {funding_goal or 'Not specified'}\n"
        f"Timeline: {timeline}\n"
    )
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nBusiness Idea:\n{business_idea}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return PlannerOutput(**json.loads(raw))


def qa_agent(plan: PlannerOutput, provider: str = "openai") -> QAResult:
    system = _load_prompt("qa_prompt")
    user_msg = f"Business plan to validate:\n{json.dumps(plan.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return QAResult(**json.loads(raw))


def run_pipeline(business_idea: str, plan_type: str = "startup",
                 industry: str = "", funding_goal: str = "",
                 timeline: str = "3 years", provider: str = "openai",
                 max_retries: int = 2) -> BusinessPlanOutput:
    print(f"\n[BUSINESS PLAN] Starting pipeline — {plan_type}")

    print("\n  [1/2] Drafting business plan...")
    plan = planner_agent(business_idea, plan_type, industry, funding_goal,
                         timeline, provider=provider)
    print(f"  → \"{plan.company_name}\"")
    print(f"  → {len(plan.business_model.revenue_streams)} revenue streams, "
          f"{len(plan.risks_and_mitigation)} risks identified")

    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(plan, provider)
        print(f"  → {qa.status} (score: {qa.score})")
        if qa.status == "PASS":
            break
        if attempt <= max_retries and qa.revision_notes:
            print("  → Revising plan...")
            plan = planner_agent(business_idea, plan_type, industry,
                                 funding_goal, timeline, qa.revision_notes,
                                 provider)

    return BusinessPlanOutput(
        plan=plan, qa=qa,
        meta={"plan_type": plan_type, "provider": provider,
              "timestamp": datetime.now(timezone.utc).isoformat()},
    )


def save_output(output: BusinessPlanOutput) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"bizplan_{ts}_{run_id}.json"
    path.write_text(json.dumps(output.model_dump(), indent=2, default=str),
                    encoding="utf-8")
    print(f"\n  [SAVED] {path}")
    return path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Business Plan Writer Agent")
    parser.add_argument("--text", default="")
    parser.add_argument("--file", default="")
    parser.add_argument("--type", default="startup",
                        choices=["startup", "expansion", "investor_pitch",
                                 "internal", "loan_application", "lean_canvas"],
                        dest="plan_type")
    parser.add_argument("--industry", default="")
    parser.add_argument("--funding", default="")
    parser.add_argument("--timeline", default="3 years")
    parser.add_argument("--provider", default="openai")
    args = parser.parse_args()

    if args.file:
        data = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        data = args.text
    else:
        print("Error: provide --text or --file"); sys.exit(1)

    result = run_pipeline(data, args.plan_type, args.industry, args.funding,
                          args.timeline, args.provider)
    save_output(result)
