"""
Minervini Screener v1.0 - Backtesting Engine
Simulates trading strategy on historical data.
"""
from typing import Optional
from datetime import datetime
import pandas as pd
import numpy as np

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


class BacktestEngine:
    """Simple backtesting engine for Minervini strategy.

    Walks through historical data and simulates trades based on
    pattern detection and breakout signals.
    """

    def __init__(
        self,
        initial_capital: float = 100000,
        commission_pct: float = 0.0003,
        slippage_pct: float = 0.001,
    ):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.positions: dict[str, dict] = {}
        self.trades: list[dict] = []
        self.equity_curve: list[float] = []
        self.date_curve: list[str] = []
        self.max_positions = 6  # Minervini default
        self.max_position_pct = 25  # 25% max single position

    def run(
        self,
        data: dict[str, pd.DataFrame],
        signals: dict[str, pd.Series],
        start_date: str,
        end_date: Optional[str] = None,
    ) -> dict:
        """Run backtest over historical period.

        Args:
            data: {code: OHLCV DataFrame} with pre-calculated indicators
            signals: {code: signal_series} with buy signals
            start_date: Backtest start
            end_date: Backtest end (default: today)

        Returns:
            dict with performance metrics
        """
        end = end_date or datetime.now().strftime("%Y-%m-%d")
        logger.info(f"开始回测: {start_date} ~ {end}，{len(data)}只股票")

        # Get common date index
        all_dates = pd.date_range(start=start_date, end=end, freq="B")
        all_dates = [d.strftime("%Y-%m-%d") for d in all_dates]

        self.equity_curve = [self.initial_capital]
        self.date_curve = [start_date]

        for current_date in all_dates:
            day_capital = self.capital + sum(
                pos["shares"] * pos["entry_price"]
                for pos in self.positions.values()
            )

            # Check exits
            self._check_exits(data, current_date)

            # Check entries
            if len(self.positions) < self.max_positions:
                self._check_entries(data, signals, current_date)

            # Record equity
            total_equity = self._calculate_equity(data, current_date)
            self.equity_curve.append(total_equity)
            self.date_curve.append(current_date)

        # Calculate metrics
        results = self._calculate_results()
        return results

    def _check_entries(
        self,
        data: dict[str, pd.DataFrame],
        signals: dict[str, pd.Series],
        current_date: str,
    ):
        """Check for new entry signals."""
        slots = self.max_positions - len(self.positions)

        candidates = []
        for code, signal_series in signals.items():
            if code in self.positions:
                continue
            if code not in data:
                continue

            df = data[code]
            if current_date not in df.index:
                continue

            idx = df.index.get_loc(current_date)
            if idx < 1:
                continue

            signal = signal_series.get(current_date, 0)
            if signal <= 0:
                continue

            price = df["close"].iloc[idx]
            if price <= 0:
                continue

            candidates.append((code, price, signal))

        # Sort by signal strength and take top slots
        candidates.sort(key=lambda x: x[2], reverse=True)
        for code, price, _ in candidates[:slots]:
            shares = self._position_sizing(price)
            if shares <= 0:
                continue

            cost = shares * price
            if cost > self.capital:
                continue

            self.positions[code] = {
                "entry_date": current_date,
                "entry_price": price,
                "shares": shares,
                "highest_price": price,
            }
            self.capital -= cost

            self.trades.append({
                "date": current_date,
                "action": "buy",
                "code": code,
                "price": round(price, 2),
                "shares": shares,
                "cost": round(cost, 2),
            })

    def _check_exits(self, data: dict[str, pd.DataFrame], current_date: str):
        """Check for stop loss / take profit exits."""
        for code in list(self.positions.keys()):
            if code not in data:
                self._close_position(code, current_date, "数据缺失")
                continue

            df = data[code]
            if current_date not in df.index:
                continue

            idx = df.index.get_loc(current_date)
            if idx < 0:
                continue

            pos = self.positions[code]
            current_price = df["close"].iloc[idx]

            # Update highest price
            if current_price > pos["highest_price"]:
                pos["highest_price"] = current_price

            # Stop loss check
            stop_pct = 0.08  # 8% max loss default
            loss = (current_price - pos["entry_price"]) / pos["entry_price"]
            if loss < -stop_pct:
                self._close_position(code, current_date, "止损", exit_price=current_price)
                continue

            # Trailing stop
            if pos["highest_price"] > pos["entry_price"] * 1.1:
                trail_from = max(pos["entry_price"], pos["highest_price"] * 0.85)
                if current_price < trail_from:
                    self._close_position(code, current_date, "移动止盈", exit_price=current_price)
                    continue

    def _position_sizing(self, price: float) -> int:
        """Calculate position size."""
        max_position = self.capital * self.max_position_pct / 100
        shares = int(max_position / price) if price > 0 else 0
        return max(shares, 0)

    def _close_position(self, code: str, date: str, reason: str, exit_price: Optional[float] = None):
        """Close a position and record trade.

        Args:
            code: Stock symbol
            date: Closing date
            reason: Reason for closing
            exit_price: Current market price (preferred). If None, uses entry price as fallback.
        """
        pos = self.positions.pop(code, None)
        if pos is None:
            return

        entry_price = pos["entry_price"]
        shares = pos["shares"]

        # Estimate exit price with slippage applied to market price
        price_before_slippage = exit_price if exit_price is not None else entry_price
        exit_price_after = price_before_slippage * (1 - self.slippage_pct)
        value = shares * exit_price_after
        commission = value * self.commission_pct
        net_value = value - commission
        self.capital += net_value

        pnl = net_value - (shares * entry_price)
        pnl_pct = (exit_price_after / entry_price - 1) * 100

        self.trades.append({
            "date": date,
            "action": "sell",
            "code": code,
            "price": round(exit_price_after, 2),
            "shares": shares,
            "value": round(net_value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "reason": reason,
        })

    def _calculate_equity(self, data: dict, current_date: str) -> float:
        """Calculate total equity (cash + positions)."""
        total = self.capital
        for code, pos in self.positions.items():
            if code in data and current_date in data[code].index:
                idx = data[code].index.get_loc(current_date)
                price = data[code]["close"].iloc[idx]
                total += pos["shares"] * price
            else:
                total += pos["shares"] * pos["entry_price"]
        return total

    def _calculate_results(self) -> dict:
        """Calculate final performance metrics."""
        if not self.equity_curve or len(self.equity_curve) < 2:
            return {"error": "回测数据不足"}

        final_value = self.equity_curve[-1]
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100

        # Calculate drawdown
        peak = self.equity_curve[0]
        max_dd = 0
        for v in self.equity_curve:
            if v > peak:
                peak = v
            dd = (peak - v) / peak * 100
            if dd > max_dd:
                max_dd = dd

        # Win rate
        closed_trades = [t for t in self.trades if t["action"] == "sell"]
        wins = sum(1 for t in closed_trades if t.get("pnl", 0) > 0)
        win_rate = wins / len(closed_trades) * 100 if closed_trades else 0

        avg_win = (
            sum(t["pnl"] for t in closed_trades if t.get("pnl", 0) > 0) / max(wins, 1)
        )
        avg_loss = (
            sum(abs(t["pnl"]) for t in closed_trades if t.get("pnl", 0) <= 0)
            / max(len(closed_trades) - wins, 1)
        )

        profit_factor = avg_win / avg_loss if avg_loss > 0 else float("inf")

        return {
            "initial_capital": round(self.initial_capital, 2),
            "final_value": round(final_value, 2),
            "total_return_pct": round(total_return, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "total_trades": len([t for t in self.trades if t["action"] == "sell"]),
            "win_rate_pct": round(win_rate, 1),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "sharpe_ratio": round(self._calculate_sharpe(), 2),
        }

    def _calculate_sharpe(self) -> float:
        """Calculate Sharpe ratio from equity curve."""
        if len(self.equity_curve) < 30:
            return 0

        returns = pd.Series(self.equity_curve).pct_change().dropna()
        if len(returns) < 10:
            return 0

        excess = returns - 0.0002  # ~5% annual risk-free / 252
        if excess.std() == 0:
            return 0
        return float(np.sqrt(252) * excess.mean() / excess.std())
