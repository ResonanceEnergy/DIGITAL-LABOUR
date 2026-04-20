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
from api.notifications_router import router as notifications_router
from api.ops_router import router as ops_router
from api.intel_router import router as intel_router
from api.outputs_router import router as outputs_router

# P6.3 — Credential TTL check on startup
try:
    from utils.credential_ttl import check_credential_ttl
    check_credential_ttl()
except Exception:
    pass

# ── .env validation on startup ─────────────────────────────────
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

import threading


@app.on_event("startup")
async def startup_background_daemons():
    """Start critical background daemons if worker.py is not running separately."""
    import os
    if os.environ.get("DISABLE_EMBEDDED_WORKER") == "true":
        logger.info("[STARTUP] Embedded worker disabled via DISABLE_EMBEDDED_WORKER")
        return

    try:
        # Check if worker is already running on a separate port
        import urllib.request
        worker_port = int(os.environ.get("WORKER_HEALTH_PORT", "9090"))
        urllib.request.urlopen(f"http://localhost:{worker_port}/health", timeout=2)
        logger.info("[STARTUP] External worker detected on port %d — skipping embedded daemons", worker_port)
        return
    except Exception:
        logger.info("[STARTUP] No external worker detected — starting embedded daemons")

    def _run_queue_processor():
        """Embedded queue processor — runs tasks as fast as LLMs can handle them."""
        import time as _time
        import os
        max_concurrent = int(os.environ.get("QUEUE_MAX_CONCURRENT", "3"))
        idle_poll = int(os.environ.get("QUEUE_IDLE_POLL_SECONDS", "5"))
        active_threads = []

        def _process_task(t):
            try:
                task_inputs = t.get("inputs", {})
                if isinstance(task_inputs, str):
                    import json as _json
                    task_inputs = _json.loads(task_inputs)
                # Inject provider into inputs so route_task can pick it up
                if t.get("provider"):
                    task_inputs["provider"] = t["provider"]
                event = create_event(t["task_type"], task_inputs, t.get("client", "direct"))
                result = route_task(event)
                qa_data = result.get("qa", {})
                qa_status = qa_data.get("status", "")
                outputs = result.get("outputs", {})
                cost = result.get("billing", {}).get("amount", 0.0)
                if qa_status == "PASS":
                    queue.complete(t["task_id"], outputs=outputs, qa_status=qa_status, cost_usd=cost)
                    logger.info("[QUEUE] Completed: %s (%s) QA=PASS", t["task_id"][:8], t["task_type"])
                else:
                    issues = qa_data.get("issues", [])
                    queue.fail(t["task_id"], str(issues)[:500])
                    logger.warning("[QUEUE] QA Failed: %s (%s) — %s", t["task_id"][:8], t["task_type"], issues[:1])
            except Exception as e:
                queue.fail(t["task_id"], str(e))
                logger.error("[QUEUE] Error processing %s: %s", t["task_id"][:8], e)

        while True:
            try:
                # Clean up finished threads
                active_threads[:] = [t for t in active_threads if t.is_alive()]

                # If we have capacity, grab more tasks
                if len(active_threads) < max_concurrent:
                    task = queue.dequeue()
                    if task:
                        t = threading.Thread(target=_process_task, args=(task,),
                                           name=f"QP-{task['task_id'][:8]}", daemon=True)
                        t.start()
                        active_threads.append(t)
                        continue  # Immediately try to grab another
                    else:
                        _time.sleep(idle_poll)  # Nothing queued, wait
                else:
                    _time.sleep(2)  # At capacity, brief pause
            except Exception as e:
                logger.error("[QUEUE_PROC] Error: %s", e)
                _time.sleep(10)

    def _run_nerve_lite():
        """NERVE cycle — full NCL daily push every 30 min, internal ops every 15 min."""
        import time as _time
        import os
        nerve_interval = int(os.environ.get("NERVE_INTERVAL_SECONDS", "1800"))  # 30 min default
        ops_interval = int(os.environ.get("OPS_INTERVAL_SECONDS", "900"))       # 15 min default
        _time.sleep(20)  # Wait for app to fully start

        last_full_push = 0
        last_ops_gen = 0
        cycle = 0

        while True:
            try:
                now = _time.time()
                cycle += 1

                # Internal ops generation — every 15 min (lightweight, just queues tasks)
                if now - last_ops_gen >= ops_interval:
                    try:
                        from automation.internal_ops import generate_daily_tasks
                        logger.info("[NERVE] Cycle %d — generating internal ops tasks...", cycle)
                        result = generate_daily_tasks()
                        dispatched = result.get("dispatched", 0)
                        logger.info("[NERVE] Internal ops: %d tasks dispatched", dispatched)
                        last_ops_gen = now
                    except Exception as e:
                        logger.error("[NERVE] Internal ops error: %s", e)

                # Full BRL ops push — every 30 min (health checks, escalations, revenue)
                if now - last_full_push >= nerve_interval:
                    try:
                        from dispatcher.ops_commander import daily_ops_push
                        logger.info("[NERVE] Cycle %d — full BRL ops push...", cycle)
                        daily_ops_push()
                        logger.info("[NERVE] Full push complete")
                        last_full_push = now
                    except Exception as e:
                        logger.error("[NERVE] Daily push error: %s", e)

            except Exception as e:
                logger.error("[NERVE] Cycle error: %s", e)

            _time.sleep(60)  # Check every 60 seconds, act based on intervals

    def _run_galactia():
        """Galactia Unified Intelligence Engine — runs full pipeline autonomously.

        Phase 1: PARALLEL ingestion (Reddit + YouTube + X in separate threads)
        Phase 2a: VERITAS truth scoring via LLM
        Phase 2b: ML statistical scoring (anomaly + trend + TF-IDF)
        Phase 2c: Context governance (TTL + freshness + cleanup)
        Phase 3: Correlation analysis (every 3rd cycle)
        Phase 4: Research generation (every 6th cycle)
        Phase 5: Unified memory status
        """
        import time as _time
        import os
        galactia_interval = int(os.environ.get("GALACTIA_INTERVAL_SECONDS", "1800"))  # 30 min default
        _time.sleep(45)  # Wait for app + NERVE to stabilize first

        cycle = 0
        consecutive_failures = 0

        while True:
            cycle += 1
            try:
                logger.info("[GALACTIA] Unified cycle %d — parallel ingest + VERITAS + ML + Governor...", cycle)
                from galactia.galactia import run_cycle
                report = run_cycle()
                ingestion = report.get("phases", {}).get("ingestion", {})
                scoring = report.get("phases", {}).get("scoring", {})
                ingested = ingestion.get("total_new", 0)
                veritas = scoring.get("veritas", {}).get("scored", 0)
                ml = scoring.get("ml", {}).get("scored", 0)
                elapsed = report.get("elapsed_seconds", "?")
                logger.info("[GALACTIA] Cycle %d complete — %d ingested (parallel), %d VERITAS, %d ML scored in %ss",
                           cycle, ingested, veritas, ml, elapsed)
                consecutive_failures = 0
            except ImportError as e:
                logger.error("[GALACTIA] Import error: %s — will retry in 5 min", e)
                _time.sleep(300)
                continue
            except Exception as e:
                consecutive_failures += 1
                logger.error("[GALACTIA] Cycle %d error: %s", cycle, e)
                if consecutive_failures >= 5:
                    logger.error("[GALACTIA] 5 consecutive failures — backing off 10 min")
                    _time.sleep(600)
                    consecutive_failures = 0
                    continue

            _time.sleep(galactia_interval)

    queue_thread = threading.Thread(target=_run_queue_processor, name="EmbeddedQueueProc", daemon=True)
    queue_thread.start()
    logger.info("[STARTUP] Embedded QueueProc started")

    nerve_thread = threading.Thread(target=_run_nerve_lite, name="EmbeddedNERVE", daemon=True)
    nerve_thread.start()
    logger.info("[STARTUP] Embedded NERVE-lite started")

    galactia_thread = threading.Thread(target=_run_galactia, name="EmbeddedGalactia", daemon=True)
    galactia_thread.start()
    logger.info("[STARTUP] Embedded Galactia intelligence daemon started (30-min cycles)")

    # Verify at least one LLM provider is available
    try:
        from utils.llm_client import list_available_providers
        providers = list_available_providers()
        if providers:
            logger.info("[STARTUP] Available LLM providers: %s", ", ".join(providers))
        else:
            logger.warning("[STARTUP] WARNING: No LLM providers available! Agents will fail.")
    except Exception as e:
        logger.warning("[STARTUP] Could not check LLM providers: %s", e)


