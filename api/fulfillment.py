"""Fiverr Order Fulfillment API Router — Process gig orders through agent pipelines.

Accepts order details from the internal fulfillment web form or CLI tool,
dispatches to the appropriate agent runner, packages output as downloadable
content, records revenue, and returns structured results.

Mount in the main app:
    from api.fulfillment import router as fulfillment_router
    app.include_router(fulfillment_router)
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("api.fulfillment")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HISTORY_FILE = PROJECT_ROOT / "data" / "fulfillment_history.json"

router = APIRouter(prefix="/fulfillment", tags=["fulfillment"])

# ── Gig type configuration ─────────────────────────────────────────────────

GIG_CONFIG = {
    "product_desc": {
        "label": "Product Descriptions",
        "agent_module": "agents.product_desc.runner",
        "runner_fn": "run_pipeline",
        "base_revenue": 25.00,
    },
    "seo_content": {
        "label": "SEO Blog Post",
        "agent_module": "agents.seo_content.runner",
        "runner_fn": "run_pipeline",
        "base_revenue": 75.00,
    },
    "resume": {
        "label": "Resume Writing",
        "agent_module": "agents.resume_writer.runner",
        "runner_fn": "run_pipeline",
        "base_revenue": 35.00,
    },
    "ad_copy": {
        "label": "Ad Copy",
        "agent_module": "agents.ad_copy.runner",
        "runner_fn": "run_pipeline",
        "base_revenue": 40.00,
    },
    "email_sequence": {
        "label": "Email Sequence",
        "agent_module": "agents.email_marketing.runner",
        "runner_fn": "run_pipeline",
        "base_revenue": 100.00,
    },
}

VALID_GIG_TYPES = set(GIG_CONFIG.keys())


# ── Request / Response Models ──────────────────────────────────────────────

class FulfillmentRequest(BaseModel):
    gig_type: str
    requirements: str = Field(..., min_length=10, max_length=32000)
    platform: Optional[str] = None
    audience: Optional[str] = None
    tone: Optional[str] = None
    keywords: Optional[str] = None
    word_count: Optional[int] = Field(None, ge=300, le=5000)
    role: Optional[str] = None

    @field_validator("gig_type")
    @classmethod
    def validate_gig_type(cls, v: str) -> str:
        if v not in VALID_GIG_TYPES:
            raise ValueError(
                f"Invalid gig_type '{v}'. Must be one of: {', '.join(sorted(VALID_GIG_TYPES))}"
            )
        return v


class FulfillmentResponse(BaseModel):
    fulfillment_id: str
    gig_type: str
    status: str
    qa_status: str = ""
    deliverable_text: str = ""
    result: dict = Field(default_factory=dict)
    revenue_usd: float = 0.0
    processing_time: float = 0.0
    timestamp: str = ""


# ── History persistence ────────────────────────────────────────────────────

def _load_history() -> list[dict]:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_history(history: list[dict]) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(
        json.dumps(history[-500:], indent=2, default=str),  # keep last 500
        encoding="utf-8",
    )


def _record_fulfillment(entry: dict) -> None:
    history = _load_history()
    history.append(entry)
    _save_history(history)


# ── Agent dispatch ─────────────────────────────────────────────────────────

def _dispatch_product_desc(req: FulfillmentRequest) -> dict:
    from agents.product_desc.runner import run_pipeline, save_output
    result = run_pipeline(
        product_specs=req.requirements,
        platform=req.platform or "amazon",
        audience=req.audience or "",
        tone=req.tone or "professional",
        keywords=req.keywords or "",
    )
    save_output(result)
    data = result.model_dump()
    text = _format_product_desc(data)
    return {"result": data, "text": text, "qa_status": data.get("qa", {}).get("status", "")}


def _dispatch_seo_content(req: FulfillmentRequest) -> dict:
    from agents.seo_content.runner import run_pipeline, save_output
    kwargs = {
        "topic": req.requirements,
        "content_type": "blog",
        "audience": req.audience or "",
        "tone": req.tone or "professional",
    }
    if req.keywords:
        kwargs["seed_keywords"] = req.keywords
    if req.word_count:
        kwargs["word_count"] = req.word_count
    result = run_pipeline(**kwargs)
    save_output(result)
    data = result.model_dump()
    text = _format_seo_content(data)
    return {"result": data, "text": text, "qa_status": data.get("qa", {}).get("status", "")}


def _dispatch_resume(req: FulfillmentRequest) -> dict:
    from agents.resume_writer.runner import run_pipeline, save_output
    result = run_pipeline(
        career_data=req.requirements,
        target_role=req.role or "",
        industry=req.audience or "",
    )
    save_output(result)
    data = result.model_dump()
    text = _format_resume(data)
    return {"result": data, "text": text, "qa_status": data.get("qa", {}).get("status", "")}


def _dispatch_ad_copy(req: FulfillmentRequest) -> dict:
    from agents.ad_copy.runner import run_pipeline, save_output
    result = run_pipeline(
        product_info=req.requirements,
        platform=req.platform or "google_search",
        audience=req.audience or "",
        tone=req.tone or "professional",
    )
    save_output(result)
    data = result.model_dump()
    text = _format_ad_copy(data)
    return {"result": data, "text": text, "qa_status": data.get("qa", {}).get("status", "")}


def _dispatch_email_sequence(req: FulfillmentRequest) -> dict:
    from agents.email_marketing.runner import run_pipeline, save_output
    result = run_pipeline(
        business_info=req.requirements,
        goal="sales",
        audience=req.audience or "",
        tone=req.tone or "professional",
    )
    save_output(result)
    data = result.model_dump()
    text = _format_email_sequence(data)
    return {"result": data, "text": text, "qa_status": data.get("qa", {}).get("status", "")}


DISPATCHERS = {
    "product_desc": _dispatch_product_desc,
    "seo_content": _dispatch_seo_content,
    "resume": _dispatch_resume,
    "ad_copy": _dispatch_ad_copy,
    "email_sequence": _dispatch_email_sequence,
}


# ── Output formatters ─────────────────────────────────────────────────────

def _format_product_desc(data: dict) -> str:
    desc = data.get("description", {})
    lines = [
        f"PRODUCT: {desc.get('product_name', 'N/A')}",
        f"PLATFORM: {desc.get('platform', 'N/A')}",
        f"\nTITLE: {desc.get('title', '')}",
        "\nBULLET POINTS:",
    ]
    for bp in desc.get("bullet_points", []):
        lines.append(f"  - {bp}")
    lines.append(f"\nSHORT DESCRIPTION:\n{desc.get('short_description', '')}")
    lines.append(f"\nLONG DESCRIPTION:\n{desc.get('long_description', '')}")
    seo = desc.get("seo_meta", {})
    if seo:
        lines.append(f"\nMETA TITLE: {seo.get('meta_title', '')}")
        lines.append(f"META DESCRIPTION: {seo.get('meta_description', '')}")
        kws = seo.get("keywords", [])
        if kws:
            lines.append(f"KEYWORDS: {', '.join(kws)}")
    for v in desc.get("variations", []):
        lines.append(f"\nVARIATION ({v.get('variant', '')}):")
        lines.append(f"  A: {v.get('version_a', '')}")
        lines.append(f"  B: {v.get('version_b', '')}")
    return "\n".join(lines)


def _format_seo_content(data: dict) -> str:
    article = data.get("article", data.get("content", {}))
    lines = []
    if isinstance(article, dict):
        lines.append(f"TITLE: {article.get('title', '')}")
        lines.append(f"META: {article.get('meta_description', '')}")
        lines.append(f"\n{article.get('body', article.get('content', ''))}")
    else:
        lines.append(str(article))
    return "\n".join(lines)


def _format_resume(data: dict) -> str:
    resume = data.get("resume", {})
    lines = []
    if isinstance(resume, dict):
        contact = resume.get("contact", {})
        if contact:
            lines.append(f"{contact.get('name', '')}")
            lines.append(f"{contact.get('email', '')} | {contact.get('phone', '')}")
        lines.append(f"\nSUMMARY:\n{resume.get('summary', '')}")
        for exp in resume.get("experience", []):
            lines.append(f"\n{exp.get('title', '')} at {exp.get('company', '')} ({exp.get('dates', '')})")
            for b in exp.get("bullets", []):
                lines.append(f"  - {b}")
        for edu in resume.get("education", []):
            lines.append(f"\n{edu.get('degree', '')} - {edu.get('school', '')}")
        skills = resume.get("skills", [])
        if skills:
            lines.append(f"\nSKILLS: {', '.join(skills) if isinstance(skills, list) else skills}")
    else:
        lines.append(str(resume))
    return "\n".join(lines)


def _format_ad_copy(data: dict) -> str:
    ads = data.get("ads", data.get("ad_copy", {}))
    lines = []
    if isinstance(ads, dict):
        for platform, variants in ads.items():
            lines.append(f"\n{'='*40}")
            lines.append(f"PLATFORM: {platform.upper()}")
            lines.append(f"{'='*40}")
            if isinstance(variants, list):
                for i, v in enumerate(variants, 1):
                    lines.append(f"\n--- Variant {i} ---")
                    if isinstance(v, dict):
                        for k, val in v.items():
                            lines.append(f"  {k}: {val}")
                    else:
                        lines.append(f"  {v}")
    elif isinstance(ads, list):
        for i, ad in enumerate(ads, 1):
            lines.append(f"\n--- Ad {i} ---")
            lines.append(json.dumps(ad, indent=2) if isinstance(ad, dict) else str(ad))
    else:
        lines.append(str(ads))
    return "\n".join(lines)


def _format_email_sequence(data: dict) -> str:
    emails = data.get("sequence", data.get("emails", data.get("campaign", {})))
    lines = []
    if isinstance(emails, list):
        for i, email in enumerate(emails, 1):
            lines.append(f"\n{'='*40}")
            lines.append(f"EMAIL {i}")
            lines.append(f"{'='*40}")
            if isinstance(email, dict):
                lines.append(f"Subject: {email.get('subject', email.get('subject_line', ''))}")
                lines.append(f"Preheader: {email.get('preheader', '')}")
                lines.append(f"\n{email.get('body', email.get('content', ''))}")
            else:
                lines.append(str(email))
    elif isinstance(emails, dict):
        lines.append(json.dumps(emails, indent=2))
    else:
        lines.append(str(emails))
    return "\n".join(lines)


# ── Revenue tracking ──────────────────────────────────────────────────────

def _record_revenue(gig_type: str, revenue: float, fulfillment_id: str) -> None:
    """Attempt to record revenue in the platform tracker."""
    try:
        from income.tracker import record_income
        record_income(
            source="fiverr",
            category=gig_type,
            amount=revenue,
            reference=fulfillment_id,
        )
    except ImportError:
        logger.debug("income.tracker not available — skipping revenue recording")
    except Exception as e:
        logger.warning("Revenue recording failed: %s", e)


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
def fulfillment_form():
    """Serve the fulfillment intake web form."""
    html_path = PROJECT_ROOT / "site" / "fulfillment.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Fulfillment form not found")
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@router.post("/process", response_model=FulfillmentResponse)
def process_order(req: FulfillmentRequest):
    """Accept a Fiverr order, dispatch to the appropriate agent, return result.

    Steps:
    1. Validate gig type and inputs
    2. Dispatch to agent runner pipeline
    3. Package output as deliverable text
    4. Record fulfillment in history and revenue tracker
    5. Return structured response
    """
    fulfillment_id = f"ff-{uuid.uuid4().hex[:12]}"
    start = time.time()
    timestamp = datetime.now(timezone.utc).isoformat()

    logger.info(
        "[FULFILLMENT] %s — gig=%s, requirements=%d chars",
        fulfillment_id, req.gig_type, len(req.requirements),
    )

    dispatcher = DISPATCHERS.get(req.gig_type)
    if not dispatcher:
        raise HTTPException(status_code=400, detail=f"No dispatcher for gig type: {req.gig_type}")

    try:
        output = dispatcher(req)
    except Exception as e:
        logger.exception("[FULFILLMENT] %s failed", fulfillment_id)
        elapsed = round(time.time() - start, 2)
        _record_fulfillment({
            "fulfillment_id": fulfillment_id,
            "gig_type": req.gig_type,
            "status": "failed",
            "qa_status": "FAIL",
            "error": str(e),
            "revenue_usd": 0.0,
            "processing_time": elapsed,
            "timestamp": timestamp,
        })
        raise HTTPException(status_code=500, detail=f"Agent pipeline failed: {str(e)}")

    elapsed = round(time.time() - start, 2)
    qa_status = output.get("qa_status", "")
    revenue = GIG_CONFIG[req.gig_type]["base_revenue"]

    # Record
    entry = {
        "fulfillment_id": fulfillment_id,
        "gig_type": req.gig_type,
        "status": "completed",
        "qa_status": qa_status,
        "revenue_usd": revenue,
        "processing_time": elapsed,
        "timestamp": timestamp,
    }
    _record_fulfillment(entry)
    _record_revenue(req.gig_type, revenue, fulfillment_id)

    logger.info(
        "[FULFILLMENT] %s complete — qa=%s, time=%.1fs, revenue=$%.2f",
        fulfillment_id, qa_status, elapsed, revenue,
    )

    return FulfillmentResponse(
        fulfillment_id=fulfillment_id,
        gig_type=req.gig_type,
        status="completed",
        qa_status=qa_status,
        deliverable_text=output.get("text", ""),
        result=output.get("result", {}),
        revenue_usd=revenue,
        processing_time=elapsed,
        timestamp=timestamp,
    )


@router.get("/history")
def fulfillment_history(limit: int = 50):
    """Return recent fulfillment history."""
    history = _load_history()
    history.reverse()  # newest first
    return {"history": history[:limit], "total": len(history)}
