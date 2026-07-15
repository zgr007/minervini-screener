"""
Minervini Screener v1.0 - Stop Loss Management
Calculates and tracks stop loss levels for positions.
"""
from typing import Optional
import pandas as pd
import numpy as np

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


def calculate_stop_loss(
    df: pd.DataFrame,
    entry_price: float,
    method: str = "atr",
    atr_multiplier: Optional[float] = None,
    max_loss_pct: Optional[float] = None,
) -> dict:
    """Calculate stop loss based on selected method.

    Supports:
    - atr: ATR-based trailing stop
    - pct: Fixed percentage stop
    - pattern: Pattern-based (VCP low, pivot, etc.)

    Args:
        df: DataFrame with OHLCV data
        entry_price: Entry price for the position
        method: 'atr', 'pct', or 'pattern'
        atr_multiplier: ATR multiplier (default from config)
        max_loss_pct: Maximum loss percentage (default from config)

    Returns:
        dict with stop loss details
    """
    risk_cfg = settings.risk
    sell_cfg = settings.signals.get("sell", {})
    stop_loss_cfg = sell_cfg.get("stop_loss", {})
    default_mult = stop_loss_cfg.get("vcp_pct", 0.08)
    default_max_loss = risk_cfg.portfolio.max_drawdown_pct
    multiplier = atr_multiplier or default_mult
    max_loss = max_loss_pct or (default_max_loss * 100)

    result = {
        "stop_price": None,
        "stop_pct": 0.0,
        "method": method,
        "atr_value": 0.0,
        "risk_amount": 0.0,
        "support_level": None,
        "trailing_active": False,
        "warning": "",
    }

    if df.empty or entry_price <= 0:
        result["warning"] = "数据或价格无效"
        return result

    price_col = "adjusted_close" if "adjusted_close" in df.columns else "close"

    if method == "atr":
        # Use ATR from indicator or calculate
        if "atr" in df.columns:
            atr_value = df["atr"].iloc[-1]
        else:
            # Simple ATR calculation
            high, low = df["high"], df["low"]
            prev_close = df[price_col].shift(1)
            tr = pd.concat([
                (high - low).abs(),
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ], axis=1).max(axis=1)
            atr_value = tr.tail(14).mean()

        atr_value = float(atr_value) if not pd.isna(atr_value) else 0.0

        if atr_value <= 0:
            result["warning"] = "ATR值无效"
            result["stop_price"] = round(entry_price * (1 - max_loss / 100), 2)
            result["stop_pct"] = round(max_loss, 2)
            return result

        # Initial stop
        stop_distance = atr_value * multiplier
        stop_price = entry_price - stop_distance
        stop_pct = stop_distance / entry_price * 100

        # Check trailing conditions
        current_price = df[price_col].iloc[-1]
        if current_price > entry_price * 1.15:
            # Trail stop up to lock in profits
            trail_stop = current_price - atr_value * multiplier * 2
            if trail_stop > stop_price:
                stop_price = trail_stop
                result["trailing_active"] = True

        result["atr_value"] = round(atr_value, 4)

    elif method == "pct":
        stop_price = entry_price * (1 - max_loss / 100)
        stop_pct = max_loss

    else:  # pattern
        # Use recent swing low
        low = df["low"]
        swing_low = low.tail(20).min() if len(low) > 20 else low.min()
        if not pd.isna(swing_low) and swing_low > 0:
            stop_price = swing_low
            stop_pct = (entry_price - stop_price) / entry_price * 100
            if stop_pct > max_loss:
                stop_price = entry_price * (1 - max_loss / 100)
                stop_pct = max_loss
            result["support_level"] = round(float(swing_low), 2)
        else:
            stop_price = entry_price * (1 - max_loss / 100)
            stop_pct = max_loss

    result["stop_price"] = round(float(stop_price), 2)
    result["stop_pct"] = round(float(stop_pct), 2)
    result["risk_amount"] = round(entry_price - stop_price, 2)

    return result


def evaluate_stop_hit(
    df: pd.DataFrame,
    stop_price: float,
) -> dict:
    """Check if stop loss has been hit.

    Args:
        df: DataFrame with price data
        stop_price: Stop loss level

    Returns:
        dict with stop loss status
    """
    result = {
        "stopped_out": False,
        "lowest_since_entry": 0.0,
        "below_stop_bars": 0,
        "gap_down": False,
        "reason": "",
    }

    if df.empty:
        result["reason"] = "无数据"
        return result

    low = df["low"].tail(10)
    close = df["adjusted_close"].tail(10) if "adjusted_close" in df.columns else df["close"].tail(10)

    if low.empty:
        return result

    lowest = low.min()
    result["lowest_since_entry"] = round(float(lowest), 2)

    below_bars = (low < stop_price).sum()
    result["below_stop_bars"] = int(below_bars)

    # Check gap down
    if len(low) >= 2:
        gap = low.iloc[-1] < low.iloc[-2] * 0.95
        result["gap_down"] = bool(gap)

    if below_bars > 0:
        result["stopped_out"] = True
        result["reason"] = f"触发止损: 最低{lowest:.2f}<止损价{stop_price:.2f}"
    elif lowest > stop_price * 1.08:
        result["reason"] = "价格远离止损，安全"

    return result


def calculate_position_size(
    account_value: float,
    stop_loss_pct: float,
    risk_per_trade_pct: Optional[float] = None,
) -> dict:
    """Calculate position size using fixed fractional model.

    Args:
        account_value: Total account value
        stop_loss_pct: Stop loss as percentage of entry
        risk_per_trade_pct: Risk per trade (default from config)

    Returns:
        dict with position sizing
    """
    risk_cfg = settings.risk
    buy_cfg = settings.signals.get("buy", {})
    risk_pct = risk_per_trade_pct or buy_cfg.get("max_risk_per_trade_pct", 0.02)

    dollar_risk = account_value * risk_pct / 100
    position_value = dollar_risk / (stop_loss_pct / 100) if stop_loss_pct > 0 else 0

    return {
        "account_value": round(account_value, 2),
        "risk_per_trade_pct": round(risk_pct, 2),
        "dollar_risk": round(dollar_risk, 2),
        "position_value": round(position_value, 2),
        "max_shares": round(position_value / 100, 0) if position_value > 0 else 0,
    }
