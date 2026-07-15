"""
Minervini Screener v1.0 - Double Bottom Pattern Detection
Identifies W-shaped reversal patterns.
"""
from typing import Optional
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


def detect_double_bottom(
    df: pd.DataFrame,
    config: Optional[object] = None,
) -> dict:
    """Detect Double Bottom (W-bottom) pattern.

    Characteristics:
    - Two troughs at similar price levels
    - Second bottom volume should be lower
    - Minimum gap between bottoms
    - Neckline = highest point between the two bottoms

    Args:
        df: DataFrame with OHLCV data
        config: DoubleBottomConfig from settings.patterns.double_bottom

    Returns:
        dict with detection results
    """
    cfg = config or settings.patterns.double_bottom
    result = {
        "detected": False,
        "first_bottom": None,
        "second_bottom": None,
        "neckline": None,
        "buy_point": None,
        "stop_price": None,
        "target_price": None,
        "confidence": "low",
        "reason": "",
    }

    if df.empty or len(df) < 60:
        result["reason"] = "数据不足(需至少60行)"
        return result

    price_col = "adjusted_close" if "adjusted_close" in df.columns else "close"

    # Use last 6 months
    lookback = min(len(df), 180)
    segment = df.tail(lookback).copy()

    # Find local minima (troughs)
    order = 3
    trough_idx = argrelextrema(segment[price_col].values, np.less, order=order)[0]

    if len(trough_idx) < 2:
        result["reason"] = f"识别到的谷值不足({len(trough_idx)})"
        return result

    # Find best pair of bottoms
    best_pair = None
    best_score = float("-inf")

    for i in range(len(trough_idx) - 1):
        for j in range(i + 1, len(trough_idx)):
            first_idx = trough_idx[i]
            second_idx = trough_idx[j]

            # Gap between bottoms
            gap = second_idx - first_idx
            if gap < cfg.min_gap_days:
                continue

            first_price = segment[price_col].iloc[first_idx]
            second_price = segment[price_col].iloc[second_idx]

            # Bottoms should be similar (within 10% of each other)
            bottom_diff = abs(first_price - second_price) / max(first_price, second_price) * 100
            if bottom_diff > 10:
                continue

            # Find neckline (highest point between bottoms)
            between = segment.iloc[first_idx:second_idx + 1]
            neckline = between[price_col].max()
            neckline_idx = between[price_col].idxmax()

            if pd.isna(neckline) or neckline <= max(first_price, second_price):
                continue

            # Volume on second bottom should be lower
            vol_first = segment["volume"].iloc[first_idx]
            vol_second = segment["volume"].iloc[second_idx]
            vol_declining = vol_second < vol_first * 1.1

            # Rise from second bottom should be above neckline
            current_price = segment[price_col].iloc[-1]
            above_neckline = current_price > neckline

            # Score: prefer tight bottoms with clear neckline and volume decline
            score = (100 - bottom_diff) + (50 if vol_declining else 0) + (50 if above_neckline else 0) - gap * 0.1

            if score > best_score:
                best_score = score
                best_pair = {
                    "first_idx": first_idx,
                    "second_idx": second_idx,
                    "first_price": first_price,
                    "second_price": second_price,
                    "neckline": neckline,
                    "gap": gap,
                    "bottom_diff": bottom_diff,
                    "vol_declining": vol_declining,
                    "above_neckline": above_neckline,
                }

    if best_pair is None:
        result["reason"] = "未找到符合条件双底"
        return result

    if not best_pair["above_neckline"]:
        result["reason"] = f"股价未突破颈线{best_pair['neckline']:.2f}"
        return result

    # Pattern found!
    first_bottom = best_pair["first_price"]
    second_bottom = best_pair["second_price"]
    neckline = best_pair["neckline"]
    buy_point = neckline
    stop_price = second_bottom * (1 - cfg.stop_loss_pct_below_second)
    target_price = neckline + (neckline - min(first_bottom, second_bottom))

    confidence = "high" if best_pair["vol_declining"] else "medium"

    result.update({
        "detected": True,
        "first_bottom": round(float(first_bottom), 2),
        "second_bottom": round(float(second_bottom), 2),
        "neckline": round(float(neckline), 2),
        "buy_point": round(float(buy_point), 2),
        "stop_price": round(float(stop_price), 2),
        "target_price": round(float(target_price), 2),
        "confidence": confidence,
        "reason": f"双底识别成功: 第一底{first_bottom:.2f}，第二底{second_bottom:.2f}，"
                  f"颈线{neckline:.2f}，买入点{buy_point:.2f}，止损{stop_price:.2f}，目标{target_price:.2f}",
    })

    return result
