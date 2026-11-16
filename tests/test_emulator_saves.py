"""模拟器存档发现：单游戏存档、共享存档、portable/Flatpak 路径。"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import config
import emulator_saves
from tianyi_service import TianyiService
from tianyi_store import TianyiSettings, TianyiStateStore


def _record(platform: str, rom_path: str = "", install_path: str = ""):
    return SimpleNamespace(
        game_id=f"{platform}-1",
        game_title=f"{platform} game",
        platform=platform,
        rom_path=rom_path,
        install_path=install_path,
        launcher_path="",
        updated_at=1,
    )


def test_gba_per_game_save(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    save = tmp_path / ".local" / "share" / "mgba" / "saves" / "game.sav"
    save.parent.mkdir(parents=True)
    save.write_bytes(b"save")
    result = emulator_saves.collect_emulator_save_paths(_record("gba", rom_path="/roms/game.gba"))
    assert result.per_game is True
    assert result.paths == [str(save)]


def test_gba_no_save_does_not_upload_shared_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    other = tmp_path / ".local" / "share" / "mgba" / "saves" / "other.sav"
    other.parent.mkdir(parents=True)
    other.write_bytes(b"other")
    result = emulator_saves.collect_emulator_save_paths(_record("gba", rom_path="/roms/game.gba"))
    assert result.paths == []
    assert result.reason == "game_save_not_found"


def test_psp_shared_save_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    savedata = tmp_path / ".local" / "share" / "ppsspp" / "PSP" / "SAVEDATA" / "ULUS12345"
    savedata.mkdir(parents=True)
    result = emulator_saves.collect_emulator_save_paths(_record("psp", rom_path="/roms/game.iso"))
    assert result.per_game is False
    assert str(savedata.parent) in result.paths


def test_3ds_flatpak_save_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    sdmc = tmp_path / ".var" / "app" / "org.azahar_emu.Azahar" / "data" / "azahar" / "sdmc" / "Nintendo 3DS"
    sdmc.mkdir(parents=True)
    result = emulator_saves.collect_emulator_save_paths(_record("3ds", rom_path="/roms/game.3ds"))
    assert str(sdmc.parent) in result.paths


def test_portable_save_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    install = tmp_path / "emulators" / "psp"
    savedata = install / "memstick" / "PSP" / "SAVEDATA" / "ULUS12345"
    savedata.mkdir(parents=True)
    result = emulator_saves.collect_emulator_save_paths(
        _record("psp", rom_path="/roms/game.iso", install_path=str(install))
    )
    assert str(savedata.parent) in result.paths


def test_cloud_candidates_include_emulator_saves(tmp_path, monkeypatch):
    service = TianyiService.__new__(TianyiService)
    service.store = TianyiStateStore(str(tmp_path / "state.json"))
    service.store.settings = TianyiSettings()
    service.plugin_dir = str(tmp_path / "plugin")
    service.store.installed_games = [
        SimpleNamespace(
            game_id="g1",
            game_title="GBA Game",
            platform="gba",
            install_path=str(tmp_path / "installed"),
            rom_path=str(tmp_path / "installed" / "game.gba"),
            launcher_path="",
            updated_at=1,
        )
    ]
    (tmp_path / "installed").mkdir()
    save = tmp_path / "save.sav"
    save.write_bytes(b"save")
    monkeypatch.setattr(
        service,
        "_snapshot_record_playtime",
        lambda record: {"seconds": 0, "sessions": 0, "last_played_at": 0},
    )
    monkeypatch.setattr(
        service,
        "_build_cloud_save_game_key",
        lambda game_id, title: "gba-g1",
    )
    monkeypatch.setattr(
        service,
        "_build_cloud_save_match_tokens",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        "tianyi_service.collect_emulator_save_paths",
        lambda record: emulator_saves.EmulatorSaveResult(
            [str(save)], "gba", "mGBA", True, [str(save)]
        ),
    )
    candidates, diagnostics = asyncio.run(service._collect_cloud_save_candidates())
    assert len(candidates) == 1
    assert candidates[0]["source_strategy"] == "emulator_saves"
    assert candidates[0]["source_paths"] == [str(save)]
    assert diagnostics["candidate_total"] == 1


def test_cloud_candidates_respect_emulator_toggle(tmp_path, monkeypatch):
    service = TianyiService.__new__(TianyiService)
    service.store = TianyiStateStore(str(tmp_path / "state.json"))
    service.store.settings = TianyiSettings(cloud_save_include_emulators=False)
    service.plugin_dir = str(tmp_path / "plugin")
    service.store.installed_games = [
        SimpleNamespace(
            game_id="g1",
            game_title="GBA Game",
            platform="gba",
            install_path=str(tmp_path / "installed"),
            rom_path=str(tmp_path / "installed" / "game.gba"),
            launcher_path="",
            updated_at=1,
        )
    ]
    (tmp_path / "installed").mkdir()
    candidates, diagnostics = asyncio.run(service._collect_cloud_save_candidates())
    assert candidates == []
    assert diagnostics["ignored"][0]["reason"] == "emulator_saves_disabled"
