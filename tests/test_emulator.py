"""GBA / mGBA 闭环测试。"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import config
import emulator_manager as emu
import emulator_setup as emu_setup
import tianyi_service as svc_module
from game_catalog import GameCatalogEntry
from tianyi_client import ResolvedFile, ResolvedShare
from tianyi_service import TianyiService
from tianyi_store import TianyiSettings, TianyiTaskRecord


def _entry(**overrides) -> GameCatalogEntry:
    values = dict(
        game_id="gba-1",
        title="Test GBA Game",
        category_parent="",
        categories="角色扮演",
        down_url="https://cloud.189.cn/web/share?code=abc&pwd=1234",
        pwd="1234",
        openpath="Test Game (JP).zip",
        size_bytes=1024,
        size_text="1 KB",
        platform="gba",
    )
    values.update(overrides)
    return GameCatalogEntry(**values)


class _FakeCatalog:
    def __init__(self, entry):
        self.entry = entry
        self.entries = [entry] if entry else []

    def get_by_game_id(self, game_id):
        if self.entry is not None and str(self.entry.game_id) == str(game_id):
            return self.entry
        return None


def _service(tmp_path: Path) -> TianyiService:
    service = TianyiService.__new__(TianyiService)
    service.plugin_dir = str(tmp_path)
    service.plugin = SimpleNamespace(downloads_dir=str(tmp_path / "Downloads"))
    (tmp_path / "Downloads").mkdir(parents=True, exist_ok=True)
    service.store = SimpleNamespace(
        settings=TianyiSettings(
            download_dir=str(tmp_path / "Downloads"),
            install_dir=str(tmp_path / "Games"),
        ),
        login=SimpleNamespace(cookie="UID=test"),
    )
    (tmp_path / "Games").mkdir(parents=True, exist_ok=True)

    async def _ok():
        return True, "tester", ""

    service.check_login_state = _ok  # type: ignore[assignment]
    return service


def test_find_rom_file_prefers_openpath(tmp_path):
    (tmp_path / "a.gba").write_bytes(b"a")
    (tmp_path / "Test Game (JP).GBA").write_bytes(b"b")
    assert emu.find_rom_file(str(tmp_path), "Test Game (JP).zip").endswith("Test Game (JP).GBA")
    assert emu.find_rom_file(str(tmp_path), "missing.zip").endswith("a.gba")
    assert emu.find_rom_file(str(tmp_path / "nope"), "") == ""


def test_create_launch_wrapper(tmp_path):
    wrapper = tmp_path / "launch.sh"
    emu.create_launch_wrapper(
        command=["/usr/bin/mgba"],
        rom_path="/roms/a b.gba",
        wrapper_path=str(wrapper),
    )
    text = wrapper.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash")
    assert "/usr/bin/mgba" in text
    assert "a b.gba" in text
    assert os.access(wrapper, os.X_OK)


def test_ensure_mgba_env_override(tmp_path, monkeypatch):
    binary = tmp_path / "mgba"
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setenv("FREEDECKCY_MGBA_BIN", str(binary))
    assert asyncio.run(emu.ensure_mgba(str(tmp_path), allow_download=False)) == [str(binary)]


def test_emulator_status_offers_download_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("FREEDECKCY_MGBA_BIN", raising=False)
    status = emu.emulator_status("gba", str(tmp_path / "plugin"))
    assert status["available"] is True
    assert status["source"] == "download"
    assert "mGBA" in status["url"]


def test_gba_plan_selects_target_rom(monkeypatch, tmp_path):
    service = _service(tmp_path)
    service.catalog = _FakeCatalog(_entry())

    async def _resolve(share_url, cookie, *, target_name="", max_pages=40):
        assert target_name == "Test Game (JP).zip"
        return ResolvedShare(
            share_code="abc",
            share_id="share-1",
            pwd="1234",
            files=[
                ResolvedFile(file_id="1", name="Other Game.zip", size=10, is_folder=False),
                ResolvedFile(file_id="2", name="Test Game (JP).zip", size=2048, is_folder=False),
            ],
        )

    monkeypatch.setattr(svc_module, "resolve_share", _resolve)
    monkeypatch.setattr(
        svc_module,
        "emulator_status",
        lambda platform, plugin_dir: {"available": True, "source": "local", "command": "mGBA.AppImage"},
    )

    plan = asyncio.run(service._build_install_plan(game_id="gba-1"))
    assert plan["platform"] == "gba"
    assert plan["emulator"] == "mgba"
    assert plan["rom_target"] == "Test Game (JP).zip"
    assert [item["name"] for item in plan["files"]] == ["Test Game (JP).zip"]
    assert plan["required_download_bytes"] == 2048


def test_gba_plan_reports_missing_rom(monkeypatch, tmp_path):
    service = _service(tmp_path)
    service.catalog = _FakeCatalog(_entry())

    async def _resolve(share_url, cookie, *, target_name="", max_pages=40):
        return ResolvedShare(
            share_code="abc",
            share_id="share-1",
            pwd="1234",
            files=[ResolvedFile(file_id="1", name="Other.zip", size=10, is_folder=False)],
        )

    monkeypatch.setattr(svc_module, "resolve_share", _resolve)
    monkeypatch.setattr(
        svc_module,
        "emulator_status",
        lambda platform, plugin_dir: {"available": True, "source": "local", "command": "mGBA.AppImage"},
    )

    with pytest.raises(svc_module.TianyiApiError) as exc:
        asyncio.run(service._build_install_plan(game_id="gba-1"))
    assert "没有找到 ROM" in str(exc.value)


def test_unsupported_platform_still_rejected(monkeypatch, tmp_path):
    service = _service(tmp_path)
    service.catalog = _FakeCatalog(_entry(platform="wiiu", openpath="game.wud"))

    with pytest.raises(ValueError) as exc:
        asyncio.run(service._build_install_plan(game_id="gba-1"))
    assert "暂未接入模拟器" in str(exc.value)


def test_register_gba_creates_wrapper_and_none_proton(monkeypatch, tmp_path):
    service = _service(tmp_path)
    service.catalog = _FakeCatalog(None)

    async def _cover(**kwargs):
        return {}

    service.resolve_catalog_cover = _cover  # type: ignore[assignment]

    install_dir = tmp_path / "Games" / "Test Game"
    install_dir.mkdir(parents=True)
    (install_dir / "Test Game (JP).gba").write_bytes(b"rom")

    task = TianyiTaskRecord(
        task_id="t-1",
        gid="g-1",
        game_id="gba-1",
        game_title="Test Game",
        share_code="abc",
        share_id="share-1",
        file_id="2",
        file_name="Test Game (JP).zip",
        download_dir=str(tmp_path / "Downloads"),
        local_path=str(tmp_path / "Downloads" / "Test Game (JP).zip"),
        status="complete",
        progress=100.0,
        speed=0,
        openpath="Test Game (JP).zip",
        platform="gba",
    )

    async def _ensure(platform_name, plugin_dir="", **kwargs):
        assert platform_name == "gba"
        return ["/usr/bin/mgba"]

    captured = {}

    async def _shortcut(**kwargs):
        captured.update(kwargs)
        return {"ok": True, "appid_unsigned": 123, "steam_root": "/tmp/Steam"}

    monkeypatch.setattr(svc_module, "ensure_emulator", _ensure)
    monkeypatch.setattr(svc_module, "add_or_update_tianyi_shortcut", _shortcut)

    result = asyncio.run(service._auto_register_task_to_steam(task=task, target_dir=str(install_dir)))
    assert result["ok"] is True
    assert result["rom_path"].endswith("Test Game (JP).gba")
    assert captured["proton_tool"] == "none"
    assert captured["exe_path"].endswith("launch-freedeckcy.sh")
    assert "freedeckcy:tianyi:" in captured["launch_options"]
    wrapper = Path(captured["exe_path"])
    assert wrapper.is_file()
    assert "Test Game (JP).gba" in wrapper.read_text(encoding="utf-8")


def test_installed_view_exposes_emulator_fields():
    service = TianyiService.__new__(TianyiService)
    record = svc_module.TianyiInstalledGame(
        game_id="gba-1",
        game_title="Test",
        install_path="/tmp/test",
        source_path="",
        platform="gba",
        emulator="mgba",
        rom_path="/tmp/test/game.gba",
        launcher_path="/tmp/test/launch-freedeckcy.sh",
    )
    view = service._installed_record_to_view(record)
    assert view["platform"] == "gba"
    assert view["emulator"] == "mgba"
    assert view["rom_path"].endswith("game.gba")
    assert view["launcher_path"].endswith("launch-freedeckcy.sh")


def test_registry_has_psp_and_nds_assets():
    assert emu.emulator_name_for_platform("psp") == "ppsspp"
    assert emu.emulator_name_for_platform("nds") == "melonds"
    assert emu.emulator_name_for_platform("switch") == "eden"
    psp = emu.get_spec("psp")
    assert psp is not None
    assert psp.assets["x86_64"].endswith("x86_64.AppImage")
    assert psp.assets["aarch64"].endswith("aarch64.AppImage")
    nds = emu.get_spec("nds")
    assert nds is not None
    assert nds.archive == "zip"
    assert nds.assets["aarch64"].endswith(".zip")


def test_find_rom_file_platform_extensions(tmp_path):
    (tmp_path / "game.bin").write_bytes(b"x")
    (tmp_path / "game.cue").write_bytes(b"x")
    (tmp_path / "game.iso").write_bytes(b"x")
    (tmp_path / "game.nds").write_bytes(b"x")

    assert emu.find_rom_file(str(tmp_path), "game.zip", "psp").endswith("game.iso")
    assert emu.find_rom_file(str(tmp_path), "game.zip", "nds").endswith("game.nds")
    assert emu.find_rom_file(str(tmp_path), "game.zip", "gba") == ""


def test_launch_args_per_platform(tmp_path):
    psp_wrapper = tmp_path / "psp.sh"
    emu.create_launch_wrapper(
        command=["/usr/bin/ppsspp"],
        rom_path="/roms/game.iso",
        wrapper_path=str(psp_wrapper),
        platform_name="psp",
    )
    text = psp_wrapper.read_text(encoding="utf-8")
    assert "--fullscreen" in text
    assert "game.iso" in text

    nds_wrapper = tmp_path / "nds.sh"
    emu.create_launch_wrapper(
        command=["/usr/bin/melonds"],
        rom_path="/roms/game.nds",
        wrapper_path=str(nds_wrapper),
        platform_name="nds",
    )
    assert "game.nds" in nds_wrapper.read_text(encoding="utf-8")


def test_psp_status_offers_official_download(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("FREEDECKCY_PPSSPP_BIN", raising=False)
    status = emu.emulator_status("psp", str(tmp_path / "plugin"))
    assert status["available"] is True
    assert status["source"] == "download"
    assert "PPSSPP" in status["url"]


def test_psp_plan_allowed(monkeypatch, tmp_path):
    service = _service(tmp_path)
    service.catalog = _FakeCatalog(
        _entry(platform="psp", openpath="PSPCH001.7z", title="PSP Game")
    )

    async def _resolve(share_url, cookie, *, target_name="", max_pages=40):
        assert target_name == "PSPCH001.7z"
        return ResolvedShare(
            share_code="abc",
            share_id="share-1",
            pwd="1234",
            files=[
                ResolvedFile(file_id="1", name="Other.7z", size=10, is_folder=False),
                ResolvedFile(file_id="2", name="PSPCH001.7z", size=4096, is_folder=False),
            ],
        )

    monkeypatch.setattr(svc_module, "resolve_share", _resolve)
    monkeypatch.setattr(
        svc_module,
        "emulator_status",
        lambda platform, plugin_dir: {
            "available": True,
            "source": "download",
            "name": "PPSSPP",
        },
    )

    plan = asyncio.run(service._build_install_plan(game_id="gba-1"))
    assert plan["platform"] == "psp"
    assert plan["emulator"] == "ppsspp"
    assert [item["name"] for item in plan["files"]] == ["PSPCH001.7z"]


def test_registry_ps1_fc_md():
    assert emu.emulator_name_for_platform("ps1") == "duckstation"
    assert emu.emulator_name_for_platform("fc") == "mesen"
    assert emu.emulator_name_for_platform("md") == "mesen"

    ps1 = emu.get_spec("ps1")
    assert ps1 is not None and ps1.bios_required
    assert ps1.assets["aarch64"] == "DuckStation-arm64.AppImage"

    fc = emu.get_spec("fc")
    md = emu.get_spec("md")
    assert fc is not None and md is not None
    assert fc.state_key == md.state_key == "mesen"
    assert fc.assets["x86_64"].endswith(".zip")


def test_ps1_rom_prefers_cue(tmp_path):
    for name in ("game.bin", "game.cue", "game.iso"):
        (tmp_path / name).write_bytes(b"x")
    assert emu.find_rom_file(str(tmp_path), "game.zip", "ps1").endswith("game.cue")


def test_fc_md_rom_extensions(tmp_path):
    (tmp_path / "game.nes").write_bytes(b"x")
    (tmp_path / "game.md").write_bytes(b"x")
    assert emu.find_rom_file(str(tmp_path), "rom.zip", "fc").endswith("game.nes")
    assert emu.find_rom_file(str(tmp_path), "rom.zip", "md").endswith("game.md")


def test_zip_emulator_extraction(tmp_path):
    import zipfile

    spec = emu.get_spec("md")
    archive = tmp_path / "mesen.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("Mesen", b"#!/bin/sh\n")
    root = tmp_path / "mesen-root"
    found = emu._extract_zip_emulator(spec, str(archive), root)
    assert found.endswith("/Mesen")
    assert os.access(found, os.X_OK)


def test_ps1_bios_prepare_and_status(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    source = tmp_path / "state" / "bios" / "ps1"
    source.mkdir(parents=True)
    (source / "scph5501.bin").write_bytes(b"bios")

    assert emu.bios_present("ps1") is True
    spec = emu.get_spec("ps1")
    messages = emu.prepare_bios(spec)
    assert any("BIOS" in message for message in messages)

    target = tmp_path / "home" / ".local" / "share" / "duckstation" / "bios" / "scph5501.bin"
    assert target.is_file()

    status = emu.emulator_status("ps1", str(tmp_path / "plugin"))
    assert status["bios_required"] is True
    assert status["bios_present"] is True
    assert status["bios_dir"].endswith("/bios/ps1")


def test_ps1_launch_args(tmp_path):
    wrapper = tmp_path / "ps1.sh"
    emu.create_launch_wrapper(
        command=["/usr/bin/duckstation"],
        rom_path="/roms/game.cue",
        wrapper_path=str(wrapper),
        platform_name="ps1",
    )
    text = wrapper.read_text(encoding="utf-8")
    assert "-batch" in text
    assert "-fullscreen" in text
    assert "game.cue" in text


def test_registry_ps2_ps3_3ds_switch_assets():
    assert emu.emulator_name_for_platform("ps2") == "pcsx2"
    assert emu.emulator_name_for_platform("ps3") == "rpcs3"
    assert emu.emulator_name_for_platform("3ds") == "azahar"
    assert emu.emulator_name_for_platform("switch") == "eden"

    for platform, adapter in (("ps2", "pcsx2"), ("ps3", "rpcs3"), ("3ds", "azahar")):
        spec = emu.get_spec(platform)
        assert spec is not None
        assert "x86_64" in spec.assets
        assert "aarch64" not in spec.assets

    switch = emu.get_spec("switch")
    assert switch is not None
    assert switch.assets["aarch64"].startswith("Eden-Linux")
    assert switch.setup_required is True


def test_available_platforms_by_arch():
    x86 = set(emu.available_platforms("x86_64"))
    arm = set(emu.available_platforms("aarch64"))
    assert {"gba", "psp", "nds", "ps1", "fc", "md", "3ds", "ps2", "ps3", "switch"} <= x86
    assert arm == {"gba", "psp", "nds", "ps1", "fc", "md", "switch"}
    assert "3ds" not in arm and "ps2" not in arm and "ps3" not in arm


def test_ps2_hidden_on_arm(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(emu, "runtime_arch", lambda: "aarch64")
    status = emu.emulator_status("ps2", str(tmp_path / "plugin"))
    assert status["available"] is False
    assert "没有 PCSX2 官方包" in status["message"]


def test_ps2_bios_prepare(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    source = tmp_path / "state" / "bios" / "ps2"
    source.mkdir(parents=True)
    (source / "scph70012.bin").write_bytes(b"bios")

    spec = emu.get_spec("ps2")
    messages = emu.prepare_bios(spec)
    assert messages
    target = tmp_path / "home" / ".local" / "share" / "PCSX2" / "bios" / "scph70012.bin"
    assert target.is_file()


def test_ps2_launch_args(tmp_path):
    wrapper = tmp_path / "ps2.sh"
    emu.create_launch_wrapper(
        command=["/usr/bin/pcsx2"],
        rom_path="/roms/game.iso",
        wrapper_path=str(wrapper),
        platform_name="ps2",
    )
    text = wrapper.read_text(encoding="utf-8")
    assert "-batch" in text and "-fullscreen" in text and "game.iso" in text


def test_ps2_rom_prefers_iso(tmp_path):
    (tmp_path / "game.bin").write_bytes(b"x")
    (tmp_path / "game.iso").write_bytes(b"x")
    assert emu.find_rom_file(str(tmp_path), "game.zip", "ps2").endswith("game.iso")


def test_setup_ps1_deploys_bios_and_portable_config(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    root = tmp_path / "emu" / "duckstation"
    root.mkdir(parents=True)
    (root / "AppRun").write_text("#!/bin/sh\n", encoding="utf-8")
    source = tmp_path / "state" / "bios" / "ps1"
    source.mkdir(parents=True)
    (source / "scph5501.bin").write_bytes(b"bios")

    messages = emu_setup.setup_emulator("ps1", [str(root / "AppRun")])
    assert "BIOS" in " ".join(messages)
    assert (root / "portable.txt").is_file()
    assert (root / "bios" / "scph5501.bin").is_file()
    settings = (root / "portable_data" / "settings" / "settings.ini").read_text(encoding="utf-8")
    assert "SearchDirectory = ./bios" in settings


def test_setup_ps2_deploys_bios_and_ini(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    root = tmp_path / "emu" / "pcsx2"
    root.mkdir(parents=True)
    (root / "AppRun").write_text("#!/bin/sh\n", encoding="utf-8")
    source = tmp_path / "state" / "bios" / "ps2"
    source.mkdir(parents=True)
    (source / "scph70012.bin").write_bytes(b"bios")

    emu_setup.setup_emulator("ps2", [str(root / "AppRun")])
    assert (root / "bios" / "scph70012.bin").is_file()
    ini = (root / "inis" / "PCSX2.ini").read_text(encoding="utf-8")
    assert "Bios = " in ini and "Fullscreen = true" in ini


def test_setup_ps1_extracts_bios_archive(tmp_path, monkeypatch):
    import zipfile

    class FakeSevenZip:
        def extract_archive(self, archive_path, output_dir):
            with zipfile.ZipFile(archive_path) as zf:
                zf.extractall(output_dir)

    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    root = tmp_path / "emu" / "duckstation"
    root.mkdir(parents=True)
    (root / "AppRun").write_text("#!/bin/sh\n", encoding="utf-8")
    source = tmp_path / "state" / "bios" / "ps1"
    source.mkdir(parents=True)
    with zipfile.ZipFile(source / "bios.zip", "w") as zf:
        zf.writestr("scph5501.bin", b"bios")

    emu_setup.setup_emulator("ps1", [str(root / "AppRun")], seven_zip=FakeSevenZip())
    assert (root / "bios" / "scph5501.bin").is_file()


def test_setup_switch_deploys_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(emu_setup, "_EDEN_KEYS", tmp_path / "eden" / "keys")
    monkeypatch.setattr(emu_setup, "_EDEN_REGISTERED", tmp_path / "eden" / "registered")
    source = tmp_path / "state" / "bios" / "switch"
    source.mkdir(parents=True)
    (source / "prod.keys").write_text("key", encoding="utf-8")

    messages = emu_setup.setup_emulator("switch", [])
    assert (tmp_path / "eden" / "keys" / "prod.keys").is_file()
    assert "keys" in " ".join(messages)


def test_setup_missing_bios_message(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    root = tmp_path / "emu" / "duckstation"
    root.mkdir(parents=True)
    messages = emu_setup.setup_emulator("ps1", [str(root / "AppRun")])
    assert any("未检测到" in message for message in messages)


def test_setup_ps3_installs_firmware(tmp_path, monkeypatch):
    import subprocess as subprocess_module

    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(emu_setup, "_RPCS3_CONFIG", tmp_path / "rpcs3")
    root = tmp_path / "emu" / "rpcs3"
    root.mkdir(parents=True)
    (root / "AppRun").write_text("#!/bin/sh\n", encoding="utf-8")
    source = tmp_path / "state" / "bios" / "ps3"
    source.mkdir(parents=True)
    (source / "PS3UPDAT.PUP").write_bytes(b"pup")

    calls = []

    class Result:
        returncode = 0
        stderr = b""

    def fake_run(args, **kwargs):
        calls.append(args)
        return Result()

    monkeypatch.setattr(subprocess_module, "run", fake_run)
    messages = emu_setup.setup_emulator("ps3", [str(root / "AppRun")])
    assert calls and "--installfw" in calls[0]
    assert any("固件" in message for message in messages)


def test_azahar_uses_flatpak_spec():
    spec = emu.get_spec("3ds")
    assert spec is not None
    assert spec.flatpak_id == "org.azahar_emu.Azahar"


def test_flatpak_installed_and_resolve(monkeypatch):
    monkeypatch.setattr(emu.shutil, "which", lambda name: "/usr/bin/flatpak" if name == "flatpak" else None)
    monkeypatch.setattr(
        emu.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0),
    )
    emu._FLATPAK_CACHE.clear()
    spec = emu.get_spec("3ds")
    assert emu.flatpak_installed(spec.flatpak_id) is True
    command = emu.resolve_command(spec)
    assert command == ["/usr/bin/flatpak", "run", "org.azahar_emu.Azahar"]


def test_steamos_prefers_flatpak_on_install(tmp_path, monkeypatch):
    monkeypatch.setattr(emu, "get_spec", lambda platform: emu.EMULATORS["3ds"])
    monkeypatch.setattr(emu, "flatpak_installed", lambda app_id, **kwargs: False)
    monkeypatch.setattr(emu, "_is_steamos", lambda: True)
    monkeypatch.setattr(emu, "resolve_command", lambda spec, plugin_dir="": None)

    async def _fake_flatpak(spec, *, allow_download):
        return ["/usr/bin/flatpak", "run", "org.azahar_emu.Azahar"]

    monkeypatch.setattr(emu, "_ensure_flatpak", _fake_flatpak)
    command = asyncio.run(emu.ensure_emulator("3ds", str(tmp_path)))
    assert command == ["/usr/bin/flatpak", "run", "org.azahar_emu.Azahar"]


def test_3ds_wrapper_sets_xwayland_env(tmp_path):
    wrapper = tmp_path / "3ds.sh"
    emu.create_launch_wrapper(
        command=["/usr/bin/flatpak", "run", "org.azahar_emu.Azahar"],
        rom_path="/roms/game.3ds",
        wrapper_path=str(wrapper),
        platform_name="3ds",
    )
    text = wrapper.read_text(encoding="utf-8")
    assert "QT_QPA_PLATFORM=xcb" in text
    assert "game.3ds" in text


def test_ps1_multidisc_generates_m3u(tmp_path):
    (tmp_path / "Disc 1.cue").write_text('FILE "Disc 1.bin" BINARY\n', encoding="utf-8")
    (tmp_path / "Disc 2.cue").write_text('FILE "Disc 2.bin" BINARY\n', encoding="utf-8")
    found = emu.find_rom_file(str(tmp_path), "Disc 1.cue", "ps1")
    assert found.endswith("freedeckcy-multidisc.m3u")
    content = Path(found).read_text(encoding="utf-8")
    assert "Disc 1.cue" in content and "Disc 2.cue" in content
    assert content.index("Disc 1.cue") < content.index("Disc 2.cue")


def test_ps1_prefers_existing_m3u(tmp_path):
    (tmp_path / "game.cue").write_text("x", encoding="utf-8")
    (tmp_path / "custom.m3u").write_text("game.cue\n", encoding="utf-8")
    assert emu.find_rom_file(str(tmp_path), "game.cue", "ps1").endswith("custom.m3u")


def test_ps1_single_cue_returns_cue(tmp_path):
    (tmp_path / "game.cue").write_text("x", encoding="utf-8")
    assert emu.find_rom_file(str(tmp_path), "game.cue", "ps1").endswith("game.cue")


def test_ps1_nested_disc_directories_sort_naturally(tmp_path):
    for label in ("Disc 1", "Disc 2", "Disc 10"):
        disc_dir = tmp_path / label
        disc_dir.mkdir()
        (disc_dir / "game.cue").write_text('FILE "game.bin" BINARY\n', encoding="utf-8")
    found = emu.find_rom_file(str(tmp_path), "Disc 1/game.cue", "ps1")
    content = Path(found).read_text(encoding="utf-8")
    assert content.index("Disc 1/game.cue") < content.index("Disc 2/game.cue") < content.index("Disc 10/game.cue")


def test_ps1_same_disc_cue_and_chd_not_duplicated(tmp_path):
    (tmp_path / "Disc 1.cue").write_text('FILE "Disc 1.bin" BINARY\n', encoding="utf-8")
    (tmp_path / "Disc 1.chd").write_bytes(b"chd")
    (tmp_path / "Disc 2.cue").write_text('FILE "Disc 2.bin" BINARY\n', encoding="utf-8")
    found = emu.find_rom_file(str(tmp_path), "Disc 1.cue", "ps1")
    content = Path(found).read_text(encoding="utf-8")
    assert "Disc 1.cue" in content
    assert "Disc 1.chd" not in content


def test_copy_tree_missing_preserves_directories_and_skips_existing(tmp_path):
    from emulator_setup import _copy_tree_missing

    source = tmp_path / "sysdata"
    (source / "nand" / "data").mkdir(parents=True)
    (source / "nand" / "data" / "file.bin").write_bytes(b"new")
    (source / "root.bin").write_bytes(b"new-root")
    target = tmp_path / "target"
    (target / "nand" / "data").mkdir(parents=True)
    (target / "nand" / "data" / "file.bin").write_bytes(b"old")
    copied = _copy_tree_missing(source, target)
    assert copied == 1
    assert (target / "nand" / "data" / "file.bin").read_bytes() == b"old"
    assert (target / "root.bin").read_bytes() == b"new-root"


def test_ps1_flat_directory_groups_games_by_disc_prefix(tmp_path):
    for name in ("GameA Disc 1.cue", "GameA Disc 2.cue", "GameB Disc 1.cue", "GameB Disc 2.cue"):
        (tmp_path / name).write_text('FILE "x.bin" BINARY\n', encoding="utf-8")
    found_a = emu.find_rom_file(str(tmp_path), "GameA Disc 1.cue", "ps1")
    found_b = emu.find_rom_file(str(tmp_path), "GameB Disc 1.cue", "ps1")
    assert found_a != found_b
    content_a = Path(found_a).read_text(encoding="utf-8")
    content_b = Path(found_b).read_text(encoding="utf-8")
    assert "GameA Disc 1.cue" in content_a and "GameA Disc 2.cue" in content_a
    assert "GameB" not in content_a
    assert "GameB Disc 1.cue" in content_b and "GameB Disc 2.cue" in content_b
    assert "GameA" not in content_b


def test_find_rom_file_strict_rejects_ambiguous_candidates(tmp_path):
    (tmp_path / "alpha.gba").write_bytes(b"a")
    (tmp_path / "beta.gba").write_bytes(b"b")
    assert emu.find_rom_file(str(tmp_path), "missing.zip", "gba", strict=True) == ""
    assert emu.find_rom_file(str(tmp_path), "missing.zip", "gba", strict=False)


def _make_ps1_same_name_dirs(tmp_path):
    for game in ("GameA", "GameB"):
        for disc in ("Disc 1", "Disc 2"):
            folder = tmp_path / game
            folder.mkdir(exist_ok=True)
            (folder / f"{disc}.cue").write_text('FILE "x.bin" BINARY\n', encoding="utf-8")


def test_ps1_same_disc_names_use_title_to_disambiguate(tmp_path):
    _make_ps1_same_name_dirs(tmp_path)
    found = emu.find_rom_file(str(tmp_path), "Disc 1.cue", "ps1", title="中文/GameB")
    assert "GameB" in found
    content = Path(found).read_text(encoding="utf-8")
    assert "GameB/Disc 1.cue" in content or "Disc 1.cue" in content
    assert "GameA" not in content


def test_ps1_same_disc_names_without_title_are_ambiguous(tmp_path):
    _make_ps1_same_name_dirs(tmp_path)
    assert emu.find_rom_file(str(tmp_path), "Disc 1.cue", "ps1") == ""


def test_ps1_full_openpath_wins_over_same_names(tmp_path):
    _make_ps1_same_name_dirs(tmp_path)
    found = emu.find_rom_file(str(tmp_path), "GameA/Disc 1.cue", "ps1")
    content = Path(found).read_text(encoding="utf-8")
    assert "GameA" in found
    assert "GameB" not in content


def test_3ds_cia_auto_install(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from tianyi_service import TianyiService

    cia = tmp_path / "game.cia"
    cia.write_bytes(b"CIA")
    service = TianyiService.__new__(TianyiService)
    service.plugin_dir = str(tmp_path)

    async def _ensure(platform, plugin_dir=None, **kwargs):
        assert platform == "3ds"
        return ["/usr/bin/azahar"]

    calls = []

    def _run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout=b"installed")

    monkeypatch.setattr("tianyi_service.ensure_emulator", _ensure)
    monkeypatch.setattr("tianyi_service.subprocess.run", _run)
    task = SimpleNamespace(platform="3ds", openpath="", game_title="Game")
    result = asyncio.run(service._auto_register_emulator_to_steam(task=task, target_dir=str(tmp_path), platform="3ds"))
    assert result["ok"] is True
    assert "CIA 已自动安装" in result["message"]
    assert calls and calls[0][-1] == str(cia)
