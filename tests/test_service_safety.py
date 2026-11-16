"""安全边界回归测试：分享链接校验、状态文件权限、本地 API 的 Host/Origin 守卫。"""

from __future__ import annotations

import os
import stat

import pytest
from aiohttp import web
from aiohttp.test_utils import make_mocked_request

import server_manager
import tianyi_service as svc
from tianyi_store import TianyiStateStore


@pytest.mark.parametrize(
    "url",
    [
        "https://cloud.189.cn/t/abcdEFG",
        "https://cloud.189.cn/t/abcdEFG?pwd=1234",
        "https://h5.cloud.189.cn/web/share?code=xyz",
        "https://api.cloud.189.cn/open/x",
        "https://t.189.cn/x",
    ],
)
def test_accepts_tianyi_share_urls(url):
    assert svc._is_tianyi_share_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not-a-url",
        "file:///etc/passwd",
        "ftp://cloud.189.cn/t/x",
        "https://evil.example/t/x",
        "https://cloud.189.cn.evil.example/t/x",
        "https://evil.example/cloud.189.cn/t/x",
    ],
)
def test_rejects_non_tianyi_share_urls(url):
    assert svc._is_tianyi_share_url(url) is False


def test_state_file_and_dir_permissions(tmp_path):
    store = TianyiStateStore(str(tmp_path / "state" / "state.json"))
    store.set_settings(download_dir=str(tmp_path))
    store.save()

    file_mode = stat.S_IMODE(os.stat(store.state_file).st_mode)
    dir_mode = stat.S_IMODE(os.stat(os.path.dirname(store.state_file)).st_mode)

    assert file_mode == 0o600
    assert dir_mode == 0o700


async def _ok_handler(request):
    return web.json_response({"ok": True})


@pytest.mark.asyncio
async def test_rejects_cross_site_origin():
    request = make_mocked_request(
        "POST",
        "/api/tianyi/settings",
        headers={"Origin": "https://evil.example", "Host": "127.0.0.1:59271"},
    )
    response = await server_manager.cors_middleware(request, _ok_handler)
    assert response.status == 403


@pytest.mark.asyncio
async def test_rejects_foreign_host_header():
    """防 DNS rebinding：Host 不是回环地址一律拒绝。"""
    request = make_mocked_request(
        "GET",
        "/api/tianyi/state",
        headers={"Host": "evil.example:59271"},
    )
    response = await server_manager.cors_middleware(request, _ok_handler)
    assert response.status == 403


@pytest.mark.asyncio
async def test_rejects_cross_site_sec_fetch():
    request = make_mocked_request(
        "POST",
        "/api/tianyi/install/start",
        headers={
            "Host": "127.0.0.1:59271",
            "Sec-Fetch-Site": "cross-site",
        },
    )
    response = await server_manager.cors_middleware(request, _ok_handler)
    assert response.status == 403


@pytest.mark.asyncio
async def test_allows_local_page_and_echoes_origin():
    origin = "http://127.0.0.1:59271"
    request = make_mocked_request(
        "POST",
        "/api/tianyi/settings",
        headers={"Origin": origin, "Host": "127.0.0.1:59271"},
    )
    response = await server_manager.cors_middleware(request, _ok_handler)
    assert response.status == 200
    assert response.headers.get("Access-Control-Allow-Origin") == origin


@pytest.mark.asyncio
async def test_get_has_no_wildcard_cors():
    request = make_mocked_request(
        "GET",
        "/api/tianyi/state",
        headers={"Host": "127.0.0.1:59271"},
    )
    response = await server_manager.cors_middleware(request, _ok_handler)
    assert response.status == 200
    assert "Access-Control-Allow-Origin" not in response.headers


