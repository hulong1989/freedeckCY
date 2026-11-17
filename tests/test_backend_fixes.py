"""后端可靠性/安全边界回归测试。

覆盖本轮审计确认并修复的问题：

- 安装收尾（post-process）异常时的重试语义：异常中断不能把成员误标 ``post_processed``
  （否则提示“将自动重试”但永不重试），且退避重试需要上限，避免永久重试；
- 插件长时间未启动时，已下载完但未安装的任务不能被 7 天保留策略清掉（丢任务）；
- 卸载与面板刷新/并发卸载的竞态：记录被并发清理时不能删完文件再报错；
- 只读路径（面板轮询）不能修改内存中的 installed_games（SD 卡瞬时不可用会丢记录）；
- 日志文件 O_NOFOLLOW；aria2 运行时元数据（含 RPC secret）0600；
- HTTP 边界：带副作用的 GET 也不能被跨站触发、Origin 端口跟随当前监听端口、
  并发 start 不会留下孤儿服务、错误响应脱敏。
"""

from __future__ import annotations

import asyncio
import socket
import stat
import time
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from aiohttp import web
from aiohttp.test_utils import make_mocked_request

import config
import server_manager
import tianyi_http
import tianyi_service as svc_module
from aria2_manager import Aria2Manager, Aria2Runtime
from tianyi_service import TianyiService, POST_PROCESS_MAX_ATTEMPTS
from tianyi_store import TianyiInstalledGame, TianyiTaskRecord


# ---------------------------------------------------------------------------
# 全离线 TianyiService 装配（只落到 tmp_path，不联网/不碰真实 Steam 目录）
# ---------------------------------------------------------------------------


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
    downloads = tmp_path / "Downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    plugin = _FakePlugin(downloads)

    instance = TianyiService(plugin)
    asyncio.run(instance.initialize())

    async def _no_cover(**kwargs):
        return {}

    async def _no_shortcut(**kwargs):
        return {"ok": False, "message": "test: steam 不可用"}

    async def _no_remove(**kwargs):
        return {"ok": False, "removed": False, "message": "test: steam 不可用"}

    monkeypatch.setattr(instance, "resolve_catalog_cover", _no_cover)
    monkeypatch.setattr(svc_module, "add_or_update_tianyi_shortcut", _no_shortcut)
    monkeypatch.setattr(svc_module, "remove_tianyi_shortcut", _no_remove)

    async def _settled(paths, **kwargs):
        return True, ""

    monkeypatch.setattr(instance, "_wait_payload_settled", _settled)
    monkeypatch.setattr(instance.seven_zip, "test_archive", lambda *a, **k: (True, ""))
    return instance


def _make_zip(path: Path, exe_rel: str = "DemoGame/bin/Demo.exe") -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(exe_rel, b"MZ fake exe")
        zf.writestr("readme.txt", "hello")


def _add_completed_task(
    service: TianyiService,
    tmp_path: Path,
    task_id: str = "t1",
    *,
    group_id: str = "",
    status: str = "complete",
    file_name: str = "",
) -> TianyiTaskRecord:
    pkg = tmp_path / "Downloads" / (file_name or f"{task_id}.zip")
    _make_zip(pkg)
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
        file_size=0,
        group_id=group_id,
    )
    service.store.upsert_tasks([task])
    service.store.save()
    return task


def _patch_aria2(service: TianyiService) -> None:
    async def _ensure_running():
        return {"status": "running"}

    async def _tell_status(gid: str):
        return {"status": "complete", "totalLength": 100, "completedLength": 100, "downloadSpeed": 0}

    service.aria2.ensure_running = _ensure_running  # type: ignore[assignment]
    service.aria2.tell_status = _tell_status  # type: ignore[assignment]


async def _wait(condition, timeout: float = 8.0, message: str = "后台安装未推进") -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        await asyncio.sleep(0.02)
    raise AssertionError(message)


# ---------------------------------------------------------------------------
# 1. post-process 失败：异常不能误标已处理；退避重试；有上限
# ---------------------------------------------------------------------------


