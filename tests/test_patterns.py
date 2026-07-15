"""Tests for pattern detection modules."""
import pytest
import pandas as pd
import numpy as np

from core.vcp import detect_vcp
from core.flat_base import detect_flat_base
from core.double_bottom import detect_double_bottom
from core.boll import detect_bollinger_signal


@pytest.fixture
def volatile_df():
    """Create a DataFrame with volatility contraction pattern."""
    n = 250
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    np.random.seed(42)
    close = np.ones(n) * 100
    # Add some volatility for VCP detection
    for i in range(1, n):
        close[i] = close[i-1] + np.random.randn() * 3
    close = np.maximum.accumulate(close) * 0.8 + close * 0.2  # blend with trend

    return pd.DataFrame({
        "open": close * 0.998,
        "high": close * 1.01,
        "low": close * 0.99,
        "close": close,
        "adjusted_close": close,
        "volume": np.random.randint(1000000, 10000000, n),
    }, index=dates)


@pytest.fixture
def flat_df():
    """Create a DataFrame with a flat base section."""
    n = 200
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    np.random.seed(42)
    # First half: uptrend, second half: flat
    trend = np.concatenate([
        np.linspace(80, 120, n//2),
        np.ones(n//2) * 120 + np.random.randn(n//2) * 2,
    ])
    return pd.DataFrame({
        "open": trend * 0.998,
        "high": trend * 1.008,
        "low": trend * 0.992,
        "close": trend,
        "adjusted_close": trend,
        "volume": np.random.randint(1000000, 10000000, n),
    }, index=dates)


def test_detect_vcp(volatile_df):
    """Test VCP detection."""
    result = detect_vcp(volatile_df)
    assert isinstance(result, dict)
    assert "detected" in result
    assert "reason" in result


def test_detect_vcp_insufficient():
    """Test VCP with insufficient data."""
    empty = pd.DataFrame()
    result = detect_vcp(empty)
    assert result["detected"] is False
    assert "数据不足" in result.get("reason", "")


def test_detect_vcp_no_data():
    """Test VCP with no data at all."""
    result = detect_vcp(pd.DataFrame())
    assert result["detected"] is False


def test_detect_flat_base(flat_df):
    """Test flat base detection."""
    result = detect_flat_base(flat_df)
    assert isinstance(result, dict)
    assert "detected" in result
    assert "reason" in result


def test_detect_flat_base_insufficient():
    """Test flat base with insufficient data."""
    result = detect_flat_base(pd.DataFrame({"close": [100]}))
    assert result["detected"] is False


def test_detect_double_bottom(volatile_df):
    """Test double bottom detection."""
    result = detect_double_bottom(volatile_df)
    assert isinstance(result, dict)
    assert "detected" in result
    assert "reason" in result


def test_detect_double_bottom_empty():
    """Test double bottom with empty data."""
    result = detect_double_bottom(pd.DataFrame())
    assert result["detected"] is False


def test_detect_bollinger_signal(volatile_df):
    """Test Bollinger signal detection."""
    result = detect_bollinger_signal(volatile_df)
    assert isinstance(result, dict)
    assert "detected" in result or "reason" in result
