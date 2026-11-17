"""tests/sim 共用的全模拟装配工具。

只做三件事：
1. 构造一个真实 ``TianyiService``（catalog/state 都落到 tmp_path，不碰用户目录）；
2. 把 aria2 / 7z / Steam / 网络全部换成 tests/sim/fakes.py 里的替身；
3. 提供建计划、造任务、等后台安装等小工具，避免各测试文件重复样板。
"""

from __future__ import annotations

import asyncio
import os
import time
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Sequence

import config
import tianyi_service as svc_module
from tianyi_service import TianyiService
from tests.sim.fakes import FakeAria2, FakeCloud, FakeSevenZip


# ---------------------------------------------------------------------------
# 插件替身（Decky 侧只需要 downloads_dir / 服务器字段）
# ---------------------------------------------------------------------------


class FakePlugin:
    def __init__(self, downloads_dir: Path, *, port: int = 59271):
        self.downloads_dir = str(downloads_dir)
        self.server_running = False
        self.server_port = int(port)
        self.plugin_dir = str(Path(config.DECKY_SEND_DIR).parent.parent)

    async def set_download_dir(self, path: str) -> Dict[str, Any]:
        self.downloads_dir = path
        return {"status": "success", "path": path}


# ---------------------------------------------------------------------------
# 默认假归档内容
# ---------------------------------------------------------------------------


def demo_payload(path: str, _out_name: str) -> None:
    """默认安装包：``DemoGame/bin/Demo.exe`` + readme。"""
    archive = Path(path)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("DemoGame/bin/Demo.exe", b"MZ fake")
        zf.writestr("DemoGame/readme.txt", "hello")


def volume_payload(path: str, _out_name: str) -> None:
    """分卷主卷内容（假 7z 只用 zipfile，因此任何扩展名都能解压）。"""
    archive = Path(path)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("VolGame/bin/Vol.exe", b"MZ volume")
        zf.writestr("VolGame/data.pak", b"volume payload")


# ---------------------------------------------------------------------------
# 服务装配
# ---------------------------------------------------------------------------


class SimStubs:
    """记录所有替身调用，方便断言“只安装一次/只注册一次”。"""

    def __init__(self) -> None:
        self.shortcut_calls: List[Dict[str, Any]] = []
        self.download_url_calls: List[Dict[str, Any]] = []
        self.cover_calls: List[Dict[str, Any]] = []
        self.appid = 4242


async def make_sim_service(
    tmp_path: Path,
    monkeypatch,
    *,
    payload_builder: Optional[Callable[[str, str], None]] = demo_payload,
    initial_status: str = "complete",
    appid: int = 4242,
    auto_delete_package: bool = False,
    split: int = 8,
    state_name: str = "state",
    downloads_name: str = "Downloads",
    initialize: bool = True,
) -> SimpleNamespace:
    """构造并初始化一个全模拟服务。

    返回 ``SimpleNamespace(service, plugin, downloads, stubs)``。
    后台安装用 ``run_post_process``/``wait_post_process`` 推进。
    """
    state_root = tmp_path / state_name
    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(state_root))
    downloads = tmp_path / downloads_name
    downloads.mkdir(parents=True, exist_ok=True)
    install_dir = tmp_path / "installed"
    install_dir.mkdir(parents=True, exist_ok=True)
    plugin = FakePlugin(downloads)
    service = TianyiService(plugin)
    if initialize:
        await service.initialize()
        service.store.set_settings(
            download_dir=str(downloads),
            install_dir=str(install_dir),
            auto_delete_package=bool(auto_delete_package),
            split_count=int(split),
        )
        # 假登录态：_readd_task_download / start_cloud_save_upload 都要求有 cookie。
        service.store.set_login("UID=sim", "sim-user")
        service.store.save()

    stubs = SimStubs()
    await apply_offline_stubs(monkeypatch, service, stubs=stubs, appid=appid)

    service.aria2 = FakeAria2(payload_builder, initial_status=initial_status)
    service.seven_zip = FakeSevenZip()
    service.plugin = plugin
    return SimpleNamespace(
        service=service,
        plugin=plugin,
        downloads=downloads,
        install_dir=install_dir,
        stubs=stubs,
        aria2=service.aria2,
        seven_zip=service.seven_zip,
    )


async def apply_offline_stubs(
    monkeypatch,
    service: TianyiService,
    *,
    stubs: Optional[SimStubs] = None,
    appid: int = 4242,
    settled: bool = True,
) -> SimStubs:
    """把网络/Steam/封面/收尾等待全部打桩。"""
    stubs = stubs or SimStubs()
    stubs.appid = int(appid)

    async def _no_cover(**kwargs):
        stubs.cover_calls.append(dict(kwargs))
        return {}

    async def _shortcut(**kwargs):
        stubs.shortcut_calls.append(dict(kwargs))
        return {"ok": True, "appid_unsigned": stubs.appid}

    async def _token(_cookie):
        return "fake-token"

    async def _url(_cookie, _token, share_id, file_id):
        stubs.download_url_calls.append(
            {"share_id": share_id, "file_id": file_id}
        )
        return f"https://fake.invalid/{file_id}"

    async def _settled(_paths, **_kwargs):
        return (True, "") if settled else (False, "fake payload not settled")

    monkeypatch.setattr(service, "resolve_catalog_cover", _no_cover)
    monkeypatch.setattr(service, "_wait_payload_settled", _settled)
    monkeypatch.setattr(svc_module, "add_or_update_tianyi_shortcut", _shortcut)
    monkeypatch.setattr(svc_module, "fetch_access_token", _token)
    monkeypatch.setattr(svc_module, "fetch_download_url", _url)
    return stubs


# ---------------------------------------------------------------------------
# 安装计划 / 任务
# ---------------------------------------------------------------------------


