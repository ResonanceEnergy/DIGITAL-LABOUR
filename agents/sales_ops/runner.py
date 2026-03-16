"""Sales Ops Agent — Lead Enrichment + Personalized Outreach Pipeline.

Usage:
    python runner.py --company "Acme Corp" --role "Head of Growth"
    python runner.py --company "https://example.com" --role "CTO" --product "We help B2B teams automate outbound"
    python runner.py --batch leads.csv --product "We help B2B teams automate outbound"
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv(PROJECT_ROOT / ".env")

sys.path.insert(0, str(PROJECT_ROOT))
from utils.dl_agent import make_bridge
llm_call = make_bridge("sales_ops", chain_of_thought=False)


# ── Models ──────────────────────────────────────────────────────────────────

class LeadEnrichment(BaseModel):
    company_name: str
    company_website: str = ""
    industry: str = ""
    company_size_estimate: str = ""
    recent_signal: str
    signal_source: str = ""
    contact_name: str = ""
    contact_role: str = ""
    contact_email_guess: str = ""
    linkedin_url: str = ""
    role_relevant_pain: str = ""
    personalization_angle: str


class EmailMessage(BaseModel):
    subject: str
    body: str


class EmailSequence(BaseModel):
    primary_email: EmailMessage
    follow_up_1: EmailMessage
    follow_up_2: EmailMessage


class QAResult(BaseModel):
    status: str = Field(pattern=r"^(PASS|FAIL)$")
    issues: list[str] = []
    revision_notes: str = ""


class SalesOpsOutput(BaseModel):
    lead_enrichment: LeadEnrichment
    emails: EmailSequence
    qa_status: str


# ── Prompt Loading ──────────────────────────────────────────────────────────

AGENT_DIR = Path(__file__).parent

def load_prompt(name: str) -> str:
    path = AGENT_DIR / f"{name}_prompt.md"
    return path.read_text(encoding="utf-8")


# ── LLM Call ────────────────────────────────────────────────────────────────

def call_llm(system_prompt: str, user_message: str, provider: str | None = None) -> str:
    return llm_call(system_prompt, user_message, provider=provider, temperature=0.7, json_mode=True)


# ── Agent Functions ─────────────────────────────────────────────────────────

def research_agent(company: str, role: str, provider: str | None = None) -> LeadEnrichment:
    """Step 1: Research and enrich a lead."""
    prompt = load_prompt("research")
    user_msg = f"Company: {company}\nTarget Role: {role}"
    raw = call_llm(prompt, user_msg, provider)
    data = json.loads(raw, strict=False)
    return LeadEnrichment.model_validate(data)


def copy_agent(enrichment: LeadEnrichment, product: str, tone: str = "direct", provider: str | None = None) -> EmailSequence:
    """Step 2: Generate personalized outreach emails."""
    prompt = load_prompt("copywriter")
    user_msg = json.dumps({
        "enrichment": enrichment.model_dump(),
        "product_description": product,
        "tone": tone,
    }, indent=2)
    raw = call_llm(prompt, user_msg, provider)
    data = json.loads(raw, strict=False)
    return EmailSequence.model_validate(data)


def qa_agent(enrichment: LeadEnrichment, emails: EmailSequence, provider: str | None = None) -> QAResult:
    """Step 3: Quality check the output."""
    prompt = load_prompt("../qa/verifier")
    user_msg = json.dumps({
        "lead_enrichment": enrichment.model_dump(),
        "emails": emails.model_dump(),
    }, indent=2)
    raw = call_llm(prompt, user_msg, provider)
    data = json.loads(raw, strict=False)
    return QAResult.model_validate(data)


# ── Pipeline ────────────────────────────────────────────────────────────────

def run_pipeline(
    company: str,
    role: str,
    product: str = "We help companies automate repetitive business processes with AI agents.",
    tone: str = "direct",
    max_retries: int = 1,
    provider: str | None = None,
) -> SalesOpsOutput | None:
    """Run the full Sales Ops pipeline: Research → Copy → QA (with retry)."""
    start = time.time()

    print(f"[RESEARCH] Enriching: {company} / {role}")
    enrichment = research_agent(company, role, provider)

    print(f"[COPY] Generating outreach sequence...")
    emails = copy_agent(enrichment, product, tone, provider)

    for attempt in range(1 + max_retries):
        print(f"[QA] Verifying (attempt {attempt + 1})...")
        qa = qa_agent(enrichment, emails, provider)

        if qa.status == "PASS":
            elapsed = round(time.time() - start, 1)
            print(f"[PASS] Lead ready in {elapsed}s")
            return SalesOpsOutput(
                lead_enrichment=enrichment,
                emails=emails,
                qa_status="PASS",
            )
        else:
            print(f"[FAIL] Issues: {qa.issues}")
            if attempt < max_retries:
                print(f"[RETRY] Regenerating copy with revision notes...")
                revision_prompt = f"{product}\n\nREVISION REQUIRED: {qa.revision_notes}"
                emails = copy_agent(enrichment, revision_prompt, tone, provider)

    print("[FAILED] Could not pass QA after retries. Flagged for human review.")
    return SalesOpsOutput(
        lead_enrichment=enrichment,
        emails=emails,
        qa_status="FAIL",
    )


# ── Output ──────────────────────────────────────────────────────────────────

def save_output(output: SalesOpsOutput, output_dir: Path | None = None) -> Path:
    """Save output as JSON."""
    output_dir = output_dir or PROJECT_ROOT / "output" / "sales_ops"
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{output.lead_enrichment.company_name.replace(' ', '_')}_{uuid4().hex[:6]}.json"
    path = output_dir / filename
    path.write_text(output.model_dump_json(indent=2), encoding="utf-8")
    print(f"[SAVED] {path}")
    return path


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Sales Ops Agent — Lead Enrichment + Outreach")
    parser.add_argument("--company", required=True, help="Company name or URL")
    parser.add_argument("--role", required=True, help="Target role (e.g. 'Head of Growth')")
    parser.add_argument("--product", default="We help companies automate repetitive business processes with AI agents.", help="Your product description")
    parser.add_argument("--tone", default="direct", choices=["neutral", "casual", "direct"], help="Email tone")
    parser.add_argument("--provider", default=None, choices=["openai", "anthropic", "gemini", "grok"], help="LLM provider")
    args = parser.parse_args()

    result = run_pipeline(args.company, args.role, args.product, args.tone, provider=args.provider)
    if result:
        save_output(result)
        if result.qa_status == "PASS":
            print("\n✅ Lead pack ready to sell.")
        else:
            print("\n⚠️  Lead pack needs human review before selling.")


if __name__ == "__main__":
    main()
