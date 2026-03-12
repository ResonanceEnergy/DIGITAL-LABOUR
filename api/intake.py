"""FastAPI intake webhook for Digital Labour.

Receives task requests via HTTP, validates them, queues them, and returns task IDs.
Optionally processes immediately (sync mode) or returns for async pickup.

Usage:
    uvicorn api.intake:app --host 0.0.0.0 --port 8000
    # Or: python -m api.intake
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime, timezone
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

load_dotenv(PROJECT_ROOT / ".env")

from dispatcher.queue import TaskQueue
from dispatcher.router import DAILY_LIMITS, create_event, route_task
from api.monitor import router as monitor_router
from api.payments import router as payment_router

app = FastAPI(
    title="Digital Labour Intake API",
    version="1.0.0",
    description="Submit tasks to the AI workforce. Returns structured outputs.",
)

# CORS for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Monitoring endpoints
app.include_router(monitor_router)

# Payment & signup endpoints
app.include_router(payment_router)


@app.get("/ops", response_class=HTMLResponse)
def ops_dashboard():
    """Serve the live operations dashboard."""
    html_path = Path(__file__).parent / "ops_dashboard.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/subscribe", response_class=HTMLResponse)
def subscribe_page():
    """Serve the subscription pricing page."""
    html_path = Path(__file__).resolve().parent.parent / "site" / "subscribe.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))

queue = TaskQueue()


# ── Request / Response Models ───────────────────────────────────────────────

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
    # Budget check
    if req.client:
        limit = DAILY_LIMITS.get(req.task_type, 50)
        if not queue.check_budget(req.client, req.task_type, limit):
            raise HTTPException(
                status_code=429,
                detail=f"Daily limit ({limit}) reached for {req.task_type}. Resets at midnight UTC.",
            )

    # Enqueue
    task_id = queue.enqueue(
        task_type=req.task_type,
        inputs=req.inputs,
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
                    inputs={**req.inputs, "provider": req.provider} if req.provider else req.inputs,
                    client_id=req.client or "direct",
                )
                result = route_task(event)
                qa = result.get("qa", {}).get("status", "")
                outputs = result.get("outputs", {})
                cost = result.get("billing", {}).get("amount", 0.0)
                queue.complete(task_id, outputs=outputs, qa_status=qa, cost_usd=cost)
                return TaskResponse(task_id=task_id, status="completed", message=f"QA: {qa}")
            except Exception as e:
                queue.fail(task_id, error=str(e))
                raise HTTPException(status_code=500, detail=f"Task failed: {e}")

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
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.intake:app", host="127.0.0.1", port=8000, reload=True)
