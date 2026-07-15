"""
Minervini Screener v1.0 - WeChat Push Notification
Sends screening results via ServerChan / PushPlus / WeCom Bot.
"""
import json
import os
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


def send_wechat(
    title: str,
    content: str,
    channel: Optional[str] = None,
) -> bool:
    """Send WeChat push notification.

    Supports multiple channels:
    - serverchan: ServerChan (方糖)
    - pushplus: PushPlus
    - wecom_bot: WeCom (企业微信) Bot

    Args:
        title: Message title
        content: Message content (markdown supported)
        channel: Push channel (default from config)

    Returns:
        True if sent successfully
    """
    # WeChat-specific config not in Settings; use direct token/env
    token = os.environ.get("WECHAT_PUSH_TOKEN", "")
    channel = channel or os.environ.get("WECHAT_PUSH_CHANNEL", "serverchan")

    if not token:
        logger.info("微信通知未启用或未配置Token")
        return False

    if channel == "serverchan":
        return _send_serverchan(token, title, content)
    elif channel == "pushplus":
        return _send_pushplus(token, title, content)
    elif channel == "wecom_bot":
        return _send_wecom_bot(token, content)
    else:
        logger.warning(f"未知推送通道: {channel}")
        return False


def _send_serverchan(token: str, title: str, content: str) -> bool:
    """Send via ServerChan (https://sct.ftqq.com/)."""
    url = f"https://sctapi.ftqq.com/{token}.send"
    data = json.dumps({"title": title, "desp": content}).encode()
    return _post_json(url, data)


def _send_pushplus(token: str, title: str, content: str) -> bool:
    """Send via PushPlus (https://www.pushplus.plus/)."""
    url = "https://www.pushplus.plus/send"
    data = json.dumps({"token": token, "title": title, "content": content, "template": "markdown"}).encode()
    return _post_json(url, data)


def _send_wecom_bot(webhook_url: str, content: str) -> bool:
    """Send via WeCom Bot webhook."""
    payload = {
        "msgtype": "markdown",
        "markdown": {"content": content},
    }
    data = json.dumps(payload).encode()
    return _post_json(webhook_url, data)


def _post_json(url: str, data: bytes) -> bool:
    """Post JSON data to URL."""
    try:
        req = Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Content-Length", str(len(data)))
        with urlopen(req, timeout=10) as resp:
            body = resp.read().decode()
            logger.debug(f"推送响应: {body[:200]}")
            return True
    except URLError as e:
        logger.error(f"推送请求失败: {e}")
    except TimeoutError:
        logger.error("推送请求超时")
    except Exception as e:
        logger.error(f"推送异常: {e}")
    return False


def send_screening_summary(signals: list[dict]) -> bool:
    """Send screening summary as WeChat push.

    Args:
        signals: List of signal dicts

    Returns:
        True if sent successfully
    """
    buy = [s for s in signals if s.get("signal") == "buy"]
    watch = [s for s in signals if s.get("signal") == "watch"]

    lines = [f"## Minervini选股 {__import__('datetime').datetime.now().strftime('%m/%d')}"]
    lines.append(f"\n### 买入信号 ({len(buy)})")
    for s in buy:
        lines.append(f"- **{s.get('code')} {s.get('name')}** 评分{s.get('score', 0)} {s.get('pattern_type', '')} 现价{s.get('current_price', 0):.2f}")

    lines.append(f"\n### 关注 ({len(watch)})")
    for s in watch[:10]:
        lines.append(f"- {s.get('code')} {s.get('name'):6s} RS{s.get('rs_rating', 0)} 形态:{s.get('pattern_type', '-')}")

    if len(watch) > 10:
        lines.append(f"- ...等{len(watch)}只")

    title = f"选股信号: {len(buy)}买入/{len(watch)}关注"
    return send_wechat(title, "\n".join(lines))