# CORS — restrict to known origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://bit-rage-labour.com",
        "https://www.bit-rage-labour.com",
        "https://bitrage-labour-api-production.up.railway.app",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
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

# DIGITAL LABOUR MATRIX MONITOR — Mobile C2
app.include_router(matrix_router)

# OpenClaw Automation Engine
app.include_router(openclaw_router)

# Lead Magnet — Inbound lead capture + free demo
app.include_router(lead_router)

# Freelance Engine — Job hunt, bidding, delivery automation
app.include_router(freelance_router)

# API Marketplace — Top 8 agents as clean API products (RapidAPI / Zyla)
app.include_router(marketplace_router)

# Revenue Dashboard — Revenue tracking, agent economics, client LTV
app.include_router(revenue_router)

# Stripe Checkout — Service landing pages → payment → agent fulfillment
app.include_router(checkout_router)

# Fiverr Fulfillment — Order intake, agent dispatch, deliverable packaging
app.include_router(fulfillment_router)

# BRL Task Management — Full ops tracking (human + AI)
app.include_router(task_router)

# Notification System — Real-time alerts for workstation
app.include_router(notifications_router)

# Bit Rage Operations Commander
app.include_router(ops_router)

# Intelligence Engine (Galactia — NCL-bound, see SOT)
app.include_router(intel_router)

