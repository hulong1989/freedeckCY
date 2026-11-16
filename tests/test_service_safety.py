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
