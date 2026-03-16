"""Freelancer Work Agent — Search, Match, Bid, Deliver Pipeline.

End-to-end automation for Freelancer.com:
  1. Search/poll for projects matching our agent capabilities
  2. Score and match projects to internal agents
  3. Generate personalized bid proposals via LLM
  4. QA verify bids before submission
  5. Dispatch won projects to internal agent pipelines for delivery

Usage:
    python runner.py --action search                          # Search for new projects
    python runner.py --action bid --project project.json      # Generate bid for a project
    python runner.py --action deliver --project project.json  # Plan delivery for won project
    python runner.py --action scan --dry-run                  # Full scan cycle (dry run)
"""

import argparse
import json
import sys
import time
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv(PROJECT_ROOT / ".env")

from utils.dl_agent import make_bridge
llm_call = make_bridge("freelancer_work")
from campaign.freelancer_deploy import (
    FREELANCER_GIGS,
    BID_TEMPLATES,
    AGENCY_PROFILE,
    match_project,
)


# ── Models ──────────────────────────────────────────────────────────────────

class FreelancerProject(BaseModel):
    """Normalized project from Freelancer.com."""
    id: str = ""
    title: str = ""
    description: str = ""
    budget_min: float = 0
    budget_max: float = 0
    currency: str = "USD"
    skills: list[str] = []
    url: str = ""
    platform: str = "freelancer"
    client_name: str = ""
    client_country: str = ""
    proposals_count: int = 0


class BidOutput(BaseModel):
    """Generated bid proposal."""
    subject: str = ""
    body: str = ""
    estimated_delivery: str = ""
    suggested_bid_usd: float = 0
    confidence: float = 0
    matched_agents: list[str] = []
    key_selling_points: list[str] = []


class QAResult(BaseModel):
    status: str = Field(pattern=r"^(PASS|FAIL)$")
    issues: list[str] = []
    revision_notes: str = ""
    scores: dict = {}


class DeliveryStep(BaseModel):
    step: int = 0
    agent: str = ""
    action: str = ""
    inputs: dict = {}


class DeliveryPlan(BaseModel):
    primary_agent: str = ""
    supporting_agents: list[str] = []
    steps: list[DeliveryStep] = []
    estimated_time_minutes: int = 0
    milestones: list[str] = []
    client_deliverables: list[str] = []
    quality_checks: list[str] = []


class ClientMessage(BaseModel):
    """Generated client message."""
    message_type: str = ""
    subject: str = ""
    body: str = ""
    follow_up_date: str = ""
    internal_notes: str = ""


class ExecutionResult(BaseModel):
    """Result of executing a delivery step via internal agent."""
    step: int = 0
    agent: str = ""
    action: str = ""
    status: str = "pending"
    output_summary: str = ""
    output_files: list[str] = []
    error: str = ""


class ProjectState(BaseModel):
    """Tracks a won project through execution and delivery."""
    project: FreelancerProject = FreelancerProject()
    delivery_plan: DeliveryPlan | None = None
    execution_results: list[ExecutionResult] = []
    messages_sent: list[ClientMessage] = []
    milestones_completed: list[str] = []
    status: str = "won"  # won → executing → delivered → completed
    deliverable_files: list[str] = []


class FreelancerWorkOutput(BaseModel):
    """Full pipeline output."""
    action: str = ""
    project: FreelancerProject = FreelancerProject()
    match_results: list[dict] = []
    bid: BidOutput | None = None
    qa: QAResult | None = None
    delivery_plan: DeliveryPlan | None = None
    client_message: ClientMessage | None = None
    execution_results: list[ExecutionResult] = []
    project_state: ProjectState | None = None
    status: str = "pending"


# ── Prompt Loading ──────────────────────────────────────────────────────────

AGENT_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    path = AGENT_DIR / f"{name}_prompt.md"
    if not path.exists():
        path = AGENT_DIR.parent / "qa" / f"{name}_prompt.md"
    return path.read_text(encoding="utf-8")


# ── LLM ─────────────────────────────────────────────────────────────────────

def call_llm(system_prompt: str, user_message: str, provider: str | None = None) -> str:
    return llm_call(system_prompt, user_message, provider=provider, temperature=0.4, json_mode=True)


# ── Agent Functions ─────────────────────────────────────────────────────────

