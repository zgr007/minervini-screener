"""
Minervini Screener v1.0 - Command Line Scheduler & Task Runner

Usage:
    python scheduler.py init-db              # Initialize database tables
    python scheduler.py migrate              # Run Alembic migrations
    python scheduler.py update-data --market US  # Update market data
    python scheduler.py update-data --market CN  # Update A-share data
    python scheduler.py scan --market US     # Run screening scan
    python scheduler.py scan --market CN     # Run screening scan (A-shares)
    python scheduler.py monitor --market US  # Start live monitoring
    python scheduler.py monitor --market CN  # Start live monitoring (A-shares)
    python scheduler.py backtest --market US --start 2018-01-01 --end 2026-12-31
"""

import argparse
import asyncio
import sys
import pandas as pd
from datetime import datetime
from core.logging_setup import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def cmd_init_db() -> int:
    """Initialize database tables."""
    logger.info("Initializing database...")
    try:
        asyncio.run(_init_db_async())
        print("[OK] Database initialized")
        return 0
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        print(f"[FAIL] Database initialization failed: {e}")
        return 1


async def _init_db_async() -> None:
    """Async helper to initialize database."""
    from data.database import init_db
    await init_db()


def cmd_migrate() -> int:
    """Run Alembic migrations."""
    logger.info("Running database migrations...")
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            logger.error(f"Alembic failed: {result.stderr}")
            print(f"[FAIL] Migrations failed: {result.stderr.strip()}")
            return 1
        print("[OK] Migrations complete")
        return 0
    except Exception as e:
        logger.error(f"Migration error: {e}")
        print(f"✗ Migration error: {e}")
        return 1


def cmd_update_data(market: str) -> int:
    """Update market data for given market."""
    logger.info(f"Updating data for market: {market}")
    try:
        asyncio.run(_update_data_async(market))
        print(f"[OK] Data update complete for {market}")
        return 0
    except Exception as e:
        logger.error(f"Data update failed: {e}", exc_info=True)
        print(f"[FAIL] Data update failed: {e}")
        return 1


async def _update_data_async(market: str) -> dict:
    """Async helper to download market data."""
    from data.downloader import DataDownloader
    downloader = DataDownloader()
    results = await downloader.download_market(market)
    total = sum(v for v in results.values() if v > 0)
    failed = sum(1 for v in results.values() if v < 0)
    logger.info(f"Download complete: {total} rows, {failed} failures")
    return results


def cmd_scan(market: str) -> int:
    """Run screening scan for given market."""
    logger.info(f"Running screening scan for market: {market}")
    try:
        asyncio.run(_scan_async(market))
        print(f"[OK] Screening complete for {market}")
        return 0
    except Exception as e:
        logger.error(f"Screening failed: {e}", exc_info=True)
        print(f"[FAIL] Screening failed: {e}")
        return 1


async def _scan_async(market: str) -> list[dict]:
    """Async helper to run screening, persists results to DB."""
    from data.downloader import DataDownloader
    downloader = DataDownloader()
    results = await downloader.screen_all(market=market)

    # Persist results to DB so dashboard can read them
    await _persist_scan_results_to_db(results)

    buy_signals = [r for r in results if r.get("signal") == "buy"]
    watch_signals = [r for r in results if r.get("signal") == "watch"]

    print(f"\n=== Screening Results: {market} ===")
    print(f"Total analyzed: {len(results)}")
    print(f"Buy signals:     {len(buy_signals)}")
    print(f"Watch signals:   {len(watch_signals)}")

    if buy_signals:
        print("\n--- Buy Signals ---")
        for r in buy_signals[:10]:
            print(f"  {r['code']:10s} {r.get('name',''):30s} Score={r['score']:.1f}  Pattern={r.get('pattern',{}).get('type','n/a')}")

    if watch_signals:
        print("\n--- Watch Signals (Top 10) ---")
        for r in watch_signals[:10]:
            print(f"  {r['code']:10s} {r.get('name',''):30s} Score={r['score']:.1f}  Reason={r.get('reason','')[:60]}")

    return results


async def _persist_scan_results_to_db(results: list[dict]) -> None:
    """Write screen_all() results to the screen_results DB table."""
    from datetime import datetime
    from data.database import async_session_factory, ScreenResult
    from sqlalchemy import delete

    if not results:
        logger.warning("No scan results to persist")
        return

    async with async_session_factory() as session:
        await session.execute(delete(ScreenResult))

        for r in results:
            signal = r.get("signal", "no_entry")
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
        logger.info(f"Persisted {len(results)} scan results to screen_results table")


