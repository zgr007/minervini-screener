"""API routers for Minervini Screener."""
from web.routers.health import router as health_router
from web.routers.screener import router as screener_router
from web.routers.stock import router as stock_router
from web.routers.analysis import router as analysis_router
from web.routers.backtest import router as backtest_router
from web.routers.settings import router as settings_router
from web.routers.portfolio import router as portfolio_router
from web.routers.tasks import router as tasks_router
from web.routers.stubs import router as stubs_router
from web.routers.stock_browser import router as stock_browser_router

__all__ = [
    "health_router",
    "screener_router",
    "stock_router",
    "analysis_router",
    "backtest_router",
    "settings_router",
    "portfolio_router",
    "tasks_router",
    "stubs_router",
]
