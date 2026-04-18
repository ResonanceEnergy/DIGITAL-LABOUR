"""FastAPI intake webhook for DIGITAL LABOUR.

Receives task requests via HTTP, validates them, queues them, and returns task IDs.
Optionally processes immediately (sync mode) or returns for async pickup.

Usage:
    uvicorn api.intake:app --host 0.0.0.0 --port 8000
    # Or: python -m api.intake
"""

import sys
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging
from datetime import datetime, timezone
from typing import Literal

logger = logging.getLogger("api.intake")

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field

load_dotenv(PROJECT_ROOT / ".env")

from dispatcher.queue import TaskQueue
from dispatcher.router import DAILY_LIMITS, create_event, route_task
from api.monitor import router as monitor_router
from api.payments import router as payment_router
from api.matrix_monitor import router as matrix_router
from api.openclaw import router as openclaw_router
from api.lead_magnet import router as lead_router
from api.freelance import router as freelance_router
from api.marketplace import router as marketplace_router
from api.revenue import router as revenue_router
from api.checkout import router as checkout_router
from api.fulfillment import router as fulfillment_router
from api.task_router import router as task_router

# P6.3 â Credential TTL check on startup
try:
    from utils.credential_ttl import check_credential_ttl
    check_credential_ttl()
except Exception:
    pass

# ââ .env validation on startup âââââââââââââââââââââââââââââââââ
import os as _os

_REQUIRED_ENV = {
    "core": ["MATRIX_AUTH_TOKEN"],
    "email": ["SMTP_HOST", "SMTP_USER", "SMTP_PASS"],
    "billing": ["STRIPE_API_KEY"],
    "llm": ["OPENAI_API_KEY"],
}
_missing = []
for _cat, _keys in _REQUIRED_ENV.items():
    for _k in _keys:
        _v = _os.environ.get(_k, "")
        if not _v or _v.startswith("your_") or _v == "changeme":
            _missing.append(f"{_k} ({_cat})")
if _missing:
    logger.warning("[STARTUP] Missing required .env keys: %s", ", ".join(_missing))
else:
    logger.info("[STARTUP] All required .env keys present")

app = FastAPI(
    title="DIGITAL LABOUR Intake API",
    version="1.0.0",
    description="Submit tasks to the AI workforce. Returns structured outputs.",
)

# CORS â restrict to known origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://bit-rage-labour.com",
        "https://www.bit-rage-labour.com",
        "https://bitrage-labour-api-production.up.railway.app",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)


@app.middleware("http")
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
        "script-src 'self' 'unsafe-inline' https://js.stripe.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self' https://api.stripe.com; "
        "frame-src https://js.stripe.com https://checkout.stripe.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'"
    )
    return response

# Monitoring endpoints
app.include_router(monitor_router)

# Payment & signup endpoints
app.include_router(payment_router)

# DIGITAL LABOUR MATRIX MONITOR â Mobile C2
app.include_router(matrix_router)

# OpenClaw Automation Engine
app.include_router(openclaw_router)

# Lead Magnet â Inbound lead capture + free demo
app.include_router(lead_router)

# Freelance Engine â Job hunt, bidding, delivery automation
app.include_router(freelance_router)

# API Marketplace â Top 8 agents as clean API products (RapidAPI / Zyla)
app.include_router(marketplace_router)

# Revenue Dashboard â Revenue tracking, agent economics, client LTV
app.include_router(revenue_router)

# Stripe Checkout â Service landing pages â payment â agent fulfillment
app.include_router(checkout_router)

# Fiverr Fulfillment â Order intake, agent dispatch, deliverable packaging
app.include_router(fulfillment_router)

# BRL Task Management â Full ops tracking (human + AI)
app.include_router(task_router)


@app.get("/ops", response_class=HTMLResponse)
def ops_dashboard():
    """Serve the live operations dashboard."""
    html_path = Path(__file__).parent / "ops_dashboard.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/command-center", response_class=HTMLResponse)
def command_center():
    """Serve the BRL Command Center â Task Management PWA."""
    html_path = Path(__file__).parent / "task_dashboard.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/matrix", response_class=HTMLResponse)
def matrix_dashboard():
    """Serve the DIGITAL LABOUR MATRIX MONITOR â mobile C2 dashboard."""
    html_path = Path(__file__).parent / "matrix_dashboard.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/matrix/manifest.json")
