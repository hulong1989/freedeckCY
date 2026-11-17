"""云存档端到端全模拟：PSP / PS3 / 3DS 上传 → 恢复。

链路完全离线：
- 真实 ``TianyiService`` + 真实 ``emulator_saves`` 存档发现；
- ``FakeSevenZip`` 打包/解包（归档内保留目录层 + manifest.json）；
- ``FakeCloud`` 模拟天翼云盘的上传 / 版本列表 / 下载；
- 恢复写盘、覆盖前备份、游玩时长合并都走真实代码。

同时覆盖旧 manifest（无 entries / 无 archive_rel_path）、旧备份迁移、备份保留策略。
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import time
import zipfile
from pathlib import Path

import pytest

import config
from tests.sim.fakes import FakeCloud, build_param_sfo, write_3ds_rom, write_zip_archive
from tests.sim.support import (
    make_installed_record,
    make_sim_service,
    patch_cloud,
    patch_login,
    run_cloud_upload,
)


# ---------------------------------------------------------------------------
# 场景搭建
# ---------------------------------------------------------------------------


def _psp_save(home: Path) -> Path:
    path = home / ".local" / "share" / "ppsspp" / "PSP" / "SAVEDATA" / "ULUS12345" / "DATA.BIN"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"psp-v1")
    # 同目录另一个游戏的存档：恢复时不能被误删。
    other = path.parent.parent / "ULUS00002" / "DATA.BIN"
    other.parent.mkdir(parents=True)
    other.write_bytes(b"other-title")
    return path


def _ps3_save(home: Path) -> Path:
    title_dir = (
        home / ".config" / "rpcs3" / "dev_hdd0" / "home" / "00000001" / "savedata" / "BLUS12345"
    )
    title_dir.mkdir(parents=True)
    (title_dir / "PARAM.SFO").write_bytes(build_param_sfo("PS3 Demo"))
    data = title_dir / "DATA.BIN"
    data.write_bytes(b"ps3-v1")
    return data


def _3ds_save(home: Path, tmp_path: Path) -> tuple[Path, Path]:
    rom = tmp_path / "installed" / "3ds" / "Demo.3ds"
    rom.parent.mkdir(parents=True, exist_ok=True)
    write_3ds_rom(rom, "0004000000033600")
    save = (
        home
        / ".local"
        / "share"
        / "azahar"
        / "sdmc"
        / "Nintendo 3DS"
        / "id0"
        / "id1"
        / "title"
        / "00040000"
        / "00033600"
        / "data"
        / "00000001.sav"
    )
    save.parent.mkdir(parents=True)
    save.write_bytes(b"3ds-v1")
    return rom, save


def _add_records(service, tmp_path: Path, records) -> None:
    for record in records:
        Path(record.install_path).mkdir(parents=True, exist_ok=True)
        service.store.installed_games.append(record)
    service.store.save()


def _manifest_from_cloud(cloud: FakeCloud, game_key: str) -> tuple[dict, list[str]]:
    version = cloud.versions(game_key)[0]
    data = cloud.files[game_key][version]
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
    return manifest, names


def _backup_files(service) -> list[Path]:
    root = Path(config.DECKY_SEND_DIR) / "backups"
    if not root.is_dir():
        return []
    return [path for path in root.rglob("*") if path.is_file()]


def _write_cloud_archive(cloud: FakeCloud, game_key: str, version: str, entries: dict) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    cloud.add_archive([game_key], version, buffer.getvalue())


# ---------------------------------------------------------------------------
# 上传 → 恢复 主链路
# ---------------------------------------------------------------------------


def test_psp_ps3_3ds_upload_then_restore_roundtrip(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    psp_save = _psp_save(home)
    ps3_save = _ps3_save(home)
    rom, save_3ds = _3ds_save(home, tmp_path)

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch)
        service = sim.service
        records = [
            make_installed_record(
                game_id="psp-1",
                game_title="PSP Demo",
                install_path=str(tmp_path / "installed" / "psp"),
                platform="psp",
                playtime_seconds=120,
            ),
            make_installed_record(
                game_id="ps3-1",
                game_title="PS3 Demo",
                install_path=str(tmp_path / "installed" / "ps3"),
                platform="ps3",
                playtime_seconds=60,
            ),
            make_installed_record(
                game_id="3ds-1",
                game_title="3DS Demo",
                install_path=str(tmp_path / "installed" / "3ds"),
                platform="3ds",
                rom_path=str(rom),
                playtime_seconds=30,
            ),
        ]
        _add_records(service, tmp_path, records)

        cloud = FakeCloud()
        patch_cloud(monkeypatch, cloud)
        state = await run_cloud_upload(service)
        assert state["stage"] == "completed"
        assert (state["uploaded"], state["failed"], state["skipped"]) == (3, 0, 0)

        # 归档里必须带目录层 + manifest，且 manifest 记录了 emulator 策略与游玩时长。
        for record in records:
            assert cloud.versions(record.game_id), f"{record.game_id} 没有上传版本"
            manifest, names = _manifest_from_cloud(cloud, record.game_id)
            assert manifest["manifest_version"] == 2
            assert manifest["source_strategy"] == "emulator_saves"
            assert manifest["entries"]
            assert manifest["playtime"]["seconds"] > 0
            assert "manifest.json" in names

        # 上传后本地存档被新内容覆盖（模拟另一台设备/新进度）。
        for path in (psp_save, ps3_save, save_3ds):
            path.write_bytes(b"local-v2")

        await patch_login(monkeypatch, service)

        # PSP：先验证“不确认 → 取消且不写盘”，再确认恢复。
        version = cloud.versions("psp-1")[0]
        plan = await service.plan_cloud_save_restore(
            game_id="psp-1",
            game_key="psp-1",
            game_title="PSP Demo",
            version_name=version,
            selected_entry_ids=[],
        )
        assert plan["accepted"] is True
        assert plan["requires_confirmation"] is True
        assert plan["conflict_count"] >= 1
        assert plan["restorable_files"] >= 1

        cancelled = await service.apply_cloud_save_restore(
            plan_id=plan["plan_id"], confirm_overwrite=False
        )
        assert cancelled["status"] == "cancelled"
        assert psp_save.read_bytes() == b"local-v2"

        plan = await service.plan_cloud_save_restore(
            game_id="psp-1",
            game_key="psp-1",
            game_title="PSP Demo",
            version_name=version,
            selected_entry_ids=[],
        )
        result = await service.apply_cloud_save_restore(
            plan_id=plan["plan_id"], confirm_overwrite=True
        )
        assert result["status"] == "success"
        assert result["restored_files"] >= 1
        assert psp_save.read_bytes() == b"psp-v1"
        # 覆盖前备份：旧内容（local-v2）必须能在备份目录找到。
        backup_files = _backup_files(service)
        assert any(path.read_bytes() == b"local-v2" for path in backup_files)
        # 同目录其它游戏的存档不受影响。
        assert (psp_save.parent.parent / "ULUS00002" / "DATA.BIN").read_bytes() == b"other-title"
        # 游玩时长从 manifest 合并回本地记录。
        psp_record = next(item for item in service.store.installed_games if item.game_id == "psp-1")
        assert psp_record.playtime_seconds == 120

        # PS3 / 3DS 直接确认恢复，验证目录层（savedata/<TITLEID>、title/<hi>/<lo>/data）。
        for record, target, expected, version_name in (
            (records[1], ps3_save, b"ps3-v1", cloud.versions("ps3-1")[0]),
            (records[2], save_3ds, b"3ds-v1", cloud.versions("3ds-1")[0]),
        ):
            plan = await service.plan_cloud_save_restore(
                game_id=record.game_id,
                game_key=record.game_id,
                game_title=record.game_title,
                version_name=version_name,
                selected_entry_ids=[],
            )
            assert plan["accepted"] is True, plan
            result = await service.apply_cloud_save_restore(
                plan_id=plan["plan_id"], confirm_overwrite=True
            )
            assert result["status"] == "success", result
            assert target.read_bytes() == expected

        assert (ps3_save.parent / "PARAM.SFO").is_file()
        merged = {item.game_id: item.playtime_seconds for item in service.store.installed_games}
        assert merged["ps3-1"] == 60
        assert merged["3ds-1"] == 30

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# 旧 manifest 兼容
# ---------------------------------------------------------------------------


def test_restore_legacy_manifest_with_source_paths_only(tmp_path, monkeypatch):
    """最老的 manifest：只有 source_paths，没有 entries（靠归档根目录兜底）。"""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    psp_save = _psp_save(home)
    psp_save.write_bytes(b"local-current")

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch)
        service = sim.service
        record = make_installed_record(
            game_id="psp-1",
            game_title="PSP Demo",
            install_path=str(tmp_path / "installed" / "psp"),
            platform="psp",
        )
        _add_records(service, tmp_path, [record])
        cloud = FakeCloud()
        patch_cloud(monkeypatch, cloud)
        _write_cloud_archive(
            cloud,
            "psp-1",
            "20260101_000000.7z",
            {
                "ULUS00001/DATA.BIN": b"legacy-save",
                "manifest.json": json.dumps(
                    {
                        # 旧格式：没有 entries / manifest_version / source_strategy 仅保留策略
                        "source_paths": ["/home/deck/.local/share/ppsspp/PSP/SAVEDATA/ULUS00001"],
                        "source_strategy": "emulator_saves",
                        "game_title": "PSP Demo",
                    }
                ),
            },
        )
        await patch_login(monkeypatch, service)

        plan = await service.plan_cloud_save_restore(
            game_id="psp-1",
            game_key="psp-1",
            game_title="PSP Demo",
            version_name="20260101_000000.7z",
            selected_entry_ids=[],
        )
        assert plan["accepted"] is True, plan
        result = await service.apply_cloud_save_restore(
            plan_id=plan["plan_id"], confirm_overwrite=True
        )
        assert result["status"] == "success"
        restored = psp_save.parent.parent / "ULUS00001" / "DATA.BIN"
        assert restored.read_bytes() == b"legacy-save"

    asyncio.run(scenario())


def test_restore_legacy_manifest_entries_without_rel_path(tmp_path, monkeypatch):
    """旧 manifest entries 只有 name：用条目名回退定位归档目录。"""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    psp_save = _psp_save(home)

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch)
        service = sim.service
        record = make_installed_record(
            game_id="psp-1",
            game_title="PSP Demo",
            install_path=str(tmp_path / "installed" / "psp"),
            platform="psp",
        )
        _add_records(service, tmp_path, [record])
        cloud = FakeCloud()
        patch_cloud(monkeypatch, cloud)
        _write_cloud_archive(
            cloud,
            "psp-1",
            "20260102_000000.7z",
            {
                "TITLELEGACY/DATA.BIN": b"legacy-entry-save",
                "manifest.json": json.dumps(
                    {
                        "source_strategy": "emulator_saves",
                        "entries": [{"entry_id": "e1", "name": "TITLELEGACY"}],
                    }
                ),
            },
        )
        await patch_login(monkeypatch, service)

        plan = await service.plan_cloud_save_restore(
            game_id="psp-1",
            game_key="psp-1",
            game_title="PSP Demo",
            version_name="20260102_000000.7z",
            selected_entry_ids=[],
        )
        assert plan["accepted"] is True, plan
        result = await service.apply_cloud_save_restore(
            plan_id=plan["plan_id"], confirm_overwrite=True
        )
        assert result["status"] == "success"
        assert (psp_save.parent.parent / "TITLELEGACY" / "DATA.BIN").read_bytes() == b"legacy-entry-save"

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# 备份迁移 / 保留策略
# ---------------------------------------------------------------------------


def test_legacy_backup_migration_and_backup_prune(tmp_path, monkeypatch):
    """旧 .freedeckcy-bak-* 迁到中央目录；恢复备份超过 10 份时自动裁剪。"""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    psp_save = _psp_save(home)
    title_dir = psp_save.parent
    legacy_file = title_dir / "DATA.BIN.freedeckcy-bak-20260101_000000"
    legacy_file.write_bytes(b"very-old")
    legacy_dir = title_dir / "old.freedeckcy-bak-dir"
    legacy_dir.mkdir()
    (legacy_dir / "junk.bin").write_bytes(b"junk")

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch)
        service = sim.service
        record = make_installed_record(
            game_id="psp-1",
            game_title="PSP Demo",
            install_path=str(tmp_path / "installed" / "psp"),
            platform="psp",
        )
        _add_records(service, tmp_path, [record])

        tick = await service.maintenance_tick()
        assert tick["legacy_backups_migrated"] >= 2
        legacy_root = Path(config.DECKY_SEND_DIR) / "backups" / "legacy"
        assert legacy_root.is_dir()
        assert len(list(legacy_root.iterdir())) >= 2
        assert not legacy_file.exists()
        assert not legacy_dir.exists()
        assert psp_save.read_bytes() == b"psp-v1"

        # 上传一份云存档，并制造 12 份历史备份。
        cloud = FakeCloud()
        patch_cloud(monkeypatch, cloud)
        state = await run_cloud_upload(service)
        assert state["uploaded"] == 1
        backups_root = Path(config.DECKY_SEND_DIR) / "backups"
        for index in range(12):
            old = backups_root / f"cloud-save-2026010{index % 10}_{index:02d}"
            old.mkdir(parents=True, exist_ok=True)
            (old / "f.bin").write_bytes(b"x")
        for index, old in enumerate(sorted(backups_root.glob("cloud-save-*"))):
            os.utime(old, (time.time() - 1000 + index, time.time() - 1000 + index))

        await patch_login(monkeypatch, service)
        version = cloud.versions("psp-1")[0]
        psp_save.write_bytes(b"local-before-restore")
        plan = await service.plan_cloud_save_restore(
            game_id="psp-1",
            game_key="psp-1",
            game_title="PSP Demo",
            version_name=version,
            selected_entry_ids=[],
        )
        result = await service.apply_cloud_save_restore(
            plan_id=plan["plan_id"], confirm_overwrite=True
        )
        assert result["status"] == "success"
        assert psp_save.read_bytes() == b"psp-v1"
        remaining = list(backups_root.glob("cloud-save-*"))
        assert len(remaining) <= 10
        assert legacy_root.is_dir(), "裁剪备份时不能删掉 legacy 迁移目录"

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# 上传失败 / 跳过
# ---------------------------------------------------------------------------


def test_upload_failures_and_unchanged_skip(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    psp_save = _psp_save(home)

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch)
        service = sim.service
        record = make_installed_record(
            game_id="psp-1",
            game_title="PSP Demo",
            install_path=str(tmp_path / "installed" / "psp"),
            platform="psp",
        )
        _add_records(service, tmp_path, [record])
        cloud = FakeCloud()
        patch_cloud(monkeypatch, cloud)

        # 1) 云盘上传失败：单游戏 failed / upload_failed，任务整体 partial_failed。
        cloud.fail_upload = True
        state = await run_cloud_upload(service)
        assert state["stage"] == "failed"
        assert state["reason"] == "partial_failed"
        assert state["failed"] == 1
        assert state["results"][0]["reason"] == "upload_failed"

        # 2) 打包失败（7z create 抛 SevenZipError）：package_failed。
        cloud.fail_upload = False
        sim.seven_zip.fail_create = True
        state = await run_cloud_upload(service)
        assert state["stage"] == "failed"
        assert state["results"][0]["reason"] == "package_failed"

        # 3) 恢复正常：上传成功。
        sim.seven_zip.fail_create = False
        state = await run_cloud_upload(service)
        assert state["stage"] == "completed"
        assert state["uploaded"] == 1

        # 4) 存档没变化：第二次自动跳过（指纹去重）。
        state = await run_cloud_upload(service)
        assert state["stage"] == "completed"
        assert state["uploaded"] == 0
        assert state["skipped"] == 1
        assert state["results"][0]["reason"] == "unchanged"

        # 5) 存档变化：重新上传。
        psp_save.write_bytes(b"psp-v3")
        state = await run_cloud_upload(service)
        assert state["uploaded"] == 1
        assert state["skipped"] == 0
        # 失败/成功上传分别调用过 upload；同秒内版本名可能相同，按调用次数断言更稳。
        assert len(cloud.upload_calls) == 3
        assert cloud.versions("psp-1")

    asyncio.run(scenario())


def test_upload_without_candidates_completes_cleanly(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch)
        service = sim.service
        cloud = FakeCloud()
        patch_cloud(monkeypatch, cloud)
        state = await run_cloud_upload(service)
        assert state["stage"] == "completed"
        assert state["uploaded"] == 0
        assert state["total_games"] == 0
        assert "成功 0" in state["message"]
        assert cloud.upload_calls == []

    asyncio.run(scenario())


def test_cloud_download_failure_marks_restore_failed(tmp_path, monkeypatch):
    """下载云版本失败：恢复计划失败并复位状态，不写本机存档。"""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    psp_save = _psp_save(home)

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch)
        service = sim.service
        record = make_installed_record(
            game_id="psp-1",
            game_title="PSP Demo",
            install_path=str(tmp_path / "installed" / "psp"),
            platform="psp",
        )
        _add_records(service, tmp_path, [record])
        cloud = FakeCloud()
        patch_cloud(monkeypatch, cloud)
        state = await run_cloud_upload(service)
        assert state["uploaded"] == 1
        version = cloud.versions("psp-1")[0]
        await patch_login(monkeypatch, service)

        psp_save.write_bytes(b"local-before-failure")
        cloud.fail_download = True
        with pytest.raises(Exception):
            await service.plan_cloud_save_restore(
                game_id="psp-1",
                game_key="psp-1",
                game_title="PSP Demo",
                version_name=version,
                selected_entry_ids=[],
            )
        restore_state = (await service.get_cloud_save_restore_status())["state"]
        assert restore_state["stage"] == "failed"
        assert psp_save.read_bytes() == b"local-before-failure"

    asyncio.run(scenario())


def test_restore_version_list_groups_uploaded_versions(tmp_path, monkeypatch):
    """上传后 /restore/list 能看到带时间戳的版本（UI 恢复入口的数据源）。"""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    _psp_save(home)

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch)
        service = sim.service
        record = make_installed_record(
            game_id="psp-1",
            game_title="PSP Demo",
            install_path=str(tmp_path / "installed" / "psp"),
            platform="psp",
        )
        _add_records(service, tmp_path, [record])
        cloud = FakeCloud()
        patch_cloud(monkeypatch, cloud)
        assert (await run_cloud_upload(service))["uploaded"] == 1
        await patch_login(monkeypatch, service)

        options = await service.list_cloud_save_restore_options()
        assert options["updated_at"] > 0
        games = options["games"]
        assert len(games) == 1
        game = games[0]
        assert game["game_id"] == "psp-1"
        assert game["available"] is True
        assert len(game["versions"]) == 1
        version = game["versions"][0]
        assert version["version_name"].endswith(".7z")
        assert version["timestamp"] > 0
        assert version["display_time"]
        assert version["file_id"]

    asyncio.run(scenario())


def test_restore_requires_installed_record(tmp_path, monkeypatch):
    """删除安装记录后再恢复：计划失败并给出明确原因（不落盘）。"""
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    _psp_save(home)

    async def scenario():
        sim = await make_sim_service(tmp_path, monkeypatch)
        service = sim.service
        record = make_installed_record(
            game_id="psp-1",
            game_title="PSP Demo",
            install_path=str(tmp_path / "installed" / "psp"),
            platform="psp",
        )
        _add_records(service, tmp_path, [record])
        cloud = FakeCloud()
        patch_cloud(monkeypatch, cloud)
        assert (await run_cloud_upload(service))["uploaded"] == 1
        version = cloud.versions("psp-1")[0]

        # 模拟游戏已被卸载：记录不存在。
        service.store.installed_games = []
        service.store.save()
        await patch_login(monkeypatch, service)

        with pytest.raises(Exception, match="安装记录"):
            await service.plan_cloud_save_restore(
                game_id="psp-1",
                game_key="psp-1",
                game_title="PSP Demo",
                version_name=version,
                selected_entry_ids=[],
            )
        restore_state = (await service.get_cloud_save_restore_status())["state"]
        assert restore_state["stage"] == "failed"
        assert restore_state["reason"] == "plan_failed"

    asyncio.run(scenario())