def test_post_process_exception_stays_pending_then_retries(service, tmp_path, monkeypatch):
    """安装收尾抛异常：成员必须保持未处理，退避后重试能装完。"""
    task = _add_completed_task(service, tmp_path, task_id="pp-exc")
    _patch_aria2(service)

    original_finalize = service._finalize_group_install

    async def _boom(**kwargs):
        raise RuntimeError("state dir unavailable")

    monkeypatch.setattr(service, "_finalize_group_install", _boom)

    async def _scenario():
        await service.maintenance_tick()
        await _wait(lambda: task.install_status == "failed")
        assert task.post_processed is False, "异常中断的任务不能标记为已处理（否则永远不会重试）"
        assert "自动重试" in task.install_message
        assert service._post_process_backoff_active(task)
        # 第二次 tick 在退避窗口内不应重复调度
        second = await service.maintenance_tick()
        assert second["scheduled"] == 0

        # 环境恢复 + 退避到期：下一轮维护应重新调度并完成安装
        monkeypatch.setattr(service, "_finalize_group_install", original_finalize)
        service._post_process_failures.clear()
        await service.maintenance_tick()
        await _wait(lambda: task.post_processed)
        assert task.install_status == "installed", task.install_message

    asyncio.run(_scenario())
    assert len(service.store.installed_games) == 1


def test_post_process_gives_up_after_max_attempts(service, tmp_path, monkeypatch):
    """持续失败（如安装根不可用）到重试上限后转终态失败，不再无限重试。"""
    task = _add_completed_task(service, tmp_path, task_id="pp-give-up")
    _patch_aria2(service)

    async def _boom(**kwargs):
        raise RuntimeError("install root unavailable")

    monkeypatch.setattr(service, "_finalize_group_install", _boom)

    async def _scenario():
        for _ in range(POST_PROCESS_MAX_ATTEMPTS):
            await service._run_post_process_task(task.task_id)
        assert task.post_processed is True
        assert task.install_status == "gave_up"
        assert "停止自动重试" in task.install_message
        assert "请检查安装目录" in task.install_message
        assert service._post_process_failures == {}
        # 已达到终态：后台维护不再调度
        result = await service.maintenance_tick()
        assert result["scheduled"] == 0

    asyncio.run(_scenario())


def test_post_process_state_save_failure_does_not_escape(service, tmp_path, monkeypatch):
    """后台任务 finally 里 store.save 失败不能变成未处理异常（会静默停掉自动重试）。"""
    task = _add_completed_task(service, tmp_path, task_id="pp-save")
    calls = {"count": 0}

    def _always_fail_save():
        calls["count"] += 1
        raise RuntimeError("disk full")

    async def _noop_post_process(current_task):
        return None

    monkeypatch.setattr(service.store, "save", _always_fail_save)
    monkeypatch.setattr(service, "_post_process_completed_task", _noop_post_process)

    asyncio.run(service._run_post_process_task(task.task_id))
    assert calls["count"] >= 1


# ---------------------------------------------------------------------------
# 2. 保留策略不能丢掉“已下载但未安装”的任务；组内失败分卷不能单独被清理
# ---------------------------------------------------------------------------


def test_complete_unprocessed_task_survives_retention_cleanup(service, tmp_path):
    """插件停机超过 7 天后启动：已下完未安装的任务不能被清掉，必须继续安装。"""
    task = _add_completed_task(service, tmp_path, task_id="old-pending")
    task.updated_at = int(time.time()) - 8 * 24 * 3600
    assert task.post_processed is False
    service.store.save()
    _patch_aria2(service)

    async def _scenario():
        await service.maintenance_tick()
        await _wait(lambda: task.post_processed, message="已下载未安装的老任务被保留策略清掉了")
        assert task.install_status == "installed", task.install_message

    asyncio.run(_scenario())
    assert task in service.store.tasks


def test_retention_keeps_error_part_of_pending_group():
    """同一安装计划还有待安装成员时，组内失败分卷不能被单独清理（否则会放行残缺分卷）。"""
    service = TianyiService.__new__(TianyiService)
    old = int(time.time()) - 8 * 24 * 3600
    ok_member = SimpleNamespace(status="complete", post_processed=False, updated_at=old, group_id="group-1")
    bad_member = SimpleNamespace(status="error", post_processed=False, updated_at=old, group_id="group-1")
    unrelated_error = SimpleNamespace(status="error", post_processed=False, updated_at=old, group_id="")

    tasks = [ok_member, bad_member, unrelated_error]
    service._cleanup_tasks(tasks)

    assert tasks == [ok_member, bad_member]


