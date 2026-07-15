"""
Minervini Screener v1.0 - API Endpoints (Frontend-facing)
Routes that match what the frontend expects, backed by real scan data.
"""
import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from core.logging_setup import get_logger
from web.scan_cache import get_scan_results

router = APIRouter(prefix="/api", tags=["stubs"])
logger = get_logger(__name__)


def _transform_screen_result(r: dict) -> dict:
    """Transform backend screen_all() dict to frontend ScreenResult shape."""
    signal = r.get("signal", "no_entry")
    stage2 = r.get("stage2", False)
    rs_rating = r.get("rs_rating", 0) or 0
    pattern = r.get("pattern") or {}
    pattern_detected = bool(pattern and pattern.get("detected"))
    score = r.get("score", 0) or 0

    rs_min = 80  # typical RS min threshold
    rs_passed = rs_rating >= rs_min and stage2
    reason_text = r.get("reason", "")

    return {
        "symbol": r.get("code", ""),
        "name": r.get("name", ""),
        "run_date": datetime.now().strftime("%Y-%m-%d"),
        "trend_passed": stage2,
        "rs_passed": rs_passed,
        "rs_rating": rs_rating,
        "signal": signal,
        "total_score": score,
        "pattern_type": pattern.get("type") if pattern_detected else None,
        "is_selected": signal == "buy",
        "reason": {
            "stage2": {"passed": stage2, "score": 1 if stage2 else 0, "reason": "Stage 2 uptrend" if stage2 else "Not in Stage 2"},
            "rs": {"passed": rs_passed, "score": rs_rating, "reason": reason_text[:100] if not stage2 else f"RS {rs_rating}"},
            "fundamental": {"passed": False, "score": 0, "reason": "No fundamental data"},
            "institutional": {"passed": False, "score": 0, "reason": "No institutional data"},
        },
    }


@router.get("/dashboard")
async def dashboard():
    """Dashboard summary data from real scan results."""
    try:
        results = await get_scan_results()
    except Exception as e:
        logger.error(f"仪表板扫描失败: {e}")
        return {
            "data": {
                "market_phase": "unknown",
                "total_stocks_scanned": 0,
                "stage2_passed": 0,
                "rs_passed": 0,
                "fundamental_passed": 0,
                "patterns_found": 0,
                "near_pivot": 0,
            }
        }

    stage2_count = sum(1 for r in results if r.get("stage2"))
    rs_passed = sum(1 for r in results if (r.get("rs_rating") or 0) >= 80 and r.get("stage2"))
    patterns = sum(1 for r in results if r.get("pattern") and r["pattern"].get("detected"))
    buy_signals = sum(1 for r in results if r.get("signal") == "buy")
    watch_signals = sum(1 for r in results if r.get("signal") == "watch")

    return {
        "data": {
            "market_phase": "bull",
            "total_stocks_scanned": len(results),
            "stage2_passed": stage2_count,
            "rs_passed": rs_passed,
            "fundamental_passed": 0,
            "patterns_found": patterns,
            "near_pivot": watch_signals,
        }
    }


@router.get("/data/status")
async def data_status():
    """Data update status — queries DB for latest dates per market."""
    from data.downloader import DataDownloader
    try:
        downloader = DataDownloader()
        us_status = await downloader.get_data_status("US")
        cn_status = await downloader.get_data_status("CN")
        return {
            "data": {
                "last_update": {
                    "US": us_status.get("latest_date"),
                    "CN": cn_status.get("latest_date"),
                },
                "has_data": {
                    "US": us_status.get("has_data", False),
                    "CN": cn_status.get("has_data", False),
                },
                "stock_counts": {
                    "US": await _get_stock_count("US"),
                    "CN": await _get_stock_count("CN"),
                },
            }
        }
    except Exception as e:
        logger.error(f"数据状态获取失败: {e}")
        return {"data": {"last_update": {}, "has_data": {}, "stock_counts": {}}}


async def _get_stock_count(market: str) -> int:
    """Count stocks in a market."""
    from data.database import async_session_factory, Stock
    from sqlalchemy import select, func
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(func.count()).select_from(Stock).where(Stock.market == market)
            )
            return result.scalar() or 0
    except Exception:
        return 0


class DataUpdateRequest(BaseModel):
    market: str = "US"


@router.post("/data/update")
async def data_update(req: DataUpdateRequest):
    """Trigger data update for a market — runs in background task."""
    from web.scan_cache import invalidate_cache
    from web.task_manager import create_task, start_task, complete_task

    market = req.market.upper()
    if market not in ("US", "CN"):
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")

    task_id = create_task()

    # Run download in background
    import asyncio
    asyncio.create_task(_run_data_download(task_id, market))

    return {
        "data": {
            "task_id": task_id,
            "market": market,
            "status": "started",
        }
    }