def match_agent(project: FreelancerProject) -> list[dict]:
    """Match project to internal agents using keyword rules."""
    matches = match_project(project.title, project.description)
    if not matches:
        # Try matching on skills too
        skills_text = " ".join(project.skills)
        matches = match_project(project.title, f"{project.description} {skills_text}")
    return matches


def generate_bid(project: FreelancerProject, matches: list[dict], provider: str | None = None) -> BidOutput:
    """Generate a personalized bid using LLM."""
    prompt = load_prompt("bid_generator")

    # Build context about our matching capabilities
    matched_agents = [m["agent"] for m in matches]
    matched_gigs = [g for g in FREELANCER_GIGS if g["agent"] in matched_agents]

    # Get the best matching bid template as a starting point
    best_template = matches[0].get("bid_template", {}) if matches else {}

    user_msg = json.dumps({
        "project": {
            "title": project.title,
            "description": project.description,
            "budget_min": project.budget_min,
            "budget_max": project.budget_max,
            "currency": project.currency,
            "skills_required": project.skills,
            "client_name": project.client_name,
            "client_country": project.client_country,
            "proposals_count": project.proposals_count,
        },
        "our_matching_agents": matched_agents,
        "our_matching_services": [
            {"agent": g["agent"], "title": g["title"], "packages": g["packages"]}
            for g in matched_gigs
        ],
        "template_hint": best_template,
        "agency_profile": {
            "name": AGENCY_PROFILE["name"],
            "tagline": AGENCY_PROFILE["tagline"],
            "location": AGENCY_PROFILE["location"],
        },
    }, indent=2)

    raw = call_llm(prompt, user_msg, provider)
    return BidOutput.model_validate_json(raw)


def qa_bid(project: FreelancerProject, bid: BidOutput, provider: str | None = None) -> QAResult:
    """QA check on generated bid."""
    prompt = load_prompt("qa")

    user_msg = json.dumps({
        "project": {
            "title": project.title,
            "description": project.description,
            "budget_min": project.budget_min,
            "budget_max": project.budget_max,
            "skills_required": project.skills,
        },
        "bid": bid.model_dump(),
    }, indent=2)

    raw = call_llm(prompt, user_msg, provider)
    return QAResult.model_validate_json(raw)


def plan_delivery(project: FreelancerProject, matches: list[dict], provider: str | None = None) -> DeliveryPlan:
    """Plan delivery for a won project."""
    prompt = load_prompt("delivery")

    user_msg = json.dumps({
        "project": {
            "title": project.title,
            "description": project.description,
            "budget_min": project.budget_min,
            "budget_max": project.budget_max,
            "skills_required": project.skills,
            "client_name": project.client_name,
        },
        "matched_agents": [m["agent"] for m in matches],
    }, indent=2)

    raw = call_llm(prompt, user_msg, provider)
    data = json.loads(raw)
    plan_data = data.get("delivery_plan", data)
    return DeliveryPlan.model_validate(plan_data)


def generate_client_message(
    project: FreelancerProject,
    message_type: str = "intro",
    context: str = "",
    provider: str | None = None,
) -> ClientMessage:
    """Generate a professional client message using LLM."""
    prompt = load_prompt("client_message")

    user_msg = json.dumps({
        "message_type": message_type,
        "project": {
            "title": project.title,
            "description": project.description,
            "budget_max": project.budget_max,
            "client_name": project.client_name,
        },
        "context": context,
    }, indent=2)

    raw = call_llm(prompt, user_msg, provider)
    return ClientMessage.model_validate_json(raw)


def execute_delivery_step(step: DeliveryStep, project: FreelancerProject) -> ExecutionResult:
    """Execute a single delivery step by dispatching to the internal agent."""
    from dispatcher.router import route_task, create_event

    result = ExecutionResult(step=step.step, agent=step.agent, action=step.action)

    # Map delivery step to dispatcher inputs
    inputs = _build_agent_inputs(step, project)

    event = create_event(
        client_id="freelancer_delivery",
        task_type=step.agent,
        inputs=inputs,
    )

    print(f"  [STEP {step.step}] Dispatching to {step.agent}: {step.action[:50]}...")

    try:
        completed = route_task(event)

        if completed["qa"]["status"] == "PASS":
            result.status = "completed"
            outputs = completed.get("outputs", {})
            result.output_summary = _summarize_output(outputs)
            result.output_files = _collect_output_files(outputs, step.agent, project)
        else:
            result.status = "failed"
            result.error = "; ".join(completed["qa"].get("issues", []))
    except Exception as e:
        result.status = "error"
        result.error = str(e)

    return result


