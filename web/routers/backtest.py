"""
Minervini Screener v1.0 - Backtest API
Runs and displays backtesting results.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query

from core.logging_setup import get_logger
from core.backtest import SEPABacktest

router = APIRouter(prefix="/api/backtest", tags=["backtest"])
logger = get_logger(__name__)


@router.get("/run")
async def run_backtest(
    market: str = Query("US", description="市场: US/CN"),
    start_date: str = Query("2024-01-01", description="开始日期"),
    end_date: str = Query("", description="结束日期(默认今天)"),
    initial_capital: float = Query(100000, description="初始资金"),
    max_positions: int = Query(10, description="最大持仓数"),
    symbols: str = Query("", description="自定义股票池，逗号分隔"),
):
    """Run a backtest synchronously (may take time)."""
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()] if symbols else None
    engine = SEPABacktest(
        market=market,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        max_positions=max_positions,
        symbols=symbol_list,
    )
    result = await engine.run()
    return {
        "status": "completed",
        "message": result.get("message", ""),
        "config": result["config"],
        "metrics": result["metrics"],
        "trades": result["trades"],
        "equity_curve": result["equity_curve"],
    }


@router.get("/results")
async def backtest_results(backtest_id: str = Query("", description="回测ID")):
    """Get backtest results."""
    return {
        "backtest_id": backtest_id,
        "message": "使用 POST /api/backtests/run 运行回测",
    }


@router.get("/metrics")
async def backtest_metrics():
    """Get performance metrics from last backtest."""
    return {"message": "查看回测结果请使用 POST /api/backtests/run"}


@router.get("/leaderboard")
async def backtest_leaderboard(
    sort_by: str = Query("total_return", description="排序字段"),
    limit: int = Query(20, le=100),
):
    return {"message": "排行榜功能待实现", "results": []}
