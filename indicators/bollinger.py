"""
Minervini Screener v1.0 - Bollinger Bands Indicator
"""
from typing import Optional
import pandas as pd
import numpy as np

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


def calculate_bollinger(
    df: pd.DataFrame,
    period: Optional[int] = None,
    std_mult: Optional[float] = None,
) -> pd.DataFrame:
    """Calculate Bollinger Bands.

    Args:
        df: DataFrame with price data
        period: MA period, defaults to 20
        std_mult: Standard deviation multiplier, defaults to 2.0

    Returns:
        DataFrame with added: boll_mid, boll_upper, boll_lower, boll_width
    """
    result = df.copy()
    period = period or settings.indicators.bollinger.period
    std_mult = std_mult or settings.indicators.bollinger.std_multiplier

    price_col = "adjusted_close" if "adjusted_close" in result.columns else "close"
    if price_col not in result.columns:
        logger.error("No price column for Bollinger calculation")
        return result

    result["boll_mid"] = result[price_col].rolling(window=period).mean()
    rolling_std = result[price_col].rolling(window=period).std(ddof=0)

    result["boll_upper"] = result["boll_mid"] + (rolling_std * std_mult)
    result["boll_lower"] = result["boll_mid"] - (rolling_std * std_mult)

    # Bandwidth: (upper - lower) / mid
    result["boll_width"] = (
        (result["boll_upper"] - result["boll_lower"]) / result["boll_mid"].replace(0, np.nan)
    )

    # %B: (price - lower) / (upper - lower)
    result["boll_pct_b"] = (
        (result[price_col] - result["boll_lower"])
        / (result["boll_upper"] - result["boll_lower"]).replace(0, np.nan)
    )

    return result


def detect_bollinger_squeeze(
    df: pd.DataFrame,
    threshold_pct: Optional[float] = None,
    lookback: int = 20,
) -> pd.Series:
    """Detect Bollinger Band squeeze (volatility contraction).

    Squeeze occurs when bandwidth is near its low over the lookback period.

    Returns:
        Boolean Series where True = squeeze detected
    """
    threshold_pct = threshold_pct or settings.patterns.bollinger.band_width_contract_pct

    if "boll_width" not in df.columns or len(df) < lookback:
        return pd.Series([False] * len(df), index=df.index)

    width = df["boll_width"]
    width_low = width.rolling(window=lookback).min()
    width_high = width.rolling(window=lookback).max()

    # Squeeze when bandwidth is in the bottom 15% of its lookback range
    range_width = width_high - width_low
    range_width = range_width.replace(0, np.nan)
    relative_position = (width - width_low) / range_width

    return relative_position < threshold_pct


def detect_bollinger_buy_signal(df: pd.DataFrame) -> dict:
    """Detect Bollinger Band buy signal.

    Conditions:
    1. Price touched/broke below lower band
    2. Price crosses back above mid band
    3. Volume confirmation on cross above mid
    4. Band width contracted before expansion

    Returns:
        dict: {detected, lower_touch_date, mid_cross_date, bandwidth_change,
               volume_confirmed, signal_strength, reason}
    """
    result = {
        "detected": False,
        "lower_touch_date": None,
        "mid_cross_date": None,
        "bandwidth_change": 0,
        "volume_confirmed": False,
        "signal_strength": "low",
        "reason": "",
    }

    required = ["boll_upper", "boll_lower", "boll_mid", "boll_width", "volume"]
    if not all(c in df.columns for c in required) or len(df) < 30:
        result["reason"] = "布林数据不足"
        return result

    price_col = "adjusted_close" if "adjusted_close" in df.columns else "close"
    recent = df.tail(20)

    # Find lower band touch in last 10 days
    lower_touch = recent[recent[price_col] <= recent["boll_lower"]]
    if lower_touch.empty:
        result["reason"] = "未触碰到布林下轨"
        return result

    touch_date = str(lower_touch.index[-1]) if hasattr(lower_touch.index[-1], "strftime") else str(lower_touch.tail(1).index[0])

    # Check if price crossed back above mid band after touch
    after_touch = recent.loc[lower_touch.index[-1]:]
    mid_cross = after_touch[after_touch[price_col] >= after_touch["boll_mid"]]

    if mid_cross.empty:
        result["reason"] = "触碰下轨后未站回中轨"
        return result

    cross_date = str(mid_cross.index[0]) if hasattr(mid_cross.index[0], "strftime") else str(mid_cross.index[0])

    # Check bandwidth contraction before signal
    before_width = df["boll_width"].iloc[-len(recent)-10:-len(recent)].mean() if len(df) > len(recent) + 10 else 0
    current_width = recent["boll_width"].iloc[:5].mean()
    bw_change = ((before_width - current_width) / before_width * 100) if before_width > 0 else 0

    # Volume confirmation
    vol_ratio = recent["volume"].iloc[-1] / recent["volume_ma_20"].iloc[-1] if "volume_ma_20" in recent.columns else 1
    volume_confirmed = vol_ratio > settings.patterns.bollinger.volume_confirmation_multiplier

    signal_strength = "high" if (bw_change > 15 and volume_confirmed) else "medium" if (bw_change > 5) else "low"

    return {
        "detected": True,
        "lower_touch_date": touch_date,
        "mid_cross_date": cross_date,
        "bandwidth_change": round(float(bw_change), 2),
        "volume_confirmed": volume_confirmed,
        "volume_ratio": round(float(vol_ratio), 2),
        "signal_strength": signal_strength,
        "reason": f"布林下轨触碰后站回中轨，带宽变化{bw_change:.1f}%，量比{vol_ratio:.2f}",
    }
