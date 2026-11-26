"""插件更新准备（交给 Decky 安装）测试。"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import update_flow
from tianyi_service import TianyiService


def _service(update):
    service = TianyiService.__new__(TianyiService)
    service.store = SimpleNamespace(settings=SimpleNamespace(catalog_url=""))
    service._update_cache = None
    service._update_cache_at = 0.0
    service._update_tls_insecure = False

    async def fake_check(*args, **kwargs):
        return dict(update)

    service.check_update = fake_check
    return service


def test_prepare_update_install_uses_arch_asset_and_digest(monkeypatch):
    monkeypatch.setattr(update_flow.platform, "machine", lambda: "x86_64")
    service = _service({
        "ok": True,
        "current": "0.28.16",
        "latest": "0.28.17",
        "has_update": True,
        "assets": [
            {"name": "freedeckCY-v0.28.17-arm64.zip", "url": "https://example.com/a.zip", "size": 2, "digest": "sha256:bbbb"},
            {"name": "freedeckCY-v0.28.17.zip", "url": "https://example.com/x.zip", "size": 10, "digest": "sha256:aaaa"},
        ],
    })
    result = asyncio.run(service.prepare_update_install())
    assert result["ok"] is True
    assert result["url"] == "https://example.com/x.zip"
    assert result["sha256"] == "aaaa"
    assert result["filename"] == "freedeckCY-v0.28.17.zip"
    assert result["version"] == "0.28.17"


def test_prepare_update_install_picks_arm64(monkeypatch):
    monkeypatch.setattr(update_flow.platform, "machine", lambda: "aarch64")
    service = _service({
        "ok": True,
        "current": "0.28.16",
        "latest": "0.28.17",
        "has_update": True,
        "assets": [
            {"name": "freedeckCY-v0.28.17-arm64.zip", "url": "https://example.com/a.zip", "size": 2, "digest": "sha256:bbbb"},
            {"name": "freedeckCY-v0.28.17.zip", "url": "https://example.com/x.zip", "size": 10, "digest": "sha256:aaaa"},
        ],
    })
    result = asyncio.run(service.prepare_update_install())
    assert result["url"] == "https://example.com/a.zip"
    assert result["sha256"] == "bbbb"


def test_prepare_update_install_requires_hash(monkeypatch):
    monkeypatch.setattr(update_flow.platform, "machine", lambda: "x86_64")
    service = _service({
        "ok": True,
        "current": "0.28.16",
        "latest": "0.28.17",
        "has_update": True,
        "assets": [
            {"name": "freedeckCY-v0.28.17.zip", "url": "https://example.com/x.zip", "size": 10},
        ],
    })
    result = asyncio.run(service.prepare_update_install())
    assert result["ok"] is False
    assert "SHA256" in result["message"]


def test_prepare_update_install_no_update(monkeypatch):
    monkeypatch.setattr(update_flow.platform, "machine", lambda: "x86_64")
    service = _service({"ok": True, "current": "0.28.17", "latest": "0.28.17", "has_update": False, "assets": []})
    result = asyncio.run(service.prepare_update_install())
    assert result["ok"] is False
    assert "最新" in result["message"]
