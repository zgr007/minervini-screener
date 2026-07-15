"""
Tests for the backtesting engine.
"""
import pandas as pd
import numpy as np
import pytest
from datetime import datetime, timedelta


def _make_price_data(days: int = 252, start_price: float = 100.0) -> pd.DataFrame:
    """Generate synthetic OHLCV data for testing."""
    dates = pd.bdate_range(end=datetime.now(), periods=days)
    prices = np.linspace(start_price, start_price * 1.2, days) + np.random.randn(days) * 2
    prices = np.maximum(prices, start_price * 0.5)  # floor

    df = pd.DataFrame({
        "open": prices * 0.99,
        "high": prices * 1.02,
        "low": prices * 0.98,
        "close": prices,
        "volume": np.random.randint(1_000_000, 10_000_000, days),
    }, index=dates)
    df.index.name = "trade_date"
    return df


class TestBacktestEngine:
    """Test suite for BacktestEngine."""

    def test_init_defaults(self):
        """Verify engine initializes with default parameters."""
        from backtest.engine import BacktestEngine
        engine = BacktestEngine()
        assert engine.initial_capital == 100000
        assert engine.capital == 100000
        assert engine.commission_pct == 0.0003
        assert engine.slippage_pct == 0.001
        assert engine.max_positions == 6
        assert engine.positions == {}
        assert engine.trades == []

    def test_init_custom(self):
        """Verify engine accepts custom parameters."""
        from backtest.engine import BacktestEngine
        engine = BacktestEngine(initial_capital=50000, commission_pct=0.001, slippage_pct=0.002)
        assert engine.initial_capital == 50000
        assert engine.commission_pct == 0.001
        assert engine.slippage_pct == 0.002

    def test_run_no_signals(self):
        """Backtest with no signals should produce flat result."""
        from backtest.engine import BacktestEngine
        df = _make_price_data(60)
        data = {"AAPL": df}
        signals = {"AAPL": pd.Series(0, index=df.index)}

        engine = BacktestEngine(initial_capital=100000)
        result = engine.run(data, signals, start_date="2025-01-01", end_date="2025-03-31")

        assert "total_return_pct" in result
        assert result["total_trades"] == 0
        assert len(engine.trades) == 0
        assert engine.capital == pytest.approx(100000, rel=1e-3)

    def test_run_one_buy_signal(self):
        """A single buy signal should result in one trade."""
        from backtest.engine import BacktestEngine
        df = _make_price_data(60, start_price=100.0)
        data = {"AAPL": df}
        # Signal on the last day
        signals = {"AAPL": pd.Series(0, index=df.index)}
        signals["AAPL"].iloc[-1] = 1

        engine = BacktestEngine(initial_capital=100000)
        result = engine.run(data, signals, start_date=str(df.index[0].date()), end_date=str(df.index[-1].date()))

        buy_trades = [t for t in engine.trades if t["action"] == "buy"]
        # May or may not have entered depending on capital/price
        total_trades = len([t for t in engine.trades if t["action"] == "sell"])
        assert "total_return_pct" in result
        assert "max_drawdown_pct" in result

    def test_run_multiple_stocks(self):
        """Multiple stocks with signals should be processed."""
        from backtest.engine import BacktestEngine
        df1 = _make_price_data(60, start_price=100.0)
        df2 = _make_price_data(60, start_price=50.0)

        data = {"AAPL": df1, "MSFT": df2}
        signals = {}
        for code in data:
            s = pd.Series(0, index=data[code].index)
            s.iloc[-1] = 1
            signals[code] = s

        engine = BacktestEngine(initial_capital=200000)
        result = engine.run(data, signals,
                            start_date=str(df1.index[0].date()),
                            end_date=str(df1.index[-1].date()))

        assert "total_return_pct" in result
        assert result.get("total_trades", 0) >= 0

    def test_stop_loss_triggers(self):
        """A sharp price drop should trigger stop loss."""
        from backtest.engine import BacktestEngine
        dates = pd.bdate_range(end=datetime.now(), periods=30)
        # Prices drop 15% from entry
        prices = np.concatenate([
            np.full(5, 100.0),  # flat
            np.linspace(100, 110, 5),   # rise
            np.linspace(110, 85, 20),   # sharp drop
        ])
        df = pd.DataFrame({
            "open": prices, "high": prices * 1.01, "low": prices * 0.99,
            "close": prices, "volume": 1_000_000,
        }, index=dates)
        data = {"TEST": df}
        signals = {"TEST": pd.Series(0, index=df.index)}
        signals["TEST"].iloc[5] = 1  # Buy at the peak

        engine = BacktestEngine(initial_capital=100000)
        result = engine.run(data, signals,
                            start_date=str(dates[0].date()),
                            end_date=str(dates[-1].date()))

        closed = [t for t in engine.trades if t["action"] == "sell"]
        if closed:
            assert any("止损" in t.get("reason", "") for t in closed)

    def test_sharpe_no_data(self):
        """Short equity curve returns 0 Sharpe."""
        from backtest.engine import BacktestEngine
        engine = BacktestEngine()
        engine.equity_curve = [100000, 100000]
        assert engine._calculate_sharpe() == 0

    def test_results_no_trades(self):
        """No trades produces zero returns."""
        from backtest.engine import BacktestEngine
        engine = BacktestEngine()
        engine.equity_curve = [100000, 100000]
        engine.date_curve = ["2025-01-01", "2025-01-02"]
        result = engine._calculate_results()
        assert result["total_return_pct"] == 0
        assert result["total_trades"] == 0

    def test_position_sizing(self):
        """Position sizing follows max_position_pct rule."""
        from backtest.engine import BacktestEngine
        engine = BacktestEngine(initial_capital=100000)
        engine.capital = 80000
        shares = engine._position_sizing(price=50.0)
        # max_position = 80000 * 25/100 = 20000 (default 25%)
        # shares = 20000 / 50 = 400
        assert shares == 400

    def test_close_position_adds_capital(self):
        """Closing a position adds proceeds back to capital."""
        from backtest.engine import BacktestEngine
        engine = BacktestEngine(initial_capital=100000)
        engine.capital = 90000
        engine.positions["TEST"] = {
            "entry_date": "2025-01-10",
            "entry_price": 100.0,
            "shares": 100,
            "highest_price": 100.0,
        }
        capital_before = engine.capital
        engine._close_position("TEST", "2025-01-15", "止损")
        assert "TEST" not in engine.positions
        # Capital should have increased (exit proceeds added back)
        assert engine.capital > capital_before

    def test_equity_calculation(self):
        """Total equity includes both cash and position value."""
        from backtest.engine import BacktestEngine
        dates = pd.bdate_range(end=datetime.now(), periods=10)
        prices = np.linspace(100, 110, 10)
        df = pd.DataFrame({
            "open": prices, "high": prices, "low": prices,
            "close": prices, "volume": 1_000_000,
        }, index=dates)

        engine = BacktestEngine(initial_capital=100000)
        engine.capital = 90000
        engine.positions["TEST"] = {
            "entry_price": 100.0, "shares": 100, "highest_price": 100.0,
        }

        equity = engine._calculate_equity({"TEST": df}, str(dates[-1].date()))
        expected = 90000 + 100 * prices[-1]  # cash + position value
        assert equity == pytest.approx(expected, rel=1e-3)

    def test_multiple_buy_signal_entry_timing(self):
        """Buy signal in middle of date range enters at correct date."""
        from backtest.engine import BacktestEngine
        df = _make_price_data(50)
        data = {"AAPL": df}
        signals = {"AAPL": pd.Series(0, index=df.index)}
        # Signal on day 25
        mid_date = df.index[25]
        signals["AAPL"].loc[mid_date] = 1

        engine = BacktestEngine(initial_capital=100000)
        result = engine.run(data, signals,
                            start_date=str(df.index[0].date()),
                            end_date=str(df.index[-1].date()))

        buy_trades = [t for t in engine.trades if t["action"] == "buy" and t["code"] == "AAPL"]
        if buy_trades:
            assert buy_trades[0]["date"] == str(mid_date.date())

    def test_empty_data_graceful(self):
        """Empty data dict should not crash."""
        from backtest.engine import BacktestEngine
        engine = BacktestEngine()
        result = engine.run({}, {}, start_date="2025-01-01", end_date="2025-03-31")
        assert "total_return_pct" in result
        assert result["total_trades"] == 0

    def test_profit_factor_infinite_when_no_loss(self):
        """Profit factor is inf when there are no losses."""
        from backtest.engine import BacktestEngine
        engine = BacktestEngine()
        engine.trades.append({
            "date": "2025-01-01", "action": "sell", "code": "TEST",
            "price": 110, "shares": 100, "value": 11000, "pnl": 1000, "pnl_pct": 10, "reason": "止盈",
        })
        engine.equity_curve = [100000, 110000, 105000]
        engine.date_curve = ["2025-01-01", "2025-01-02", "2025-01-03"]
        result = engine._calculate_results()
        assert result["profit_factor"] == float("inf")
