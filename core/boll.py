"""
Minervini Screener v1.0 - Bollinger Band Signal Detection
Identifies buy signals from Bollinger Band patterns.
"""
from typing import Optional
import pandas as pd

from config.loader import settings
from core.logging_setup import get_logger
from indicators.bollinger import detect_bollinger_buy_signal

logger = get_logger(__name__)


def detect_bollinger_signal(
    df: pd.DataFrame,
    config: Optional[object] = None,
) -> dict:
    """Detect Bollinger Band buy signal.

    Delegates to indicators.bollinger.detect_bollinger_buy_signal
    after ensuring Bollinger Bands are calculated.

    Args:
        df: DataFrame with OHLCV data
        config: BollingerSignalConfig

    Returns:
        dict with detection results
    """
    cfg = config or settings.patterns.bollinger

    # Ensure BB are calculated
    required_cols = ["boll_upper", "boll_lower", "boll_mid", "boll_width"]
    if not all(c in df.columns for c in required_cols):
        from indicators.bollinger import calculate_bollinger
        df = calculate_bollinger(df)

    if not all(c in df.columns for c in required_cols):
        return {
            "detected": False,
            "lower_touch_date": None,
            "mid_cross_date": None,
            "bandwidth_change": 0,
            "volume_confirmed": False,
            "signal_strength": "low",
            "reason": "布林带计算失败",
        }

    return detect_bollinger_buy_signal(df)
