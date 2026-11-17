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


def _sfo(title: str) -> bytes:
    import struct

    key = b"TITLE\x00"
    value = title.encode("utf-8") + b"\x00"
    key_start = 36
    data_start = key_start + len(key)
    header = b"\x00PSF" + struct.pack("<IIII", 0x101, key_start, data_start, 1)
    index = struct.pack("<HHIII", 0, 0x0204, len(value), len(value), 0)
    return header + index + key + value


def test_psp_save_split_by_param_sfo(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    savedata = tmp_path / ".local" / "share" / "ppsspp" / "PSP" / "SAVEDATA"
    target = savedata / "ULUS10001"
    other = savedata / "ULUS10002"
    target.mkdir(parents=True)
    other.mkdir(parents=True)
    (target / "PARAM.SFO").write_bytes(_sfo("Game One"))
    (other / "PARAM.SFO").write_bytes(_sfo("Other Game"))

    result = emulator_saves.collect_emulator_save_paths(
        SimpleNamespace(platform="psp", game_title="Game One", rom_path="/roms/game.iso", install_path="", launcher_path="")
    )
    assert result.per_game is True
    assert result.paths == [str(target)]


def test_ps3_save_split_by_param_sfo(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    savedata = tmp_path / ".config" / "rpcs3" / "dev_hdd0" / "home" / "00000001" / "savedata"
    target = savedata / "NPWR10001"
    other = savedata / "NPWR10002"
    target.mkdir(parents=True)
    other.mkdir(parents=True)
    (target / "PARAM.SFO").write_bytes(_sfo("Game One"))
    (other / "PARAM.SFO").write_bytes(_sfo("Other Game"))

    result = emulator_saves.collect_emulator_save_paths(
        SimpleNamespace(platform="ps3", game_title="Game One", rom_path="/roms/game.iso", install_path="", launcher_path="")
    )
    assert result.per_game is True
    assert result.paths == [str(target)]


def test_restore_targets_use_original_home_path(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    source = tmp_path / ".local" / "share" / "mgba" / "saves" / "game.sav"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"x")
    roots, targets = emulator_saves.build_restore_targets(
        SimpleNamespace(platform="gba", rom_path="/roms/game.gba", install_path="", launcher_path=""),
        [{"entry_id": "e1", "source_path": str(source), "archive_rel_path": "game.sav"}],
    )
    assert roots
    assert targets["e1"] == str(source.parent)


def test_plan_emulator_save_restore(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    home_save = tmp_path / ".local" / "share" / "mgba" / "saves"
    home_save.mkdir(parents=True)
    source = home_save / "game.sav"

    service = TianyiService.__new__(TianyiService)
    service.store = TianyiStateStore(str(tmp_path / "state.json"))
    service.store.installed_games = [
        SimpleNamespace(
            game_id="g1",
            game_title="GBA Game",
            platform="gba",
            rom_path=str(tmp_path / "game.gba"),
            install_path=str(tmp_path),
            launcher_path="",
        )
    ]
    service._cloud_save_restore_lock = asyncio.Lock()
    service._cloud_save_restore_plan = None
    service._cloud_save_restore_state = {}

    extract = tmp_path / "extract"
    extract.mkdir()
    (extract / "game.sav").write_bytes(b"save")
    bundle = {"temp_dir": str(tmp_path / "tmp"), "extract_dir": str(extract)}
    manifest = {"source_strategy": "emulator_saves"}
    entries = [
        {
            "entry_id": "e1",
            "entry_name": "game.sav",
            "source_path": str(source),
            "archive_rel_path": "game.sav",
            "file_count": 1,
        }
    ]
    result = asyncio.run(
        service._plan_emulator_save_restore(
            bundle=bundle,
            manifest=manifest,
            entries=entries,
            selected_ids=["e1"],
            game_id="g1",
            game_key="gba-g1",
            game_title="GBA Game",
            version_name="2026.7z",
            manifest_playtime={},
        )
    )
    assert result["accepted"] is True
    assert result["restorable_files"] == 1
    plan = service._cloud_save_restore_plan
    assert plan["copy_pairs"][0][1] == str(source)


def test_3ds_save_split_by_title_id(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    rom = tmp_path / "game.3ds"
    header = bytearray(0x120)
    header[0x100:0x104] = b"NCSD"
    header[0x108:0x110] = (0x0004000000033600).to_bytes(8, "little")
    rom.write_bytes(bytes(header))

    sdmc = tmp_path / ".local" / "share" / "azahar" / "sdmc"
    title = sdmc / "Nintendo 3DS" / "id0" / "id1" / "title" / "00040000" / "00033600"
    (title / "data").mkdir(parents=True)
    (title / "data" / "00000001.sav").write_bytes(b"save")

    result = emulator_saves.collect_emulator_save_paths(
        SimpleNamespace(platform="3ds", game_title="Game", rom_path=str(rom), install_path="", launcher_path="")
    )
    assert result.per_game is True
    assert result.paths == [str(title / "data")]


def test_restore_plan_rebuilds_per_game_directory_layer(tmp_path):
    from tianyi_service import TianyiService

    service = TianyiService.__new__(TianyiService)
    extract_root = tmp_path / "extract"
    entry_dir = extract_root / "TITLEID01"
    entry_dir.mkdir(parents=True)
    (entry_dir / "data.bin").write_bytes(b"save")
    target_root = tmp_path / "SAVEDATA"
    target_root.mkdir()
    plan = service._build_restore_copy_plan(
        extract_dir=str(extract_root),
        entries=[{"entry_id": "e1", "entry_name": "TITLEID01", "archive_rel_path": "TITLEID01"}],
        selected_entry_ids=["e1"],
        target_dir=str(target_root),
    )
    assert plan["copy_pairs"][0][1] == str(target_root / "TITLEID01" / "data.bin")


def test_restore_plan_shared_root_writes_contents_to_root(tmp_path):
    from tianyi_service import TianyiService

    service = TianyiService.__new__(TianyiService)
    extract_root = tmp_path / "extract"
    entry_dir = extract_root / "memcards"
    entry_dir.mkdir(parents=True)
    (entry_dir / "card1.mcr").write_bytes(b"save")
    target_root = tmp_path / "memcards"
    target_root.mkdir()
    plan = service._build_restore_copy_plan(
        extract_dir=str(extract_root),
        entries=[{"entry_id": "e1", "entry_name": "memcards", "archive_rel_path": "memcards"}],
        selected_entry_ids=["e1"],
        target_dir=str(target_root),
    )
    assert plan["copy_pairs"][0][1] == str(target_root / "card1.mcr")


def test_single_directory_working_dir_is_parent(tmp_path):
    from tianyi_service import TianyiService

    service = TianyiService.__new__(TianyiService)
    source = tmp_path / "SAVEDATA" / "TITLEID01"
    source.mkdir(parents=True)
    assert service._compute_common_working_dir([str(source)]) == str(source.parent)


def test_gba_save_next_to_rom(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    rom = tmp_path / "roms" / "game.gba"
    rom.parent.mkdir(parents=True)
    rom.write_bytes(b"rom")
    (rom.parent / "game.sav").write_bytes(b"save")
    result = emulator_saves.collect_emulator_save_paths(_record("gba", rom_path=str(rom)))
    assert result.per_game is True
    assert str(rom.parent / "game.sav") in result.paths


def test_legacy_manifest_uses_entry_name_when_rel_path_missing(tmp_path):
    from tianyi_service import TianyiService

    service = TianyiService.__new__(TianyiService)
    extract = tmp_path / "extract"
    (extract / "TITLEID01").mkdir(parents=True)
    (extract / "TITLEID01" / "data.bin").write_bytes(b"save")
    entries = service._normalize_cloud_restore_entries(
        manifest={"entries": [{"entry_id": "e1", "name": "TITLEID01", "archive_rel_path": ""}]},
        extract_dir=str(extract),
    )
    assert entries and entries[0]["archive_rel_path"] == "TITLEID01"


def test_legacy_backup_migration_moves_into_central_dir(tmp_path, monkeypatch):
    import config
    from tianyi_service import TianyiService

    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path / "freedeckcy"))
    save_root = tmp_path / "saves"
    save_root.mkdir()
    (save_root / "game.sav").write_bytes(b"current")
    (save_root / "game.sav.freedeckcy-bak-20260101_000000").write_bytes(b"old")
    (save_root / "old.freedeckcy-bak-dir").mkdir()
    service = TianyiService.__new__(TianyiService)
    moved = service._migrate_legacy_backup_roots([str(save_root)])
    assert moved == 2
    assert (save_root / "game.sav").exists()
    assert not (save_root / "game.sav.freedeckcy-bak-20260101_000000").exists()
    legacy = tmp_path / "freedeckcy" / "backups" / "legacy"
    assert len(list(legacy.iterdir())) == 2


def test_flat_legacy_manifest_restores_into_entry_directory(tmp_path):
    from tianyi_service import TianyiService

    service = TianyiService.__new__(TianyiService)
    extract = tmp_path / "extract"
    extract.mkdir()
    (extract / "data.bin").write_bytes(b"save")
    target = tmp_path / "SAVEDATA"
    target.mkdir()
    entries = service._normalize_cloud_restore_entries(
        manifest={"entries": [{"entry_id": "e1", "name": "TITLEID01", "archive_rel_path": "TITLEID01"}]},
        extract_dir=str(extract),
    )
    assert entries and entries[0]["archive_rel_path"] == ""
    plan = service._build_restore_copy_plan(
        extract_dir=str(extract),
        entries=entries,
        selected_entry_ids=["e1"],
        target_dir=str(target),
    )
    assert plan["copy_pairs"][0][1] == str(target / "TITLEID01" / "data.bin")


def test_prune_keeps_legacy_backup_dir(tmp_path, monkeypatch):
    import config
    from tianyi_service import TianyiService

    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path))
    backups = tmp_path / "backups"
    backups.mkdir()
    for index in range(5):
        folder = backups / f"cloud-save-{index:02d}"
        folder.mkdir()
        (folder / "f").write_bytes(b"x")
    (backups / "legacy").mkdir()
    TianyiService._prune_cloud_save_backups(keep=2)
    assert len(list(backups.glob("cloud-save-*"))) == 2
    assert (backups / "legacy").is_dir()