async def _run_data_download(task_id: str, market: str):
    """Run data download and update task status."""
    from web.task_manager import start_task, complete_task
    from data.downloader import DataDownloader

    start_task(task_id)
    try:
        downloader = DataDownloader()
        result = await downloader.download_market(market)
        from web.scan_cache import invalidate_cache
        invalidate_cache()
        complete_task(task_id)
        logger.info(f"数据下载完成", market=market, task_id=task_id, result=result)
    except Exception as e:
        logger.error(f"数据下载失败", market=market, task_id=task_id, error=str(e))
        complete_task(task_id, error=str(e))


@router.get("/data/update/{task_id}")
async def data_update_status(task_id: str):
    """Poll task status for a running data update."""
    from web.task_manager import get_task
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"data": task}


@router.get("/screen/results")
async def screen_results():
    """Get latest screening results from real scan."""
    try:
        results = await get_scan_results()
    except Exception as e:
        logger.error(f"筛选结果获取失败: {e}")
        return {"data": []}

    transformed = [_transform_screen_result(r) for r in results]
    return {"data": transformed}


@router.post("/screen/run")
async def screen_run():
    """Run screening scan as a background asyncio task.
    Returns immediately with a run_id for progress polling."""
    from web.scan_progress import get_progress, is_running

    if is_running():
        return {"data": get_progress(), "message": "Scan already running"}

    run_id = datetime.now().strftime("%Y%m%d%H%M%S")

    # Launch scan in background asyncio task (not subprocess)
    import asyncio
    asyncio.create_task(_run_scan_background(run_id))

    return {
        "data": {
            "run_id": run_id,
            "status": "started",
            "message": "Scan started in background",
        }
    }


async def _run_scan_background(run_id: str):
    """Run the full scan pipeline with progress tracking."""
    from web.scan_progress import create_run, update_progress, complete_run
    from data.downloader import DataDownloader
    from web.scan_cache import invalidate_cache
    from scheduler import _persist_scan_results_to_db
    import os

    try:
        # Count stocks first for progress total
        from data.database import async_session_factory, Stock
        from sqlalchemy import select, func

        async with async_session_factory() as session:
            count_result = await session.execute(
                select(func.count()).select_from(Stock).where(Stock.market == "CN")
            )
            total_stocks = count_result.scalar() or 0

        create_run(run_id, total=total_stocks)

        async def callback(processed, total, phase, phase_label, message):
            update_progress(processed, total, phase, phase_label, message)

        downloader = DataDownloader()
        results = await downloader.screen_all(market="CN", progress_callback=callback)

        if results:
            await _persist_scan_results_to_db(results)

        invalidate_cache()
        complete_run("completed")
        logger.info(f"后台扫描完成: {len(results)} 条结果")

    except Exception as e:
        logger.error(f"后台扫描失败: {e}", exc_info=True)
        complete_run("failed", str(e))


@router.get("/screen/run/progress")
async def screen_run_progress():
    """Get current scan progress for progress bar polling."""
    from web.scan_progress import get_progress
    return {"data": get_progress()}


async def _persist_scan_results(run_id: str, results: list[dict]) -> None:
    """Write screen_all() results to the screen_results DB table."""
    from data.database import async_session_factory, ScreenResult
    from sqlalchemy import delete

    if not results:
        logger.warning("无扫描结果需要保存")
        return

    async with async_session_factory() as session:
        # Clear old results for this run
        await session.execute(delete(ScreenResult))

        for r in results:
            signal = r.get("signal", "no_entry")
            # Determine if the stock should carry existing scan data as a fresh entry:
            entry = ScreenResult(
                run_date=datetime.now(),
                market=r.get("market", "CN"),
                symbol=r.get("code", ""),
                name=r.get("name", ""),
                price=r.get("current_price") or 0,
                trend_passed=r.get("stage2", False),
                rs_passed=(r.get("rs_rating") or 0) >= 80 and r.get("stage2", False),
                rs_percentile=r.get("rs_rating") or 0,
                total_score=r.get("score") or 0,
                selected=(signal == "buy"),
                reason=str(r.get("reason", ""))[:500],
            )
            session.add(entry)

        await session.commit()
        logger.info(f"已将{len(results)}条扫描结果保存到screen_results表")


@router.get("/watchlist")
async def watchlist():
    """Get watchlist."""
    return {"data": []}


