"""
Minervini Screener v1.0 - Stage 2 Trend Analysis
Implements Mark Minervini's trend template for identifying Stage 2 uptrends.
"""
from typing import Optional
import pandas as pd
import numpy as np

from config.loader import settings
from core.logging_setup import get_logger
from indicators.ma import calculate_ma

logger = get_logger(__name__)


def check_stage2(
    df: pd.DataFrame,
    config: Optional[object] = None,
) -> dict:
    """Check if stock meets all Stage 2 trend conditions.

    Minervini Stage 2 conditions:
    1. Current price > 200-day MA
    2. 150-day MA > 200-day MA
    3. 50-day MA > 150-day MA
    4. 10-day MA > 50-day MA
    5. Current price >= 30% above 52-week low

    Args:
        df: DataFrame with price data and at least 200 rows
        config: Stage2Config object (from settings.screening.stage2)

    Returns:
        dict: {passed: bool, reasons: List[str], details: dict}
    """
    cfg = config or settings.screening.stage2
    reasons = []

    if df.empty:
        return {"passed": False, "reasons": ["无数据"], "details": {}}

    # Ensure MAs are calculated
    if any(c not in df.columns for c in ["ma_10", "ma_50", "ma_150", "ma_200"]):
        df = calculate_ma(df)

    price_col = "adjusted_close" if "adjusted_close" in df.columns else "close"
    latest = df.iloc[-1]
    price = latest.get(price_col) or latest.get("close")

    if pd.isna(price):
        return {"passed": False, "reasons": ["无法获取最新价格"], "details": {}}

    checks = {}
    all_passed = True

    # Condition 1: Price > 200-day MA
    ma_200 = latest.get("ma_200")
    if pd.notna(ma_200):
        cond1 = price > ma_200
        pct_above = (price - ma_200) / ma_200 * 100
        checks["price_above_ma200"] = {
            "passed": cond1,
            "value": f"价格{price:.2f} {'>' if cond1 else '<'} 200日均线{ma_200:.2f} ({pct_above:+.1f}%)",
        }
        reasons.append(
            f"股价{price:.2f} {'高于' if cond1 else '低于'}200日均线{ma_200:.2f}：{'通过' if cond1 else '未通过'}"
        )
        if not cond1:
            all_passed = False
    else:
        checks["price_above_ma200"] = {"passed": False, "value": "数据不足"}
        reasons.append("200日均线数据不足：未通过")
        all_passed = False

    # Condition 2: 150-day MA > 200-day MA
    ma_150 = latest.get("ma_150")
    ma_200_v2 = latest.get("ma_200")
    if pd.notna(ma_150) and pd.notna(ma_200_v2) and ma_200_v2 != 0:
        cond2 = ma_150 > ma_200_v2
        checks["ma150_above_ma200"] = {
            "passed": cond2,
            "value": f"150日线{ma_150:.2f} {'>' if cond2 else '<'} 200日线{ma_200_v2:.2f}",
        }
        reasons.append(
            f"150日线{ma_150:.2f} {'高于' if cond2 else '低于'}200日线{ma_200_v2:.2f}：{'通过' if cond2 else '未通过'}"
        )
        if not cond2:
            all_passed = False
    else:
        checks["ma150_above_ma200"] = {"passed": False, "value": "数据不足"}
        reasons.append("150/200日均线数据不足：未通过")
        all_passed = False

    # Condition 3: 50-day MA > 150-day MA
    ma_50 = latest.get("ma_50")
    ma_150_v2 = latest.get("ma_150")
    if pd.notna(ma_50) and pd.notna(ma_150_v2) and ma_150_v2 != 0:
        cond3 = ma_50 > ma_150_v2
        checks["ma50_above_ma150"] = {
            "passed": cond3,
            "value": f"50日线{ma_50:.2f} {'>' if cond3 else '<'} 150日线{ma_150_v2:.2f}",
        }
        reasons.append(
            f"50日线{ma_50:.2f} {'高于' if cond3 else '低于'}150日线{ma_150_v2:.2f}：{'通过' if cond3 else '未通过'}"
        )
        if not cond3:
            all_passed = False
    else:
        checks["ma50_above_ma150"] = {"passed": False, "value": "数据不足"}
        reasons.append("50/150日均线数据不足：未通过")
        all_passed = False

    # Condition 4: 10-day MA > 50-day MA
    ma_10 = latest.get("ma_10")
    ma_50_v2 = latest.get("ma_50")
    if pd.notna(ma_10) and pd.notna(ma_50_v2) and ma_50_v2 != 0:
        cond4 = ma_10 > ma_50_v2
        checks["ma10_above_ma50"] = {
            "passed": cond4,
            "value": f"10日线{ma_10:.2f} {'>' if cond4 else '<'} 50日线{ma_50_v2:.2f}",
        }
        reasons.append(
            f"10日线{ma_10:.2f} {'高于' if cond4 else '低于'}50日线{ma_50_v2:.2f}：{'通过' if cond4 else '未通过'}"
        )
        if not cond4:
            all_passed = False
    else:
        checks["ma10_above_ma50"] = {"passed": False, "value": "数据不足"}
        reasons.append("10/50日均线数据不足：未通过")
        all_passed = False

    # Condition 5: Price >= 30% above 52-week low
    min_rise = cfg.min_rise_from_52w_low_pct
    window = 252
    if len(df) >= window:
        low_52w = df["low"].tail(window).min()
        if low_52w > 0:
            rise_pct = (price - low_52w) / low_52w * 100
            cond5 = rise_pct >= min_rise
            checks["rise_from_52w_low"] = {
                "passed": cond5,
                "value": f"距52周低点涨幅{rise_pct:.1f}% {'>=' if cond5 else '<'} {min_rise:.0f}%",
            }
            reasons.append(
                f"较52周低点上涨{rise_pct:.1f}%{'，' if cond5 else '，未'}达到{min_rise:.0f}%阈值：{'通过' if cond5 else '未通过'}"
            )
            if not cond5:
                all_passed = False
        else:
            checks["rise_from_52w_low"] = {"passed": False, "value": "52周低点为0"}
            reasons.append("52周低点异常：未通过")
            all_passed = False
    else:
        # Use available data
        low_period = df["low"].min()
        if low_period > 0:
            rise_pct = (price - low_period) / low_period * 100
            cond5 = rise_pct >= min_rise
            checks["rise_from_period_low"] = {
                "passed": cond5,
                "value": f"距区间低点涨幅{rise_pct:.1f}% {'>=' if cond5 else '<'} {min_rise:.0f}%",
            }
            reasons.append(
                f"较数据区间低点上涨{rise_pct:.1f}%{'，' if cond5 else '，未'}达到{min_rise:.0f}%阈值：{'通过' if cond5 else '未通过'}"
            )
            if not cond5:
                all_passed = False
        else:
            checks["rise_from_period_low"] = {"passed": False, "value": "低点异常"}
            reasons.append("低点数据异常：未通过")
            all_passed = False

    return {
        "passed": all_passed,
        "reasons": reasons,
        "details": checks,
        "price": round(float(price), 2),
    }
