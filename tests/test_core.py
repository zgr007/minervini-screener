"""Tests for core algorithm modules."""
import pytest
import pandas as pd
import numpy as np

from core.stage2 import check_stage2
from core.rs_rating import RSRatingEngine
from core.scoring import calculate_total_score, calculate_fundamental_score, calculate_institutional_score


@pytest.fixture
def uptrend_df():
    """Create an uptrending stock DataFrame with all required columns."""
    np.random.seed(42)
    n = 250
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    trend = np.linspace(100, 180, n)
    noise = np.random.randn(n) * 2
    close = trend + noise
    return pd.DataFrame({
        "open": close * 0.99,
        "high": close * 1.01,
        "low": close * 0.99,
        "close": close,
        "adjusted_close": close,
        "volume": np.random.randint(1000000, 10000000, n),
    }, index=dates)


@pytest.fixture
def downtrend_df():
    """Create a downtrending stock DataFrame."""
    np.random.seed(42)
    n = 250
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    trend = np.linspace(150, 80, n)
    noise = np.random.randn(n) * 2
    close = trend + noise
    return pd.DataFrame({
        "open": close * 0.99,
        "high": close * 1.01,
        "low": close * 0.99,
        "close": close,
        "adjusted_close": close,
        "volume": np.random.randint(1000000, 10000000, n),
    }, index=dates)


def test_check_stage2_uptrend(uptrend_df):
    """Test Stage 2 detection with uptrending stock."""
    result = check_stage2(uptrend_df)
    assert isinstance(result, dict)
    assert "passed" in result


def test_check_stage2_downtrend(downtrend_df):
    """Test Stage 2 detection with downtrending stock."""
    result = check_stage2(downtrend_df)
    assert isinstance(result, dict)
    assert "passed" in result
    assert "price" in result


def test_check_stage2_insufficient_data():
    """Test Stage 2 with insufficient data."""
    result = check_stage2(pd.DataFrame())
    assert result["passed"] is False

    # Must include all required columns
    short = pd.DataFrame({
        "open": [100]*100, "high": [101]*100, "low": [99]*100,
        "close": range(100, 200), "adjusted_close": range(100, 200),
        "volume": [1000000]*100,
    })
    result = check_stage2(short)
    assert result["passed"] is False


def test_rs_rating_engine(uptrend_df):
    """Test RS rating calculation."""
    engine = RSRatingEngine()
    result = engine.compute_rs("TEST", uptrend_df)
    assert isinstance(result, dict)
    assert "rs_percentile" in result
    assert "rs_grade" in result
    assert "period_returns" in result
    assert 0 <= result["rs_percentile"] <= 100


def test_rs_rating_empty():
    """Test RS rating with empty data."""
    engine = RSRatingEngine()
    result = engine.compute_rs("TEST", pd.DataFrame())
    assert result["rs_percentile"] == 50.0


def test_rs_ranking():
    """Test RS ranking across stocks."""
    engine = RSRatingEngine()
    mock_data = {
        "000001": pd.DataFrame({"close": range(100, 200), "adjusted_close": range(100, 200)}),
        "000002": pd.DataFrame({"close": range(100, 160), "adjusted_close": range(100, 160)}),
    }
    rankings = []
    for code, df in mock_data.items():
        r = engine.compute_rs(code, df)
        rankings.append((code, r["rs_percentile"]))
    rankings.sort(key=lambda x: x[1], reverse=True)
    assert len(rankings) == 2


def test_calculate_total_score():
    """Test total score calculation."""
    stage2 = {"passed": True, "reasons": [], "details": {}, "price": 150.0}
    rs = {"rs_percentile": 90, "rs_grade": "A", "period_returns": {"3m": 15}}
    fund = {"total_score": 8, "passed": True, "details": ""}
    inst = {"total_score": 4, "max_score": 5, "details": ""}

    result = calculate_total_score(stage2, rs, fund, inst)
    assert isinstance(result, dict)
    assert "total_score" in result
    assert result["total_score"] > 0


def test_calculate_total_score_minimal():
    """Test total score with all failing inputs."""
    stage2 = {"passed": False, "reasons": ["未通过"], "details": {}, "price": 80.0}
    rs = {"rs_percentile": 30, "rs_grade": "D", "period_returns": {}}
    fund = {"total_score": 0, "passed": False, "details": ""}
    inst = {"total_score": 0, "max_score": 5, "details": ""}

    result = calculate_total_score(stage2, rs, fund, inst)
    assert result["total_score"] < 60


def test_calculate_fundamental_score():
    """Test fundamental score calculation."""
    fund = {
        "eps_growth_yoy": 35.0,
        "revenue_growth_yoy": 15.0,
        "roe": 20.0,
        "catalyst_note": "新产品发布",
    }
    result = calculate_fundamental_score(fund)
    assert isinstance(result, dict)
    assert "total_score" in result


def test_calculate_institutional_score():
    """Test institutional score calculation."""
    inst = {
        "holder_count_change_pct": 0.1,
        "avg_position_change_pct": 0.08,
        "volume_accumulation": 2.0,
    }
    result = calculate_institutional_score(inst)
    assert isinstance(result, dict)
    assert "total_score" in result
