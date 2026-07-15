"""
Minervini Screener v1.0 - LLM Analysis
Generates AI-powered analysis of screening results.
"""
from typing import Optional
from datetime import datetime

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


async def analyze_signals(signals: list[dict]) -> dict:
    """Generate LLM analysis of screening signals.

    Uses configured LLM provider (OpenAI/DashScope/Claude) to
    provide natural language insights on scan results.

    Args:
        signals: List of signal dicts from screening

    Returns:
        dict with analysis text and metadata
    """
    cfg = settings.ai
    if not cfg.enabled:
        return _fallback_analysis(signals)

    provider = cfg.provider
    api_key = cfg.api_key
    model = cfg.model

    if not api_key:
        logger.warning(f"AI [{provider}] 未配置API Key，使用降级分析")
        return _fallback_analysis(signals)

    # Build prompt
    prompt = _build_analysis_prompt(signals)

    try:
        if provider == "openai":
            result = await _call_openai(api_key, model, prompt)
        elif provider == "dashscope":
            result = await _call_dashscope(api_key, model, prompt)
        elif provider == "claude":
            result = await _call_claude(api_key, model, prompt)
        else:
            logger.warning(f"未知AI提供商: {provider}")
            return _fallback_analysis(signals)

        return {
            "provided": True,
            "provider": provider,
            "model": model,
            "analysis": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"AI分析失败: {e}", exc_info=True)
        return {
            "provided": False,
            "error": str(e),
            "analysis": _fallback_analysis(signals)["analysis"],
            "timestamp": datetime.now().isoformat(),
        }


def _build_analysis_prompt(signals: list[dict]) -> str:
    """Build analysis prompt from signals."""
    buy_signals = [s for s in signals if s.get("signal") == "buy"]
    watch_signals = [s for s in signals if s.get("signal") == "watch"]

    lines = [
        "## Minervini选股系统扫描结果分析",
        f"扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"买入信号: {len(buy_signals)}",
        f"关注信号: {len(watch_signals)}",
        "",
        "### 买入信号",
    ]

    for s in buy_signals[:10]:
        lines.append(
            f"- {s.get('code')} {s.get('name')} "
            f"评分{s.get('score', 0)} RS{s.get('rs_rating', 0)} "
            f"形态:{s.get('pattern_type', '-')} "
            f"现价:{s.get('current_price', 0):.2f}"
        )

    lines.extend(["", "### 关注信号"])
    for s in watch_signals[:10]:
        lines.append(
            f"- {s.get('code')} {s.get('name')} "
            f"RS{s.get('rs_rating', 0)} {s.get('pattern_type', '-')}"
        )

    lines.extend([
        "",
        "请从以下角度分析：",
        "1. 市场整体状况判断",
        "2. 值得重点关注的个股及理由",
        "3. 当前市场的风险提示",
        "4. 操作建议",
    ])

    return "\n".join(lines)


def _fallback_analysis(signals: list[dict]) -> dict:
    """Generate rule-based analysis when AI is unavailable."""
    buy_signals = [s for s in signals if s.get("signal") == "buy"]
    watch_signals = [s for s in signals if s.get("signal") == "watch"]

    lines = ["# Minervini选股 - 自动化分析"]

    if not signals:
        lines.append("今日未筛选出符合条件的股票。市场可能处于调整阶段，建议观望。")
    else:
        lines.append(f"今日扫描发现 **{len(buy_signals)}** 个买入信号，**{len(watch_signals)}** 个关注信号。")

        if buy_signals:
            lines.append("")
            lines.append("## 重点关注")
            top = buy_signals[:3]
            for s in top:
                lines.append(
                    f"- {s.get('code')} {s.get('name')}: "
                    f"评分{s.get('score', 0)}分，RS评分{s.get('rs_rating', 0)}，"
                    f"形态{bt.get('pattern_type', '-')}，现价{s.get('current_price', 0):.2f}"
                )

        if watch_signals:
            lines.append("")
            lines.append("## 待突破关注")
            for s in watch_signals[:5]:
                lines.append(
                    f"- {s.get('code')} {s.get('name')} (RS{s.get('rs_rating', 0)})"
                )

        lines.extend([
            "",
            "## 风险提示",
            "- 本分析基于技术指标，不构成投资建议",
            "- 建议严控仓位，单票不超过总资金20%",
            "- 严格执行止损纪律",
        ])

    return {
        "provided": False,
        "provider": "rule-based",
        "analysis": "\n".join(lines),
        "timestamp": datetime.now().isoformat(),
    }


async def _call_openai(api_key: str, model: str, prompt: str) -> str:
    """Call OpenAI-compatible API."""
    import json
    from urllib.request import Request, urlopen

    url = settings.ai.api_base or "https://api.openai.com/v1/chat/completions"
    payload = json.dumps({
        "model": model or "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 2000,
    }).encode()

    req = Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")

    with urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode())
        return result["choices"][0]["message"]["content"]


async def _call_dashscope(api_key: str, model: str, prompt: str) -> str:
    """Call DashScope (Alibaba Cloud) API."""
    import json
    from urllib.request import Request, urlopen

    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    payload = json.dumps({
        "model": model or "qwen-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 2000,
    }).encode()

    req = Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")

    with urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode())
        return result["choices"][0]["message"]["content"]


async def _call_claude(api_key: str, model: str, prompt: str) -> str:
    """Call Anthropic Claude API."""
    import json
    from urllib.request import Request, urlopen

    url = "https://api.anthropic.com/v1/messages"
    payload = json.dumps({
        "model": model or "claude-3-haiku-20240307",
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = Request(url, data=payload, method="POST")
    req.add_header("x-api-key", api_key)
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("Content-Type", "application/json")

    with urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode())
        return result["content"][0]["text"]
