"""
Minervini Screener v1.0 - SEPA Backtest Engine
Monthly-rebalance backtesting for Minervini SEPA strategy.
"""
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import numpy as np

from config.loader import settings
from core.logging_setup import get_logger
from data.downloader import DataDownloader
from data.database import async_session_factory, Stock
from indicators.ma import calculate_ma
from indicators.atr import calculate_atr
from indicators.volume import calculate_volume_ma
from indicators.bollinger import calculate_bollinger
from core.rs_rating import RSRatingEngine
from core.sepa import run_sepa
from sqlalchemy import select

logger = get_logger(__name__)


class SEPABacktest:
    """SEPA strategy backtest engine with monthly rebalance."""

    def __init__(
        self,
        market: str = "US",
        start_date: str = "2024-01-01",
        end_date: str = "",
        initial_capital: float = 100000.0,
        commission_pct: float = 0.001,
        slippage_pct: float = 0.001,
        max_positions: int = 10,
        symbols: Optional[list[str]] = None,
    ):
        self.market = market
        self.start_date = start_date
        self.end_date = end_date or datetime.now().strftime("%Y-%m-%d")
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.max_positions = max_positions
        self.symbols = symbols

        self.downloader = DataDownloader()
        self.cash = initial_capital
        self.positions: dict[str, dict] = {}  # symbol -> position info
        self.trades: list[dict] = []
        self.equity_curve: list[dict] = []

    async def run(self) -> dict:
        """Execute the backtest and return results."""
        logger.info(
            "Backtest start",
            market=self.market,
            period=f"{self.start_date} ~ {self.end_date}",
            capital=self.initial_capital,
        )

        # 1. Load stock universe
        stocks = await self._load_universe()
        if not stocks:
            return self._result("没有可用的股票数据")

        logger.info(f"Universe: {len(stocks)} stocks")

        # 2. Pre-load all price data + calculate indicators (rolling → point-in-time valid)
        stock_dfs: dict[str, tuple] = {}
        for stock in stocks:
            try:
                df = await self.downloader._load_stock_data(stock.symbol, stock.market)
                if df is None or df.empty or len(df) < 60:
                    continue
                df = calculate_ma(df)
                df = calculate_atr(df)
                df = calculate_volume_ma(df)
                df = calculate_bollinger(df)
                stock_dfs[stock.symbol] = (stock, df)
            except Exception as e:
                logger.warning(f"load fail {stock.symbol}: {e}")

        if not stock_dfs:
            return self._result("没有足够的历史数据")

        # 3. Pre-compute RS ratings (batch, using full data)
        raw = {sym: df for sym, (stk, df) in stock_dfs.items()}
        rs_engine = RSRatingEngine()
        rs_results = rs_engine.compute_batch(raw)

        # 4. Build trading calendar — union of all dates in range
        all_dates: set = set()
        for sym, (stk, df) in stock_dfs.items():
            for d in df.index:
                ds = str(d) if not hasattr(d, 'strftime') else d.strftime('%Y-%m-%d')
                if self.start_date <= ds <= self.end_date:
                    all_dates.add(d)
        trading_days = sorted(all_dates)
        if not trading_days:
            return self._result(f"日期范围 {self.start_date}~{self.end_date} 内无交易日")

        # 5. Main loop — daily equity tracking + monthly rebalance
        last_rebalance_month = -1
        rebalance_count = 0

        for current_date in trading_days:
            date_str = self._fmt(current_date)
            dt_ts = pd.Timestamp(current_date) if not isinstance(current_date, pd.Timestamp) else current_date

            # --- Stop-loss check (daily) ---
            self._check_stops(current_date, stock_dfs, date_str)

            # --- Rebalance on first trading day of each month ---
            this_month = dt_ts.month
            if this_month != last_rebalance_month:
                last_rebalance_month = this_month
                rebalance_count += 1
                await self._rebalance(current_date, stock_dfs, rs_results, date_str)

            # --- Record portfolio value ---
            self._record_equity(current_date, stock_dfs)

        # 6. Close remaining positions at end
        last_date_str = self._fmt(trading_days[-1])
        for sym in list(self.positions.keys()):
            df = stock_dfs[sym][1]
            px = float(df.iloc[-1]["close"])
            self._close_position(sym, px, last_date_str, "回测结束平仓")

        self._record_equity(trading_days[-1], stock_dfs)

        logger.info(f"Backtest done: {rebalance_count} rebalances, {len(self.trades)} trades")

        # 7. Compute metrics
        return self._result(metrics=self._calc_metrics())

    @staticmethod
    def _fmt(d) -> str:
        """Safely convert a date/timestamp to YYYY-MM-DD string."""
        if hasattr(d, 'strftime'):
            return d.strftime('%Y-%m-%d')
        return str(d)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load_universe(self) -> list:
        async with async_session_factory() as session:
            q = select(Stock).where(Stock.is_active == True)
            if self.symbols:
                q = q.where(Stock.symbol.in_(self.symbols))
            elif self.market and self.market != "all":
                q = q.where(Stock.market == self.market)
            r = await session.execute(q)
            return list(r.scalars().all())

    def _check_stops(self, current_date: pd.Timestamp, stock_dfs: dict, date_str: str):
        for sym in list(self.positions.keys()):
            if sym not in stock_dfs:
                continue
            df = stock_dfs[sym][1]
            past = df[df.index <= current_date]
            if past.empty:
                continue
            price = float(past.iloc[-1]["close"])
            pos = self.positions[sym]
            stop = pos.get("stop_loss", 0)
            if stop > 0 and price <= stop:
                self._close_position(sym, price, date_str, "止损")

    async def _rebalance(
        self,
        current_date: pd.Timestamp,
        stock_dfs: dict,
        rs_results: dict,
        date_str: str,
    ):
        """Monthly rebalance: scan universe, rank, enter/exit positions.

        If `self.symbols` (custom pool) is set, skip SEPA filtering — just
        buy & hold / equal-weight the selected stocks. Otherwise run full
        SEPA screening across the universe.
        """
        candidates: list[dict] = []

        if self.symbols:
            # ── Custom pool mode: equal-weight all pool stocks, no filtering ──
            for sym, (stock, df_full) in stock_dfs.items():
                try:
                    df_slice = df_full[df_full.index <= current_date].copy()
                    if df_slice.empty:
                        continue
                    price = float(df_slice.iloc[-1]["close"])
                    if price <= 0:
                        continue
                    candidates.append({
                        "symbol": sym,
                        "score": 50,  # equal weight
                        "price": price,
                        "stop_loss": price * 0.85,  # default trailing stop
                        "stage2": True,
                        "rs_rating": 0,
                    })
                except Exception:
                    continue
        else:
            # ── Full SEPA screening mode ──
            for sym, (stock, df_full) in stock_dfs.items():
                try:
                    df_slice = df_full[df_full.index <= current_date].copy()
                    if len(df_slice) < 60:
                        continue

                    rs = rs_results.get(sym, {})
                    result = run_sepa(
                        df=df_slice,
                        code=sym,
                        name=stock.name or "",
                        check_breakout=True,
                        rs_result=rs,
                    )

                    if result.signal == "buy":
                        bp = (
                            (result.pattern or {}).get("buy_point")
                            or (result.pattern or {}).get("pivot_price")
                            or float(df_slice.iloc[-1]["close"])
                        )
                        sp = (result.stop_loss or {}).get("stop_price", 0)
                        candidates.append({
                            "symbol": sym,
                            "score": result.score,
                            "price": bp,
                            "stop_loss": sp,
                            "stage2": result.stage2,
                            "rs_rating": result.rs_rating_val,
                        })
                except Exception:
                    continue

        if not candidates:
            return

        # Rank by score descending
        candidates.sort(key=lambda x: x["score"], reverse=True)
        top = candidates[: self.max_positions]
        top_syms = {c["symbol"] for c in top}

        # Sell positions that fell out of top N
        for sym in list(self.positions.keys()):
            if sym not in top_syms:
                df = stock_dfs.get(sym)
                if df:
                    past = df[1][df[1].index <= current_date]
                    if not past.empty:
                        self._close_position(
                            sym, float(past.iloc[-1]["close"]), date_str, "调仓"
                        )
                if sym in self.positions:
                    del self.positions[sym]

        # Buy top candidates (skip if already holding)
        budget_per = self.cash / max(len(top), 1) * 0.95
        for c in top:
            if c["symbol"] in self.positions:
                continue
            if len(self.positions) >= self.max_positions:
                break
            self._open_position(c, date_str, budget_per)

    def _open_position(self, c: dict, date_str: str, budget: float):
        """Open a new long position."""
        price = c["price"]
        if price <= 0:
            return
        buy_price = price * (1 + self.slippage_pct)
        total_cost = buy_price * (1 + self.commission_pct)
        shares = max(1, int(budget / total_cost))
        cost = shares * total_cost

        if cost > self.cash or cost <= 0:
            shares = max(1, int(self.cash * 0.5 / total_cost))
            cost = shares * total_cost
            if cost > self.cash or cost <= 0:
                return

        self.cash -= cost
        self.positions[c["symbol"]] = {
            "shares": shares,
            "entry_price": buy_price,
            "entry_date": date_str,
            "stop_loss": c.get("stop_loss", buy_price * 0.85),
            "cost_basis": cost,
        }
        self.trades.append({
            "symbol": c["symbol"],
            "entry_date": date_str,
            "entry_price": round(buy_price, 2),
            "shares": shares,
            "exit_date": None,
            "exit_price": None,
            "pnl": None,
            "pnl_pct": None,
            "exit_reason": "",
        })

    def _close_position(self, symbol: str, price: float, date_str: str, reason: str):
        """Close an existing position."""
        pos = self.positions.get(symbol)
        if not pos:
            return

        sell_price = price * (1 - self.slippage_pct)
        proceeds = sell_price * pos["shares"] * (1 - self.commission_pct)
        pnl = proceeds - pos["cost_basis"]
        pnl_pct = (pnl / pos["cost_basis"]) * 100 if pos["cost_basis"] else 0

        self.cash += max(proceeds, 0)

        # Update trade record
        for t in reversed(self.trades):
            if t["symbol"] == symbol and t["exit_date"] is None:
                t["exit_date"] = date_str
                t["exit_price"] = round(sell_price, 2)
                t["pnl"] = round(pnl, 2)
                t["pnl_pct"] = round(pnl_pct, 2)
                t["exit_reason"] = reason
                break

        if symbol in self.positions:
            del self.positions[symbol]

    def _record_equity(self, current_date: pd.Timestamp, stock_dfs: dict):
        """Record daily portfolio value."""
        pos_value = 0.0
        for sym, pos in self.positions.items():
            if sym in stock_dfs:
                df = stock_dfs[sym][1]
                past = df[df.index <= current_date]
                if not past.empty:
                    pos_value += float(past.iloc[-1]["close"]) * pos["shares"]

        total = round(self.cash + pos_value, 2)
        self.equity_curve.append({"date": self._fmt(current_date), "value": total})

    def _calc_metrics(self) -> dict:
        """Calculate performance metrics from trades and equity curve."""
        values = [e["value"] for e in self.equity_curve]
        start_v = self.initial_capital
        end_v = values[-1] if values else start_v

        total_return = ((end_v - start_v) / start_v) * 100 if start_v else 0

        # CAGR — only annualize if period >= 1 year, else return total_return
        try:
            d1 = datetime.strptime(self.start_date, "%Y-%m-%d")
            d2 = datetime.strptime(self.end_date, "%Y-%m-%d")
            days = (d2 - d1).days
            if days >= 365:
                years = days / 365.25
                cagr = ((end_v / max(start_v, 0.01)) ** (1 / years) - 1) * 100
            else:
                cagr = total_return
        except Exception:
            cagr = 0.0

        # Max drawdown
        peak = values[0] if values else start_v
        max_dd = 0.0
        for v in values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak * 100 if peak else 0
            max_dd = max(max_dd, dd)

        # Trade analysis
        closed = [t for t in self.trades if t["exit_date"] is not None]
        total_trades = len(closed)
        winners = [t for t in closed if t["pnl"] is not None and t["pnl"] > 0]
        losers = [t for t in closed if t["pnl"] is not None and t["pnl"] <= 0]
        win_rate = (len(winners) / total_trades * 100) if total_trades else 0

        total_win = sum(t["pnl"] for t in winners) if winners else 0
        total_loss = abs(sum(t["pnl"] for t in losers)) if losers else 0
        avg_win = np.mean([t["pnl"] for t in winners]) if winners else 0
        avg_loss = abs(np.mean([t["pnl"] for t in losers])) if losers else 0
        profit_factor = (total_win / total_loss) if total_loss > 0 else (total_win if total_win > 0 else 0)

        # Sharpe (daily returns)
        daily_ret = []
        for i in range(1, len(values)):
            r = (values[i] - values[i - 1]) / values[i - 1] if values[i - 1] else 0
            daily_ret.append(r)
        sharpe = 0.0
        if daily_ret and np.std(daily_ret) > 0:
            sharpe = (np.mean(daily_ret) / np.std(daily_ret)) * np.sqrt(252)

        # Avg holding days
        avg_holding = 0.0
        if closed:
            days = []
            for t in closed:
                try:
                    ed = datetime.strptime(t["entry_date"], "%Y-%m-%d")
                    xd = datetime.strptime(t["exit_date"], "%Y-%m-%d")
                    days.append((xd - ed).days)
                except Exception:
                    pass
            avg_holding = np.mean(days) if days else 0

        return {
            "total_return": round(float(total_return), 2),
            "cagr": round(float(cagr), 2),
            "sharpe": round(float(sharpe), 2),
            "max_drawdown": round(float(max_dd), 2),
            "win_rate": round(float(win_rate), 1),
            "total_trades": int(total_trades),
            "profit_factor": round(float(profit_factor), 2),
            "avg_win": round(float(avg_win), 2),
            "avg_loss": round(float(avg_loss), 2),
            "avg_holding_days": round(float(avg_holding), 1),
        }

    def _result(self, message="", metrics=None) -> dict:
        return {
            "message": message,
            "config": {
                "market": self.market,
                "start_date": self.start_date,
                "end_date": self.end_date,
                "initial_capital": self.initial_capital,
                "commission_pct": self.commission_pct,
                "slippage_pct": self.slippage_pct,
                "max_positions": self.max_positions,
                "symbols": self.symbols,
            },
            "metrics": metrics or {
                "total_return": 0, "cagr": 0, "sharpe": 0,
                "max_drawdown": 0, "win_rate": 0, "total_trades": 0,
                "profit_factor": 0, "avg_win": 0, "avg_loss": 0,
                "avg_holding_days": 0,
            },
            "trades": self.trades,
            "equity_curve": self.equity_curve,
        }
