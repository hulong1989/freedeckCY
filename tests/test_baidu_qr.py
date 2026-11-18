"""百度二维码轮询响应解析。"""

from __future__ import annotations

import asyncio
import json
import ssl

import aiohttp

import baidu_openapi_client as openapi
import baidu_qr
from baidu_qr import parse_qr_poll_payload


def test_qr_poll_waiting():
    assert parse_qr_poll_payload('{"errno":1}') == {"status": "waiting"}


def test_qr_poll_expired():
    result = parse_qr_poll_payload('{"errno":2,"prompt":"二维码已失效"}')
    assert result["status"] == "expired"
    assert "失效" in result["error"]


def test_qr_poll_scanned():
    payload = {"errno": 0, "channel_v": json.dumps({"status": 1})}
    assert parse_qr_poll_payload(json.dumps(payload))["status"] == "scanned"


def test_qr_poll_confirmed():
    payload = {"errno": 0, "channel_v": json.dumps({"v": "token-123"})}
    result = parse_qr_poll_payload(json.dumps(payload))
    assert result == {"status": "confirmed", "v": "token-123"}


def test_qr_poll_invalid_json():
    assert parse_qr_poll_payload("<html>blocked</html>")["status"] == "error"


# ---- 轮询状态机：过期 vs 临时错误、空响应、超时 ----


def test_qr_poll_unknown_errno_is_error_not_expired():
    result = baidu_qr.parse_qr_poll_payload('{"errno":3,"prompt":"系统繁忙，请稍后再试"}')
    assert result["status"] == "error"
    assert "过期" not in result.get("error", "")


def test_qr_poll_expired_only_for_expiry_markers():
    assert baidu_qr.parse_qr_poll_payload('{"errno":2,"prompt":"二维码已失效"}')["status"] == "expired"
    assert baidu_qr.parse_qr_poll_payload('{"errno":9,"prompt":"二维码已过期"}')["status"] == "expired"


def test_qr_poll_empty_and_error_detail_redacted():
    assert baidu_qr.parse_qr_poll_payload("")["status"] == "error"
    result = baidu_qr.parse_qr_poll_payload("<html>blocked sign=SECRET123&bduss=BDUSSVALUE</html>")
    assert result["status"] == "error"
    assert "SECRET123" not in result["error"]
    assert "BDUSSVALUE" not in result["error"]
    assert "<redacted>" in result["error"]


def test_parse_login_payload_handles_apostrophe_and_jsonp():
    payload = '{"errInfo":{"msg":"it\'s fine"},"data":{"session":{"bduss":"B1","stoken":"S1"}}}'
    data = baidu_qr._parse_login_payload(payload)
    assert data["data"]["session"]["bduss"] == "B1"

    jsonp = 'tangram_guid_1({"errno":0,"data":{"session":{"bduss":"B2"}}})'
    assert baidu_qr._parse_login_payload(jsonp)["data"]["session"]["bduss"] == "B2"


class _FakeResponse:
    def __init__(self, status: int, body: str):
        self.status = status
        self._body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def text(self):
        return self._body

    async def read(self):
        return self._body.encode("utf-8")


def _install_fake_session(monkeypatch, *, attempts):
    """attempts: 依次消费的异常或 (status, body)。"""
    state = {"index": 0}
    ssl_flags = []

    class _FakeSession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, url, params=None, headers=None):
            index = state["index"]
            state["index"] += 1
            item = attempts[min(index, len(attempts) - 1)]
            if isinstance(item, BaseException):
                raise item
            return _FakeResponse(*item)

    class _FakeJar:
        def __init__(self, *args, **kwargs):
            pass

        def __iter__(self):
            return iter(())

        def update_cookies(self, *args, **kwargs):
            return None

    def _fake_connector(*args, **kwargs):
        ssl_flags.append(kwargs.get("ssl", "missing"))
        return None

    monkeypatch.setattr(baidu_qr.aiohttp, "ClientSession", _FakeSession)
    monkeypatch.setattr(baidu_qr.aiohttp, "CookieJar", _FakeJar)
    monkeypatch.setattr(baidu_qr.aiohttp, "TCPConnector", _fake_connector)
    return ssl_flags


def test_request_qr_falls_back_to_unverified_tls_only_for_cert_errors(monkeypatch):
    ssl_flags = _install_fake_session(
        monkeypatch,
        attempts=[
            ssl.SSLCertVerificationError("certificate verify failed"),
            (200, '{"sign":"sign-1","imgurl":"https://passport.baidu.com/qr"}'),
        ],
    )
    result = asyncio.run(baidu_qr.request_qr())
    assert result["sign"] == "sign-1"
    # 第一次用系统 CA，第二次才降级为不校验证书（ssl=False）。
    assert ssl_flags[0] is not False
    assert ssl_flags[1] is False


def test_request_qr_keeps_cookies_from_urllib_fallback(monkeypatch):
    _install_fake_session(monkeypatch, attempts=[OSError("tls stack broken")])

    def _fake_urllib_get_text(url, params=None, *, timeout=15.0):
        return '{"sign":"sign-2","imgurl":"https://passport.baidu.com/qr"}', {"BAIDUID": "cookie-1"}

    monkeypatch.setattr(baidu_qr, "_urllib_get_text", _fake_urllib_get_text)
    result = asyncio.run(baidu_qr.request_qr())
    assert result["cookies"] == {"BAIDUID": "cookie-1"}


