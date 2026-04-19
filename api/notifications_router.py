"""FastAPI router for the notification system.

Wraps the SQLite-backed NotificationStore to provide REST endpoints
for the unified workstation dashboard.

Wire into intake.py:
    from api.notifications_router import router as notifications_router
    app.include_router(notifications_router)
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = os.environ.get(
    "NOTIFICATIONS_DB_PATH",
    str(PROJECT_ROOT / "data" / "notifications.db"),
)

try:
    from notifications.models import (
        NotificationPriority,
        NotificationStatus,
        NotificationStore,
        NotificationType,
    )
    _store = NotificationStore(db_path=DB_PATH)
except Exception:
    _store = None


router = APIRouter(prefix="/api/v1", tags=["notifications"])


class NotificationCreate(BaseModel):
    type: str
    title: str
    message: str
    priority: Optional[str] = None
    source: str = "system"
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationResponse(BaseModel):
    notification: Dict[str, Any]


class NotificationListResponse(BaseModel):
    notifications: List[Dict[str, Any]]
    count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class DeletedCountResponse(BaseModel):
    deleted_count: int

def _validate_enum(value, enum_cls, field_name):
    upper = value.upper()
    try:
        return enum_cls(upper)
    except (ValueError, KeyError):
        valid = [e.value for e in enum_cls]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name} '{value}'. Must be one of: {', '.join(valid)}",
        )


def _get_store():
    global _store
    if _store is None:
        try:
            from notifications.models import NotificationStore
            _store = NotificationStore(db_path=DB_PATH)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Notification store unavailable: {e}")
    return _store


@router.get("/notifications", response_model=NotificationListResponse)
def list_notifications(
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List notifications with optional filters."""
    store = _get_store()
    if status:
        _validate_enum(status, NotificationStatus, "status")
    if type:
        _validate_enum(type, NotificationType, "type")
    if priority:
        _validate_enum(priority, NotificationPriority, "priority")
    results = store.list_notifications(
        status=status, notification_type=type,
        priority=priority, limit=limit, offset=offset,
    )
    return {"notifications": results, "count": len(results)}


@router.get("/notifications/unread/count", response_model=UnreadCountResponse)
def unread_count():
    """Quick badge count of unread notifications."""
    store = _get_store()
    return {"unread_count": store.unread_count()}


@router.post("/notifications", response_model=NotificationResponse, status_code=201)
def create_notification(body: NotificationCreate):
    """Create a new notification."""
    store = _get_store()
    ntype = _validate_enum(body.type, NotificationType, "type")
    priority = None
    if body.priority:
        priority = _validate_enum(body.priority, NotificationPriority, "priority")
    notif = store.create(
        notification_type=ntype, title=body.title, message=body.message,
        priority=priority, source=body.source, action_url=body.action_url,
        action_label=body.action_label, metadata=body.metadata,
    )
    return {"notification": notif}


@router.patch("/notifications/{notif_id}/read", response_model=NotificationResponse)
def mark_read(notif_id: str):
    """Mark a notification as read."""
    store = _get_store()
    notif = store.mark_read(notif_id)
    if notif is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"notification": notif}


@router.patch("/notifications/{notif_id}/action", response_model=NotificationResponse)
def mark_actioned(notif_id: str):
    """Mark a notification as actioned."""
    store = _get_store()
    notif = store.mark_actioned(notif_id)
    if notif is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"notification": notif}


@router.patch("/notifications/{notif_id}/dismiss", response_model=NotificationResponse)
def mark_dismissed(notif_id: str):
    """Mark a notification as dismissed."""
    store = _get_store()
    notif = store.mark_dismissed(notif_id)
    if notif is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"notification": notif}


@router.delete("/notifications/clear", response_model=DeletedCountResponse)
def clear_dismissed(older_than_days: int = Query(30, ge=1)):
    """Remove dismissed notifications older than N days."""
    store = _get_store()
    deleted = store.clear_dismissed(older_than_days=older_than_days)
    return {"deleted_count": deleted}
