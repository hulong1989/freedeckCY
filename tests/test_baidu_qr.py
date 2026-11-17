"""百度二维码轮询响应解析。"""

from __future__ import annotations

import json

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