@router.post("/watchlist")
async def watchlist_add():
    """Add to watchlist."""
    return {"data": {"id": 0, "symbol": "", "note": ""}}


@router.patch("/watchlist/{item_id}")
async def watchlist_update(item_id: int):
    """Update watchlist item."""
    return {"data": {"id": item_id}}


@router.delete("/watchlist/{item_id}")
async def watchlist_delete(item_id: int):
    """Delete watchlist item."""
    return {"data": {"ok": True}}


@router.get("/signals/check")
async def signals_check():
    """Check signals for symbols from latest scan."""
    return await _signals_today_impl()


@router.get("/signals/today")
async def signals_today():
    """Get today's signals from real scan."""
    return await _signals_today_impl()


async def _signals_today_impl():
    """Shared impl: return buy/watch signals as frontend Signal[]."""
    try:
        results = await get_scan_results()
    except Exception as e:
        logger.error(f"信号获取失败: {e}")
        return {"data": []}

    signals = []
    for r in results:
        signal = r.get("signal", "no_entry")
        if signal not in ("buy", "watch"):
            continue
        pattern = r.get("pattern") or {}
        price = r.get("current_price", 0)
        if not price:
            price = (pattern.get("buy_point") or pattern.get("pivot_price") or 0)
        rs_rating = r.get("rs_rating", 0)
        signals.append({
            "id": 0,
            "symbol": r.get("code", ""),
            "name": r.get("name", ""),
            "signal_time": datetime.now().isoformat(),
            "signal_type": "BUY" if signal == "buy" else "WATCH",
            "direction": "ENTER",
            "price": float(price),
            "volume_confirmed": False,
            "market_confirmed": False,
            "risk_confirmed": False,
            "reason": r.get("reason", "")[:200] if rs_rating else r.get("reason", "")[:200],
            "status": "pending",
        })
    return {"data": signals}


@router.post("/orders/preview")
async def order_preview():
    """Preview an order."""
    return {"data": {"symbol": "", "side": "buy", "estimated_price": 0}}


@router.post("/orders/simulate")
async def order_simulate():
    """Simulate an order."""
    return {"data": {"order_id": 0, "status": "simulated"}}


@router.post("/orders/confirm")
async def order_confirm():
    """Confirm an order."""
    return {"data": {"order_id": 0, "status": "confirmed"}}


@router.get("/notify/test")
async def notify_test():
    """Test notification."""
    return {"data": {"sent": True}}


@router.get("/reports/daily")
async def daily_report():
    """Get daily AI report."""
    return {"data": None}


@router.get("/risk/portfolio")
async def risk_portfolio():
    """Portfolio risk metrics."""
    return {
        "data": {
            "total_exposure": 0,
            "market_phase": "bull",
            "var": 0,
            "concentration": {},
        }
    }


@router.get("/risk/market")
async def risk_market():
    """Market phase / risk."""
    return {"data": {"phase": "bull", "reason": "Market in uptrend"}}


@router.get("/stocks/{symbol}")
async def stock_stub(symbol: str):
    """Stock detail — proxies to real /api/stock/{code}."""
    try:
        from core.sepa import run_sepa
        from data.downloader import DataDownloader
        downloader = DataDownloader()
        df = await downloader.download_stock(symbol, force_download=False)
        if df is None or df.empty:
            return {"data": None, "code": symbol, "error": f"No data for {symbol}"}

        result = run_sepa(df, symbol)
        pattern = result.pattern
        pattern_detected = bool(pattern and pattern.get("detected"))
        return {
            "data": {
                "code": symbol,
                "signal": result.signal,
                "score": result.score,
                "stage2": result.stage2,
                "rs_rating": result.rs_rating_val,
                "pattern": (pattern or {}).get("type") if pattern_detected else None,
                "pattern_detail": pattern,
                "breakout": result.breakout,
                "stop_loss": result.stop_loss,
                "reason": result.reason,
                "current_price": result.data.get("current_price"),
            }
        }
    except Exception as e:
        logger.error(f"[{symbol}] 股票详情获取失败: {e}")
        return {"data": None, "code": symbol, "error": str(e)}


