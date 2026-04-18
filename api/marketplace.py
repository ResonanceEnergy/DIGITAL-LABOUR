"""Marketplace API Router -- Exposes top 8 BRL agents as clean API products.

Each endpoint accepts a simple, validated request body, routes to the existing
dispatcher pipeline, and returns clean JSON output.  Designed for listing on
RapidAPI / Zyla API Hub.

Authentication: X-API-Key header (validated against client hashes or RapidAPI proxy secret).
Rate limiting:  100 req/day (free), 1000 req/day (paid), enforced per API key.

Mount in the main app:
    from api.marketplace import router as marketplace_router
    app.include_router(marketplace_router)
"""

import hashlib
import json
import logging
import os
import sqlite3
import time
import threading
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("api.marketplace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ── Rate Limiting (per-key daily counter, SQLite-backed) ─────────────────────

_RATE_DB = PROJECT_ROOT / "data" / "marketplace_rate.db"
_rate_lock = threading.Lock()

_FREE_LIMIT = 100
_PAID_LIMIT = 1000

# In-memory cache: key_hash -> {"count": int, "date": str, "tier": str}
_rate_cache: dict[str, dict] = {}


def _init_rate_db() -> None:
    """Ensure the rate-limit SQLite table exists."""
    _RATE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_RATE_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            key_hash  TEXT PRIMARY KEY,
            tier      TEXT DEFAULT 'free',
            label     TEXT DEFAULT '',
            created   TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rate_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            key_hash  TEXT NOT NULL,
            date      TEXT NOT NULL,
            count     INTEGER DEFAULT 0,
            UNIQUE(key_hash, date)
        )
    """)
    conn.commit()
    conn.close()


try:
    _init_rate_db()
except Exception as _exc:
    import logging as _lg
    _lg.getLogger(__name__).warning("[MARKETPLACE] Deferred rate DB init: %s", _exc)


def _get_daily_count(key_hash: str) -> int:
    """Return today's request count for a given API key hash."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with _rate_lock:
        cached = _rate_cache.get(key_hash)
        if cached and cached["date"] == today:
            return cached["count"]
    conn = sqlite3.connect(str(_RATE_DB))
    row = conn.execute(
        "SELECT count FROM rate_log WHERE key_hash = ? AND date = ?",
        (key_hash, today),
    ).fetchone()
    conn.close()
    count = row[0] if row else 0
    with _rate_lock:
        _rate_cache[key_hash] = {"count": count, "date": today, "tier": "free"}
    return count


