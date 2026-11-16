from __future__ import annotations

import asyncio
import importlib


def _load_module():
    return importlib.import_module("baidu_openapi_client")


def test_refresh_baidu_oauth_token_parses_expiry(monkeypatch) -> None:
    module = _load_module()
    request_calls = []

    async def _fake_request_json(method: str, url: str, *, params=None, data=None, headers=None):
        request_calls.append(
            {
                "method": method,
                "url": url,
                "params": dict(params or {}),
                "data": dict(data or {}),
            }
        )
        return {
            "access_token": "access-token-new",
            "refresh_token": "refresh-token-new",
            "expires_in": 7200,
        }

    monkeypatch.setattr(module, "_request_json", _fake_request_json)
    monkeypatch.setattr(module.time, "time", lambda: 1700000000)

    refreshed = asyncio.run(
        module.refresh_baidu_oauth_token(
            app_key="demo-app",
            secret_key="demo-secret",
            refresh_token="refresh-token-old",
        )
    )

    assert refreshed == {
        "access_token": "access-token-new",
        "refresh_token": "refresh-token-new",
        "expires_in": 7200,
        "expires_at": 1700007200,
        "scope": "",
    }
    assert request_calls == [
        {
            "method": "POST",
            "url": module.BAIDU_OPENAPI_TOKEN_URL,
            "params": {},
            "data": {
                "grant_type": "refresh_token",
                "refresh_token": "refresh-token-old",
                "client_id": "demo-app",
                "client_secret": "demo-secret",
            },
        }
    ]


def test_resolve_baidu_openapi_resource_reads_file_meta_from_parent_listing(monkeypatch) -> None:
    module = _load_module()

    async def _fake_list_dir(*, access_token: str, path: str):
        assert access_token == "access-token"
        assert path == "/Freedeck/Games"
        return [
            {
                "fs_id": "123456",
                "path": "/Freedeck/Games/BlackMythWukong.7z",
                "server_filename": "BlackMythWukong.7z",
                "size": 987654321,
                "isdir": 0,
            }
        ]

    monkeypatch.setattr(module, "_list_baidu_openapi_dir", _fake_list_dir)

    resolved, share_ctx = asyncio.run(
        module.resolve_baidu_openapi_resource(
            access_token="access-token",
            descriptor={
                "path": "/Freedeck/Games/BlackMythWukong.7z",
                "display_name": "BlackMythWukong.7z",
            },
        )
    )

    assert resolved.share_code == "baidu-openapi"
    assert resolved.share_id == "/Freedeck/Games/BlackMythWukong.7z"
    assert len(resolved.files) == 1
    assert resolved.files[0].file_id == "123456"
    assert resolved.files[0].name == "BlackMythWukong.7z"
    assert share_ctx["provider"] == "baidu_openapi"
    assert share_ctx["descriptor"]["path"] == "/Freedeck/Games/BlackMythWukong.7z"
    assert share_ctx["files"]["123456"]["path"] == "/Freedeck/Games/BlackMythWukong.7z"


def test_fetch_baidu_openapi_download_url_fetches_dlink_and_updates_share_ctx(monkeypatch) -> None:
    module = _load_module()

    async def _fake_fetch_metas(*, access_token: str, fs_ids, dlink: bool):
        assert access_token == "access-token"
        assert list(fs_ids) == ["123456"]
        assert dlink is True
        return [
            {
                "fs_id": "123456",
                "path": "/Freedeck/Games/BlackMythWukong.7z",
                "server_filename": "BlackMythWukong.7z",
                "size": 987654321,
                "isdir": 0,
                "dlink": "https://d.pcs.baidu.com/file/demo-dlink",
            }
        ]

    monkeypatch.setattr(module, "_fetch_baidu_openapi_metas_by_fsids", _fake_fetch_metas)

    share_ctx = {"files": {}}
    direct_url = asyncio.run(
        module.fetch_baidu_openapi_download_url(
            access_token="access-token",
            share_ctx=share_ctx,
            file_id="123456",
        )
    )

    assert direct_url.startswith("https://d.pcs.baidu.com/file/demo-dlink")
    assert "access_token=access-token" in direct_url
    assert "clienttype=0" in direct_url
    assert share_ctx["files"]["123456"]["dlink"] == "https://d.pcs.baidu.com/file/demo-dlink"


