"""Email Marketing Agent — Design complete email campaigns and sequences.

2-step pipeline:
    1. Strategist Agent — designs campaign with sequences, subject lines, CTAs
    2. QA Agent — validates deliverability, compliance, and effectiveness

Usage:
    python -m agents.email_marketing.runner --business "AI agency" --goal launch
    python -m agents.email_marketing.runner --business "SaaS tool" --goal nurture --count 5
    python -m agents.email_marketing.runner --business "ecommerce store" --goal abandoned_cart
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
call_llm = make_bridge("email_marketing")

PROMPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "email_marketing"


# ── Pydantic Models ────────────────────────────────────────────

class EmailInSequence(BaseModel):
    email_number: int = 0
    send_day: int = 0
    subject_line: str = ""
    preview_text: str = ""
    body_html: str = ""
    body_text: str = ""
    cta_text: str = ""
    cta_url: str = ""
    purpose: str = ""
    word_count: int = 0
    personalization_tokens: list[str] = Field(default_factory=list)


class SubjectVariant(BaseModel):
    email: int = 0
    variant_a: str = ""
    variant_b: str = ""


class CampaignOutput(BaseModel):
    campaign_name: str = ""
    goal: str = ""
    audience_segment: str = ""
    sequence: list[EmailInSequence] = Field(default_factory=list)
    subject_line_variants: list[SubjectVariant] = Field(default_factory=list)
    send_schedule: str = ""
    kpis: dict = Field(default_factory=dict)


class QAResult(BaseModel):
    status: str = "FAIL"
    score: int = 0
    issues: list[str] = Field(default_factory=list)
    revision_notes: str = ""


class EmailMarketingOutput(BaseModel):
    campaign: CampaignOutput = Field(default_factory=CampaignOutput)
    qa: QAResult = Field(default_factory=QAResult)
    meta: dict = Field(default_factory=dict)


# ── Agent Functions ─────────────────────────────────────────────

def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def strategist_agent(
    business: str,
    audience: str = "",
    goal: str = "nurture",
    tone: str = "professional",
    email_count: int = 5,
    context: str = "",
    provider: str = "openai",
) -> CampaignOutput:
    """Step 1: Design the email campaign."""
    system = _load_prompt("strategist_prompt")
    user_msg = (
        f"Business: {business}\n"
        f"Audience: {audience or 'General prospects and leads'}\n"
        f"Goal: {goal}\n"
        f"Tone: {tone}\n"
        f"Email Count: {email_count}\n"
        f"Additional Context: {context}"
    )
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(CampaignOutput, data, agent_name="email_marketing.strategist")


def qa_agent(
    campaign: CampaignOutput,
    provider: str = "openai",
) -> QAResult:
    """Step 2: Validate campaign quality and compliance."""
    system = _load_prompt("qa_prompt")
    user_msg = f"Campaign to validate:\n{json.dumps(campaign.model_dump(), indent=2)}"
    raw = call_llm(system_prompt=system, user_prompt=user_msg,
                   provider=provider, json_mode=True)
    data = json.loads(raw, strict=False)
    return safe_validate(QAResult, data, agent_name="email_marketing.qa")


# ── Pipeline ────────────────────────────────────────────────────

def run_pipeline(
    business: str,
    audience: str = "",
    goal: str = "nurture",
    tone: str = "professional",
    email_count: int = 5,
    context: str = "",
    provider: str = "openai",
    max_retries: int = 2,
) -> EmailMarketingOutput:
    """Run the full email marketing pipeline: Strategist → QA."""
    print(f"\n[EMAIL_MARKETING] Starting pipeline — {goal} campaign")
    print(f"  Business: {business} | Emails: {email_count} | Provider: {provider}")

    # Step 1: Design campaign
    print("\n  [1/2] Designing campaign...")
    campaign = strategist_agent(business, audience, goal, tone,
                                email_count, context, provider)
    print(f"  → {len(campaign.sequence)} emails designed")

    # Step 2: QA (with retries)
    for attempt in range(1, max_retries + 2):
        print(f"\n  [2/2] QA verification (attempt {attempt})...")
        qa = qa_agent(campaign, provider)
        print(f"  → {qa.status} (score: {qa.score})")

        if qa.status == "PASS":
            break

        if attempt <= max_retries and qa.revision_notes:
            print(f"  → Retrying with revision notes...")
            revision_context = f"\n\nPREVIOUS QA FEEDBACK:\n{qa.revision_notes}\nFix all issues above."
            campaign = strategist_agent(business, audience, goal, tone,
                                        email_count, context + revision_context, provider)

    output = EmailMarketingOutput(
        campaign=campaign,
        qa=qa,
        meta={
            "business": business,
            "goal": goal,
            "provider": provider,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    return output


def save_output(output: EmailMarketingOutput) -> Path:
    """Save pipeline output to JSON file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"campaign_{ts}_{run_id}.json"
    path.write_text(json.dumps(output.model_dump(), indent=2, default=str),
                    encoding="utf-8")
    print(f"\n  [SAVED] {path}")
    return path


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Email Marketing Agent")
    parser.add_argument("--business", required=True, help="Business description")
    parser.add_argument("--audience", default="", help="Target audience")
    parser.add_argument("--goal", default="nurture",
                        choices=["nurture", "launch", "re-engagement", "onboarding",
                                 "seasonal", "abandoned_cart", "upsell"])
    parser.add_argument("--tone", default="professional",
                        choices=["professional", "casual", "bold", "friendly", "authoritative"])
    parser.add_argument("--count", type=int, default=5, help="Emails in sequence")
    parser.add_argument("--provider", default="openai", help="LLM provider")
    args = parser.parse_args()

    result = run_pipeline(
        business=args.business,
        audience=args.audience,
        goal=args.goal,
        tone=args.tone,
        email_count=args.count,
        provider=args.provider,
    )
    save_output(result)
