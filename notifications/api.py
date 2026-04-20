"""
REST API route handlers for the notification system.

Provides both a Flask Blueprint and a standalone Flask app.
Can also be used with FastAPI by importing the handler functions directly.

Usage with Flask:
    from notifications.api import notifications_bp
    app.register_blueprint(notifications_bp, url_prefix="/api/v1")

Standalone:
    python -m notifications.api
"""

import json
import os
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple

from flask import Blueprint, Flask, Response, jsonify, request

from notifications.models import (
    NotificationPriority,
    NotificationStatus,
    NotificationStore,
    NotificationType,
)

# ---------------------------------------------------------------------------
# Shared store instance (lazy-init, thread-safe via NotificationStore)
# ---------------------------------------------------------------------------
_store: Optional[NotificationStore] = None


def _get_store() -> NotificationStore:
    global _store
    if _store is None:
        db_path = os.environ.get("NOTIFICATIONS_DB_PATH", None)
        _store = NotificationStore(db_path=db_path)
    return _store


def set_store(store: NotificationStore) -> None:
    """Allow tests or other code to inject a custom store instance."""
    global _store
    _store = store


# ---------------------------------------------------------------------------
# Error handling decorator
# ---------------------------------------------------------------------------

def _handle_errors(fn: Callable) -> Callable:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Tuple[Response, int]:
        try:
            return fn(*args, **kwargs)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except KeyError as exc:
            return jsonify({"error": f"Missing field: {exc}"}), 400
        except Exception as exc:
            return jsonify({"error": f"Internal error: {exc}"}), 500
    return wrapper


# ---------------------------------------------------------------------------
# Blueprint
# ---------------------------------------------------------------------------

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/notifications", methods=["GET"])
@_handle_errors
def list_notifications():
    """
    GET /notifications?status=UNREAD&type=ERROR&priority=HIGH&limit=50&offset=0

    Returns a list of notifications, sorted by priority then recency.
    """
    store = _get_store()

    status = request.args.get("status")
    ntype = request.args.get("type")
    priority = request.args.get("priority")
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))

    # Validate enum values if provided
    if status:
        _validate_enum(status, NotificationStatus, "status")
    if ntype:
        _validate_enum(ntype, NotificationType, "type")
    if priority:
        _validate_enum(priority, NotificationPriority, "priority")

    results = store.list_notifications(
        status=status,
        notification_type=ntype,
        priority=priority,
        limit=min(limit, 500),
        offset=offset,
    )

    return jsonify({"notifications": results, "count": len(results)}), 200


@notifications_bp.route("/notifications/unread/count", methods=["GET"])
@_handle_errors
def unread_count():
    """GET /notifications/unread/count - Quick badge count."""
    store = _get_store()
    count = store.unread_count()
    return jsonify({"unread_count": count}), 200


@notifications_bp.route("/notifications", methods=["POST"])
@_handle_errors
def create_notification():
    """
    POST /notifications

    JSON body:
        {
            "type": "ERROR",
            "title": "Build failed",
            "message": "Details here",
            "priority": "HIGH",          // optional
            "source": "deploy-agent",    // optional
            "action_url": "https://...", // optional
            "action_label": "View Logs", // optional
            "metadata": {}              // optional
        }
    """
    store = _get_store()
    data = request.get_json(force=True)

    if not data:
        raise ValueError("Request body must be JSON")

    # Required fields
    ntype_str = data.get("type")
    title = data.get("title")
    message = data.get("message")

    if not ntype_str or not title or not message:
        raise ValueError("Fields 'type', 'title', and 'message' are required")

    ntype = _validate_enum(ntype_str, NotificationType, "type")

    priority = None
    if "priority" in data:
        priority = _validate_enum(data["priority"], NotificationPriority, "priority")

    notif = store.create(
        notification_type=ntype,
        title=title,
        message=message,
        priority=priority,
        source=data.get("source", "system"),
        action_url=data.get("action_url"),
        action_label=data.get("action_label"),
        metadata=data.get("metadata"),
    )

    return jsonify({"notification": notif}), 201


@notifications_bp.route("/notifications/<notif_id>/read", methods=["PATCH"])
@_handle_errors
def mark_read(notif_id: str):
    """PATCH /notifications/{id}/read"""
    store = _get_store()
    notif = store.mark_read(notif_id)
    if notif is None:
        return jsonify({"error": "Notification not found"}), 404
    return jsonify({"notification": notif}), 200


@notifications_bp.route("/notifications/<notif_id>/action", methods=["PATCH"])
@_handle_errors
def mark_actioned(notif_id: str):
    """PATCH /notifications/{id}/action"""
    store = _get_store()
    notif = store.mark_actioned(notif_id)
    if notif is None:
        return jsonify({"error": "Notification not found"}), 404
    return jsonify({"notification": notif}), 200


@notifications_bp.route("/notifications/<notif_id>/dismiss", methods=["PATCH"])
@_handle_errors
def mark_dismissed(notif_id: str):
    """PATCH /notifications/{id}/dismiss"""
    store = _get_store()
    notif = store.mark_dismissed(notif_id)
    if notif is None:
        return jsonify({"error": "Notification not found"}), 404
    return jsonify({"notification": notif}), 200


@notifications_bp.route("/notifications/clear", methods=["DELETE"])
@_handle_errors
def clear_dismissed():
    """
    DELETE /notifications/clear?older_than_days=30

    Removes dismissed notifications older than the specified number of days.
    """
    store = _get_store()
    days = int(request.args.get("older_than_days", 30))
    deleted = store.clear_dismissed(older_than_days=days)
    return jsonify({"deleted_count": deleted}), 200


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_enum(value: str, enum_cls: type, field_name: str):
    """Validate and return an enum member, raising ValueError on mismatch."""
    upper = value.upper()
    try:
        return enum_cls(upper)
    except ValueError:
        valid = [e.value for e in enum_cls]
        raise ValueError(
            f"Invalid {field_name} '{value}'. Must be one of: {', '.join(valid)}"
        )


# ---------------------------------------------------------------------------
# Standalone app
# ---------------------------------------------------------------------------

def create_app() -> Flask:
    """Create a standalone Flask app with the notifications blueprint."""
    app = Flask(__name__)
    app.register_blueprint(notifications_bp, url_prefix="/api/v1")

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "service": "notifications"}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("NOTIFICATIONS_PORT", 5099))
    app.run(host="0.0.0.0", port=port, debug=False)
