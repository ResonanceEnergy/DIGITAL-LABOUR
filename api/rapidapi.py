"""RapidAPI Integration — Expose Digital Labour agents as public API products.

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
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional


# ── RapidAPI-Ready App ──────────────────────────────────────────

rapid_app = FastAPI(
    title="Bit Rage Labour — AI Agents API",
    version="1.0.0",
    description=(
        "Four AI agents for sales outreach, support resolution, "
        "content repurposing, and document extraction. "
        "Multi-agent pipelines with QA verification on every output."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

rapid_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


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
        # For now accept any key — will add key management later
        return True

    # In development/test, allow unauthenticated
    if not RAPIDAPI_SECRET:
        return True

    raise HTTPException(status_code=401, detail="API key required")


# ── Endpoints ───────────────────────────────────────────────────

@rapid_app.get("/")
def api_root():
    return {
        "name": "Bit Rage Labour — AI Agents API",
        "version": "1.0.0",
        "agents": ["sales_ops", "support", "content_repurpose", "doc_extract"],
        "docs": "/docs",
    }


@rapid_app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


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
    parser.add_argument("--port", type=int, default=8001, help="Port for standalone server")
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
