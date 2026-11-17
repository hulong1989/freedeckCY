"""安装链路全模拟：假 aria2 + 假 7z + 假 Steam，不联网、不执行 Linux 二进制。"""

from __future__ import annotations

import asyncio
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

import config
import tianyi_service as svc_module
from tianyi_service import TianyiService
from tianyi_store import TianyiSettings, TianyiStateStore
from tests.sim.fakes import FakeAria2, FakeSevenZip


class _Plugin:
    def __init__(self, downloads: Path):
        self.downloads_dir = str(downloads)
        self.server_running = False
        self.server_port = 59271

    async def set_download_dir(self, path: str):
        self.downloads_dir = path
        return {"status": "success"}


def _payload_builder(path: str, _out_name: str) -> None:
    archive = Path(path)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("DemoGame/bin/Demo.exe", b"MZ fake")
        zf.writestr("DemoGame/readme.txt", "hello")


@pytest.fixture()
def sim(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path / "state"))
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    service = TianyiService(_Plugin(downloads))
    asyncio.run(service.initialize())
    service.store.set_settings(
        download_dir=str(downloads),
        install_dir=str(tmp_path / "installed"),
        auto_delete_package=True,
    )
    service.store.save()
    service.aria2 = FakeAria2(_payload_builder)
    service.seven_zip = FakeSevenZip()
    shortcuts = []
    shortcut_calls = []

    async def _no_cover(**kwargs):
        return {}

    async def _shortcut(**kwargs):
        shortcut_calls.append(kwargs)
        return {"ok": True, "appid_unsigned": 4242}

    async def _settled(paths, **kwargs):
        return True, ""

    monkeypatch.setattr(service, "resolve_catalog_cover", _no_cover)
    monkeypatch.setattr(svc_module, "add_or_update_tianyi_shortcut", _shortcut)
    monkeypatch.setattr(service, "_wait_payload_settled", _settled)

    async def _token(cookie):
        return "fake-token"

    async def _url(cookie, token, share_id, file_id):
        return f"https://fake.invalid/{file_id}"

    monkeypatch.setattr(svc_module, "fetch_access_token", _token)
    monkeypatch.setattr(svc_module, "fetch_download_url", _url)
    return SimpleNamespace(service=service, downloads=downloads, shortcuts=shortcuts, shortcut_calls=shortcut_calls)


def _plan(service: TianyiService, downloads: Path, files=1):
    return {
        "provider": "tianyi",
        "game_id": "game-sim",
        "game_title": "DemoGame",
        "share_id": "share-sim",
        "share_code": "code-sim",
        "download_dir": str(downloads),
        "install_dir": str(service.store.settings.install_dir),
        "openpath": "DemoGame/bin/Demo.exe",
        "platform": "pc",
        "can_install": True,
        "files": [
            {"file_id": f"f{index}", "name": f"DemoGame-{index}.7z", "size": 100}
            for index in range(files)
        ],
    }


def test_full_install_from_plan_to_installed(sim):
    service = sim.service
    plan = _plan(service, sim.downloads)

    async def scenario():
        tasks = await service._create_tasks_from_plan(plan=plan, split=8)
        service.store.upsert_tasks(tasks)
        assert len(tasks) == 1
        task = tasks[0]
        assert Path(task.local_path).is_file()
        task.status = "complete"
        task.progress = 100.0
        await service._run_post_process_task(task.task_id)
        return task

    task = asyncio.run(scenario())
    assert task.install_status == "installed"
    records = list(service.store.installed_games)
    assert len(records) == 1
    assert records[0].game_id == "game-sim"
    assert records[0].steam_app_id == 4242
    assert Path(records[0].install_path).is_dir()
    assert (Path(records[0].install_path) / "bin" / "Demo.exe").is_file()
    assert sim.shortcut_calls and sim.shortcut_calls[0]["game_id"] == "game-sim"
    assert not Path(task.local_path).exists()  # auto_delete_package


def test_partial_task_creation_rolls_back_aria2(sim):
    service = sim.service
    service.aria2.fail_add_at = 2

    async def scenario():
        with pytest.raises(RuntimeError):
            await service._create_tasks_from_plan(plan=_plan(service, sim.downloads, files=2), split=8)

    asyncio.run(scenario())
    assert len(service.aria2.added) == 1
    assert service.aria2.removed == [service.aria2.added[0]["gid"]]


def test_extract_failure_marks_task_failed_for_manual_retry(sim):
    service = sim.service
    plan = _plan(service, sim.downloads)

    async def scenario():
        tasks = await service._create_tasks_from_plan(plan=plan, split=8)
        service.store.upsert_tasks(tasks)
        task = tasks[0]
        task.status = "complete"
        task.progress = 100.0
        service.seven_zip.fail_extract = True
        await service._run_post_process_task(task.task_id)
        return task

    task = asyncio.run(scenario())
    assert task.post_processed is True
    assert task.install_status == "failed"
    assert "解压异常" in task.install_message


def test_fatal_postprocess_failure_uses_backoff(sim, monkeypatch):
    service = sim.service
    plan = _plan(service, sim.downloads)

    async def scenario():
        tasks = await service._create_tasks_from_plan(plan=plan, split=8)
        service.store.upsert_tasks(tasks)
        task = tasks[0]
        task.status = "complete"
        task.progress = 100.0
        monkeypatch.setattr(service, "_resolve_install_root", lambda: (_ for _ in ()).throw(RuntimeError("root gone")))
        await service._run_post_process_task(task.task_id)
        return task

    task = asyncio.run(scenario())
    assert task.post_processed is False
    assert task.install_status == "failed"
    assert service._post_process_failures
    assert service._post_process_backoff_active(task)


def test_restart_recovers_completed_task_and_installs(sim, monkeypatch):
    service = sim.service
    plan = _plan(service, sim.downloads)

    async def prepare():
        tasks = await service._create_tasks_from_plan(plan=plan, split=8)
        service.store.upsert_tasks(tasks)
        task = tasks[0]
        task.status = "complete"
        task.progress = 100.0
        service.store.save()
        return task.task_id

    task_id = asyncio.run(prepare())

    restarted = TianyiService(_Plugin(sim.downloads))
    asyncio.run(restarted.initialize())
    restarted.aria2 = FakeAria2(_payload_builder)
    restarted.seven_zip = FakeSevenZip()

    async def _no_cover(**kwargs):
        return {}

    async def _shortcut(**kwargs):
        return {"ok": True, "appid_unsigned": 4343}

    async def _settled(paths, **kwargs):
        return True, ""

    monkeypatch.setattr(restarted, "resolve_catalog_cover", _no_cover)
    monkeypatch.setattr(svc_module, "add_or_update_tianyi_shortcut", _shortcut)
    monkeypatch.setattr(restarted, "_wait_payload_settled", _settled)
    monkeypatch.setattr("tianyi_service.add_or_update_tianyi_shortcut", _shortcut)

    asyncio.run(restarted._run_post_process_task(task_id))
    records = list(restarted.store.installed_games)
    assert len(records) == 1
    assert records[0].steam_app_id == 4343
    assert (Path(records[0].install_path) / "bin" / "Demo.exe").is_file()
