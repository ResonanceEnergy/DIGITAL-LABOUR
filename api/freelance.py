"""Freelance API routes — job hunt, bidding, delivery, and status.

Provides HTTP endpoints for the freelance automation engine:
  - /freelance/hunt      — Trigger job aggregation across platforms
  - /freelance/bid       — Run autobidder scan
  - /freelance/deliver   — Check and fulfill pending orders
  - /freelance/status    — Dashboard + stats
  - /freelance/cycle     — Full hunt→bid→deliver cycle
  - /freelance/feed      — Get ranked job feed
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

router = APIRouter(prefix="/freelance", tags=["Freelance"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_VALID_PLATFORMS = {"freelancer", "upwork", "fiverr", ""}


class CycleRequest(BaseModel):
    platform: str = ""
    dry_run: bool = False

    @field_validator("platform")
    @classmethod
    def platform_must_be_valid(cls, v: str) -> str:
        if v and v not in _VALID_PLATFORMS:
            raise ValueError(f"Unknown platform '{v}'. Valid: {sorted(_VALID_PLATFORMS - {''})}")
        return v


class FeedRequest(BaseModel):
    platform: str = ""
    agent: str = ""
    top: int = 30
    hours: int = 48


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/cycle")
def run_full_cycle(req: CycleRequest):
    """Run full freelance automation cycle: hunt → bid → deliver → revenue."""
    try:
        from automation.freelance_engine import full_cycle
        report = full_cycle(platform_filter=req.platform, dry_run=req.dry_run)
        return {"status": "ok", "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hunt")
def trigger_hunt(req: CycleRequest):
    """Aggregate and rank jobs from all platforms."""
    try:
        from automation.freelance_engine import hunt_jobs
        result = hunt_jobs(platform_filter=req.platform)
        return {"status": "ok", "hunt": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bid")
def trigger_autobid(req: CycleRequest):
    """Run one autobidder scan cycle."""
    try:
        from automation.freelance_engine import run_autobid
        result = run_autobid(dry_run=req.dry_run)
        return {"status": "ok", "autobid": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deliver")
def trigger_delivery():
    """Check all platforms for pending orders and report status."""
    try:
        from automation.freelance_engine import check_and_deliver
        result = check_and_deliver()
        return {"status": "ok", "delivery": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
def freelance_status():
    """Get comprehensive freelance automation status."""
    try:
        from automation.freelance_engine import status_dashboard
        state = status_dashboard()
        return {"status": "ok", "state": state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/revenue")
def freelance_revenue():
    """Get revenue tracking across all freelance sources."""
    try:
        from automation.freelance_engine import track_revenue
        result = track_revenue()
        return {"status": "ok", "revenue": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feed")
def get_job_feed(req: FeedRequest):
    """Get the ranked job feed from all platforms."""
    try:
        from automation.job_aggregator import aggregate
        feed = aggregate(
            max_age_hours=req.hours,
            platform_filter=req.platform,
            agent_filter=req.agent,
        )
        return {
            "status": "ok",
            "total": len(feed),
            "feed": feed[:req.top],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/review-queue")
def get_review_queue():
    """Get bids pending human review."""
    review_file = PROJECT_ROOT / "data" / "autobidder" / "human_review_queue.json"
    if not review_file.exists():
        return {"status": "ok", "queue": [], "count": 0}
    try:
        queue = json.loads(review_file.read_text(encoding="utf-8"))
        return {"status": "ok", "queue": queue, "count": len(queue)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