def test_group_lead_prefers_main_volume_and_keeps_bundled(service, tmp_path, monkeypatch):
    """同秒创建且非主卷 task_id 更小时，收尾 lead 仍要选主卷，不能覆盖 bundled 语义。"""
    group = "lead-pick-group"
    main = _add_completed_task(
        service, tmp_path, task_id="zz-main", group_id=group, file_name="VolGame.7z.001"
    )
    part = _add_completed_task(
        service, tmp_path, task_id="aa-part", group_id=group, file_name="VolGame.7z.002"
    )
    # 同一秒创建：按 created_at+task_id 排序时非主卷 aa-part 排在前面（曾经的 bug 触发条件）
    main.created_at = 100
    part.created_at = 100
    service.store.save()

    def _fake_extract(archive_path, target_dir, **kwargs):
        exe = Path(target_dir) / "bin" / "Vol.exe"
        exe.parent.mkdir(parents=True, exist_ok=True)
        exe.write_bytes(b"MZ")
        return True, ""

    monkeypatch.setattr(service, "_extract_archive_to_dir", _fake_extract)

    asyncio.run(service._run_post_process_task(part.task_id))

    assert main.install_status == "installed"
    assert part.install_status == "bundled", "同一安装计划的非主卷不能被收尾覆盖成 installed"
    assert "由主卷统一解压" in part.install_message
    assert main.post_processed is True and part.post_processed is True
    assert len(service.store.installed_games) == 1


# ---------------------------------------------------------------------------
# 3. 只读路径不能改状态；卸载竞态
# ---------------------------------------------------------------------------


def test_installed_summary_read_path_keeps_state(service, tmp_path):
    """面板轮询（persist=False）只过滤展示，不能把缺失目录的记录从内存裁掉。"""
    keep_dir = tmp_path / "installed" / "Keep"
    keep_dir.mkdir(parents=True)
    service.store.upsert_installed_game(
        TianyiInstalledGame(
            game_id="keep", game_title="Keep", install_path=str(keep_dir), source_path=str(keep_dir)
        )
    )
    service.store.upsert_installed_game(
        TianyiInstalledGame(
            game_id="gone",
            game_title="Gone",
            install_path=str(tmp_path / "installed" / "Gone"),
            source_path="",
        )
    )

    summary = service._build_installed_summary(limit=10, persist=False)
    assert summary["total"] == 1
    assert len(service.store.installed_games) == 2, "只读路径不应修改 installed_games"

    # persist=True 时才真正裁剪并落盘
    service._build_installed_summary(limit=10, persist=True)
    assert len(service.store.installed_games) == 1


def test_uninstall_completes_when_record_pruned_concurrently(service, tmp_path, monkeypatch):
    """文件已删、记录被并发清理（另一路卸载/面板刷新）时，卸载仍应完成而不是报错。"""
    install_dir = tmp_path / "installed" / "Demo"
    install_dir.mkdir(parents=True)
    (install_dir / "game.bin").write_bytes(b"x")
    service.store.upsert_installed_game(
        TianyiInstalledGame(
            game_id="demo-1", game_title="Demo", install_path=str(install_dir), source_path=""
        )
    )

    steam_calls: list[dict] = []

    async def _fake_remove(**kwargs):
        steam_calls.append(kwargs)
        return {"ok": True, "removed": True, "cleanup_ok": True}

    monkeypatch.setattr(svc_module, "remove_tianyi_shortcut", _fake_remove)

    def _remove_after_concurrent_prune(**kwargs):
        # 模拟等锁/删除文件期间另一路已经把这台游戏的记录从 store 里清掉
        service.store.installed_games = [
            item for item in service.store.installed_games if item.game_id != kwargs.get("game_id")
        ]
        return None

    monkeypatch.setattr(service.store, "remove_installed_game", _remove_after_concurrent_prune)

    result = asyncio.run(service.uninstall_installed_game(game_id="demo-1"))

    assert result["removed"] is True
    assert not install_dir.exists()
    assert steam_calls and steam_calls[0]["game_id"] == "demo-1"


