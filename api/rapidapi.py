"""RapidAPI Integration — Expose Bit Rage Labour agents as public API products.

Wraps existing agent endpoints into a format suitable for listing on RapidAPI Hub.
Provides standalone FastAPI app with API key auth, rate limiting, and usage tracking.

Steps to list on RapidAPI:
    1. Create account: https://rapidapi.com/auth/sign-up
    2. Go to: https://rapidapi.com/provider/dashboard
    3. Click "My APIs" → "Add New API"
    4. Name: "Bit Rage Labour — AI Agents"
    5. Category: Artificial Intelligence
    6. Upload OpenAPI spec: python -m api.rapidapi --spec > openapi.json
    7. Set base URL to your deployed server
    8. Configure pricing tiers (Freemium, Pro, Enterprise)

Usage:
    python -m api.rapidapi --spec     # Print OpenAPI spec
    python -m api.rapidapi --serve    # Run standalone RapidAPI-ready server
"""

import json
import os
import sys
import time
from collections import defaultdict, deque
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field, field_validator
from typing import Optional


# ── RapidAPI-Ready App ──────────────────────────────────────────

# Hide docs in production — no need to expose API schema to attackers
_on_railway = bool(os.environ.get("RAILWAY_ENVIRONMENT"))

rapid_app = FastAPI(
    title="Bit Rage Labour — AI Agents API",
    version="2.0.0",
    description=(
        "24 AI agents for sales outreach, lead generation, content creation, "
        "data entry, web scraping, bookkeeping, proposals, SEO, ad copy, "
        "market research, business plans, tech docs, and more. "
        "Multi-agent pipelines with QA verification on every output."
    ),
    docs_url=None if _on_railway else "/docs",
    redoc_url=None if _on_railway else "/redoc",
    openapi_url=None if _on_railway else "/openapi.json",
)

rapid_app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://bit-rage-labour.com",
        "https://www.bit-rage-labour.com",
        "https://bitrage-labour-api-production.up.railway.app",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key",
                    "X-RapidAPI-Proxy-Secret", "X-RapidAPI-Key",
                    "X-Matrix-Token"],
)


# ── Rate Limiting (in-memory sliding window) ─────────────────────
_rate_buckets: dict[str, list[float]] = defaultdict(list)
_bucket_last_seen: dict[str, float] = {}
RATE_LIMIT = 100      # requests per window (PRD spec)
RATE_WINDOW = 60.0    # seconds
_BUCKET_STALE = 300.0  # purge IPs idle for 5 minutes
_HEALTHCHECK_PATHS = {"/health", "/health/"}

# ── Error log buffer (last 50 errors, in-memory) ──────────────────
_error_log: deque[dict] = deque(maxlen=50)


@rapid_app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """IP-based sliding-window rate limiting (100 req/min per IP)."""
    # Skip rate limiting for internal healthcheck probes
    if request.url.path in _HEALTHCHECK_PATHS:
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    cutoff = now - RATE_WINDOW

    # Prune old timestamps in-place
    bucket = _rate_buckets[client_ip]
    bucket[:] = [t for t in bucket if t > cutoff]
    _bucket_last_seen[client_ip] = now

    if len(bucket) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."},
            headers={"Retry-After": str(int(RATE_WINDOW))},
        )
    bucket.append(now)

    # Periodic cleanup: drop stale IPs (every ~100 requests)
    if sum(len(v) for v in _rate_buckets.values()) % 100 == 0:
        stale = [ip for ip, ts in _bucket_last_seen.items() if now - ts > _BUCKET_STALE]
        for ip in stale:
            _rate_buckets.pop(ip, None)
            _bucket_last_seen.pop(ip, None)

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT)
    response.headers["X-RateLimit-Remaining"] = str(max(0, RATE_LIMIT - len(bucket)))
    return response


@rapid_app.middleware("http")
async def security_headers(request: Request, call_next):
    """Add OWASP-recommended security headers to every response."""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains; preload"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    return response

# ── Mount the full intake API (all 24 agents via /tasks) ────────
from api.intake import app as intake_app
rapid_app.mount("/intake", intake_app)

# ── Operations Monitor API (ops dashboard data endpoints) ──────────────
from api.monitor import router as monitor_router
rapid_app.include_router(monitor_router)

# ── BIT RAGE LABOUR MATRIX MONITOR (mobile C2 dashboard) ────────────────
from api.matrix_monitor import router as matrix_router
rapid_app.include_router(matrix_router)

# ── OpenClaw Freelance Automation Engine ───────────────────────────────
from api.openclaw import router as openclaw_router
rapid_app.include_router(openclaw_router)


