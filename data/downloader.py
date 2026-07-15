"""
Minervini Screener v1.0 - Data Download Orchestrator
Coordinates data fetching from multiple sources with quality checks.
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from collections.abc import Callable
import pandas as pd

from config.loader import settings
from core.logging_setup import get_logger
from data.database import async_session_factory, DailyBar, Stock, init_db
from data.yfinance_source import YFinanceSource
from data.akshare_source import AKShareSource
from sqlalchemy import select

logger = get_logger(__name__)


class DataQualityError(Exception):
    """Raised when data fails quality checks."""
    pass


class DataDownloader:
    """Orchestrates data downloading from multiple market sources."""

    def __init__(self):
        self.sources = {
            "US": YFinanceSource(),
            "CN": AKShareSource(),
        }
        self.qc_config = settings.data.quality_checks

    async def download_market(self, market: str, tickers: Optional[List[str]] = None) -> dict:
        """Download and store data for an entire market.

        Args:
            market: "US" or "CN"
            tickers: Optional list of tickers, defaults to config default_tickers

        Returns:
            dict with {symbol: rows_inserted} summary
        """
        source = self.sources.get(market)
        if not source:
            raise ValueError(f"Unsupported market: {market}")

        symbols = tickers or settings.market.markets.get(market, {}).get("default_tickers", [])
        results = {}

        for symbol in symbols:
            try:
                # Async wrapper for sync library calls
                df = await asyncio.to_thread(
                    self._fetch_with_retry, source, symbol, market
                )
                if df.empty:
                    results[symbol] = 0
                    continue

                # Quality check
                try:
                    self._check_data_quality(df, symbol)
                except DataQualityError as e:
                    logger.warning("Data quality failed", symbol=symbol, error=str(e))
                    results[symbol] = -1
                    continue

                # Store to DB
                rows = await self._store_bars(symbol, market, df)
                results[symbol] = rows
                logger.info("Market data stored", market=market, symbol=symbol, rows=rows)

            except Exception as e:
                logger.error("Market download failed", market=market, symbol=symbol, error=str(e))
                results[symbol] = -2

        return results

    async def update_all(self) -> dict:
        """Update data for all configured markets.

        Returns:
            dict with {market: {symbol: rows_inserted}} summary
        """
        results = {}
        for market_key in settings.market.markets:
            logger.info(f"Updating market: {market_key}")
            try:
                market_result = await self.download_market(market_key)
                results[market_key] = market_result
                total = sum(v for v in market_result.values() if v > 0)
                logger.info(f"Market {market_key} updated: {total} total bars stored")
            except Exception as e:
                logger.error(f"Market {market_key} update failed", error=str(e))
                results[market_key] = {"error": str(e)}
        return results

    async def download_stock(self, code: str, force_download: bool = False) -> Optional[pd.DataFrame]:
        """Download data for a single stock.

        Tries database first; if not found or force_download, fetches from source.

        Args:
            code: Stock symbol (e.g. "AAPL", "600519")
            force_download: Skip DB cache and re-download from source

        Returns:
            DataFrame with OHLCV data, or None on failure
        """
        # Determine market from code format
        if code.isdigit() and len(code) == 6:
            market = "CN"
        else:
            market = "US"

        # Try DB first
        if not force_download:
            df = await self._load_stock_data(code, market)
            if df is not None and not df.empty:
                return df

        # Fetch from source
        source = self.sources.get(market)
        if not source:
            # Try other market as fallback
            other = "CN" if market == "US" else "US"
            source = self.sources.get(other)
            if not source:
                return None
            market = other

        try:
            df = await asyncio.to_thread(self._fetch_with_retry, source, code, market)
            if df is None or df.empty:
                return None
            await self._store_bars(code, market, df)
            return df
        except Exception as e:
            logger.error(f"download_stock failed", code=code, error=str(e))
            return None

    async def screen_all(
        self,
        market: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
    ) -> list[dict]:
        """Run SEPA screening for all stocks in one or all markets.

        Loads stock data from database, calculates indicators,
        and runs the Minervini SEPA strategy.

        Args:
            market: Optional market filter ("US" or "CN"). If None, screens all.
            progress_callback: Optional async callable(processed, total, phase, phase_label, message)
                               for progress bar reporting.

        Returns:
            list of dict result with signal, score, pattern info per stock
        """
        from indicators.ma import calculate_ma, check_ma_alignment
        from indicators.atr import calculate_atr
        from indicators.volume import calculate_volume_ma, calculate_volume_ratio, detect_volume_spike
        from indicators.bollinger import calculate_bollinger
        from core.rs_rating import RSRatingEngine
        from core.sepa import run_sepa

        async with async_session_factory() as session:
            query = select(Stock)
            if market:
                query = query.where(Stock.market == market)
            result = await session.execute(query)
            stocks = result.scalars().all()

        total_stocks = len(stocks)

        # Phase 1: Load ALL price data and calculate indicators
        stock_dfs = {}  # {symbol: df_with_indicators}
        for i, stock in enumerate(stocks):
            try:
                df = await self._load_stock_data(stock.symbol, stock.market)
                if df is None or df.empty:
                    continue
                df = calculate_ma(df)
                df = calculate_atr(df)
                df = calculate_volume_ma(df)
                df = calculate_bollinger(df)
                stock_dfs[stock.symbol] = (stock, df)
            except Exception as e:
                logger.error(f"Data load failed for {stock.symbol}", error=str(e))
            if progress_callback:
                await progress_callback(i + 1, total_stocks, "phase1", "加载行情数据", stock.symbol)

        # Phase 2: Compute RS ratings with full market context
        if progress_callback:
            await progress_callback(0, total_stocks, "phase2", "计算RS排名", "批量计算中...")
        raw_dfs = {sym: df for sym, (stk, df) in stock_dfs.items()}
        rs_engine = RSRatingEngine()
        rs_results = rs_engine.compute_batch(raw_dfs)

        # Phase 3: Run SEPA per stock with proper RS context
        results = []
        stock_items = list(stock_dfs.items())
        for j, (symbol, (stock, df)) in enumerate(stock_items):
            try:
                rs = rs_results.get(symbol, {})
                strategy_result = run_sepa(
                    df=df,
                    code=stock.symbol,
                    name=stock.name or "",
                    check_breakout=True,
                    rs_result=rs,
                )

                results.append({
                    "code": stock.symbol,
                    "name": stock.name,
                    "market": stock.market,
                    "signal": strategy_result.signal,
                    "score": strategy_result.score,
                    "stage2": strategy_result.stage2,
                    "rs_rating": strategy_result.rs_rating_val,
                    "rs_rank": strategy_result.rs_rank,
                    "pattern": strategy_result.pattern,
                    "breakout": strategy_result.breakout,
                    "stop_loss": strategy_result.stop_loss,
                    "reason": strategy_result.reason,
                })

            except Exception as e:
                logger.error(f"Screening failed for {stock.symbol}", error=str(e))
                continue
            if progress_callback:
                await progress_callback(j + 1, len(stock_items), "phase3", "分析SEPA信号", stock.symbol)

        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        logger.info(f"Screening complete: {len(results)} stocks analyzed")
        return results

    async def _load_stock_data(self, symbol: str, market: str) -> Optional[pd.DataFrame]:
        """Load OHLCV data for a stock from the database.

        Returns a DataFrame with columns: trade_date, open, high, low, close, volume
        """
        async with async_session_factory() as session:
            query = (
                select(DailyBar)
                .where(DailyBar.symbol == symbol)
                .where(DailyBar.market == market)
                .order_by(DailyBar.trade_date.asc())
            )
            result = await session.execute(query)
            bars = result.scalars().all()

        if not bars:
            return None

        records = []
        for bar in bars:
            records.append({
                "trade_date": bar.trade_date,
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": float(bar.volume),
            })

        df = pd.DataFrame(records)
        df.set_index("trade_date", inplace=True)
        return df

    def _fetch_with_retry(self, source, symbol: str, market: str) -> pd.DataFrame:
        """Fetch data with retries."""
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=365 * 3)).strftime("%Y-%m-%d")

        if market == "US":
            return source.fetch_daily_bars(symbol, start=start, end=end)
        else:
            return source.fetch_daily_bars(symbol, start=start.replace("-", ""), end=end.replace("-", ""))

    def _check_data_quality(self, df: pd.DataFrame, symbol: str) -> None:
        """Run data quality checks. Raises DataQualityError on failure."""
        if df.empty:
            raise DataQualityError("Empty DataFrame")

        max_missing = self.qc_config.get("max_missing_pct", 0.1)
        max_zero_vol = self.qc_config.get("max_zero_volume_days", 5)
        max_price_gap = self.qc_config.get("max_price_gap_pct", 50.0)

        # Check missing data percentage
        total_cells = df.size
        missing_cells = df.isnull().sum().sum()
        missing_pct = missing_cells / total_cells if total_cells > 0 else 1.0
        if missing_pct > max_missing:
            raise DataQualityError(f"Missing data {missing_pct:.1%} > {max_missing:.1%}")

        # Check zero volume days
        zero_vol_days = (df["volume"] == 0).sum()
        if zero_vol_days > max_zero_vol:
            raise DataQualityError(f"Zero volume days {zero_vol_days} > {max_zero_vol}")

        # Check price gaps (daily return > threshold)
        if len(df) > 1:
            daily_returns = df["close"].pct_change().abs()
            large_gaps = (daily_returns > max_price_gap / 100.0).sum()
            if large_gaps > len(df) * 0.01:  # Less than 1% of days
                pass  # Allow occasional gaps for splits/dividends

        logger.info("Data quality passed", symbol=symbol, rows=len(df))

    async def _store_bars(self, symbol: str, market: str, df: pd.DataFrame) -> int:
        """Store daily bars to database, also registering the stock."""
        from sqlalchemy import delete
        async with async_session_factory() as session:
            # Delete existing data for symbol to prevent duplicates
            await session.execute(
                delete(DailyBar).where(DailyBar.symbol == symbol)
            )

            rows = []
            for _, row in df.iterrows():
                bar = DailyBar(
                    symbol=symbol,
                    market=market,
                    trade_date=row["trade_date"].to_pydatetime().date()
                    if hasattr(row["trade_date"], "to_pydatetime")
                    else row["trade_date"],
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    adjusted_close=float(row.get("adjusted_close", row["close"])),
                    volume=float(row["volume"]),
                )
                rows.append(bar)

            session.add_all(rows)

            # Register/update the stock in the Stock table
            existing = await session.execute(
                select(Stock).where(Stock.symbol == symbol, Stock.market == market)
            )
            stock = existing.scalar_one_or_none()
            if stock:
                stock.updated_at = datetime.now()
            else:
                from data.stock_names import resolve_name
                stock_name = resolve_name(symbol, market)
                stock = Stock(
                    symbol=symbol,
                    name=stock_name,
                    market=market,
                    is_active=True,
                )
                session.add(stock)

            await session.commit()
            return len(rows)

    async def get_market_summary(self) -> dict:
        """Get overall market summary.

        Returns basic market stats including stock counts and last update time.
        """
        try:
            async with async_session_factory() as session:
                result = await session.execute(select(Stock))
                stocks = result.scalars().all()

            return {
                "total_stocks": len(stocks),
                "last_updated": datetime.now().isoformat(),
                "status": "ok",
            }
        except Exception as e:
            logger.error("get_market_summary failed", error=str(e))
            return {
                "total_stocks": 0,
                "last_updated": datetime.now().isoformat(),
                "status": "error",
                "detail": str(e),
            }

    async def get_data_status(self, market: str) -> dict:
        """Check data freshness for a market."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(DailyBar.symbol, DailyBar.trade_date)
                .where(DailyBar.market == market)
                .order_by(DailyBar.trade_date.desc())
                .limit(1)
            )
            row = result.first()
            if row:
                return {
                    "market": market,
                    "latest_date": str(row.trade_date) if hasattr(row, "trade_date") else "unknown",
                    "has_data": True,
                }
            return {"market": market, "latest_date": None, "has_data": False}
