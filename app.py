"""
Minervini Screener v1.0 - Backend Application Entry Point
"""
import uvicorn
from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


def main():
    logger.info("正在启动Minervini选股器v1.0", app_name=settings.app.name)
    uvicorn.run(
        "web.api:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app.debug,
    )


if __name__ == "__main__":
    main()