def test_poll_qr_connection_timeout_is_error(monkeypatch):
    _install_fake_session(monkeypatch, attempts=[aiohttp.ConnectionTimeoutError("passport.baidu.com", 443)])
    result = asyncio.run(baidu_qr.poll_qr("sign-1"))
    assert result["status"] == "error"
    assert "超时" in result["error"]


def test_poll_qr_read_timeout_is_waiting(monkeypatch):
    _install_fake_session(monkeypatch, attempts=[asyncio.TimeoutError()])
    assert asyncio.run(baidu_qr.poll_qr("sign-1")) == {"status": "waiting"}


def test_poll_qr_falls_back_to_urllib_without_tls_error(monkeypatch):
    _install_fake_session(monkeypatch, attempts=[OSError("aiohttp unavailable")])

    def _fake_urllib_get_text(url, params=None, *, timeout=15.0):
        return '{"errno":0,"channel_v":"{\\"v\\":\\"v-token\\"}"}', {}

    monkeypatch.setattr(baidu_qr, "_urllib_get_text", _fake_urllib_get_text)
    result = asyncio.run(baidu_qr.poll_qr("sign-1"))
    assert result == {"status": "confirmed", "v": "v-token"}


def test_complete_login_falls_back_to_urllib(monkeypatch):
    _install_fake_session(monkeypatch, attempts=[OSError("tls stack broken")])

    def _fake_urllib_get_text(url, params=None, *, timeout=15.0):
        assert params["bduss"] == "v-token"
        return (
            '{"data":{"session":{"bduss":"BDUSS-1","stoken":"STOKEN-1"},"user":{"displayName":"tester"}}}',
            {},
        )

    monkeypatch.setattr(baidu_qr, "_urllib_get_text", _fake_urllib_get_text)
    result = asyncio.run(baidu_qr.complete_login("v-token"))
    assert result["cookie"] == "BDUSS=BDUSS-1; STOKEN=STOKEN-1"
    assert result["user_account"] == "tester"


def test_complete_login_error_detail_redacted(monkeypatch):
    _install_fake_session(
        monkeypatch,
        attempts=[(500, "error bduss=SECRET-V&stoken=SECRET-S")],
    )

    def _fail_urllib(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr(baidu_qr, "_urllib_get_text", _fail_urllib)
    try:
        asyncio.run(baidu_qr.complete_login("v-token"))
    except baidu_qr.BaiduQrError as exc:
        assert "SECRET-V" not in str(exc)
        assert "<redacted>" in str(exc)
    else:
        raise AssertionError("HTTP 500 must raise BaiduQrError")


# ---- 百度 OpenAPI 诊断/secret 脱敏（同属百度登录链路） ----


def test_openapi_mask_secret_does_not_leak_short_secrets():
    assert openapi._mask_secret("") == ""
    assert openapi._mask_secret("abcd1234") == "<redacted>"
    masked = openapi._mask_secret("abcdefghijklmnop")  # 16 位
    assert masked.startswith("ab") and masked.endswith("op") and "cdefghijklmn" not in masked
    assert openapi._mask_secret("tok-1234567890abcdef") == "tok-…cdef"


def test_openapi_diagnostics_sanitizes_nested_tokens_and_urls():
    error = openapi.BaiduOpenApiError(
        "请求 https://pan.baidu.com/rest?access_token=SECRET-TOKEN-VALUE 失败",
        diagnostics={
            "url": "https://pan.baidu.com/rest?access_token=SECRET-TOKEN-VALUE",
            "params": {"access_token": "SECRET-TOKEN-VALUE", "method": "list"},
            "response": {"session_secret": "SECRET-SESSION", "ok": 1},
            "headers": [{"Authorization": "Bearer SECRET-BEARER"}],
        },
    )
    text = str(error)
    assert "SECRET-TOKEN-VALUE" not in text
    assert "<redacted>" in text

    dumped = str(error.diagnostics)
    for secret in ("SECRET-TOKEN-VALUE", "SECRET-SESSION", "SECRET-BEARER"):
        assert secret not in dumped
    assert error.diagnostics["params"]["method"] == "list"


def test_openapi_error_message_redacts_cookie_and_device_code():
    error = openapi.BaiduOpenApiError(
        "legacy 失败：cookie=BDUSS%3DSECRET&device_code=DEVCODE1234567890&randsk=RANDSK"
    )
    message = str(error)
    for secret in ("SECRET", "DEVCODE1234567890", "RANDSK"):
        assert secret not in message


def test_qr_poll_scanned_with_token_is_not_confirmed():
    payload = {"errno": 0, "channel_v": json.dumps({"status": 1, "v": "temporary-token"})}
    assert parse_qr_poll_payload(json.dumps(payload))["status"] == "scanned"


def test_qr_poll_confirmed_status_zero():
    payload = {"errno": 0, "channel_v": json.dumps({"status": 0, "v": "confirmed-token"})}
    result = parse_qr_poll_payload(json.dumps(payload))
    assert result == {"status": "confirmed", "v": "confirmed-token"}