def make_plan(
    service: TianyiService,
    downloads: Path,
    *,
    files: Union[int, Sequence[Tuple[str, int]]] = 1,
    openpath: str = "DemoGame/bin/Demo.exe",
    game_id: str = "game-sim",
    game_title: str = "DemoGame",
    platform: str = "pc",
    provider: str = "tianyi",
) -> Dict[str, Any]:
    """构造与 ``_build_install_plan`` 同构的安装计划（跳过真实分享解析）。"""
    if isinstance(files, int):
        file_rows = [
            {"file_id": f"f{index}", "name": f"DemoGame-{index}.7z", "size": 0}
            for index in range(files)
        ]
    else:
        file_rows = [
            {"file_id": f"f{index}", "name": name, "size": int(size)}
            for index, (name, size) in enumerate(files)
        ]
    return {
        "provider": provider,
        "game_id": game_id,
        "game_title": game_title,
        "share_id": "share-sim",
        "share_code": "code-sim",
        "share_url": "https://cloud.189.cn/web/share?code=sim",
        "download_dir": str(downloads),
        "install_dir": str(service.store.settings.install_dir),
        "openpath": openpath,
        "platform": platform,
        "can_install": True,
        "files": file_rows,
    }


async def create_tasks(service: TianyiService, plan: Dict[str, Any], *, split: int = 8) -> List[Any]:
    """建任务并写入 store（真实链路：fetch_download_url + aria2.add_uri）。"""
    tasks = await service._create_tasks_from_plan(plan=plan, split=split)
    service.store.upsert_tasks(tasks)
    return tasks


def mark_complete(service: TianyiService, task: Any, size: Optional[int] = None) -> Any:
    task.status = "complete"
    task.progress = 100.0
    task.speed = 0
    if size is not None:
        task.file_size = int(size)
    service.store.save()
    return task


async def run_post_process(service: TianyiService, task: Any) -> None:
    """直接执行一次安装流程（避免依赖后台任务调度）。"""
    await service._run_post_process_task(task.task_id)


async def wait_post_process(service: TianyiService, timeout: float = 10.0) -> List[BaseException]:
    """等待当前所有后台安装任务结束，返回收集到的异常。"""
    errors: List[BaseException] = []
    deadline = time.monotonic() + float(timeout)
    seen: set[int] = set()
    while time.monotonic() < deadline:
        jobs = [job for job in list(service._post_process_jobs.values()) if not job.done()]
        if not jobs:
            # 给 done_callback 一个执行机会，再确认确实没有新调度的安装任务。
            await asyncio.sleep(0)
            pending = [job for job in list(service._post_process_jobs.values()) if not job.done()]
            if not pending:
                return errors
            continue
        for job in jobs:
            if id(job) in seen:
                continue
            seen.add(id(job))
            try:
                await job
            except BaseException as exc:  # noqa: BLE001 - 测试里收集后由断言处理
                errors.append(exc)
    raise AssertionError("后台安装任务未在超时时间内结束")


async def install_completed_task(service: TianyiService, plan: Dict[str, Any], *, split: int = 8) -> Any:
    """建任务 + 标记完成 + 执行安装，返回任务。"""
    tasks = await create_tasks(service, plan, split=split)
    task = tasks[0]
    mark_complete(service, task)
    await run_post_process(service, task)
    return task


# ---------------------------------------------------------------------------
# 云存档
# ---------------------------------------------------------------------------


def patch_cloud(monkeypatch, cloud: FakeCloud) -> FakeCloud:
    """把云存档上传/列表/下载换成内存云盘。"""
    monkeypatch.setattr(svc_module, "upload_archive_to_cloud", cloud.upload)
    monkeypatch.setattr(svc_module, "list_cloud_archives", cloud.list)
    monkeypatch.setattr(svc_module, "download_cloud_archive", cloud.download)
    return cloud


async def patch_login(monkeypatch, service: TianyiService, *, logged_in: bool = True) -> None:
    async def _check_login_state():
        return (bool(logged_in), "sim-user", "ok" if logged_in else "未登录")

    monkeypatch.setattr(service, "check_login_state", _check_login_state)


async def run_cloud_upload(service: TianyiService) -> Dict[str, Any]:
    """直接跑一次云存档上传任务并返回最终状态快照。"""
    await service._run_cloud_save_upload_task(cookie="UID=sim", user_account="sim-user")
    return (await service.get_cloud_save_upload_status())["state"]


def make_installed_record(
    *,
    game_id: str,
    game_title: str,
    install_path: str,
    platform: str = "pc",
    rom_path: str = "",
    playtime_seconds: int = 0,
) -> svc_module.TianyiInstalledGame:
    """构造已安装记录（云存档测试用）。"""
    return svc_module.TianyiInstalledGame(
        game_id=game_id,
        game_title=game_title,
        install_path=str(install_path),
        source_path="",
        platform=platform,
        rom_path=str(rom_path),
        playtime_seconds=int(playtime_seconds),
        updated_at=int(time.time()),
    )


# ---------------------------------------------------------------------------
# 断言辅助
# ---------------------------------------------------------------------------


def installed_records(service: TianyiService) -> List[Any]:
    return list(service.store.installed_games)


def find_task(service: TianyiService, task_id: str) -> Any:
    for task in service.store.tasks:
        if task.task_id == task_id:
            return task
    raise AssertionError(f"任务不存在: {task_id}")


def sha256_file(path: str) -> str:
    import hashlib

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def newest_file(root: os.PathLike, pattern: str = "*") -> Optional[str]:
    matches = [path for path in Path(root).rglob(pattern) if path.is_file()]
    if not matches:
        return None
    matches.sort(key=lambda path: path.stat().st_mtime)
    return str(matches[-1])
