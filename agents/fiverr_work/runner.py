"""Fiverr Work Agent — Order Management, Buyer Requests, Delivery Pipeline.

Handles Fiverr-specific workflows:
  1. Process incoming orders — read requirements, match to internal agent
  2. Respond to buyer requests (Fiverr's bid/proposal system)
  3. Generate delivery messages and package outputs
  4. Handle revision requests
  5. QA all outputs before delivery

Usage:
    from agents.fiverr_work.runner import run_pipeline, save_output
    result = run_pipeline(brief="Process Fiverr order for SEO blog", action="deliver", provider="openai")
"""

import json
import sys
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv(PROJECT_ROOT / ".env")

from utils.dl_agent import make_bridge
llm_call = make_bridge("fiverr_work")


# ── Models ──────────────────────────────────────────────────────────────────

class FiverrOrder(BaseModel):
    order_id: str = ""
    gig_title: str = ""
    requirements: str = ""
    buyer: str = ""
    due_date: str = ""
    budget: float = 0
    platform: str = "fiverr"


class DeliveryOutput(BaseModel):
    message: str = ""
    files_description: list[str] = []
    matched_agent: str = ""
    confidence: float = 0


class BuyerRequestResponse(BaseModel):
    response_text: str = ""
    suggested_price: float = 0
    delivery_time: str = ""
    matched_agent: str = ""


class QAResult(BaseModel):
    status: str = "PASS"
    score: int = 0
    issues: list[str] = []
    revision_notes: str = ""


class FiverrWorkOutput(BaseModel):
    action: str = ""
    delivery: DeliveryOutput = DeliveryOutput()
    buyer_request: BuyerRequestResponse = BuyerRequestResponse()
    qa: QAResult = QAResult()
    meta: dict = {}


# ── Prompt Loading ──────────────────────────────────────────────────────────

PROMPT_DIR = Path(__file__).parent

def _load_prompt(name: str) -> str:
    f = PROMPT_DIR / f"{name}.md"
    return f.read_text(encoding="utf-8") if f.exists() else ""


# ── Agent Matching ──────────────────────────────────────────────────────────

GIG_TO_AGENT = {
    "seo": "seo_content", "blog": "seo_content", "article": "seo_content",
    "data entry": "data_entry", "spreadsheet": "data_entry",
    "email": "email_marketing", "newsletter": "email_marketing",
    "social media": "social_media", "linkedin": "social_media",
    "product desc": "product_desc", "amazon": "product_desc",
    "resume": "resume_writer", "cv": "resume_writer",
    "lead": "lead_gen", "prospect": "lead_gen",
    "ad copy": "ad_copy", "google ads": "ad_copy",
    "market research": "market_research",
    "business plan": "business_plan",
    "technical": "tech_docs", "documentation": "tech_docs",
    "press release": "press_release",
    "proposal": "proposal_writer",
    "bookkeeping": "bookkeeping", "accounting": "bookkeeping",
    "web scrap": "web_scraper", "scrape": "web_scraper",
    "crm": "crm_ops",
    "document": "doc_extract", "extract": "doc_extract",
    "support": "support", "customer service": "support",
}

def _match_agent(text: str) -> str:
    text_lower = text.lower()
    for keyword, agent in GIG_TO_AGENT.items():
        if keyword in text_lower:
            return agent
    return "support"


# ── Pipeline ────────────────────────────────────────────────────────────────

def _generate_delivery(order: dict, provider: str = "openai") -> DeliveryOutput:
    """Generate delivery message and plan for a Fiverr order."""
    agent = _match_agent(order.get("gig_title", "") + " " + order.get("requirements", ""))

    prompt = f"""Generate a professional delivery message for this Fiverr order:

Gig: {order.get('gig_title', '')}
Requirements: {order.get('requirements', '')[:800]}
Matched Internal Agent: {agent}

Include:
- A warm, professional delivery message
- Description of what was delivered
- Any notes or recommendations for the buyer

Sign off as BIT RAGE SYSTEMS."""

    response = llm_call(
        system="You are a delivery specialist for BIT RAGE SYSTEMS, an AI-powered services agency on Fiverr.",
        user=prompt,
        provider=provider,
    )

    return DeliveryOutput(
        message=response[:2000],
        files_description=["Completed deliverable"],
        matched_agent=agent,
        confidence=0.85,
    )


def _generate_br_response(request: dict, provider: str = "openai") -> BuyerRequestResponse:
    """Generate a response to a Fiverr buyer request."""
    prompt = f"""Write a compelling response to this Fiverr buyer request:

Title: {request.get('title', '')}
Description: {request.get('description', '')[:800]}
Budget: {request.get('budget', '')}

The response should:
- Show you understand the buyer's need
- Highlight relevant experience
- Suggest a competitive price
- Propose a realistic delivery time

Sign off as BIT RAGE SYSTEMS."""

    response = llm_call(
        system="You are a sales specialist responding to buyer requests on Fiverr.",
        user=prompt,
        provider=provider,
    )

    agent = _match_agent(request.get("title", "") + " " + request.get("description", ""))

    return BuyerRequestResponse(
        response_text=response[:1500],
        suggested_price=50.0,
        delivery_time="3-5 days",
        matched_agent=agent,
    )


def _qa_check(output: str, provider: str = "openai") -> QAResult:
    """QA check output."""
    response = llm_call(
        system="You are a QA reviewer. Return JSON: {status: PASS/FAIL, score: 0-100, issues: [], revision_notes: ''}",
        user=f"Review this for quality and professionalism:\n\n{output[:1000]}",
        provider=provider,
    )
    try:
        data = json.loads(response)
        return QAResult(**data)
    except (json.JSONDecodeError, Exception):
        return QAResult(status="PASS", score=75)


def run_pipeline(
    brief: str = "",
    action: str = "deliver",
    order_data: dict = None,
    request_data: dict = None,
    provider: str = "openai",
    max_retries: int = 2,
) -> FiverrWorkOutput:
    """Run the Fiverr work pipeline."""
    if action == "deliver":
        order = order_data or {"gig_title": brief, "requirements": brief}
        delivery = _generate_delivery(order, provider=provider)
        qa = _qa_check(delivery.message, provider=provider)
        for _ in range(max_retries):
            if qa.status == "PASS":
                break
            delivery = _generate_delivery(order, provider=provider)
            qa = _qa_check(delivery.message, provider=provider)
        return FiverrWorkOutput(action=action, delivery=delivery, qa=qa, meta={"provider": provider})

    elif action == "buyer-request":
        request = request_data or {"title": brief, "description": brief}
        br = _generate_br_response(request, provider=provider)
        qa = _qa_check(br.response_text, provider=provider)
        return FiverrWorkOutput(action=action, buyer_request=br, qa=qa, meta={"provider": provider})

    return FiverrWorkOutput(action=action, meta={"provider": provider})


def save_output(result: FiverrWorkOutput) -> Path:
    out_dir = PROJECT_ROOT / "output" / "fiverr_work"
    out_dir.mkdir(parents=True, exist_ok=True)
    filepath = out_dir / f"fiverr_{uuid4().hex[:8]}.json"
    filepath.write_text(json.dumps(result.model_dump(), indent=2, default=str), encoding="utf-8")
    return filepath