def cmd_monitor(market: str) -> int:
    """Start live monitoring for given market (continuous)."""
    logger.info(f"Starting monitor for market: {market}")
    try:
        from tasks.worker import TaskWorker
        worker = TaskWorker()
        print(f"[OK] Monitor started for {market}. Press Ctrl+C to stop.")
        asyncio.run(worker.start())
        return 0
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
        print("\n[OK] Monitor stopped")
        return 0
    except Exception as e:
        logger.error(f"Monitor failed: {e}", exc_info=True)
        print(f"[FAIL] Monitor failed: {e}")
        return 1


def cmd_backtest(market: str, start: str, end: str) -> int:
    """Run backtest for given market and date range."""
    logger.info(f"Running backtest: market={market}, start={start}, end={end}")
    try:
        asyncio.run(_backtest_async(market, start, end))
        print(f"[OK] Backtest complete for {market} {start} to {end}")
        return 0
    except Exception as e:
        logger.error(f"Backtest failed: {e}", exc_info=True)
        print(f"[FAIL] Backtest failed: {e}")
        return 1


async def _backtest_async(market: str, start: str, end: str) -> dict:
    """Async helper to run backtest."""
    from data.downloader import DataDownloader
    from backtest.engine import BacktestEngine

    downloader = DataDownloader()
    results = await downloader.screen_all(market=market)

    if not results:
        logger.warning("No screening results for backtest")
        return {}

    # Build data dict from the screening results (signals)
    signals = {}
    for r in results:
        if r.get("signal") in ("buy", "watch"):
            signals[r["code"]] = r

    # Run backtest on signals
    engine = BacktestEngine(
        initial_capital=settings.backtest.default_initial_capital,
        commission_pct=settings.backtest.default_commission_pct,
        slippage_pct=settings.backtest.default_slippage_pct,
    )

    # Load full OHLCV data for each stock with signals
    data = {}
    for code in signals:
        df = await downloader._load_stock_data(code, market)
        if df is not None and not df.empty:
            data[code] = df

    if not data:
        logger.warning("No price data available for backtest")
        return {}

    # Build signal series from screening
    signal_series = {}
    for code, r in signals.items():
        if code in data:
            s = pd.Series(0, index=data[code].index)
            if r.get("signal") == "buy":
                s.iloc[-1] = 1  # Signal at the last date
            signal_series[code] = s

    result = engine.run(data, signal_series, start_date=start, end_date=end)

    # Print summary (result is flat dict from _calculate_results, no nested "metrics" key)
    if "error" in result:
        print(f"\n=== Backtest Error ===")
        print(f"Error: {result['error']}")
        return result

    print(f"\n=== Backtest Results: {market} ({start} ~ {end}) ===")
    print(f"Total Return:   {result.get('total_return_pct', 0):+.2f}%")
    print(f"Max Drawdown:   {result.get('max_drawdown_pct', 0):.2f}%")
    print(f"Win Rate:       {result.get('win_rate_pct', 0):.1f}%")
    print(f"Total Trades:   {result.get('total_trades', 0)}")
    print(f"Sharpe Ratio:   {result.get('sharpe_ratio', 0):.2f}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Minervini Screener v1.0 - Scheduler & Task Runner"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init-db
    subparsers.add_parser("init-db", help="Initialize database tables")

    # migrate
    subparsers.add_parser("migrate", help="Run database migrations")

    # update-data
    update_parser = subparsers.add_parser("update-data", help="Update market data")
    update_parser.add_argument("--market", choices=["US", "CN"], default="US")

    # scan
    scan_parser = subparsers.add_parser("scan", help="Run screening scan")
    scan_parser.add_argument("--market", choices=["US", "CN"], default="US")

    # monitor
    monitor_parser = subparsers.add_parser("monitor", help="Start live monitoring")
    monitor_parser.add_argument("--market", choices=["US", "CN"], default="US")

    # backtest
    backtest_parser = subparsers.add_parser("backtest", help="Run backtest")
    backtest_parser.add_argument("--market", choices=["US", "CN"], default="US")
    backtest_parser.add_argument("--start", default="2018-01-01")
    backtest_parser.add_argument("--end", default="2026-12-31")

    args = parser.parse_args()

    if args.command == "init-db":
        return cmd_init_db()
    elif args.command == "migrate":
        return cmd_migrate()
    elif args.command == "update-data":
        return cmd_update_data(args.market)
    elif args.command == "scan":
        return cmd_scan(args.market)
    elif args.command == "monitor":
        return cmd_monitor(args.market)
    elif args.command == "backtest":
        return cmd_backtest(args.market, args.start, args.end)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
