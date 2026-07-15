"""
Minervini Screener v1.0 - Tasks API
Manage scheduled background tasks.
"""
from fastapi import APIRouter

from core.logging_setup import get_logger

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
logger = get_logger(__name__)


@router.get("/")
async def list_tasks():
    """List all scheduled background tasks."""
    return {
        "tasks": [
            {
                "id": "daily_scan",
                "name": "每日扫描",
                "schedule": "交易日 15:30",
                "enabled": True,
                "last_run": None,
                "status": "idle",
            },
            {
                "id": "data_update",
                "name": "数据更新",
                "schedule": "交易日 09:00",
                "enabled": True,
                "last_run": None,
                "status": "idle",
            },
        ]
    }


@router.post("/trigger/{task_id}")
async def trigger_task(task_id: str):
    """Manually trigger a background task."""
    logger.info(f"手动触发任务: {task_id}")
    return {
        "task_id": task_id,
        "status": "triggered",
        "message": f"任务{task_id}已触发",
    }


@router.get("/status")
async def task_status():
    """Get running task status."""
    return {"running_tasks": [], "queue_size": 0}


@router.get("/log")
async def task_log():
    """Get task execution log."""
    return {"message": "任务日志功能待实现", "entries": []}
