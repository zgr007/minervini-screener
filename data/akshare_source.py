"""
Minervini Screener v1.0 - AKShare Data Source
Fetches A-share stock data via akshare library.
"""
import time
from datetime import datetime, timedelta
from typing import Optional, List
import pandas as pd

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


class AKShareSource:
    """Data source for Chinese A-shares using AKShare."""

    def __init__(self):
        self.max_retries = settings.data.max_retries
        self.retry_delay = settings.data.retry_delay_seconds
        self.name = "akshare"

    def _safe_import(self):
        """Lazy import akshare to avoid startup crashes if not installed."""
        try:
            import akshare as ak
            return ak
        except ImportError:
            logger.error("akshare未安装")
            return None

    def _symbol_to_sina_format(self, symbol: str) -> str:
        """Convert '000001' or '600519' to 'sz000001' or 'sh600519'."""
        if symbol.startswith(('6', '9')) or symbol.startswith('688'):
            return f"sh{symbol}"
        elif symbol.startswith(('0', '3', '2')):
            return f"sz{symbol}"
        else:
            return f"sz{symbol}"

    def fetch_daily_bars(
        self,
        symbol: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch daily OHLCV data for an A-share symbol.

        Uses Sina Finance API via AKShare (more reliable from overseas).

        Args:
            symbol: A-share code, e.g. "000001", "600519"
            start: Start date YYYYMMDD, default 5 years ago
            end: End date YYYYMMDD, default today

        Returns:
            Standardized DataFrame or empty on failure.
        """
        ak = self._safe_import()
        if ak is None:
            return pd.DataFrame()

        start_date = start or (datetime.now() - timedelta(days=365 * 5)).strftime("%Y%m%d")
        end_date = end or datetime.now().strftime("%Y%m%d")

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info("正在获取A股数据", symbol=symbol, start=start_date, end=end_date, attempt=attempt)

                # First try: Sina Finance API (more reliable internationally)
                sina_symbol = self._symbol_to_sina_format(symbol)
                df = ak.stock_zh_a_daily(symbol=sina_symbol, adjust="qfq")

                if df.empty:
                    logger.warning("新浪返回空数据", symbol=symbol)
                    # Fallback: try East Money API
                    try:
                        df = ak.stock_zh_a_hist(
                            symbol=symbol, period="daily",
                            start_date=start_date, end_date=end_date,
                        )
                    except Exception:
                        return pd.DataFrame()

                if df.empty:
                    logger.warning("A股返回空数据", symbol=symbol)
                    return pd.DataFrame()

                # Map AKShare columns to standard format
                # Sina format: date, open, high, close, low, volume, amount, outstanding_share, turnover
                # East Money format: 日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率
                if "date" in df.columns:
                    # Sina format
                    result = pd.DataFrame({
                        "symbol": symbol,
                        "trade_date": pd.to_datetime(df["date"]),
                        "open": df["open"].astype(float),
                        "high": df["high"].astype(float),
                        "low": df["low"].astype(float),
                        "close": df["close"].astype(float),
                        "adjusted_close": df["close"].astype(float),
                        "volume": df["volume"].astype(float),
                    })
                else:
                    # East Money format
                    result = pd.DataFrame({
                        "symbol": symbol,
                        "trade_date": pd.to_datetime(df["日期"]),
                        "open": df["开盘"].astype(float),
                        "high": df["最高"].astype(float),
                        "low": df["最低"].astype(float),
                        "close": df["收盘"].astype(float),
                        "adjusted_close": df["收盘"].astype(float),
                        "volume": df["成交量"].astype(float),
                    })

                # Filter by date range
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                result = result[(result["trade_date"] >= start_dt) & (result["trade_date"] <= end_dt)]

                result.sort_values("trade_date", inplace=True)
                result.reset_index(drop=True, inplace=True)

                logger.info("A股数据获取成功", symbol=symbol, rows=len(result))
                return result

            except Exception as e:
                logger.error("A股数据获取失败", symbol=symbol, error=str(e), attempt=attempt)
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)

        return pd.DataFrame()

    def fetch_stock_list(self) -> pd.DataFrame:
        """Fetch all A-share stock list.

        Returns:
            DataFrame with columns: symbol, name, exchange
        """
        ak = self._safe_import()
        if ak is None:
            return pd.DataFrame()
        try:
            df = ak.stock_zh_a_spot_em()
            result = pd.DataFrame({
                "symbol": df["代码"].astype(str).str.strip(),
                "name": df["名称"].str.strip(),
            })
            return result
        except Exception as e:
            logger.error("获取股票列表失败", error=str(e))
            return pd.DataFrame()
