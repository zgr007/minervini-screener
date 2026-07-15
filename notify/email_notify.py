"""
Minervini Screener v1.0 - Email Notification
Sends screening results and alerts via SMTP email.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


def send_email(
    subject: str,
    body: str,
    to_addrs: Optional[list[str]] = None,
    html: bool = True,
) -> bool:
    """Send email notification.

    Args:
        subject: Email subject
        body: Email body (plain text or HTML)
        to_addrs: Recipients (default from config)
        html: Whether body is HTML

    Returns:
        True if sent successfully
    """
    cfg = settings.notifications.channels.email
    if not cfg.enabled:
        logger.info("邮件通知未启用")
        return False

    sender_addr = cfg.from_addr or "minervini@example.com"
    recipients = to_addrs or ([cfg.to_addr] if cfg.to_addr else [])
    if not recipients:
        logger.warning("未配置收件人")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[Minervini筛选] {subject}"
    msg["From"] = sender_addr
    msg["To"] = ", ".join(recipients)

    content_type = "html" if html else "plain"
    msg.attach(MIMEText(body, content_type, "utf-8"))

    try:
        # Port 465 = SMTP_SSL, port 587 = SMTP + STARTTLS
        if cfg.smtp_port == 465:
            server = smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port)
        else:
            server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port)
            server.starttls()
        with server:
            if cfg.smtp_user:
                server.login(cfg.smtp_user, cfg.smtp_password)
            server.sendmail(sender_addr, recipients, msg.as_string())
        logger.info(f"邮件已发送: {subject}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP认证失败")
    except smtplib.SMTPException as e:
        logger.error(f"SMTP发送失败: {e}")
    except ConnectionRefusedError:
        logger.error(f"无法连接SMTP服务器{cfg.smtp_host}:{cfg.smtp_port}")
    except Exception as e:
        logger.error(f"邮件发送异常: {e}")
    return False


def send_screening_alert(
    signals: list[dict],
    summary: str,
) -> bool:
    """Send screening results as formatted HTML email.

    Args:
        signals: List of signal dicts with code/name/pattern/score
        summary: Overall market summary text

    Returns:
        True if sent successfully
    """
    if not signals:
        return send_email("筛选结果", "今日无信号", html=False)

    rows = []
    for s in signals:
        rows.append(f"""
        <tr>
            <td>{s.get('code', '')}</td>
            <td>{s.get('name', '')}</td>
            <td><span style="color: {'red' if s.get('signal') == 'buy' else 'orange'}">{s.get('signal', '')}</span></td>
            <td>{s.get('score', 0)}</td>
            <td>{s.get('pattern_type', '-')}</td>
            <td>{s.get('current_price', 0):.2f}</td>
            <td>{s.get('rs_rating', 0)}</td>
            <td>{s.get('reason', '')[:50]}</td>
        </tr>""")

    html = f"""
    <html><body>
    <h2>Minervini选股系统 - 筛选结果</h2>
    <p><b>时间:</b> {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    <p><b>摘要:</b> {summary}</p>
    <table border="1" cellpadding="5" style="border-collapse: collapse;">
        <tr style="background: #f0f0f0;">
            <th>代码</th><th>名称</th><th>信号</th><th>评分</th><th>形态</th>
            <th>现价</th><th>RS</th><th>说明</th>
        </tr>
        {"".join(rows)}
    </table>
    <p><small>本邮件由Minervini Screener自动生成，仅供参考。</small></p>
    </body></html>
    """

    buy_count = sum(1 for s in signals if s.get("signal") == "buy")
    watch_count = sum(1 for s in signals if s.get("signal") == "watch")
    return send_email(f"买入信号{buy_count}个/关注{watch_count}个", html)
