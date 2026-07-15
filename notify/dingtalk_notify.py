"""
Minervini Screener v1.0 - DingTalk Notification
Sends screening results via DingTalk Bot webhook.
"""
import json
import os
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError
from datetime import datetime

from config.loader import settings
from core.logging_setup import get_logger

logger = get_logger(__name__)


def send_dingtalk(
    content: str,
    msg_type: str = "text",
    at_mobiles: Optional[list[str]] = None,
    at_all: bool = False,
) -> bool:
    """Send DingTalk notification via bot webhook.

    Args:
        content: Message content
        msg_type: 'text' or 'markdown'
        at_mobiles: Phone numbers to @
        at_all: @所有人

    Returns:
        True if sent successfully
    """
    # DingTalk config from env or direct parameter
    webhook = os.environ.get("DINGTALK_WEBHOOK_URL", "")
    secret = os.environ.get("DINGTALK_SECRET", "")

    if not webhook:
        logger.info("钉钉通知未启用或未配置")
        return False

    # Sign the request if secret is set
    if secret:
        import hmac
        import hashlib
        import base64
        timestamp = str(round(datetime.now().timestamp() * 1000))
        sign_str = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode("utf-8"),
            sign_str.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = base64.b64encode(hmac_code).decode("utf-8")
        webhook += f"&timestamp={timestamp}&sign={sign}"

    payload = {"msgtype": msg_type}
    at_info = {}
    if at_mobiles:
        at_info["atMobiles"] = at_mobiles
    if at_all:
        at_info["isAtAll"] = True

    if msg_type == "text":
        payload["text"] = {"content": content}
        if at_info:
            payload["at"] = at_info
    elif msg_type == "markdown":
        payload["markdown"] = {
            "title": "Minervini选股",
            "text": content,
        }
        if at_info:
            payload["at"] = at_info

    try:
        data = json.dumps(payload).encode("utf-8")
        req = Request(webhook, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        with urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            if result.get("errcode") == 0:
                logger.info("钉钉消息已发送")
                return True
            else:
                logger.error(f"钉钉发送失败: {result}")
                return False
    except URLError as e:
        logger.error(f"钉钉请求失败: {e}")
    except Exception as e:
        logger.error(f"钉钉异常: {e}")
    return False


def send_dingtalk_screening(signals: list[dict]) -> bool:
    """Send screening results as DingTalk markdown message.

    Args:
        signals: List of signal dicts

    Returns:
        True if sent successfully
    """
    buy = [s for s in signals if s.get("signal") == "buy"]
    watch = [s for s in signals if s.get("signal") == "watch"]

    lines = [f"# Minervini选股 {datetime.now().strftime('%Y-%m-%d')}", ""]

    lines.append(f"## 买入信号 ({len(buy)})")
    if buy:
        for s in buy:
            lines.append(f"- **{s.get('code')} {s.get('name')}**")
            lines.append(f"  - 评分: {s.get('score', 0)} | RS: {s.get('rs_rating', 0)}")
            lines.append(f"  - 形态: {s.get('pattern_type', '-')}")
            lines.append(f"  - 现价: {s.get('current_price', 0):.2f}")
            lines.append(f"  - 说明: {s.get('reason', '')}")
    else:
        lines.append("无")
    lines.append("")

    lines.append(f"## 关注 ({len(watch)})")
    for s in watch[:15]:
        lines.append(f"- {s.get('code')} {s.get('name')} RS{s.get('rs_rating', 0)} {s.get('pattern_type', '-')}")
    if len(watch) > 15:
        lines.append(f"- ...等{len(watch)}只")

    return send_dingtalk("\n".join(lines), msg_type="markdown")