def matrix_manifest():
    """PWA manifest for DIGITAL LABOUR MATRIX â Add to Home Screen support."""
    return JSONResponse({
        "name": "DIGITAL LABOUR MATRIX",
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


@app.get("/checkout", response_class=HTMLResponse)
def checkout_page():
    """Serve the Stripe Checkout landing page."""
    html_path = PROJECT_ROOT / "site" / "checkout.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/subscribe", response_class=HTMLResponse)
def subscribe_page():
    """Serve the subscription pricing page."""
    html_path = Path(__file__).resolve().parent.parent / "site" / "subscribe.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


# ââ Services landing pages âââââââââââââââââââââââââââââââââââââââââââââââââ

SERVICE_SLUGS = {
    "content",
    "seo",
    "ecommerce",
    "resume",
    "grant-proposal",
    "compliance",
    "insurance-appeal",
    "data-report",
}


@app.get("/services", response_class=HTMLResponse)
def services_index():
    """Serve the services overview page."""
    html_path = PROJECT_ROOT / "site" / "services" / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/services/{service}", response_class=HTMLResponse)
def service_page(service: str):
    """Serve an individual service landing page."""
    if service not in SERVICE_SLUGS:
        raise HTTPException(status_code=404, detail="Service not found")
    html_path = PROJECT_ROOT / "site" / "services" / f"{service}.html"
    if not html_path.is_file():
        raise HTTPException(status_code=404, detail="Service not found")
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


# ââ Blog routes âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

BLOG_SLUGS = {
    "building-24-agent-ai-workforce",
    "multi-llm-failover",
    "nerve-autonomous-outreach",
    "chatgpt-wrappers-vs-production-agents",
}


@app.get("/blog", response_class=HTMLResponse)
def blog_index():
    """Serve the blog index page."""
    html_path = PROJECT_ROOT / "site" / "blog" / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/blog/{slug}", response_class=HTMLResponse)
def blog_post(slug: str):
    """Serve an individual blog post."""
    if slug not in BLOG_SLUGS:
        raise HTTPException(status_code=404, detail="Post not found")
    html_path = PROJECT_ROOT / "site" / "blog" / f"{slug}.html"
    if not html_path.is_file():
        raise HTTPException(status_code=404, detail="Post not found")
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


queue = TaskQueue()

# ââ Input Sanitization ââââââââââââââââââââââââââââââââââââââââââââââââââââââ

_MAX_FIELD_LENGTH = 32_000
_INJECTION_PATTERNS = re.compile(
    r"(ignore previous|disregard (all |your )?instructions|you are now|"
    r"<script|javascript:|on\w+\s*=|"
    r"union\s+select|drop\s+table|;\s*delete|"
    r"&&|\|\||;\s*[a-z]+|\$\(|`)",
    re.IGNORECASE,
)


def sanitize_input(inputs: dict) -> dict:
    """Strip control chars, limit field lengths, reject injection patterns.

    Raises HTTPException 413 on oversized payload.
    Raises HTTPException 400 on detected injection patterns.
    """
    total_chars = 0
    sanitized: dict = {}
    for key, value in inputs.items():
        if isinstance(value, str):
            clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)
            if len(clean) > _MAX_FIELD_LENGTH:
                raise HTTPException(
                    status_code=413,
                    detail=f"Field '{key}' exceeds maximum length ({_MAX_FIELD_LENGTH} chars)",
                )
            total_chars += len(clean)
            if _INJECTION_PATTERNS.search(clean):
                logger.warning("[SUSPICIOUS_INPUT] Injection pattern in field '%s'", key)
                logger.warning("[REJECTED_INPUT] Injection pattern in field '%s'", key)
                raise HTTPException(
                    status_code=400,
                    detail="Request rejected: suspicious input pattern detected",
                )
            sanitized[key] = clean
        else:
            sanitized[key] = value

    if total_chars > _MAX_FIELD_LENGTH * 3:
        raise HTTPException(status_code=413, detail="Total payload size exceeds limit")
    return sanitized


# ââ Request / Response Models âââââââââââââââââââââââââââââââââââââââââââââââ

class TaskRequest(BaseModel):
    task_type: Literal[
        "sales_outreach", "support_ticket", "content_repurpose", "doc_extract",
        "lead_gen", "email_marketing", "seo_content", "social_media",
        "data_entry", "web_scraper", "crm_ops", "bookkeeping",
        "proposal_writer", "product_desc", "resume_writer", "ad_copy",
        "market_research", "business_plan", "press_release", "tech_docs",
        "context_manager", "qa_manager", "production_manager", "automation_manager",
    ]
    client: str = ""
    provider: str = ""
    priority: int = Field(default=0, ge=0, le=10)
    inputs: dict = Field(default_factory=dict)
    sync: bool = Field(default=False, description="If True, process immediately and return result")
    schema_version: str = Field(default="2.0", description="Schema version â must match current version")


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class TaskStatus(BaseModel):
    task_id: str
    task_type: str
    status: str
    client: str
    created_at: str
    started_at: str
    completed_at: str
    qa_status: str
    outputs: dict | None = None
    error: str = ""


# ââ Endpoints âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

