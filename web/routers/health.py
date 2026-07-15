"""
Minervini Screener v1.0 - Health Check API
"""
from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "ok",
        "service": "Minervini Screener API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/health/db")
async def db_health():
    """Database health check (if applicable)."""
    try:
        from data.database import async_session_factory
        async with async_session_factory() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except ImportError:
        return {"status": "ok", "database": "not_configured"}
    except Exception as e:
        return {"status": "error", "database": "disconnected", "detail": str(e)}
