"""Revenue Dashboard API Router -- Exposes revenue metrics as REST endpoints.

Provides read-only access to revenue summaries, agent performance, channel
breakdowns, and client LTV rankings.  Protected by the same API key auth
used across the platform.

Mount in the main app:
    from api.revenue import router as revenue_router
    app.include_router(revenue_router)
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query

logger = logging.getLogger("api.revenue")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Auth (shared pattern with intake/rapidapi) ───────────────────────────────

MATRIX_AUTH_TOKEN = os.getenv("MATRIX_AUTH_TOKEN", "")


async def verify_revenue_access(
    x_api_key: Optional[str] = Header(None),
    x_matrix_token: Optional[str] = Header(None),
) -> bool:
    """Verify access to revenue data.

    Accepts either:
    - X-API-Key matching a registered client hash
    - X-Matrix-Token matching the MATRIX_AUTH_TOKEN env var (internal dashboards)
    - Unauthenticated in dev mode (no MATRIX_AUTH_TOKEN set)
    """
    # Internal dashboard token
    if MATRIX_AUTH_TOKEN and x_matrix_token:
        if x_matrix_token == MATRIX_AUTH_TOKEN:
            return True
        raise HTTPException(status_code=403, detail="Invalid Matrix token")

    # Client API key
    if x_api_key:
        key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
        clients_dir = PROJECT_ROOT / "clients"
        if clients_dir.exists():
            for profile_path in clients_dir.glob("*.json"):
                try:
                    profile = json.loads(profile_path.read_text(encoding="utf-8"))
                    if profile.get("api_key_hash") == key_hash:
                        return True
                except Exception:
                    continue
        raise HTTPException(status_code=403, detail="Invalid API key")

    # Dev mode fallback
    if not MATRIX_AUTH_TOKEN:
        return True

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Pass X-API-Key or X-Matrix-Token header.",
    )


# ── Router ───────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/revenue", tags=["Revenue"])


def _get_tracker():
    """Lazy import to avoid circular imports at module load time."""
    from billing.revenue_tracker import RevenueTracker
    return RevenueTracker()


@router.get("/summary")
async def revenue_summary(
    days: int = Query(default=30, ge=1, le=365, description="Lookback period in days"),
    _auth: bool = Depends(verify_revenue_access),
):
    """Overall revenue summary with daily breakdown.

    Returns total revenue, costs, profit, margin percentage, average daily
    revenue, projected monthly revenue, and a day-by-day breakdown.
    """
    try:
        rt = _get_tracker()
        summary = rt.get_revenue_summary(days=days)

        # Enrich with weekly and monthly rollups
        summary["weekly"] = rt.get_weekly_summary(weeks=min(days // 7, 12) or 1)
        summary["monthly"] = rt.get_monthly_summary(months=min(days // 30, 6) or 1)

        return summary
    except Exception as exc:
        logger.exception("[REVENUE] Summary query failed")
        raise HTTPException(status_code=500, detail="Failed to generate revenue summary") from exc


@router.get("/agents")
async def revenue_by_agent(
    days: int = Query(default=30, ge=1, le=365, description="Lookback period in days"),
    _auth: bool = Depends(verify_revenue_access),
):
    """Revenue breakdown by agent.

    Returns per-agent task count, revenue, cost, profit, margin percentage,
    and average revenue per task.  Sorted by revenue descending.
    """
    try:
        rt = _get_tracker()
        result = rt.get_agent_performance(days=days)

        # Add top performer highlights
        agents = result.get("agents", {})
        if agents:
            top_revenue = max(agents.items(), key=lambda x: x[1]["revenue"])
            top_margin = max(agents.items(), key=lambda x: x[1]["margin_pct"])
            top_volume = max(agents.items(), key=lambda x: x[1]["tasks"])
            result["highlights"] = {
                "top_revenue_agent": {"agent": top_revenue[0], **top_revenue[1]},
                "top_margin_agent": {"agent": top_margin[0], **top_margin[1]},
                "top_volume_agent": {"agent": top_volume[0], **top_volume[1]},
            }

        return result
    except Exception as exc:
        logger.exception("[REVENUE] Agent performance query failed")
        raise HTTPException(status_code=500, detail="Failed to generate agent performance") from exc


@router.get("/channels")
async def revenue_by_channel(
    days: int = Query(default=30, ge=1, le=365, description="Lookback period in days"),
    _auth: bool = Depends(verify_revenue_access),
):
    """Revenue breakdown by channel.

    Returns per-channel revenue, costs, profit, task count, and percentage
    of total revenue.  Channels: fiverr, api_marketplace, white_label,
    direct, cold_email, freelance.
    """
    try:
        rt = _get_tracker()
        return rt.get_channel_breakdown(days=days)
    except Exception as exc:
        logger.exception("[REVENUE] Channel breakdown query failed")
        raise HTTPException(status_code=500, detail="Failed to generate channel breakdown") from exc


@router.get("/clients")
async def client_ltv_rankings(
    limit: int = Query(default=50, ge=1, le=500, description="Number of clients to return"),
    _auth: bool = Depends(verify_revenue_access),
):
    """Client lifetime value rankings.

    Returns top clients ranked by total lifetime revenue, including task
    count, average revenue per task, first seen, last active, and channel.
    """
    try:
        rt = _get_tracker()
        rankings = rt.get_client_rankings(limit=limit)
        total_ltv = sum(c["total_revenue"] for c in rankings)
        return {
            "total_clients": len(rankings),
            "total_ltv": round(total_ltv, 2),
            "avg_ltv": round(total_ltv / max(len(rankings), 1), 2),
            "clients": rankings,
        }
    except Exception as exc:
        logger.exception("[REVENUE] Client rankings query failed")
        raise HTTPException(status_code=500, detail="Failed to generate client rankings") from exc


@router.get("/clients/{client_id}")
async def client_ltv_detail(
    client_id: str,
    _auth: bool = Depends(verify_revenue_access),
):
    """Detailed lifetime value for a specific client.

    Returns total revenue, total tasks, average revenue per task, tenure,
    agents used, and monthly revenue trend.
    """
    try:
        rt = _get_tracker()
        result = rt.get_client_ltv(client_id=client_id)
        if not result.get("found"):
            raise HTTPException(status_code=404, detail=f"Client '{client_id}' not found")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[REVENUE] Client LTV query failed for %s", client_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve client data") from exc


@router.post("/record")
async def record_revenue_event(
    channel: str = Query(..., description="Revenue channel"),
    agent: str = Query(..., description="Agent task type"),
    client_id: str = Query(..., description="Client identifier"),
    amount: float = Query(..., ge=0, description="Revenue amount in USD"),
    cost: float = Query(default=0.0, ge=0, description="LLM/infra cost in USD"),
    description: str = Query(default="", description="Optional description"),
    _auth: bool = Depends(verify_revenue_access),
):
    """Record a revenue event manually.

    Used for recording revenue from channels that don't flow through the
    standard dispatcher (e.g. manual Fiverr orders, white-label invoices).
    """
    try:
        rt = _get_tracker()
        result = rt.record_revenue(
            channel=channel,
            agent=agent,
            client_id=client_id,
            amount=amount,
            cost=cost,
            description=description,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("[REVENUE] Record failed")
        raise HTTPException(status_code=500, detail="Failed to record revenue event") from exc
