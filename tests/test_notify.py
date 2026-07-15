"""
Tests for notification modules.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestNotifyEmail:
    """Tests for email notification module."""

    def test_send_screening_alert_no_config(self):
        """When email is disabled, returns False."""
        from notify.email_notify import send_screening_alert
        # Email is disabled by default in config
        result = send_screening_alert([], "test summary")
        assert result is False

    def test_send_email_no_config(self):
        """Direct send without config returns False."""
        from notify.email_notify import send_email
        result = send_email("test", "body")
        assert result is False


class TestNotifyWeChat:
    """Tests for WeChat push notification module."""

    def test_send_no_token(self):
        """Without WECHAT_PUSH_TOKEN, should return False."""
        from notify.wechat_push import send_screening_summary
        result = send_screening_summary([])
        assert result is False

    def test_send_wechat_no_token(self):
        """Direct send without token returns False."""
        from notify.wechat_push import send_wechat
        result = send_wechat("test title", "test content")
        assert result is False


class TestNotifyDingTalk:
    """Tests for DingTalk notification module."""

    def test_send_no_webhook(self):
        """Without DINGTALK_WEBHOOK_URL, should return False."""
        from notify.dingtalk_notify import send_dingtalk_screening
        result = send_dingtalk_screening([])
        assert result is False

    def test_send_dingtalk_no_webhook(self):
        """Direct send without webhook returns False."""
        from notify.dingtalk_notify import send_dingtalk
        result = send_dingtalk("test")
        assert result is False
