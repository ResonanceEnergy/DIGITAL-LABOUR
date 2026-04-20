"""
Notification data models and SQLite-backed store.

Thread-safe, WAL-mode SQLite storage for the notification system.
DB path defaults to <project_root>/data/notifications.db.
"""

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class NotificationType(str, Enum):
    DECISION_NEEDED = "DECISION_NEEDED"
    PAYMENT_REQUIRED = "PAYMENT_REQUIRED"
    STATUS_UPDATE = "STATUS_UPDATE"
    MILESTONE = "MILESTONE"
    ERROR = "ERROR"
    CLIENT_ACTION = "CLIENT_ACTION"


class NotificationPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NotificationStatus(str, Enum):
    UNREAD = "UNREAD"
    READ = "READ"
    ACTIONED = "ACTIONED"
    DISMISSED = "DISMISSED"


# Default priority per notification type
_DEFAULT_PRIORITY = {
    NotificationType.DECISION_NEEDED: NotificationPriority.HIGH,
    NotificationType.PAYMENT_REQUIRED: NotificationPriority.HIGH,
    NotificationType.STATUS_UPDATE: NotificationPriority.LOW,
    NotificationType.MILESTONE: NotificationPriority.MEDIUM,
    NotificationType.ERROR: NotificationPriority.CRITICAL,
    NotificationType.CLIENT_ACTION: NotificationPriority.MEDIUM,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_db_path(db_path: Optional[str] = None) -> str:
    """Resolve the database path, creating parent dirs if needed."""
    if db_path is None:
        project_root = Path(__file__).resolve().parent.parent
        db_path = str(project_root / "data" / "notifications.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return db_path


class NotificationStore:
    """
    Thread-safe SQLite-backed notification store.

    Each instance maintains its own connection pool keyed by thread id.
    WAL mode is enabled for concurrent reads during writes.
    """

    _CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS notifications (
        id              TEXT PRIMARY KEY,
        type            TEXT NOT NULL,
        title           TEXT NOT NULL,
        message         TEXT NOT NULL,
        priority        TEXT NOT NULL DEFAULT 'MEDIUM',
        status          TEXT NOT NULL DEFAULT 'UNREAD',
        source          TEXT NOT NULL DEFAULT 'system',
        action_url      TEXT,
        action_label    TEXT,
        metadata        TEXT DEFAULT '{}',
        created_at      TEXT NOT NULL,
        read_at         TEXT,
        actioned_at     TEXT
    );
    """

    _CREATE_INDEXES = [
        "CREATE INDEX IF NOT EXISTS idx_notif_status ON notifications(status);",
        "CREATE INDEX IF NOT EXISTS idx_notif_type ON notifications(type);",
        "CREATE INDEX IF NOT EXISTS idx_notif_priority ON notifications(priority);",
        "CREATE INDEX IF NOT EXISTS idx_notif_created ON notifications(created_at DESC);",
    ]

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = _resolve_db_path(db_path)
        self._local = threading.local()
        self._init_lock = threading.Lock()
        self._ensure_schema()

    def _get_conn(self) -> sqlite3.Connection:
        """Return a per-thread connection, creating one if needed."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._db_path, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")
            conn.execute("PRAGMA foreign_keys=ON;")
            self._local.conn = conn
        return conn

    @contextmanager
    def _transaction(self):
        """Context manager that commits on success, rolls back on error."""
        conn = self._get_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _ensure_schema(self):
        """Create tables and indexes if they don't exist (thread-safe)."""
        with self._init_lock:
            with self._transaction() as conn:
                conn.execute(self._CREATE_TABLE)
                for idx_sql in self._CREATE_INDEXES:
                    conn.execute(idx_sql)

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    def create(
        self,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: Optional[NotificationPriority] = None,
        source: str = "system",
        action_url: Optional[str] = None,
        action_label: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new notification. Returns the full notification dict.

        If priority is not specified, a sensible default is chosen based
        on the notification type.
        """
        if priority is None:
            priority = _DEFAULT_PRIORITY.get(
                notification_type, NotificationPriority.MEDIUM
            )

        notif_id = str(uuid.uuid4())
        now = _now_iso()
        meta_json = json.dumps(metadata or {})

        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO notifications
                    (id, type, title, message, priority, status, source,
                     action_url, action_label, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    notif_id,
                    notification_type.value,
                    title,
                    message,
                    priority.value,
                    NotificationStatus.UNREAD.value,
                    source,
                    action_url,
                    action_label,
                    meta_json,
                    now,
                ),
            )

        return self.get(notif_id)

    def get(self, notif_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single notification by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM notifications WHERE id = ?", (notif_id,)
        ).fetchone()
        return self._row_to_dict(row) if row else None

    def list_notifications(
        self,
        status: Optional[str] = None,
        notification_type: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List notifications with optional filters.

        All filter values are matched case-insensitively against enum values.
        """
        clauses: List[str] = []
        params: List[Any] = []

        if status:
            clauses.append("status = ?")
            params.append(status.upper())
        if notification_type:
            clauses.append("type = ?")
            params.append(notification_type.upper())
        if priority:
            clauses.append("priority = ?")
            params.append(priority.upper())

        where = ""
        if clauses:
            where = "WHERE " + " AND ".join(clauses)

        query = f"""
            SELECT * FROM notifications
            {where}
            ORDER BY
                CASE priority
                    WHEN 'CRITICAL' THEN 0
                    WHEN 'HIGH' THEN 1
                    WHEN 'MEDIUM' THEN 2
                    WHEN 'LOW' THEN 3
                END,
                created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        conn = self._get_conn()
        rows = conn.execute(query, params).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def unread_count(self) -> int:
        """Return the count of unread notifications."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM notifications WHERE status = ?",
            (NotificationStatus.UNREAD.value,),
        ).fetchone()
        return row["cnt"] if row else 0

    def mark_read(self, notif_id: str) -> Optional[Dict[str, Any]]:
        """Mark a notification as read."""
        return self._update_status(
            notif_id, NotificationStatus.READ, read_at=_now_iso()
        )

    def mark_actioned(self, notif_id: str) -> Optional[Dict[str, Any]]:
        """Mark a notification as actioned."""
        now = _now_iso()
        return self._update_status(
            notif_id, NotificationStatus.ACTIONED, read_at=now, actioned_at=now
        )

    def mark_dismissed(self, notif_id: str) -> Optional[Dict[str, Any]]:
        """Mark a notification as dismissed."""
        return self._update_status(
            notif_id, NotificationStatus.DISMISSED, read_at=_now_iso()
        )

    def clear_dismissed(self, older_than_days: int = 30) -> int:
        """
        Delete dismissed notifications older than the given number of days.
        Returns the count of deleted rows.
        """
        cutoff = datetime.now(timezone.utc)
        # Calculate cutoff by subtracting days manually to avoid importing timedelta at top
        from datetime import timedelta

        cutoff = (cutoff - timedelta(days=older_than_days)).isoformat()

        with self._transaction() as conn:
            cursor = conn.execute(
                """
                DELETE FROM notifications
                WHERE status = ? AND created_at < ?
                """,
                (NotificationStatus.DISMISSED.value, cutoff),
            )
            return cursor.rowcount

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_status(
        self,
        notif_id: str,
        new_status: NotificationStatus,
        read_at: Optional[str] = None,
        actioned_at: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update status and optional timestamp fields."""
        sets = ["status = ?"]
        params: List[Any] = [new_status.value]

        if read_at:
            sets.append("read_at = COALESCE(read_at, ?)")
            params.append(read_at)
        if actioned_at:
            sets.append("actioned_at = ?")
            params.append(actioned_at)

        params.append(notif_id)

        with self._transaction() as conn:
            cursor = conn.execute(
                f"UPDATE notifications SET {', '.join(sets)} WHERE id = ?",
                params,
            )
            if cursor.rowcount == 0:
                return None

        return self.get(notif_id)

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a sqlite3.Row to a plain dict with parsed metadata."""
        d = dict(row)
        try:
            d["metadata"] = json.loads(d.get("metadata") or "{}")
        except (json.JSONDecodeError, TypeError):
            d["metadata"] = {}
        return d

    def close(self):
        """Close the current thread's connection if open."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None
