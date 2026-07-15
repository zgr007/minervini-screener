"""
Minervini Screener v1.0 - Simple Async Task Manager
Tracks background data download tasks in memory.
"""
import uuid
from datetime import datetime
from typing import Optional
from core.logging_setup import get_logger

logger = get_logger(__name__)

# In-memory task store: {task_id: {"status": ..., "started_at": ..., "completed_at": ..., "error": ...}}
_tasks: dict[str, dict] = {}


def create_task() -> str:
    """Create a new pending task, return its ID."""
    task_id = uuid.uuid4().hex[:12]
    _tasks[task_id] = {
        "status": "pending",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "error": None,
    }
    logger.info(f"任务已创建: {task_id}")
    return task_id


def start_task(task_id: str):
    """Mark task as running."""
    if task_id in _tasks:
        _tasks[task_id]["status"] = "running"


def complete_task(task_id: str, error: Optional[str] = None):
    """Mark task as completed (or failed if error is set)."""
    if task_id in _tasks:
        _tasks[task_id]["status"] = "failed" if error else "completed"
        _tasks[task_id]["completed_at"] = datetime.now().isoformat()
        _tasks[task_id]["error"] = error


def get_task(task_id: str) -> Optional[dict]:
    """Get task status dict."""
    return _tasks.get(task_id)


def cleanup_old_tasks(max_age_hours: int = 1):
    """Remove tasks older than max_age_hours."""
    now = datetime.now()
    to_delete = []
    for tid, task in _tasks.items():
        started = datetime.fromisoformat(task["started_at"])
        if (now - started).total_seconds() > max_age_hours * 3600:
            to_delete.append(tid)
    for tid in to_delete:
        del _tasks[tid]
