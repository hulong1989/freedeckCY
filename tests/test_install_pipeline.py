"""安装链路与路径安全的回归测试。

重点是本次补全修复的两个 P0：
1. 下载完成后由后台维护推进安装（不再依赖 QAM 面板轮询）；
2. 同一安装目录串行、可重入（分卷/多包任务不会互相覆盖）。
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import zipfile
from pathlib import Path

import pytest

import config
import tianyi_service as svc_module
from tianyi_service import TianyiService, _is_within_dir
from tianyi_store import TianyiInstalledGame, TianyiTaskRecord


class _FakePlugin:
    def __init__(self, downloads_dir: Path):
        self.downloads_dir = str(downloads_dir)
        self.server_running = False
        self.server_port = 59271

    async def set_download_dir(self, path: str):
        self.downloads_dir = path
        return {"status": "success", "path": path}


@pytest.fixture()
def service(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path / "state"))
    plugin = _FakePlugin(tmp_path / "Downloads")
    (tmp_path / "Downloads").mkdir(parents=True, exist_ok=True)

    instance = TianyiService(plugin)
    asyncio.run(instance.initialize())

    # 网络相关全部打桩：封面解析、Steam 注册。
    async def _no_cover(**kwargs):
        return {}

    async def _no_shortcut(**kwargs):
        return {"ok": False, "message": "test: steam 不可用"}

    monkeypatch.setattr(instance, "resolve_catalog_cover", _no_cover)
    monkeypatch.setattr(svc_module, "add_or_update_tianyi_shortcut", _no_shortcut)

    # 收尾等待（.aria2 控制文件 + 大小稳定）在集成测试里没有意义，单独测；
    # 这里默认直接判定“已收尾”，避免每个用例多等 1 秒。
    async def _settled(paths, **kwargs):
        return True, ""

    monkeypatch.setattr(instance, "_wait_payload_settled", _settled)

    # 7z 校验在集成测试里默认视为通过（真实二进制是 Linux 版，macOS 上跑不了）
    def _verified(archive_path, timeout=900.0):
        return True, ""

    monkeypatch.setattr(instance.seven_zip, "test_archive", _verified)
    return instance


def _make_zip(path: Path, exe_rel: str) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(exe_rel, b"MZ fake exe")
        zf.writestr("readme.txt", "hello")


def _add_completed_task(
    service: TianyiService,
    tmp_path: Path,
    task_id: str = "t1",
    *,
    group_id: str = "",
    file_size: int = 0,
    status: str = "complete",
    entry: str = "DemoGame/bin/Demo.exe",
    payload_name: str = "",
    file_name: str = "",
) -> TianyiTaskRecord:
    pkg = tmp_path / "Downloads" / (file_name or f"{task_id}.zip")
    _make_zip(pkg, entry)
    task = TianyiTaskRecord(
        task_id=task_id,
        gid=f"g-{task_id}",
        game_id="1001",
        game_title="DemoGame",
        share_code="code",
        share_id="share",
        file_id="file",
        file_name=pkg.name,
        download_dir=str(pkg.parent),
        local_path=str(pkg),
        status=status,
        progress=100.0 if status == "complete" else 0.0,
        speed=0,
        openpath="DemoGame/bin/Demo.exe",
        file_size=file_size,
        group_id=group_id,
        group_total=0,
    )
    if payload_name:
        # 覆盖 zip 内容，用于分卷/多包场景
        with zipfile.ZipFile(pkg, "w") as zf:
            zf.writestr(payload_name, b"payload")
    service.store.upsert_tasks([task])
    service.store.save()
    return task


async def _wait_processed(task: TianyiTaskRecord, timeout: float = 8.0) -> None:
    """在同一个事件循环里等待后台安装完成。

    注意：不能在 asyncio.run() 外层等待——每次 asyncio.run 都会新建并关闭事件
    循环，后台任务会被连带取消（Decky 运行时只有一个常驻循环，不存在此问题）。
    """
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if task.post_processed:
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"安装未被后台维护推进: status={task.install_status} msg={task.install_message}")


def _patch_aria2(service: TianyiService) -> None:
    async def _ensure_running():
        return {"status": "running"}

    async def _tell_status(gid: str):
        return {
            "status": "complete",
            "totalLength": 100,
            "completedLength": 100,
            "downloadSpeed": 0,
        }

    service.aria2.ensure_running = _ensure_running  # type: ignore[assignment]
    service.aria2.tell_status = _tell_status  # type: ignore[assignment]


def test_background_tick_installs_completed_task(service, tmp_path):
    task = _add_completed_task(service, tmp_path)
    _patch_aria2(service)

    async def _scenario():
        result = await service.maintenance_tick()
        assert result["ok"] is True
        assert result["scheduled"] == 1
        await _wait_processed(task)

    asyncio.run(_scenario())
    assert task.install_status == "installed", task.install_message
    assert task.installed_path

    records = list(service.store.installed_games)
    assert len(records) == 1
    assert records[0].game_id == "1001"
    assert records[0].size_bytes > 0

    # 压缩包里套了一层同名目录，合并时应被去掉
    extracted = Path(task.installed_path) / "bin" / "Demo.exe"
    assert extracted.is_file()


def test_second_tick_does_not_reprocess(service, tmp_path):
    task = _add_completed_task(service, tmp_path, task_id="t2")
    _patch_aria2(service)

    async def _scenario():
        await service.maintenance_tick()
        await _wait_processed(task)
        return await service.maintenance_tick()

    second = asyncio.run(_scenario())
    assert task.post_processed is True
    assert second["scheduled"] == 0
    assert second["pending_post_process"] == 0


def test_missing_archive_marks_failed_but_processed(service, tmp_path):
    task = _add_completed_task(service, tmp_path, task_id="t3")
    Path(task.local_path).unlink()
    _patch_aria2(service)

    async def _scenario():
        await service.maintenance_tick()
        await _wait_processed(task)

    asyncio.run(_scenario())
    assert task.install_status == "failed"
    assert "不存在" in task.install_message


def test_is_within_dir_rejects_escape(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    (base / "ok.txt").write_text("x")
    (tmp_path / "base_evil").mkdir()

    assert _is_within_dir(base / "ok.txt", base) is True
    assert _is_within_dir(base, base) is True
    assert _is_within_dir(tmp_path / "base_evil" / "x", base) is False
    assert _is_within_dir(base / ".." / "escape", base) is False


def test_group_waits_for_all_parts_then_installs_once(service, tmp_path, monkeypatch):
    """分卷/多包：必须全部下完才安装，且只注册一次 Steam。"""
    group = "group-demo-1"
    part_a = _add_completed_task(
        service, tmp_path, task_id="part-a", group_id=group, status="waiting",
        entry="DemoGame/bin/Demo.exe",
    )
    part_b = _add_completed_task(
        service, tmp_path, task_id="part-b", group_id=group, status="waiting",
        payload_name="DemoGame/data.pak",
    )

    registered = []

    async def _fake_shortcut(**kwargs):
        registered.append(kwargs)
        return {"ok": False, "message": "test: steam 不可用"}

    monkeypatch.setattr(svc_module, "add_or_update_tianyi_shortcut", _fake_shortcut)

    async def _tell_status(gid: str):
        return {"status": "complete", "totalLength": 100, "completedLength": 100, "downloadSpeed": 0}

    async def _ensure_running():
        return {"status": "running"}

    service.aria2.ensure_running = _ensure_running  # type: ignore[assignment]
    service.aria2.tell_status = _tell_status  # type: ignore[assignment]

    async def _scenario():
        await service.maintenance_tick()
        # 第一个 tick 之后两个任务都 complete，组才被调度
        for _ in range(100):
            if part_a.post_processed and part_b.post_processed:
                return
            await asyncio.sleep(0.05)
        raise AssertionError("分卷组未被处理")

    asyncio.run(_scenario())

    assert part_a.post_processed and part_b.post_processed
    assert part_a.install_status == "installed"
    assert part_b.install_status == "installed"
    target = Path(part_a.installed_path)
    assert (target / "bin" / "Demo.exe").is_file()
    assert (target / "data.pak").is_file()

    records = list(service.store.installed_games)
    assert len(records) == 1
    # 体积按两个包累加
    assert records[0].size_bytes == Path(part_a.local_path).stat().st_size + Path(part_b.local_path).stat().st_size
    assert len(registered) == 1


def test_recovers_gid_after_aria2_restart(service, tmp_path):
    """插件重载后 aria2 用新 gid 续传，应按文件路径重新认领。"""
    from aria2_manager import Aria2Error

    task = _add_completed_task(service, tmp_path, task_id="recover", status="waiting")
    original_gid = task.gid
    new_gid = "gid-after-restart"

    async def _ensure_running():
        return {"status": "running"}

    async def _tell_status(gid: str):
        if gid == original_gid:
            raise Aria2Error("aria2 rpc 错误 code=1 message=GID not found")
        return {"status": "active", "totalLength": 100, "completedLength": 40, "downloadSpeed": 10}

    async def _list_downloads():
        return [{"gid": new_gid, "status": "active", "files": [{"path": os.path.realpath(task.local_path)}]}]

    service.aria2.ensure_running = _ensure_running  # type: ignore[assignment]
    service.aria2.tell_status = _tell_status  # type: ignore[assignment]
    service.aria2.list_downloads = _list_downloads  # type: ignore[assignment]

    asyncio.run(service.refresh_tasks())

    assert task.gid == new_gid
    assert task.status == "active"
    assert task.progress > 0


def test_completed_file_on_disk_is_trusted_after_restart(service, tmp_path):
    """gid 丢失但文件已完整落盘：判为完成并进入安装。"""
    from aria2_manager import Aria2Error

    pkg_size = 0
    task = _add_completed_task(service, tmp_path, task_id="ondisk", status="waiting")
    pkg_size = Path(task.local_path).stat().st_size
    task.file_size = pkg_size

    async def _ensure_running():
        return {"status": "running"}

    async def _tell_status(gid: str):
        raise Aria2Error("GID not found")

    async def _list_downloads():
        return []

    service.aria2.ensure_running = _ensure_running  # type: ignore[assignment]
    service.aria2.tell_status = _tell_status  # type: ignore[assignment]
    service.aria2.list_downloads = _list_downloads  # type: ignore[assignment]

    async def _scenario():
        await service.maintenance_tick()
        for _ in range(100):
            if task.post_processed:
                return
            await asyncio.sleep(0.05)
        raise AssertionError("已落盘任务未被推进")

    asyncio.run(_scenario())
    assert task.status == "complete"
    assert task.install_status == "installed"


def test_size_mismatch_marks_error(service, tmp_path):
    """下载完整性与资源记录不符时判错，不进入安装。"""
    task = _add_completed_task(service, tmp_path, task_id="bad-size", status="waiting")
    task.file_size = 999999  # 与真实 zip 大小不符

    async def _ensure_running():
        return {"status": "running"}

    async def _tell_status(gid: str):
        return {"status": "complete", "totalLength": 100, "completedLength": 100, "downloadSpeed": 0}

    service.aria2.ensure_running = _ensure_running  # type: ignore[assignment]
    service.aria2.tell_status = _tell_status  # type: ignore[assignment]

    asyncio.run(service.refresh_tasks())

    assert task.status == "error"
    assert "校验失败" in task.error_reason
    assert task.post_processed is False


def test_readds_download_when_aria2_session_lost(service, tmp_path, monkeypatch):
    """aria2 会话文件丢失（且本地文件不完整）时，用原直链自动重新加入下载。"""
    from aria2_manager import Aria2Error

    task = _add_completed_task(service, tmp_path, task_id="readd", status="waiting")
    Path(task.local_path).unlink()

    added = []

    async def _ensure_running():
        return {"status": "running"}

    async def _tell_status(gid: str):
        raise Aria2Error("GID not found")

    async def _list_downloads():
        return []

    async def _add_uri(**kwargs):
        added.append(kwargs)
        return "gid-readded"

    async def _fetch_token(cookie):
        return "access-token"

    async def _fetch_url(cookie, token, share_id, file_id):
        return "https://api.cloud.189.cn/download/fake"

    service.aria2.ensure_running = _ensure_running  # type: ignore[assignment]
    service.aria2.tell_status = _tell_status  # type: ignore[assignment]
    service.aria2.list_downloads = _list_downloads  # type: ignore[assignment]
    service.aria2.add_uri = _add_uri  # type: ignore[assignment]
    service.store.login.cookie = "UID=1; TEST=1"
    service.store.login.user_account = "tester"

    monkeypatch.setattr(svc_module, "fetch_access_token", _fetch_token)
    monkeypatch.setattr(svc_module, "fetch_download_url", _fetch_url)

    asyncio.run(service.refresh_tasks())

    assert task.gid == "gid-readded"
    assert task.status == "waiting"
    assert len(added) == 1
    assert added[0]["out_name"] == task.file_name


def test_group_with_failed_part_blocks_until_removed(service, tmp_path):
    """组里有分卷失败时不安装；用户移除失败任务后，剩余分卷继续安装。"""
    group = "group-with-failure"
    ok_task = _add_completed_task(service, tmp_path, task_id="ok-part", group_id=group, status="waiting")
    bad_task = _add_completed_task(service, tmp_path, task_id="bad-part", group_id=group, status="error")

    async def _ensure_running():
        return {"status": "running"}

    async def _tell_status(gid: str):
        return {"status": "complete", "totalLength": 100, "completedLength": 100, "downloadSpeed": 0}

    service.aria2.ensure_running = _ensure_running  # type: ignore[assignment]
    service.aria2.tell_status = _tell_status  # type: ignore[assignment]

    async def _tick():
        return await service.maintenance_tick()

    first = asyncio.run(_tick())
    assert first["scheduled"] == 0
    assert ok_task.post_processed is False
    assert "分卷" in ok_task.install_message

    # 用户移除失败分卷后，剩余部分应该能继续安装
    bad_task.status = "removed"

    async def _scenario():
        await service.maintenance_tick()
        for _ in range(100):
            if ok_task.post_processed:
                return
            await asyncio.sleep(0.05)
        raise AssertionError("移除失败分卷后组未被安装")

    asyncio.run(_scenario())
    assert ok_task.install_status == "installed"
    assert len(service.store.installed_games) == 1


def test_multi_volume_extracts_only_entry(service, tmp_path, monkeypatch):
    """多分卷归档只解主卷，其余分卷标记 bundled。"""
    group = "bundle-group"
    part1 = _add_completed_task(
        service, tmp_path, task_id="v1", group_id=group, status="waiting",
        file_name="Game.7z.001",
    )
    part2 = _add_completed_task(
        service, tmp_path, task_id="v2", group_id=group, status="waiting",
        file_name="Game.7z.002",
    )

    extracted = []

    def _fake_extract(archive_path, target_dir, **kwargs):
        extracted.append((archive_path, kwargs))
        exe = Path(target_dir) / "bin" / "Demo.exe"
        exe.parent.mkdir(parents=True, exist_ok=True)
        exe.write_bytes(b"MZ")
        return True, ""

    monkeypatch.setattr(service, "_extract_archive_to_dir", _fake_extract)

    async def _ensure_running():
        return {"status": "running"}

    async def _tell_status(gid: str):
        return {"status": "complete", "totalLength": 100, "completedLength": 100, "downloadSpeed": 0}

    service.aria2.ensure_running = _ensure_running  # type: ignore[assignment]
    service.aria2.tell_status = _tell_status  # type: ignore[assignment]

    async def _scenario():
        await service.maintenance_tick()
        for _ in range(100):
            if part1.post_processed and part2.post_processed:
                return
            await asyncio.sleep(0.05)
        raise AssertionError("分卷组未被处理")

    asyncio.run(_scenario())

    assert len(extracted) == 1, extracted
    extracted_path, kwargs = extracted[0]
    assert extracted_path.endswith("Game.7z.001")
    assert kwargs.get("force_seven_zip") is True

    assert part1.install_status == "installed"
    assert part2.install_status == "bundled"
    assert "主卷" in part2.install_message

    records = list(service.store.installed_games)
    assert len(records) == 1
    assert records[0].size_bytes == (
        Path(part1.local_path).stat().st_size + Path(part2.local_path).stat().st_size
    )


def test_missing_volume_fails_without_install(service, tmp_path):
    """缺少中间分卷时不安装，并给出缺失清单。"""
    group = "broken-bundle"
    part1 = _add_completed_task(
        service, tmp_path, task_id="b1", group_id=group, status="waiting",
        file_name="Game.7z.001",
    )
    part3 = _add_completed_task(
        service, tmp_path, task_id="b3", group_id=group, status="waiting",
        file_name="Game.7z.003",
    )

    async def _ensure_running():
        return {"status": "running"}

    async def _tell_status(gid: str):
        return {"status": "complete", "totalLength": 100, "completedLength": 100, "downloadSpeed": 0}

    service.aria2.ensure_running = _ensure_running  # type: ignore[assignment]
    service.aria2.tell_status = _tell_status  # type: ignore[assignment]

    async def _scenario():
        await service.maintenance_tick()
        for _ in range(100):
            if part1.post_processed and part3.post_processed:
                return
            await asyncio.sleep(0.05)
        raise AssertionError("缺失分卷的任务未被处理")

    asyncio.run(_scenario())

    assert part1.install_status == "failed"
    assert "分卷不完整" in part1.install_message
    assert "Game.7z.002" in part1.install_message
    assert len(service.store.installed_games) == 0


def test_wait_payload_settled_detects_stable_file(service, tmp_path):
    path = tmp_path / "payload.zip"
    path.write_bytes(b"PK\x03\x04data")

    # 注意：service fixture 把 _wait_payload_settled 打了桩，这里要测原始实现。
    ok, message = asyncio.run(
        TianyiService._wait_payload_settled(
            service, [str(path)], timeout_seconds=2.0, poll_seconds=0.05, stable_required=2
        )
    )
    assert ok is True
    assert message == ""


def test_wait_payload_settled_respects_aria2_control_file(service, tmp_path):
    path = tmp_path / "payload.zip"
    path.write_bytes(b"PK\x03\x04data")
    control = tmp_path / "payload.zip.aria2"
    control.write_bytes(b"ctrl")

    ok, message = asyncio.run(
        TianyiService._wait_payload_settled(
            service, [str(path)], timeout_seconds=0.3, poll_seconds=0.05, stable_required=2
        )
    )
    assert ok is False
    assert "控制文件" in message


def test_precheck_archive_payload_rejects_html_and_empty(service, tmp_path):
    html = tmp_path / "login.html"
    html.write_bytes(b"<!DOCTYPE html><html><body>login</body></html>")
    ok, message = service._precheck_archive_payload(str(html))
    assert ok is False
    assert "网页" in message

    empty = tmp_path / "empty.7z"
    empty.write_bytes(b"")
    ok, message = service._precheck_archive_payload(str(empty))
    assert ok is False

    good = tmp_path / "good.7z"
    good.write_bytes(b"7z\xbc\xaf\x27\x1c" + b"0" * 32)
    ok, message = service._precheck_archive_payload(str(good))
    assert ok is True


def test_archive_validation_failure_schedules_redownload(service, tmp_path, monkeypatch):
    """7z t 失败：隔离坏文件 + 自动重新下载，且不把任务标记为已处理。"""
    task = _add_completed_task(service, tmp_path, task_id="bad-archive", status="waiting")
    _patch_aria2(service)
    monkeypatch.setattr(
        service.seven_zip, "test_archive", lambda *a, **k: (False, "归档校验失败: 数据损坏")
    )

    async def _fetch_token(cookie):
        return "token"

    async def _fetch_url(cookie, token, share_id, file_id):
        return "https://api.cloud.189.cn/fake"

    async def _add_uri(**kwargs):
        return "gid-repaired"

    monkeypatch.setattr(svc_module, "fetch_access_token", _fetch_token)
    monkeypatch.setattr(svc_module, "fetch_download_url", _fetch_url)
    service.aria2.add_uri = _add_uri  # type: ignore[assignment]
    service.store.login.cookie = "UID=1; TEST=1"

    async def _scenario():
        await service.maintenance_tick()
        for _ in range(120):
            if task.gid == "gid-repaired":
                return
            await asyncio.sleep(0.05)
        raise AssertionError(f"未触发重新下载: status={task.status} msg={task.install_message}")

    asyncio.run(_scenario())
    assert task.post_processed is False
    assert "归档" in task.install_message
    assert "下载" in task.install_message


def test_retry_task_reinstalls_complete_file(service, tmp_path):
    """失败任务重试：文件已完整时直接重新安装。"""
    task = _add_completed_task(service, tmp_path, task_id="retry-ok", status="error")
    task.file_size = Path(task.local_path).stat().st_size
    task.error_reason = "模拟失败"

    async def _scenario():
        view = await service.retry_task(task.task_id)
        assert view["status"] == "complete"
        for _ in range(120):
            if task.post_processed:
                return
            await asyncio.sleep(0.05)
        raise AssertionError("重试后未被安装")

    asyncio.run(_scenario())
    assert task.install_status == "installed"
    assert len(service.store.installed_games) == 1


def test_retry_task_readds_when_file_missing(service, tmp_path, monkeypatch):
    """失败任务重试：文件不完整时重新获取直链加入下载。"""
    task = _add_completed_task(service, tmp_path, task_id="retry-missing", status="error")
    Path(task.local_path).unlink()

    async def _fetch_token(cookie):
        return "token"

    async def _fetch_url(cookie, token, share_id, file_id):
        return "https://api.cloud.189.cn/fake"

    async def _add_uri(**kwargs):
        return "gid-retry"

    monkeypatch.setattr(svc_module, "fetch_access_token", _fetch_token)
    monkeypatch.setattr(svc_module, "fetch_download_url", _fetch_url)
    service.aria2.add_uri = _add_uri  # type: ignore[assignment]
    service.store.login.cookie = "UID=1; TEST=1"

    view = asyncio.run(service.retry_task(task.task_id))
    assert view["status"] == "waiting"
    assert task.gid == "gid-retry"


def test_uninstall_preview_and_compatdata_cleanup(service, tmp_path, monkeypatch):
    """卸载可选回收 Proton 前缀，并给出预览大小。"""
    home = tmp_path / "home"
    main_root = home / ".steam" / "steam"
    (main_root / "steamapps").mkdir(parents=True)
    sd_library = home / "sdcard" / "SteamLibrary"
    compat = sd_library / "steamapps" / "compatdata" / "123456" / "pfx" / "drive_c" / "users" / "steamuser"
    compat.mkdir(parents=True)
    (compat / "save.dat").write_bytes(b"x" * 1024)
    (main_root / "steamapps" / "libraryfolders.vdf").write_text(
        '"libraryfolders"\n{\n'
        f'\t"0"\n\t{{\n\t\t"path"\t\t"{main_root}"\n\t}}\n'
        f'\t"1"\n\t{{\n\t\t"path"\t\t"{sd_library}"\n\t}}\n'
        "}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(
        svc_module,
        "remove_tianyi_shortcut",
        lambda **kwargs: {"ok": True, "removed": True, "cleanup_ok": True},
    )

    install_dir = tmp_path / "installed" / "DemoGame"
    install_dir.mkdir(parents=True)
    (install_dir / "game.bin").write_bytes(b"y" * 2048)
    service.store.upsert_installed_game(
        TianyiInstalledGame(
            game_id="1001",
            game_title="DemoGame",
            install_path=str(install_dir),
            source_path="",
            steam_app_id=123456,
        )
    )

    preview = asyncio.run(service.preview_uninstall(game_id="1001"))
    assert preview["install_size_bytes"] == 2048
    assert preview["compatdata_size_bytes"] == 1024
    assert preview["steam_app_id"] == 123456
    assert preview["compatdata_paths"]

    result = asyncio.run(service.uninstall_installed_game(game_id="1001", delete_compatdata=True))
    assert result["compatdata"]["freed_bytes"] == 1024
    assert result["compatdata"]["removed_paths"]
    assert not (sd_library / "steamapps" / "compatdata" / "123456").exists()
    assert not install_dir.exists()


def test_non_pc_platform_install_is_rejected(service, tmp_path, monkeypatch):
    """模拟器资源当前只可浏览，安装应得到明确提示而不是去下整包。"""
    csv_path = tmp_path / "switch_catalog.csv"
    csv_path.write_text(
        "game_id,title,categories,down_url,pwd,openpath,platform,filesize_z,list_filesize\n"
        "9001,SwitchGame,角色扮演,https://cloud.189.cn/t/abcdef,1234,SwitchGame/mario.nsp,switch,1000,1 KB\n",
        encoding="utf-8-sig",
    )
    catalog = svc_module.GameCatalog(str(csv_path))
    catalog.load()
    service.catalog = catalog

    async def _login_ok():
        return True, "tester", ""

    monkeypatch.setattr(service, "check_login_state", _login_ok)

    try:
        asyncio.run(service._build_install_plan(game_id="9001"))
    except ValueError as exc:
        assert "暂未接入模拟器" in str(exc)
    else:
        raise AssertionError("非 PC 资源不应生成安装计划")


def test_list_installed_games_includes_catalog_metadata(service, tmp_path):
    entry = service.catalog.entries[0]
    install_dir = tmp_path / "installed" / "LibraryGame"
    install_dir.mkdir(parents=True)
    (install_dir / "game.bin").write_bytes(b"x" * 128)
    service.store.upsert_installed_game(
        TianyiInstalledGame(
            game_id=entry.game_id,
            game_title=entry.title,
            install_path=str(install_dir),
            source_path="",
            steam_app_id=424242,
        )
    )

    data = asyncio.run(service.list_installed_games())
    assert data["total"] == 1
    item = data["items"][0]
    assert item["exists"] is True
    assert item["platform"] == entry.platform
    assert item["steam_app_id"] == 424242


def test_launch_installed_game_uses_steam_url(service, tmp_path, monkeypatch):
    install_dir = tmp_path / "installed" / "LaunchMe"
    install_dir.mkdir(parents=True)
    service.store.upsert_installed_game(
        TianyiInstalledGame(
            game_id="launch-1",
            game_title="LaunchMe",
            install_path=str(install_dir),
            source_path="",
            steam_app_id=123456,
        )
    )
    captured = {}
    monkeypatch.setattr(svc_module, "_launch_external", lambda target: captured.update(target=target))

    result = asyncio.run(service.launch_installed_game("launch-1"))
    assert result["steam_app_id"] == 123456
    assert captured["target"] == "steam://rungameid/123456"


def test_launch_installed_game_requires_app_id(service, tmp_path, monkeypatch):
    install_dir = tmp_path / "installed" / "NoAppId"
    install_dir.mkdir(parents=True)
    service.store.upsert_installed_game(
        TianyiInstalledGame(
            game_id="no-appid",
            game_title="NoAppId",
            install_path=str(install_dir),
            source_path="",
            steam_app_id=0,
        )
    )
    monkeypatch.setattr(svc_module, "resolve_tianyi_shortcut_sync", lambda game_id: {})

    with pytest.raises(ValueError):
        asyncio.run(service.launch_installed_game("no-appid"))


def test_open_installed_folder_launches_path(service, tmp_path, monkeypatch):
    install_dir = tmp_path / "installed" / "FolderGame"
    install_dir.mkdir(parents=True)
    service.store.upsert_installed_game(
        TianyiInstalledGame(
            game_id="folder-1",
            game_title="FolderGame",
            install_path=str(install_dir),
            source_path="",
        )
    )
    captured = {}
    monkeypatch.setattr(svc_module, "_launch_external", lambda target: captured.update(target=target))

    result = asyncio.run(service.open_installed_folder("folder-1"))
    assert result["opened"] is True
    assert captured["target"] == os.path.realpath(str(install_dir))


def test_diagnostics_redacts_home_and_tokens(service):
    service.store.login.cookie = "UID=12345; accessToken=supersecret"
    service.store.set_settings(download_dir=os.path.expanduser("~/Games"))

    diagnostics = asyncio.run(service.get_diagnostics())
    text = json.dumps(diagnostics, ensure_ascii=False)

    assert "supersecret" not in text
    assert "UID=12345" not in text
    assert "~/Games" in text
    assert diagnostics["catalog"]["total"] > 0
    assert set(diagnostics["runtime"]) == {"aria2", "7z", "node"}
    assert "log_tail" in diagnostics


def test_export_diagnostics_zip(service):
    payload = asyncio.run(service.export_diagnostics())
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = set(archive.namelist())
        assert {"diagnostics.json", "log-tail.txt", "README.txt"} <= names
        content = archive.read("diagnostics.json").decode("utf-8")
        assert "version" in content
