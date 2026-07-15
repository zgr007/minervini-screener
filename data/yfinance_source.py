"""
Minervini Screener v1.0 - Yahoo Finance Data Source
Fetches US stock data via yfinance library.
"""
import time
from datetime import datetime, timedelta
from typing import Optional, List
import pandas as pd
import yfinance as yf

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


class YFinanceSource:
    """Data source for US stocks using Yahoo Finance."""

    def __init__(self):
        self.max_retries = settings.data.max_retries
        self.retry_delay = settings.data.retry_delay_seconds
        self.request_timeout = settings.data.request_timeout
        self.name = "yfinance"

    def fetch_daily_bars(
        self,
        symbol: str,
        start: str = "5y",
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch daily OHLCV data for a symbol.

        Args:
            symbol: Ticker symbol (e.g. "AAPL")
            start: Start date string or "5y", "1y", "6mo", etc.
            end: End date string, defaults to today

        Returns:
            DataFrame with columns: symbol, trade_date, open, high, low, close,
            adjusted_close, volume. Returns empty DataFrame on failure.
        """
        end_date = end or datetime.now().strftime("%Y-%m-%d")

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info("正在获取美股数据", symbol=symbol, start=start, end=end_date, attempt=attempt)
                ticker = yf.Ticker(symbol)
                df = ticker.history(start=start, end=end_date, auto_adjust=True)

                if df.empty:
                    logger.warning("返回空数据", symbol=symbol)
                    return pd.DataFrame()

                # Standardize columns
                result = pd.DataFrame({
                    "symbol": symbol,
                    "trade_date": df.index.date,
                    "open": df["Open"].values,
                    "high": df["High"].values,
                    "low": df["Low"].values,
                    "close": df["Close"].values,
                    "adjusted_close": df["Close"].values,  # yfinance auto_adjust
                    "volume": df["Volume"].values,
                })
                result["trade_date"] = pd.to_datetime(result["trade_date"])
                result.sort_values("trade_date", inplace=True)
                result.reset_index(drop=True, inplace=True)

                logger.info("数据获取成功", symbol=symbol, rows=len(result))
                return result

            except Exception as e:
                logger.error("获取失败", symbol=symbol, error=str(e), attempt=attempt)
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)

        return pd.DataFrame()

    def fetch_stock_info(self, symbol: str) -> dict:
        """Fetch stock metadata.

        Returns:
            dict with keys: name, sector, industry, market_cap, currency, exchange
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info or {}
                return {
                    "symbol": symbol,
                    "name": info.get("longName") or info.get("shortName", ""),
                    "sector": info.get("sector", ""),
                    "industry": info.get("industry", ""),
                    "market_cap": info.get("marketCap", 0),
                    "currency": info.get("currency", "USD"),
                    "exchange": info.get("exchange", ""),
                }
            except Exception as e:
                logger.error("获取信息失败", symbol=symbol, error=str(e), attempt=attempt)
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
        return {"symbol": symbol, "name": "", "sector": "", "industry": "",
                "market_cap": 0, "currency": "USD", "exchange": ""}

    def fetch_multiple(self, symbols: List[str], start: str = "1y") -> dict:
        """Fetch daily data for multiple symbols.

        Returns:
            dict of {symbol: DataFrame}
        """
        result = {}
        for symbol in symbols:
            df = self.fetch_daily_bars(symbol, start)
            if not df.empty:
                result[symbol] = df
        return result
