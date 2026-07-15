"""
Minervini Screener v1.0 - Screener API
Main endpoint for running screening scans.
"""
from typing import Optional
from fastapi import APIRouter, Query

from config.loader import settings
from core.logging_setup import get_logger
from data.downloader import DataDownloader

router = APIRouter(prefix="/api/screener", tags=["screener"])
logger = get_logger(__name__)


@router.get("/scan")
async def run_screening(
    market: str = Query("all", description="市场: all/sh600/sh000/hk/us"),
    limit: int = Query(50, description="返回结果数量上限", le=200),
    min_score: float = Query(0, description="最低评分"),
):
    """Run full Minervini screening scan.

    Downloads data, calculates indicators, detects patterns,
    and returns ranked results.
    """
    try:
        downloader = DataDownloader()
        # This is a placeholder - the full pipeline will be wired
        # when the screening orchestrator is complete
        results = await downloader.screen_all()
        filtered = [r for r in results if r.get("score", 0) >= min_score]
        sorted_results = sorted(filtered, key=lambda x: x.get("score", 0), reverse=True)
        return {
            "total": len(sorted_results),
            "results": sorted_results[:limit],
            "market": market,
        }
    except Exception as e:
        logger.error(f"筛选扫描失败: {e}", exc_info=True)
        return {"error": str(e)}


@router.get("/signals")
async def get_signals(
    signal_type: str = Query("all", description="信号类型: buy/watch/no_entry/all"),
    limit: int = Query(50, le=200),
):
    """Get screening signals from latest scan."""
    try:
        downloader = DataDownloader()
        results = await downloader.screen_all()
        if signal_type != "all":
            results = [r for r in results if r.get("signal") == signal_type]
        return {
            "total": len(results),
            "signals": results[:limit],
        }
    except Exception as e:
        logger.error(f"获取信号失败: {e}", exc_info=True)
        return {"error": str(e)}


@router.get("/market-summary")
async def market_summary():
    """Get overall market summary (breadth, leaders, etc.)."""
    try:
        downloader = DataDownloader()
        summary = await downloader.get_market_summary()
        return summary
    except Exception as e:
        logger.error(f"市场概况获取失败: {e}")
        return {"error": str(e)}


@router.get("/history")
async def scan_history(
    days: int = Query(7, description="查询天数", le=30),
):
    """Get historical scan results."""
    return {
        "days": days,
        "message": "扫描历史功能待实现",
        "records": [],
    }
