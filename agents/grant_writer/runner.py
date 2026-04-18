"""Grant Writer Agent — Generate SBIR proposals, government RFP responses, and grant applications.

2-step pipeline:
    1. Writer Agent — produces full grant proposal from solicitation/brief
    2. QA Agent — validates completeness, compliance, and technical merit

Handles: SBIR Phase I/II, federal RFP responses, state grants, foundation grants,
         STTR proposals, DOD BAA responses.

Usage:
    python -m agents.grant_writer.runner --file solicitation.txt --type sbir_phase1 --agency nsf
    python -m agents.grant_writer.runner --text "Project developing..." --type federal_rfp
    python -m agents.grant_writer.runner --file rfp.md --type foundation_grant --provider anthropic
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
call_llm = make_bridge("grant_writer")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "grants"


# ── Pydantic Models ────────────────────────────────────────────

class ProjectSummary(BaseModel):
    title: str = ""
    abstract: str = Field(default="", description="300 words max")
    keywords: list[str] = Field(default_factory=list)


class ProblemStatement(BaseModel):
    significance: str = ""
    innovation: str = ""
    current_gap: str = ""
    impact_if_solved: str = ""


class Phase(BaseModel):
    phase_number: int = 0
    name: str = ""
    duration: str = ""
    objectives: list[str] = Field(default_factory=list)
    tasks: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    milestones: list[str] = Field(default_factory=list)


class TechnicalApproach(BaseModel):
    methodology: str = ""
    phases: list[Phase] = Field(default_factory=list)
    key_innovations: list[str] = Field(default_factory=list)
    feasibility_evidence: str = ""
    risk_mitigation: list[str] = Field(default_factory=list)


class TeamMember(BaseModel):
    name: str = ""
    role: str = ""
    qualifications: str = ""
    time_commitment: str = ""


class TeamQualifications(BaseModel):
    pi_name: str = ""
    pi_credentials: str = ""
    team_members: list[TeamMember] = Field(default_factory=list)
    facilities: str = ""
    partnerships: str = ""


class BudgetNarrative(BaseModel):
    total_amount: float = 0.0
    personnel: float = 0.0
    equipment: float = 0.0
    travel: float = 0.0
    other_direct: float = 0.0
    indirect_rate: float = 0.0
    budget_justification: list[str] = Field(default_factory=list)


class CommercializationPlan(BaseModel):
    market_size: str = ""
    target_customers: list[str] = Field(default_factory=list)
    competitive_advantage: str = ""
    revenue_model: str = ""
    go_to_market: str = ""
    ip_strategy: str = ""


class WriterOutput(BaseModel):
    grant_type: str = ""
    title: str = ""
    project_summary: ProjectSummary = Field(default_factory=ProjectSummary)
    problem_statement: ProblemStatement = Field(default_factory=ProblemStatement)
    technical_approach: TechnicalApproach = Field(default_factory=TechnicalApproach)
    team_qualifications: TeamQualifications = Field(default_factory=TeamQualifications)
    budget_narrative: BudgetNarrative = Field(default_factory=BudgetNarrative)
    commercialization_plan: CommercializationPlan = Field(default_factory=CommercializationPlan)
    references: list[str] = Field(default_factory=list)
    compliance_notes: str = ""
    full_markdown: str = ""


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class GrantOutput(BaseModel):
    grant: WriterOutput = Field(default_factory=WriterOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


# ── Agent Functions ─────────────────────────────────────────────

def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def writer_agent(
    brief: str,
    grant_type: str = "sbir_phase1",
    agency: str = "nsf",
    revision_notes: str = "",
    provider: str = "openai",
) -> WriterOutput:
    """Step 1: Generate the grant proposal."""
    system = _load_prompt("writer_prompt")
    user_msg = (
        f"Grant Type: {grant_type}\n"
        f"Target Agency: {agency}\n"
    )
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nProject Brief / Solicitation:\n{brief}"

    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(WriterOutput, data, agent_name="grant_writer.writer")


def qa_agent(grant: WriterOutput, provider: str = "openai") -> QAResult:
    """Step 2: Validate grant proposal quality and compliance."""
    system = _load_prompt("qa_prompt")
    user_msg = f"Grant proposal to validate:\n{json.dumps(grant.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(QAResult, data, agent_name="grant_writer.qa")


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    brief: str,
    grant_type: str = "sbir_phase1",
    agency: str = "nsf",
    provider: str = "openai",
    max_retries: int = 2,
) -> GrantOutput:
    """Run the full grant writing pipeline: Writer -> QA."""
    print(f"\n[GRANT] Starting pipeline — {grant_type} ({agency})")
    print(f"  Provider: {provider}")

    # Step 1: Write
    print("\n  [1/2] Generating grant proposal...")
    grant = writer_agent(brief, grant_type, agency, provider=provider)
    print(f"  -> \"{grant.title}\"")
    print(f"  -> {len(grant.technical_approach.phases)} phases, "
          f"${grant.budget_narrative.total_amount:,.0f} total budget")

    # Step 2: QA (with retries)
    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(grant, provider)
        print(f"  -> {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print("  -> Rewriting with revision notes...")
            grant = writer_agent(
                brief, grant_type, agency,
                revision_notes=qa.revision_notes, provider=provider)

    output = GrantOutput(
        grant=grant,
        qa=qa,
        meta={
            "grant_type": grant_type,
            "agency": agency,
            "provider": provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return output


def save_output(output: GrantOutput) -> Path:
    """Save pipeline output to JSON and standalone Markdown grant proposal."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # JSON
    json_path = OUTPUT_DIR / f"grant_{ts}_{run_id}.json"
    json_path.write_text(
        json.dumps(output.model_dump(), indent=2, default=str),
        encoding="utf-8")

    # Markdown
    g = output.grant
    md_lines = [
        f"# {g.title}\n",
        f"**Grant Type:** {g.grant_type}  ",
        f"**Date:** {datetime.now(timezone.utc).strftime('%B %d, %Y')}  ",
        f"**Total Budget:** ${g.budget_narrative.total_amount:,.0f}\n",
    ]

    # Project Summary
    md_lines.append("## Project Summary\n")
    md_lines.append(f"{g.project_summary.abstract}\n")
    md_lines.append(f"**Keywords:** {', '.join(g.project_summary.keywords)}\n")

    # Problem Statement / Significance
    md_lines.append("## Significance and Innovation\n")
    md_lines.append("### Significance\n")
    md_lines.append(f"{g.problem_statement.significance}\n")
    md_lines.append("### Innovation\n")
    md_lines.append(f"{g.problem_statement.innovation}\n")
    md_lines.append("### Current Gap\n")
    md_lines.append(f"{g.problem_statement.current_gap}\n")
    md_lines.append("### Impact if Solved\n")
    md_lines.append(f"{g.problem_statement.impact_if_solved}\n")

    # Technical Approach
    md_lines.append("## Technical Approach\n")
    md_lines.append(f"{g.technical_approach.methodology}\n")
    md_lines.append("### Key Innovations\n")
    for inn in g.technical_approach.key_innovations:
        md_lines.append(f"- {inn}")
    md_lines.append("")
    for phase in g.technical_approach.phases:
        md_lines.append(f"### Phase {phase.phase_number}: {phase.name} ({phase.duration})\n")
        md_lines.append("**Objectives:**\n")
        for obj in phase.objectives:
            md_lines.append(f"- {obj}")
        md_lines.append("\n**Tasks:**\n")
        for task in phase.tasks:
            md_lines.append(f"- {task}")
        md_lines.append("\n**Deliverables:**\n")
        for d in phase.deliverables:
            md_lines.append(f"- {d}")
        md_lines.append("\n**Milestones:**\n")
        for m in phase.milestones:
            md_lines.append(f"- {m}")
        md_lines.append("")

    md_lines.append("### Feasibility Evidence\n")
    md_lines.append(f"{g.technical_approach.feasibility_evidence}\n")
    md_lines.append("### Risk Mitigation\n")
    for r in g.technical_approach.risk_mitigation:
        md_lines.append(f"- {r}")
    md_lines.append("")

    # Team Qualifications
    md_lines.append("## Team Qualifications\n")
    md_lines.append(f"**Principal Investigator:** {g.team_qualifications.pi_name}  ")
    md_lines.append(f"**Credentials:** {g.team_qualifications.pi_credentials}\n")
    if g.team_qualifications.team_members:
        md_lines.append("### Team Members\n")
        md_lines.append("| Name | Role | Qualifications | Time Commitment |")
        md_lines.append("|------|------|---------------|-----------------|")
        for tm in g.team_qualifications.team_members:
            md_lines.append(f"| {tm.name} | {tm.role} | {tm.qualifications} | {tm.time_commitment} |")
        md_lines.append("")
    md_lines.append(f"**Facilities:** {g.team_qualifications.facilities}\n")
    md_lines.append(f"**Partnerships:** {g.team_qualifications.partnerships}\n")

    # Budget Narrative
    md_lines.append("## Budget Narrative\n")
    md_lines.append(f"**Total Amount:** ${g.budget_narrative.total_amount:,.0f}\n")
    md_lines.append("| Category | Amount |")
    md_lines.append("|----------|--------|")
    md_lines.append(f"| Personnel | ${g.budget_narrative.personnel:,.0f} |")
    md_lines.append(f"| Equipment | ${g.budget_narrative.equipment:,.0f} |")
    md_lines.append(f"| Travel | ${g.budget_narrative.travel:,.0f} |")
    md_lines.append(f"| Other Direct Costs | ${g.budget_narrative.other_direct:,.0f} |")
    md_lines.append(f"| Indirect ({g.budget_narrative.indirect_rate}%) | — |")
    md_lines.append("\n### Budget Justification\n")
    for bj in g.budget_narrative.budget_justification:
        md_lines.append(f"- {bj}")
    md_lines.append("")

    # Commercialization Plan
    md_lines.append("## Commercialization Plan\n")
    md_lines.append(f"**Market Size:** {g.commercialization_plan.market_size}  ")
    md_lines.append(f"**Competitive Advantage:** {g.commercialization_plan.competitive_advantage}\n")
    md_lines.append(f"**Revenue Model:** {g.commercialization_plan.revenue_model}\n")
    md_lines.append(f"**Go-to-Market:** {g.commercialization_plan.go_to_market}\n")
    md_lines.append(f"**IP Strategy:** {g.commercialization_plan.ip_strategy}\n")
    md_lines.append("**Target Customers:**\n")
    for tc in g.commercialization_plan.target_customers:
        md_lines.append(f"- {tc}")
    md_lines.append("")

    # References
    if g.references:
        md_lines.append("## References\n")
        for i, ref in enumerate(g.references, 1):
            md_lines.append(f"{i}. {ref}")
        md_lines.append("")

    # Compliance Notes
    if g.compliance_notes:
        md_lines.append("## Compliance Notes\n")
        md_lines.append(f"{g.compliance_notes}\n")

    md_path = OUTPUT_DIR / f"grant_{ts}_{run_id}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\n  [SAVED] {json_path}")
    print(f"  [SAVED] {md_path}")
    return json_path


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Grant Writer Agent")
    parser.add_argument("--text", default="", help="Project brief as text")
    parser.add_argument("--file", default="", help="File containing brief/solicitation")
    parser.add_argument("--type", default="sbir_phase1",
                        choices=["sbir_phase1", "sbir_phase2", "federal_rfp",
                                 "state_grant", "foundation_grant"],
                        dest="grant_type")
    parser.add_argument("--agency", default="nsf",
                        choices=["nih", "nsf", "doe", "dod", "usda", "sba", "other"],
                        help="Target funding agency")
    parser.add_argument("--provider", default="openai", help="LLM provider")
    args = parser.parse_args()

    if args.file:
        brief = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        brief = args.text
    else:
        print("Error: provide --text or --file")
        sys.exit(1)

    result = run_pipeline(
        brief=brief,
        grant_type=args.grant_type,
        agency=args.agency,
        provider=args.provider,
    )
    save_output(result)