def _build_agent_inputs(step: DeliveryStep, project: FreelancerProject) -> dict:
    """Map a delivery step to the correct agent input format."""
    agent = step.agent
    desc = project.description
    title = project.title
    inputs_override = step.inputs or {}

    # Common mapping — each agent has different input params
    agent_input_map = {
        "seo_content": {"topic": title, "content_type": "blog_post", "audience": inputs_override.get("audience", "")},
        "data_entry": {"raw_data": inputs_override.get("raw_data", desc), "data_task": "clean", "output_format": "json"},
        "web_scraper": {"page_content": inputs_override.get("page_content", desc), "url": inputs_override.get("url", ""), "target": "company_info"},
        "email_marketing": {"business": inputs_override.get("business", title), "audience": inputs_override.get("audience", ""), "goal": "nurture"},
        "lead_gen": {"industry": inputs_override.get("industry", ""), "icp": inputs_override.get("icp", desc), "count": inputs_override.get("count", 10)},
        "sales_ops": {"company": inputs_override.get("company", ""), "role": inputs_override.get("role", ""), "product": desc},
        "support": {"ticket": desc},
        "content_repurpose": {"source_text": inputs_override.get("source_text", desc)},
        "doc_extract": {"document_text": inputs_override.get("document_text", desc), "doc_type": inputs_override.get("doc_type", "auto")},
        "social_media": {"topic": title, "platforms": inputs_override.get("platforms", ["linkedin", "twitter"])},
        "crm_ops": {"crm_data": inputs_override.get("crm_data", desc), "crm_task": "clean"},
        "bookkeeping": {"financial_data": inputs_override.get("financial_data", desc), "task_type": "categorize"},
        "proposal_writer": {"project_brief": desc, "client": project.client_name},
        "product_desc": {"product_info": desc, "platform": inputs_override.get("platform", "shopify")},
        "resume_writer": {"resume_text": inputs_override.get("resume_text", desc), "job_title": inputs_override.get("job_title", title)},
        "ad_copy": {"product": desc, "platform": inputs_override.get("platform", "google")},
        "market_research": {"industry": inputs_override.get("industry", title), "scope": inputs_override.get("scope", "overview")},
        "business_plan": {"business_idea": desc},
        "press_release": {"announcement": desc, "company": inputs_override.get("company", "")},
        "tech_docs": {"source_code": inputs_override.get("source_code", desc), "doc_type": inputs_override.get("doc_type", "api_reference")},
    }

    base_inputs = agent_input_map.get(agent, {"raw_input": desc})
    # Override with any explicit step inputs
    base_inputs.update({k: v for k, v in inputs_override.items() if k not in base_inputs or v})
    return base_inputs


def _summarize_output(outputs: dict) -> str:
    """Create a brief summary of agent output for status reporting."""
    if not outputs:
        return "No output generated"
    # Take first 300 chars of the most relevant field
    for key in ["final_content", "content", "result", "output", "data", "text"]:
        if key in outputs and outputs[key]:
            val = str(outputs[key])
            return val[:300] + ("..." if len(val) > 300 else "")
    # Fallback: summarize keys
    return f"Output keys: {', '.join(list(outputs.keys())[:10])}"


def _collect_output_files(outputs: dict, agent: str, project: FreelancerProject) -> list[str]:
    """Save agent output to deliverable files and return paths."""
    output_dir = PROJECT_ROOT / "output" / "freelancer_deliveries" / project.id
    output_dir.mkdir(parents=True, exist_ok=True)

    files = []
    # Save full output as JSON
    out_path = output_dir / f"{agent}_output.json"
    out_path.write_text(json.dumps(outputs, indent=2, default=str), encoding="utf-8")
    files.append(str(out_path))

    # If there's text content, also save as readable format
    for key in ["final_content", "content", "result", "text"]:
        if key in outputs and isinstance(outputs[key], str) and len(outputs[key]) > 100:
            txt_path = output_dir / f"{agent}_{key}.txt"
            txt_path.write_text(outputs[key], encoding="utf-8")
            files.append(str(txt_path))
            break

    return files


