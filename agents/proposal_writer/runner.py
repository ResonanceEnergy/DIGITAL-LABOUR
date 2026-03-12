"""Proposal Writer Agent — Generate professional proposals from project briefs.

2-step pipeline:
    1. Writer Agent — produces full proposal from brief/RFP
    2. QA Agent — validates completeness, pricing integrity, and professionalism

Handles: RFP responses, project proposals, SOWs, service agreements,
         pitch deck scripts, case studies.

Usage:
    python -m agents.proposal_writer.runner --file rfp.txt --type rfp_response
    python -m agents.proposal_writer.runner --text "Client needs..." --type project_proposal
    python -m agents.proposal_writer.runner --file brief.md --type sow --budget "5000-10000"
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
OUTPUT_DIR = PROJECT_ROOT / "output" / "proposals"


# ── Pydantic Models ────────────────────────────────────────────

class Challenge(BaseModel):
    description: str = ""


class ClientUnderstanding(BaseModel):
    company: str = ""
    industry: str = ""
    challenges: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)


class Phase(BaseModel):
    phase: int = 0
    name: str = ""
    duration: str = ""
    deliverables: list[str] = Field(default_factory=list)
    description: str = ""


class ProposedSolution(BaseModel):
    overview: str = ""
    phases: list[Phase] = Field(default_factory=list)
    technology_stack: list[str] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)


class ScopeOfWork(BaseModel):
    in_scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class Milestone(BaseModel):
    milestone: str = ""
    date: str = ""
    deliverable: str = ""


class Timeline(BaseModel):
    start_date: str = ""
    total_duration: str = ""
    milestones: list[Milestone] = Field(default_factory=list)


class PricingLineItem(BaseModel):
    item: str = ""
    amount: float = 0.0
    description: str = ""


class Pricing(BaseModel):
    model: str = "fixed_price"
    total: float = 0.0
    currency: str = "USD"
    breakdown: list[PricingLineItem] = Field(default_factory=list)
    payment_terms: str = ""
    notes: str = ""


class Terms(BaseModel):
    validity: str = ""
    warranty: str = ""
    ip_ownership: str = ""
    confidentiality: str = ""
    cancellation: str = ""


class CaseStudy(BaseModel):
    client: str = ""
    challenge: str = ""
    solution: str = ""
    result: str = ""


class WriterOutput(BaseModel):
    proposal_type: str = ""
    title: str = ""
    executive_summary: str = ""
    client_understanding: ClientUnderstanding = Field(
        default_factory=ClientUnderstanding)
    proposed_solution: ProposedSolution = Field(
        default_factory=ProposedSolution)
    scope_of_work: ScopeOfWork = Field(default_factory=ScopeOfWork)
    timeline: Timeline = Field(default_factory=Timeline)
    pricing: Pricing = Field(default_factory=Pricing)
    why_us: list[str] = Field(default_factory=list)
    terms: Terms = Field(default_factory=Terms)
    next_steps: list[str] = Field(default_factory=list)
    case_studies: list[CaseStudy] = Field(default_factory=list)


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class ProposalOutput(BaseModel):
    proposal: WriterOutput = Field(default_factory=WriterOutput)
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
    proposal_type: str = "project_proposal",
    company_name: str = "Digital Labour",
    company_description: str = "AI-powered automation agency",
    budget_range: str = "",
    deadline: str = "",
    revision_notes: str = "",
    provider: str = "openai",
) -> WriterOutput:
    """Step 1: Generate the proposal."""
    system = _load_prompt("writer_prompt")
    user_msg = (
        f"Proposal Type: {proposal_type}\n"
        f"Company: {company_name} — {company_description}\n"
        f"Budget Range: {budget_range or 'Not specified'}\n"
        f"Deadline: {deadline or 'Not specified'}\n"
    )
    if revision_notes:
        user_msg += f"\nQA REVISION NOTES:\n{revision_notes}\n"
    user_msg += f"\nProject Brief:\n{brief}"

    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return WriterOutput(**json.loads(raw))


def qa_agent(proposal: WriterOutput, provider: str = "openai") -> QAResult:
    """Step 2: Validate proposal quality."""
    system = _load_prompt("qa_prompt")
    user_msg = f"Proposal to validate:\n{json.dumps(proposal.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    return QAResult(**json.loads(raw))


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    brief: str,
    proposal_type: str = "project_proposal",
    company_name: str = "Digital Labour",
    budget_range: str = "",
    deadline: str = "",
    provider: str = "openai",
    max_retries: int = 2,
) -> ProposalOutput:
    """Run the full proposal pipeline: Writer → QA."""
    print(f"\n[PROPOSAL] Starting pipeline — {proposal_type}")
    print(f"  Company: {company_name} | Provider: {provider}")

    # Step 1: Write
    print("\n  [1/2] Generating proposal...")
    proposal = writer_agent(brief, proposal_type, company_name,
                            budget_range=budget_range, deadline=deadline,
                            provider=provider)
    print(f"  → \"{proposal.title}\"")
    print(f"  → {len(proposal.proposed_solution.phases)} phases, "
          f"${proposal.pricing.total:,.0f} total")

    # Step 2: QA (with retries)
    qa = QAResult()
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(proposal, provider)
        print(f"  → {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print("  → Rewriting with revision notes...")
            proposal = writer_agent(
                brief, proposal_type, company_name,
                budget_range=budget_range, deadline=deadline,
                revision_notes=qa.revision_notes, provider=provider)

    output = ProposalOutput(
        proposal=proposal,
        qa=qa,
        meta={
            "proposal_type": proposal_type,
            "company": company_name,
            "provider": provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return output


def save_output(output: ProposalOutput) -> Path:
    """Save pipeline output to JSON and standalone Markdown proposal."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # JSON
    json_path = OUTPUT_DIR / f"proposal_{ts}_{run_id}.json"
    json_path.write_text(
        json.dumps(output.model_dump(), indent=2, default=str),
        encoding="utf-8")

    # Markdown
    p = output.proposal
    md_lines = [
        f"# {p.title}\n",
        f"**Type:** {p.proposal_type}  ",
        f"**Date:** {datetime.now(timezone.utc).strftime('%B %d, %Y')}  ",
        f"**Valid for:** {p.terms.validity}\n",
        "## Executive Summary\n",
        f"{p.executive_summary}\n",
        "## Client Understanding\n",
        f"**Company:** {p.client_understanding.company}  ",
        f"**Industry:** {p.client_understanding.industry}\n",
        "### Challenges\n",
    ]
    for c in p.client_understanding.challenges:
        md_lines.append(f"- {c}")
    md_lines.append("\n### Goals\n")
    for g in p.client_understanding.goals:
        md_lines.append(f"- {g}")
    md_lines.append("\n## Proposed Solution\n")
    md_lines.append(f"{p.proposed_solution.overview}\n")
    for phase in p.proposed_solution.phases:
        md_lines.append(f"### Phase {phase.phase}: {phase.name} ({phase.duration})\n")
        md_lines.append(f"{phase.description}\n")
        md_lines.append("**Deliverables:**\n")
        for d in phase.deliverables:
            md_lines.append(f"- {d}")
        md_lines.append("")
    md_lines.append("## Scope of Work\n")
    md_lines.append("### In Scope\n")
    for s in p.scope_of_work.in_scope:
        md_lines.append(f"- {s}")
    md_lines.append("\n### Out of Scope\n")
    for s in p.scope_of_work.out_of_scope:
        md_lines.append(f"- {s}")
    md_lines.append(f"\n## Timeline — {p.timeline.total_duration}\n")
    md_lines.append("| Milestone | Date | Deliverable |")
    md_lines.append("|-----------|------|-------------|")
    for m in p.timeline.milestones:
        md_lines.append(f"| {m.milestone} | {m.date} | {m.deliverable} |")
    md_lines.append(f"\n## Pricing — ${p.pricing.total:,.0f} {p.pricing.currency}\n")
    md_lines.append("| Item | Amount | Description |")
    md_lines.append("|------|--------|-------------|")
    for li in p.pricing.breakdown:
        md_lines.append(f"| {li.item} | ${li.amount:,.0f} | {li.description} |")
    md_lines.append(f"\n**Payment Terms:** {p.pricing.payment_terms}\n")
    md_lines.append("## Why Us\n")
    for w in p.why_us:
        md_lines.append(f"- {w}")
    md_lines.append("\n## Terms\n")
    md_lines.append(f"- **Validity:** {p.terms.validity}")
    md_lines.append(f"- **Warranty:** {p.terms.warranty}")
    md_lines.append(f"- **IP Ownership:** {p.terms.ip_ownership}")
    md_lines.append(f"- **Confidentiality:** {p.terms.confidentiality}")
    md_lines.append(f"- **Cancellation:** {p.terms.cancellation}")
    md_lines.append("\n## Next Steps\n")
    for i, ns in enumerate(p.next_steps, 1):
        md_lines.append(f"{i}. {ns}")
    md_lines.append("")

    md_path = OUTPUT_DIR / f"proposal_{ts}_{run_id}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\n  [SAVED] {json_path}")
    print(f"  [SAVED] {md_path}")
    return json_path


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Proposal Writer Agent")
    parser.add_argument("--text", default="", help="Brief as text")
    parser.add_argument("--file", default="", help="File containing brief")
    parser.add_argument("--type", default="project_proposal",
                        choices=["rfp_response", "project_proposal", "sow",
                                 "service_agreement", "pitch_deck_script",
                                 "case_study"],
                        dest="proposal_type")
    parser.add_argument("--company", default="Digital Labour")
    parser.add_argument("--budget", default="", help="Budget range")
    parser.add_argument("--deadline", default="", help="Project deadline")
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
        proposal_type=args.proposal_type,
        company_name=args.company,
        budget_range=args.budget,
        deadline=args.deadline,
        provider=args.provider,
    )
    save_output(result)
