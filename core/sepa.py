"""
Minervini Screener v1.0 - SEPA Strategy
(Specific Entry Point Analysis) - Main strategy orchestrator.
"""
from typing import Optional
import pandas as pd
from dataclasses import dataclass

from config.loader import settings
from core.logging_setup import get_logger
from core.scoring import calculate_total_score, calculate_fundamental_score, calculate_institutional_score
from core.stage2 import check_stage2
from core.rs_rating import RSRatingEngine
from core.vcp import detect_vcp
from core.cup_handle import detect_cup_handle
from core.flat_base import detect_flat_base
from core.double_bottom import detect_double_bottom
from core.boll import detect_bollinger_signal
from core.breakout import detect_breakout, check_breakout_distance
from core.stoploss import calculate_stop_loss

logger = get_logger(__name__)


@dataclass
class StrategyResult:
    """Result of SEPA strategy analysis for a single stock."""
    code: str
    name: str
    signal: str  # 'buy', 'watch', 'no_entry'
    score: float
    stage2: bool
    rs_rating_val: int
    rs_rank: int
    pattern: Optional[dict]
    breakout: Optional[dict]
    stop_loss: Optional[dict]
    reason: str
    data: dict


def run_sepa(
    df: pd.DataFrame,
    code: str,
    name: str = "",
    check_breakout: bool = True,
    rs_result: Optional[dict] = None,
) -> StrategyResult:
    """Run SEPA strategy on a single stock.

    The Minervini SEPA method:
    1. Stock must be in Stage 2 (uptrend)
    2. RS Rating >= 80
    3. At least one buyable pattern
    4. Breakout confirmation with volume

    Args:
        df: OHLCV DataFrame with pre-calculated indicators
        code: Stock code
        name: Stock name (optional)
        check_breakout: Whether to check breakout status

    Returns:
        StrategyResult with signal and details
    """
    if df.empty or len(df) < 50:
        return StrategyResult(
            code=code, name=name or code,
            signal="no_entry", score=0, stage2=False,
            rs_rating_val=0, rs_rank=0,
            pattern=None, breakout=None, stop_loss=None,
            reason="数据不足", data={},
        )

    # 1. Stage 2 check
    stage2_result = check_stage2(df)
    stage2_passed = stage2_result.get("passed", False)
    stage2_required = True  # Could come from config

    if not stage2_passed:
        return StrategyResult(
            code=code, name=name or code,
            signal="no_entry", score=0, stage2=False,
            rs_rating_val=0, rs_rank=0,
            pattern=None, breakout=None, stop_loss=None,
            reason="非Stage2上涨趋势", data={},
        )

    # 2. RS Rating - use pre-computed from batch if available, else compute per-stock
    if rs_result is None:
        rs_engine = RSRatingEngine()
        rs_result = rs_engine.compute_rs(code, df)
    rs_percentile = rs_result.get("rs_percentile", 0)
    rs_grade = rs_result.get("rs_grade", "C")

    min_rs = settings.screening.rs.get("min_percentile", 80) if isinstance(settings.screening.rs, dict) else 80
    if rs_percentile < min_rs:
        return StrategyResult(
            code=code, name=name or code,
            signal="no_entry", score=0,
            stage2=stage2_passed,
            rs_rating_val=int(rs_percentile), rs_rank=0,
            pattern=None, breakout=None, stop_loss=None,
            reason=f"RS评分{rs_percentile:.0f}<{min_rs}",
            data={"rs_rating": int(rs_percentile), "rs_grade": rs_grade},
        )

    # 3. Detect patterns
    best_pattern = None
    best_confidence = 0

    pattern_funcs = [
        ("VCP", detect_vcp, settings.patterns.vcp),
        ("杯柄", detect_cup_handle, settings.patterns.cup_handle),
        ("平台底", detect_flat_base, settings.patterns.flat_base),
        ("双底", detect_double_bottom, settings.patterns.double_bottom),
        ("布林带", detect_bollinger_signal, settings.patterns.bollinger),
    ]

    for name_pat, func, cfg in pattern_funcs:
        try:
            p_result = func(df, cfg)
            if p_result.get("detected"):
                conf = {"high": 3, "medium": 2, "low": 1}.get(p_result.get("confidence"), 0)
                p_result["type"] = name_pat
                if conf > best_confidence:
                    best_confidence = conf
                    best_pattern = p_result
        except Exception as e:
            logger.warning(f"[{code}] {name_pat}检测异常: {e}")
            continue

    if not best_pattern or best_confidence < 1:
        return StrategyResult(
            code=code, name=name or code,
            signal="watch", score=0,
            stage2=stage2_passed,
            rs_rating_val=int(rs_percentile), rs_rank=0,
            pattern=None, breakout=None, stop_loss=None,
            reason="未发现可买入形态, 待突破",
            data={"rs_rating": int(rs_percentile), "rs_grade": rs_grade},
        )

    # 4. Compute scoring
    fund_score = calculate_fundamental_score({})
    inst_score = calculate_institutional_score({})
    total_score = calculate_total_score(stage2_result, rs_result, fund_score, inst_score)
    final_score = total_score.get("total_score", 0)

    # 5. Check breakout
    buy_point = best_pattern.get("buy_point") or best_pattern.get("pivot_price", 0)
    breakout_result = None
    stop_loss_result = None

    if check_breakout and buy_point > 0:
        breakout_result = detect_breakout(df, buy_point)
        breakout_distance = check_breakout_distance(df, buy_point)

        if breakout_result.get("failed_breakout"):
            return StrategyResult(
                code=code, name=name or code,
                signal="no_entry", score=final_score,
                stage2=stage2_passed,
                rs_rating_val=int(rs_percentile), rs_rank=0,
                pattern=best_pattern, breakout=breakout_result,
                stop_loss=None, reason="突破失败",
                data={"rs_rating": int(rs_percentile), "rs_grade": rs_grade},
            )

        # If price is way above buy point (extended), pattern is played out
        if breakout_distance in ("extended", "too_extended"):
            price_col = "adjusted_close" if "adjusted_close" in df.columns else "close"
            current_price = df[price_col].iloc[-1]
            return StrategyResult(
                code=code, name=name or code,
                signal="extended", score=round(float(final_score), 1),
                stage2=stage2_passed,
                rs_rating_val=int(rs_percentile), rs_rank=0,
                pattern=best_pattern, breakout=breakout_result,
                stop_loss=None,
                reason=f"{best_pattern.get('type','')}形态已延伸({breakout_distance})，等待新形态",
                data={
                    "current_price": round(float(current_price), 2),
                    "rs_rating": int(rs_percentile), "rs_grade": rs_grade,
                },
            )

        # Calculate stop loss
        stop_loss_result = calculate_stop_loss(df, buy_point)

    # Determine signal
    if breakout_result and breakout_result.get("detected"):
        signal = "buy"
        reason = f"{best_pattern.get('type', '')}形态突破，"
        if breakout_result.get("follow_through"):
            reason += "跟进确认，"
    elif breakout_result and breakout_result.get("close_above_buy_point"):
        signal = "buy"
        reason = f"{best_pattern.get('type', '')}形态，已站上买入点，"
    else:
        signal = "watch"
        reason = f"{best_pattern.get('type', '')}形态形成，待突破，"

    price_col = "adjusted_close" if "adjusted_close" in df.columns else "close"
    current_price = df[price_col].iloc[-1]

    reason += f"当前价{current_price:.2f}，RS评分{rs_percentile:.0f}"

    return StrategyResult(
        code=code, name=name or code,
        signal=signal, score=round(float(final_score), 1),
        stage2=stage2_passed,
        rs_rating_val=int(rs_percentile), rs_rank=0,
        pattern=best_pattern, breakout=breakout_result,
        stop_loss=stop_loss_result, reason=reason,
        data={
            "current_price": round(float(current_price), 2),
            "rs_rating": int(rs_percentile),
            "rs_grade": rs_grade,
            "stage2_reasons": stage2_result.get("reasons", []),
        },
    )