def _increment_count(key_hash: str) -> int:
    """Increment and return today's request count."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = sqlite3.connect(str(_RATE_DB))
    conn.execute(
        """INSERT INTO rate_log (key_hash, date, count) VALUES (?, ?, 1)
           ON CONFLICT(key_hash, date) DO UPDATE SET count = count + 1""",
        (key_hash, today),
    )
    conn.commit()
    row = conn.execute(
        "SELECT count FROM rate_log WHERE key_hash = ? AND date = ?",
        (key_hash, today),
    ).fetchone()
    conn.close()
    new_count = row[0] if row else 1
    with _rate_lock:
        _rate_cache[key_hash] = {"count": new_count, "date": today, "tier": "free"}
    return new_count


def _get_key_tier(key_hash: str) -> str:
    """Return the tier ('free' or 'paid') for an API key."""
    conn = sqlite3.connect(str(_RATE_DB))
    row = conn.execute("SELECT tier FROM api_keys WHERE key_hash = ?", (key_hash,)).fetchone()
    conn.close()
    return row[0] if row else "free"


# ── Authentication + Rate Limit Dependency ───────────────────────────────────

RAPIDAPI_SECRET = os.getenv("RAPIDAPI_SECRET", "")


async def verify_marketplace_key(
    x_rapidapi_proxy_secret: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
) -> str:
    """Authenticate the caller and enforce daily rate limits.

    Returns the key_hash for tracking.  Raises 401/403/429 on failure.
    """
    key_hash: str = ""

    # Path 1: RapidAPI proxy secret
    if RAPIDAPI_SECRET and x_rapidapi_proxy_secret:
        if x_rapidapi_proxy_secret != RAPIDAPI_SECRET:
            raise HTTPException(status_code=403, detail="Invalid RapidAPI proxy secret")
        key_hash = hashlib.sha256(x_rapidapi_proxy_secret.encode()).hexdigest()

    # Path 2: Direct X-API-Key
    elif x_api_key:
        key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
        # Validate against stored client hashes
        clients_dir = PROJECT_ROOT / "clients"
        valid = False
        if clients_dir.exists():
            for profile_path in clients_dir.glob("*.json"):
                try:
                    profile = json.loads(profile_path.read_text(encoding="utf-8"))
                    if profile.get("api_key_hash") == key_hash:
                        valid = True
                        break
                except Exception:
                    continue
        # Also check the rate DB for pre-registered keys
        if not valid:
            conn = sqlite3.connect(str(_RATE_DB))
            row = conn.execute("SELECT key_hash FROM api_keys WHERE key_hash = ?", (key_hash,)).fetchone()
            conn.close()
            if row:
                valid = True
        if not valid and RAPIDAPI_SECRET:
            raise HTTPException(status_code=403, detail="Invalid API key")

    # Path 3: No auth in dev mode
    elif not RAPIDAPI_SECRET:
        key_hash = "dev_anonymous"

    else:
        raise HTTPException(
            status_code=401,
            detail="API key required. Pass your key via the X-API-Key header.",
        )

    # ── Rate limit check ──────────────────────────────────────
    tier = _get_key_tier(key_hash)
    limit = _PAID_LIMIT if tier == "paid" else _FREE_LIMIT
    current = _get_daily_count(key_hash)

    if current >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily rate limit exceeded ({limit} requests/day for {tier} tier). Resets at midnight UTC.",
            headers={"Retry-After": "3600"},
        )

    _increment_count(key_hash)
    return key_hash


# ── Request / Response Models ────────────────────────────────────────────────

class ProductDescriptionRequest(BaseModel):
    """Generate an e-commerce product description."""
    product_specs: str = Field(..., min_length=10, description="Product specifications and features")
    platform: str = Field(default="general", description="Target e-commerce platform")
    audience: str = Field(default="", description="Target audience")
    tone: str = Field(default="persuasive", description="Writing tone")
    keywords: str = Field(default="", description="Comma-separated SEO keywords")
    provider: str = Field(default="", description="LLM provider preference")

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        allowed = {"amazon", "shopify", "ebay", "etsy", "walmart", "general"}
        if v and v not in allowed:
            raise ValueError(f"Platform must be one of: {', '.join(sorted(allowed))}")
        return v


class SEOContentRequest(BaseModel):
    """Generate an SEO-optimized blog post or article."""
    topic: str = Field(..., min_length=5, description="Blog post topic or keyword cluster")
    content_type: str = Field(default="blog_post", description="Content type")
    tone: str = Field(default="professional", description="Writing tone")
    audience: str = Field(default="", description="Target audience")
    provider: str = Field(default="", description="LLM provider preference")

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        allowed = {"blog_post", "pillar_page", "landing_page", "listicle", "how_to"}
        if v and v not in allowed:
            raise ValueError(f"content_type must be one of: {', '.join(sorted(allowed))}")
        return v


class ResumeRequest(BaseModel):
    """Generate a professional resume."""
    career_data: str = Field(..., min_length=20, description="Career history, skills, education")
    target_role: str = Field(default="", description="Target job title")
    target_industry: str = Field(default="", description="Target industry")
    style: str = Field(default="combination", description="Resume format style")
    level: str = Field(default="mid", description="Career level")
    provider: str = Field(default="", description="LLM provider preference")

    @field_validator("style")
    @classmethod
    def validate_style(cls, v: str) -> str:
        allowed = {"chronological", "functional", "combination", "modern"}
        if v and v not in allowed:
            raise ValueError(f"style must be one of: {', '.join(sorted(allowed))}")
        return v

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        allowed = {"entry", "mid", "senior", "executive"}
        if v and v not in allowed:
            raise ValueError(f"level must be one of: {', '.join(sorted(allowed))}")
        return v


class AdCopyRequest(BaseModel):
    """Generate advertising copy for a specific platform."""
    product: str = Field(..., min_length=10, description="Product/service description or brief")
    platform: str = Field(default="google_search", description="Advertising platform")
    audience: str = Field(default="", description="Target audience")
    goal: str = Field(default="conversions", description="Campaign objective")
    provider: str = Field(default="", description="LLM provider preference")

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        allowed = {"google_search", "google_display", "facebook", "instagram", "linkedin", "twitter", "tiktok"}
        if v and v not in allowed:
            raise ValueError(f"platform must be one of: {', '.join(sorted(allowed))}")
        return v

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, v: str) -> str:
        allowed = {"conversions", "awareness", "traffic", "engagement", "leads"}
        if v and v not in allowed:
            raise ValueError(f"goal must be one of: {', '.join(sorted(allowed))}")
        return v


class EmailSequenceRequest(BaseModel):
    """Generate an email marketing sequence."""
    business: str = Field(..., min_length=10, description="Business or product description")
    audience: str = Field(default="", description="Target audience")
    goal: str = Field(default="nurture", description="Sequence goal")
    tone: str = Field(default="professional", description="Email tone")
    email_count: int = Field(default=5, ge=2, le=10, description="Number of emails")
    provider: str = Field(default="", description="LLM provider preference")

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, v: str) -> str:
        allowed = {"nurture", "onboarding", "re-engagement", "upsell", "launch", "webinar"}
        if v and v not in allowed:
            raise ValueError(f"goal must be one of: {', '.join(sorted(allowed))}")
        return v


class PressReleaseRequest(BaseModel):
    """Generate a press release."""
    announcement: str = Field(..., min_length=15, description="News or announcement")
    company_name: str = Field(default="", description="Company name")
    release_type: str = Field(default="product_launch", description="Press release type")
    tone: str = Field(default="professional", description="Writing tone")
    provider: str = Field(default="", description="LLM provider preference")

    @field_validator("release_type")
    @classmethod
    def validate_release_type(cls, v: str) -> str:
        allowed = {"product_launch", "funding", "partnership", "milestone", "executive_hire", "event", "general"}
        if v and v not in allowed:
            raise ValueError(f"release_type must be one of: {', '.join(sorted(allowed))}")
        return v


class TechDocsRequest(BaseModel):
    """Generate technical documentation."""
    content: str = Field(..., min_length=10, description="Source code or technical content")
    doc_type: str = Field(default="api_reference", description="Documentation type")
    audience: str = Field(default="developers", description="Target audience")
    framework: str = Field(default="", description="Framework/technology context")
    provider: str = Field(default="", description="LLM provider preference")

    @field_validator("doc_type")
    @classmethod
    def validate_doc_type(cls, v: str) -> str:
        allowed = {"api_reference", "readme", "tutorial", "architecture", "changelog", "runbook"}
        if v and v not in allowed:
            raise ValueError(f"doc_type must be one of: {', '.join(sorted(allowed))}")
        return v


class DataExtractRequest(BaseModel):
    """Extract structured data from a document."""
    document_text: str = Field(..., min_length=10, description="Document text to extract from")
    doc_type: str = Field(default="auto", description="Document type or 'auto' for detection")
    provider: str = Field(default="", description="LLM provider preference")

    @field_validator("doc_type")
    @classmethod
    def validate_doc_type(cls, v: str) -> str:
        allowed = {"invoice", "contract", "resume", "receipt", "report", "auto"}
        if v and v not in allowed:
            raise ValueError(f"doc_type must be one of: {', '.join(sorted(allowed))}")
        return v


class GrantProposalRequest(BaseModel):
    """Generate a grant proposal."""
    content: str = Field(..., min_length=10, description="Project description and objectives")
    grant_type: str = Field(default="sbir_phase1", description="Grant program type")
    agency: str = Field(default="sba", description="Target funding agency")
    provider: str = Field(default="", description="LLM provider preference")

    @field_validator("grant_type")
    @classmethod
    def validate_grant_type(cls, v: str) -> str:
        allowed = {"sbir_phase1", "sbir_phase2", "sttr", "r01", "nsf_seed", "general"}
        if v and v not in allowed:
            raise ValueError(f"grant_type must be one of: {', '.join(sorted(allowed))}")
        return v

    @field_validator("agency")
    @classmethod
    def validate_agency(cls, v: str) -> str:
        allowed = {"sba", "nsf", "nih", "doe", "dod", "usda", "general"}
        if v and v not in allowed:
            raise ValueError(f"agency must be one of: {', '.join(sorted(allowed))}")
        return v


class ComplianceDocRequest(BaseModel):
    """Generate a compliance document."""
    content: str = Field(..., min_length=10, description="Company details and compliance requirements")
    doc_type: str = Field(default="employee_handbook", description="Compliance document type")
    company: str = Field(default="", description="Company name")
    jurisdiction: str = Field(default="us_federal", description="Legal jurisdiction")
    provider: str = Field(default="", description="LLM provider preference")

    @field_validator("doc_type")
    @classmethod
    def validate_doc_type(cls, v: str) -> str:
        allowed = {"employee_handbook", "privacy_policy", "terms_of_service", "hipaa", "gdpr", "sox", "general"}
        if v and v not in allowed:
            raise ValueError(f"doc_type must be one of: {', '.join(sorted(allowed))}")
        return v

    @field_validator("jurisdiction")
    @classmethod
    def validate_jurisdiction(cls, v: str) -> str:
        allowed = {"us_federal", "us_state", "eu", "uk", "canada", "australia", "general"}
        if v and v not in allowed:
            raise ValueError(f"jurisdiction must be one of: {', '.join(sorted(allowed))}")
        return v


class InsuranceAppealRequest(BaseModel):
    """Generate an insurance appeal letter."""
    content: str = Field(..., min_length=10, description="Claim details and denial information")
    letter_type: str = Field(default="first_level_appeal", description="Appeal letter type")
    urgency: str = Field(default="routine", description="Urgency level")
    provider: str = Field(default="", description="LLM provider preference")

    @field_validator("letter_type")
    @classmethod
    def validate_letter_type(cls, v: str) -> str:
        allowed = {"first_level_appeal", "second_level_appeal", "external_review", "expedited", "general"}
        if v and v not in allowed:
            raise ValueError(f"letter_type must be one of: {', '.join(sorted(allowed))}")
        return v

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, v: str) -> str:
        allowed = {"routine", "urgent", "expedited", "emergency"}
        if v and v not in allowed:
            raise ValueError(f"urgency must be one of: {', '.join(sorted(allowed))}")
        return v


class DataReportRequest(BaseModel):
    """Generate a data report."""
    content: str = Field(..., min_length=10, description="Raw data or data description to report on")
    report_type: str = Field(default="monthly_performance", description="Report type")
    period: str = Field(default="", description="Reporting period")
    audience: str = Field(default="executive", description="Target audience")
    provider: str = Field(default="", description="LLM provider preference")

    @field_validator("report_type")
    @classmethod
    def validate_report_type(cls, v: str) -> str:
        allowed = {"monthly_performance", "quarterly_review", "annual_summary", "kpi_dashboard", "ad_hoc", "general"}
        if v and v not in allowed:
            raise ValueError(f"report_type must be one of: {', '.join(sorted(allowed))}")
        return v

    @field_validator("audience")
    @classmethod
    def validate_audience(cls, v: str) -> str:
        allowed = {"executive", "board", "team", "stakeholders", "technical", "general"}
        if v and v not in allowed:
            raise ValueError(f"audience must be one of: {', '.join(sorted(allowed))}")
        return v


class MarketplaceResponse(BaseModel):
    """Standard response wrapper for all marketplace endpoints."""
    task_id: str = Field(description="Unique task identifier")
    agent: str = Field(description="Agent that processed the request")
    status: str = Field(description="Processing status: completed | failed")
    processing_time_ms: int = Field(description="Wall-clock processing time in milliseconds")
    result: dict = Field(description="Agent output payload")
    qa_status: str = Field(default="UNKNOWN", description="Quality assurance verdict")


# ── Router ───────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/v1", tags=["Marketplace"])


def _dispatch(task_type: str, inputs: dict, key_hash: str) -> MarketplaceResponse:
    """Route a request to the dispatcher and return a MarketplaceResponse.

    This is the shared execution path for all marketplace endpoints. It:
    1. Creates a dispatcher event
    2. Routes to the correct agent pipeline
    3. Wraps the output in a clean response
    """
    start = time.time()
    try:
        from dispatcher.router import create_event, route_task

        if inputs.get("provider"):
            inputs["provider"] = inputs["provider"]

        event = create_event(
            task_type=task_type,
            inputs=inputs,
            client_id=f"marketplace_{key_hash[:12]}",
        )
        result = route_task(event)
        elapsed = int((time.time() - start) * 1000)

        qa_status = result.get("qa", {}).get("status", "UNKNOWN")
        outputs = result.get("outputs", {})

        if qa_status == "FAIL" and not outputs:
            issues = result.get("qa", {}).get("issues", ["Processing failed"])
            raise HTTPException(
                status_code=422,
                detail=f"Agent returned FAIL: {'; '.join(issues)}",
            )

        return MarketplaceResponse(
            task_id=result.get("event_id", str(uuid4())),
            agent=task_type,
            status="completed" if qa_status == "PASS" else "completed_with_warnings",
            processing_time_ms=elapsed,
            result=outputs if isinstance(outputs, dict) else {"output": outputs},
            qa_status=qa_status,
        )

    except HTTPException:
        raise
    except Exception as exc:
        elapsed = int((time.time() - start) * 1000)
        logger.exception("[MARKETPLACE] %s failed after %dms", task_type, elapsed)
        raise HTTPException(status_code=500, detail="Internal processing error") from exc


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/product-description", response_model=MarketplaceResponse)
async def generate_product_description(
    req: ProductDescriptionRequest,
    key_hash: str = Depends(verify_marketplace_key),
):
    """Generate an e-commerce product description optimized for the target platform.

    Accepts raw product specs and returns a structured listing with title,
    description, bullet points, and SEO keywords.
    """
    inputs = {
        "raw_input": req.product_specs,
        "platform": req.platform,
        "audience": req.audience,
        "tone": req.tone,
        "keywords": req.keywords,
    }
    if req.provider:
        inputs["provider"] = req.provider
    return _dispatch("product_desc", inputs, key_hash)


@router.post("/seo-content", response_model=MarketplaceResponse)
async def generate_seo_content(
    req: SEOContentRequest,
    key_hash: str = Depends(verify_marketplace_key),
):
    """Generate an SEO-optimized blog post with keyword analysis and meta tags.

    Returns a full article with heading structure, meta title/description,
    and keyword density analysis.
    """
    inputs = {
        "topic": req.topic,
        "content_type": req.content_type,
        "tone": req.tone,
        "audience": req.audience,
    }
    if req.provider:
        inputs["provider"] = req.provider
    return _dispatch("seo_content", inputs, key_hash)


@router.post("/resume", response_model=MarketplaceResponse)
async def generate_resume(
    req: ResumeRequest,
    key_hash: str = Depends(verify_marketplace_key),
):
    """Generate a professional, ATS-optimized resume from career data.

    Accepts unstructured career history and returns a polished resume with
    summary, skills, and structured experience sections.
    """
    inputs = {
        "raw_input": req.career_data,
        "target_role": req.target_role,
        "industry": req.target_industry,
        "style": req.style,
        "level": req.level,
    }
    if req.provider:
        inputs["provider"] = req.provider
    return _dispatch("resume_writer", inputs, key_hash)


@router.post("/ad-copy", response_model=MarketplaceResponse)
async def generate_ad_copy(
    req: AdCopyRequest,
    key_hash: str = Depends(verify_marketplace_key),
):
    """Generate platform-specific ad copy with headlines, descriptions, and CTAs.

    Respects platform character limits and best practices for Google Ads,
    Facebook, Instagram, LinkedIn, Twitter, and TikTok.
    """
    inputs = {
        "brief": req.product,
        "platform": req.platform,
        "audience": req.audience,
        "goal": req.goal,
    }
    if req.provider:
        inputs["provider"] = req.provider
    return _dispatch("ad_copy", inputs, key_hash)


@router.post("/email-sequence", response_model=MarketplaceResponse)
async def generate_email_sequence(
    req: EmailSequenceRequest,
    key_hash: str = Depends(verify_marketplace_key),
):
    """Generate a multi-email drip sequence with subject lines and send timing.

    Supports nurture, onboarding, re-engagement, upsell, launch, and
    webinar sequences with 2-10 emails.
    """
    inputs = {
        "business": req.business,
        "audience": req.audience,
        "goal": req.goal,
        "tone": req.tone,
        "email_count": req.email_count,
    }
    if req.provider:
        inputs["provider"] = req.provider
    return _dispatch("email_marketing", inputs, key_hash)


@router.post("/press-release", response_model=MarketplaceResponse)
async def generate_press_release(
    req: PressReleaseRequest,
    key_hash: str = Depends(verify_marketplace_key),
):
    """Generate an AP-style press release with headline, body, and quotes.

    Supports product launches, funding announcements, partnerships,
    milestones, and executive hires.
    """
    inputs = {
        "announcement": req.announcement,
        "company_name": req.company_name,
        "release_type": req.release_type,
        "tone": req.tone,
    }
    if req.provider:
        inputs["provider"] = req.provider
    return _dispatch("press_release", inputs, key_hash)


@router.post("/tech-docs", response_model=MarketplaceResponse)
async def generate_tech_docs(
    req: TechDocsRequest,
    key_hash: str = Depends(verify_marketplace_key),
):
    """Generate technical documentation from source code or specifications.

    Supports API references, READMEs, tutorials, architecture docs,
    changelogs, and runbooks.
    """
    inputs = {
        "content": req.content,
        "doc_type": req.doc_type,
        "audience": req.audience,
        "framework": req.framework,
    }
    if req.provider:
        inputs["provider"] = req.provider
    return _dispatch("tech_docs", inputs, key_hash)


@router.post("/data-extract", response_model=MarketplaceResponse)
async def extract_data(
    req: DataExtractRequest,
    key_hash: str = Depends(verify_marketplace_key),
):
    """Extract structured data from unstructured document text.

    Automatically detects document type and returns entities, amounts,
    dates, and other fields with confidence scores.
    """
    inputs = {
        "document_text": req.document_text,
        "doc_type": req.doc_type,
    }
    if req.provider:
        inputs["provider"] = req.provider
    return _dispatch("doc_extract", inputs, key_hash)


@router.post("/grant-proposal", response_model=MarketplaceResponse)
async def generate_grant_proposal(
    req: GrantProposalRequest,
    key_hash: str = Depends(verify_marketplace_key),
):
    """Generate a grant proposal tailored to the target agency and program.

    Produces a structured proposal with project narrative, budget justification,
    specific aims, and compliance sections for SBIR, STTR, NIH, NSF, and more.
    """
    inputs = {
        "content": req.content,
        "grant_type": req.grant_type,
        "agency": req.agency,
    }
    if req.provider:
        inputs["provider"] = req.provider
    return _dispatch("grant_proposal", inputs, key_hash)


@router.post("/compliance-doc", response_model=MarketplaceResponse)
async def generate_compliance_doc(
    req: ComplianceDocRequest,
    key_hash: str = Depends(verify_marketplace_key),
):
    """Generate a compliance document for the specified jurisdiction and type.

    Produces employee handbooks, privacy policies, terms of service, and
    regulatory compliance documents tailored to HIPAA, GDPR, SOX, and more.
    """
    inputs = {
        "content": req.content,
        "doc_type": req.doc_type,
        "company": req.company,
        "jurisdiction": req.jurisdiction,
    }
    if req.provider:
        inputs["provider"] = req.provider
    return _dispatch("compliance_document", inputs, key_hash)


@router.post("/insurance-appeal", response_model=MarketplaceResponse)
async def generate_insurance_appeal(
    req: InsuranceAppealRequest,
    key_hash: str = Depends(verify_marketplace_key),
):
    """Generate an insurance appeal letter for denied claims.

    Produces structured appeal letters with medical necessity arguments,
    policy references, and supporting documentation guidance for first-level,
    second-level, and external review appeals.
    """
    inputs = {
        "content": req.content,
        "letter_type": req.letter_type,
        "urgency": req.urgency,
    }
    if req.provider:
        inputs["provider"] = req.provider
    return _dispatch("insurance_appeal", inputs, key_hash)


@router.post("/data-report", response_model=MarketplaceResponse)
async def generate_data_report(
    req: DataReportRequest,
    key_hash: str = Depends(verify_marketplace_key),
):
    """Generate a data-driven report with analysis and visualizations.

    Produces executive summaries, KPI dashboards, monthly/quarterly performance
    reports, and ad-hoc analyses with charts, tables, and recommendations.
    """
    inputs = {
        "content": req.content,
        "report_type": req.report_type,
        "period": req.period,
        "audience": req.audience,
    }
    if req.provider:
        inputs["provider"] = req.provider
    return _dispatch("data_report", inputs, key_hash)


# ── Marketplace Info ─────────────────────────────────────────────────────────

@router.get("/catalog")
async def marketplace_catalog():
    """List all available marketplace API products with pricing and rate limits."""
    return {
        "marketplace": "DIGITAL LABOUR AI Agents",
        "version": "1.0.0",
        "products": [
            {
                "endpoint": "/api/v1/product-description",
                "name": "Product Description Generator",
                "description": "Generate e-commerce product descriptions optimized for any platform",
                "pricing": {"per_request": 1.50, "currency": "USD"},
                "avg_latency_ms": 10000,
                "tags": ["e-commerce", "content", "SEO"],
            },
            {
                "endpoint": "/api/v1/seo-content",
                "name": "SEO Content Writer",
                "description": "Generate SEO-optimized blog posts with keyword analysis",
                "pricing": {"per_request": 4.00, "currency": "USD"},
                "avg_latency_ms": 20000,
                "tags": ["SEO", "content", "blogging"],
            },
            {
                "endpoint": "/api/v1/resume",
                "name": "Resume Builder",
                "description": "Generate ATS-optimized professional resumes",
                "pricing": {"per_request": 3.00, "currency": "USD"},
                "avg_latency_ms": 12000,
                "tags": ["resume", "career", "HR"],
            },
            {
                "endpoint": "/api/v1/ad-copy",
                "name": "Ad Copy Generator",
                "description": "Generate platform-specific advertising copy",
                "pricing": {"per_request": 2.00, "currency": "USD"},
                "avg_latency_ms": 10000,
                "tags": ["advertising", "marketing", "PPC"],
            },
            {
                "endpoint": "/api/v1/email-sequence",
                "name": "Email Sequence Builder",
                "description": "Generate multi-email drip campaigns",
                "pricing": {"per_request": 2.00, "currency": "USD"},
                "avg_latency_ms": 15000,
                "tags": ["email", "marketing", "automation"],
            },
            {
                "endpoint": "/api/v1/press-release",
                "name": "Press Release Writer",
                "description": "Generate AP-style press releases",
                "pricing": {"per_request": 4.00, "currency": "USD"},
                "avg_latency_ms": 12000,
                "tags": ["PR", "communications", "media"],
            },
            {
                "endpoint": "/api/v1/tech-docs",
                "name": "Technical Documentation Generator",
                "description": "Generate API docs, READMEs, and tutorials from code",
                "pricing": {"per_request": 3.50, "currency": "USD"},
                "avg_latency_ms": 15000,
                "tags": ["documentation", "developer-tools", "API"],
            },
            {
                "endpoint": "/api/v1/data-extract",
                "name": "Data Extractor",
                "description": "Extract structured data from documents",
                "pricing": {"per_request": 1.50, "currency": "USD"},
                "avg_latency_ms": 9000,
                "tags": ["data-extraction", "OCR", "documents"],
            },
            {
                "endpoint": "/api/v1/grant-proposal",
                "name": "Grant Proposal Writer",
                "description": "Generate grant proposals for SBIR, STTR, NIH, NSF, and more",
                "pricing": {"per_request": 5.00, "currency": "USD"},
                "avg_latency_ms": 25000,
                "tags": ["grants", "proposals", "government"],
            },
            {
                "endpoint": "/api/v1/compliance-doc",
                "name": "Compliance Document Generator",
                "description": "Generate compliance documents for HIPAA, GDPR, SOX, and more",
                "pricing": {"per_request": 4.50, "currency": "USD"},
                "avg_latency_ms": 20000,
                "tags": ["compliance", "legal", "regulatory"],
            },
            {
                "endpoint": "/api/v1/insurance-appeal",
                "name": "Insurance Appeal Writer",
                "description": "Generate insurance appeal letters for denied claims",
                "pricing": {"per_request": 3.50, "currency": "USD"},
                "avg_latency_ms": 15000,
                "tags": ["insurance", "appeals", "healthcare"],
            },
            {
                "endpoint": "/api/v1/data-report",
                "name": "Data Report Generator",
                "description": "Generate data-driven reports with analysis and recommendations",
                "pricing": {"per_request": 3.00, "currency": "USD"},
                "avg_latency_ms": 18000,
                "tags": ["analytics", "reporting", "business-intelligence"],
            },
        ],
        "rate_limits": {
            "free": {"requests_per_day": _FREE_LIMIT},
            "paid": {"requests_per_day": _PAID_LIMIT},
        },
        "authentication": "X-API-Key header",
    }
