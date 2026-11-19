"""安装前自检、已安装校验/修复、失败任务诊断与换源的回归测试。"""

from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace

import pytest

import tianyi_service as svc_module
from game_catalog import GameCatalogEntry
from tianyi_service import PREFLIGHT_MIN_FREE_BYTES, TianyiService
from tianyi_store import (
    TianyiInstalledGame,
    TianyiSettings,
    TianyiStateStore,
    TianyiTaskRecord,
)


def _entry(
    game_id: str,
    *,
    title: str = "Demo Game",
    server: str = "t",
    down_url: str = "https://cloud.189.cn/t/abc",
    platform: str = "pc",
    executable_name: str = "",
) -> GameCatalogEntry:
    return GameCatalogEntry(
        game_id=game_id,
        title=title,
        category_parent="",
        categories="",
        down_url=down_url,
        pwd="",
        openpath="",
        size_bytes=0,
        size_text="",
        executable_name=executable_name,
        platform=platform,
        server=server,
    )


def _service(tmp_path, entries=None, *, download_dir=None, install_dir=None) -> TianyiService:
    service = TianyiService.__new__(TianyiService)
    service.store = TianyiStateStore(str(tmp_path / "state.json"))
    service.store.settings = TianyiSettings(
        download_dir=str(download_dir or (tmp_path / "downloads")),
        install_dir=str(install_dir or (tmp_path / "installed")),
    )
    service.plugin = SimpleNamespace(downloads_dir=str(tmp_path), server_running=False, server_port=0)
    entries = list(entries or [])
    service.catalog = SimpleNamespace(
        entries=entries,
        get_by_game_id=lambda game_id: next((item for item in entries if item.game_id == game_id), None),
    )
    service._post_process_failures = {}
    service._readd_attempts = {}
    service._task_sync_misses = {}
    service._invalidate_panel_cache = lambda **kwargs: None
    return service


def _record(tmp_path, game_id="g1", *, platform="pc", install_path=None) -> TianyiInstalledGame:
    record = TianyiInstalledGame(
        game_id=game_id,
        game_title="Demo Game",
        install_path=str(install_path or (tmp_path / "installed" / "Demo")),
        source_path="",
        platform=platform,
    )
    return record


def _task(game_id="g1", *, task_id="t1", status="error", install_status="failed", error_reason="") -> TianyiTaskRecord:
    return TianyiTaskRecord(
        task_id=task_id,
        gid="gid1",
        game_id=game_id,
        game_title="Demo Game",
        share_code="code",
        share_id="share",
        file_id="file",
        file_name="demo.zip",
        download_dir="/tmp",
        local_path="/tmp/demo.zip",
        status=status,
        progress=0.0,
        speed=0,
        install_status=install_status,
        error_reason=error_reason,
    )


# ---------------------------------------------------------------- preflight


def test_preflight_ok_with_writable_dirs(tmp_path):
    (tmp_path / "downloads").mkdir()
    (tmp_path / "installed").mkdir()
    service = _service(tmp_path)
    report = asyncio.run(service.preflight_install())
    checks = {item["id"]: item for item in report["checks"]}
    assert report["ok"] is True
    assert checks["download_dir"]["ok"] is True
    assert checks["install_dir"]["ok"] is True
    assert checks["disk_free"]["free_bytes"] > 0
    assert checks["disk_free_install"]["free_bytes"] > 0
    assert report["min_free_bytes"] == PREFLIGHT_MIN_FREE_BYTES


def test_preflight_missing_dirs_are_creatable(tmp_path):
    service = _service(tmp_path, download_dir=tmp_path / "new" / "downloads", install_dir=tmp_path / "new" / "installed")
    report = asyncio.run(service.preflight_install())
    checks = {item["id"]: item for item in report["checks"]}
    assert report["ok"] is True
    assert checks["download_dir"]["exists"] is False
    assert "自动创建" in checks["download_dir"]["message"]
    assert checks["install_dir"]["exists"] is False


def test_preflight_path_is_file_fails(tmp_path):
    (tmp_path / "downloads").mkdir()
    not_a_dir = tmp_path / "installed"
    not_a_dir.write_text("not a directory", encoding="utf-8")
    service = _service(tmp_path, install_dir=not_a_dir)
    report = asyncio.run(service.preflight_install())
    checks = {item["id"]: item for item in report["checks"]}
    assert report["ok"] is False
    assert checks["install_dir"]["ok"] is False
    assert checks["install_dir"]["message"] == "路径不是目录"