def test_resolve_baidu_openapi_share_url_wraps_public_share_as_official(monkeypatch) -> None:
    module = _load_module()

    async def _fake_resolve_baidu_share(share_url: str, cookie: str):
        assert share_url == "https://pan.baidu.com/s/1demoShare?pwd=6666"
        assert cookie == ""
        resolved = module.ResolvedShare(
            share_code="demoShare",
            share_id="6255541619",
            pwd="6666",
            files=[
                module.ResolvedFile(
                    file_id="123456",
                    name="DemoGame.7z",
                    size=13579,
                    is_folder=False,
                    path="/DemoGame.7z",
                    folder_path="/",
                )
            ],
        )
        return resolved, {
            "share_url": "https://pan.baidu.com/share/init?surl=demoShare&pwd=6666",
            "canonical_url": "https://pan.baidu.com/share/init?surl=demoShare&pwd=6666",
            "share_id": 6255541619,
            "uk": 2175769893,
            "surl": "demoShare",
            "pwd": "6666",
            "randsk": "demo-randsk",
            "sekey": "demo-sekey",
        }

    monkeypatch.setattr(module, "resolve_baidu_share", _fake_resolve_baidu_share)

    resolved, share_ctx = asyncio.run(
        module.resolve_baidu_openapi_share_url(share_url="https://pan.baidu.com/s/1demoShare?pwd=6666")
    )

    assert resolved.share_id == "6255541619"
    assert share_ctx["provider"] == "baidu_openapi"
    assert share_ctx["share_source"] == "public_share_url"
    assert share_ctx["share_id"] == "6255541619"
    assert share_ctx["uk"] == "2175769893"
    assert share_ctx["sekey"] == "demo-sekey"
    assert share_ctx["files"]["123456"]["name"] == "DemoGame.7z"


def test_fetch_baidu_openapi_download_url_reuses_cached_transfer_fs_id(monkeypatch) -> None:
    module = _load_module()
    request_calls = []
    meta_calls = []

    async def _fake_request_json(method: str, url: str, *, params=None, data=None, headers=None):
        request_calls.append(
            {
                "method": method,
                "url": url,
                "params": dict(params or {}),
                "data": dict(data or {}),
                "headers": dict(headers or {}),
            }
        )
        return {}

    async def _fake_fetch_metas(*, access_token: str, fs_ids, dlink: bool):
        meta_calls.append({"access_token": access_token, "fs_ids": list(fs_ids), "dlink": dlink})
        assert access_token == "access-token"
        assert list(fs_ids) == ["987654"]
        assert dlink is True
        return [
            {
                "fs_id": "987654",
                "path": "/FreedeckTmp/DemoGame.7z",
                "server_filename": "DemoGame.7z",
                "size": 13579,
                "isdir": 0,
                "dlink": "https://d.pcs.baidu.com/file/demo-reuse-dlink",
            }
        ]

    monkeypatch.setattr(module, "_request_json", _fake_request_json)
    monkeypatch.setattr(module, "_fetch_baidu_openapi_metas_by_fsids", _fake_fetch_metas)

    share_ctx = {
        "provider": "baidu_openapi",
        "share_source": "public_share_url",
        "share_id": "6255541619",
        "uk": "2175769893",
        "files": {
            "123456": {
                "file_id": "123456",
                "name": "DemoGame.7z",
                "size": 13579,
                "is_folder": False,
                "transfer_fs_id": "987654",
                "transfer_dir": "/FreedeckTmp",
                "transfer_path": "/FreedeckTmp/DemoGame.7z",
            }
        },
    }

    direct_url = asyncio.run(
        module.fetch_baidu_openapi_download_url(
            access_token="access-token",
            share_ctx=share_ctx,
            file_id="123456",
        )
    )

    assert direct_url.startswith("https://d.pcs.baidu.com/file/demo-reuse-dlink")
    assert "access_token=access-token" in direct_url
    assert request_calls == []
    assert meta_calls == [{"access_token": "access-token", "fs_ids": ["987654"], "dlink": True}]
    assert share_ctx["files"]["123456"]["dlink"] == "https://d.pcs.baidu.com/file/demo-reuse-dlink"