@rapid_app.get("/matrix", response_class=HTMLResponse)
def matrix_dashboard():
    """Serve the BIT RAGE LABOUR MATRIX MONITOR — mobile C2 dashboard."""
    html_path = Path(__file__).parent / "matrix_dashboard.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@rapid_app.get("/matrix/manifest.json")
def matrix_manifest():
    """PWA manifest for Add to Home Screen."""
    return JSONResponse({
        "name": "BIT RAGE LABOUR MATRIX",
        "short_name": "MATRIX",
        "start_url": "/matrix",
        "display": "standalone",
        "background_color": "#0a0a0f",
        "theme_color": "#0a0a0f",
        "icons": [
            {"src": "/matrix/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/matrix/icon-512.png", "sizes": "512x512", "type": "image/png"}
        ]
    })


@rapid_app.get("/ops", response_class=HTMLResponse)
def ops_dashboard():
    """Serve the live operations dashboard."""
    html_path = Path(__file__).parent / "ops_dashboard.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


# ── Models ──────────────────────────────────────────────────────

class SalesRequest(BaseModel):
    company: str = Field(..., description="Target company name", examples=["Stripe"])
    role: str = Field(default="Head of Sales", description="Target role/title")
    provider: str = Field(default="", description="LLM provider: openai|anthropic|gemini|grok")

class SupportRequest(BaseModel):
    ticket_text: str = Field(..., description="Support ticket content")
    provider: str = Field(default="", description="LLM provider")

class ContentRequest(BaseModel):
    content: str = Field(..., description="Blog post or article text to repurpose")
    provider: str = Field(default="", description="LLM provider")

class DocExtractRequest(BaseModel):
    document_text: str = Field(..., description="Document text to extract data from")
    doc_type: str = Field(default="auto", description="Document type: invoice|contract|resume|auto")
    provider: str = Field(default="", description="LLM provider")

class AgentResponse(BaseModel):
    task_id: str
    agent: str
    status: str
    processing_time_ms: int
    result: dict
    qa_status: str = "UNKNOWN"


# ── Auth Middleware ─────────────────────────────────────────────

RAPIDAPI_SECRET = os.getenv("RAPIDAPI_SECRET", "")


async def verify_api_key(
    x_rapidapi_proxy_secret: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
):
    """Verify RapidAPI proxy secret or direct API key."""
    # RapidAPI sends X-RapidAPI-Proxy-Secret
    if RAPIDAPI_SECRET and x_rapidapi_proxy_secret:
        if x_rapidapi_proxy_secret != RAPIDAPI_SECRET:
            raise HTTPException(status_code=403, detail="Invalid RapidAPI proxy secret")
        return True

    # Direct API key for non-RapidAPI usage
    if x_api_key:
        return True

    # In development/test, allow unauthenticated
    if not RAPIDAPI_SECRET:
        return True

    raise HTTPException(status_code=401, detail="API key required")


# ── Unified Run Endpoint (ALL 24 agents) ────────────────────────

ALL_AGENTS = [
    "sales_outreach", "support_ticket", "content_repurpose", "doc_extract",
    "lead_gen", "email_marketing", "seo_content", "social_media",
    "data_entry", "web_scraper", "crm_ops", "bookkeeping",
    "proposal_writer", "product_desc", "resume_writer", "ad_copy",
    "market_research", "business_plan", "press_release", "tech_docs",
    "context_manager", "qa_manager", "production_manager", "automation_manager",
]


class UnifiedRequest(BaseModel):
    agent: str = Field(..., description=f"Agent name. One of: {', '.join(ALL_AGENTS)}")
    inputs: dict = Field(default_factory=dict, description="Agent-specific inputs (see /agents for details)")
    provider: str = Field(default="", description="LLM provider: openai|anthropic|gemini|grok")
    client: str = Field(default="direct", description="Client identifier for billing/tracking")

    @field_validator("agent")
    @classmethod
    def agent_must_be_valid(cls, v: str) -> str:
        if v not in ALL_AGENTS:
            raise ValueError(f"Unknown agent '{v}'. Valid options: {ALL_AGENTS}")
        return v


