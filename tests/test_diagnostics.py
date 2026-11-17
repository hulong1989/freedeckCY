"""诊断自检：不依赖网络也要能返回结构化检查。"""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from types import SimpleNamespace

from tianyi_service import TianyiService
from tianyi_store import TianyiInstalledGame, TianyiSettings, TianyiStateStore


def test_run_diagnostics_returns_checks_without_network(tmp_path, monkeypatch):
    service = TianyiService.__new__(TianyiService)
    service.store = TianyiStateStore(str(tmp_path / "state.json"))
    service.store.settings = TianyiSettings(
        download_dir=str(tmp_path / "downloads"),
        install_dir=str(tmp_path / "installed"),
    )
    service.plugin = SimpleNamespace(downloads_dir=str(tmp_path), server_running=False, server_port=0)
    service.catalog = SimpleNamespace(
        entries=[object()],
        platform_counts=lambda: [{"value": "pc", "label": "PC", "count": 1}],
        cover_index_total=0,
    )
    service._invalidate_panel_cache = lambda **kwargs: None
    monkeypatch.setattr("tianyi_service._find_steam_root", lambda: "")
    monkeypatch.setattr("tianyi_service._tail_text", lambda path, limit=200: "")
    result = asyncio.run(service.run_diagnostics(include_network=False))
    ids = {item["id"] for item in result["checks"]}
    assert {"plugin", "state_dir", "download_dir", "install_dir", "catalog", "steam", "baidu_qr", "tasks", "log"} <= ids
    assert result["summary"]["fail"] >= 0
    assert "sign" not in str(result).lower()


def test_library_time_stats_unmanaged_games_get_no_hltb(tmp_path, monkeypatch):
    service = TianyiService.__new__(TianyiService)
    service.store = TianyiStateStore(str(tmp_path / "state.json"))
    service.catalog = SimpleNamespace(get_by_game_id=lambda game_id: None)
    called = []

    async def _fake_hltb(**kwargs):
        called.append(kwargs)
        return {"main_story_hours": 10.0, "total_hours": 20.0}

    monkeypatch.setattr(service, "resolve_hltb_stats", _fake_hltb)
    result = asyncio.run(service.get_library_game_time_stats(app_id="0", title="Original Steam Game"))
    assert result["managed"] is False
    assert called == []
    assert result["main_story_hours"] == 0.0


def test_update_settings_forwards_cloud_and_proton_flags(tmp_path):
    service = TianyiService.__new__(TianyiService)
    service.store = TianyiStateStore(str(tmp_path / "state.json"))
    service._invalidate_panel_cache = lambda **kwargs: None

    class _Plugin:
        downloads_dir = str(tmp_path / "downloads")

        async def set_download_dir(self, path):
            self.downloads_dir = path

    service.plugin = _Plugin()
    asyncio.run(
        service.update_settings(
            download_dir=str(tmp_path / "downloads"),
            install_dir=str(tmp_path / "installed"),
            proton_tool="proton_experimental",
            cloud_save_auto_upload=False,
            cloud_save_include_emulators=False,
        )
    )
    assert service.store.settings.proton_tool == "proton_experimental"
    assert service.store.settings.cloud_save_auto_upload is False
    assert service.store.settings.cloud_save_include_emulators is False


def test_update_settings_rejects_empty_directory(tmp_path):
    service = TianyiService.__new__(TianyiService)
    service.store = TianyiStateStore(str(tmp_path / "state.json"))
    service._invalidate_panel_cache = lambda **kwargs: None

    class _Plugin:
        downloads_dir = ""

        async def set_download_dir(self, path):
            pass

    service.plugin = _Plugin()
    try:
        asyncio.run(service.update_settings(download_dir="   "))
    except ValueError as exc:
        assert "不能为空" in str(exc)
    else:
        raise AssertionError("empty download_dir must be rejected")


def test_installed_game_upsert_preserves_emulator_fields(tmp_path):
    store = TianyiStateStore(str(tmp_path / "state.json"))
    store.upsert_installed_game(
        TianyiInstalledGame(
            game_id="gba-1",
            game_title="Demo GBA",
            install_path=str(tmp_path / "Demo GBA"),
            source_path=str(tmp_path / "Demo GBA"),
            platform="gba",
            emulator="mgba",
            rom_path="/roms/demo.gba",
            launcher_path="/roms/launch.sh",
        )
    )
    record = store.installed_games[0]
    assert record.platform == "gba"
    assert record.emulator == "mgba"
    assert record.rom_path == "/roms/demo.gba"
    assert record.launcher_path == "/roms/launch.sh"


def test_installed_game_from_dict_roundtrip_keeps_emulator_fields():
    record = TianyiInstalledGame(
        game_id="3ds-1",
        game_title="Demo 3DS",
        install_path="/games/demo",
        source_path="/games/demo",
        platform="3ds",
        emulator="azahar",
        rom_path="/games/demo/rom.3ds",
        launcher_path="/games/demo/launch.sh",
    )
    restored = TianyiInstalledGame.from_dict(asdict(record))
    assert restored.platform == "3ds"
    assert restored.emulator == "azahar"
    assert restored.rom_path == "/games/demo/rom.3ds"
    assert restored.launcher_path == "/games/demo/launch.sh"


def test_describe_exception_keeps_empty_timeout_readable():
    from tianyi_service import _describe_exception

    assert _describe_exception(asyncio.TimeoutError()) == "TimeoutError"
    assert "boom" in _describe_exception(RuntimeError("boom"))
