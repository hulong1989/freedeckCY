"""重启恢复、并发双入口、卸载竞态的全模拟。

对应真机上的三条关键路径：
- 插件/设备重启后：任务还在，但 aria2 gid 全变，需要按文件路径认领并继续；
- 用户双击/两个入口同时点安装：不能创建两份下载、两个解压流程；
- 安装收尾与卸载并发：必须串行，不能出现“删到一半又开始解压”。
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

import config
from tests.sim.support import (
    create_tasks,
    find_task,
    installed_records,
    make_installed_record,
    make_plan,
    make_sim_service,
    mark_complete,
    wait_post_process,
)


def test_restart_recovers_gid_and_finishes_install(tmp_path, monkeypatch):
    """重启后 aria2 换了 gid：刷新按路径认领，下载完成后自动安装。"""

    async def scenario():
        sim1 = await make_sim_service(tmp_path, monkeypatch, initial_status="active")
        tasks1 = await create_tasks(sim1.service, make_plan(sim1.service, sim1.downloads))
        task_id = tasks1[0].task_id
        local_path = tasks1[0].local_path
        assert Path(local_path).is_file()

        # 模拟插件重启：同一个 state 目录重新构造服务（aria2 会话由新进程接管）。
        sim2 = await make_sim_service(tmp_path, monkeypatch, initial_status="active")
        service = sim2.service
        task = find_task(service, task_id)
        assert task.status == "waiting"
        assert len(service.store.tasks) == 1

        sim2.aria2.inject_download(
            "gid-after-restart",
            local_path,
            status="active",
            total=100,
            completed=35,
        )
        await service.refresh_tasks(sync_aria2=True)
        assert task.gid == "gid-after-restart"
        assert task.status == "active"
        assert task.progress == 35.0

        sim2.aria2.set_download_status("gid-after-restart", "complete")
        await service.refresh_tasks(sync_aria2=True)
        assert task.status == "complete"
        await wait_post_process(service)

        assert task.post_processed is True
        assert task.install_status == "installed"
        records = installed_records(service)
        assert len(records) == 1
        assert (Path(records[0].install_path) / "bin" / "Demo.exe").is_file()
        assert len(sim2.stubs.shortcut_calls) == 1

    asyncio.run(scenario())


def test_restart_group_waits_for_all_parts_then_installs_once(tmp_path, monkeypatch):
    """重启时组内一半完成一半在跑：等第二个分卷完成，只安装/注册一次。"""

    async def scenario():
        sim1 = await make_sim_service(tmp_path, monkeypatch, initial_status="active")
        plan = make_plan(sim1.service, sim1.downloads, files=2, game_title="GroupGame")
        tasks1 = await create_tasks(sim1.service, plan)
        paths = [task.local_path for task in tasks1]
        task_ids = [task.task_id for task in tasks1]

        sim2 = await make_sim_service(tmp_path, monkeypatch, initial_status="active")
        service = sim2.service
        first, second = (find_task(service, task_id) for task_id in task_ids)

        # 重启后 aria2 里：第一个已下完，第二个还在跑。
        sim2.aria2.inject_download("gid-part-1", paths[0], status="complete", total=100, completed=100)
        sim2.aria2.inject_download("gid-part-2", paths[1], status="active", total=100, completed=20)
        await service.refresh_tasks(sync_aria2=True)
        assert first.status == "complete"
        assert second.status == "active"
        await asyncio.sleep(0.05)
        assert installed_records(service) == []

        sim2.aria2.set_download_status("gid-part-2", "complete")
        await service.refresh_tasks(sync_aria2=True)
        await wait_post_process(service)

        assert first.post_processed is True
        assert second.post_processed is True
        assert first.install_status == "installed"
        assert second.install_status == "installed"
        records = installed_records(service)
        assert len(records) == 1
        assert len(sim2.seven_zip.extracted) == 2
        assert len(sim2.stubs.shortcut_calls) == 1

    asyncio.run(scenario())


def test_restart_migrates_legacy_cloud_backups(tmp_path, monkeypatch):
    """重启后的后台维护会把存档树里的旧 .freedeckcy-bak-* 迁到中央备份目录。"""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    save_root = home / ".local" / "share" / "ppsspp" / "PSP" / "SAVEDATA"
    title_dir = save_root / "ULUS99999"
    title_dir.mkdir(parents=True)
    (title_dir / "DATA.BIN").write_bytes(b"current")
    legacy_file = title_dir / "DATA.BIN.freedeckcy-bak-20260101_000000"
    legacy_file.write_bytes(b"old")
    legacy_dir = save_root / "old.freedeckcy-bak-dir"
    legacy_dir.mkdir()
    (legacy_dir / "x.bin").write_bytes(b"x")

    async def scenario():
        sim1 = await make_sim_service(tmp_path, monkeypatch)
        record = make_installed_record(
            game_id="psp-1",
            game_title="PSP Demo",
            install_path=str(tmp_path / "installed" / "psp-1"),
            platform="psp",
        )
        Path(record.install_path).mkdir(parents=True, exist_ok=True)
        sim1.service.store.installed_games.append(record)
        sim1.service.store.save()

        sim2 = await make_sim_service(tmp_path, monkeypatch)
        tick = await sim2.service.maintenance_tick()
        assert tick["legacy_backups_migrated"] >= 2

        legacy_root = Path(config.DECKY_SEND_DIR) / "backups" / "legacy"
        moved = list(legacy_root.iterdir())
        assert len(moved) == 2
        assert not legacy_file.exists()
        assert not legacy_dir.exists()
        # 当前存档不受影响。
        assert (title_dir / "DATA.BIN").read_bytes() == b"current"

    asyncio.run(scenario())


def test_concurrent_start_install_reuses_active_download(tmp_path, monkeypatch):
    """双入口同时点安装：第二次复用正在下载的任务，不重复 addUri。"""

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch, initial_status="active")
        service = sim.service
        plan = make_plan(service, sim.downloads)

        async def _fake_plan(**_kwargs):
            return plan

        monkeypatch.setattr(service, "_build_install_plan", _fake_plan)

        first, second = await asyncio.gather(
            service.start_install(),
            service.start_install(),
        )
        assert sim.aria2.add_calls == 1
        assert len(service.store.tasks) == 1
        assert second.get("reused") is True
        task_ids = {row["task_id"] for row in second["tasks"]}
        assert task_ids == {service.store.tasks[0].task_id}
        assert first.get("reused") is not True

    asyncio.run(scenario())


def test_concurrent_post_process_installs_and_registers_once(tmp_path, monkeypatch):
    """同一个完成任务被两个入口同时触发：只解压一次、只写一条记录、只注册一次。"""

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch)
        service = sim.service
        tasks = await create_tasks(service, make_plan(service, sim.downloads))
        task = tasks[0]
        mark_complete(service, task)

        await asyncio.gather(
            service._run_post_process_task(task.task_id),
            service._run_post_process_task(task.task_id),
        )

        assert task.install_status == "installed"
        assert len(installed_records(service)) == 1
        assert len(sim.seven_zip.extracted) == 1
        assert len(sim.stubs.shortcut_calls) == 1

    asyncio.run(scenario())


def test_uninstall_waits_for_inflight_install(tmp_path, monkeypatch):
    """安装收尾持锁期间点卸载：卸载必须等安装完成后再删，不能交错。"""

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch)
        service = sim.service
        plan = make_plan(service, sim.downloads)

        # 先完整安装一次，生成已安装记录。
        first_tasks = await create_tasks(service, plan)
        mark_complete(service, first_tasks[0])
        await service._run_post_process_task(first_tasks[0].task_id)
        assert len(installed_records(service)) == 1
        install_path = Path(installed_records(service)[0].install_path)

        # 再准备一个同游戏的完成任务，并把安装解压卡住，模拟“正在收尾”。
        second_tasks = await create_tasks(service, plan)
        second = second_tasks[0]
        mark_complete(service, second)

        events: list[str] = []
        started = asyncio.Event()
        release = asyncio.Event()
        original_install_payload = service._install_payload

        async def _gated_install(task, target_dir, *, bundle_index=None):
            events.append("install_start")
            started.set()
            await release.wait()
            result = await original_install_payload(task, target_dir, bundle_index=bundle_index)
            events.append("install_done")
            return result

        monkeypatch.setattr(service, "_install_payload", _gated_install)

        install_task = asyncio.create_task(service._run_post_process_task(second.task_id))
        await asyncio.wait_for(started.wait(), timeout=5)

        uninstall_task = asyncio.create_task(
            service.uninstall_installed_game(game_id="game-sim")
        )
        await asyncio.sleep(0.1)
        assert not uninstall_task.done(), "卸载没有等待安装锁"
        assert sim.seven_zip.extracted == [first_tasks[0].local_path], "安装不应在持锁期间被打断"
        assert install_path.is_dir()

        release.set()
        await asyncio.wait_for(install_task, timeout=10)
        result = await asyncio.wait_for(uninstall_task, timeout=10)
        events.append("uninstall_done")

        assert events == ["install_start", "install_done", "uninstall_done"]
        assert result["removed"] is True
        assert installed_records(service) == []
        assert not install_path.exists()

    asyncio.run(scenario())


def test_maintenance_tick_overlap_returns_busy(tmp_path, monkeypatch):
    """两个后台维护入口同时触发：第二个直接跳过，不并发同步 aria2。"""

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch)
        service = sim.service
        entered = asyncio.Event()
        release = asyncio.Event()
        original_refresh = service.refresh_tasks

        async def _gated_refresh(*args, **kwargs):
            entered.set()
            await release.wait()
            return await original_refresh(*args, **kwargs)

        monkeypatch.setattr(service, "refresh_tasks", _gated_refresh)

        first = asyncio.create_task(service.maintenance_tick())
        await asyncio.wait_for(entered.wait(), timeout=5)
        second = await service.maintenance_tick()
        assert second == {"ok": True, "skipped": "busy"}

        release.set()
        result = await asyncio.wait_for(first, timeout=10)
        assert result["ok"] is True
        assert "skipped" not in result

    asyncio.run(scenario())
