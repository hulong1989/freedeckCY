"""设置页“更新游戏列表”：服务器 CSV 条件下载、校验、本地优先加载。"""

from __future__ import annotations

import asyncio
from pathlib import Path

import config
import game_catalog
from tianyi_service import TianyiService
from tianyi_store import TianyiStateStore


def _valid_csv() -> bytes:
    rows = ["game_id,title,category_parent,categories,down_url,pwd,openpath,filesize_z,list_filesize,platform,cover_url,cover_portrait_url,steam_appid"]
    for index in range(1, 16):
        rows.append(f"{index},Game {index},5,动作冒险,https://cloud.189.cn/t/code{index},,Game {index}/Game.7z,100,100 B,pc,,,0")
    return ("\n".join(rows) + "\n").encode("utf-8")


def _service(tmp_path):
    state_dir = tmp_path / "state" / "tianyi"
    state_dir.mkdir(parents=True)
    service = TianyiService.__new__(TianyiService)
    service.store = TianyiStateStore(str(state_dir / "state.json"))
    service.catalog = type(
        "Catalog",
        (),
        {"csv_path": "", "json_path": "", "entries": [1, 2], "source": "csv", "load": lambda self: None, "get_by_game_id": lambda self, game_id: None},
    )()
    service._invalidate_panel_cache = lambda **kwargs: None
    return service, state_dir


def test_catalog_update_downloads_and_reloads(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path / "state"))
    service, state_dir = _service(tmp_path)

    async def _fetch(url, **kwargs):
        assert "freedeckcy_catalog.csv" in url
        return _valid_csv(), {"ETag": '"v1"', "Last-Modified": "Wed, 01 Jan 2026 00:00:00 GMT"}, 200

    monkeypatch.setattr(service, "_fetch_catalog_csv", _fetch)
    result = asyncio.run(service.update_catalog_csv())
    assert result["updated"] is True
    assert result["total"] == 2
    assert (state_dir / "catalog.csv").is_file()
    assert (state_dir / "catalog.csv.meta.json").is_file()
    assert service.catalog.csv_path == str(state_dir / "catalog.csv")


def test_invalid_catalog_csv_is_rejected(tmp_path, monkeypatch):
    service, _state_dir = _service(tmp_path)

    async def _fetch(url, **kwargs):
        return b"game_id,title\n1,broken\n", {}, 200

    monkeypatch.setattr(service, "_fetch_catalog_csv", _fetch)
    try:
        asyncio.run(service.update_catalog_csv())
    except ValueError as exc:
        assert "缺少字段" in str(exc)
    else:
        raise AssertionError("缺少字段的目录应被拒绝")


def test_local_downloaded_catalog_has_priority(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path / "state"))
    local = tmp_path / "state" / "tianyi" / "catalog.csv"
    local.parent.mkdir(parents=True)
    local.write_text("game_id,title\n", encoding="utf-8")
    monkeypatch.delenv("FREEDECKCY_GAME_CATALOG_CSV", raising=False)
    monkeypatch.delenv("FRIENDECK_GAME_CATALOG_CSV", raising=False)
    resolved = game_catalog.resolve_default_catalog_path()
    assert Path(resolved).resolve() == local.resolve()


def test_catalog_update_skips_when_not_modified(tmp_path, monkeypatch):
    service, state_dir = _service(tmp_path)
    calls = []

    async def _fetch(url, **kwargs):
        calls.append(dict(kwargs))
        return None, {"ETag": '"v1"'}, 304

    monkeypatch.setattr(service, "_fetch_catalog_csv", _fetch)
    (state_dir / "catalog.csv").write_text("x", encoding="utf-8")
    result = asyncio.run(service.update_catalog_csv())
    assert result["updated"] is False
    assert result["reason"] == "not_modified"


def test_catalog_update_skips_same_hash(tmp_path, monkeypatch):
    service, state_dir = _service(tmp_path)
    csv_data = _valid_csv()

    async def _fetch(url, **kwargs):
        return csv_data, {"ETag": '"v1"'}, 200

    monkeypatch.setattr(service, "_fetch_catalog_csv", _fetch)
    (state_dir / "catalog.csv").write_bytes(csv_data)
    result = asyncio.run(service.update_catalog_csv())
    assert result["updated"] is False
    assert result["reason"] == "already_latest"


def test_catalog_update_records_added_games(tmp_path, monkeypatch):
    service, state_dir = _service(tmp_path)
    initial = _valid_csv()
    updated = initial + "999,New Game,5,动作冒险,https://cloud.189.cn/t/newgame,,New Game/New Game.7z,100,100 B,pc,,,0\n".encode("utf-8")

    async def _fetch_initial(url, **kwargs):
        return initial, {"ETag": '"v1"'}, 200

    monkeypatch.setattr(service, "_fetch_catalog_csv", _fetch_initial)
    first = asyncio.run(service.update_catalog_csv())
    assert first["updated"] is True
    assert first["added_count"] == 0

    async def _fetch_updated(url, **kwargs):
        return updated, {"ETag": '"v2"'}, 200

    monkeypatch.setattr(service, "_fetch_catalog_csv", _fetch_updated)
    second = asyncio.run(service.update_catalog_csv())
    assert second["updated"] is True
    assert second["added_count"] == 1
    assert (state_dir / "catalog.csv.meta.json").is_file()
    update = service.get_catalog_update()
    assert update["added_count"] == 1
    assert update["added"][0]["title"] == "New Game"
    assert (state_dir / "catalog.csv.meta.json").is_file()
