"""百度登录健康检查的离线分支。"""

from __future__ import annotations

import asyncio

from baidu_client import check_baidu_web_health


def test_health_without_cookie_is_login_failure():
    result = asyncio.run(check_baidu_web_health(""))
    assert result["ok"] is False
    assert result["stage"] == "login"
    assert "扫码" in result["message"]
    assert any(check["id"] == "bduss" and check["status"] == "fail" for check in result["checks"])