def test_preflight_unwritable_dir_fails(tmp_path, monkeypatch):
    (tmp_path / "downloads").mkdir()
    (tmp_path / "installed").mkdir()
    service = _service(tmp_path)
    blocked = os.path.realpath(tmp_path / "installed")

    real_access = os.access

    def fake_access(path, mode):
        if os.path.realpath(str(path)) == blocked and mode & os.W_OK:
            return False
        return real_access(path, mode)

    monkeypatch.setattr(svc_module.os, "access", fake_access)
    report = asyncio.run(service.preflight_install())
    checks = {item["id"]: item for item in report["checks"]}
    assert report["ok"] is False
    assert checks["install_dir"]["ok"] is False
    assert checks["install_dir"]["message"] == "目录不可写"


def test_preflight_low_disk_space_fails(tmp_path, monkeypatch):
    (tmp_path / "downloads").mkdir()
    (tmp_path / "installed").mkdir()
    service = _service(tmp_path)
    monkeypatch.setattr(
        svc_module.shutil,
        "disk_usage",
        lambda path: SimpleNamespace(total=1, used=1, free=PREFLIGHT_MIN_FREE_BYTES - 1),
    )
    report = asyncio.run(service.preflight_install())
    checks = {item["id"]: item for item in report["checks"]}
    assert report["ok"] is False
    assert checks["disk_free"]["ok"] is False
    assert "剩余空间不足" in checks["disk_free"]["message"]


def test_preflight_disk_usage_error_is_reported(tmp_path, monkeypatch):
    (tmp_path / "downloads").mkdir()
    (tmp_path / "installed").mkdir()
    service = _service(tmp_path)

    def boom(path):
        raise OSError("stat failed")

    monkeypatch.setattr(svc_module.shutil, "disk_usage", boom)
    report = asyncio.run(service.preflight_install())
    checks = {item["id"]: item for item in report["checks"]}
    assert report["ok"] is False
    assert "无法读取磁盘空间" in checks["disk_free"]["message"]


# ---------------------------------------------------------------- verify


def test_verify_pc_game_ok(tmp_path, monkeypatch):
    install_dir = tmp_path / "installed" / "Demo"
    install_dir.mkdir(parents=True)
    (install_dir / "Demo.exe").write_bytes(b"MZ")
    service = _service(tmp_path, [_entry("g1", executable_name="Demo.exe")])
    service.store.installed_games = [_record(tmp_path, install_path=install_dir)]
    monkeypatch.setattr(svc_module, "resolve_tianyi_shortcut_sync", lambda **kwargs: {"ok": True, "appid_unsigned": 123})

    report = asyncio.run(service.verify_installed_game("g1"))
    checks = {item["id"]: item for item in report["checks"]}
    assert report["ok"] is True
    assert report["needs_reinstall"] is False
    assert checks["install_path"]["ok"] is True
    assert checks["executable"]["path"].endswith("Demo.exe")
    assert checks["steam_shortcut"]["appid"] == 123


def test_verify_missing_executable_needs_reinstall(tmp_path, monkeypatch):
    install_dir = tmp_path / "installed" / "Demo"
    install_dir.mkdir(parents=True)
    service = _service(tmp_path, [_entry("g1", executable_name="Missing.exe")])
    service.store.installed_games = [_record(tmp_path, install_path=install_dir)]
    monkeypatch.setattr(svc_module, "resolve_tianyi_shortcut_sync", lambda **kwargs: {"ok": True})

    report = asyncio.run(service.verify_installed_game("g1"))
    checks = {item["id"]: item for item in report["checks"]}
    assert report["ok"] is False
    assert report["needs_reinstall"] is True
    assert checks["executable"]["ok"] is False


def test_verify_emulator_game_checks_rom_and_launcher(tmp_path, monkeypatch):
    rom = tmp_path / "roms" / "demo.gba"
    rom.parent.mkdir(parents=True)
    rom.write_bytes(b"rom")
    launcher = tmp_path / "launch.sh"
    launcher.write_text("#!/bin/sh", encoding="utf-8")
    install_dir = tmp_path / "installed" / "Demo"
    install_dir.mkdir(parents=True)
    service = _service(tmp_path, [_entry("g1", platform="gba")])
    record = _record(tmp_path, platform="gba", install_path=install_dir)
    record.rom_path = str(rom)
    record.launcher_path = str(launcher)
    service.store.installed_games = [record]
    monkeypatch.setattr(svc_module, "resolve_tianyi_shortcut_sync", lambda **kwargs: {"ok": True})

    report = asyncio.run(service.verify_installed_game("g1"))
    checks = {item["id"]: item for item in report["checks"]}
    assert report["ok"] is True
    assert checks["rom"]["ok"] is True
    assert checks["launcher"]["ok"] is True
    assert "executable" not in checks