@router.get("/stocks/{symbol}/patterns")
async def stock_patterns_stub(symbol: str):
    """Stock patterns — run full analysis for this symbol."""
    try:
        from core.sepa import run_sepa
        from data.downloader import DataDownloader
        downloader = DataDownloader()
        df = await downloader.download_stock(symbol, force_download=False)
        if df is None or df.empty:
            return {"data": [], "code": symbol}

        result = run_sepa(df, symbol)
        pattern = result.pattern
        if pattern and pattern.get("detected"):
            return {"data": [{
                "symbol": symbol,
                "detected_date": datetime.now().strftime("%Y-%m-%d"),
                "pattern_type": pattern.get("type", "").upper(),
                "pivot_price": pattern.get("buy_point") or pattern.get("pivot_price"),
                "pattern_low": pattern.get("low") or pattern.get("first_bottom"),
                "stop_price": pattern.get("stop_price") or result.stop_loss.get("stop_price") if result.stop_loss else None,
                "target_price": pattern.get("target_price"),
                "confidence": {"high": 3, "medium": 2, "low": 1}.get(pattern.get("confidence"), 0),
                "status": "active",
                "details": pattern,
            }], "code": symbol}
        return {"data": [], "code": symbol}
    except Exception as e:
        logger.error(f"[{symbol}] 形态分析失败: {e}")
        return {"data": [], "code": symbol}


@router.get("/stocks/{symbol}/price")
async def stock_price_stub(symbol: str):
    """Stock price — query from DB."""
    try:
        from data.downloader import DataDownloader
        downloader = DataDownloader()
        df = await downloader.download_stock(symbol, force_download=False)
        if df is None or df.empty:
            return {"data": {"prices": []}, "code": symbol}

        recent = df.tail(200)
        if "adjusted_close" in recent.columns:
            price_col = "adjusted_close"
        else:
            price_col = "close"

        prices = []
        for idx, row in recent.iterrows():
            prices.append({
                "date": str(idx.date()) if hasattr(idx, "date") else str(idx),
                "open": float(row.get("open", 0)),
                "high": float(row.get("high", 0)),
                "low": float(row.get("low", 0)),
                "close": float(row.get(price_col, row.get("close", 0))),
                "volume": int(row.get("volume", 0)),
            })
        return {"data": {"prices": prices}, "code": symbol}
    except Exception as e:
        logger.error(f"[{symbol}] 价格获取失败: {e}")
        return {"data": {"prices": []}, "code": symbol}


@router.get("/stocks/{symbol}/indicators")
async def stock_indicators_stub(symbol: str):
    """Stock indicators — from DB."""
    try:
        from indicators.ma import calculate_ma
        from indicators.atr import calculate_atr
        from indicators.volume import calculate_volume_ma
        from data.downloader import DataDownloader
        downloader = DataDownloader()
        df = await downloader.download_stock(symbol, force_download=False)
        if df is None or df.empty:
            return {"data": [], "code": symbol}

        df = calculate_ma(df)
        df = calculate_atr(df)
        df = calculate_volume_ma(df)

        cols = [c for c in df.columns if c not in ("open", "high", "low", "volume")]
        recent = df[cols].tail(5)
        indicators = recent.to_dict(orient="records")
        # Convert numpy types
        for row in indicators:
            for k, v in row.items():
                if hasattr(v, "item"):
                    row[k] = v.item()
        return {"data": indicators, "code": symbol}
    except Exception as e:
        logger.error(f"[{symbol}] 指标获取失败: {e}")
        return {"data": [], "code": symbol}


@router.get("/positions")
async def positions_stub():
    """Stub for positions (real: /api/portfolio/)."""
    return {"data": []}


class BacktestRunRequest(BaseModel):
    market: str = "US"
    start_date: str = "2024-01-01"
    end_date: str = ""
    initial_capital: float = 100000.0
    commission_pct: float = 0.001
    slippage_pct: float = 0.001
    max_positions: int = 10
    symbols: Optional[list[str]] = None


_backtest_history: list = []  # ordered newest-first


@router.get("/backtests")
async def backtests_list():
    """Return backtest history (newest first)."""
    return {"data": _backtest_history}


@router.post("/backtests/run")
async def backtests_run(req: BacktestRunRequest):
    """Run a full SEPA backtest."""
    global _backtest_history
    from core.backtest import SEPABacktest

    engine = SEPABacktest(
        market=req.market,
        start_date=req.start_date,
        end_date=req.end_date,
        initial_capital=req.initial_capital,
        commission_pct=req.commission_pct,
        slippage_pct=req.slippage_pct,
        max_positions=req.max_positions,
        symbols=req.symbols,
    )
    result = await engine.run()

    # Wrap in ApiResponse format for frontend
    payload = {
        "id": datetime.now().strftime("BT-%Y%m%d%H%M%S"),
        "config": result["config"],
        "metrics": result["metrics"],
        "equity_curve": result["equity_curve"],
        "trades": result["trades"],
        "created_at": datetime.now().isoformat(),
    }
    _backtest_history.insert(0, payload)
    if len(_backtest_history) > 20:
        _backtest_history.pop()
    return {"data": payload}



