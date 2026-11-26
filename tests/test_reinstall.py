"""已安装游戏重新下载安装测试。"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from tianyi_service import TianyiService
from tianyi_store import TianyiInstalledGame, TianyiSettings, TianyiStateStore


def _service(tmp_path, entries=None):
    service = TianyiService.__new__(TianyiService)
    service.store = TianyiStateStore(str(tmp_path / "state.json"))
    service.store.settings = TianyiSettings(download_dir=str(tmp_path / "dl"), install_dir=str(tmp_path / "games"))
    service.plugin = SimpleNamespace(downloads_dir=str(tmp_path), server_running=False, server_port=0)
    entries = list(entries or [])
    service.catalog = SimpleNamespace(get_by_game_id=lambda gid: next((e for e in entries if e.game_id == gid), None))
    service._invalidate_panel_cache = lambda **kwargs: None
    return service


def _entry(game_id="g1", title="Demo"):
    return SimpleNamespace(game_id=game_id, title=title, platform="pc")


def _record(tmp_path, game_id="g1", install_path=None):
    return TianyiInstalledGame(
        game_id=game_id,
        game_title="Demo",
        install_path=str(install_path or (tmp_path / "games" / "Demo")),
        source_path="",
    )


def test_reinstall_uses_existing_install_parent(tmp_path, monkeypatch):
    service = _service(tmp_path, [_entry()])
    service.store.installed_games = [_record(tmp_path)]
    captured = {}

    async def fake_start(**kwargs):
        captured.update(kwargs)
        return {"tasks": [{"task_id": "new"}], "reused": False}

    monkeypatch.setattr(service, "start_install", fake_start)
    result = asyncio.run(service.reinstall_installed_game("g1"))
    assert captured["game_id"] == "g1"
    assert captured["install_dir"] == str(tmp_path / "games")
    assert result["tasks"] == [{"task_id": "new"}]


def test_reinstall_missing_record_raises(tmp_path):
    service = _service(tmp_path)
    with pytest.raises(ValueError):
        asyncio.run(service.reinstall_installed_game("missing"))


def test_reinstall_missing_catalog_entry_raises(tmp_path):
    service = _service(tmp_path)
    service.store.installed_games = [_record(tmp_path)]
    with pytest.raises(ValueError):
        asyncio.run(service.reinstall_installed_game("g1"))


def test_reinstall_batch_continues_after_error(tmp_path, monkeypatch):
    service = _service(tmp_path, [_entry("g1"), _entry("g2")])
    service.store.installed_games = [_record(tmp_path, "g1"), _record(tmp_path, "g2")]

    async def fake_reinstall(game_id):
        if game_id == "g2":
            raise RuntimeError("目录损坏")
        return {"game_id": game_id, "tasks": [{"task_id": "t"}]}

    monkeypatch.setattr(service, "reinstall_installed_game", fake_reinstall)
    result = asyncio.run(service.reinstall_installed_games(["g1", "g2", "g1"]))
    assert result["attempted"] == 2
    assert result["started"] == 1
    assert result["failed"] == 1
    assert result["errors"][0]["game_id"] == "g2"
    assert "目录损坏" in result["errors"][0]["message"]
