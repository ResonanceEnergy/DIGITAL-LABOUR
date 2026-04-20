"""
Convenience functions for creating notifications from any module.

These provide a simple, import-and-call interface so that daemons and agents
don't need to know about the store or enum details.

Usage:
    from notifications.helpers import notify_error, notify_milestone

    notify_error("Deploy failed", "Container exited with code 137", source="deploy-agent")
    notify_milestone("Revenue target hit", "Monthly revenue exceeded $50k")
"""

from typing import Any, Dict, Optional

from notifications.models import (
    NotificationPriority,
    NotificationStore,
    NotificationType,
)

# Module-level store singleton (lazy-initialized, thread-safe)
_store: Optional[NotificationStore] = None


def _get_store() -> NotificationStore:
    global _store
    if _store is None:
        _store = NotificationStore()
    return _store


def set_store(store: NotificationStore) -> None:
    """Inject a custom store (useful for tests or shared instances)."""
    global _store
    _store = store


# ---------------------------------------------------------------------------
# Public convenience functions
# ---------------------------------------------------------------------------


def notify_decision_needed(
    title: str,
    message: str,
    action_url: Optional[str] = None,
    action_label: Optional[str] = None,
    source: str = "system",
    priority: Optional[NotificationPriority] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a DECISION_NEEDED notification.

    Use when something requires human approval or a choice between options.
    """
    label = action_label or ("Decide" if action_url else None)
    return _get_store().create(
        notification_type=NotificationType.DECISION_NEEDED,
        title=title,
        message=message,
        priority=priority or NotificationPriority.HIGH,
        source=source,
        action_url=action_url,
        action_label=label,
        metadata=metadata,
    )


def notify_payment_required(
    title: str,
    message: str,
    amount: float,
    action_url: Optional[str] = None,
    source: str = "billing",
    priority: Optional[NotificationPriority] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a PAYMENT_REQUIRED notification.

    The amount is stored in metadata automatically.
    """
    meta = metadata or {}
    meta["amount"] = amount

    return _get_store().create(
        notification_type=NotificationType.PAYMENT_REQUIRED,
        title=title,
        message=message,
        priority=priority or NotificationPriority.HIGH,
        source=source,
        action_url=action_url,
        action_label="Pay Now" if action_url else None,
        metadata=meta,
    )


def notify_status_update(
    title: str,
    message: str,
    source: str = "system",
    priority: Optional[NotificationPriority] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a STATUS_UPDATE notification.

    General-purpose informational update (task progress, state changes, etc.).
    """
    return _get_store().create(
        notification_type=NotificationType.STATUS_UPDATE,
        title=title,
        message=message,
        priority=priority or NotificationPriority.LOW,
        source=source,
        metadata=metadata,
    )


def notify_milestone(
    title: str,
    message: str,
    source: str = "system",
    priority: Optional[NotificationPriority] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a MILESTONE notification.

    Use for significant achievements, targets hit, or project completions.
    """
    return _get_store().create(
        notification_type=NotificationType.MILESTONE,
        title=title,
        message=message,
        priority=priority or NotificationPriority.MEDIUM,
        source=source,
        metadata=metadata,
    )


def notify_error(
    title: str,
    message: str,
    source: str = "system",
    priority: Optional[NotificationPriority] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create an ERROR notification.

    Use for failures, crashes, or conditions requiring immediate attention.
    """
    return _get_store().create(
        notification_type=NotificationType.ERROR,
        title=title,
        message=message,
        priority=priority or NotificationPriority.CRITICAL,
        source=source,
        metadata=metadata,
    )


def notify_client_action(
    title: str,
    message: str,
    client_id: str,
    action_url: Optional[str] = None,
    source: str = "system",
    priority: Optional[NotificationPriority] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a CLIENT_ACTION notification.

    Use when a client needs to take action (respond, approve, provide info).
    The client_id is stored in metadata automatically.
    """
    meta = metadata or {}
    meta["client_id"] = client_id

    return _get_store().create(
        notification_type=NotificationType.CLIENT_ACTION,
        title=title,
        message=message,
        priority=priority or NotificationPriority.MEDIUM,
        source=source,
        action_url=action_url,
        action_label="Review" if action_url else None,
        metadata=meta,
    )
