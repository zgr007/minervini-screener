"""
Minervini Screener v1.0 - Analysis API
Deep analysis endpoints for patterns and comparisons.
"""
from typing import Optional
import pandas as pd
from fastapi import APIRouter, Query

from config.loader import settings
from core.logging_setup import get_logger
from core.vcp import detect_vcp
from core.cup_handle import detect_cup_handle
from core.flat_base import detect_flat_base
from core.double_bottom import detect_double_bottom
from core.boll import detect_bollinger_signal
from data.downloader import DataDownloader
from indicators.ma import calculate_ma

router = APIRouter(prefix="/api/analysis", tags=["analysis"])
logger = get_logger(__name__)


@router.get("/patterns/{code}")
async def analyze_patterns(code: str):
    """Run all pattern detection algorithms on a stock."""
    try:
        downloader = DataDownloader()
        df = await downloader.download_stock(code)
        if df is None or df.empty:
            return {"error": f"无法获取{code}数据"}

        results = {}
        for name, func, cfg in [
            ("vcp", detect_vcp, settings.patterns.vcp),
            ("cup_handle", detect_cup_handle, settings.patterns.cup_handle),
            ("flat_base", detect_flat_base, settings.patterns.flat_base),
            ("double_bottom", detect_double_bottom, settings.patterns.double_bottom),
            ("bollinger", detect_bollinger_signal, settings.patterns.bollinger),
        ]:
            try:
                results[name] = func(df, cfg)
            except Exception as e:
                results[name] = {"error": str(e)}

        return {"code": code, "results": results}
    except Exception as e:
        logger.error(f"[{code}] 形态分析失败: {e}")
        return {"error": str(e)}


@router.get("/compare")
async def compare_stocks(
    codes: str = Query(..., description="逗号分隔的股票代码"),
):
    """Compare multiple stocks side by side."""
    try:
        code_list = [c.strip() for c in codes.split(",")]
        downloader = DataDownloader()
        results = []

        for code in code_list[:10]:
            df = await downloader.download_stock(code)
            if df is not None and not df.empty:
                from core.sepa import run_sepa
                result = run_sepa(df, code)
                results.append({
                    "code": code,
                    "signal": result.signal,
                    "score": result.score,
                    "stage2": result.stage2,
                    "rs_rating": result.rs_rating_val,
                    "pattern_type": result.pattern.get("type", "-") if result.pattern else "-",
                    "current_price": result.data.get("current_price"),
                })

        sorted_results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
        return {"count": len(sorted_results), "results": sorted_results}
    except Exception as e:
        logger.error(f"股票对比失败: {e}")
        return {"error": str(e)}


@router.get("/stage2/{code}")
async def stage2_analysis(code: str):
    """Detailed Stage 2 analysis."""
    try:
        downloader = DataDownloader()
        df = await downloader.download_stock(code)
        if df is None or df.empty:
            return {"error": f"无法获取{code}数据"}

        # Ensure MAs are calculated on this copy
        df = calculate_ma(df)

        from core.stage2 import check_stage2
        stage2_result = check_stage2(df)
        stage2 = stage2_result.get("passed", False)
        price_col = "adjusted_close" if "adjusted_close" in df.columns else "close"

        # Trend analysis
        ma50 = df["ma_50"].iloc[-1] if "ma_50" in df.columns else None
        ma150 = df["ma_150"].iloc[-1] if "ma_150" in df.columns else None
        ma200 = df["ma_200"].iloc[-1] if "ma_200" in df.columns else None
        current = df[price_col].iloc[-1]

        # Count days above moving averages
        days_above_ma50 = int((df[price_col].tail(50) > df["ma_50"].tail(50)).sum()) if "ma_50" in df.columns else 0
        days_above_ma150 = int((df[price_col].tail(50) > df["ma_150"].tail(50)).sum()) if "ma_150" in df.columns else 0

        return {
            "code": code,
            "stage2": stage2,
            "current_price": round(float(current), 2),
            "ma_50": round(float(ma50), 2) if ma50 is not None and not pd.isna(ma50) else None,
            "ma_150": round(float(ma150), 2) if ma150 is not None and not pd.isna(ma150) else None,
            "ma_200": round(float(ma200), 2) if ma200 is not None and not pd.isna(ma200) else None,
            "days_above_ma50": days_above_ma50,
            "days_above_ma150": days_above_ma150,
            "near_52w_high": None,  # TODO: calculate
        }
    except Exception as e:
        logger.error(f"[{code}] Stage2分析失败: {e}")
        return {"error": str(e)}
