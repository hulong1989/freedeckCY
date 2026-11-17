"""FakeAria2 故障注入：gid 丢失、status error、never complete、pause/resume。

这些场景对应真实设备上最常见的下载卡死/重启问题：
- 插件重启或 aria2 进程重启后 gid 全部失效；
- 网盘直链过期后 aria2 报 error；
- 某些直链永远停在 active（0%），既装不上也不报错；
- 用户手动暂停/恢复后状态要能回到任务列表。
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

import tianyi_service as svc_module
from tests.sim.support import (
    create_tasks,
    find_task,
    installed_records,
    make_plan,
    make_sim_service,
    mark_complete,
    wait_post_process,
)


def _task_file(task) -> Path:
    return Path(task.local_path)


def test_gid_lost_recovers_by_file_path(tmp_path, monkeypatch):
    """aria2 重启丢 gid：按落盘路径重新认领新 gid，进度不丢。"""

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch, initial_status="active")
        service = sim.service
        tasks = await create_tasks(service, make_plan(service, sim.downloads))
        task = tasks[0]
        assert task.status == "waiting"

        old_gid = task.gid
        payload = _task_file(task)
        assert payload.is_file()
        # 模拟 aria2 重启：旧 gid 消失，同一个文件以新 gid 继续下载。
        sim.aria2.forget_gid(old_gid)
        sim.aria2.inject_download(
            "gid-restarted",
            payload,
            status="active",
            total=100,
            completed=42,
            speed=1024,
        )

        await service.refresh_tasks(sync_aria2=True)
        assert task.gid == "gid-restarted"
        assert task.status == "active"
        assert task.progress == 42.0
        assert task.speed == 1024
        # 认领成功，不应该触发“重新加下载”。
        assert sim.aria2.add_calls == 1
        assert task.task_id not in service._task_sync_misses

    asyncio.run(scenario())


def test_gid_lost_but_file_already_complete_installs(tmp_path, monkeypatch):
    """gid 丢失但文件已按预期大小落盘：直接判完成并进入安装。"""

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch, initial_status="active")
        service = sim.service
        tasks = await create_tasks(service, make_plan(service, sim.downloads))
        task = tasks[0]
        payload = _task_file(task)
        task.file_size = os.path.getsize(payload)
        service.store.save()

        assert task.status == "waiting"
        sim.aria2.forget_gid(task.gid)
        await service.refresh_tasks(sync_aria2=True)
        assert task.status == "complete"
        assert task.progress == 100.0

        await wait_post_process(service)
        assert task.post_processed is True
        assert task.install_status == "installed"
        assert len(installed_records(service)) == 1
        # 没有重新加下载，也没有删过下载
        assert sim.aria2.add_calls == 1
        assert sim.aria2.removed == []

    asyncio.run(scenario())


def test_gid_lost_readds_download_once(tmp_path, monkeypatch):
    """gid 丢失且半成品不在：自动重新加入下载，每个任务每进程只尝试一次。"""

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch, initial_status="active")
        service = sim.service
        tasks = await create_tasks(service, make_plan(service, sim.downloads))
        task = tasks[0]
        old_gid = task.gid
        _task_file(task).unlink()
        sim.aria2.forget_gid(old_gid)

        await service.refresh_tasks(sync_aria2=True)
        assert task.gid != old_gid
        assert task.gid == "gid-2"
        assert task.status == "waiting"
        assert task.progress == 0.0
        assert service._readd_attempts[task.task_id] == 1
        # 1 次建任务取链 + 1 次重新加入取链
        assert len(sim.stubs.download_url_calls) == 2
        assert [row["gid"] for row in sim.aria2.added] == ["gid-1", "gid-2"]

        # 第二次刷新时 gid-2 正常返回 active，任务继续下载，不再重复取链。
        await service.refresh_tasks(sync_aria2=True)
        assert task.status == "active"
        assert len(sim.stubs.download_url_calls) == 2

    asyncio.run(scenario())


def test_gid_lost_persistent_marks_error_after_threshold(tmp_path, monkeypatch):
    """gid 一直不存在且无法重新取链：连续 5 次后标记 error，而不是无限重试。"""

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch, initial_status="active")
        service = sim.service
        tasks = await create_tasks(service, make_plan(service, sim.downloads))
        task = tasks[0]
        _task_file(task).unlink()
        sim.aria2.forget_gid(task.gid, hide=True)

        async def _fail_url(*_args, **_kwargs):
            raise RuntimeError("fake direct url expired")

        monkeypatch.setattr(svc_module, "fetch_download_url", _fail_url)

        statuses = []
        for _ in range(5):
            await service.refresh_tasks(sync_aria2=True)
            statuses.append(task.status)
        assert statuses[:-1] == ["waiting"] * 4
        assert task.status == "error"
        assert "连续 5 次" in task.error_reason
        # 只尝试过一次重新取链；失败后靠 sync miss 计数收敛。
        assert len([call for call in service._readd_attempts]) == 1
        assert len(service._task_sync_misses) == 1

    asyncio.run(scenario())


def test_aria2_status_error_blocks_group_and_recovers_after_remove(tmp_path, monkeypatch):
    """一个分卷 error：同组 complete 分卷给出提示、不安装；移除失败任务后自动补装。"""

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch, initial_status="active")
        service = sim.service
        plan = make_plan(service, sim.downloads, files=2, game_title="GroupGame")
        tasks = await create_tasks(service, plan)
        first, second = tasks

        sim.aria2.set_download_status(first.gid, "complete")
        sim.aria2.set_download_status(second.gid, "error", error_message="fake network error")
        await service.refresh_tasks(sync_aria2=True)
        # 后台维护（真实链路）会对“complete 但同组有 error”的任务补提示并阻止安装。
        tick = await service.maintenance_tick()
        assert tick["scheduled"] == 0

        assert first.status == "complete"
        assert second.status == "error"
        assert second.error_reason == "fake network error"
        assert "分卷下载失败" in first.install_message
        assert not service._post_process_jobs
        assert installed_records(service) == []

        await service.remove_task(second.task_id)
        service._maybe_schedule_group_post_process(first)
        await wait_post_process(service)

        assert first.post_processed is True
        assert first.install_status == "installed"
        assert len(installed_records(service)) == 1
        assert (Path(first.installed_path) / "bin" / "Demo.exe").is_file()

    asyncio.run(scenario())


def test_never_complete_then_pause_resume_and_finish(tmp_path, monkeypatch):
    """下载永远 active：不误装、不超时；暂停/恢复状态可见，完成后正常安装。"""

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch, initial_status="active")
        service = sim.service
        tasks = await create_tasks(service, make_plan(service, sim.downloads))
        task = tasks[0]
        assert task.status == "waiting"

        # 永远 0%：刷新与后台维护都不应该推进安装。
        await service.refresh_tasks(sync_aria2=True)
        assert task.status == "active"
        assert task.progress == 0.0
        tick = await service.maintenance_tick()
        assert tick["scheduled"] == 0
        assert not service._post_process_jobs
        assert installed_records(service) == []

        # 暂停 → 刷新后状态保持 paused。
        await service.pause_task(task.task_id)
        assert task.status == "paused"
        await service.refresh_tasks(sync_aria2=True)
        assert task.status == "paused"

        # 恢复 → 回到 active。
        await service.resume_task(task.task_id)
        assert task.status == "active"
        await service.refresh_tasks(sync_aria2=True)
        assert task.status == "active"

        # 下载真的完成：刷新后自动调度安装。
        sim.aria2.set_download_status(task.gid, "complete", speed=0)
        await service.refresh_tasks(sync_aria2=True)
        assert task.status == "complete"
        await wait_post_process(service)
        assert task.install_status == "installed"
        assert len(installed_records(service)) == 1

    asyncio.run(scenario())


def test_retry_error_task_with_complete_file_skips_redownload(tmp_path, monkeypatch):
    """error 任务但文件已经完整：retry 直接重装，不再请求直链。"""

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch, initial_status="active")
        service = sim.service
        tasks = await create_tasks(service, make_plan(service, sim.downloads))
        task = tasks[0]
        payload = _task_file(task)
        task.file_size = os.path.getsize(payload)
        service.store.save()
        assert task.status == "waiting"
        sim.aria2.set_download_status(task.gid, "error", error_message="fake io error")
        await service.refresh_tasks(sync_aria2=True)
        assert task.status == "error"

        await service.retry_task(task.task_id)
        assert task.status == "complete"
        assert task.install_status == "pending"
        await wait_post_process(service)
        assert task.install_status == "installed"
        assert len(installed_records(service)) == 1

    asyncio.run(scenario())


def test_lost_gid_uses_changeuri_in_place(tmp_path, monkeypatch):
    """gid 还在时优先原地换链，保留 aria2 进度，不新建下载。"""

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch, initial_status="active")
        service = sim.service
        tasks = await create_tasks(service, make_plan(service, sim.downloads))
        task = tasks[0]
        gid = task.gid
        assert task.status == "waiting"
        # 第一次查询直接报错（模拟直链过期），gid 本身仍在 aria2 会话里。
        sim.aria2.lose_gid_at = 1

        await service.refresh_tasks(sync_aria2=True)
        assert [row[0] for row in sim.aria2.replaced] == [gid]
        assert sim.aria2.add_calls == 1
        assert task.status == "waiting"

    asyncio.run(scenario())