@pytest.mark.asyncio
async def test_catalog_handler_passes_platform_and_category(monkeypatch):
    import tianyi_http

    captured = {}

    class _FakeService:
        async def list_catalog(self, query, page, page_size, platform="", category="", sort=""):
            captured.update(
                {
                    "query": query,
                    "page": page,
                    "page_size": page_size,
                    "platform": platform,
                    "category": category,
                    "sort": sort,
                }
            )
            return {"total": 0, "page": 1, "page_size": 50, "items": [], "platforms": [], "categories": []}

    monkeypatch.setattr(tianyi_http, "_service", lambda plugin: _FakeService())
    request = make_mocked_request(
        "GET",
        "/api/tianyi/catalog?q=zelda&platform=switch&category=%E5%8A%A8%E4%BD%9C%E5%86%92%E9%99%A9&page=2&page_size=30",
    )
    response = await tianyi_http.handle_catalog(request, object())

    assert response.status == 200
    assert captured["query"] == "zelda"
    assert captured["platform"] == "switch"
    assert captured["category"] == "动作冒险"
    assert captured["page"] == 2
    assert captured["page_size"] == 30


def _json_request(path: str, body: dict):
    """构造带 JSON body 的 mock request（aiohttp 需要 StreamReader）。"""
    import json
    from unittest.mock import Mock

    from aiohttp.streams import StreamReader

    reader = StreamReader(Mock(), 2**16)
    reader.feed_data(json.dumps(body).encode("utf-8"))
    reader.feed_eof()
    return make_mocked_request(
        "POST",
        path,
        headers={"Content-Type": "application/json"},
        payload=reader,
    )


@pytest.mark.asyncio
async def test_installed_handlers_call_service(monkeypatch):
    import json
    import tianyi_http

    captured = {}

    class _FakeService:
        async def list_installed_games(self):
            return {"total": 0, "items": []}

        async def launch_installed_game(self, game_id):
            captured["launch"] = game_id
            return {"launched": True}

        async def open_installed_folder(self, game_id):
            captured["open"] = game_id
            return {"opened": True}

        async def uninstall_installed_game(self, **kwargs):
            captured["uninstall"] = kwargs
            return {"removed": True}

        async def get_diagnostics(self):
            return {"version": "0.5.0"}

        async def export_diagnostics(self):
            return b"PKfake"

        async def check_update(self):
            return {"ok": True, "current": "0.5.0", "latest": "0.5.0", "has_update": False}

    monkeypatch.setattr(tianyi_http, "_service", lambda plugin: _FakeService())

    list_response = await tianyi_http.handle_installed_games(
        make_mocked_request("GET", "/api/tianyi/installed"), object()
    )
    assert list_response.status == 200

    launch_request = _json_request("/api/tianyi/installed/launch", {"game_id": "g-1"})
    launch_response = await tianyi_http.handle_installed_launch(launch_request, object())
    assert launch_response.status == 200
    assert captured["launch"] == "g-1"

    uninstall_request = _json_request(
        "/api/tianyi/installed/uninstall",
        {"game_id": "g-1", "install_path": "/tmp/g", "delete_compatdata": True},
    )
    uninstall_response = await tianyi_http.handle_installed_uninstall(uninstall_request, object())
    assert uninstall_response.status == 200
    assert captured["uninstall"]["delete_compatdata"] is True

    diagnostics_response = await tianyi_http.handle_diagnostics(
        make_mocked_request("GET", "/api/tianyi/diagnostics"), object()
    )
    assert diagnostics_response.status == 200

    export_response = await tianyi_http.handle_diagnostics_export(
        make_mocked_request("GET", "/api/tianyi/diagnostics/export"), object()
    )
    assert export_response.status == 200
    assert export_response.content_type == "application/zip"

    update_response = await tianyi_http.handle_update_check(
        make_mocked_request("GET", "/api/tianyi/update-check"), object()
    )
    assert update_response.status == 200


def test_parse_version_compare():
    assert svc._parse_version("v0.5.0") == (0, 5, 0)
    assert svc._parse_version("0.4.0") == (0, 4, 0)
    assert svc._parse_version("v0.5.0-pre") == (0, 5, 0)
    assert svc._parse_version("") == (0,)
    assert svc._parse_version("0.5.0") > svc._parse_version("0.4.9")