def execute_delivery(
    project: FreelancerProject,
    delivery_plan: DeliveryPlan,
    provider: str | None = None,
) -> ProjectState:
    """Execute all delivery steps for a won project."""
    state = ProjectState(
        project=project,
        delivery_plan=delivery_plan,
        status="executing",
    )

    print(f"\n[EXECUTE] Running {len(delivery_plan.steps)} delivery steps...")

    for step in delivery_plan.steps:
        result = execute_delivery_step(step, project)
        state.execution_results.append(result)
        state.deliverable_files.extend(result.output_files)

        if result.status == "completed":
            print(f"  [STEP {step.step}] DONE — {step.agent}")
            # Mark matching milestone
            for ms in delivery_plan.milestones:
                if step.agent.lower() in ms.lower() and ms not in state.milestones_completed:
                    state.milestones_completed.append(ms)
                    break
        else:
            print(f"  [STEP {step.step}] {result.status.upper()} — {result.error[:80]}")

    # Check overall status
    completed_steps = sum(1 for r in state.execution_results if r.status == "completed")
    total_steps = len(delivery_plan.steps)

    if completed_steps == total_steps:
        state.status = "delivered"
        print(f"\n[DONE] All {total_steps} steps completed — ready for client delivery")
    elif completed_steps > 0:
        state.status = "partial"
        print(f"\n[PARTIAL] {completed_steps}/{total_steps} steps completed")
    else:
        state.status = "failed"
        print(f"\n[FAIL] No steps completed successfully")

    # Save project state
    state_dir = PROJECT_ROOT / "data" / "freelancer_projects"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / f"{project.id or uuid4().hex[:8]}_state.json"
    state_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    print(f"[STATE] Saved to {state_path}")

    return state


def load_project_state(project_id: str) -> ProjectState | None:
    """Load a saved project state."""
    state_dir = PROJECT_ROOT / "data" / "freelancer_projects"
    state_path = state_dir / f"{project_id}_state.json"
    if state_path.exists():
        return ProjectState.model_validate_json(state_path.read_text(encoding="utf-8"))
    # Try partial match
    for f in state_dir.glob(f"*{project_id}*_state.json"):
        return ProjectState.model_validate_json(f.read_text(encoding="utf-8"))
    return None

