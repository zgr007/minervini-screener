"""
Minervini Screener v1.0 - Average True Range (ATR) Indicator
"""
from typing import Optional
import pandas as pd
import numpy as np

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


def calculate_atr(
    df: pd.DataFrame,
    period: Optional[int] = None,
) -> pd.DataFrame:
    """Calculate Average True Range.

    ATR measures market volatility by decomposing the entire range of a price
    movement for a given period. Used for VCP detection and stop loss placement.

    Args:
        df: DataFrame with columns [high, low, close]
        period: ATR period, defaults to 14

    Returns:
        DataFrame with added 'atr' column
    """
    result = df.copy()
    period = period or settings.indicators.atr.period

    required = ["high", "low", "close"]
    if not all(c in result.columns for c in required):
        logger.error("ATR计算缺少必需列: high, low, close")
        return result

    prev_close = result["close"].shift(1)

    # True Range = max(high-low, abs(high-prev_close), abs(low-prev_close))
    tr = pd.concat([
        (result["high"] - result["low"]).abs(),
        (result["high"] - prev_close).abs(),
        (result["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)

    result["tr"] = tr
    result["atr"] = tr.rolling(window=period).mean()

    # Normalized ATR (ATR/Close * 100) for comparison across prices
    result["atr_pct"] = (result["atr"] / result["close"]) * 100

    return result


def detect_volatility_contraction(
    df: pd.DataFrame,
    lookback: int = 50,
    contraction_window: int = 10,
) -> dict:
    """Detect if volatility is contracting (useful for VCP).

    Checks if recent ATR is declining relative to the lookback period.

    Returns:
        dict: {contracting: bool, current_atr: float, avg_atr: float,
               contraction_pct: float, reason: str}
    """
    if "atr" not in df.columns or len(df) < lookback:
        return {
            "contracting": False,
            "current_atr": 0,
            "avg_atr": 0,
            "contraction_pct": 0,
            "reason": "ATR数据不足",
        }

    recent = df["atr"].iloc[-contraction_window:].mean()
    historical = df["atr"].iloc[-lookback:-contraction_window].mean() if len(df) > contraction_window else df["atr"].mean()

    if historical == 0 or pd.isna(historical):
        return {"contracting": False, "current_atr": float(recent), "avg_atr": float(historical),
                "contraction_pct": 0, "reason": "历史ATR为零"}

    contraction_pct = (historical - recent) / historical * 100

    return {
        "contracting": contraction_pct > 10,  # More than 10% contraction
        "current_atr": round(float(recent), 4),
        "avg_atr": round(float(historical), 4),
        "contraction_pct": round(float(contraction_pct), 2),
        "reason": f"ATR从{historical:.4f}收缩{contraction_pct:.1f}%到{recent:.4f}" if contraction_pct > 0
                  else f"ATR扩张{abs(contraction_pct):.1f}%",
    }
