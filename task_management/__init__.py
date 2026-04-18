"""BRL Task Management System — Full ops tracking for human + AI work.

Integrates with NCL (intelligence), Paperclip/C-Suite (directives),
and NERVE (autonomous execution) to keep BRL synced with everything
that needs doing.
"""

from task_management.store import TaskStore
from task_management.manager import TaskManager

__all__ = ["TaskStore", "TaskManager"]