# Persistent Output Store — query/search/retrieve completed outputs
app.include_router(outputs_router)


@app.get("/ops", response_class=HTMLResponse)
def ops_dashboard():
    """Serve the live operations dashboard."""
    html_path = Path(__file__).parent / "ops_dashboard.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/command-center", response_class=HTMLResponse)
def command_center():
    """Serve the BRL Command Center — Task Management PWA."""
    html_path = Path(__file__).parent / "task_dashboard.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/matrix", response_class=HTMLResponse)
def matrix_dashboard():
    """Serve the DIGITAL LABOUR MATRIX MONITOR — mobile C2 dashboard."""
    html_path = Path(__file__).parent / "matrix_dashboard.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/workstation", response_class=HTMLResponse)
def bitrage_workstation():
    """Serve the Bit Rage Labour Workstation — task execution engine."""
    html_path = Path(__file__).parent / "bitrage_workstation.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/ncl-workstation", response_class=HTMLResponse)
def ncl_workstation():
    """Serve the NCL Operations Commander — autonomous intelligence hub."""
    html_path = Path(__file__).parent / "ncl_workstation.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/matrix/manifest.json")
def matrix_manifest():
    """PWA manifest for DIGITAL LABOUR MATRIX — Add to Home Screen support."""
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


# ── Services landing pages ─────────────────────────────────────────────────

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


# ── Blog routes ─────────────────────────────────────────────────────────────

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

# ── Input Sanitization ──────────────────────────────────────────────────────

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


# ── Request / Response Models ───────────────────────────────────────────────

class TaskRequest(BaseModel):
    task_type: Literal[
        "sales_outreach", "support_ticket", "content_repurpose", "doc_extract",
        "lead_gen", "email_marketing", "seo_content", "social_media",
        "data_entry", "web_scraper", "crm_ops", "bookkeeping",
        "proposal_writer", "product_desc", "resume_writer", "ad_copy",
        "market_research", "business_plan", "press_release", "tech_docs",
        "context_manager", "qa_manager", "production_manager", "automation_manager",
        "grant_writer", "insurance_appeals", "compliance_docs", "data_reporter",
        # ── CTR-SVC division ──
        "contractor_doc_writer", "contractor_qa", "contractor_compliance",
        "permit_application", "inspection_report", "contractor_proposal",
        "lien_waiver", "safety_plan", "change_order", "progress_report", "bid_document",
        # ── MUN-SVC division ──
        "municipal_doc_writer", "municipal_qa", "municipal_compliance",
        "meeting_minutes", "public_notice", "ordinance", "resolution",
        "municipal_grant", "budget_summary", "annual_report", "municipal_rfp",
        "agenda", "staff_report",
        # ── INS-OPS division (QA + compliance) ──
        "insurance_qa", "insurance_compliance",
        # ── GRANT-OPS division (QA + compliance) ──
        "grant_qa", "grant_compliance",
    ]
    client: str = ""
    provider: str = ""
    priority: int = Field(default=0, ge=0, le=10)
    inputs: dict = Field(default_factory=dict)
    sync: bool = Field(default=False, description="If True, process immediately and return result")
    schema_version: str = Field(default="2.0", description="Schema version — must match current version")


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


# ── Endpoints ───────────────────────────────────────────────────────────────

@app.post("/tasks", response_model=TaskResponse)
def submit_task(req: TaskRequest):
    """Submit a new task for processing."""
    # P1.4: Schema version validation — reject mismatched versions
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
                qa_data = result.get("qa", {})
                qa = qa_data.get("status", "")
                outputs = result.get("outputs", {})
                cost = result.get("billing", {}).get("amount", 0.0)
                # Surface failure details so they're visible from the task API
                failure_reason = qa_data.get("failure_reason", "")
                qa_issues = qa_data.get("issues", [])
                error_detail = ""
                if qa == "FAIL" and (failure_reason or qa_issues):
                    error_detail = f"{failure_reason}: {'; '.join(qa_issues)}" if qa_issues else failure_reason
                queue.complete(task_id, outputs=outputs, qa_status=qa, cost_usd=cost)
                if error_detail:
                    # Also store the error so GET /tasks/{id} shows why it failed
                    conn = queue._get_conn()
                    conn.execute("UPDATE tasks SET error = ? WHERE task_id = ?", (error_detail, task_id))
                    conn.commit()
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
    """Full dashboard payload (legacy — use /monitor/overview instead)."""
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