def test_uninstall_waits_for_install_finalize_lock(service, tmp_path):
    """卸载与安装收尾使用同一把安装目录锁：收尾未结束前不能删目录。"""
    install_dir = tmp_path / "installed" / "Locked"
    install_dir.mkdir(parents=True)
    (install_dir / "game.bin").write_bytes(b"x")
    service.store.upsert_installed_game(
        TianyiInstalledGame(
            game_id="locked-1", game_title="Locked", install_path=str(install_dir), source_path=""
        )
    )

    async def _scenario():
        lock = service._install_lock_for(str(install_dir))
        await lock.acquire()
        try:
            uninstall = asyncio.create_task(service.uninstall_installed_game(game_id="locked-1"))
            await asyncio.sleep(0.2)
            assert install_dir.exists(), "安装目录锁未生效：卸载在收尾完成前就删除了目录"
            assert not uninstall.done()
        finally:
            lock.release()
        result = await asyncio.wait_for(uninstall, timeout=5.0)
        assert result["removed"] is True

    asyncio.run(_scenario())
    assert not install_dir.exists()


# ---------------------------------------------------------------------------
# 4. /tmp 日志与 aria2 运行时元数据权限
# ---------------------------------------------------------------------------


def test_log_handler_rejects_symlink(tmp_path):
    """日志文件不允许跟随 /tmp 下预先放置的符号链接（避免写穿到任意文件）。"""
    target = tmp_path / "victim.txt"
    target.write_text("keep me", encoding="utf-8")
    link = tmp_path / "freedeckcy.log"
    link.symlink_to(target)

    with pytest.raises(OSError):
        config._PrivateRotatingFileHandler(
            str(link), maxBytes=1024, backupCount=1, encoding="utf-8"
        )
    assert target.read_text(encoding="utf-8") == "keep me"


def test_aria2_runtime_meta_is_private(tmp_path):
    """aria2 运行元数据含 RPC secret：文件 0600、目录 0700。"""
    manager = Aria2Manager(plugin_dir=str(tmp_path), work_dir=str(tmp_path / "aria2"))
    runtime = Aria2Runtime(
        process=None,
        rpc_url="http://127.0.0.1:1/jsonrpc",
        rpc_secret="s3cret-secret",
        binary_path="/bin/true",
        started_at=1,
        pid=0,
    )
    manager._write_runtime_meta(runtime)

    meta_path = tmp_path / "aria2" / "aria2-runtime.json"
    assert meta_path.is_file()
    assert stat.S_IMODE(meta_path.stat().st_mode) == 0o600
    assert stat.S_IMODE((tmp_path / "aria2").stat().st_mode) == 0o700


# ---------------------------------------------------------------------------
# 5. HTTP 边界：跨站（含 GET）拒绝、Origin 端口跟随、并发启停、错误脱敏
# ---------------------------------------------------------------------------


async def _ok_handler(request):
    return web.json_response({"ok": True})


@pytest.mark.asyncio
async def test_cross_site_get_with_side_effect_is_rejected():
    """导出诊断包等 GET 有副作用，不能被任意网页用 <img> 跨站触发。"""
    request = make_mocked_request(
        "GET",
        "/api/tianyi/diagnostics/export",
        headers={"Host": "127.0.0.1:59271", "Sec-Fetch-Site": "cross-site"},
    )
    response = await server_manager.cors_middleware(request, _ok_handler)
    assert response.status == 403


@pytest.mark.asyncio
async def test_cross_origin_get_is_rejected():
    request = make_mocked_request(
        "GET",
        "/api/tianyi/state",
        headers={"Host": "127.0.0.1:59271", "Origin": "https://evil.example"},
    )
    response = await server_manager.cors_middleware(request, _ok_handler)
    assert response.status == 403


@pytest.mark.asyncio
async def test_local_page_request_still_allowed():
    request = make_mocked_request(
        "GET",
        "/api/tianyi/state",
        headers={"Host": "127.0.0.1:59271", "Sec-Fetch-Site": "same-origin"},
    )
    response = await server_manager.cors_middleware(request, _ok_handler)
    assert response.status == 200