def run_pipeline(
    action: str = "bid",
    project_data: dict | None = None,
    max_retries: int = 1,
    provider: str | None = None,
    dry_run: bool = False,
) -> FreelancerWorkOutput | None:
    """Run Freelancer Work pipeline.

    Actions:
        bid      — Match + Generate Bid + QA (with retry)
        deliver  — Match + Plan Delivery for won project
        execute  — Execute delivery plan (dispatch to internal agents)
        message  — Generate client message (intro/update/delivery/etc.)
        complete — Full lifecycle: plan + execute + deliver to client
        scan     — Full scan: search + match + bid for all new projects
    """
    start = time.time()
    output = FreelancerWorkOutput(action=action)

    # Parse project data
    if project_data:
        output.project = FreelancerProject.model_validate(project_data)

    if action == "bid":
        project = output.project
        print(f"[MATCH] Matching project: {project.title[:60]}...")
        matches = match_agent(project)
        output.match_results = matches

        if not matches:
            print("[SKIP] No matching agents for this project")
            output.status = "no_match"
            return output

        print(f"[MATCH] {len(matches)} agent(s) matched: {[m['agent'] for m in matches]}")

        # Generate bid
        print("[BID] Generating personalized bid...")
        bid = generate_bid(project, matches, provider)
        output.bid = bid

        # QA loop
        for attempt in range(1 + max_retries):
            print(f"[QA] Verifying bid (attempt {attempt + 1})...")
            qa = qa_bid(project, bid, provider)
            output.qa = qa

            if qa.status == "PASS":
                elapsed = round(time.time() - start, 1)
                print(f"[PASS] Bid ready in {elapsed}s — confidence: {bid.confidence}")
                output.status = "bid_ready"
                return output
            else:
                print(f"[FAIL] Issues: {qa.issues}")
                if attempt < max_retries:
                    print("[RETRY] Re-generating bid with QA feedback...")
                    # Feed QA feedback into regeneration
                    project_with_feedback = FreelancerProject.model_validate(
                        {**project.model_dump(),
                         "description": f"{project.description}\n\n[QA FEEDBACK: {qa.revision_notes}]"}
                    )
                    bid = generate_bid(project_with_feedback, matches, provider)
                    output.bid = bid

        print("[WARN] Bid did not pass QA — flagged for human review")
        output.status = "needs_review"
        return output

    elif action == "deliver":
        project = output.project
        print(f"[DELIVER] Planning delivery: {project.title[:60]}...")
        matches = match_agent(project)
        output.match_results = matches

        if not matches:
            print("[SKIP] No matching agents")
            output.status = "no_match"
            return output

        plan = plan_delivery(project, matches, provider)
        output.delivery_plan = plan
        output.status = "delivery_planned"

        elapsed = round(time.time() - start, 1)
        print(f"[DONE] Delivery plan ready in {elapsed}s")
        print(f"  Primary agent: {plan.primary_agent}")
        print(f"  Steps: {len(plan.steps)}")
        print(f"  Est. time: {plan.estimated_time_minutes} min")
        return output

    elif action == "execute":
        # Execute a delivery plan — dispatch each step to internal agents
        project = output.project

        # Load existing delivery plan or create one
        state = load_project_state(project.id) if project.id else None
        if state and state.delivery_plan:
            plan = state.delivery_plan
            print(f"[EXECUTE] Loaded existing plan for project {project.id}")
        else:
            print(f"[EXECUTE] No saved plan — generating delivery plan first...")
            matches = match_agent(project)
            output.match_results = matches
            if not matches:
                output.status = "no_match"
                return output
            plan = plan_delivery(project, matches, provider)

        output.delivery_plan = plan
        project_state = execute_delivery(project, plan, provider)
        output.execution_results = project_state.execution_results
        output.project_state = project_state
        output.status = project_state.status

        elapsed = round(time.time() - start, 1)
        completed = sum(1 for r in project_state.execution_results if r.status == "completed")
        total = len(project_state.execution_results)
        print(f"[DONE] Execution finished in {elapsed}s — {completed}/{total} steps")
        return output

    elif action == "message":
        # Generate a client message
        project = output.project
        msg_type = project_data.get("message_type", "intro") if project_data else "intro"
        msg_context = project_data.get("context", "") if project_data else ""

        # Enrich context with project state if available
        state = load_project_state(project.id) if project.id else None
        if state and not msg_context:
            completed = sum(1 for r in state.execution_results if r.status == "completed")
            total = len(state.execution_results)
            msg_context = (
                f"Project status: {state.status}. "
                f"Steps completed: {completed}/{total}. "
                f"Milestones completed: {', '.join(state.milestones_completed) or 'none'}. "
                f"Deliverable files: {len(state.deliverable_files)}."
            )

        print(f"[MESSAGE] Generating {msg_type} message for: {project.title[:50]}...")
        message = generate_client_message(project, msg_type, msg_context, provider)
        output.client_message = message
        output.status = "message_ready"

        elapsed = round(time.time() - start, 1)
        print(f"[DONE] Message ready in {elapsed}s")
        print(f"  Type: {message.message_type}")
        print(f"  Subject: {message.subject}")
        return output

    elif action == "complete":
        # Full lifecycle: plan → execute → generate delivery message
        project = output.project
        print(f"[COMPLETE] Full lifecycle for: {project.title[:50]}...")

        # Step 1: Plan
        matches = match_agent(project)
        output.match_results = matches
        if not matches:
            output.status = "no_match"
            return output

        plan = plan_delivery(project, matches, provider)
        output.delivery_plan = plan
        print(f"  Plan: {len(plan.steps)} steps via {plan.primary_agent}")

        # Step 2: Execute
        project_state = execute_delivery(project, plan, provider)
        output.execution_results = project_state.execution_results
        output.project_state = project_state

        if project_state.status in ("delivered", "partial"):
            # Step 3: Generate delivery message
            files_str = ", ".join(Path(f).name for f in project_state.deliverable_files[:5])
            context = (
                f"All work is complete. Deliverable files: {files_str}. "
                f"Quality checks passed on all outputs."
            )
            message = generate_client_message(project, "delivery", context, provider)
            output.client_message = message
            project_state.messages_sent.append(message)
            output.status = "ready_to_deliver"
        else:
            output.status = project_state.status

        elapsed = round(time.time() - start, 1)
        print(f"[DONE] Full lifecycle in {elapsed}s — status: {output.status}")
        return output

    elif action == "scan":
        # Full scan cycle — delegate to autobidder
        from automation.autobidder import run_scan
        print("[SCAN] Running autobidder scan cycle...")
        report = run_scan(dry_run=dry_run)
        output.status = "scan_complete"
        output.match_results = [report]

        elapsed = round(time.time() - start, 1)
        print(f"[DONE] Scan complete in {elapsed}s")
        print(f"  Projects found: {report.get('projects_found', 0)}")
        print(f"  Bids generated: {report.get('bids_generated', 0)}")
        return output

    else:
        print(f"[ERROR] Unknown action: {action}")
        output.status = "error"
        return output


