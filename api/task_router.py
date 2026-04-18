"""FastAPI router for BRL Task Management System.

Exposes full CRUD + intelligence endpoints for the Command Center PWA.

Endpoints:
  POST   /ops/tasks                — Create a task
  GET    /ops/tasks                — List tasks (with filters)
  GET    /ops/tasks/{task_id}      — Get task detail
  PUT    /ops/tasks/{task_id}      — Update task
  POST   /ops/tasks/{task_id}/note — Add a note
  DELETE /ops/tasks/{task_id}      — Archive task
  GET    /ops/tasks/stats          — Dashboard statistics
  GET    /ops/tasks/overdue        — Overdue tasks
  GET    /ops/tasks/human          — Human responsibilities
  GET    /ops/tasks/ai             — AI workload
  GET    /ops/tasks/search         — Search tasks
  POST   /ops/tasks/ingest         — Run full ingestion cycle
  GET    /ops/tasks/summary        — Daily summary
  POST   /ops/tasks/sync           — Sync with dispatcher queue
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from task_management.store import TaskStore
from task_management.manager import TaskManager

logger = logging.getLogger("api.tasks")

router = APIRouter(prefix="/ops/tasks", tags=["task-management"])

# Module-level singletons
_store = TaskStore()
_manager = TaskManager(store=_store)


# ── Request / Response Models ─────────────────────────────────────

class CreateTaskRequest(BaseModel):
    title: str
    description: str = ""
    category: str = Field(default="internal", pattern="^(client_work|internal|biz_dev|outreach)$")
    subcategory: str = ""
    priority: int = Field(default=5, ge=0, le=10)
    owner_type: str = Field(default="human", pattern="^(human|ai|hybrid)$")
    owner_name: str = ""
    assigned_agent: str = ""
    client: str = ""
    due_date: str = ""
    tags: list[str] = Field(default_factory=list)
    estimated_hours: float = 0.0


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    owner_type: Optional[str] = None
    owner_name: Optional[str] = None
    assigned_agent: Optional[str] = None
    client: Optional[str] = None
    due_date: Optional[str] = None
    tags: Optional[list[str]] = None
    progress_pct: Optional[int] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None


class AddNoteRequest(BaseModel):
    note: str
    author: str = "human"


class TaskResponse(BaseModel):
    task_id: str
    message: str


# ── Stats (must be before {task_id} routes) ───────────────────────

@router.get("/stats")
def task_stats():
    """Dashboard statistics for all active tasks."""
    return _store.stats()


@router.get("/overdue")
def overdue_tasks():
    """Get all overdue tasks."""
    return _store.overdue_tasks()


@router.get("/human")
def human_responsibilities():
    """Get all active human-owned tasks."""
    tasks = _store.list_tasks(owner_type="human")
    active = [t for t in tasks if t["status"] in ("pending", "in_progress")]
    return {"count": len(active), "tasks": active}


@router.get("/ai")
def ai_workload():
    """Get all active AI-assigned tasks."""
    tasks = _store.ai_workload()
    return {"count": len(tasks), "tasks": tasks}


@router.get("/search")
def search_tasks(q: str = Query(..., min_length=2)):
    """Full-text search across tasks."""
    results = _store.search(q)
    return {"query": q, "count": len(results), "tasks": results}


@router.get("/summary")
def daily_summary():
    """Daily task summary for Command Center."""
    return _manager.daily_summary()


# ── Ingestion & Sync ──────────────────────────────────────────────

@router.post("/ingest")
def run_ingestion():
    """Run full ingestion cycle from NCL, C-Suite, NERVE, scheduler."""
    results = _manager.run_ingestion_cycle()
    total = sum(len(v) for k, v in results.items() if isinstance(v, list))
    return {"message": f"Ingestion complete — {total} new tasks", "details": results}


@router.post("/sync")
def sync_dispatcher():
    """Sync tasks with the dispatcher queue."""
    result = _manager.sync_with_dispatcher()
    return {"message": "Sync complete", "details": result}


# ── CRUD ──────────────────────────────────────────────────────────

@router.post("", response_model=TaskResponse)
def create_task(req: CreateTaskRequest):
    """Create a new task."""
    task_id = _manager.create_task(
        title=req.title,
        description=req.description,
        category=req.category,
        subcategory=req.subcategory,
        priority=req.priority,
        owner_type=req.owner_type,
        owner_name=req.owner_name,
        assigned_agent=req.assigned_agent,
        client=req.client,
        due_date=req.due_date,
        tags=req.tags,
        estimated_hours=req.estimated_hours,
    )
    return TaskResponse(task_id=task_id, message="Task created")


@router.get("")
def list_tasks(
    status: Optional[str] = None,
    category: Optional[str] = None,
    owner_type: Optional[str] = None,
    client: Optional[str] = None,
    source: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
):
    """List tasks with optional filters."""
    tasks = _store.list_tasks(
        status=status, category=category, owner_type=owner_type,
        client=client, source=source, tag=tag, limit=limit, offset=offset,
    )
    return {"count": len(tasks), "tasks": tasks}


@router.get("/{task_id}")
def get_task(task_id: str):
    """Get a single task with full details and history."""
    task = _store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    history = _store.task_history(task_id)
    return {**task, "history": history}


@router.put("/{task_id}")
def update_task(task_id: str, req: UpdateTaskRequest):
    """Update a task's fields."""
    fields = {k: v for k, v in req.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    success = _store.update(task_id, actor="api", **fields)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, "message": "Task updated", "fields_updated": list(fields.keys())}


@router.post("/{task_id}/note")
def add_note(task_id: str, req: AddNoteRequest):
    """Add a note to a task."""
    success = _store.add_note(task_id, req.note, req.author)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, "message": "Note added"}


@router.delete("/{task_id}")
def archive_task(task_id: str):
    """Archive (soft-delete) a task."""
    success = _store.archive(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, "message": "Task archived"}