def test_verify_unknown_game_raises(tmp_path):
    service = _service(tmp_path)
    with pytest.raises(ValueError):
        asyncio.run(service.verify_installed_game("missing"))


# ---------------------------------------------------------------- repair


def test_repair_skips_when_reinstall_needed(tmp_path, monkeypatch):
    service = _service(tmp_path, [_entry("g1")])
    service.store.installed_games = [_record(tmp_path)]
    monkeypatch.setattr(svc_module, "resolve_tianyi_shortcut_sync", lambda **kwargs: {"ok": False})

    result = asyncio.run(service.repair_installed_game("g1"))
    assert result["ok"] is False
    assert result["needs_reinstall"] is True
    assert result["actions"] == []


def test_repair_rebuilds_shortcut_and_updates_appid(tmp_path, monkeypatch):
    install_dir = tmp_path / "installed" / "Demo"
    install_dir.mkdir(parents=True)
    (install_dir / "Demo.exe").write_bytes(b"MZ")
    service = _service(tmp_path, [_entry("g1", executable_name="Demo.exe")])
    record = _record(tmp_path, install_path=install_dir)
    service.store.installed_games = [record]

    async def fake_cover(**kwargs):
        return {"cover_url": "https://example.com/l.jpg", "square_cover_url": "https://example.com/p.jpg", "app_id": 0}

    async def fake_shortcut(**kwargs):
        return {"ok": True, "appid_unsigned": 456, "message": ""}

    monkeypatch.setattr(service, "resolve_catalog_cover", fake_cover)
    monkeypatch.setattr(svc_module, "add_or_update_tianyi_shortcut", fake_shortcut)

    result = asyncio.run(service.repair_installed_game("g1"))
    assert result["ok"] is True
    assert result["actions"][0]["action"] == "shortcut_and_artwork"
    assert result["actions"][0]["ok"] is True
    assert record.steam_app_id == 456


# ---------------------------------------------------------------- health report


def test_installed_health_report_aggregates(tmp_path, monkeypatch):
    good_dir = tmp_path / "installed" / "Good"
    good_dir.mkdir(parents=True)
    (good_dir / "Good.exe").write_bytes(b"MZ")
    service = _service(
        tmp_path,
        [
            _entry("good", title="Good", executable_name="Good.exe"),
            _entry("bad", title="Bad", executable_name="Bad.exe"),
        ],
    )
    service.store.installed_games = [
        _record(tmp_path, "good", install_path=good_dir),
        _record(tmp_path, "bad", install_path=tmp_path / "missing"),
    ]
    monkeypatch.setattr(svc_module, "resolve_tianyi_shortcut_sync", lambda **kwargs: {"ok": True})

    report = asyncio.run(service.installed_health_report())
    assert report["total"] == 2
    assert report["ok"] == 1
    assert report["needs_repair"] == 1
    assert report["needs_reinstall"] == 1
    assert len(report["items"]) == 2


def test_installed_health_report_keeps_going_on_error(tmp_path, monkeypatch):
    service = _service(tmp_path)
    service.store.installed_games = [_record(tmp_path, "boom")]

    async def fake_verify(game_id):
        raise RuntimeError("磁盘错误")

    monkeypatch.setattr(service, "verify_installed_game", fake_verify)
    report = asyncio.run(service.installed_health_report())
    item = report["items"][0]
    assert item["ok"] is False
    assert item["needs_reinstall"] is True
    assert "磁盘错误" in item["error"]


# ---------------------------------------------------------------- diagnose


def test_diagnose_classifies_resolve_stage(tmp_path):
    service = _service(tmp_path, [_entry("g1")])
    service.store.tasks = [_task(error_reason="无法重新获取下载直链（登录可能已失效）")]
    report = asyncio.run(service.diagnose_task("t1"))
    assert report["stage"] == "resolve"
    assert report["can_retry"] is True
    assert report["can_fallback"] is False
    assert any("登录" in item for item in report["suggestions"])


