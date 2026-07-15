"""
Minervini Screener v1.0 - Settings API
View and update application configuration at runtime.
"""
from fastapi import APIRouter, Body

from config.loader import settings
from core.logging_setup import get_logger

router = APIRouter(prefix="/api/settings", tags=["settings"])
logger = get_logger(__name__)


@router.get("/")
async def get_settings():
    """Get current application settings (non-sensitive)."""
    # Exclude passwords, tokens, and other secrets
    safe = _sanitize_settings(settings.model_dump() if hasattr(settings, "model_dump") else settings.__dict__)
    return {"settings": safe}


@router.put("/")
async def update_settings(
    updates: dict = Body(..., description="要更新的配置项"),
):
    """Update configuration at runtime.

    Note: Changes are not persisted to config files.
    """
    try:
        for key, value in updates.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        return {"status": "updated", "applied": list(updates.keys())}
    except Exception as e:
        logger.error(f"配置更新失败: {e}")
        return {"error": str(e)}


@router.get("/schema")
async def get_settings_schema():
    """Get settings schema for UI generation."""
    return {
        "message": "配置模式功能待实现",
    }


def _sanitize_settings(d: dict, depth: int = 0) -> dict:
    """Recursively remove sensitive fields from settings dict."""
    sensitive_keys = {"password", "token", "secret", "api_key", "key", "auth"}
    result = {}
    for k, v in d.items():
        if k.lower() in sensitive_keys:
            result[k] = "***"
        elif isinstance(v, dict) and depth < 5:
            result[k] = _sanitize_settings(v, depth + 1)
        elif isinstance(v, (str, int, float, bool, list)) or v is None:
            result[k] = v
        else:
            result[k] = str(v)
    return result
