"""
Minervini Screener v1.0 - Stock Browser API
Search, add, and manage tracked stocks.
"""
import re
import json
import asyncio
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from core.logging_setup import get_logger
from config.loader import settings
from pathlib import Path
import yaml

router = APIRouter(prefix="/api/stock-browser", tags=["stock-browser"])
logger = get_logger(__name__)

from data.stock_names import resolve_name

async def _resolve_name_async(symbol: str, market: str) -> str:
    """Async version of name resolution — wraps yfinance in thread pool."""
    if market == "CN":
        return resolve_name(symbol, market)
    # US stock — use thread pool to avoid blocking the event loop
    from data.stock_names import resolve_name_yf
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, resolve_name_yf, symbol)

# ── Load CN stock list from pre-generated JSON (no live akshare calls) ──
_CN_STOCKS_FILE = Path("data/cn_stocks.json")
_cn_stock_list: list[dict] = []


def _load_cn_stock_list() -> list[dict]:
    """Load A-share stock list from data/cn_stocks.json."""
    if _cn_stock_list:
        return _cn_stock_list
    try:
        if _CN_STOCKS_FILE.exists():
            raw = _CN_STOCKS_FILE.read_text(encoding="utf-8")
            records = json.loads(raw)
            _cn_stock_list.extend(records)
            logger.info(f"已从文件加载A股列表: {len(records)} 只")
        else:
            logger.warning(f"A股列表文件不存在: {_CN_STOCKS_FILE}")
    except Exception as e:
        logger.error(f"加载A股列表失败: {e}")
    return _cn_stock_list


# Load at module import — synchronous file read, no network
_load_cn_stock_list()


# ── Models ──

class AddStockRequest(BaseModel):
    symbol: str
    market: str = "CN"
    name: Optional[str] = None


# ── Search endpoint ──

@router.get("/search")
async def search_stocks(
    q: str = Query("", description="Search keyword (code or name)"),
    market: str = Query("CN", description="Market: US or CN"),
    limit: int = Query(20, description="Max results", le=100),
    local_only: bool = Query(False, description="Only search local DB stocks"),
):
    """Search stocks by code or name."""
    if not q or len(q.strip()) < 1:
        return {"data": []}

    q = q.strip().upper()

    if local_only:
        return await _search_local(q, market, limit)

    if market == "CN":
        return await _search_cn(q, limit)
    elif market == "US":
        return await _search_us(q, limit)
    else:
        raise HTTPException(400, f"Unsupported market: {market}")


async def _search_local(q: str, market: str, limit: int) -> dict:
    """Search only stocks in the local Stock table."""
    from data.database import async_session_factory, Stock
    from sqlalchemy import select, or_

    async with async_session_factory() as session:
        stmt = (
            select(Stock)
            .where(Stock.is_active == True)
            .where(Stock.market == market)
            .where(
                or_(
                    Stock.symbol.ilike(f"{q}%"),
                    Stock.name.ilike(f"%{q}%"),
                )
            )
            .limit(limit)
        )
        result = await session.execute(stmt)
        stocks = list(result.scalars().all())
        return {
            "data": [
                {
                    "code": s.symbol,
                    "name": s.name or s.symbol,
                    "market": s.market,
                    "sector": s.sector or "",
                }
                for s in stocks
            ],
            "total": len(stocks),
        }


async def _search_cn(q: str, limit: int) -> dict:
    """Search CN stocks from pre-loaded list."""
    results = []
    for s in _cn_stock_list:
        if q in s["code"] or q.lower() in s["name"].lower():
            results.append(s)
            if len(results) >= limit:
                break
    # Sort: exact code match first, then code starts with, then name match
    results.sort(key=lambda x: (
        0 if x["code"] == q else
        1 if x["code"].startswith(q) else
        2 if q.lower() in x["name"].lower() else 3
    ))
    return {"data": results[:limit], "total": len(results)}


async def _search_us(q: str, limit: int) -> dict:
    """Search US stocks via yfinance Ticker lookup."""
    results = []
    # Only search if q looks like a ticker symbol
    if re.match(r'^[A-Z]{1,5}$', q):
        try:
            import yfinance as yf
            loop = asyncio.get_running_loop()
            ticker = yf.Ticker(q)
            info = await loop.run_in_executor(None, lambda: ticker.info)
            name = info.get("shortName") or info.get("longName") or ""
            if name and "N/A" not in str(name):
                results.append({
                    "code": q,
                    "name": name.strip(),
                    "market": "US",
                    "sector": (info.get("sector") or "").strip(),
                })
        except Exception as e:
            logger.warning(f"美股代码查询失败 {q}: {e}")
    return {"data": results[:limit], "total": len(results)}


# ── Add / Remove endpoints ──

