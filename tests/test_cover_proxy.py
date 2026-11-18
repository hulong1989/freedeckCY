"""封面本地缓存代理的安全边界。"""

from __future__ import annotations

import asyncio

import pytest

from tests.test_catalog_update import _service


def test_cover_proxy_rejects_non_cdn_host(tmp_path):
    service, _state_dir = _service(tmp_path)
    with pytest.raises(ValueError):
        asyncio.run(service.fetch_cover_image("https://evil.example/x.jpg"))


def test_cover_proxy_rejects_non_http_scheme(tmp_path):
    service, _state_dir = _service(tmp_path)
    with pytest.raises(ValueError):
        asyncio.run(service.fetch_cover_image("file:///etc/passwd"))


def test_cover_proxy_base_empty_when_server_stopped(tmp_path):
    service, _state_dir = _service(tmp_path)
    service.plugin = type("Plugin", (), {"server_running": False, "server_port": 0})()
    assert service.get_cover_proxy_base() == ""
