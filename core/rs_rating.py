"""
Minervini Screener v1.0 - RS (Relative Strength) Rating Engine
Computes percentile-based relative strength rankings.
"""
from typing import List, Optional, Dict
import pandas as pd
import numpy as np

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


class RSRatingEngine:
    """Computes RS ratings for stocks relative to their market universe."""

    def __init__(self, config: Optional[object] = None):
        self.config = config or settings.indicators.rs
        self.periods_months = self.config.periods_months
        self.weights = self.config.weights
        self.min_percentile = settings.screening.rs.get("min_percentile", 80)

    def compute_rs(
        self,
        symbol: str,
        df: pd.DataFrame,
        market_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> dict:
        """Compute RS rating for a single stock.

        Args:
            symbol: Stock ticker
            df: Stock's daily price DataFrame
            market_data: Dict of {symbol: DataFrame} for all stocks in market

        Returns:
            dict: {rs_percentile: float, rs_grade: str, period_returns: dict,
                   near_high_52w: bool, pct_from_52w_high: float, reason: str}
        """
        result = {
            "rs_percentile": 50.0,
            "rs_grade": "C",
            "period_returns": {},
            "near_high_52w": False,
            "pct_from_52w_high": 0,
            "reason": "",
        }

        if df.empty or len(df) < 20:
            result["reason"] = "数据不足"
            return result

        price_col = "adjusted_close" if "adjusted_close" in df.columns else "close"
        if price_col not in df.columns:
            result["reason"] = "缺少价格数据"
            return result

        # Calculate period returns
        period_returns = {}
        for months in self.periods_months:
            trading_days = months * 21
            if len(df) > trading_days:
                ret = (df[price_col].iloc[-1] / df[price_col].iloc[-trading_days] - 1) * 100
            else:
                ret = (df[price_col].iloc[-1] / df[price_col].iloc[0] - 1) * 100
            period_returns[f"{months}m"] = round(float(ret), 2)

        result["period_returns"] = period_returns

        # Calculate weighted return
        weighted_return = 0
        for i, months in enumerate(self.periods_months):
            key = f"{months}m"
            weight = self.weights[i] if i < len(self.weights) else 0
            weighted_return += period_returns.get(key, 0) * weight

        # Compute percentile vs market if data available
        if market_data:
            all_returns = []
            for sym, mdf in market_data.items():
                if mdf.empty or sym == symbol:
                    continue
                if price_col in mdf.columns:
                    m_price = mdf[price_col]
                elif "close" in mdf.columns:
                    m_price = mdf["close"]
                else:
                    continue
                if len(m_price) < 20:
                    continue
                m_ret = (m_price.iloc[-1] / m_price.iloc[-min(len(m_price), 63)] - 1) * 100
                all_returns.append(m_ret)

            if all_returns:
                # Stock's 3-month (approx 63 trading days) return
                stock_3m = period_returns.get("3m", 0)
                below = sum(1 for r in all_returns if r < stock_3m)
                percentile = round(below / len(all_returns) * 100, 1)
                result["rs_percentile"] = max(0, min(100, percentile))
        else:
            # Simplified: map weighted return to 0-100 scale
            # Assuming typical return range of -50% to +100%
            normalized = (weighted_return + 50) / 150 * 100
            result["rs_percentile"] = round(max(0, min(100, normalized)), 1)

        # Grade
        result["rs_grade"] = self.get_grade(result["rs_percentile"])

        # Near 52-week high check
        threshold = settings.screening.rs.get("near_high_52w_threshold_pct", 15)
        if len(df) >= 252:
            high_52w = df[price_col].tail(252).max()
        else:
            high_52w = df[price_col].max()

        current = df[price_col].iloc[-1]
        if high_52w > 0:
            pct_from_high = (current - high_52w) / high_52w * 100
            result["pct_from_52w_high"] = round(float(pct_from_high), 2)
            result["near_high_52w"] = pct_from_high >= -threshold
        else:
            result["near_high_52w"] = False

        # Build reason
        reasons_parts = [f"RS百分位: {result['rs_percentile']}({result['rs_grade']})"]
        for k, v in period_returns.items():
            reasons_parts.append(f"{k}收益: {v:+.1f}%")
        reasons_parts.append(f"距52周高: {result['pct_from_52w_high']:+.1f}%")
        reasons_parts.append(f"接近新高: {'是' if result['near_high_52w'] else '否'}")
        result["reason"] = "，".join(reasons_parts)

        return result

    def compute_batch(
        self,
        market_data: Dict[str, pd.DataFrame],
    ) -> Dict[str, dict]:
        """Compute RS ratings for all stocks in a market.

        Returns:
            dict of {symbol: rs_result_dict}
        """
        results = {}
        for symbol, df in market_data.items():
            try:
                rs = self.compute_rs(symbol, df, market_data)
                results[symbol] = rs
            except Exception as e:
                logger.error("RS compute failed", symbol=symbol, error=str(e))
        return results

    @staticmethod
    def get_grade(percentile: float) -> str:
        """Convert RS percentile to letter grade."""
        if percentile >= 95:
            return "A+"
        elif percentile >= 80:
            return "A"
        elif percentile >= 60:
            return "B"
        elif percentile >= 40:
            return "C"
        elif percentile >= 20:
            return "D"
        else:
            return "F"
