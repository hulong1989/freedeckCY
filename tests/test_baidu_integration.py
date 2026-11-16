"""百度网盘 OpenAPI：来源识别、token 刷新、安装计划与任务。"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import baidu_openapi_client
import tianyi_service as svc
from game_catalog import GameCatalogEntry
from tianyi_client import ResolvedFile, ResolvedShare
from tianyi_service import TianyiService
from tianyi_store import BaiduOpenApiLoginState, TianyiSettings, TianyiStateStore


def _service(tmp_path):
    service = TianyiService.__new__(TianyiService)
    service.store = TianyiStateStore(str(tmp_path / "state.json"))
    service.store.settings = TianyiSettings(download_dir=str(tmp_path / "dl"), install_dir=str(tmp_path / "in"))
    service.plugin = SimpleNamespace(downloads_dir=str(tmp_path / "dl"), server_running=False, server_port=0)
    service._invalidate_panel_cache = lambda **kwargs: None
    service._baidu_qr_lock = asyncio.Lock()
    service._baidu_qr_session = {}
    service._baidu_device_lock = asyncio.Lock()
    service._baidu_device_login = {}
    return service


class _FakeCatalog:
    def __init__(self, entry):
        self.entry = entry

    def get_by_game_id(self, game_id):
        return self.entry if str(self.entry.game_id) == str(game_id) else None


def test_share_provider_detection():
    assert svc._share_provider("https://pan.baidu.com/s/1abc") == "baidu"
    assert svc._share_provider("https://yun.baidu.com/s/1abc") == "baidu"
    assert svc._share_provider("https://cloud.189.cn/t/abc") == "tianyi"
    assert svc._share_provider("https://example.com") == ""


def test_baidu_token_refresh(tmp_path, monkeypatch):
    service = _service(tmp_path)
    service.store.baidu_openapi = BaiduOpenApiLoginState(
        app_key="key",
        secret_key="secret",
        access_token="old",
        refresh_token="refresh",
        expires_at=0,
    )

    async def _fake_refresh(**kwargs):
        assert kwargs["refresh_token"] == "refresh"
        return {"access_token": "new", "refresh_token": "refresh2", "expires_at": 9999999999}

    monkeypatch.setattr(svc, "refresh_baidu_oauth_token", _fake_refresh)
    token = asyncio.run(service._ensure_baidu_openapi_access_token(force_refresh=True))
    assert token == "new"
    assert service.store.baidu_openapi.refresh_token == "refresh2"


def test_build_install_plan_baidu_does_not_require_tianyi_login(tmp_path, monkeypatch):
    service = _service(tmp_path)
    entry = GameCatalogEntry(
        game_id="42",
        title="Baidu Game",
        category_parent="5",
        categories="动作冒险",
        down_url="https://pan.baidu.com/s/1abc",
        pwd="x9k2",
        openpath="BaiduGame/BaiduGame.7z",
        size_bytes=0,
        size_text="",
        platform="pc",
    )
    service.catalog = _FakeCatalog(entry)
    service.store.baidu_openapi = BaiduOpenApiLoginState(
        app_key="key",
        secret_key="secret",
        access_token="token",
        refresh_token="refresh",
    )

    async def _fake_token(force_refresh=False):
        return "token"

    async def _fake_resolve(*, share_url):
        resolved = ResolvedShare(
            share_code="1abc",
            share_id="123",
            pwd="x9k2",
            files=[ResolvedFile(file_id="f1", name="BaiduGame.7z", size=100, is_folder=False)],
        )
        return resolved, {"provider": "baidu_openapi", "share_id": "123", "files": {"f1": {"file_id": "f1"}}}

    monkeypatch.setattr(service, "_ensure_baidu_openapi_access_token", _fake_token)
    monkeypatch.setattr(svc, "resolve_baidu_openapi_share_url", _fake_resolve)

    plan = asyncio.run(service._build_install_plan(game_id="42"))
    assert plan["provider"] == "baidu_openapi"
    assert plan["share_url"] == entry.down_url
    assert plan["files"][0]["file_id"] == "f1"


def test_create_baidu_tasks_uses_pan_headers(tmp_path, monkeypatch):
    service = _service(tmp_path)
    calls = []

    class _FakeAria2:
        async def ensure_running(self):
            calls.append(("ensure",))

        async def add_uri(self, **kwargs):
            calls.append(("add", kwargs))
            return "gid1"

    service.aria2 = _FakeAria2()

    async def _fake_direct(share_ctx, file_id):
        return "https://d.pcs.baidu.com/file/demo"

    monkeypatch.setattr(service, "_fetch_baidu_direct_url", _fake_direct)
    plan = {
        "provider": "baidu_openapi",
        "share_url": "https://pan.baidu.com/s/1abc",
        "share_ctx": {"provider": "baidu_openapi"},
        "share_id": "123",
        "share_code": "1abc",
        "game_id": "42",
        "game_title": "Baidu Game",
        "openpath": "BaiduGame/BaiduGame.7z",
        "download_dir": str(tmp_path / "dl"),
        "platform": "pc",
        "files": [{"file_id": "f1", "name": "BaiduGame.7z", "size": 100}],
    }
    tasks = asyncio.run(service._create_tasks_from_plan(plan=plan, split=8))
    add_call = [item for item in calls if item[0] == "add"][0][1]
    assert add_call["cookie"] == ""
    assert add_call["referer"] == "https://pan.baidu.com/disk/home"
    assert add_call["user_agent"] == "pan.baidu.com"
    assert tasks[0].provider == "baidu_openapi"
    assert tasks[0].share_ctx["provider"] == "baidu_openapi"


def test_exchange_baidu_code_stores_tokens(tmp_path, monkeypatch):
    service = _service(tmp_path)
    service.store.baidu_openapi = BaiduOpenApiLoginState(app_key="key", secret_key="secret")

    async def _fake_exchange(**kwargs):
        assert kwargs["code"] == "code"
        return {"access_token": "access", "refresh_token": "refresh", "expires_at": 1234567890}

    async def _fake_user(**kwargs):
        return {"netdisk_name": "tester"}

    monkeypatch.setattr(svc, "exchange_baidu_oauth_code", _fake_exchange)
    monkeypatch.setattr(svc, "fetch_baidu_openapi_user_info", _fake_user)
    result = asyncio.run(service.exchange_baidu_openapi_code("code"))
    assert result["logged_in"] is True
    assert service.store.baidu_openapi.access_token == "access"
    assert service.store.baidu_openapi.user_account == "tester"


def test_build_install_plan_baidu_web_cookie(tmp_path, monkeypatch):
    service = _service(tmp_path)
    service.store.baidu_login.cookie = "BDUSS=demo"
    entry = GameCatalogEntry(
        game_id="43",
        title="Baidu Web Game",
        category_parent="5",
        categories="动作冒险",
        down_url="https://pan.baidu.com/s/1web",
        pwd="x9k2",
        openpath="BaiduWeb/BaiduWeb.7z",
        size_bytes=0,
        size_text="",
        platform="pc",
    )
    service.catalog = _FakeCatalog(entry)

    async def _fake_resolve(share_url, cookie):
        assert cookie == "BDUSS=demo"
        return (
            ResolvedShare(
                share_code="1web",
                share_id="456",
                pwd="x9k2",
                files=[ResolvedFile(file_id="f1", name="BaiduWeb.7z", size=100, is_folder=False)],
            ),
            {"provider": "baidu", "share_id": "456", "files": {"f1": {"file_id": "f1"}}},
        )

    monkeypatch.setattr(svc, "resolve_baidu_share", _fake_resolve)
    plan = asyncio.run(service._build_install_plan(game_id="43"))
    assert plan["provider"] == "baidu"


def test_create_baidu_web_tasks_uses_cookie(tmp_path, monkeypatch):
    service = _service(tmp_path)
    service.store.baidu_login.cookie = "BDUSS=demo"
    calls = []

    class _FakeAria2:
        async def ensure_running(self):
            return None

        async def add_uri(self, **kwargs):
            calls.append(kwargs)
            return "gid1"

    service.aria2 = _FakeAria2()

    async def _fake_direct(share_ctx, file_id):
        return "https://d.pcs.baidu.com/file/demo"

    monkeypatch.setattr(service, "_fetch_baidu_web_direct_url", _fake_direct)
    plan = {
        "provider": "baidu",
        "share_url": "https://pan.baidu.com/s/1web",
        "share_ctx": {"provider": "baidu"},
        "share_id": "456",
        "share_code": "1web",
        "game_id": "43",
        "game_title": "Baidu Web Game",
        "openpath": "BaiduWeb/BaiduWeb.7z",
        "download_dir": str(tmp_path / "dl"),
        "platform": "pc",
        "files": [{"file_id": "f1", "name": "BaiduWeb.7z", "size": 100}],
    }
    tasks = asyncio.run(service._create_tasks_from_plan(plan=plan, split=8))
    assert calls[0]["cookie"] == "BDUSS=demo"
    assert calls[0]["referer"] == "https://pan.baidu.com/disk/home"
    assert tasks[0].provider == "baidu"


def test_baidu_qr_login_flow(tmp_path, monkeypatch):
    service = _service(tmp_path)

    async def _fake_qr():
        return {"sign": "sign1", "imgurl": "https://passport.baidu.com/qr.png"}

    async def _fake_image(url):
        return b"png"

    async def _fake_poll(sign, timeout=8.0, **kwargs):
        assert sign == "sign1"
        return {"status": "confirmed", "v": "v-token"}

    async def _fake_complete(v, **kwargs):
        assert v == "v-token"
        return {"cookie": "BDUSS=demo; STOKEN=s", "user_account": "tester"}

    monkeypatch.setattr(svc, "request_qr", _fake_qr)
    monkeypatch.setattr(svc, "fetch_qr_image", _fake_image)
    started = asyncio.run(service.start_baidu_qr_login())
    assert started["stage"] == "waiting"
    assert started["qr_data_url"].startswith("data:image/png;base64,")
    monkeypatch.setattr(svc, "poll_qr", _fake_poll)
    monkeypatch.setattr(svc, "complete_login", _fake_complete)
    result = asyncio.run(service.poll_baidu_qr_login())
    assert result["stage"] == "success"
    assert service.store.baidu_login.cookie.startswith("BDUSS=demo")
    assert service.store.baidu_login.user_account == "tester"
