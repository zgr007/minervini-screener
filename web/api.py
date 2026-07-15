"""
Minervini Screener v1.0 - FastAPI Application Factory
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.loader import settings
from core.logging_setup import setup_logging, get_logger

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    setup_logging(
        log_level=settings.app.log_level,
        log_format=settings.app.log_format,
    )

    app = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Root — welcome / redirect
    @app.get("/")
    async def root():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/docs")

    # Health check
    @app.get("/health")
    async def health():
        return {"status": "ok", "app": settings.app.name, "version": settings.app.version}

    # Register routers
    from web.routers import (
        health_router,
        screener_router,
        stock_router,
        analysis_router,
        backtest_router,
        settings_router,
        portfolio_router,
        tasks_router,
        stubs_router,
        stock_browser_router,
    )

    app.include_router(health_router)
    app.include_router(screener_router)
    app.include_router(stock_router)
    app.include_router(analysis_router)
    app.include_router(backtest_router)
    app.include_router(settings_router)
    app.include_router(portfolio_router)
    app.include_router(tasks_router)
    app.include_router(stubs_router)
    app.include_router(stock_browser_router)

    logger.info("应用已创建", routes=len(app.routes))
    return app


app = create_app()
