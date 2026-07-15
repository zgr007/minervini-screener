"""
Minervini Screener v1.0 - Moving Average Indicators
"""
from typing import List, Optional
import pandas as pd
import numpy as np

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


def calculate_ma(
    df: pd.DataFrame,
    periods: Optional[List[int]] = None,
    column: str = "adjusted_close",
) -> pd.DataFrame:
    """Calculate simple moving averages.

    Args:
        df: DataFrame with price data and 'adjusted_close' column
        periods: List of MA periods, defaults to [10, 50, 150, 200]
        column: Column name to calculate MA on

    Returns:
        DataFrame with added ma_{period} columns
    """
    result = df.copy()
    periods = periods or settings.indicators.ma.periods

    if column not in result.columns:
        # Fall back to close
        column = "close"
        if column not in result.columns:
            logger.error("No price column found for MA calculation")
            return result

    for period in periods:
        col_name = f"ma_{period}"
        if len(result) >= period:
            result[col_name] = result[column].rolling(window=period).mean()
        else:
            result[col_name] = np.nan

    return result


def check_ma_alignment(df: pd.DataFrame) -> dict:
    """Check moving average alignment for trend analysis.

    Bullish alignment: ma_10 > ma_50 > ma_150 > ma_200
    Also checks price position relative to MAs.

    Returns:
        dict: {aligned: bool, price_above_ma200: bool, ma_10_above_50: bool,
               ma_50_above_150: bool, ma_150_above_200: bool, details: str}
    """
    result = {
        "aligned": False,
        "price_above_ma200": False,
        "ma_10_above_50": False,
        "ma_50_above_150": False,
        "ma_150_above_200": False,
        "details": "",
    }

    if df.empty:
        result["details"] = "无数据"
        return result

    latest = df.iloc[-1]

    # Ensure we have MA columns
    ma_10 = latest.get("ma_10")
    ma_50 = latest.get("ma_50")
    ma_150 = latest.get("ma_150")
    ma_200 = latest.get("ma_200")
    price = latest.get("close") or latest.get("adjusted_close")

    if any(v is None or pd.isna(v) for v in [ma_10, ma_50, ma_150, ma_200, price]):
        result["details"] = "MA数据不足"
        return result

    # Check each condition
    result["ma_10_above_50"] = ma_10 > ma_50
    result["ma_50_above_150"] = ma_50 > ma_150
    result["ma_150_above_200"] = ma_150 > ma_200
    result["price_above_ma200"] = price > ma_200

    # All conditions for bullish alignment
    result["aligned"] = (
        result["price_above_ma200"]
        and result["ma_10_above_50"]
        and result["ma_50_above_150"]
        and result["ma_150_above_200"]
    )

    details_parts = []
    if result["price_above_ma200"]:
        details_parts.append(f"股价{price:.2f}高于200日均线{ma_200:.2f}")
    else:
        details_parts.append(f"股价{price:.2f}低于200日均线{ma_200:.2f}")

    if result["ma_10_above_50"]:
        details_parts.append(f"10日线({ma_10:.2f})高于50日线({ma_50:.2f})")
    else:
        details_parts.append(f"10日线({ma_10:.2f})低于50日线({ma_50:.2f})")

    if result["ma_50_above_150"]:
        details_parts.append(f"50日线({ma_50:.2f})高于150日线({ma_150:.2f})")
    else:
        details_parts.append(f"50日线({ma_50:.2f})低于150日线({ma_150:.2f})")

    if result["ma_150_above_200"]:
        details_parts.append(f"150日线({ma_150:.2f})高于200日线({ma_200:.2f})")
    else:
        details_parts.append(f"150日线({ma_150:.2f})低于200日线({ma_200:.2f})")

    result["details"] = "；".join(details_parts)
    return result


def get_price_relative_to_ma(df: pd.DataFrame, period: int = 200) -> dict:
    """Get price position relative to a specific MA."""
    col = f"ma_{period}"
    if col not in df.columns or df.empty:
        return {"above": False, "pct_diff": 0}

    latest = df.iloc[-1]
    price = latest.get("close") or latest.get("adjusted_close")
    ma_val = latest.get(col)

    if pd.isna(price) or pd.isna(ma_val) or ma_val == 0:
        return {"above": False, "pct_diff": 0}

    pct_diff = (price - ma_val) / ma_val * 100
    return {"above": price > ma_val, "pct_diff": round(pct_diff, 2)}