@rapid_app.post("/v1/run", response_model=AgentResponse)
async def run_agent(req: UnifiedRequest):
    """Run any of the 24 AI agents. Send the agent name + inputs dict.

    This is the universal endpoint — use /agents to see input schemas per agent.
    """
    await verify_api_key()
    start = time.time()
    try:
        from dispatcher.router import create_event, route_task
        inputs = {**req.inputs}
        if req.provider:
            inputs["provider"] = req.provider
        event = create_event(
            task_type=req.agent,
            inputs=inputs,
            client_id=req.client,
        )
        result = route_task(event)
        elapsed = int((time.time() - start) * 1000)
        return AgentResponse(
            task_id=result.get("task_id", f"rapid_{int(time.time())}"),
            agent=req.agent,
            status="completed",
            processing_time_ms=elapsed,
            result=result.get("outputs", result),
            qa_status=result.get("qa", {}).get("status", "UNKNOWN"),
        )
    except Exception as e:
        _error_log.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "endpoint": "/v1/run",
            "agent": req.agent,
            "error": str(e),
        })
        raise HTTPException(status_code=500, detail=str(e))


@rapid_app.get("/v1/errors")
async def get_error_log():
    """Return the last 50 API errors captured in the in-memory error buffer."""
    await verify_api_key()
    return {"errors": list(_error_log), "count": len(_error_log)}


@rapid_app.get("/v1/metrics")
async def agent_metrics():
    """Return per-agent call count and average response time since last restart."""
    await verify_api_key()
    from dispatcher.router import get_metrics
    return {"metrics": get_metrics(), "timestamp": datetime.now(timezone.utc).isoformat()}


@rapid_app.get("/agents")
def list_agents():
    """List all available agents with their expected input fields."""
    agent_info = {
        "sales_outreach": {"inputs": {"company": "Target company name", "role": "Target role/title"}},
        "support_ticket": {"inputs": {"ticket_text": "Support ticket content"}},
        "content_repurpose": {"inputs": {"content": "Blog/article text to repurpose"}},
        "doc_extract": {"inputs": {"document_text": "Document text", "doc_type": "invoice|contract|resume|auto"}},
        "lead_gen": {"inputs": {"industry": "Target industry", "region": "Geographic region"}},
        "email_marketing": {"inputs": {"product": "Product/service name", "audience": "Target audience"}},
        "seo_content": {"inputs": {"keyword": "Target keyword", "content_type": "blog|landing|pillar"}},
        "social_media": {"inputs": {"topic": "Post topic", "platform": "linkedin|twitter|instagram", "cta_goal": "Call to action"}},
        "data_entry": {"inputs": {"source_data": "Raw data to process", "output_format": "structured format spec"}},
        "web_scraper": {"inputs": {"source_url": "URL to scrape", "extraction_target": "What data to extract"}},
        "crm_ops": {"inputs": {"contact_data": "Contact info", "action": "update|segment|report"}},
        "bookkeeping": {"inputs": {"transactions": "Transaction data", "period": "monthly|quarterly|annual"}},
        "proposal_writer": {"inputs": {"project": "Project description", "client_name": "Client"}},
        "product_desc": {"inputs": {"product_specs": "Product details", "tone": "professional|casual|luxury"}},
        "resume_writer": {"inputs": {"career_data": "Career history + skills", "target_industry": "Target industry"}},
        "ad_copy": {"inputs": {"product": "Product/brand info", "platform": "google|facebook|instagram"}},
        "market_research": {"inputs": {"topic": "Research topic", "depth": "overview|detailed|comprehensive"}},
        "business_plan": {"inputs": {"business_idea": "Business concept", "market": "Target market"}},
        "press_release": {"inputs": {"announcement": "News/announcement", "company": "Company name"}},
        "tech_docs": {"inputs": {"code_or_api": "Code/API to document", "doc_type": "api|readme|tutorial"}},
    }
    return {"agents": agent_info, "total": len(ALL_AGENTS), "endpoint": "POST /v1/run"}


# ── Endpoints (Legacy v1 typed) ─────────────────────────────────

@rapid_app.get("/")
def api_root():
    """API root — returns service info, version, and available endpoints."""
    return {
        "name": "Bit Rage Labour — AI Agents API",
        "version": "2.0.0",
        "agents": ALL_AGENTS,
        "endpoints": {
            "universal": "POST /v1/run",
            "agents_list": "GET /agents",
            "full_api": "/intake/docs",
            "health": "GET /health",
        },
        "docs": "/docs",
    }


