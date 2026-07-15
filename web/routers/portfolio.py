"""
Minervini Screener v1.0 - Portfolio API
Track and manage simulated portfolio.
"""
from fastapi import APIRouter, Query

from core.logging_setup import get_logger
from core.portfolio import Portfolio

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])
logger = get_logger(__name__)

# In-memory portfolio instance (replace with DB in production)
_portfolio: Portfolio = Portfolio()


@router.get("/")
async def get_portfolio():
    """Get current portfolio status."""
    summary = _portfolio.get_summary()
    positions = []
    for code, pos in _portfolio.positions.items():
        positions.append({
            "code": code,
            "name": pos.name,
            "entry_date": pos.entry_date,
            "entry_price": pos.entry_price,
            "current_price": pos.current_price,
            "shares": pos.shares,
            "pnl_pct": round(pos.pnl_pct, 2),
            "pnl_amount": round(pos.pnl_amount, 2),
            "stop_price": pos.stop_price,
            "status": pos.status,
        })
    return {"summary": summary, "positions": positions}


@router.get("/closed")
async def closed_positions():
    """Get closed positions history."""
    closed = []
    for pos in _portfolio.closed_positions:
        closed.append({
            "code": pos.code,
            "name": pos.name,
            "entry_date": pos.entry_date,
            "entry_price": pos.entry_price,
            "exit_price": pos.current_price,
            "shares": pos.shares,
            "pnl_pct": round(pos.pnl_pct, 2),
            "pnl_amount": round(pos.pnl_amount, 2),
        })
    return {"count": len(closed), "positions": closed}


@router.get("/trades")
async def trade_log():
    """Get full trade log."""
    return {"count": len(_portfolio.trades_log), "trades": _portfolio.trades_log}


@router.post("/reset")
async def reset_portfolio():
    """Reset portfolio to initial state."""
    global _portfolio
    _portfolio = Portfolio()
    return {"status": "reset", "message": "投资组合已重置"}
