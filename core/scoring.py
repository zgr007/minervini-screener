"""
Minervini Screener v1.0 - Comprehensive Scoring Engine
Combines fundamental, institutional, and technical scores.
"""
from typing import Optional, Dict, Any, List
import pandas as pd

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


def calculate_fundamental_score(fundamentals: dict, config: Optional[object] = None) -> dict:
    """Calculate fundamental score (max 10 points).

    Scoring:
    - EPS YoY growth: >25%=2pts, >50%=3pts, >100%=4pts
    - Revenue growth: 1-3pts based on acceleration or sustained high growth
    - ROE >17%: 1-2pts
    - Catalyst exists: 1pt

    Args:
        fundamentals: dict with keys: eps_growth_yoy, revenue_growth_yoy,
                     revenue_growth_acceleration, roe, catalyst_note
        config: FundamentalConfig from settings.screening.fundamental

    Returns:
        dict: {total_score, eps_score, revenue_score, roe_score,
               catalyst_score, passed, details}
    """
    cfg = config or settings.screening.fundamental
    scoring = cfg.scoring
    min_pass = cfg.min_total_score

    eps = fundamentals.get("eps_growth_yoy", 0) or 0
    revenue = fundamentals.get("revenue_growth_yoy", 0) or 0
    revenue_accel = fundamentals.get("revenue_growth_acceleration", False)
    roe = fundamentals.get("roe", 0) or 0
    catalyst = bool(fundamentals.get("catalyst_note"))

    # EPS score
    eps_cfg = scoring.eps_growth_yoy
    if eps >= eps_cfg.threshold_100:
        eps_score = eps_cfg.score_100
    elif eps >= eps_cfg.threshold_50:
        eps_score = eps_cfg.score_50
    elif eps >= eps_cfg.threshold_25:
        eps_score = eps_cfg.score_25
    else:
        eps_score = eps_cfg.score_0

    # Revenue score (max 3)
    rev_cfg = scoring.revenue_growth
    if revenue >= 50:
        revenue_score = rev_cfg.max_score
    elif revenue >= rev_cfg.threshold:
        revenue_score = 2
    elif revenue_accel:
        revenue_score = 1
    else:
        revenue_score = 0

    # ROE score (max 2)
    roe_cfg = scoring.roe
    if roe >= roe_cfg.threshold * 2:
        roe_score = roe_cfg.max_score
    elif roe >= roe_cfg.threshold:
        roe_score = 1
    else:
        roe_score = 0

    # Catalyst score
    cat_cfg = scoring.catalyst
    catalyst_score = cat_cfg.max_score if catalyst else 0

    total = eps_score + revenue_score + roe_score + catalyst_score
    passed = total >= min_pass

    details_parts = [
        f"EPS增长{eps:.1f}%: {eps_score}分",
        f"营收增长{revenue:.1f}%: {revenue_score}分",
        f"ROE {roe:.1f}%: {roe_score}分",
        f"催化剂: {catalyst_score}分",
    ]

    return {
        "total_score": total,
        "eps_score": eps_score,
        "revenue_score": revenue_score,
        "roe_score": roe_score,
        "catalyst_score": catalyst_score,
        "passed": passed,
        "details": "，".join(details_parts),
    }