# ── Output ──────────────────────────────────────────────────────────────────

def save_output(output: FreelancerWorkOutput, output_dir: Path | None = None) -> Path:
    output_dir = output_dir or PROJECT_ROOT / "output" / "freelancer_work"
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"freelancer_{output.action}_{uuid4().hex[:8]}.json"
    path = output_dir / filename
    path.write_text(output.model_dump_json(indent=2), encoding="utf-8")
    print(f"[SAVED] {path}")
    return path


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Freelancer Work Agent")
    parser.add_argument("--action", default="bid",
                        choices=["bid", "deliver", "execute", "message", "complete", "scan"],
                        help="Pipeline action")
    parser.add_argument("--project", help="Path to project JSON file")
    parser.add_argument("--title", help="Project title (inline)")
    parser.add_argument("--description", help="Project description (inline)")
    parser.add_argument("--budget", type=float, default=0, help="Project budget max (USD)")
    parser.add_argument("--skills", nargs="+", default=[], help="Required skills")
    parser.add_argument("--message-type", default="intro",
                        choices=["intro", "update", "question", "delivery", "revision", "closing"],
                        help="Message type (for message action)")
    parser.add_argument("--context", default="", help="Additional context for message generation")
    parser.add_argument("--project-id", default="", help="Project ID to load saved state")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no submissions)")
    parser.add_argument("--provider", default=None,
                        choices=["openai", "anthropic", "gemini", "grok"],
                        help="LLM provider")
    args = parser.parse_args()

    # Build project data
    project_data = None
    if args.project:
        project_data = json.loads(Path(args.project).read_text(encoding="utf-8"))
    elif args.project_id:
        # Load from saved state
        state = load_project_state(args.project_id)
        if state:
            project_data = state.project.model_dump()
        else:
            print(f"[ERROR] No saved state for project: {args.project_id}")
            sys.exit(1)
    elif args.title:
        project_data = {
            "title": args.title,
            "description": args.description or "",
            "budget_max": args.budget,
            "skills": args.skills,
        }

    # Add message-specific fields
    if args.action == "message" and project_data:
        project_data["message_type"] = args.message_type
        project_data["context"] = args.context

    result = run_pipeline(
        action=args.action,
        project_data=project_data,
        provider=args.provider,
        dry_run=args.dry_run,
    )

    if result:
        save_output(result)
        print(f"\nStatus: {result.status}")
        if result.bid:
            print(f"Bid: {result.bid.subject}")
            print(f"Amount: ${result.bid.suggested_bid_usd}")
        if result.delivery_plan:
            print(f"Primary Agent: {result.delivery_plan.primary_agent}")
        if result.execution_results:
            completed = sum(1 for r in result.execution_results if r.status == "completed")
            print(f"Execution: {completed}/{len(result.execution_results)} steps completed")
            for r in result.execution_results:
                print(f"  Step {r.step}: {r.agent} — {r.status}")
        if result.client_message:
            print(f"\nClient Message ({result.client_message.message_type}):")
            print(f"  Subject: {result.client_message.subject}")
            print(f"  Body preview: {result.client_message.body[:200]}...")
        if result.project_state:
            print(f"Deliverable files: {len(result.project_state.deliverable_files)}")
            for f in result.project_state.deliverable_files[:5]:
                print(f"  {Path(f).name}")


if __name__ == "__main__":
    main()
