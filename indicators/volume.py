"""
Minervini Screener v1.0 - Volume Indicators
"""
from typing import List, Optional
import pandas as pd
import numpy as np

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


def calculate_volume_ma(
    df: pd.DataFrame,
    periods: Optional[List[int]] = None,
) -> pd.DataFrame:
    """Calculate volume moving averages.

    Args:
        df: DataFrame with 'volume' column
        periods: List of SMA periods, defaults to [20, 50]

    Returns:
        DataFrame with added volume_ma_{period} columns
    """
    result = df.copy()
    periods = periods or settings.indicators.volume.sma_periods

    if "volume" not in result.columns:
        logger.error("Missing 'volume' column")
        return result

    for period in periods:
        col_name = f"volume_ma_{period}"
        result[col_name] = result["volume"].rolling(window=period).mean()

    return result


def detect_volume_spike(
    df: pd.DataFrame,
    multiplier: Optional[float] = None,
    ma_period: int = 20,
) -> pd.Series:
    """Detect volume spikes (volume > multiplier * avg volume).

    Args:
        df: DataFrame with 'volume' column
        multiplier: Volume multiplier threshold, defaults to config
        ma_period: MA period for volume baseline

    Returns:
        Boolean Series where True = volume spike detected
    """
    multiplier = multiplier or settings.signals.get("buy", {}).get("volume_multiplier", 1.5)
    vol_ma_col = f"volume_ma_{ma_period}"

    if vol_ma_col not in df.columns:
        df = calculate_volume_ma(df, [ma_period])

    if vol_ma_col not in df.columns:
        return pd.Series([False] * len(df), index=df.index)

    return df["volume"] > df[vol_ma_col] * multiplier


def detect_volume_decline(
    df: pd.DataFrame,
    window: int = 10,
) -> pd.Series:
    """Detect declining volume trend.

    Checks if volume has been consistently decreasing over the window.

    Returns:
        Boolean Series where True = volume in decline
    """
    if "volume" not in df.columns or len(df) < window:
        return pd.Series([False] * len(df), index=df.index)

    volume_series = df["volume"].rolling(window=window)

    # Check if recent volume avg < earlier volume avg
    recent_avg = volume_series.mean()
    earlier_avg = df["volume"].shift(window).rolling(window=window).mean()

    return recent_avg < earlier_avg * 0.9  # 10%+ decline


def calculate_volume_ratio(df: pd.DataFrame) -> pd.Series:
    """Calculate volume ratio (current / avg_20)."""
    if "volume_ma_20" not in df.columns:
        df = calculate_volume_ma(df)
    return df["volume"] / df["volume_ma_20"].replace(0, np.nan)