def test_diagnose_detects_alternate_source(tmp_path):
    entries = [
        _entry("g1", server="t"),
        _entry("g2", server="b", down_url="https://pan.baidu.com/s/xyz"),
    ]
    service = _service(tmp_path, entries)
    service.store.tasks = [_task()]
    report = asyncio.run(service.diagnose_task("t1"))
    assert report["can_fallback"] is True


def test_retry_falls_back_automatically_once(tmp_path, monkeypatch):
    service = _service(tmp_path, [_entry("g1")])
    service.store.tasks = [_task(install_status="failed")]
    calls = []

    async def no_readd(task, **kwargs):
        return False

    async def fake_fallback(task_id):
        calls.append(task_id)
        return {"to_provider": "baidu", "tasks": [{"task_id": "new"}]}

    monkeypatch.setattr(service, "_readd_task_download", no_readd)
    monkeypatch.setattr(service, "retry_task_with_fallback", fake_fallback)

    result = asyncio.run(service.retry_task("t1"))
    assert calls == ["t1"]
    assert result["auto_fallback"] is True
    assert result["to_provider"] == "baidu"


def test_retry_without_fallback_reports_failure(tmp_path, monkeypatch):
    service = _service(tmp_path, [_entry("g1")])
    task = _task(install_status="failed")
    service.store.tasks = [task]

    async def no_readd(item, **kwargs):
        return False

    async def no_fallback(task_id):
        raise ValueError("没有其他网盘源可用")

    monkeypatch.setattr(service, "_readd_task_download", no_readd)
    monkeypatch.setattr(service, "retry_task_with_fallback", no_fallback)

    with pytest.raises(RuntimeError, match="无可用备用源"):
        asyncio.run(service.retry_task("t1"))
    assert task.install_status == "failed"
    assert "无备用源" in task.install_message


def test_retry_with_fallback_creates_task_on_other_provider(tmp_path, monkeypatch):
    entries = [
        _entry("g1", server="t"),
        _entry("g2", server="b", down_url="https://pan.baidu.com/s/xyz"),
    ]
    service = _service(tmp_path, entries)
    task = _task(install_status="failed")
    service.store.tasks = [task]

    async def fake_start_install(**kwargs):
        assert kwargs["game_id"] == "g2"
        return {"tasks": [{"task_id": "new"}], "reused": False}

    monkeypatch.setattr(service, "start_install", fake_start_install)
    result = asyncio.run(service.retry_task_with_fallback("t1"))
    assert result["from_provider"] == "tianyi"
    assert result["to_provider"] == "baidu"
    assert result["to_game_id"] == "g2"
    assert result["tasks"] == [{"task_id": "new"}]


def test_retry_with_fallback_rejects_active_task(tmp_path):
    service = _service(tmp_path, [_entry("g1")])
    service.store.tasks = [_task(status="active", install_status="pending")]
    with pytest.raises(ValueError, match="尚未结束"):
        asyncio.run(service.retry_task_with_fallback("t1"))

def test_retry_all_failed_tasks_continues_after_error(tmp_path, monkeypatch):
    service = _service(tmp_path)
    service.store.tasks = [
        _task("g1", task_id="t1"),
        _task("g2", task_id="t2"),
        _task("g3", task_id="t3", install_status="gave_up"),
        _task("g4", task_id="t4", status="active", install_status="pending"),
        _task("g5", task_id="t5", status="complete", install_status="installed"),
    ]

    async def fake_retry(task_id):
        if task_id == "t2":
            raise RuntimeError("直链获取失败")
        return {"task_id": task_id, "auto_fallback": task_id == "t3"}

    monkeypatch.setattr(service, "retry_task", fake_retry)
    result = asyncio.run(service.retry_all_failed_tasks())
    assert result["attempted"] == 3
    assert result["succeeded"] == 2
    assert result["failed"] == 1
    assert [item["task_id"] for item in result["results"]] == ["t1", "t3"]
    assert result["results"][1]["auto_fallback"] is True
    assert result["errors"][0]["task_id"] == "t2"
    assert "直链获取失败" in result["errors"][0]["message"]


def test_retry_all_failed_tasks_noop_without_failures(tmp_path):
    service = _service(tmp_path)
    service.store.tasks = [_task("g1", task_id="t1", status="active", install_status="pending")]
    result = asyncio.run(service.retry_all_failed_tasks())
    assert result == {"attempted": 0, "succeeded": 0, "failed": 0, "results": [], "errors": []}