@app.post("/tasks", response_model=TaskResponse)
def submit_task(req: TaskRequest):
    """Submit a new task for processing."""
    # P1.4: Schema version validation â reject mismatched versions
    if req.schema_version != "2.0":
        raise HTTPException(
            status_code=422,
            detail=f"Schema version mismatch: got '{req.schema_version}', expected '2.0'",
        )

    # Budget check
    if req.client:
        limit = DAILY_LIMITS.get(req.task_type, 50)
        if not queue.check_budget(req.client, req.task_type, limit):
            raise HTTPException(
                status_code=429,
                detail=f"Daily limit ({limit}) reached for {req.task_type}. Resets at midnight UTC.",
            )

    # Sanitize inputs (injection detection + size limits)
    sanitized_inputs = sanitize_input(req.inputs)

    # Enqueue
    task_id = queue.enqueue(
        task_type=req.task_type,
        inputs=sanitized_inputs,
        client=req.client,
        provider=req.provider,
        priority=req.priority,
    )

    if req.client:
        queue.increment_budget(req.client, req.task_type)

    if req.sync:
        # Process immediately
        task = queue.dequeue()
        if task:
            try:
                from dispatcher.router import create_event
                event = create_event(
                    task_type=req.task_type,
                    inputs={**sanitized_inputs, "provider": req.provider} if req.provider else sanitized_inputs,
                    client_id=req.client or "direct",
                )
                result = route_task(event)
                qa = result.get("qa", {}).get("status", "")
                outputs = result.get("outputs", {})
                cost = result.get("billing", {}).get("amount", 0.0)
                queue.complete(task_id, outputs=outputs, qa_status=qa, cost_usd=cost)
                return TaskResponse(task_id=task_id, status="completed", message=f"QA: {qa}")
            except Exception as e:
                logger.exception("Task %s failed", task_id)
                queue.fail(task_id, error=str(e))
                raise HTTPException(status_code=500, detail="Task processing failed")

    return TaskResponse(task_id=task_id, status="queued", message="Task queued for processing.")


@app.get("/tasks/{task_id}", response_model=TaskStatus)
def get_task(task_id: str):
    """Get the status and results of a task."""
    import json
    task = queue.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    outputs = task.get("outputs", "{}")
    if isinstance(outputs, str):
        outputs = json.loads(outputs) if outputs else {}
    return TaskStatus(
        task_id=task["task_id"],
        task_type=task["task_type"],
        status=task["status"],
        client=task["client"],
        created_at=task["created_at"],
        started_at=task["started_at"],
        completed_at=task["completed_at"],
        qa_status=task["qa_status"],
        outputs=outputs,
        error=task.get("error", ""),
    )


@app.get("/queue/stats")
def queue_stats(client: str = ""):
    """Get queue statistics, optionally filtered by client."""
    return queue.stats(client=client if client else None)


@app.get("/budget/{client}")
def client_budget(client: str):
    """Get today's usage for a client."""
    usage = queue.get_daily_usage(client)
    limits = {t: DAILY_LIMITS.get(t, 50) for t in DAILY_LIMITS}
    return {"client": client, "usage": usage, "limits": limits}


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/trace/{lineage_id}")
def trace_lineage(lineage_id: str):
    """Return all KPI log events for a given lineage_id."""
    from kpi.logger import get_events
    events = get_events(limit=500)
    matched = [e for e in events if e.get("lineage_id") == lineage_id]
    if not matched:
        raise HTTPException(status_code=404, detail=f"No events found for lineage_id: {lineage_id}")
    return {"lineage_id": lineage_id, "events": matched, "count": len(matched)}


@app.get("/agents")
def list_agents():
    """Return the agent registry (agent configs, ceilings, status)."""
    from dispatcher.router import AGENT_REGISTRY
    return {
        "doctrine_version": "2.0",
        "agent_count": len(AGENT_REGISTRY),
        "agents": AGENT_REGISTRY,
    }


@app.post("/admin/agents/{name}/disable")
def disable_agent(name: str, reason: str = ""):
    """Immediately disable an agent. All new tasks for this agent will be rejected."""
    from dispatcher.router import AGENT_REGISTRY, save_registry
    if name not in AGENT_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found in registry")
    AGENT_REGISTRY[name]["disabled"] = True
    save_registry()
    logger.warning("[ADMIN] Agent '%s' disabled. Reason: %s", name, reason or "(none)")
    return {"agent": name, "disabled": True, "reason": reason}


@app.post("/admin/agents/{name}/enable")
def enable_agent(name: str):
    """Re-enable a previously disabled agent."""
    from dispatcher.router import AGENT_REGISTRY, save_registry
    if name not in AGENT_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found in registry")
    AGENT_REGISTRY[name]["disabled"] = False
    save_registry()
    logger.info("[ADMIN] Agent '%s' re-enabled.", name)
    return {"agent": name, "disabled": False}


@app.get("/dashboard")
def dashboard_data():
    """Full dashboard payload (legacy â use /monitor/overview instead)."""
    from dashboard.health import full_dashboard
    return full_dashboard()


@app.get("/invoice/{client}")
def generate_invoice_pdf(client: str, days: int = 30):
    """Generate and return an invoice PDF for a client."""
    from billing.invoice_pdf import generate_invoice_pdf as make_pdf
    from fastapi.responses import FileResponse
    try:
        path = make_pdf(client, days=days)
        return FileResponse(path, media_type="application/pdf", filename=Path(path).name)
    except Exception as e:
        logger.exception("Invoice generation failed for %s", client)
        raise HTTPException(status_code=400, detail="Invoice generation failed")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.intake:app", host="127.0.0.1", port=8000, reload=True)
