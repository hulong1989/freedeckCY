"""GBA / mGBA 闭环测试。"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import config
import emulator_manager as emu
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


def test_emulator_status_prefers_bundled(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("FREEDECKCY_MGBA_BIN", raising=False)
    arch = emu.runtime_arch()
    appimage = tmp_path / "plugin" / "defaults" / "runtime" / "mgba" / arch / "mGBA.AppImage"
    appimage.parent.mkdir(parents=True)
    appimage.write_bytes(b"x" * 1024)

    status = emu.emulator_status("gba", str(tmp_path / "plugin"))
    assert status["available"] is True
    assert status["source"] == "bundled"


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
    service.catalog = _FakeCatalog(_entry(platform="switch", openpath="game.nsp"))

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
    assert emu.emulator_name_for_platform("switch") == ""
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
