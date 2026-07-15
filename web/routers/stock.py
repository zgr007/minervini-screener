"""
Minervini Screener v1.0 - Stock Detail API
Single stock analysis and chart data.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query

from config.loader import settings
from core.logging_setup import get_logger
from core.sepa import run_sepa
from data.downloader import DataDownloader

router = APIRouter(prefix="/api/stock", tags=["stock"])
logger = get_logger(__name__)


def _is_data_stale(df) -> bool:
    """Check if the latest bar in the DataFrame is from before today."""
    try:
        last_date = df.index[-1] if hasattr(df.index, '__getitem__') else None
        if last_date is None:
            return True
        last_str = str(last_date.date()) if hasattr(last_date, 'date') else str(last_date)[:10]
        today_str = datetime.now().strftime("%Y-%m-%d")
        return last_str < today_str
    except Exception:
        return True


def _ensure_date_index(df):
    """Ensure DataFrame has trade_date as its index (not a column)."""
    if df is None or df.empty:
        return df
    if "trade_date" in df.columns:
        return df.set_index("trade_date")
    return df


async def _load_fresh_data(downloader: DataDownloader, code: str, refresh: bool, market: str = None):
    """Load data, auto-refreshing if stale."""
    df = await downloader.download_stock(code, force_download=refresh)
    df = _ensure_date_index(df)
    if df is not None and not df.empty:
        if not refresh and _is_data_stale(df):
            logger.info(f"[{code}] 数据过期，正在从源刷新...")
            df = await downloader.download_stock(code, force_download=True)
            df = _ensure_date_index(df)
    else:
        df = await downloader.download_stock(code, force_download=True)
        df = _ensure_date_index(df)
    return df


@router.get("/{code}")
async def stock_detail(
    code: str,
    refresh: bool = Query(False, description="强制刷新数据"),
):
    """Get full Minervini analysis for a single stock."""
    try:
        downloader = DataDownloader()
        df = await _load_fresh_data(downloader, code, refresh)
        if df is None or df.empty:
            return {"error": f"无法获取{code}data"}

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
    """Get OHLCV price data for charting.
    Auto-refreshes if cached data is not from today.
    """
    try:
        downloader = DataDownloader()
        df = await _load_fresh_data(downloader, code, refresh)

        if df is None or df.empty:
            return {"error": f"无法获取{code}数据"}

        recent = df.tail(min(days, len(df)))
        # Build dict with YYYY-MM-DD date keys (not ISO datetime strings)
        price_data = {}
        for idx, row in recent.iterrows():
            date_str = str(idx.date()) if hasattr(idx, "date") else str(idx)[:10]
            price_data[date_str] = {
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row["volume"],
            }

        return {
            "code": code,
            "count": len(price_data),
            "prices": price_data,
        }
    except Exception as e:
        logger.error(f"[{code}] 价格获取失败: {e}")
        return {"error": str(e)}
