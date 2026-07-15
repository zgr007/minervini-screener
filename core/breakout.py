"""
Minervini Screener v1.0 - Breakout Detection
Identifies price breakouts from consolidation patterns with volume confirmation.
"""
from typing import Optional
import pandas as pd
import numpy as np

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


def detect_breakout(
    df: pd.DataFrame,
    buy_point: float,
    volume_surge_threshold: Optional[float] = None,
    lookback_days: int = 5,
) -> dict:
    """Detect breakout from a buy point.

    Checks if price has broken out above the buy point with
    volume confirmation.

    Args:
        df: DataFrame with OHLCV data
        buy_point: The breakout price level
        volume_surge_threshold: Minimum volume surge multiplier
        lookback_days: How many days to look back for breakout

    Returns:
        dict with breakout detection results
    """
    buy_cfg = settings.signals.get("buy", {})
    default_thresh = buy_cfg.get("volume_multiplier", 1.5)
    thresh = volume_surge_threshold or default_thresh
    result = {
        "detected": False,
        "breakout_date": None,
        "breakout_price": None,
        "volume_ratio": 1.0,
        "close_above_buy_point": False,
        "days_since_breakout": 0,
        "follow_through": False,
        "pullback_to_buy_point": False,
        "failed_breakout": False,
        "reason": "",
    }

    if df.empty or buy_point <= 0:
        result["reason"] = "数据为空或买入点无效"
        return result

    price_col = "adjusted_close" if "adjusted_close" in df.columns else "close"

    if df[price_col].empty:
        result["reason"] = "价格数据为空"
        return result

    # Check if price is near/above buy point
    current_price = df[price_col].iloc[-1]
    close_above = current_price > buy_point
    result["close_above_buy_point"] = bool(close_above)

    if not close_above:
        result["reason"] = f"当前价格{current_price:.2f}未突破买入点{buy_point:.2f}"
        return result

    # Find when the breakout occurred
    recent = df.tail(lookback_days * 3)
    breakout_idx = None

    for i in range(len(recent) - 1, -1, -1):
        if recent[price_col].iloc[i] > buy_point:
            breakout_idx = recent.index[i]
        else:
            break

    if breakout_idx is None:
        # Already above buy point for entire lookback
        result["reason"] = "价格长期高于买入点，非新鲜突破"
        return result

    # Calculate volume surge
    if "volume" in df.columns:
        avg_vol_50 = df["volume"].tail(60).iloc[:-5].mean() if len(df) > 55 else df["volume"].mean()
        if avg_vol_50 > 0:
            breakout_vol_idx = df.index.get_loc(breakout_idx)
            breakout_vol = df["volume"].iloc[breakout_vol_idx]
            volume_ratio = breakout_vol / avg_vol_50
            result["volume_ratio"] = round(float(volume_ratio), 2)

    # Check follow-through (price staying above buy point)
    after_breakout = df.loc[breakout_idx:] if breakout_idx in df.index else df.tail(min(10, len(df)))
    above_count = (after_breakout[price_col] > buy_point).sum()
    total_count = len(after_breakout)
    follow_through = total_count > 0 and above_count / total_count >= 0.6

    # Check pullback to buy point (healthy)
    if after_breakout[price_col].min() > buy_point * 0.98:
        pullback = True
    else:
        pullback = False

    # Check for failed breakout (dropped back below)
    failed = False
    if follow_through and total_count >= 5:
        latest = after_breakout.tail(min(5, len(after_breakout)))
        failed = (latest[price_col].iloc[-1] < buy_point * 1.02)

    vol_ratio = result["volume_ratio"]  # Always defined: default 1.0, updated when volume data exists
    days_since = len(after_breakout)
    result.update({
        "detected": bool(vol_ratio >= thresh),
        "breakout_date": str(breakout_idx.date()) if hasattr(breakout_idx, 'date') else str(breakout_idx),
        "breakout_price": round(float(recent[price_col].loc[breakout_idx]), 2),
        "volume_ratio": vol_ratio,
        "days_since_breakout": days_since,
        "follow_through": bool(follow_through),
        "pullback_to_buy_point": bool(pullback),
        "failed_breakout": bool(failed),
        "reason": f"突破{'成功' if vol_ratio >= thresh else '失败'}: "
                  f"价格{current_price:.2f}，量比{vol_ratio:.2f}，"
                  f"突破{days_since}天前",
    })

    return result


def check_breakout_distance(
    df: pd.DataFrame,
    buy_point: float,
) -> str:
    """Classify how far price is from buy point.

    Returns: 'below', 'near_breakout', 'just_above', 'extended', 'too_extended'
    """
    price_col = "adjusted_close" if "adjusted_close" in df.columns else "close"
    if df.empty:
        return "below"

    current = df[price_col].iloc[-1]
    if current < buy_point:
        return "below"

    pct_above = (current - buy_point) / buy_point * 100

    if pct_above < 2:
        return "near_breakout"
    elif pct_above < 10:
        return "just_above"
    elif pct_above < 25:
        return "extended"
    else:
        return "too_extended"