def test_allowed_origin_ports_follow_current_server_port():
    """信任的 Origin 端口只能是当前监听端口，换端口后旧端口页面不再被信任。"""
    saved = set(server_manager._ALLOWED_ORIGIN_PORTS)
    try:
        server_manager._set_allowed_origin_port(61000)
        assert server_manager._origin_allowed("http://127.0.0.1:61000")
        assert server_manager._origin_allowed("http://localhost:61000")
        assert not server_manager._origin_allowed("http://127.0.0.1:59271")
        assert not server_manager._origin_allowed("http://127.0.0.1:61001")
    finally:
        server_manager._ALLOWED_ORIGIN_PORTS.clear()
        server_manager._ALLOWED_ORIGIN_PORTS.update(saved)


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_concurrent_start_keeps_single_healthy_server(tmp_path, monkeypatch):
    """并发 start（双击/两个入口）不能互相拆台：都返回成功且服务可用、可停止。"""
    plugin = SimpleNamespace(
        server_running=False,
        server_port=59271,
        server_host="127.0.0.1",
        SETTINGS_KEY="freedeckcy_settings",
        SETTING_RUNNING="running",
        SETTING_PORT="port",
        SETTING_DOWNLOAD_DIR="download_dir",
        downloads_dir=str(tmp_path),
    )
    monkeypatch.setattr(server_manager.utils, "is_port_in_use", lambda port: False)
    monkeypatch.setattr(
        server_manager, "_backup_settings_path", lambda plugin: str(tmp_path / "settings.json")
    )
    saved_ports = set(server_manager._ALLOWED_ORIGIN_PORTS)
    port = _free_tcp_port()

    async def _scenario():
        first, second = await asyncio.gather(
            server_manager.start_server(plugin, port),
            server_manager.start_server(plugin, port),
        )
        assert first["status"] == "success", first
        assert second["status"] == "success", second
        assert plugin.server_running is True
        assert plugin.runner is not None

        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/_healthz") as response:
                assert response.status == 200

        await server_manager.stop_server(plugin)
        assert plugin.server_running is False
        assert plugin.runner is None

    try:
        asyncio.run(_scenario())
    finally:
        server_manager._ALLOWED_ORIGIN_PORTS.clear()
        server_manager._ALLOWED_ORIGIN_PORTS.update(saved_ports)


@pytest.mark.asyncio
async def test_http_error_message_is_redacted(monkeypatch):
    """接口错误信息也可能带 cookie/token，返回前必须脱敏。"""

    class _FailingService:
        async def clear_login(self):
            raise RuntimeError("cookie=SECRET123; token=TOPSECRET456")

    monkeypatch.setattr(tianyi_http, "_service", lambda plugin: _FailingService())
    request = make_mocked_request(
        "POST", "/api/tianyi/login/clear", headers={"Host": "127.0.0.1:59271"}
    )
    response = await tianyi_http.handle_login_clear(request, object())
    payload = response.text

    assert response.status == 500
    assert "SECRET123" not in payload
    assert "TOPSECRET456" not in payload


@pytest.mark.asyncio
async def test_local_web_error_diagnostics_are_masked(monkeypatch):
    """本地网页未就绪错误直传 diagnostics 的路径也必须脱敏。"""
    exc = svc_module.LocalWebNotReadyError(
        "本地网页服务未就绪",
        reason="probe_failed",
        diagnostics={"cookies": "SESSION=SECRETABC", "access_token": "TOPSECRETDEF", "port": 59271},
    )

    class _FailingService:
        async def get_login_url(self):
            raise exc

    monkeypatch.setattr(tianyi_http, "_service", lambda plugin: _FailingService())
    request = make_mocked_request(
        "GET", "/api/tianyi/login-url", headers={"Host": "127.0.0.1:59271"}
    )
    response = await tianyi_http.handle_login_url(request, object())
    payload = response.text

    assert response.status == 503
    assert "SECRETABC" not in payload
    assert "TOPSECRETDEF" not in payload
    assert "probe_failed" in payload


# ---------------------------------------------------------------------------
# 6. state.json 损坏恢复（入口层验证：插件能启动并重建 0600 状态）
# ---------------------------------------------------------------------------


def test_service_initializes_with_corrupt_state(tmp_path, monkeypatch):
    """state.json 损坏时服务仍能初始化：坏文件备份为 0600，新状态重建为 0600。"""
    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path / "state"))
    state_dir = tmp_path / "state" / "tianyi"
    state_dir.mkdir(parents=True)
    corrupt = state_dir / "state.json"
    corrupt.write_bytes(b"{not-json")
    (tmp_path / "Downloads").mkdir()

    instance = TianyiService(_FakePlugin(tmp_path / "Downloads"))
    asyncio.run(instance.initialize())  # 不应抛出

    backups = list(state_dir.glob("state.json.corrupt-*"))
    assert len(backups) == 1
    assert stat.S_IMODE(backups[0].stat().st_mode) == 0o600
    assert (state_dir / "state.json").is_file()
    assert stat.S_IMODE((state_dir / "state.json").stat().st_mode) == 0o600


