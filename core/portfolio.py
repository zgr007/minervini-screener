"""
Minervini Screener v1.0 - Portfolio Management
Simulates portfolio tracking with position sizing and risk management.
"""
from typing import Optional
from datetime import datetime
from dataclasses import dataclass

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass
class Position:
    """Single stock position."""
    code: str
    name: str
    entry_date: str
    entry_price: float
    shares: int
    stop_price: float
    current_price: float = 0.0
    peak_price: float = 0.0
    highest_price: float = 0.0
    highest_return: float = 0.0
    pnl_pct: float = 0.0
    pnl_amount: float = 0.0
    status: str = "open"  # open, closed


class Portfolio:
    """Simulated portfolio manager.

    Not a real trading system - used for signal tracking and
    performance simulation.
    """

    def __init__(self, initial_capital: Optional[float] = None):
        cfg = settings.backtest
        risk_portfolio = settings.risk.portfolio
        self.initial_capital = initial_capital or cfg.default_initial_capital
        self.capital = self.initial_capital
        self.max_positions = 6  # Default from Minervini rules
        self.max_single_pct = risk_portfolio.max_drawdown_pct * 100 if hasattr(risk_portfolio, 'max_drawdown_pct') else 25
        self.positions: dict[str, Position] = {}
        self.closed_positions: list[Position] = []
        self.trades_log: list[dict] = []

    def can_open(self) -> bool:
        """Check if portfolio can open new position."""
        return len(self.positions) < self.max_positions

    def calculate_shares(self, entry_price: float, stop_price: float = 0.0) -> int:
        """Calculate number of shares based on Minervini position sizing.

        Minervini rule: risk 0.25% of capital per position.
        Formula: (capital * 0.0025) / (entry_price - stop_price)

        Falls back to 15% of capital if stop_price is not provided.
        """
        if stop_price > 0 and entry_price > stop_price:
            risk_per_share = entry_price - stop_price
            risk_capital = self.capital * 0.0025
            shares = int(risk_capital / risk_per_share)
        else:
            max_position_value = self.capital * self.max_single_pct / 100
            shares = int(max_position_value / entry_price) if entry_price > 0 else 0
        return max(shares, 0)

    def open_position(
        self,
        code: str,
        name: str,
        entry_price: float,
        stop_price: float,
    ) -> Optional[Position]:
        """Open a new position."""
        if not self.can_open():
            logger.warning(f"[{code}] 已达最大持仓数{self.max_positions}")
            return None

        if code in self.positions:
            logger.warning(f"[{code}] 已在持仓中")
            return None

        shares = self.calculate_shares(entry_price, stop_price)
        if shares <= 0:
            logger.warning(f"[{code}] 计算份额失败(价格{entry_price})")
            return None

        cost = shares * entry_price
        if cost > self.capital:
            logger.warning(f"[{code}] 资金不足(需{cost:.2f}，有{self.capital:.2f})")
            return None

        position = Position(
            code=code,
            name=name,
            entry_date=datetime.now().strftime("%Y-%m-%d"),
            entry_price=entry_price,
            shares=shares,
            stop_price=stop_price,
            peak_price=entry_price,
            highest_price=entry_price,
        )

        self.positions[code] = position
        self.capital -= cost

        self.trades_log.append({
            "date": position.entry_date,
            "action": "buy",
            "code": code,
            "name": name,
            "price": entry_price,
            "shares": shares,
            "cost": cost,
            "remaining_capital": self.capital,
        })

        logger.info(f"[{code}] 开仓: {shares}股@{entry_price:.2f}，止损{stop_price:.2f}")
        return position

    def update_position(self, code: str, current_price: float) -> Optional[Position]:
        """Update position with current price and check stop loss."""
        if code not in self.positions:
            return None

        pos = self.positions[code]
        pos.current_price = current_price

        # Track highest price for trailing stop
        if current_price > pos.peak_price:
            pos.peak_price = current_price

        pos.pnl_pct = (current_price - pos.entry_price) / pos.entry_price * 100
        pos.pnl_amount = (current_price - pos.entry_price) * pos.shares

        # Highest return since entry
        if current_price > pos.highest_price:
            pos.highest_price = current_price
            pos.highest_return = (current_price - pos.entry_price) / pos.entry_price * 100

        return pos

    def close_position(self, code: str, reason: str = "") -> Optional[Position]:
        """Close a position."""
        if code not in self.positions:
            return None

        pos = self.positions.pop(code)
        pos.status = "closed"

        close_value = pos.current_price * pos.shares if pos.current_price > 0 else 0
        self.capital += close_value

        pos.pnl_pct = (pos.current_price - pos.entry_price) / pos.entry_price * 100
        pos.pnl_amount = (pos.current_price - pos.entry_price) * pos.shares

        self.closed_positions.append(pos)

        self.trades_log.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "action": "sell",
            "code": code,
            "name": pos.name,
            "price": pos.current_price,
            "shares": pos.shares,
            "value": close_value,
            "pnl_pct": round(pos.pnl_pct, 2),
            "pnl_amount": round(pos.pnl_amount, 2),
            "reason": reason,
            "remaining_capital": self.capital,
        })

        logger.info(f"[{code}] 平仓: 盈亏{pos.pnl_pct:.2f}%({pos.pnl_amount:.2f})，原因:{reason}")
        return pos

    def check_stops(self) -> list[str]:
        """Check all open positions for stop loss hits."""
        hit = []
        for code, pos in list(self.positions.items()):
            if pos.current_price <= pos.stop_price:
                self.close_position(code, "止损触发")
                hit.append(code)
        return hit

    def get_summary(self) -> dict:
        """Get portfolio summary."""
        total_value = self.capital + sum(
            p.current_price * p.shares
            for p in self.positions.values()
            if p.current_price > 0
        )

        total_pnl = total_value - self.initial_capital
        total_pnl_pct = (total_value - self.initial_capital) / self.initial_capital * 100

        return {
            "initial_capital": round(self.initial_capital, 2),
            "current_capital": round(self.capital, 2),
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "open_positions": len(self.positions),
            "closed_positions": len(self.closed_positions),
            "total_trades": len(self.trades_log),
            "used_margin": round(total_value - self.capital, 2) if total_value > self.capital else 0,
            "cash_ratio": round(self.capital / total_value * 100, 1) if total_value > 0 else 100,
        }