def calculate_institutional_score(inst_data: dict, config: Optional[object] = None) -> dict:
    """Calculate institutional score.

    Scoring:
    - Holder count decreasing (筹码集中): positive signal
    - Institution positions increasing: positive signal
    - Abnormal volume accumulation: positive signal

    Args:
        inst_data: dict with keys: holder_count_change, institution_position_change,
                  abnormal_volume_note
        config: InstitutionalConfig from settings.screening.institutional

    Returns:
        dict: {total_score, max_score, holder_score, position_score,
               volume_score, details}
    """
    cfg = config or settings.screening.institutional
    scoring = cfg.scoring

    holder_change = inst_data.get("holder_count_change", 0) or 0
    position_change = inst_data.get("institution_position_change", 0) or 0
    abnormal_vol = bool(inst_data.get("abnormal_volume_note"))

    holder_threshold = scoring.get("holder_decrease_threshold", -0.05)
    position_threshold = scoring.get("position_increase_threshold", 0.05)
    vol_threshold = scoring.get("volume_accumulation_threshold", 1.5)

    holder_score = 0
    if holder_change < holder_threshold:
        holder_score = 2  # Significant holder decrease = accumulation
    elif holder_change < 0:
        holder_score = 1

    position_score = 0
    if position_change > position_threshold * 2:
        position_score = 2
    elif position_change > position_threshold:
        position_score = 1

    volume_score = 1 if abnormal_vol else 0

    total = holder_score + position_score + volume_score
    max_score = 5

    details_parts = [
        f"股东变化{holder_change:+.1f}%: {holder_score}分",
        f"机构持仓变化{position_change:+.1f}%: {position_score}分",
        f"量价收集: {volume_score}分",
    ]

    return {
        "total_score": total,
        "max_score": max_score,
        "holder_score": holder_score,
        "position_score": position_score,
        "volume_score": volume_score,
        "details": "，".join(details_parts),
    }


def calculate_total_score(
    stage2_result: dict,
    rs_result: dict,
    fundamental_result: dict,
    institutional_result: dict,
    config: Optional[object] = None,
) -> dict:
    """Combine all screening scores into a total score.

    Returns:
        dict: {total_score, passed, reasons: List[str], risk_warnings: List[str]}
    """
    reasons = []
    warnings = []
    score = 0
    max_score = 0

    # Stage 2 (weight: 30%)
    if stage2_result.get("passed"):
        score += 30
        reasons.append("第二阶段趋势: 通过 (+30分)")
    else:
        reasons.append(f"第二阶段趋势: 未通过 (0分)")
        failed_reasons = [r for r in stage2_result.get("reasons", []) if "未通过" in r]
        warnings.extend(failed_reasons[:3])

    max_score += 30

    # RS Rating (weight: 25%)
    rs_pct = rs_result.get("rs_percentile", 0) or 0
    rs_passed = rs_pct >= 80
    if rs_passed:
        rs_weight = rs_result.get("rs_grade", "C")
        rs_points = {"A+": 25, "A": 22, "B": 15, "C": 10, "D": 5, "F": 0}
        pts = rs_points.get(rs_weight, 10)
        score += pts
        reasons.append(f"RS评级: {rs_weight} (RS={rs_pct}, +{pts}分)")
    else:
        reasons.append(f"RS评级: 未通过 (RS={rs_pct})")

    max_score += 25

    # Fundamental (weight: 30%)
    fund = fundamental_result or {}
    fund_score = fund.get("total_score", 0)
    fund_passed = fund.get("passed", False)
    fund_weighted = min(fund_score * 3, 30)  # Max 10 * 3 = 30
    score += fund_weighted
    reasons.append(f"基本面评分: {fund_score}分 (+{fund_weighted}分)")
    if not fund_passed:
        warnings.append(f"基本面评分{fund_score}分低于最低要求")

    max_score += 30

    # Institutional (weight: 15%)
    inst = institutional_result or {}
    inst_score = inst.get("total_score", 0)
    inst_max = inst.get("max_score", 5)
    inst_weighted = round((inst_score / max(inst_max, 1)) * 15)
    score += inst_weighted
    reasons.append(f"机构评分: {inst_score}/{inst_max} (+{inst_weighted}分)")

    max_score += 15

    # Final verdict
    min_pass_score = 60  # 60% of max
    passed = score >= 60

    if passed:
        reasons.append(f"综合评分: {score}/{max_score} - 入选")
    else:
        reasons.append(f"综合评分: {score}/{max_score} - 未达入选标准")
        warnings.append(f"总评分{score}低于入选阈值{min_pass_score}")

    return {
        "total_score": score,
        "max_score": max_score,
        "passed": passed,
        "reasons": reasons,
        "risk_warnings": warnings[:5],
    }