@router.post("/add")
async def add_stock(req: AddStockRequest):
    """Add a stock to tracking: register in DB, update config, trigger download."""
    symbol = req.symbol.strip().upper()
    market = req.market.upper()
    name = req.name or symbol
    # Auto-resolve name if caller didn't provide one or provided symbol-only
    if not req.name or req.name.strip() == symbol:
        resolved = await _resolve_name_async(symbol, market)
        if resolved and resolved != symbol:
            name = resolved

    if market not in ("US", "CN"):
        raise HTTPException(400, f"Unsupported market: {market}")

    # 1. Register in DB if not exists
    from data.database import async_session_factory, Stock
    from sqlalchemy import select
    async with async_session_factory() as session:
        existing = await session.execute(
            select(Stock).where(Stock.symbol == symbol, Stock.market == market)
        )
        if not existing.scalar_one_or_none():
            stock = Stock(symbol=symbol, name=name, market=market)
            session.add(stock)
            await session.commit()
            logger.info(f"股票已在数据库中注册", symbol=symbol, market=market)

    # 2. Add to config.yaml (non-fatal if fails, run in thread pool to avoid blocking)
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _add_to_config, symbol, market)

    # 3. Trigger data download in background
    asyncio.create_task(_download_and_refresh(symbol, market))

    # 4. Invalidate scan cache
    from web.scan_cache import invalidate_cache
    invalidate_cache()

    return {"data": {"symbol": symbol, "market": market, "status": "added"}}


async def _download_and_refresh(symbol: str, market: str):
    """Download single stock data."""
    from data.downloader import DataDownloader
    downloader = DataDownloader()
    try:
        df = await downloader.download_stock(symbol, force_download=True)
        if df is not None and not df.empty:
            logger.info(f"股票数据已下载", symbol=symbol, rows=len(df))
        else:
            logger.warning(f"股票数据下载后为空", symbol=symbol)
    except Exception as e:
        logger.error(f"股票下载失败", symbol=symbol, error=str(e))


def _add_to_config(symbol: str, market: str):
    """Add ticker to config.yaml if not already present."""
    config_path = Path("config.yaml")
    if hasattr(settings, 'config_path') and settings.config_path:
        config_path = Path(settings.config_path)
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        tickers = config.get("market", {}).get("markets", {}).get(market, {}).get("default_tickers", [])
        if symbol not in tickers:
            tickers.append(symbol)
            config_path.write_text(
                yaml.dump(config, allow_unicode=True, default_flow_style=False),
                encoding="utf-8",
            )
            logger.info(f"已添加到config.yaml", symbol=symbol, market=market)
    except Exception as e:
        logger.warning(f"配置更新失败(非致命): {e}")


@router.delete("/remove/{market}/{symbol}")
async def remove_stock(market: str, symbol: str):
    """Remove a stock from tracking."""
    symbol = symbol.strip().upper()
    market = market.upper()
    if market not in ("US", "CN"):
        raise HTTPException(400, f"Unsupported market: {market}")

    from data.database import async_session_factory, Stock, DailyBar
    from sqlalchemy import delete
    async with async_session_factory() as session:
        await session.execute(delete(DailyBar).where(DailyBar.symbol == symbol, DailyBar.market == market))
        await session.execute(delete(Stock).where(Stock.symbol == symbol, Stock.market == market))
        await session.commit()

    logger.info(f"股票已从数据库移除", symbol=symbol, market=market)
    from web.scan_cache import invalidate_cache
    invalidate_cache()
    return {"data": {"symbol": symbol, "market": market, "status": "removed"}}


@router.post("/backfill-names")
async def backfill_names():
    """Update names for all stocks that have name == symbol (i.e. unresolved)."""
    from data.database import async_session_factory, Stock
    from sqlalchemy import select

    updated = 0
    from data.stock_names import resolve_name_yf
    loop = asyncio.get_running_loop()
    async with async_session_factory() as session:
        result = await session.execute(select(Stock))
        stocks = result.scalars().all()
        for stock in stocks:
            if stock.name and stock.name != stock.symbol:
                continue  # already has a proper name
            if stock.market == "CN":
                real_name = resolve_name(stock.symbol, "CN")
            else:
                real_name = await loop.run_in_executor(None, resolve_name_yf, stock.symbol)
            if real_name and real_name != stock.symbol:
                stock.name = real_name
                updated += 1
        if updated:
            await session.commit()
            logger.info(f"已为{updated}只股票补全名称")

    return {"data": {"updated": updated}}


@router.get("/tracked")
async def list_tracked(market: Optional[str] = Query(None, description="Filter by market")):
    """List all currently tracked stocks."""
    from data.database import async_session_factory, Stock
    from sqlalchemy import select
    async with async_session_factory() as session:
        query = select(Stock)
        if market:
            query = query.where(Stock.market == market.upper())
        query = query.order_by(Stock.market, Stock.symbol)
        result = await session.execute(query)
        stocks = result.scalars().all()
        return {
            "data": [
                {"symbol": s.symbol, "name": s.name or s.symbol, "market": s.market}
                for s in stocks
            ]
        }
