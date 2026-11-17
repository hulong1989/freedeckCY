"""FakeSevenZip 故障与分卷语义：损坏包、分卷、排除规则。

覆盖真实链路里的四类问题：
- 下载到损坏/半截包：``7z t`` 失败后应隔离坏文件并自动重下一次；
- 多分卷归档：只解主卷，其余标记 bundled，缺分卷整组失败；
- zip 分卷（.z01 + .zip）缺入口文件：不能把分卷当独立压缩包安装；
- 云存档打包排除规则：``.freedeckcy-bak-*`` 不能被打进上传包。
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

import tianyi_service as svc_module
from seven_zip_manager import SevenZipError
from tests.sim.fakes import FakeSevenZip, corrupt_archive, write_zip_archive
from tests.sim.support import (
    create_tasks,
    installed_records,
    make_plan,
    make_sim_service,
    mark_complete,
    run_post_process,
    volume_payload,
)


def _demo_zip(path: str, _out_name: str) -> None:
    write_zip_archive(
        path,
        {
            "DemoGame/bin/Demo.exe": b"MZ fake",
            "DemoGame/readme.txt": "hello",
        },
    )


def test_corrupt_archive_triggers_repair_and_reinstall(tmp_path, monkeypatch):
    """7z 校验失败 → 隔离坏文件 → 自动重下一次 → 第二次安装成功。"""

    attempts = {"count": 0}

    def _flaky_payload(path: str, out_name: str) -> None:
        attempts["count"] += 1
        if attempts["count"] == 1:
            _demo_zip(path, out_name)
            corrupt_archive(path, keep_bytes=20)
        else:
            _demo_zip(path, out_name)

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch, payload_builder=_flaky_payload)
        service = sim.service
        tasks = await create_tasks(service, make_plan(service, sim.downloads))
        task = tasks[0]
        mark_complete(service, task)

        await run_post_process(service, task)
        assert attempts["count"] == 2  # 第一次坏包 + 自动重下
        assert task.post_processed is False, "重下中的任务不能被标记已处理"
        assert task.install_status == "waiting"
        assert "重新下载" in task.install_message
        assert len(list(Path(task.download_dir).glob("*freedeckcy-archive-invalid-*"))) == 1
        assert installed_records(service) == []

        # 重下完成（假 aria2 第二次写的是好包）：再跑一次安装。
        mark_complete(service, task)
        await run_post_process(service, task)
        assert task.install_status == "installed"
        assert len(installed_records(service)) == 1
        assert (Path(task.installed_path) / "bin" / "Demo.exe").is_file()
        assert len(sim.seven_zip.extracted) == 1

    asyncio.run(scenario())


def test_corrupt_archive_without_retry_marks_failed(tmp_path, monkeypatch):
    """坏包且无法重新取链：任务标 failed 并保留具体原因，不能进入安装。"""

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch)
        service = sim.service
        sim.seven_zip.fail_test_archive = True
        sim.seven_zip.test_reason = "7z t: CRC 校验失败"

        tasks = await create_tasks(service, make_plan(service, sim.downloads))
        task = tasks[0]
        mark_complete(service, task)

        async def _fail_url(*_args, **_kwargs):
            raise RuntimeError("fake direct url expired")

        monkeypatch.setattr(svc_module, "fetch_download_url", _fail_url)
        await run_post_process(service, task)

        assert task.post_processed is True
        assert task.install_status == "failed"
        assert "CRC 校验失败" in task.install_message
        assert installed_records(service) == []
        assert len(list(Path(task.download_dir).glob("*freedeckcy-archive-invalid-*"))) == 1

    asyncio.run(scenario())


def test_seven_zip_error_during_extract_marks_failed(tmp_path, monkeypatch):
    """解压阶段抛 SevenZipError：任务失败并带 7z 原始错误信息。"""

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch)
        service = sim.service
        sim.seven_zip.extract_error = SevenZipError("7z: cannot open archive")
        tasks = await create_tasks(service, make_plan(service, sim.downloads))
        task = tasks[0]
        mark_complete(service, task)
        await run_post_process(service, task)

        assert task.post_processed is True
        assert task.install_status == "failed"
        assert "cannot open archive" in task.install_message
        assert installed_records(service) == []

    asyncio.run(scenario())


def test_multi_volume_extracts_only_entry_volume(tmp_path, monkeypatch):
    """game.7z.001/.002：只解主卷，.002 标记 bundled，Steam 只注册一次。"""

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch, payload_builder=volume_payload)
        service = sim.service
        plan = make_plan(
            service,
            sim.downloads,
            files=[("VolGame.7z.001", 0), ("VolGame.7z.002", 0)],
            openpath="VolGame/bin/Vol.exe",
            game_title="VolGame",
        )
        first, second = await create_tasks(service, plan)
        # 组内 lead 按 created_at 排序：固定主卷在前，确保 bundled 语义可断言。
        first.created_at = 100
        second.created_at = 200
        mark_complete(service, first)
        mark_complete(service, second)

        await run_post_process(service, first)

        assert first.install_status == "installed"
        assert second.install_status == "bundled"
        assert "由主卷统一解压" in second.install_message
        assert sim.seven_zip.extracted == [first.local_path]
        records = installed_records(service)
        assert len(records) == 1
        assert (Path(records[0].install_path) / "bin" / "Vol.exe").is_file()
        assert len(sim.stubs.shortcut_calls) == 1

    asyncio.run(scenario())


def test_missing_volume_part_fails_without_install(tmp_path, monkeypatch):
    """只有 game.7z.001、缺 .002：整组失败并列出缺失分卷，不安装。"""

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch, payload_builder=volume_payload)
        service = sim.service
        plan = make_plan(
            service,
            sim.downloads,
            files=[("Broken.7z.001", 0)],
            openpath="Broken/bin/Broken.exe",
            game_title="Broken",
        )
        task = (await create_tasks(service, plan))[0]
        mark_complete(service, task)

        await run_post_process(service, task)

        assert task.post_processed is True
        assert task.install_status == "failed"
        assert "分卷不完整" in task.install_message
        assert "Broken.7z.002" in task.install_message
        assert installed_records(service) == []
        assert sim.seven_zip.extracted == []

    asyncio.run(scenario())


def test_zip_spanned_missing_entry_volume_fails_group(tmp_path, monkeypatch):
    """Spanned.z01/.z02 缺 Spanned.zip 入口卷：两个分卷都判失败，不注册 Steam。"""

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch, payload_builder=volume_payload)
        service = sim.service
        plan = make_plan(
            service,
            sim.downloads,
            files=[("Spanned.z01", 0), ("Spanned.z02", 0)],
            openpath="Spanned/bin/Spanned.exe",
            game_title="Spanned",
        )
        first, second = await create_tasks(service, plan)
        mark_complete(service, first)
        mark_complete(service, second)

        await run_post_process(service, first)

        assert first.install_status == "failed"
        assert second.install_status == "failed"
        messages = first.install_message + second.install_message
        assert "分卷不完整" in messages
        assert "2/2" in messages
        assert installed_records(service) == []
        assert sim.stubs.shortcut_calls == []

    asyncio.run(scenario())


def test_fake_seven_zip_exclusion_rules(tmp_path):
    """FakeSevenZip 的排除规则：备份文件/备份目录都不进包，正常文件保留。"""
    archive = FakeSevenZip()
    save_root = tmp_path / "saves"
    title = save_root / "TITLE01"
    title.mkdir(parents=True)
    (title / "DATA.BIN").write_bytes(b"current")
    (title / "DATA.BIN.freedeckcy-bak-20260101_000000").write_bytes(b"old")
    backup_dir = save_root / "old.freedeckcy-bak-dir"
    backup_dir.mkdir()
    (backup_dir / "junk.bin").write_bytes(b"junk")

    package = tmp_path / "saves.7z"
    archive.create_archive(
        str(package),
        [str(title), str(backup_dir)],
        working_dir=str(save_root),
        excludes=["*.freedeckcy-bak-*"],
    )

    names = archive.archive_entries(str(package))
    assert "TITLE01/DATA.BIN" in names
    assert all("freedeckcy-bak" not in name for name in names)
    assert archive.test_archive(str(package))[0] is True


def test_corrupt_archive_detected_by_fake_seven_zip(tmp_path):
    """损坏的包 ``test_archive`` 返回 (False, 原因)，与真实 ``7z t`` 语义一致。"""
    fake = FakeSevenZip()
    good = write_zip_archive(tmp_path / "good.7z", {"a.txt": b"a"})
    assert fake.test_archive(good) == (True, "")

    bad = write_zip_archive(tmp_path / "bad.7z", {"a.txt": b"a"})
    corrupt_archive(bad)
    ok, reason = fake.test_archive(bad)
    assert ok is False
    assert reason
