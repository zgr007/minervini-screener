"""
Minervini Screener v1.0 - VCP (Volatility Contraction Pattern) Detection
Identifies price patterns with 2-5 progressively smaller contractions.
"""
from typing import Optional
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


def detect_vcp(
    df: pd.DataFrame,
    config: Optional[object] = None,
) -> dict:
    """Detect Volatility Contraction Pattern.

    VCP is characterized by 2-5 contractions in price range where each
    contraction is smaller than the previous one, with declining volume.

    Args:
        df: DataFrame with OHLCV data (enough rows for analysis)
        config: VCPConfig from settings.patterns.vcp

    Returns:
        dict with detection results
    """
    cfg = config or settings.patterns.vcp
    result = {
        "detected": False,
        "contractions_count": 0,
        "contractions": [],
        "pivot_price": None,
        "pattern_low": None,
        "stop_price": None,
        "confidence": "low",
        "reason": "",
    }

    if df.empty or len(df) < 50:
        result["reason"] = "数据不足(需至少50行)"
        return result

    price_col = "adjusted_close" if "adjusted_close" in df.columns else "close"

    # Find peaks and troughs in the price data
    lookback = min(len(df), 120)  # Last ~6 months
    segment = df.tail(lookback).copy()
    segment_idx = segment.index

    # Find local maxima (peaks) and minima (troughs)
    order = 5  # Look at 5 bars on each side
    peak_idx = argrelextrema(segment[price_col].values, np.greater, order=order)[0]
    trough_idx = argrelextrema(segment[price_col].values, np.less, order=order)[0]

    if len(peak_idx) < 2 or len(trough_idx) < 2:
        result["reason"] = f"无法识别足够的高低点(峰值{len(peak_idx)},谷值{len(trough_idx)})"
        return result

    # Build contraction candidates from peak-trough pairs
    peaks = segment.iloc[peak_idx]
    troughs = segment.iloc[trough_idx]

    contractions = []
    # Match peaks to subsequent troughs
    for i in range(min(len(peaks), len(troughs))):
        if i < len(peaks) - 1:
            # Contraction = peak to next trough
            p_high = peaks[price_col].iloc[i]
            p_low = troughs[price_col].iloc[i] if i < len(troughs) else peaks[price_col].iloc[i+1]
            decline = (p_high - p_low) / p_high * 100

            # Volume during contraction
            p_idx = peaks.index[i]
            t_idx = troughs.index[i] if i < len(troughs) else segment.index[-1]
            if p_idx < t_idx:
                vol_slice = segment.loc[p_idx:t_idx, "volume"]
            else:
                vol_slice = segment.loc[t_idx:p_idx, "volume"]
            avg_vol = vol_slice.mean()

            contractions.append({
                "peak_idx": p_idx,
                "trough_idx": t_idx if i < len(troughs) else None,
                "high": float(p_high),
                "low": float(p_low),
                "decline_pct": round(float(decline), 2),
                "volume": round(float(avg_vol), 0),
            })

    if len(contractions) < cfg.min_contractions:
        result["reason"] = f"识别到{len(contractions)}次收缩，不足最低{cfg.min_contractions}次"
        return result

    # Check if contractions are decreasing
    declines = [c["decline_pct"] for c in contractions if c["decline_pct"] > 0]
    if len(declines) < cfg.min_contractions:
        result["reason"] = f"有效收缩次数{len(declines)}不足"
        return result

    # Truncate to max_contractions
    declines = declines[:cfg.max_contractions]

    # Check declining contraction pattern
    is_decreasing = all(declines[i] >= declines[i+1] for i in range(len(declines)-1))

    if cfg.contraction_decrease_required and not is_decreasing:
        result["reason"] = f"收缩幅度未递减: {declines}"
        return result

    # Check volume decline across contractions
    volumes = [c["volume"] for c in contractions[:len(declines)]]
    vol_declining = all(volumes[i] >= volumes[i+1] for i in range(len(volumes)-1)) if len(volumes) > 1 else True

    if cfg.volume_decline_required and not vol_declining:
        result["reason"] = "成交量未递减"
        return result

    # Pattern found!
    last_contraction = contractions[len(declines) - 1]
    pivot_price = last_contraction["high"]
    pattern_low = min(c["low"] for c in contractions)
    stop_price = pattern_low * (1 - cfg.stop_loss_pct_below_low)

    # Confidence assessment
    perfect_pattern = is_decreasing and vol_declining and len(declines) >= 3
    good_pattern = is_decreasing and len(declines) >= 2
    confidence = "high" if perfect_pattern else "medium" if good_pattern else "low"

    result.update({
        "detected": True,
        "contractions_count": len(declines),
        "contractions": [{"decline_pct": d, "volume_declining": vol_declining} for d in declines],
        "pivot_price": round(float(pivot_price), 2),
        "pattern_low": round(float(pattern_low), 2),
        "stop_price": round(float(stop_price), 2),
        "confidence": confidence,
        "reason": f"VCP识别成功: {len(declines)}次收缩，递减幅度{'，'.join(f'{d:.1f}%' for d in declines)}，"
                  f"Pivot {pivot_price:.2f}，止损 {stop_price:.2f}",
    })

    return result
