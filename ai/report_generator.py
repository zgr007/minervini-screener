"""
Minervini Screener v1.0 - Report Generator
Generates daily/weekly summary reports in multiple formats.
"""
from typing import Optional
from datetime import datetime, timedelta
import json

from core.logging_setup import get_logger

logger = get_logger(__name__)


def generate_daily_report(
    signals: list[dict],
    market_summary: Optional[dict] = None,
    format: str = "markdown",
) -> str:
    """Generate a daily screening report.

    Args:
        signals: List of screening signal dicts
        market_summary: Optional market overview data
        format: 'markdown', 'html', or 'json'

    Returns:
        Formatted report string
    """
    today = datetime.now().strftime("%Y-%m-%d")
    buy = [s for s in signals if s.get("signal") == "buy"]
    watch = [s for s in signals if s.get("signal") == "watch"]

    if format == "json":
        return json.dumps({
            "date": today,
            "total": len(signals),
            "buy_count": len(buy),
            "watch_count": len(watch),
            "buy_signals": buy[:20],
            "watch_signals": watch[:20],
            "market_summary": market_summary or {},
        }, ensure_ascii=False, indent=2)

    if format == "html":
        return _generate_html_report(today, buy, watch, market_summary)

    # Default: markdown
    return _generate_markdown_report(today, buy, watch, market_summary)


def generate_weekly_report(
    daily_signals: list[list[dict]],
    format: str = "markdown",
) -> str:
    """Generate a weekly summary report.

    Args:
        daily_signals: List of daily signal lists
        format: 'markdown' or 'html'

    Returns:
        Formatted report string
    """
    week_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    week_end = datetime.now().strftime("%Y-%m-%d")

    # Aggregate across days
    all_codes = set()
    buy_count = 0
    watch_count = 0
    for day in daily_signals:
        for s in day:
            all_codes.add(s.get("code", ""))
            if s.get("signal") == "buy":
                buy_count += 1
            elif s.get("signal") == "watch":
                watch_count += 1

    lines = [
        f"# Minervini Screener 周报",
        f"周期: {week_start} ~ {week_end}",
        "",
        f"## 总览",
        f"- 覆盖股票数: {len(all_codes)}",
        f"- 累计买入信号: {buy_count}",
        f"- 累计关注信号: {watch_count}",
        "",
        "## 持续上榜",
        "（功能开发中）",
        "",
    ]

    return "\n".join(lines)


def _generate_markdown_report(
    date_str: str,
    buy_signals: list[dict],
    watch_signals: list[dict],
    market_summary: Optional[dict],
) -> str:
    """Generate markdown format report."""
    lines = [
        f"# Minervini选股 - {date_str}",
        "",
        f"买入信号: {len(buy_signals)} | 关注信号: {len(watch_signals)}",
        "",
    ]

    if market_summary:
        lines.extend([
            "## 市场概况",
            f"- 上涨比例: {market_summary.get('up_ratio', 'N/A')}%",
            f"- 突破信号: {market_summary.get('breakout_count', 'N/A')}",
            "",
        ])

    if buy_signals:
        lines.append("## 🟢 买入信号")
        lines.append("")
        lines.append("| 代码 | 名称 | 评分 | RS评分 | 形态 | 现价 |")
        lines.append("|------|------|------|--------|------|------|")
        for s in buy_signals[:20]:
            lines.append(
                f"| {s.get('code', '')} | {s.get('name', '')} "
                f"| {s.get('score', 0)} | {s.get('rs_rating', 0)} "
                f"| {s.get('pattern_type', '-')} | {s.get('current_price', 0):.2f} |"
            )
        lines.append("")

    if watch_signals:
        lines.append("## 🟡 关注信号")
        lines.append("")
        lines.append("| 代码 | 名称 | RS评分 | 形态 |")
        lines.append("|------|------|--------|------|")
        for s in watch_signals[:15]:
            lines.append(
                f"| {s.get('code', '')} | {s.get('name', '')} "
                f"| {s.get('rs_rating', 0)} | {s.get('pattern_type', '-')} |"
            )
        lines.append("")

    lines.extend([
        "---",
        "⚠️ *本报告由 Minervini Screener v1.0 自动生成，仅供参考。*",
    ])

    return "\n".join(lines)


def _generate_html_report(
    date_str: str,
    buy_signals: list[dict],
    watch_signals: list[dict],
    market_summary: Optional[dict],
) -> str:
    """Generate HTML format report."""
    buy_rows = ""
    for s in buy_signals[:20]:
        buy_rows += f"""
        <tr>
            <td>{s.get('code', '')}</td>
            <td>{s.get('name', '')}</td>
            <td>{s.get('score', 0)}</td>
            <td>{s.get('rs_rating', 0)}</td>
            <td>{s.get('pattern_type', '-')}</td>
            <td>{s.get('current_price', 0):.2f}</td>
        </tr>"""

    watch_rows = ""
    for s in watch_signals[:15]:
        watch_rows += f"""
        <tr>
            <td>{s.get('code', '')}</td>
            <td>{s.get('name', '')}</td>
            <td>{s.get('rs_rating', 0)}</td>
            <td>{s.get('pattern_type', '-')}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Minervini选股 - {date_str}</title>
<style>
    body {{ font-family: "Microsoft YaHei", sans-serif; margin: 30px; background: #f5f5f5; }}
    .container {{ max-width: 1000px; margin: auto; background: white; padding: 30px; border-radius: 8px; }}
    h1 {{ color: #333; }}
    .summary {{ background: #f0f8ff; padding: 15px; border-radius: 6px; margin: 15px 0; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
    th {{ background: #f0f0f0; padding: 10px; text-align: left; border-bottom: 2px solid #ddd; }}
    td {{ padding: 8px 10px; border-bottom: 1px solid #eee; }}
    .buy-header {{ color: #4CAF50; }}
    .watch-header {{ color: #FF9800; }}
    .footer {{ margin-top: 30px; color: #aaa; font-size: 12px; text-align: center; }}
</style></head><body>
<div class="container">
    <h1>📊 Minervini选股 - {date_str}</h1>
    <div class="summary">
        买入信号: <strong>{len(buy_signals)}</strong> | 关注信号: <strong>{len(watch_signals)}</strong>
        {f'| 上涨比例: {market_summary.get("up_ratio", "N/A")}%' if market_summary else ''}
    </div>

    <h2 class="buy-header">🟢 买入信号 ({len(buy_signals)})</h2>
    <table>
        <tr><th>代码</th><th>名称</th><th>评分</th><th>RS</th><th>形态</th><th>现价</th></tr>
        {buy_rows or '<tr><td colspan="6">暂无</td></tr>'}
    </table>

    <h2 class="watch-header">🟡 关注信号 ({len(watch_signals)})</h2>
    <table>
        <tr><th>代码</th><th>名称</th><th>RS</th><th>形态</th></tr>
        {watch_rows or '<tr><td colspan="4">暂无</td></tr>'}
    </table>

    <div class="footer">⚠️ 本报告由 Minervini Screener v1.0 自动生成，仅供参考。</div>
</div></body></html>"""
