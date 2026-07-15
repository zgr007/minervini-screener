"""
Parallel scanning script — 10-20x faster than screen_all().
Parallelizes Phase 1 (data loading + indicator computation) using asyncio.
Phase 2 (RS rating) remains batch. Phase 3 (SEPA) runs sequentially.

Usage: python scripts/parallel_scan.py
"""
import asyncio
import sys
import os
from datetime import datetime
from typing import Optional

import pandas as pd

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logging_setup import setup_logging, get_logger
from data.database import async_session_factory, Stock, ScreenResult
from data.downloader import DataDownloader
from indicators.ma import calculate_ma
from indicators.atr import calculate_atr
from indicators.volume import calculate_volume_ma
from indicators.bollinger import calculate_bollinger
from core.rs_rating import RSRatingEngine
from core.sepa import run_sepa
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

setup_logging()
logger = get_logger("parallel_scan")


async def load_and_compute(
    downloader: DataDownloader,
    stock: Stock,
    sem: asyncio.Semaphore,
) -> tuple[Optional[str], Optional[pd.DataFrame]]:
    """Load stock data + compute indicators (Phase 1)."""
    async with sem:
        try:
            df = await downloader._load_stock_data(stock.symbol, stock.market)
            if df is None or df.empty:
                return stock.symbol, None
            df = calculate_ma(df)
            df = calculate_atr(df)
            df = calculate_volume_ma(df)
            df = calculate_bollinger(df)
            return stock.symbol, df
        except Exception as e:
            logger.error(f"Failed to load/compute {stock.symbol}: {e}")
            return stock.symbol, None


async def main():
    logger.info("Starting parallel scan...")
    downloader = DataDownloader()

    # --- Load stock list ---
    async with async_session_factory() as session:
        query = select(Stock).where(Stock.market == "CN")
        result = await session.execute(query)
        stocks = result.scalars().all()

    logger.info(f"Loaded {len(stocks)} CN stocks from DB")

    # --- Phase 1: Parallel data loading + indicator computation ---
    sem = asyncio.Semaphore(20)  # 20 concurrent
    tasks = [load_and_compute(downloader, s, sem) for s in stocks]
    results_list = await asyncio.gather(*tasks)

    stock_dfs: dict[str, pd.DataFrame] = {}
    for symbol, df in results_list:
        if df is not None:
            stock_dfs[symbol] = df

    logger.info(f"Phase 1 complete: {len(stock_dfs)}/{len(stocks)} stocks have data")

    # --- Phase 2: Batch RS rating ---
    rs_engine = RSRatingEngine()
    rs_results = rs_engine.compute_batch(stock_dfs)
    logger.info(f"Phase 2 complete: RS ratings computed for {len(rs_results)} stocks")

    # --- Phase 3: SEPA analysis per stock (sequential, fast) ---
    stock_map = {s.symbol: s for s in stocks}
    sepa_results: list[dict] = []

    for symbol, df in stock_dfs.items():
        try:
            stock = stock_map.get(symbol)
            rs = rs_results.get(symbol, {})
            strategy_result = run_sepa(
                df=df,
                code=symbol,
                name=stock.name if stock else "",
                check_breakout=True,
                rs_result=rs,
            )
            sepa_results.append({
                "code": symbol,
                "name": stock.name if stock else "",
                "market": "CN",
                "signal": strategy_result.signal,
                "score": strategy_result.score,
                "stage2": strategy_result.stage2,
                "rs_rating": strategy_result.rs_rating_val,
                "rs_rank": strategy_result.rs_rank,
                "pattern": strategy_result.pattern,
                "breakout": strategy_result.breakout,
                "stop_loss": strategy_result.stop_loss,
                "reason": strategy_result.reason,
                "current_price": strategy_result.data.get("current_price", 0),
            })
        except Exception as e:
            logger.error(f"SEPA failed for {symbol}: {e}")
            continue

    sepa_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    logger.info(f"Phase 3 complete: {len(sepa_results)} stocks analyzed")

    # --- Persist to DB ---
    async with async_session_factory() as session:
        await session.execute(delete(ScreenResult))
        for r in sepa_results:
            signal = r.get("signal", "no_entry")
            entry = ScreenResult(
                run_date=datetime.now(),
                market="CN",
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

    # Print summary
    buy_signals = [r for r in sepa_results if r.get("signal") == "buy"]
    watch_signals = [r for r in sepa_results if r.get("signal") == "watch"]
    print(f"\n=== Parallel Scan Complete ===")
    print(f"Total analyzed: {len(sepa_results)}")
    print(f"Buy signals:     {len(buy_signals)}")
    print(f"Watch signals:   {len(watch_signals)}")
    print(f"DB persisted:    {len(sepa_results)} rows in screen_results")

    if buy_signals:
        print("\n--- Buy Signals (Top 10) ---")
        for r in buy_signals[:10]:
            pattern_type = r.get("pattern", {}).get("type", "n/a") if r.get("pattern") else "n/a"
            print(f"  {r['code']:10s} {r.get('name',''):30s} Score={r['score']:.1f}  Pattern={pattern_type}")

    if watch_signals:
        print("\n--- Watch Signals (Top 10) ---")
        for r in watch_signals[:10]:
            print(f"  {r['code']:10s} {r.get('name',''):30s} Score={r['score']:.1f}  Reason={r.get('reason','')[:60]}")

    logger.info(f"Parallel scan complete: {len(buy_signals)} buy, {len(watch_signals)} watch, {len(sepa_results)} total")


if __name__ == "__main__":
    asyncio.run(main())
