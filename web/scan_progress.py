"""
Minervini Screener v1.0 - Scan Progress Tracker
In-memory scan run state for progress bar support.
Single-worker design — shared dict is safe for one uvicorn worker.
"""
from datetime import datetime
from core.logging_setup import get_logger

logger = get_logger(__name__)

# In-memory scan run state
_run: dict = {
    "run_id": None,
    "status": "idle",          # idle | running | completed | failed
    "phase": "",
    "phase_label": "",
    "total": 0,
    "processed": 0,
    "percent": 0.0,
    "message": "",
    "started_at": None,
    "completed_at": None,
}


def create_run(run_id: str, total: int = 0) -> None:
    """Initialize a new scan run."""
    _run["run_id"] = run_id
    _run["status"] = "running"
    _run["phase"] = "initializing"
    _run["phase_label"] = "初始化..."
    _run["total"] = total
    _run["processed"] = 0
    _run["percent"] = 0.0
    _run["message"] = ""
    _run["started_at"] = datetime.now().isoformat()
    _run["completed_at"] = None
    logger.info(f"扫描任务已创建: {run_id}, 总计={total}")


def update_progress(
    processed: int,
    total: int,
    phase: str = "",
    phase_label: str = "",
    message: str = "",
) -> None:
    """Update scan progress during execution."""
    _run["processed"] = processed
    _run["total"] = total
    _run["percent"] = round(processed / total * 100, 1) if total > 0 else 0
    if phase:
        _run["phase"] = phase
    if phase_label:
        _run["phase_label"] = phase_label
    if message:
        _run["message"] = message
    _run["status"] = "running"


def complete_run(status: str = "completed", error: str = "") -> None:
    """Mark scan run as completed or failed."""
    _run["status"] = status
    _run["phase_label"] = "完成" if status == "completed" else "失败"
    _run["percent"] = 100.0 if status == "completed" else _run["percent"]
    _run["completed_at"] = datetime.now().isoformat()
    if error:
        _run["message"] = error
    logger.info(f"扫描任务完成: status={status}")


def get_progress() -> dict:
    """Return current scan progress snapshot."""
    return dict(_run)


def is_running() -> bool:
    """Check if a scan is currently running."""
    return _run["status"] == "running"
