"""
Minervini Screener v1.0 - Relative Strength (RS) Indicator
"""
from typing import Optional
import pandas as pd
import numpy as np

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


def calculate_52w_high_low(df: pd.DataFrame) -> dict:
    """Calculate 52-week high, low, and price position.

    Returns:
        dict: {high_52w, low_52w, pct_from_high, pct_from_low, reason}
    """
    result = {
        "high_52w": None,
        "low_52w": None,
        "pct_from_high": None,
        "pct_from_low": None,
        "reason": "",
    }

    if df.empty or len(df) < 252:
        # Try with available data
        if len(df) < 20:
            result["reason"] = f"数据不足({len(df)}行)"
            return result
        window = len(df)
    else:
        window = 252

    price_col = "adjusted_close" if "adjusted_close" in df.columns else "close"
    if price_col not in df.columns:
        result["reason"] = "缺少价格数据"
        return result

    recent = df.tail(window)
    high_52w = recent[price_col].max()
    low_52w = recent[price_col].min()
    current = recent[price_col].iloc[-1]

    if high_52w == 0:
        result["reason"] = "52周最高价为0"
        return result

    pct_from_high = (current - high_52w) / high_52w * 100
    pct_from_low = (current - low_52w) / low_52w * 100 if low_52w > 0 else 0

    return {
        "high_52w": round(float(high_52w), 2),
        "low_52w": round(float(low_52w), 2),
        "pct_from_high": round(float(pct_from_high), 2),
        "pct_from_low": round(float(pct_from_low), 2),
        "reason": f"当前价{current:.2f}，距52周高{high_52w:.2f}为{pct_from_high:.1f}%，距低{low_52w:.2f}为{pct_from_low:.1f}%",
    }


def calculate_rs_rating(
    stock_series: pd.Series,
    benchmark_returns: pd.DataFrame,
    months: int = 12,
) -> float:
    """Calculate simplified RS rating.

    For v1.0, RS is calculated as the stock's returns percentile
    compared to a benchmark universe over the given period.

    Args:
        stock_series: Stock's close price series
        benchmark_returns: DataFrame of returns for all benchmark stocks
        months: Lookback period in months (approx 21 trading days per month)

    Returns:
        RS percentile (0-100)
    """
    if len(stock_series) < 20:
        return 50.0  # Neutral default

    # Stock's return over period
    trading_days = months * 21
    if len(stock_series) > trading_days:
        stock_return = (stock_series.iloc[-1] / stock_series.iloc[-trading_days] - 1) * 100
    else:
        stock_return = (stock_series.iloc[-1] / stock_series.iloc[0] - 1) * 100

    if benchmark_returns.empty:
        # Without benchmark, RS = 50 + stock_return (capped 0-100)
        rs = 50 + stock_return
        return max(0, min(100, rs))

    # Percentile rank among benchmark
    if isinstance(benchmark_returns, pd.DataFrame) and not benchmark_returns.empty:
        all_returns = benchmark_returns.iloc[-1] if len(benchmark_returns) > 0 else pd.Series()
        if not all_returns.empty:
            below = (all_returns < stock_return).sum()
            total = len(all_returns)
            return round(below / total * 100, 1) if total > 0 else 50.0

    return 50.0


def get_rs_grade(percentile: float) -> str:
    """Convert RS percentile to letter grade."""
    if percentile >= 80:
        return "A"
    elif percentile >= 60:
        return "B"
    elif percentile >= 40:
        return "C"
    elif percentile >= 20:
        return "D"
    else:
        return "F"


def calculate_rs_trend(
    df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate RS trend line (stock/benchmark ratio).

    Used for RS chart visualization in frontend.

    Args:
        df: Stock DataFrame with 'adjusted_close'
        benchmark_df: Benchmark DataFrame with 'adjusted_close'

    Returns:
        DataFrame with 'rs_line' column (normalized to 100 at start)
    """
    price_col = "adjusted_close" if "adjusted_close" in df.columns else "close"
    bench_col = "adjusted_close" if "adjusted_close" in benchmark_df.columns else "close"

    if price_col not in df.columns or bench_col not in benchmark_df.columns:
        return pd.DataFrame()

    # Merge on date
    merged = df[[price_col]].join(
        benchmark_df[[bench_col]],
        how="inner",
        lsuffix="_stock",
        rsuffix="_bench",
    )

    if merged.empty:
        return pd.DataFrame()

    # Calculate RS ratio
    merged["rs_line"] = merged[price_col] / merged[bench_col]

    # Normalize to 100 at start
    if merged["rs_line"].iloc[0] > 0:
        merged["rs_line"] = merged["rs_line"] / merged["rs_line"].iloc[0] * 100

    return merged[["rs_line"]]
