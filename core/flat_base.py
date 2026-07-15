"""
Minervini Screener v1.0 - Flat Base Pattern Detection
Identifies low-volatility consolidation patterns.
"""
from typing import Optional
import pandas as pd
import numpy as np

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


def detect_flat_base(
    df: pd.DataFrame,
    config: Optional[object] = None,
) -> dict:
    """Detect Flat Base pattern.

    Characteristics:
    - 3+ weeks of low-volatility consolidation
    - Price range 5-15% between high and low
    - Volume contracting during base
    - Breakout above base high triggers buy

    Args:
        df: DataFrame with OHLCV data
        config: FlatBaseConfig from settings.patterns.flat_base

    Returns:
        dict with detection results
    """
    cfg = config or settings.patterns.flat_base
    result = {
        "detected": False,
        "base_high": None,
        "base_low": None,
        "duration_days": 0,
        "buy_point": None,
        "stop_price": None,
        "can_add": False,
        "confidence": "low",
        "reason": "",
    }

    min_days = cfg.min_weeks * 5
    if df.empty or len(df) < min_days + 10:
        result["reason"] = f"数据不足(需至少{min_days + 10}行)"
        return result

    price_col = "adjusted_close" if "adjusted_close" in df.columns else "close"
    range_min, range_max = cfg.range_pct

    # Scan for flat base in the last N days
    lookback = min(len(df), 120)
    segment = df.tail(lookback).copy()

    # Use a sliding window to find flat base regions
    best_base = None
    best_range = float("inf")

    for start in range(0, len(segment) - min_days, 5):
        for end in range(start + min_days, min(start + 60, len(segment))):
            region = segment.iloc[start:end]
            high = region[price_col].max()
            low = region[price_col].min()

            if low == 0:
                continue

            range_pct = (high - low) / low * 100

            if range_min <= range_pct <= range_max:
                duration = end - start
                # Prefer longer bases with tighter range
                score = duration / range_pct
                if best_base is None or score > best_base["score"]:
                    # Check volume contraction
                    vol_ratio = region["volume"].mean() / segment["volume"].mean() if segment["volume"].mean() > 0 else 1
                    best_base = {
                        "start": start,
                        "end": end,
                        "high": high,
                        "low": low,
                        "range_pct": range_pct,
                        "duration": duration,
                        "vol_ratio": vol_ratio,
                        "score": score,
                    }

    if best_base is None:
        result["reason"] = f"未找到符合条件(区间{range_min}-{range_max}%)的平台底"
        return result

    # Check volume contraction
    if best_base["vol_ratio"] > 1.2:
        result["reason"] = f"平台内成交量未收缩(量比{best_base['vol_ratio']:.2f})"
        return result

    # Pattern found!
    base_high = best_base["high"]
    base_low = best_base["low"]
    buy_point = base_high
    stop_price = base_low * (1 - cfg.stop_loss_pct)

    # Can add position if range is tight and duration is long
    can_add = best_base["range_pct"] < range_max * 0.6 and best_base["duration"] >= min_days * 2
    confidence = "high" if (best_base["range_pct"] < 8 and best_base["duration"] > 20) else "medium"

    result.update({
        "detected": True,
        "base_high": round(float(base_high), 2),
        "base_low": round(float(base_low), 2),
        "duration_days": best_base["duration"],
        "buy_point": round(float(buy_point), 2),
        "stop_price": round(float(stop_price), 2),
        "can_add": can_add,
        "confidence": confidence,
        "reason": f"平台底识别成功: {best_base['duration']}天，区间{best_base['range_pct']:.1f}%，"
                  f"量比{best_base['vol_ratio']:.2f}，买入点{buy_point:.2f}，止损{stop_price:.2f}",
    })

    return result
