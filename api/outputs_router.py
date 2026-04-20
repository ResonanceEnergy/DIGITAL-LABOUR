"""REST API for the persistent output store.

Provides endpoints to list, search, retrieve, and inspect completed task outputs.

Prefix: /api/v1/outputs
"""

import logging
from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger("api.outputs_router")

router = APIRouter(prefix="/api/v1/outputs", tags=["outputs"])


@router.get("")
def list_outputs(
    division: str = Query(default="", description="Filter by division"),
    task_type: str = Query(default="", description="Filter by task type"),
    category: str = Query(default="", description="Filter by category"),
    qa_status: str = Query(default="", description="Filter by QA status"),
    limit: int = Query(default=50, ge=1, le=200, description="Max results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
):
    """List outputs with optional filters. Does not include full output content."""
    from utils.output_store import list_outputs as _list

    results = _list(
        division=division or None,
        task_type=task_type or None,
        category=category or None,
        qa_status=qa_status or None,
        limit=limit,
        offset=offset,
    )
    return {"count": len(results), "offset": offset, "limit": limit, "outputs": results}


@router.get("/stats")
def output_stats():
    """Return aggregate statistics about the output store."""
    from utils.output_store import get_stats
    return get_stats()


@router.get("/latest")
def latest_outputs(
    division: str = Query(default="", description="Filter by division"),
    task_type: str = Query(default="", description="Filter by task type"),
    limit: int = Query(default=10, ge=1, le=50, description="Max results"),
):
    """Return the most recent outputs."""
    from utils.output_store import get_latest

    results = get_latest(
        division=division or None,
        task_type=task_type or None,
        limit=limit,
    )
    return {"count": len(results), "outputs": results}


@router.get("/search")
def search_outputs(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=20, ge=1, le=100, description="Max results"),
):
    """Full-text search across title, summary, and tags."""
    from utils.output_store import search_outputs as _search

    results = _search(query=q, limit=limit)
    return {"query": q, "count": len(results), "outputs": results}


@router.get("/division/{division}")
def outputs_by_division(
    division: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List all outputs for a specific division."""
    from utils.output_store import list_outputs as _list

    results = _list(division=division, limit=limit, offset=offset)
    return {"division": division, "count": len(results), "outputs": results}


@router.get("/{task_id}")
def get_output(task_id: str):
    """Get a specific output with full content."""
    from utils.output_store import get_output as _get

    result = _get(task_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Output not found: {task_id}")
    return result
