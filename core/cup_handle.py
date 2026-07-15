"""
Minervini Screener v1.0 - Cup with Handle Pattern Detection
Identifies the classic cup-with-handle consolidation pattern.
"""
from typing import Optional
import pandas as pd
import numpy as np

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


def detect_cup_handle(
    df: pd.DataFrame,
    config: Optional[object] = None,
) -> dict:
    """Detect Cup with Handle pattern.

    Cup: U-shaped decline and recovery over at least 6 weeks (30 trading days)
    Handle: 1-2 week shallow pullback near cup highs

    Args:
        df: DataFrame with OHLCV data
        config: CupHandleConfig from settings.patterns.cup_handle

    Returns:
        dict with detection results
    """
    cfg = config or settings.patterns.cup_handle
    result = {
        "detected": False,
        "left_high": None,
        "cup_low": None,
        "handle_high": None,
        "handle_low": None,
        "buy_point": None,
        "stop_price": None,
        "target_price": None,
        "confidence": "low",
        "reason": "",
    }

    min_days = cfg.min_weeks * 5  # Trading days
    if df.empty or len(df) < min_days + 20:
        result["reason"] = f"数据不足(需至少{min_days + 20}行)"
        return result

    price_col = "adjusted_close" if "adjusted_close" in df.columns else "close"

    # Use last 6+ months for cup detection
    lookback = min(len(df), 200)
    segment = df.tail(lookback).copy()

    # Find the lowest point (cup bottom) in the last N days
    cup_end_idx = -20  # Exclude last 20 days for handle
    cup_region = segment.iloc[:cup_end_idx] if len(segment) > 40 else segment

    if cup_region.empty:
        result["reason"] = "杯体区域数据不足"
        return result

    cup_low_idx = cup_region[price_col].idxmin()
    cup_low = cup_region[price_col].min()

    if pd.isna(cup_low):
        result["reason"] = "无法确定杯底"
        return result

    # Find left high (highest before cup bottom)
    left_region = cup_region.loc[:cup_low_idx]
    if left_region.empty:
        result["reason"] = "无法确定左杯沿"
        return result

    left_high_idx = left_region[price_col].idxmax()
    left_high = left_region[price_col].max()

    # Find right high (highest after cup bottom, before handle)
    right_region = cup_region.loc[cup_low_idx:]
    if right_region.empty:
        result["reason"] = "无法确定右杯沿"
        return result

    right_high_idx = right_region[price_col].idxmax()
    right_high = right_region[price_col].max()

    # Cup depth
    cup_depth = (left_high - cup_low) / left_high * 100
    if cup_depth > 50 or cup_depth < 10:
        result["reason"] = f"杯体深度{cup_depth:.1f}%不在合理范围(10-50%)"
        return result

    # Cup duration
    cup_duration = (right_high_idx - left_high_idx).days if hasattr(right_high_idx, 'days') else 0
    if cup_duration < 30:
        result["reason"] = f"杯体持续时间不足({cup_duration}天 < 30天)"
        return result

    # Handle detection: after right high, look for shallow pullback
    handle_region = segment.loc[right_high_idx:]

    if len(handle_region) < 5:
        result["reason"] = "柄部区域数据不足"
        return result

    handle_low = handle_region[price_col].min()
    handle_high = handle_region[price_col].max()

    # Handle should be in upper 1/3 of cup
    handle_position = (handle_low - cup_low) / (left_high - cup_low) if left_high != cup_low else 0

    if handle_position < 0.5:
        result["reason"] = f"柄部位置过低({handle_position:.0%})"
        return result

    # Handle depth should be shallow
    handle_depth = (handle_high - handle_low) / handle_high * 100 if handle_high > 0 else 100
    if handle_depth > 15:
        result["reason"] = f"柄部回调过深({handle_depth:.1f}%)"
        return result

    # Handle duration
    handle_days = len(handle_region)
    min_handle_days = cfg.handle_weeks[0] * 5
    max_handle_days = cfg.handle_weeks[1] * 7
    if handle_days < min_handle_days or handle_days > max_handle_days * 2:
        result["reason"] = f"柄部天数{handle_days}不在合理范围({min_handle_days}-{max_handle_days}天)"
        return result

    # Pattern found!
    buy_point = handle_high
    stop_price = handle_low * (1 - cfg.stop_loss_pct)
    target_price = buy_point + (left_high - cup_low)

    confidence = "high" if handle_depth < 8 else "medium"

    result.update({
        "detected": True,
        "left_high": round(float(left_high), 2),
        "cup_low": round(float(cup_low), 2),
        "handle_high": round(float(handle_high), 2),
        "handle_low": round(float(handle_low), 2),
        "buy_point": round(float(buy_point), 2),
        "stop_price": round(float(stop_price), 2),
        "target_price": round(float(target_price), 2),
        "confidence": confidence,
        "reason": f"杯柄形态识别成功: 杯深{cup_depth:.1f}%，柄深{handle_depth:.1f}%，"
                  f"买入点{buy_point:.2f}，止损{stop_price:.2f}，目标{target_price:.2f}",
    })

    return result