@rapid_app.get("/health")
def health():
    """Health check — returns 200 with healthy status when the service is up."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@rapid_app.get("/health/smtp")
def health_smtp():
    """SMTP connectivity check — tests Zoho SMTP auth."""
    from delivery.sender import check_smtp
    ok, message = check_smtp()
    status_code = 200 if ok else 503
    return JSONResponse(
        status_code=status_code,
        content={"smtp": "ok" if ok else "error", "detail": message},
    )


@rapid_app.post("/v1/sales", response_model=AgentResponse)
async def sales_outreach(req: SalesRequest):
    """Generate personalized sales outreach for a target company + role.

    Returns company research, signals, and a 3-email outreach sequence.
    Average processing: 12-15 seconds.
    """
    await verify_api_key()
    start = time.time()
    try:
        from agents.sales_ops.pipeline import run_sales_pipeline
        result = run_sales_pipeline(
            company=req.company,
            role=req.role,
            provider=req.provider or None,
        )
        elapsed = int((time.time() - start) * 1000)
        return AgentResponse(
            task_id=result.get("task_id", f"rapid_{int(time.time())}"),
            agent="sales_ops",
            status="completed",
            processing_time_ms=elapsed,
            result=result,
            qa_status=result.get("qa_status", "UNKNOWN"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rapid_app.post("/v1/support", response_model=AgentResponse)
async def support_ticket(req: SupportRequest):
    """Resolve a support ticket — triage, severity score, and draft response.

    Returns classification, severity, draft response, and confidence score.
    Average processing: 9.6 seconds.
    """
    await verify_api_key()
    start = time.time()
    try:
        from agents.support.pipeline import run_support_pipeline
        result = run_support_pipeline(
            ticket_text=req.ticket_text,
            provider=req.provider or None,
        )
        elapsed = int((time.time() - start) * 1000)
        return AgentResponse(
            task_id=result.get("task_id", f"rapid_{int(time.time())}"),
            agent="support",
            status="completed",
            processing_time_ms=elapsed,
            result=result,
            qa_status=result.get("qa_status", "UNKNOWN"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rapid_app.post("/v1/content", response_model=AgentResponse)
async def repurpose_content(req: ContentRequest):
    """Repurpose content into 5 platform formats (LinkedIn, Twitter, email, etc).

    Takes a blog post or article and generates optimized versions for each platform.
    Average processing: 10-12 seconds.
    """
    await verify_api_key()
    start = time.time()
    try:
        from agents.content_repurpose.pipeline import run_content_pipeline
        result = run_content_pipeline(
            content=req.content,
            provider=req.provider or None,
        )
        elapsed = int((time.time() - start) * 1000)
        return AgentResponse(
            task_id=result.get("task_id", f"rapid_{int(time.time())}"),
            agent="content_repurpose",
            status="completed",
            processing_time_ms=elapsed,
            result=result,
            qa_status=result.get("qa_status", "UNKNOWN"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@rapid_app.post("/v1/extract", response_model=AgentResponse)
async def extract_document(req: DocExtractRequest):
    """Extract structured data from documents (invoices, contracts, resumes).

    Returns structured JSON with entities, amounts, dates, and confidence scores.
    Average processing: 8-10 seconds.
    """
    await verify_api_key()
    start = time.time()
    try:
        from agents.doc_extract.pipeline import run_extract_pipeline
        result = run_extract_pipeline(
            document_text=req.document_text,
            doc_type=req.doc_type,
            provider=req.provider or None,
        )
        elapsed = int((time.time() - start) * 1000)
        return AgentResponse(
            task_id=result.get("task_id", f"rapid_{int(time.time())}"),
            agent="doc_extract",
            status="completed",
            processing_time_ms=elapsed,
            result=result,
            qa_status=result.get("qa_status", "UNKNOWN"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── OpenAPI Spec Export ─────────────────────────────────────────

def export_openapi_spec() -> dict:
    """Export the OpenAPI spec for RapidAPI upload."""
    spec = rapid_app.openapi()
    # Add RapidAPI-specific extensions
    spec["info"]["x-rapidapi-host"] = "bit-rage-labour.p.rapidapi.com"
    spec["info"]["contact"] = {
        "name": "Bit Rage Labour",
        "email": "api@bit-rage-labour.com",
        "url": "https://bit-rage-labour.com",
    }
    spec["info"]["x-logo"] = {"url": "https://bit-rage-labour.com/logo.png"}
    return spec


# ── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="RapidAPI Integration")
    parser.add_argument("--spec", action="store_true", help="Print OpenAPI spec as JSON")
    parser.add_argument("--serve", action="store_true", help="Run standalone server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8001")), help="Port for standalone server")
    args = parser.parse_args()

    if args.spec:
        spec = export_openapi_spec()
        print(json.dumps(spec, indent=2))
    elif args.serve:
        import uvicorn
        print(f"[RAPIDAPI] Starting on port {args.port}...")
        uvicorn.run(rapid_app, host="0.0.0.0", port=args.port)
    else:
        parser.print_help()
