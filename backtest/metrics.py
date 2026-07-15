"""
Minervini Screener v1.0 - Backtest Metrics
Performance metric calculations and analysis.
"""
import math
from typing import Optional
import pandas as pd
import numpy as np


def calculate_metrics(equity_curve: list[float]) -> dict:
    """Calculate performance metrics from equity curve.

    Args:
        equity_curve: List of portfolio values over time

    Returns:
        dict with calculated metrics
    """
    if not equity_curve or len(equity_curve) < 2:
        return {}

    series = pd.Series(equity_curve)
    returns = series.pct_change().dropna()

    if returns.empty:
        return {}

    total_return = (series.iloc[-1] - series.iloc[0]) / series.iloc[0] * 100
    n_days = len(returns)
    n_years = n_days / 252

    # Annualized return
    if n_years > 0:
        ann_return = ((1 + total_return / 100) ** (1 / n_years) - 1) * 100
    else:
        ann_return = total_return

    # Volatility
    daily_vol = returns.std()
    ann_vol = daily_vol * math.sqrt(252)

    # Sharpe (assuming 3% risk-free)
    rf_daily = 0.03 / 252
    excess = returns - rf_daily
    sharpe = math.sqrt(252) * excess.mean() / daily_vol if daily_vol > 0 else 0

    # Sortino
    downside = returns[returns < 0]
    downside_vol = downside.std() if len(downside) > 0 else 0.0001
    sortino = math.sqrt(252) * excess.mean() / downside_vol

    # Max drawdown
    peak = series.expanding().max()
    drawdown = (peak - series) / peak * 100
    max_dd = drawdown.max()
    max_dd_duration = _calculate_max_dd_duration(drawdown)

    # Calmar
    calmar = ann_return / max_dd if max_dd > 0 else 0

    return {
        "total_return_pct": round(total_return, 2),
        "annual_return_pct": round(ann_return, 2),
        "annual_volatility_pct": round(ann_vol * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "calmar_ratio": round(calmar, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "max_drawdown_duration_days": max_dd_duration,
        "positive_days_pct": round((returns > 0).sum() / len(returns) * 100, 1),
        "total_days": n_days,
    }


def calculate_trade_metrics(trades: list[dict]) -> dict:
    """Calculate trade-level metrics.

    Args:
        trades: List of trade dicts (both buy and sell entries)

    Returns:
        dict with trade metrics
    """
    if not trades:
        return {}

    closed_trades = [t for t in trades if t.get("action") == "sell"]

    if not closed_trades:
        return {"total_trades": 0}

    total = len(closed_trades)
    pnls = [t.get("pnl_pct", 0) for t in closed_trades if t.get("pnl_pct") is not None]
    pnl_amounts = [t.get("pnl", 0) for t in closed_trades if t.get("pnl") is not None]

    if not pnls:
        return {"total_trades": total}

    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_count = len(wins)
    loss_count = len(losses)

    # Win rate
    win_rate = win_count / total * 100 if total > 0 else 0

    # Avg win/loss
    avg_win = sum(wins) / max(len(wins), 1)
    avg_loss = sum(losses) / max(losses, 1) if losses else 0

    # Profit factor
    gross_profit = sum(p for p in pnls if p > 0) if wins else 0
    gross_loss = abs(sum(p for p in pnls if p < 0)) if losses else 1
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Largest win/loss
    max_win = max(pnls) if wins else 0
    max_loss = min(pnls) if losses else 0

    # Consecutive wins/losses
    consec_wins = 0
    consec_losses = 0
    max_consec_wins = 0
    max_consec_losses = 0
    for p in pnls:
        if p > 0:
            consec_wins += 1
            consec_losses = 0
            max_consec_wins = max(max_consec_wins, consec_wins)
        else:
            consec_losses += 1
            consec_wins = 0
            max_consec_losses = max(max_consec_losses, consec_losses)

    # Holding period
    avg_holding = _calculate_avg_holding(trades)

    return {
        "total_trades": total,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate_pct": round(win_rate, 1),
        "avg_win_pct": round(avg_win, 2),
        "avg_loss_pct": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "max_win_pct": round(max_win, 2),
        "max_loss_pct": round(max_loss, 2),
        "max_consecutive_wins": max_consec_wins,
        "max_consecutive_losses": max_consec_losses,
        "avg_holding_days": avg_holding,
        "total_pnl_amount": round(sum(pnl_amounts), 2),
    }


def _calculate_max_dd_duration(drawdown_series: pd.Series) -> int:
    """Calculate the longest drawdown duration in days."""
    if drawdown_series.empty:
        return 0

    is_dd = drawdown_series > 0
    if not is_dd.any():
        return 0

    dd_streaks = []
    current = 0
    for v in is_dd:
        if v:
            current += 1
        else:
            if current > 0:
                dd_streaks.append(current)
            current = 0
    if current > 0:
        dd_streaks.append(current)

    return max(dd_streaks) if dd_streaks else 0


def _calculate_avg_holding(trades: list[dict]) -> int:
    """Calculate average holding period in days."""
    buy_map = {}
    total_days = 0
    count = 0

    for t in trades:
        code = t.get("code", "")
        action = t.get("action", "")
        date = t.get("date", "")

        if action == "buy":
            buy_map[code] = date
        elif action == "sell" and code in buy_map:
            buy_date = buy_map.pop(code)
            try:
                from datetime import datetime
                bd = datetime.strptime(buy_date, "%Y-%m-%d")
                sd = datetime.strptime(date, "%Y-%m-%d")
                total_days += (sd - bd).days
                count += 1
            except (ValueError, TypeError):
                continue

    return round(total_days / count) if count > 0 else 0
