from __future__ import annotations

import asyncio
import importlib


def _load_module():
    return importlib.import_module("baidu_client")


def test_resolve_baidu_share_retries_other_candidates_after_http_302(monkeypatch) -> None:
    module = _load_module()

    class FakeCookieJar:
        def update_cookies(self, *args, **kwargs) -> None:
            return None

        def filter_cookies(self, *args, **kwargs):
            return {}

    class FakeResponse:
        def __init__(self, *, url: str, status: int, body: str = "", headers=None):
            self.url = url
            self.status = status
            self._body = body
            self.headers = dict(headers or {})

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def text(self, *args, **kwargs) -> str:
            return self._body

    response_map = {
        "https://pan.baidu.com/": FakeResponse(url="https://pan.baidu.com/", status=200, body=""),
        "https://pan.baidu.com/share/init?surl=demoShare&pwd=6666": FakeResponse(
            url="https://pan.baidu.com/share/init?surl=demoShare&pwd=6666",
            status=302,
            body="",
            headers={"Location": "baiduboxapp://v7/share?from=demo&surl=demoShare"},
        ),
        "https://pan.baidu.com/share/init?surl=demoShare": FakeResponse(
            url="https://pan.baidu.com/share/init?surl=demoShare",
            status=302,
            body="",
            headers={"Location": "/s/1demoShare?pwd=6666"},
        ),
        "https://pan.baidu.com/s/1demoShare?pwd=6666": FakeResponse(
            url="https://pan.baidu.com/s/1demoShare?pwd=6666",
            status=200,
            body='{"shareid":6255541619,"share_uk":2175769893,"sign":"demo-sign","timestamp":1710000000}',
        ),
    }

    class FakeSession:
        def __init__(self, *args, **kwargs):
            self.cookie_jar = FakeCookieJar()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, url, headers=None, allow_redirects=True):
            normalized = str(url or "").strip()
            if normalized not in response_map:
                raise AssertionError(f"unexpected GET url: {normalized}")
            return response_map[normalized]

    async def _fake_share_list(
        session,
        *,
        share_url: str,
        share_id: int,
        uk: int,
        page: int = 1,
        num: int = 200,
        dir_path: str = "",
        sekey: str = "",
        ssl_context=None,
    ):
        assert share_url == "https://pan.baidu.com/s/1demoShare?pwd=6666"
        assert share_id == 6255541619
        assert uk == 2175769893
        assert dir_path == ""
        return {
            "errno": 0,
            "list": [
                {
                    "fs_id": "123456",
                    "server_filename": "DemoGame.7z",
                    "size": 13579,
                    "isdir": 0,
                    "path": "/DemoGame.7z",
                }
            ],
        }

    monkeypatch.setattr(module.aiohttp, "ClientSession", FakeSession)
    monkeypatch.setattr(module.aiohttp, "TCPConnector", lambda ssl=None: None)
    monkeypatch.setattr(module, "_build_ssl_context", lambda: (None, {"mode": "test"}))
    monkeypatch.setattr(module, "_share_list", _fake_share_list)

    resolved, share_ctx = asyncio.run(module.resolve_baidu_share("https://pan.baidu.com/s/1demoShare?pwd=6666", ""))

    assert resolved.share_code == "demoShare"
    assert resolved.share_id == "6255541619"
    assert resolved.pwd == "6666"
    assert len(resolved.files) == 1
    assert resolved.files[0].file_id == "123456"
    assert resolved.files[0].name == "DemoGame.7z"
    assert share_ctx["share_url"] == "https://pan.baidu.com/s/1demoShare?pwd=6666"
    assert share_ctx["share_id"] == 6255541619
    assert share_ctx["uk"] == 2175769893
