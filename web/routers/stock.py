"""
Minervini Screener v1.0 - Stock Detail API
Single stock analysis and chart data.
"""
from typing import Optional
from fastapi import APIRouter, Query

from config.loader import settings
from core.logging_setup import get_logger
from core.sepa import run_sepa
from data.downloader import DataDownloader

router = APIRouter(prefix="/api/stock", tags=["stock"])
logger = get_logger(__name__)


@router.get("/{code}")
async def stock_detail(
    code: str,
    refresh: bool = Query(False, description="强制刷新数据"),
):
    """Get full Minervini analysis for a single stock."""
    try:
        downloader = DataDownloader()
        df = await downloader.download_stock(code, force_download=refresh)
        if df is None or df.empty:
            return {"error": f"无法获取{code}数据"}

        result = run_sepa(df, code)
        return {
            "code": code,
            "signal": result.signal,
            "score": result.score,
            "stage2": result.stage2,
            "rs_rating": result.rs_rating_val,
            "rs_rank": result.rs_rank,
            "pattern": result.pattern,
            "breakout": result.breakout,
            "stop_loss": result.stop_loss,
            "reason": result.reason,
            "current_price": result.data.get("current_price"),
        }
    except Exception as e:
        logger.error(f"[{code}] 分析失败: {e}", exc_info=True)
        return {"error": str(e)}


@router.get("/{code}/indicators")
async def stock_indicators(
    code: str,
    refresh: bool = Query(False),
):
    """Get all calculated indicators for a stock."""
    try:
        downloader = DataDownloader()
        df = await downloader.download_stock(code, force_download=refresh)
        if df is None or df.empty:
            return {"error": f"无法获取{code}数据"}

        # Return last 5 rows of key indicators
        cols = [c for c in df.columns if c not in ["open", "high", "low", "volume"]]
        recent = df[cols].tail(5)

        return {
            "code": code,
            "indicators": recent.to_dict(orient="records"),
        }
    except Exception as e:
        logger.error(f"[{code}] 指标获取失败: {e}")
        return {"error": str(e)}


@router.get("/{code}/price")
async def stock_price(
    code: str,
    days: int = Query(100, le=500, description="返回天数"),
    refresh: bool = Query(False),
):
    """Get OHLCV price data for charting."""
    try:
        downloader = DataDownloader()
        df = await downloader.download_stock(code, force_download=refresh)
        if df is None or df.empty:
            return {"error": f"无法获取{code}数据"}

        recent = df.tail(min(days, len(df)))
        price_data = recent[["open", "high", "low", "close", "volume"]].to_dict(orient="index")

        return {
            "code": code,
            "count": len(price_data),
            "prices": price_data,
        }
    except Exception as e:
        logger.error(f"[{code}] 价格获取失败: {e}")
        return {"error": str(e)}