def test_maintenance_still_schedules_completed_task_when_refresh_fails(tmp_path, monkeypatch):
    """aria2 同步超时不能让已完成任务永远卡在“下载完成未安装”。"""
    from tianyi_store import TianyiStateStore, TianyiTaskRecord

    service = TianyiService.__new__(TianyiService)
    service.store = TianyiStateStore(str(tmp_path / "state.json"))
    service._maintenance_lock = asyncio.Lock()
    service._refresh_lock = asyncio.Lock()
    service._post_process_jobs = {}
    service._migrate_all_legacy_backups = lambda: 0
    service._poll_game_watch = lambda: None
    service._maybe_schedule_launcher_repair = lambda: None
    task = TianyiTaskRecord(
        task_id="done-1",
        gid="g1",
        game_id="g1",
        game_title="Demo",
        share_code="code",
        share_id="share",
        file_id="file",
        file_name="Demo.zip",
        speed=0,
        download_dir=str(tmp_path),
        local_path=str(tmp_path / "Demo.zip"),
        status="complete",
        progress=100.0,
        post_processed=False,
    )
    service.store.upsert_tasks([task])
    scheduled = []

    async def _timeout(**kwargs):
        raise asyncio.TimeoutError()

    monkeypatch.setattr(service, "refresh_tasks", _timeout)
    def _schedule_once(item):
        if item.task_id not in scheduled:
            scheduled.append(item.task_id)

    monkeypatch.setattr(service, "_maybe_schedule_group_post_process", _schedule_once)

    result = asyncio.run(service.maintenance_tick())

    assert scheduled == ["done-1"]
    assert result["ok"] is False
    assert "TimeoutError" in result["message"]


def test_recover_unfinished_install_task_resets_post_processed(tmp_path):
    """旧版本把失败任务标成 post_processed，升级后必须重新排队安装。"""
    from tianyi_store import TianyiStateStore, TianyiTaskRecord

    service = TianyiService.__new__(TianyiService)
    service.store = TianyiStateStore(str(tmp_path / "state.json"))
    task = TianyiTaskRecord(
        task_id="stuck-1",
        gid="g1",
        game_id="stuck-game",
        game_title="Stuck",
        share_code="code",
        share_id="share",
        file_id="file",
        file_name="Stuck.zip",
        speed=0,
        download_dir=str(tmp_path),
        local_path=str(tmp_path / "Stuck.zip"),
        status="complete",
        progress=100.0,
        post_processed=True,
        install_status="failed",
        install_message="安装流程异常",
    )
    service.store.upsert_tasks([task])

    assert service._recover_unfinished_install_tasks() == 1
    assert task.post_processed is False
    assert task.install_status == "pending"
    assert "重新排队" in task.install_message


def test_quarantine_stale_aria2_sidecar(tmp_path):
    from tianyi_service import TianyiService

    payload = tmp_path / "30XX.zip"
    payload.write_bytes(b"PK\x03\x04data")
    sidecar = tmp_path / "30XX.zip.aria2"
    sidecar.write_bytes(b"stale-control")
    service = TianyiService.__new__(TianyiService)

    assert service._quarantine_stale_aria2_sidecars([str(payload)]) is True
    assert payload.is_file()
    assert not sidecar.exists()
    assert list(tmp_path.glob("30XX.zip.aria2.stale-*"))


def test_remove_task_immediately_drops_removed_record(tmp_path):
    from tianyi_store import TianyiStateStore, TianyiTaskRecord

    service = TianyiService.__new__(TianyiService)
    service.store = TianyiStateStore(str(tmp_path / "state.json"))
    service._invalidate_panel_cache = lambda **kwargs: None

    class _Aria:
        removed = []

        async def remove(self, gid):
            self.removed.append(gid)

    service.aria2 = _Aria()
    task = TianyiTaskRecord(
        task_id="remove-me",
        gid="g-remove",
        game_id="g1",
        game_title="Demo",
        share_code="code",
        share_id="share",
        file_id="file",
        file_name="Demo.zip",
        speed=0,
        download_dir=str(tmp_path),
        local_path=str(tmp_path / "Demo.zip"),
        status="error",
        progress=0.0,
    )
    service.store.upsert_tasks([task])

    asyncio.run(service.remove_task("remove-me"))

    assert service.store.tasks == []
    assert service.aria2.removed == ["g-remove"]
