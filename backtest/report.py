"""
Minervini Screener v1.0 - Backtest Report
Generates formatted HTML/text reports from backtest results.
"""
from typing import Optional
from datetime import datetime

from core.logging_setup import get_logger

logger = get_logger(__name__)


def generate_report(
    metrics: dict,
    trade_metrics: dict,
    trades: list[dict],
    strategy_name: str = "Minervini SEPA",
) -> str:
    """Generate a human-readable backtest report.

    Args:
        metrics: Performance metrics dict
        trade_metrics: Trade-level metrics dict
        trades: All trades data
        strategy_name: Strategy name

    Returns:
        Formatted report string (plain text)
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "=" * 60,
        f"  Minervini Screener - 回测报告",
        f"  策略: {strategy_name}",
        f"  时间: {now}",
        "=" * 60,
        "",
        "【总体表现】",
        f"  初始资金:      {metrics.get('initial_capital', 'N/A')}",
        f"  最终价值:      {metrics.get('final_value', 'N/A')}",
        f"  总收益率:      {metrics.get('total_return_pct', 0):+.2f}%",
        f"  年化收益率:    {metrics.get('annual_return_pct', 'N/A')}%",
        f"  最大回撤:      {metrics.get('max_drawdown_pct', 0):.2f}%",
        f"  夏普比率:      {metrics.get('sharpe_ratio', 0):.2f}",
        f"  索提诺比率:    {metrics.get('sortino_ratio', 'N/A')}",
        f"  卡玛比率:      {metrics.get('calmar_ratio', 'N/A')}",
        "",
        "【交易统计】",
        f"  总交易次数:    {trade_metrics.get('total_trades', 0)}",
        f"  胜率:          {trade_metrics.get('win_rate_pct', 0):.1f}%",
        f"  胜局数:        {trade_metrics.get('win_count', 0)} / 败局数: {trade_metrics.get('loss_count', 0)}",
        f"  平均盈利:      {trade_metrics.get('avg_win_pct', 0):+.2f}%",
        f"  平均亏损:      {trade_metrics.get('avg_loss_pct', 0):+.2f}%",
        f"  盈亏比:        {trade_metrics.get('profit_factor', 0):.2f}",
        f"  最大单笔盈利:  {trade_metrics.get('max_win_pct', 0):+.2f}%",
        f"  最大单笔亏损:  {trade_metrics.get('max_loss_pct', 0):+.2f}%",
        f"  连续胜局:      {trade_metrics.get('max_consecutive_wins', 0)}",
        f"  连续败局:      {trade_metrics.get('max_consecutive_losses', 0)}",
        f"  平均持仓天数:  {trade_metrics.get('avg_holding_days', 0)}",
        "",
        "【风险指标】",
        f"  年化波动率:    {metrics.get('annual_volatility_pct', 'N/A')}%",
        f"  最大回撤天数:  {metrics.get('max_drawdown_duration_days', 'N/A')}",
        f"  盈利天数占比:  {metrics.get('positive_days_pct', 'N/A')}%",
        "",
    ]

    if trades:
        sell_trades = [t for t in trades if t.get("action") == "sell"][-20:]
        lines.append("【最近20笔交易】")
        lines.append(f"  {'日期':<12} {'代码':<8} {'价格':<10} {'盈亏%':<10} {'原因':<12}")
        lines.append("  " + "-" * 55)
        for t in reversed(sell_trades):
            pnl = t.get("pnl_pct", 0)
            pnl_str = f"{pnl:+.2f}%" if pnl else "-"
            lines.append(
                f"  {str(t.get('date', '')):<12} "
                f"{str(t.get('code', '')):<8} "
                f"{t.get('price', 0):<10.2f} "
                f"{pnl_str:<10} "
                f"{str(t.get('reason', '')):<12}"
            )

    lines.extend([
        "",
        "=" * 60,
        "  报告结束",
        "=" * 60,
    ])

    return "\n".join(lines)


def generate_html_report(
    metrics: dict,
    trade_metrics: dict,
    trades: list[dict],
    strategy_name: str = "Minervini SEPA",
) -> str:
    """Generate HTML formatted backtest report.

    Args:
        Same as generate_report

    Returns:
        HTML report string
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    sell_trades = [t for t in trades if t.get("action") == "sell"][-50:]

    trade_rows = []
    for t in reversed(sell_trades):
        pnl = t.get("pnl_pct", 0)
        color = "green" if pnl > 0 else "red"
        trade_rows.append(f"""
        <tr>
            <td>{t.get('date', '')}</td>
            <td>{t.get('code', '')}</td>
            <td>{t.get('price', 0):.2f}</td>
            <td style="color:{color}">{pnl:+.2f}%</td>
            <td>{t.get('reason', '')}</td>
        </tr>""")

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Minervini Screener - 回测报告</title>
<style>
    body {{ font-family: "Microsoft YaHei", sans-serif; margin: 30px; background: #f5f5f5; }}
    .container {{ max-width: 900px; margin: auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
    h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
    h2 {{ color: #555; margin-top: 25px; }}
    .metrics {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    .metric {{ padding: 8px 12px; background: #f9f9f9; border-radius: 4px; }}
    .metric .label {{ color: #888; font-size: 12px; }}
    .metric .value {{ font-size: 18px; font-weight: bold; color: #333; }}
    .positive {{ color: #4CAF50; }}
    .negative {{ color: #f44336; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
    th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #ddd; }}
    th {{ background: #f0f0f0; }}
    tr:hover {{ background: #f5f5f5; }}
    .footer {{ margin-top: 30px; text-align: center; color: #aaa; font-size: 12px; }}
</style></head><body>
<div class="container">
    <h1>📊 Minervini Screener 回测报告</h1>
    <p>策略: {strategy_name} | 生成时间: {now}</p>

    <h2>总体表现</h2>
    <div class="metrics">
        <div class="metric"><div class="label">总收益率</div><div class="value {'positive' if (metrics.get('total_return_pct', 0) or 0) >= 0 else 'negative'}">{metrics.get('total_return_pct', 'N/A')}%</div></div>
        <div class="metric"><div class="label">年化收益率</div><div class="value">{metrics.get('annual_return_pct', 'N/A')}%</div></div>
        <div class="metric"><div class="label">最大回撤</div><div class="value negative">{metrics.get('max_drawdown_pct', 'N/A')}%</div></div>
        <div class="metric"><div class="label">夏普比率</div><div class="value">{metrics.get('sharpe_ratio', 'N/A')}</div></div>
        <div class="metric"><div class="label">初始/最终资金</div><div class="value">{metrics.get('initial_capital', 'N/A')} → {metrics.get('final_value', 'N/A')}</div></div>
        <div class="metric"><div class="label">索提诺/卡玛</div><div class="value">{metrics.get('sortino_ratio', 'N/A')} / {metrics.get('calmar_ratio', 'N/A')}</div></div>
    </div>

    <h2>交易统计</h2>
    <div class="metrics">
        <div class="metric"><div class="label">总交易</div><div class="value">{trade_metrics.get('total_trades', 0)}</div></div>
        <div class="metric"><div class="label">胜率</div><div class="value">{trade_metrics.get('win_rate_pct', 0)}%</div></div>
        <div class="metric"><div class="label">盈亏比</div><div class="value">{trade_metrics.get('profit_factor', 0)}</div></div>
        <div class="metric"><div class="label">平均持仓</div><div class="value">{trade_metrics.get('avg_holding_days', 0)}天</div></div>
        <div class="metric"><div class="label">平均盈利/亏损</div><div class="value">{trade_metrics.get('avg_win_pct', 0):+.2f}% / {trade_metrics.get('avg_loss_pct', 0):+.2f}%</div></div>
        <div class="metric"><div class="label">连续胜/败局</div><div class="value">{trade_metrics.get('max_consecutive_wins', 0)} / {trade_metrics.get('max_consecutive_losses', 0)}</div></div>
    </div>

    <h2>最近交易</h2>
    <table>
        <tr><th>日期</th><th>代码</th><th>价格</th><th>盈亏</th><th>原因</th></tr>
        {''.join(trade_rows) if trade_rows else '<tr><td colspan="5">暂无交易</td></tr>'}
    </table>

    <div class="footer">本报告由 Minervini Screener v1.0 自动生成</div>
</div></body></html>"""
