"""Tests for technical indicators."""
import pytest
import pandas as pd
import numpy as np

from indicators.ma import calculate_ma, check_ma_alignment
from indicators.atr import calculate_atr
from indicators.volume import calculate_volume_ma, calculate_volume_ratio, detect_volume_spike
from indicators.bollinger import calculate_bollinger, detect_bollinger_buy_signal
from indicators.rs import calculate_52w_high_low, calculate_rs_rating, get_rs_grade


@pytest.fixture
def sample_df():
    """Create a sample OHLCV DataFrame for testing."""
    np.random.seed(42)
    n = 250
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    base = 100 + np.cumsum(np.random.randn(n) * 0.5)
    return pd.DataFrame({
        "open": base * (1 + np.random.randn(n) * 0.005),
        "high": base * (1 + np.random.randn(n) * 0.01),
        "low": base * (1 + np.random.randn(n) * 0.01),
        "close": base,
        "adjusted_close": base,
        "volume": np.random.randint(1000000, 10000000, n),
    }, index=dates)


def test_calculate_ma(sample_df):
    """Test moving average calculation."""
    df = calculate_ma(sample_df)
    assert "ma_50" in df.columns
    assert "ma_150" in df.columns
    assert "ma_200" in df.columns
    assert not df["ma_50"].iloc[50:].isna().all()
    assert not df["ma_150"].iloc[150:].isna().all()
    assert not df["ma_200"].iloc[200:].isna().all()
    assert pd.isna(df["ma_50"].iloc[0])


def test_calculate_ma_custom_periods(sample_df):
    """Test MA with custom periods."""
    df = calculate_ma(sample_df, periods=[20])
    assert "ma_20" in df.columns


def test_check_ma_alignment(sample_df):
    """Test MA alignment check."""
    df = calculate_ma(sample_df)
    result = check_ma_alignment(df)
    assert isinstance(result, dict)


def test_calculate_atr(sample_df):
    """Test ATR calculation."""
    df = calculate_atr(sample_df)
    assert "atr" in df.columns
    assert not df["atr"].iloc[14:].isna().all()
    assert pd.isna(df["atr"].iloc[0])
    assert (df["atr"].dropna() > 0).all()


def test_calculate_volume_ma(sample_df):
    """Test volume MA calculation."""
    df = calculate_volume_ma(sample_df)
    assert "volume_ma_50" in df.columns
    assert not df["volume_ma_50"].iloc[50:].isna().all()


def test_calculate_volume_ratio(sample_df):
    """Test volume ratio calculation."""
    ratio = calculate_volume_ratio(sample_df)
    assert isinstance(ratio, pd.Series)
    assert len(ratio) == len(sample_df)


def test_detect_volume_spike(sample_df):
    """Test volume spike detection."""
    spikes = detect_volume_spike(sample_df)
    assert isinstance(spikes, pd.Series)
    assert spikes.dtype == bool
    assert len(spikes) == len(sample_df)


def test_calculate_bollinger(sample_df):
    """Test Bollinger Band calculation."""
    df = calculate_bollinger(sample_df)
    assert "boll_upper" in df.columns
    assert "boll_mid" in df.columns
    assert "boll_lower" in df.columns
    assert "boll_width" in df.columns
    assert (df["boll_upper"].dropna() >= df["boll_mid"].dropna()).all()
    assert (df["boll_mid"].dropna() >= df["boll_lower"].dropna()).all()


def test_bollinger_buy_signal(sample_df):
    """Test Bollinger Band buy signal detection."""
    df = calculate_bollinger(sample_df)
    signal = detect_bollinger_buy_signal(df)
    assert isinstance(signal, dict)
    assert "detected" in signal
    assert "reason" in signal


def test_calculate_52w_high_low(sample_df):
    """Test 52-week high/low calculation."""
    result = calculate_52w_high_low(sample_df)
    assert isinstance(result, dict)
    assert "high_52w" in result
    assert "low_52w" in result


def test_get_rs_grade():
    """Test RS grade mapping."""
    assert get_rs_grade(95) == "A"
    assert get_rs_grade(85) == "A"
    assert get_rs_grade(70) == "B"
    assert get_rs_grade(50) == "C"
    assert get_rs_grade(30) == "D"
    assert get_rs_grade(10) == "F"


def test_empty_df():
    """Test indicators with empty DataFrame."""
    empty = pd.DataFrame()
    assert calculate_ma(empty).empty


def test_single_row():
    """Test indicators with single row."""
    single = pd.DataFrame({
        "open": [100], "high": [101], "low": [99], "close": [100], "volume": [1000000],
    })
    result = calculate_ma(single)
    assert "ma_50" in result.columns
    assert pd.isna(result["ma_50"].iloc[0])
