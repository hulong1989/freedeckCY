# tianyi_service.py - 天翼下载业务编排
#
# 该模块串联目录、登录态、直链与下载任务。

from __future__ import annotations

import asyncio
import base64
import csv
import hashlib
import io
import json
import os
import platform
import re
import shutil
import sqlite3
import ssl
import subprocess
import tarfile
import tempfile
import time
import uuid
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import parse_qs, quote, urljoin, urlparse

import aiohttp
import decky
from yarl import URL

import config
import catalog_signature
from archive_bundle import build_bundle_index, looks_like_multi_volume_name
from aria2_manager import Aria2Error, Aria2Manager
from baidu_client import (
    BaiduApiError,
    check_baidu_web_health,
    delete_baidu_home_file,
    fetch_baidu_download_url,
    resolve_baidu_share,
)
from baidu_qr import BaiduQrError, complete_login, fetch_qr_image, poll_qr, request_qr
from baidu_openapi_client import (
    BaiduOpenApiError,
    build_baidu_oauth_authorize_url,
    delete_baidu_openapi_transfer_file,
    exchange_baidu_oauth_code,
    fetch_baidu_openapi_download_url,
    fetch_baidu_openapi_user_info,
    is_baidu_openapi_auth_error,
    poll_baidu_device_token,
    refresh_baidu_oauth_token,
    request_baidu_device_code,
    resolve_baidu_openapi_share_url,
)
from emulator_setup import setup_emulator
from emulator_manager import (
    available_platforms,
    create_launch_wrapper,
    emulator_name_for_platform,
    emulator_status,
    ensure_emulator,
    find_rom_file,
    flatpak_installed,
    get_spec,
    supported_platforms,
)
from emulator_saves import build_restore_targets, collect_emulator_save_paths, restore_roots
from storage_options import detect_storage_options
from gamewatch import GameWatcher
from save_manifest import load_manifest, match_manifest, resolve_manifest_paths
from game_catalog import (
    GameCatalog,
    resolve_default_catalog_json_path,
    resolve_default_catalog_path,
    resolve_default_cover_index_path,
)
from seven_zip_manager import SevenZipError, SevenZipManager
from steam_shortcuts import (
    _find_steam_root,
    add_or_update_tianyi_shortcut,
    detect_proton_tool,
    is_droiddeck,
    find_compatdata_dirs,
    list_all_shortcuts_sync,
    list_tianyi_shortcuts_sync,
    remove_tianyi_shortcut,
    resolve_tianyi_shortcut_sync,
)
from tianyi_client import (
    TianyiApiError,
    build_tls_context,
    download_cloud_archive,
    fetch_access_token,
    fetch_download_url,
    get_user_account,
    list_cloud_archives,
    resolve_share,
    upload_archive_to_cloud,
)
from tianyi_store import TianyiInstalledGame, TianyiStateStore, TianyiTaskRecord
from update_flow import UpdateFlowMixin


def _describe_exception(exc: BaseException) -> str:
    """异常文本为空（如 TimeoutError）时至少记录类型，避免日志只有冒号。"""
    name = type(exc).__name__
    text = str(exc).strip()
    return f"{name}: {text}" if text else name


TASK_RETENTION_SECONDS = 7 * 24 * 3600
PANEL_TASK_REFRESH_TIMEOUT_SECONDS = 2.0
# 后台维护：不依赖前端轮询的下载/安装推进。
MAINTENANCE_INTERVAL_SECONDS = 8.0
MAINTENANCE_SYNC_TIMEOUT_SECONDS = 8.0
# aria2 单次状态查询失败不立刻判死，连续多次才标记错误（容忍重启/瞬时不可用）。
TASK_SYNC_ERROR_THRESHOLD = 5
# 安装收尾异常的后台自动重试上限：退避重试到上限后转为终态失败（避免永久重试刷日志）。
# 用户修复目录/空间后仍可在任务上手动“重试”，会重新获得重试次数。
POST_PROCESS_MAX_ATTEMPTS = 5
# 解压前的最低剩余空间系数：压缩包之外还要留一点余量。
EXTRACT_FREE_SPACE_MARGIN = 1.05
# 安装空间估算系数（压缩包 -> 解压后），仅用于给用户提示，不作为硬性拦截。
INSTALL_SPACE_ESTIMATE_FACTOR = 1.5
LOCAL_WEB_READY_TIMEOUT_SECONDS = 3.0
LOCAL_WEB_PROBE_TIMEOUT_SECONDS = 1.2
CAPTURE_DEFAULT_TIMEOUT_SECONDS = 240
CAPTURE_MIN_TIMEOUT_SECONDS = 30
CAPTURE_MAX_TIMEOUT_SECONDS = 600
CDP_ENDPOINT_PORTS = (8080, 9222)
TIANYI_HOST_KEYWORDS = ("cloud.189.cn", "h5.cloud.189.cn", "open.e.189.cn", "189.cn")
CAPTURE_LOOP_WINDOW = 8
CAPTURE_LOOP_CORE_HOSTS = ("cloud.189.cn", "h5.cloud.189.cn")
COOKIE_CAPTURE_SOURCES = ("cdp", "cookie_db")
COOKIE_DB_MAX_ROWS = 600
QR_LOGIN_SESSION_TIMEOUT_SECONDS = 300
QR_LOGIN_HTTP_TIMEOUT_SECONDS = 20
CATALOG_COVER_CACHE_TTL_SECONDS = 7 * 24 * 3600
CATALOG_COVER_NEGATIVE_TTL_SECONDS = 1800
CATALOG_COVER_HTTP_TIMEOUT_SECONDS = 6.0
CATALOG_COVER_SEARCH_LIMIT = 8
PROTONDB_HTTP_TIMEOUT_SECONDS = 4.5
HLTB_CACHE_TTL_SECONDS = 7 * 24 * 3600
HLTB_NEGATIVE_TTL_SECONDS = 60
HLTB_HTTP_TIMEOUT_SECONDS = 4.0
HLTB_SEARCH_LIMIT = 12
HLTB_TOKEN_URL = "https://howlongtobeat.com/api/finder/init"
HLTB_SEARCH_URL = "https://howlongtobeat.com/api/finder"
HLTB_LEGACY_SEARCH_URL = "https://howlongtobeat.com/api/search"
PANEL_POLL_MODE_ACTIVE = "active"
PANEL_POLL_MODE_IDLE = "idle"
PANEL_POLL_MODE_BACKGROUND = "background"
PANEL_TASK_REFRESH_ACTIVE_SECONDS = 1.0
PANEL_TASK_REFRESH_IDLE_SECONDS = 10.0
PANEL_TASK_REFRESH_BACKGROUND_SECONDS = 30.0
PANEL_INSTALLED_REFRESH_ACTIVE_SECONDS = 20.0
PANEL_INSTALLED_REFRESH_IDLE_SECONDS = 60.0
PANEL_INSTALLED_REFRESH_BACKGROUND_SECONDS = 120.0

QR_STATUS_SUCCESS = 0
QR_STATUS_WAITING = {-106}
QR_STATUS_SCANNED_WAIT_CONFIRM = {-11002}
QR_STATUS_EXPIRED = {-11001, -20099}
QR_STATUS_NEED_EXTRA_VERIFY = {-134}
QR_CA_CANDIDATE_FILES = (
    "/etc/ssl/certs/ca-certificates.crt",
    "/etc/pki/tls/certs/ca-bundle.crt",
    "/etc/ssl/cert.pem",
    "/etc/openssl/certs/ca-certificates.crt",
)
ARCHIVE_SUFFIXES = {
    ".zip",
    ".tar",
    ".tgz",
    ".tar.gz",
    ".tbz",
    ".tbz2",
    ".tar.bz2",
    ".txz",
    ".tar.xz",
    ".7z",
    ".rar",
}
CLOUD_SAVE_TASK_STAGES = {
    "idle",
    "scanning",
    "packaging",
    "uploading",
    "completed",
    "failed",
}
CLOUD_SAVE_RESTORE_TASK_STAGES = {
    "idle",
    "listing",
    "planning",
    "ready",
    "applying",
    "completed",
    "failed",
}
CLOUD_SAVE_DATE_FORMAT = "%Y%m%d_%H%M%S"
CLOUD_SAVE_UPLOAD_ROOT = "freedeckCYCloudSaves"
CLOUD_SAVE_PROTON_BASE_DIRS = (
    ("Documents", "My Games"),
    ("Saved Games",),
    ("AppData", "Roaming"),
    ("AppData", "Local"),
    ("AppData", "LocalLow"),
)
CLOUD_SAVE_INSTALL_FALLBACK_DIRS = (
    "save",
    "saves",
    "saved",
    "userdata",
    "profiles",
)
CLOUD_SAVE_SCAN_MAX_DEPTH = 6
CLOUD_SAVE_SCAN_MAX_MATCHES = 32
CLOUD_SAVE_MAX_SOURCE_PATHS = 24
CLOUD_SAVE_RESTORE_CONFLICT_SAMPLES = 16
PLAYTIME_SESSION_MAX_SECONDS = 12 * 3600
PLAYTIME_STALE_SESSION_SECONDS = 3 * 24 * 3600

def _now_wall_ts() -> int:
    """返回当前 wall-clock 秒级时间戳。"""
    return int(time.time())


_TIANYI_SHARE_HOSTS = {"cloud.189.cn", "h5.cloud.189.cn", "api.cloud.189.cn"}


def _is_tianyi_share_url(url: str) -> bool:
    """只接受天翼云盘的分享链接，避免本地页面把任意 URL 塞进下载链路。"""
    try:
        parsed = urlparse(str(url or "").strip())
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = str(parsed.hostname or "").strip().lower()
    if not host:
        return False
    if host in _TIANYI_SHARE_HOSTS:
        return True
    return host.endswith(".189.cn")


_BAIDU_SHARE_HOSTS = {"pan.baidu.com", "yun.baidu.com", "eyun.baidu.com"}


def _is_baidu_share_url(url: str) -> bool:
    try:
        parsed = urlparse(str(url or "").strip())
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = str(parsed.hostname or "").strip().lower()
    return any(host == candidate or host.endswith("." + candidate) for candidate in _BAIDU_SHARE_HOSTS)


def _share_provider(url: str) -> str:
    if _is_tianyi_share_url(url):
        return "tianyi"
    if _is_baidu_share_url(url):
        return "baidu"
    return ""


class ArchiveRepairScheduled(RuntimeError):
    """归档校验失败后已安排重新下载，调用方不应把任务标记为已处理。"""


class InstallRetryable(RuntimeError):
    """下载文件仍在收尾：保持任务未处理，稍后自动重试安装。"""


def _dir_size_bytes(path: str) -> int:
    """递归统计目录大小（符号链接不跟随），失败时返回已统计部分。"""
    root = str(path or "").strip()
    if not root or not os.path.isdir(root):
        return 0
    total = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            file_path = os.path.join(dirpath, name)
            try:
                if os.path.islink(file_path):
                    continue
                total += max(0, int(os.path.getsize(file_path)))
            except Exception:
                continue
    return total


def _is_within_dir(path: str, base: str) -> bool:
    """判断 path 是否位于 base 目录之内。

    用 `os.path.commonpath` 而不是 `startswith`：后者会把 `/a/bc` 误判为 `/a/b`
    的子路径，也可能被 `../` 逃逸。
    """
    try:
        base_real = os.path.realpath(os.path.expanduser(str(base or "")))
        target_real = os.path.realpath(os.path.expanduser(str(path or "")))
        if not base_real or not target_real:
            return False
        if target_real == base_real:
            return True
        return os.path.commonpath([base_real, target_real]) == base_real
    except Exception:
        return False


def _safe_int(value: Any, default: int = 0) -> int:
    """安全解析整数。"""
    try:
        return int(value)
    except Exception:
        return default


def _format_size_bytes(size_bytes: int) -> str:
    """将字节数格式化为易读文本。"""
    value = float(max(0, int(size_bytes or 0)))
    units = ["B", "KB", "MB", "GB", "TB"]
    unit = units[0]
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            break
        value /= 1024.0
    if unit == "B":
        return f"{int(value)} {unit}"
    return f"{value:.2f} {unit}"


def _format_playtime_seconds(total_seconds: int) -> str:
    """将累计游玩秒数格式化为可读文本。"""
    seconds = max(0, int(total_seconds or 0))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours} 小时 {minutes} 分钟"
    if minutes > 0:
        return f"{minutes} 分钟"
    return "0 分钟"


def _format_hours_value(hours_value: Any) -> str:
    """将小时数格式化为可读文本。"""
    try:
        value = float(hours_value)
    except Exception:
        value = 0.0
    if value <= 0:
        return "-"
    rounded = round(value, 1)
    if abs(rounded - round(rounded)) < 0.05:
        return f"{int(round(rounded))} 小时"
    return f"{rounded:.1f} 小时"


def _disk_free_bytes(path: str) -> int:
    """获取目标目录所在分区的可用空间。"""
    target = os.path.realpath(os.path.expanduser(str(path or "").strip()))
    if not target:
        raise ValueError("目录无效")
    os.makedirs(target, exist_ok=True)
    usage = shutil.disk_usage(target)
    return int(usage.free)


def _task_to_view(task: TianyiTaskRecord) -> Dict[str, Any]:
    """转换任务展示结构。"""
    return {
        "task_id": task.task_id,
        "game_id": task.game_id,
        "game_title": task.game_title,
        "file_name": task.file_name,
        "status": task.status,
        "progress": round(float(task.progress), 2),
        "speed": int(task.speed),
        "error_reason": task.error_reason,
        "install_status": task.install_status,
        "install_message": task.install_message,
        "installed_path": task.installed_path,
        "post_processed": bool(task.post_processed),
        "platform": str(getattr(task, "platform", "pc") or "pc"),
        "updated_at": task.updated_at,
    }


def _is_terminal(status: str) -> bool:
    """判断任务是否终态。"""
    return status in {"complete", "error", "removed"}


class LocalWebNotReadyError(RuntimeError):
    """本地网页未就绪异常，附带结构化诊断信息。"""

    def __init__(self, message: str, *, reason: str, diagnostics: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.reason = str(reason or "local_web_not_ready")
        self.diagnostics = diagnostics or {}


def _runtime_arch_name() -> str:
    """运行时目录使用的架构名。"""
    machine = str(platform.machine() or "").strip().lower()
    if machine in {"x86_64", "amd64"}:
        return "x86_64"
    if machine in {"aarch64", "arm64"}:
        return "aarch64"
    return machine


def _tail_text(path: str, limit: int = 200) -> str:
    """读取文本文件末尾若干行。"""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except Exception:
        return ""
    return "".join(lines[-max(1, int(limit)) :])


_REDACT_PATTERN = re.compile(
    r"(?i)\b(cookie|authorization|token|access_token|refresh_token|sessionkey|accesstoken|client_secret|secret|uid|pwd|randsk|bduss|stoken|ptoken|bdstoken|sign)\b(\s*[=:]\s*)([^\s;，,]+)"
)


def _write_private_file(path: str, data: bytes) -> None:
    """写 0600 文件（诊断包可能含路径/错误信息）。"""
    with open(path, "wb") as fh:
        fh.write(data)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def _redact_text(text: str) -> str:
    """脱敏：替换 HOME 路径与 cookie/token 类键值。"""
    value = str(text or "")
    home = os.path.expanduser("~")
    if home and home != "/":
        value = value.replace(home, "~")
    return _REDACT_PATTERN.sub(lambda m: f"{m.group(1)}{m.group(2)}<redacted>", value)


def _parse_version(value: str) -> Tuple[int, ...]:
    """把 v0.4.0 / 0.4.0-pre 解析成可比较元组。"""
    parts = re.findall(r"\d+", str(value or ""))
    return tuple(int(part) for part in parts[:4]) if parts else (0,)


def _launch_external(target: str) -> None:
    """用 xdg-open / gio 拉起 URL 或目录（后端与浏览器同一台机器）。"""
    value = str(target or "").strip()
    if not value:
        raise ValueError("目标为空")
    opener = shutil.which("xdg-open")
    if opener:
        command = [opener, value]
    else:
        gio = shutil.which("gio")
        if not gio:
            raise ValueError("当前环境没有 xdg-open/gio，无法拉起到外部程序")
        command = [gio, "open", value]
    subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


class TianyiService(UpdateFlowMixin):
    """天翼下载业务入口。"""

    def __init__(self, plugin: Any):
        self.plugin = plugin
        plugin_dir = str(getattr(decky, "DECKY_PLUGIN_DIR", Path.cwd()))
        self.plugin_dir = plugin_dir
        state_root = config.DECKY_SEND_DIR
        try:
            os.makedirs(state_root, exist_ok=True)
        except Exception:
            # 某些开发环境中家目录不可写，回退到插件目录下的临时目录。
            state_root = os.path.join(plugin_dir, ".tmp", "Decky-send")

        state_dir = os.path.join(state_root, "tianyi")
        state_file = os.path.join(state_dir, "state.json")
        self.store = TianyiStateStore(state_file)
        self.catalog = GameCatalog(
            resolve_default_catalog_path(),
            cover_index_path=resolve_default_cover_index_path(),
            json_path=resolve_default_catalog_json_path(),
        )
        self._cover_cache_path = os.path.join(state_dir, "cover_cache.json")
        self._update_cache: Dict[str, Any] = {}
        self._update_cache_at: float = 0.0
        self.aria2 = Aria2Manager(plugin_dir=plugin_dir, work_dir=os.path.join(state_dir, "aria2"))
        self.seven_zip = SevenZipManager(plugin_dir=plugin_dir)
        self._lock = asyncio.Lock()
        self._refresh_lock = asyncio.Lock()
        self._post_process_jobs: Dict[str, asyncio.Task] = {}
        self._post_process_failures: Dict[str, Dict[str, Any]] = {}
        self._legacy_backup_migration_done = False
        self._steam_restart_pending: Dict[str, Any] = {}
        self._launcher_repair_task: Optional[asyncio.Task] = None
        self._launcher_repair_done = False
        self._catalog_auto_update_task: Optional[asyncio.Task] = None
        self._catalog_update_notice: Dict[str, Any] = {}
        self._baidu_device_lock = asyncio.Lock()
        self._baidu_device_login: Dict[str, Any] = {}
        self._baidu_qr_lock = asyncio.Lock()
        self._baidu_qr_session: Dict[str, Any] = {}
        # 后台维护（不依赖前端轮询）与安装互斥。
        self._maintenance_lock = asyncio.Lock()
        self._install_locks: Dict[str, asyncio.Lock] = {}
        self._task_sync_misses: Dict[str, int] = {}
        # refresh_tasks 里按需构建：aria2 文件路径 -> 下载项，用于重启后认领任务
        self._aria2_path_index: Optional[Dict[str, Dict[str, Any]]] = None
        # aria2 会话丢失时，每个任务最多自动重新加入一次下载
        self._readd_attempts: Dict[str, int] = {}

        # 登录采集状态机（内存态）。
        self._capture_state: Dict[str, Any] = {
            "stage": "idle",
            "message": "未开始",
            "reason": "",
            "next_action": "",
            "user_account": "",
            "updated_at": _now_wall_ts(),
            "diagnostics": {},
            "source_attempts": [],
            "success_source": "",
            "source_diagnostics": {},
        }
        self._capture_task: Optional[asyncio.Task] = None
        self._capture_lock = asyncio.Lock()
        self._qr_login_lock = asyncio.Lock()
        self._qr_login_state: Dict[str, Any] = {
            "session_id": "",
            "stage": "idle",
            "message": "未开始",
            "reason": "",
            "next_action": "",
            "user_account": "",
            "image_url": "",
            "expires_at": 0,
            "updated_at": _now_wall_ts(),
            "diagnostics": {},
        }
        self._qr_login_context: Optional[Dict[str, Any]] = None
        self._catalog_cover_cache: Dict[str, Dict[str, Any]] = {}
        self._catalog_cover_lock = asyncio.Lock()
        self._hltb_cache: Dict[str, Dict[str, Any]] = {}
        self._hltb_lock = asyncio.Lock()
        self._panel_cache_lock = asyncio.Lock()
        self._panel_tasks_cache: List[Dict[str, Any]] = []
        self._panel_tasks_cache_at = 0.0
        self._panel_installed_cache: Dict[str, Any] = {"total": 0, "preview": []}
        self._panel_installed_cache_at = 0.0
        self._panel_last_expensive_refresh_at = 0.0
        self._panel_last_mode = PANEL_POLL_MODE_IDLE
        self._panel_last_active_tasks = 0
        self._cloud_save_lock = asyncio.Lock()
        self._cloud_save_task: Optional[asyncio.Task] = None
        self._game_watcher = GameWatcher()
        self._auto_cloud_upload_task: Optional[asyncio.Task] = None
        self._last_auto_cloud_upload_at = 0.0
        self._cloud_save_state: Dict[str, Any] = {
            "stage": "idle",
            "message": "未开始",
            "reason": "",
            "running": False,
            "progress": 0.0,
            "current_game": "",
            "total_games": 0,
            "processed_games": 0,
            "uploaded": 0,
            "skipped": 0,
            "failed": 0,
            "results": [],
            "diagnostics": {},
            "updated_at": _now_wall_ts(),
            "last_result": {},
        }
        self._cloud_save_restore_lock = asyncio.Lock()
        self._cloud_save_restore_state: Dict[str, Any] = {
            "stage": "idle",
            "message": "未开始",
            "reason": "",
            "running": False,
            "progress": 0.0,
            "target_game_id": "",
            "target_game_title": "",
            "target_game_key": "",
            "target_version": "",
            "selected_entry_ids": [],
            "selected_target_dir": "",
            "requires_confirmation": False,
            "conflict_count": 0,
            "conflict_samples": [],
            "restored_files": 0,
            "restored_entries": 0,
            "results": [],
            "diagnostics": {},
            "updated_at": _now_wall_ts(),
            "last_result": {},
        }
        self._cloud_save_restore_plan: Dict[str, Any] = {}
        self._playtime_lock = asyncio.Lock()
        self._playtime_sessions: Dict[str, Dict[str, Any]] = {}

    async def _auto_update_catalog(self, url: str) -> None:
        """后台检查并更新服务器目录；失败只记日志，不阻塞插件启动。"""
        try:
            result = await asyncio.wait_for(self.update_catalog_csv(url), timeout=90)
            config.logger.info(
                "启动自动检查目录: updated=%s reason=%s total=%s",
                result.get("updated"),
                result.get("reason", ""),
                result.get("total", 0),
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            config.logger.warning("启动自动检查目录失败: %s", exc)

    async def initialize(self) -> None:
        """初始化状态与目录。"""
        os.makedirs(os.path.dirname(self.store.state_file), exist_ok=True)
        await asyncio.to_thread(self.store.load)
        await asyncio.to_thread(self._load_cover_cache)
        await asyncio.to_thread(self.catalog.load)
        if not self.store.settings.download_dir:
            default_dir = getattr(self.plugin, "downloads_dir", config.DOWNLOADS_DIR)
            self.store.set_settings(download_dir=default_dir)
        if not self.store.settings.install_dir:
            default_install = os.path.join(self.store.settings.download_dir or config.DOWNLOADS_DIR, "installed")
            os.makedirs(default_install, exist_ok=True)
            self.store.set_settings(install_dir=default_install)
        # 自动安装能力固定开启，避免 UI 配置分叉造成行为不一致。
        if not bool(self.store.settings.auto_install):
            self.store.set_settings(auto_install=True)
        self._cloud_save_state["last_result"] = dict(self.store.cloud_save_last_result or {})
        self._cloud_save_restore_state["last_result"] = dict(self.store.cloud_save_restore_last_result or {})
        await self._recover_playtime_sessions_from_store()
        if self._recover_unfinished_install_tasks():
            await asyncio.to_thread(self.store.save)
        catalog_url = str(getattr(self.store.settings, "catalog_url", "") or "").strip()
        if not catalog_url:
            catalog_url = str(getattr(config, "DEFAULT_CATALOG_CSV_URL", "") or "").strip()
        if catalog_url.startswith(("http://", "https://")):
            self._catalog_auto_update_task = asyncio.create_task(self._auto_update_catalog(catalog_url))

    async def shutdown(self) -> None:
        """关闭后台资源。"""
        async with self._capture_lock:
            if self._capture_task and not self._capture_task.done():
                self._capture_task.cancel()
                try:
                    await self._capture_task
                except BaseException:
                    pass
            self._capture_task = None
        async with self._qr_login_lock:
            await self._close_qr_login_context_locked()
        await self._finalize_active_playtime_sessions(reason="service_shutdown")
        if self._launcher_repair_task and not self._launcher_repair_task.done():
            self._launcher_repair_task.cancel()
            try:
                await self._launcher_repair_task
            except BaseException:
                pass
        self._launcher_repair_task = None
        if self._catalog_auto_update_task and not self._catalog_auto_update_task.done():
            self._catalog_auto_update_task.cancel()
            try:
                await self._catalog_auto_update_task
            except BaseException:
                pass
        self._catalog_auto_update_task = None
        if self._auto_cloud_upload_task and not self._auto_cloud_upload_task.done():
            self._auto_cloud_upload_task.cancel()
            try:
                await self._auto_cloud_upload_task
            except BaseException:
                pass
        self._auto_cloud_upload_task = None
        await self._cancel_cloud_save_task()
        await self._clear_cloud_save_restore_plan()
        jobs = list(self._post_process_jobs.values())
        for job in jobs:
            if not job.done():
                job.cancel()
        for job in jobs:
            try:
                await job
            except BaseException:
                pass
        self._post_process_jobs.clear()
        await asyncio.to_thread(self.aria2.stop)

    async def maintenance_tick(self) -> Dict[str, Any]:
        """后台维护：同步下载进度并补做未完成的安装。

        由 `main.py` 的主循环周期调用，保证**不依赖 Decky 面板是否打开**：
        下载完成、插件重启、解压中断等场景都能继续推进安装。
        """
        if self._maintenance_lock.locked():
            return {"ok": True, "skipped": "busy"}

        async with self._maintenance_lock:
            pending_before = [
                task for task in list(self.store.tasks)
                if str(task.status) == "complete" and not bool(task.post_processed)
            ]
            jobs_before = set(self._post_process_jobs)
            # 先调度已完成的安装，再同步 aria2：即使 RPC 卡住/超时，
            # 已下载完的游戏也能立即进入解压入库，不必等 refresh 超时。
            for task in pending_before:
                self._maybe_schedule_group_post_process(task)
            refresh_error = ""
            try:
                if self._refresh_lock.locked():
                    # 另一个安装准备/同步正在持锁：不要排队等超时，直接做本地兜底。
                    tasks = [_task_to_view(task) for task in self.store.tasks]
                    raise TimeoutError("refresh lock busy")
                tasks = await asyncio.wait_for(
                    self.refresh_tasks(sync_aria2=True),
                    timeout=MAINTENANCE_SYNC_TIMEOUT_SECONDS,
                )
            except Exception as exc:
                # aria2 同步失败/超时不能阻断安装收尾：下载文件可能已经完整，
                # 只是 RPC 暂时不可用。先做文件大小兜底，再照常调度后处理。
                refresh_error = _describe_exception(exc)
                config.logger.warning("Maintenance refresh failed (continue post-process): %s", refresh_error)
                for task in list(self.store.tasks):
                    if _is_terminal(task.status):
                        continue
                    if self._file_matches_expected_size(task):
                        task.status = "complete"
                        task.progress = 100.0
                        task.speed = 0
                        task.error_reason = ""
                        task.updated_at = _now_wall_ts()
                try:
                    await asyncio.to_thread(self.store.save)
                except Exception as save_exc:
                    config.logger.warning("Maintenance fallback save failed: %s", _describe_exception(save_exc))
                tasks = [_task_to_view(task) for task in self.store.tasks]

            pending = [
                task for task in list(self.store.tasks)
                if str(task.status) == "complete" and not bool(task.post_processed)
            ]
            for task in pending:
                self._maybe_schedule_group_post_process(task)
            scheduled = len(set(self._post_process_jobs) - jobs_before)
            self._poll_game_watch()
            self._maybe_schedule_launcher_repair()
            legacy_backups_migrated = self._migrate_all_legacy_backups()

            result = {
                "ok": not bool(refresh_error),
                "tasks": len(tasks),
                "pending_post_process_before": len(pending_before),
                "pending_post_process": len(pending),
                "scheduled": scheduled,
                "legacy_backups_migrated": legacy_backups_migrated,
            }
            if refresh_error:
                result["message"] = refresh_error
            return result

    def _normalize_panel_mode(self, context: Optional[Dict[str, Any]] = None) -> tuple[str, bool, bool]:
        """规范化面板轮询模式。"""
        payload = context if isinstance(context, dict) else {}
        mode = str(payload.get("poll_mode", "") or "").strip().lower()
        visible = bool(payload.get("visible", True))
        has_focus = bool(payload.get("has_focus", True))
        if mode not in {PANEL_POLL_MODE_ACTIVE, PANEL_POLL_MODE_IDLE, PANEL_POLL_MODE_BACKGROUND}:
            mode = PANEL_POLL_MODE_BACKGROUND if not visible else PANEL_POLL_MODE_IDLE
        if mode != PANEL_POLL_MODE_BACKGROUND and not visible:
            mode = PANEL_POLL_MODE_BACKGROUND
        return mode, visible, has_focus

    def _panel_task_refresh_window(self, mode: str, active_tasks: int) -> float:
        """按模式与活跃任务数量返回任务刷新窗口。"""
        if mode == PANEL_POLL_MODE_BACKGROUND:
            return PANEL_TASK_REFRESH_BACKGROUND_SECONDS
        if active_tasks > 0:
            return PANEL_TASK_REFRESH_ACTIVE_SECONDS
        return PANEL_TASK_REFRESH_IDLE_SECONDS

    def _panel_installed_refresh_window(self, mode: str, active_tasks: int) -> float:
        """按模式与活跃任务数量返回安装列表刷新窗口。"""
        if mode == PANEL_POLL_MODE_BACKGROUND:
            return PANEL_INSTALLED_REFRESH_BACKGROUND_SECONDS
        if active_tasks > 0:
            return PANEL_INSTALLED_REFRESH_ACTIVE_SECONDS
        return PANEL_INSTALLED_REFRESH_IDLE_SECONDS

    def _count_active_tasks(self, tasks: Sequence[Dict[str, Any]]) -> int:
        """统计非终态任务数量。"""
        count = 0
        for item in tasks:
            status = str((item or {}).get("status", "")).strip().lower()
            if status and not _is_terminal(status):
                count += 1
        return count

    def _invalidate_panel_cache(self, *, tasks: bool = False, installed: bool = False, all_data: bool = False) -> None:
        """失效面板缓存，确保关键变更后可及时刷新。"""
        if all_data or tasks:
            self._panel_tasks_cache = []
            self._panel_tasks_cache_at = 0.0
        if all_data or installed:
            self._panel_installed_cache = {"total": 0, "preview": []}
            self._panel_installed_cache_at = 0.0
        if all_data or tasks or installed:
            self._panel_last_expensive_refresh_at = 0.0

    async def get_panel_state(self, *, request_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """返回 Decky 面板状态。"""
        async with self._panel_cache_lock:
            now = time.monotonic()
            requested_mode, visible, has_focus = self._normalize_panel_mode(request_context)

            cached_tasks = list(self._panel_tasks_cache)
            if not cached_tasks:
                cached_tasks = [_task_to_view(task) for task in list(self.store.tasks)]

            active_tasks = self._count_active_tasks(cached_tasks)
            effective_mode = requested_mode
            if requested_mode != PANEL_POLL_MODE_BACKGROUND:
                effective_mode = PANEL_POLL_MODE_ACTIVE if active_tasks > 0 else PANEL_POLL_MODE_IDLE

            task_window = self._panel_task_refresh_window(effective_mode, active_tasks)
            installed_window = self._panel_installed_refresh_window(effective_mode, active_tasks)
            tasks_refreshed = False
            installed_refreshed = False

            tasks = cached_tasks
            if self._refresh_lock.locked():
                tasks = list(self._panel_tasks_cache) if self._panel_tasks_cache else list(cached_tasks)
            elif now - float(self._panel_tasks_cache_at or 0.0) >= float(task_window):
                try:
                    tasks = await asyncio.wait_for(
                        self.refresh_tasks(sync_aria2=True, persist=False),
                        timeout=PANEL_TASK_REFRESH_TIMEOUT_SECONDS,
                    )
                    self._panel_tasks_cache = list(tasks)
                    self._panel_tasks_cache_at = now
                    tasks_refreshed = True
                except Exception as exc:
                    config.logger.warning("Panel tasks refresh fallback to cache: %s", _describe_exception(exc))
                    tasks = list(self._panel_tasks_cache) if self._panel_tasks_cache else list(cached_tasks)

            active_tasks = self._count_active_tasks(tasks)
            if requested_mode != PANEL_POLL_MODE_BACKGROUND:
                effective_mode = PANEL_POLL_MODE_ACTIVE if active_tasks > 0 else PANEL_POLL_MODE_IDLE
                task_window = self._panel_task_refresh_window(effective_mode, active_tasks)
                installed_window = self._panel_installed_refresh_window(effective_mode, active_tasks)

            installed_cached = dict(self._panel_installed_cache or {"total": 0, "preview": []})
            installed_cached["preview"] = list(installed_cached.get("preview") or [])
            installed = installed_cached
            if now - float(self._panel_installed_cache_at or 0.0) >= float(installed_window):
                installed = self._build_installed_summary(limit=60, persist=False)
                self._panel_installed_cache = {
                    "total": int(installed.get("total", 0) or 0),
                    "preview": list(installed.get("preview") or []),
                }
                self._panel_installed_cache_at = now
                installed_refreshed = True
            elif not installed_cached.get("preview"):
                installed = self._build_installed_summary(limit=60, persist=False)
                self._panel_installed_cache = {
                    "total": int(installed.get("total", 0) or 0),
                    "preview": list(installed.get("preview") or []),
                }
                self._panel_installed_cache_at = now
                installed_refreshed = True

            if tasks_refreshed or installed_refreshed:
                self._panel_last_expensive_refresh_at = now

            self._panel_last_mode = effective_mode
            self._panel_last_active_tasks = active_tasks

            last_expensive_at = float(self._panel_last_expensive_refresh_at or 0.0)
            last_task_at = float(self._panel_tasks_cache_at or 0.0)
            last_installed_at = float(self._panel_installed_cache_at or 0.0)

            power_diagnostics = {
                "requested_mode": requested_mode,
                "effective_mode": effective_mode,
                "visible": bool(visible),
                "has_focus": bool(has_focus),
                "active_tasks": int(active_tasks),
                "task_refresh_interval_seconds": float(task_window),
                "installed_refresh_interval_seconds": float(installed_window),
                "tasks_refreshed": bool(tasks_refreshed),
                "installed_refreshed": bool(installed_refreshed),
                "last_expensive_refresh_age_seconds": round(max(0.0, now - last_expensive_at), 3)
                if last_expensive_at > 0
                else -1.0,
                "last_tasks_refresh_age_seconds": round(max(0.0, now - last_task_at), 3) if last_task_at > 0 else -1.0,
                "last_installed_refresh_age_seconds": round(max(0.0, now - last_installed_at), 3)
                if last_installed_at > 0
                else -1.0,
            }

        summary = self.catalog.summary()
        cached_cookie = str(self.store.login.cookie or "").strip()
        cached_account = str(self.store.login.user_account or "").strip()
        login_ok = bool(cached_cookie)
        account = cached_account
        message = "未登录"
        if login_ok:
            message = f"已登录（缓存）：{cached_account or '未知账号'}"

        # 面板轮询走纯缓存快路径，避免本地端口探测与网络校验阻塞 RPC。
        # 服务已在运行时直接拼 URL（不探测），未运行时前端会再调 get_tianyi_library_url 兜底。
        login_url = ""
        library_url = ""
        if bool(getattr(self.plugin, "server_running", False)):
            port = int(getattr(self.plugin, "server_port", 0) or 0)
            if port > 0:
                library_url = f"http://127.0.0.1:{port}/tianyi/library"
                login_url = f"http://127.0.0.1:{port}/tianyi/library/login-bridge"

        return {
            "login": {
                "logged_in": login_ok,
                "user_account": account,
                "message": message,
                "login_url": login_url,
            },
            "catalog": {
                "total": summary.get("total", 0),
                "preview": [],
                "path": summary.get("path", ""),
            },
            "installed": installed,
            "tasks": tasks,
            "settings": {
                **asdict(self.store.settings),
                # 内置地址只在后端使用，不回显到设置页；用户填写后才显示/覆盖。
                "catalog_url": str(getattr(self.store.settings, "catalog_url", "") or "").strip(),
            },
            "library_url": library_url,
            "cover_proxy_base": self.get_cover_proxy_base(),
            "login_capture": await self.get_login_capture_status(),
            "baidu_login": {
                "logged_in": self.store.baidu_login.logged_in,
                "user_account": self.store.baidu_login.user_account,
                "message": "已登录" if self.store.baidu_login.logged_in else "未登录",
            },
            "baidu_openapi_login": self._baidu_openapi_payload(),
            "power_diagnostics": power_diagnostics,
            "steam_restart": dict(self._steam_restart_pending or {"pending": False}),
            "catalog_update_notice": dict(self._catalog_update_notice or {}),
        }

    def get_cloud_login_url(self) -> str:
        """返回天翼云官方登录网址。"""
        return "https://cloud.189.cn/web/login.html"

    async def get_login_url(self) -> str:
        """返回本地登录桥接页面地址。"""
        target = quote(self.get_cloud_login_url(), safe="")
        return await self._ensure_local_web_ready(f"/tianyi/library/login-bridge?target={target}")

    async def get_library_url(self) -> str:
        """返回本地游戏库网页地址。"""
        return await self._ensure_local_web_ready("/tianyi/library")

    async def peek_login_url(self) -> str:
        """只读取登录桥接地址，不主动启动服务。"""
        target = quote(self.get_cloud_login_url(), safe="")
        return await self._peek_local_web_url(f"/tianyi/library/login-bridge?target={target}")

    async def peek_library_url(self) -> str:
        """只读取游戏库地址，不主动启动服务。"""
        return await self._peek_local_web_url("/tianyi/library")

    async def check_login_state(self) -> tuple[bool, str, str]:
        """校验当前登录态。"""
        cookie = (self.store.login.cookie or "").strip()
        if not cookie:
            return False, "", "未登录"
        try:
            account = await get_user_account(cookie)
        except Exception as exc:
            return False, "", f"登录态检查失败: {exc}"

        if not account:
            self.store.clear_login()
            return False, "", "登录态已失效，请重新登录"

        # 登录态有效时刷新账号名。
        self.store.set_login(cookie, account)
        return True, account, "登录态有效"

    def _baidu_web_login_payload(self) -> Dict[str, Any]:
        state = self.store.baidu_login
        return {
            "logged_in": state.logged_in,
            "user_account": state.user_account,
            "message": "已登录" if state.logged_in else "未登录",
        }

    async def check_baidu_web_login_health(self) -> Dict[str, Any]:
        """检查百度网页登录、bdstoken 和转存目录。"""
        cookie = str(self.store.baidu_login.cookie or "").strip()
        if not cookie:
            return {
                "ok": False,
                "stage": "login",
                "message": "未登录百度网盘，请先扫码登录",
                "user": "",
                "vip_type": 0,
                "checks": [],
            }
        return await check_baidu_web_health(cookie)

    async def start_baidu_qr_login(self) -> Dict[str, Any]:
        """百度网页版扫码：返回二维码 data URL。"""
        async with self._baidu_qr_lock:
            config.logger.info("Baidu QR start requested")
            try:
                qr = await asyncio.wait_for(request_qr(), timeout=12)
            except asyncio.TimeoutError as exc:
                config.logger.warning("Baidu QR request timed out")
                raise TianyiApiError("获取百度二维码超时（网络/TLS 可能受阻，请重试或运行诊断）") from exc
            except Exception as exc:
                config.logger.warning("Baidu QR request failed: %s", exc)
                raise TianyiApiError(f"获取百度二维码失败：{exc}") from exc
            config.logger.info("Baidu QR ready sign_len=%s", len(str(qr.get("sign", ""))))
            raw = b""
            try:
                raw = await asyncio.wait_for(fetch_qr_image(str(qr.get("imgurl", "") or "")), timeout=6)
            except Exception as exc:
                config.logger.warning("下载百度二维码图片失败: %s", exc)
            qr_data_url = ""
            if raw:
                qr_data_url = "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
            self._baidu_qr_session = {
                "sign": qr["sign"],
                "imgurl": qr.get("imgurl", ""),
                "cookies": qr.get("cookies") or {},
                "expires_at": _now_wall_ts() + 180,
            }
            return {
                "stage": "waiting",
                "qr_data_url": qr_data_url,
                "qrcode_url": str(qr.get("imgurl", "") or ""),
                "expires_at": self._baidu_qr_session["expires_at"],
                "message": "请用百度 App / 百度网盘 App 扫码登录",
            }

    async def poll_baidu_qr_login(self) -> Dict[str, Any]:
        """轮询百度扫码状态；确认后写入 BDUSS/Cookie。"""
        async with self._baidu_qr_lock:
            session = dict(self._baidu_qr_session or {})
            if not session:
                return {"stage": "idle", "message": "未开始扫码登录", **self._baidu_web_login_payload()}
            if int(session.get("expires_at", 0) or 0) <= _now_wall_ts():
                self._baidu_qr_session = {}
                return {"stage": "expired", "message": "二维码已过期，请重新获取", **self._baidu_web_login_payload()}
            result = await poll_qr(
                str(session.get("sign", "") or ""),
                timeout=8.0,
                cookies=session.get("cookies") if isinstance(session.get("cookies"), dict) else None,
            )
            stage = str(result.get("status", "") or "")
            if stage == "scanned":
                return {"stage": "scanned", "message": "已扫码，请在手机上确认登录", **self._baidu_web_login_payload()}
            if stage == "error":
                return {"stage": "failed", "message": f"扫码轮询失败：{result.get('error', '')}", **self._baidu_web_login_payload()}
            if stage == "expired":
                self._baidu_qr_session = {}
                return {"stage": "expired", "message": "二维码已失效，请重新获取", **self._baidu_web_login_payload()}
            if stage != "confirmed":
                return {"stage": "waiting", "message": "等待手机扫码…", **self._baidu_web_login_payload()}
            try:
                login = await complete_login(
                    str(result.get("v", "") or ""),
                    cookies=session.get("cookies") if isinstance(session.get("cookies"), dict) else None,
                )
            except BaiduQrError as exc:
                self._baidu_qr_session = {}
                return {"stage": "failed", "message": str(exc), **self._baidu_web_login_payload()}
            self.store.baidu_login.cookie = str(login.get("cookie", "") or "")
            self.store.baidu_login.user_account = str(login.get("user_account", "") or "")
            self.store.baidu_login.updated_at = _now_wall_ts()
            self._baidu_qr_session = {}
            await asyncio.to_thread(self.store.save)
            self._invalidate_panel_cache(all_data=True)
            return {"stage": "success", "message": "百度网盘登录成功", **self._baidu_web_login_payload()}

    async def cancel_baidu_qr_login(self) -> Dict[str, Any]:
        async with self._baidu_qr_lock:
            self._baidu_qr_session = {}
        return {"stage": "idle", "message": "已取消百度扫码登录"}

    async def clear_baidu_login(self) -> Dict[str, Any]:
        self.store.baidu_login.cookie = ""
        self.store.baidu_login.user_account = ""
        self.store.baidu_login.updated_at = _now_wall_ts()
        await asyncio.to_thread(self.store.save)
        self._invalidate_panel_cache(all_data=True)
        return {"ok": True, **self._baidu_web_login_payload()}

    def _baidu_openapi_payload(self) -> Dict[str, Any]:
        state = self.store.baidu_openapi
        return {
            "configured": state.configured,
            "logged_in": state.logged_in,
            "user_account": state.user_account,
            "expires_at": state.expires_at,
            "message": "已授权" if state.logged_in else ("已配置应用，待授权" if state.configured else "未配置"),
        }

    def _baidu_openapi_credentials(self) -> tuple[str, str]:
        state = self.store.baidu_openapi
        app_key = str(state.app_key or os.getenv("FREEDECKCY_BAIDU_OPENAPI_APP_KEY", "") or "").strip()
        secret_key = str(state.secret_key or os.getenv("FREEDECKCY_BAIDU_OPENAPI_SECRET_KEY", "") or "").strip()
        return app_key, secret_key

    async def get_baidu_openapi_authorize_url(self) -> Dict[str, Any]:
        app_key, secret_key = self._baidu_openapi_credentials()
        if not app_key or not secret_key:
            raise BaiduOpenApiError("请先填写百度网盘开放平台 App Key 与 Secret Key")
        return {
            "url": build_baidu_oauth_authorize_url(app_key=app_key),
            "redirect_uri": "oob",
            "message": "在浏览器授权后把页面显示的授权码粘贴回来",
        }

    async def start_baidu_openapi_device_login(self) -> Dict[str, Any]:
        """官方设备码扫码登录：返回二维码 data URL 与用户码。"""
        app_key, secret_key = self._baidu_openapi_credentials()
        if not app_key or not secret_key:
            raise BaiduOpenApiError("请先填写百度开放平台 App Key 与 Secret Key")
        async with self._baidu_device_lock:
            data = await request_baidu_device_code(app_key=app_key)
            qr_data_url = ""
            qrcode_url = str(data.get("qrcode_url", "") or "").strip()
            if qrcode_url:
                try:
                    timeout = aiohttp.ClientTimeout(total=15)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(qrcode_url, headers={"User-Agent": "pan.baidu.com"}) as response:
                            if response.status == 200:
                                raw = await response.read()
                                if 0 < len(raw) <= 2 * 1024 * 1024:
                                    qr_data_url = "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
                except Exception as exc:
                    config.logger.warning("下载百度二维码失败: %s", exc)
            self._baidu_device_login = {
                "device_code": data["device_code"],
                "user_code": data["user_code"],
                "qrcode_url": qrcode_url,
                "verification_url": data.get("verification_url", ""),
                "expires_at": _now_wall_ts() + max(60, int(data.get("expires_in", 300))),
                "interval": max(5, int(data.get("interval", 5))),
                "app_key": app_key,
            }
            return {
                "stage": "waiting",
                "qr_data_url": qr_data_url,
                "qrcode_url": qrcode_url,
                "user_code": self._baidu_device_login["user_code"],
                "verification_url": self._baidu_device_login["verification_url"],
                "expires_at": self._baidu_device_login["expires_at"],
                "interval": self._baidu_device_login["interval"],
                "message": "请用百度 App / 百度网盘 App 扫码并确认授权",
            }

    async def poll_baidu_openapi_device_login(self) -> Dict[str, Any]:
        """轮询扫码结果；成功时写入 token 并返回 logged_in。"""
        async with self._baidu_device_lock:
            session = dict(self._baidu_device_login or {})
            if not session:
                return {"stage": "idle", "message": "未开始扫码登录", **self._baidu_openapi_payload()}
            if int(session.get("expires_at", 0) or 0) <= _now_wall_ts():
                self._baidu_device_login = {}
                return {"stage": "expired", "message": "二维码已过期，请重新获取", **self._baidu_openapi_payload()}

            app_key, secret_key = self._baidu_openapi_credentials()
            try:
                tokens = await poll_baidu_device_token(
                    app_key=app_key,
                    secret_key=secret_key,
                    device_code=str(session.get("device_code", "") or ""),
                )
            except BaiduOpenApiError as exc:
                diagnostics = dict(getattr(exc, "diagnostics", {}) or {})
                payload = diagnostics.get("response") if isinstance(diagnostics.get("response"), dict) else {}
                error = str(diagnostics.get("error", "") or payload.get("error", "") or "").lower()
                if error in {"authorization_pending", "slow_down", "authorization_waiting"}:
                    return {"stage": "waiting", "message": "等待手机确认授权…", "interval": session.get("interval", 5)}
                self._baidu_device_login = {}
                return {"stage": "failed", "message": str(exc), **self._baidu_openapi_payload()}

            user_account = ""
            try:
                info = await fetch_baidu_openapi_user_info(access_token=str(tokens.get("access_token", "") or ""))
                user_account = str(
                    info.get("netdisk_name") or info.get("user_name") or info.get("uk") or ""
                ).strip()
            except Exception as exc:
                config.logger.warning("Baidu device user info failed: %s", exc)
            state = self.store.baidu_openapi
            state.app_key = app_key
            state.secret_key = secret_key
            state.access_token = str(tokens.get("access_token", "") or "")
            state.refresh_token = str(tokens.get("refresh_token", "") or "")
            state.expires_at = _safe_int(tokens.get("expires_at"), 0)
            state.user_account = user_account
            state.updated_at = _now_wall_ts()
            self._baidu_device_login = {}
            await asyncio.to_thread(self.store.save)
            self._invalidate_panel_cache(all_data=True)
            return {"stage": "success", "message": "百度网盘扫码授权成功", "user_account": user_account, **self._baidu_openapi_payload()}

    async def cancel_baidu_openapi_device_login(self) -> Dict[str, Any]:
        async with self._baidu_device_lock:
            self._baidu_device_login = {}
        return {"stage": "idle", "message": "已取消扫码登录"}

    async def set_baidu_openapi_app(self, app_key: str = "", secret_key: str = "") -> Dict[str, Any]:
        normalized_key = str(app_key or "").strip()
        normalized_secret = str(secret_key or "").strip()
        if not normalized_key and not normalized_secret:
            self.store.baidu_openapi = type(self.store.baidu_openapi)()
            await asyncio.to_thread(self.store.save)
            self._invalidate_panel_cache(all_data=True)
            return {"ok": True, **self._baidu_openapi_payload()}
        if not normalized_key or not normalized_secret:
            raise BaiduOpenApiError("App Key 与 Secret Key 必须同时填写")
        state = self.store.baidu_openapi
        if state.app_key != normalized_key or state.secret_key != normalized_secret:
            state.access_token = ""
            state.refresh_token = ""
            state.expires_at = 0
            state.user_account = ""
        state.app_key = normalized_key
        state.secret_key = normalized_secret
        state.updated_at = _now_wall_ts()
        await asyncio.to_thread(self.store.save)
        self._invalidate_panel_cache(all_data=True)
        return {"ok": True, **self._baidu_openapi_payload()}

    async def exchange_baidu_openapi_code(self, code: str = "") -> Dict[str, Any]:
        normalized_code = str(code or "").strip()
        if not normalized_code:
            raise BaiduOpenApiError("请填写授权码")
        app_key, secret_key = self._baidu_openapi_credentials()
        if not app_key or not secret_key:
            raise BaiduOpenApiError("请先配置 App Key 与 Secret Key")
        tokens = await exchange_baidu_oauth_code(app_key=app_key, secret_key=secret_key, code=normalized_code)
        access_token = str(tokens.get("access_token", "") or "").strip()
        refresh_token = str(tokens.get("refresh_token", "") or "").strip()
        if not access_token or not refresh_token:
            raise BaiduOpenApiError("百度授权返回的 access_token/refresh_token 为空")
        user_account = ""
        try:
            user_info = await fetch_baidu_openapi_user_info(access_token=access_token)
            user_account = str(user_info.get("netdisk_name") or user_info.get("user_name") or user_info.get("uk") or "").strip()
        except Exception as exc:
            config.logger.warning("Baidu OpenAPI user info failed: %s", exc)
        state = self.store.baidu_openapi
        state.app_key = app_key
        state.secret_key = secret_key
        state.access_token = access_token
        state.refresh_token = refresh_token
        state.expires_at = _safe_int(tokens.get("expires_at"), 0)
        state.user_account = user_account
        state.updated_at = _now_wall_ts()
        await asyncio.to_thread(self.store.save)
        self._invalidate_panel_cache(all_data=True)
        return {"ok": True, "user_account": user_account, "message": "百度网盘授权成功", **self._baidu_openapi_payload()}

    async def clear_baidu_openapi_login(self) -> Dict[str, Any]:
        state = self.store.baidu_openapi
        state.access_token = ""
        state.refresh_token = ""
        state.expires_at = 0
        state.user_account = ""
        state.updated_at = _now_wall_ts()
        await asyncio.to_thread(self.store.save)
        self._invalidate_panel_cache(all_data=True)
        return {"ok": True, **self._baidu_openapi_payload()}

    async def check_baidu_openapi_login_state(self) -> Dict[str, Any]:
        state = self.store.baidu_openapi
        app_key, secret_key = self._baidu_openapi_credentials()
        configured = bool(app_key and secret_key)
        if not configured:
            return {"configured": False, "logged_in": False, "user_account": "", "expires_at": 0, "message": "未配置百度开放平台应用"}
        if not state.logged_in:
            return {"configured": True, "logged_in": False, "user_account": "", "expires_at": 0, "message": "已配置应用，待授权"}
        token = state.access_token
        try:
            if state.expires_at and state.expires_at <= _now_wall_ts() + 60:
                token = await self._ensure_baidu_openapi_access_token(force_refresh=True)
            account = state.user_account
            if not account:
                info = await fetch_baidu_openapi_user_info(access_token=token)
                account = str(info.get("netdisk_name") or info.get("user_name") or info.get("uk") or "").strip()
                state.user_account = account
                await asyncio.to_thread(self.store.save)
            return {"configured": True, "logged_in": True, "user_account": account, "expires_at": state.expires_at, "message": "登录态有效"}
        except Exception as exc:
            return {"configured": True, "logged_in": False, "user_account": state.user_account, "expires_at": state.expires_at, "message": f"百度授权失效：{exc}"}

    async def _ensure_baidu_openapi_access_token(self, force_refresh: bool = False) -> str:
        state = self.store.baidu_openapi
        app_key, secret_key = self._baidu_openapi_credentials()
        if not app_key or not secret_key:
            raise BaiduOpenApiError("请先在设置中配置百度网盘开放平台 App Key/Secret Key")
        if not state.logged_in:
            raise BaiduOpenApiError("请先完成百度网盘授权（设置 → 百度网盘 OpenAPI）")
        now = _now_wall_ts()
        if not force_refresh and state.access_token and (not state.expires_at or state.expires_at > now + 300):
            return state.access_token
        refresh_token = str(state.refresh_token or os.getenv("FREEDECKCY_BAIDU_OPENAPI_REFRESH_TOKEN", "") or "").strip()
        if not refresh_token:
            raise BaiduOpenApiError("百度 refresh_token 为空，请重新授权")
        tokens = await refresh_baidu_oauth_token(app_key=app_key, secret_key=secret_key, refresh_token=refresh_token)
        access_token = str(tokens.get("access_token", "") or "").strip()
        if not access_token:
            raise BaiduOpenApiError("百度刷新 access_token 失败")
        state.access_token = access_token
        state.refresh_token = str(tokens.get("refresh_token", "") or refresh_token).strip()
        state.expires_at = _safe_int(tokens.get("expires_at"), 0)
        state.updated_at = now
        await asyncio.to_thread(self.store.save)
        return access_token

    async def save_manual_cookie(self, cookie: str, user_account: str = "") -> Dict[str, Any]:
        """手动保存 cookie。"""
        normalized = (cookie or "").strip()
        if not normalized:
            raise TianyiApiError("cookie 不能为空")
        account = (user_account or "").strip()
        if not account:
            fetched = await get_user_account(normalized)
            if not fetched:
                raise TianyiApiError("cookie 无效，请重新获取")
            account = fetched
        self.store.set_login(normalized, account)
        await self._set_capture_state(
            stage="completed",
            message=f"已保存 cookie，登录账号：{account}",
            reason="",
            next_action="",
            user_account=account,
            diagnostics={"source": "manual_cookie"},
        )
        return {"logged_in": True, "user_account": account, "message": "登录态已保存"}

    async def clear_login(self) -> Dict[str, Any]:
        """清理本地登录态。"""
        self.store.clear_login()
        self._invalidate_panel_cache(all_data=True)
        async with self._qr_login_lock:
            await self._close_qr_login_context_locked()
            await self._set_qr_login_state(
                session_id="",
                stage="idle",
                message="未开始",
                reason="",
                next_action="",
                user_account="",
                image_url="",
                expires_at=0,
                diagnostics={},
            )
        await self._set_capture_state(
            stage="idle",
            message="未开始",
            reason="",
            next_action="",
            user_account="",
            diagnostics={},
        )
        await self._cancel_cloud_save_task()
        await self._set_cloud_save_state(
            stage="idle",
            running=False,
            message="未开始",
            reason="login_cleared",
            progress=0.0,
            current_game="",
            total_games=0,
            processed_games=0,
            uploaded=0,
            skipped=0,
            failed=0,
            results=[],
            diagnostics={},
        )
        return {"logged_in": False, "user_account": "", "message": "已清理登录态"}

    def _installed_record_session_key(self, record: TianyiInstalledGame) -> str:
        """为已安装记录构造稳定会话键。"""
        game_id = str(record.game_id or "").strip()
        install_path = self._normalize_dir_path(str(record.install_path or "").strip())
        if game_id and install_path:
            return f"{game_id}|{install_path}"
        if game_id:
            return f"{game_id}|"
        if install_path:
            return f"|{install_path}"
        return ""

    def _derive_tianyi_launch_token(self, game_id: str) -> str:
        """与 steam_shortcuts 使用同一规则构造 freedeckCY 启动 token。"""
        token = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(game_id or "")).strip("_")
        return token or "game"

    def _snapshot_record_playtime(self, record: TianyiInstalledGame, *, now_ts: Optional[int] = None) -> Dict[str, Any]:
        """输出记录的游玩时长快照（包含进行中的会话增量）。"""
        now = max(0, _safe_int(now_ts, 0)) or _now_wall_ts()
        total_seconds = max(0, _safe_int(record.playtime_seconds, 0))
        sessions = max(0, _safe_int(record.playtime_sessions, 0))
        last_played_at = max(0, _safe_int(record.playtime_last_played_at, 0))
        active_started_at = max(0, _safe_int(record.playtime_active_started_at, 0))
        active_app_id = max(0, _safe_int(record.playtime_active_app_id, 0))

        active_seconds = 0
        active = bool(active_started_at > 0 and active_app_id > 0)
        if active and now > active_started_at:
            active_seconds = min(now - active_started_at, PLAYTIME_SESSION_MAX_SECONDS)
        snapshot_seconds = total_seconds + active_seconds
        if active_seconds > 0:
            last_played_at = max(last_played_at, now)

        return {
            "seconds": snapshot_seconds,
            "sessions": sessions,
            "last_played_at": last_played_at,
            "active": active,
            "active_app_id": active_app_id,
            "active_started_at": active_started_at,
            "active_seconds_included": active_seconds,
        }

    async def _resolve_installed_record_by_app_id(self, app_id_unsigned: int) -> Optional[TianyiInstalledGame]:
        """按 Steam AppID 定位已安装记录，必要时自动回填 appid 缓存。"""
        target_app_id = max(0, int(app_id_unsigned or 0))
        if target_app_id <= 0:
            return None

        records = list(self.store.installed_games or [])
        for record in records:
            if max(0, _safe_int(record.steam_app_id, 0)) == target_app_id:
                return record

        # 慢路径优化：一次性读取 shortcuts，避免对每条记录重复解析 shortcuts.vdf。
        shortcut_index: Dict[str, Any] = {}
        try:
            shortcut_index = await asyncio.to_thread(list_tianyi_shortcuts_sync)
        except Exception:
            shortcut_index = {}

        by_token = shortcut_index.get("by_token", {}) if isinstance(shortcut_index, dict) else {}
        if isinstance(by_token, dict) and by_token:
            matched: Optional[TianyiInstalledGame] = None
            needs_save = False

            for record in records:
                game_id = str(record.game_id or "").strip()
                if not game_id:
                    continue
                token = self._derive_tianyi_launch_token(game_id)
                row = by_token.get(token)
                if not isinstance(row, dict):
                    continue
                resolved_app_id = max(0, _safe_int(row.get("appid_unsigned"), 0))
                if resolved_app_id <= 0:
                    continue
                if resolved_app_id != max(0, _safe_int(record.steam_app_id, 0)):
                    record.steam_app_id = resolved_app_id
                    needs_save = True
                if resolved_app_id == target_app_id and matched is None:
                    matched = record

            if needs_save:
                await asyncio.to_thread(self.store.save)
            return matched

        matched: Optional[TianyiInstalledGame] = None
        needs_save = False
        for record in records:
            game_id = str(record.game_id or "").strip()
            if not game_id:
                continue
            try:
                shortcut = await asyncio.to_thread(resolve_tianyi_shortcut_sync, game_id=game_id)
            except Exception:
                continue
            if not bool(shortcut.get("ok")):
                continue
            resolved_app_id = max(0, _safe_int(shortcut.get("appid_unsigned"), 0))
            if resolved_app_id <= 0:
                continue
            if resolved_app_id != max(0, _safe_int(record.steam_app_id, 0)):
                record.steam_app_id = resolved_app_id
                needs_save = True
            if resolved_app_id == target_app_id and matched is None:
                matched = record

        if needs_save:
            await asyncio.to_thread(self.store.save)
        return matched

    async def _recover_playtime_sessions_from_store(self) -> None:
        """从 state.json 恢复进行中的游玩会话。"""
        now = _now_wall_ts()
        recovered: Dict[str, Dict[str, Any]] = {}
        stale_updated = False

        for record in list(self.store.installed_games or []):
            active_started_at = max(0, _safe_int(record.playtime_active_started_at, 0))
            active_app_id = max(0, _safe_int(record.playtime_active_app_id, 0))
            if active_started_at <= 0 or active_app_id <= 0:
                continue

            age = max(0, now - active_started_at)
            if age > PLAYTIME_STALE_SESSION_SECONDS:
                record.playtime_active_started_at = 0
                record.playtime_active_app_id = 0
                stale_updated = True
                continue

            key = self._installed_record_session_key(record)
            if not key:
                continue
            recovered[key] = {
                "game_id": str(record.game_id or "").strip(),
                "install_path": str(record.install_path or "").strip(),
                "app_id": active_app_id,
                "started_at": active_started_at,
            }

        async with self._playtime_lock:
            self._playtime_sessions = recovered

        if stale_updated:
            await asyncio.to_thread(self.store.save)
            self._invalidate_panel_cache(installed=True)

    async def _finalize_active_playtime_sessions(self, *, reason: str = "") -> None:
        """在服务关闭等场景结算所有活跃游玩会话。"""
        del reason  # 预留给后续诊断扩展。

        async with self._playtime_lock:
            active_sessions = dict(self._playtime_sessions or {})
            self._playtime_sessions = {}

        if not active_sessions:
            return

        now = _now_wall_ts()
        changed = False
        for session in active_sessions.values():
            game_id = str(session.get("game_id", "") or "").strip()
            install_path = str(session.get("install_path", "") or "").strip()
            started_at = max(0, _safe_int(session.get("started_at"), 0))

            record = self._find_installed_record(game_id=game_id, install_path=install_path)
            if record is None and game_id:
                record = self._find_installed_record(game_id=game_id)
            if record is None:
                continue

            record_changed = False
            if started_at > 0 and now > started_at:
                added = min(now - started_at, PLAYTIME_SESSION_MAX_SECONDS)
                if added > 0:
                    record.playtime_seconds = max(0, _safe_int(record.playtime_seconds, 0)) + added
                    record.playtime_sessions = max(0, _safe_int(record.playtime_sessions, 0)) + 1
                    record.playtime_last_played_at = max(0, now)
                    record_changed = True
            if max(0, _safe_int(record.playtime_active_started_at, 0)) > 0:
                record.playtime_active_started_at = 0
                record_changed = True
            if max(0, _safe_int(record.playtime_active_app_id, 0)) > 0:
                record.playtime_active_app_id = 0
                record_changed = True

            if record_changed:
                record.updated_at = now
                changed = True

        if changed:
            await asyncio.to_thread(self.store.save)
            self._invalidate_panel_cache(installed=True)

    async def record_game_action(self, *, phase: str, app_id: str, action_name: str = "") -> Dict[str, Any]:
        """记录 Steam 启动/退出事件并累计游玩时长。"""
        normalized_phase = str(phase or "").strip().lower()
        if normalized_phase not in {"start", "end"}:
            return {"accepted": False, "reason": "invalid_phase", "message": "无效的 phase"}

        app_id_unsigned = max(0, _safe_int(app_id, 0))
        if app_id_unsigned <= 0:
            return {"accepted": False, "reason": "invalid_app_id", "message": "无效的 app_id"}

        normalized_action = str(action_name or "").strip()
        if normalized_phase == "start" and normalized_action and normalized_action != "LaunchApp":
            return {
                "accepted": False,
                "reason": "ignored_action",
                "message": "非 LaunchApp 事件已忽略",
                "action_name": normalized_action,
            }

        record = await self._resolve_installed_record_by_app_id(app_id_unsigned)
        if record is None:
            return {
                "accepted": False,
                "reason": "app_not_managed",
                "message": "该 AppID 不属于 freedeckCY 安装记录",
                "app_id": app_id_unsigned,
            }

        session_key = self._installed_record_session_key(record)
        if not session_key:
            return {"accepted": False, "reason": "record_invalid", "message": "已安装记录无效"}

        now = _now_wall_ts()
        changed = False
        added_seconds = 0
        now_record = self._find_installed_record(game_id=record.game_id, install_path=record.install_path) or record
        duplicate_start_grace_seconds = 5

        async with self._playtime_lock:
            existing = dict(self._playtime_sessions.get(session_key) or {})
            started_at = max(
                0,
                _safe_int(
                    existing.get("started_at"),
                    _safe_int(now_record.playtime_active_started_at, 0),
                ),
            )

            if normalized_phase == "start":
                if started_at > 0 and now > started_at:
                    elapsed = now - started_at
                    if elapsed > duplicate_start_grace_seconds:
                        added_seconds = min(elapsed, PLAYTIME_SESSION_MAX_SECONDS)
                        if added_seconds > 0:
                            now_record.playtime_seconds = max(0, _safe_int(now_record.playtime_seconds, 0)) + added_seconds
                            now_record.playtime_sessions = max(0, _safe_int(now_record.playtime_sessions, 0)) + 1
                            now_record.playtime_last_played_at = max(0, now)
                            changed = True

                self._playtime_sessions[session_key] = {
                    "game_id": str(now_record.game_id or "").strip(),
                    "install_path": str(now_record.install_path or "").strip(),
                    "app_id": app_id_unsigned,
                    "started_at": now,
                }
                if max(0, _safe_int(now_record.playtime_active_started_at, 0)) != now:
                    now_record.playtime_active_started_at = now
                    changed = True
                if max(0, _safe_int(now_record.playtime_active_app_id, 0)) != app_id_unsigned:
                    now_record.playtime_active_app_id = app_id_unsigned
                    changed = True
                if max(0, _safe_int(now_record.steam_app_id, 0)) != app_id_unsigned:
                    now_record.steam_app_id = app_id_unsigned
                    changed = True
            else:
                if started_at > 0 and now > started_at:
                    added_seconds = min(now - started_at, PLAYTIME_SESSION_MAX_SECONDS)
                    if added_seconds > 0:
                        now_record.playtime_seconds = max(0, _safe_int(now_record.playtime_seconds, 0)) + added_seconds
                        now_record.playtime_sessions = max(0, _safe_int(now_record.playtime_sessions, 0)) + 1
                        now_record.playtime_last_played_at = max(0, now)
                        changed = True

                if session_key in self._playtime_sessions:
                    self._playtime_sessions.pop(session_key, None)
                if max(0, _safe_int(now_record.playtime_active_started_at, 0)) > 0:
                    now_record.playtime_active_started_at = 0
                    changed = True
                if max(0, _safe_int(now_record.playtime_active_app_id, 0)) > 0:
                    now_record.playtime_active_app_id = 0
                    changed = True
                if max(0, _safe_int(now_record.steam_app_id, 0)) != app_id_unsigned:
                    now_record.steam_app_id = app_id_unsigned
                    changed = True

            if changed:
                now_record.updated_at = now
                await asyncio.to_thread(self.store.save)

        if changed:
            self._invalidate_panel_cache(installed=True)

        playtime = self._snapshot_record_playtime(now_record, now_ts=now)
        return {
            "accepted": True,
            "reason": "",
            "message": "记录成功",
            "phase": normalized_phase,
            "app_id": app_id_unsigned,
            "game_id": str(now_record.game_id or "").strip(),
            "game_title": str(now_record.game_title or "").strip(),
            "playtime_seconds": max(0, _safe_int(playtime.get("seconds"), 0)),
            "playtime_sessions": max(0, _safe_int(playtime.get("sessions"), 0)),
            "added_seconds": max(0, int(added_seconds or 0)),
        }

    async def get_library_game_time_stats(self, *, app_id: str = "", title: str = "") -> Dict[str, Any]:
        """按 Steam 库页面游戏返回 freedeckCY 时长数据。"""
        app_id_unsigned = max(0, _safe_int(app_id, 0))
        title_raw = str(title or "").strip()
        title_norm = self._normalize_cover_text(title_raw)

        record: Optional[TianyiInstalledGame] = None
        # 先按 AppID 精确匹配，避免 Steam 原有游戏与插件游戏同名时被误判。
        if app_id_unsigned > 0:
            record = await self._resolve_installed_record_by_app_id(app_id_unsigned)
        if record is None and title_norm:
            for candidate in list(self.store.installed_games or []):
                candidate_title = str(candidate.game_title or "").strip()
                if not candidate_title:
                    continue
                candidate_norm = self._normalize_cover_text(candidate_title)
                if not candidate_norm:
                    continue
                if candidate_norm == title_norm or candidate_norm in title_norm or title_norm in candidate_norm:
                    record = candidate
                    break

        if record is None:
            # Steam 原有游戏：不查询 HLTB、不返回时长/日期，前端也不会插入任何块。
            return {
                "managed": False,
                "reason": "not_managed",
                "message": "当前库页面游戏不属于 freedeckCY 安装记录",
                "app_id": app_id_unsigned,
                "title": title_raw,
                "my_playtime_seconds": 0,
                "my_playtime_text": "-",
                "main_story_hours": 0.0,
                "main_story_time_text": "-",
                "total_hours": 0.0,
                "total_time_text": "-",
            }

        game_id = str(record.game_id or "").strip()
        game_title = str(record.game_title or title_raw or "").strip()
        catalog_item = self.catalog.get_by_game_id(game_id) if game_id else None
        categories = str(getattr(catalog_item, "categories", "") or "")
        hltb_app_id = max(0, _safe_int(record.steam_app_id, 0))

        playtime = self._snapshot_record_playtime(record)
        my_playtime_seconds = max(0, _safe_int(playtime.get("seconds"), 0))
        my_playtime_text = _format_playtime_seconds(my_playtime_seconds)

        hltb: Dict[str, Any] = {}
        try:
            hltb = await self.resolve_hltb_stats(
                game_id=game_id,
                title=game_title,
                categories=categories,
                app_id=hltb_app_id,
                force_refresh=False,
            )
        except Exception as exc:
            config.logger.warning("库页面查询 HLTB 时长失败: game=%s error=%s", game_title, exc)

        main_story_hours = 0.0
        total_hours = 0.0
        try:
            main_story_hours = max(0.0, float(hltb.get("main_story_hours", 0.0) or 0.0))
        except Exception:
            main_story_hours = 0.0
        try:
            total_hours = max(0.0, float(hltb.get("total_hours", 0.0) or 0.0))
        except Exception:
            total_hours = 0.0

        return {
            "managed": True,
            "reason": "",
            "message": "",
            "app_id": hltb_app_id or app_id_unsigned,
            "game_id": game_id,
            "title": game_title,
            "my_playtime_seconds": my_playtime_seconds,
            "my_playtime_text": my_playtime_text,
            "my_playtime_active": bool(playtime.get("active")),
            "main_story_hours": main_story_hours,
            "main_story_time_text": str(hltb.get("main_story_text", "") or "").strip() or "-",
            "total_hours": total_hours,
            "total_time_text": str(hltb.get("total_time_text", "") or "").strip() or "-",
        }

    async def start_qr_login(self) -> Dict[str, Any]:
        """启动后端二维码登录会话。"""
        async with self._qr_login_lock:
            await self._close_qr_login_context_locked()

            login_ok, account, message = await self.check_login_state()
            if login_ok and account:
                await self._set_qr_login_state(
                    session_id="",
                    stage="completed",
                    message=f"检测到有效登录态：{account}",
                    reason="",
                    next_action="",
                    user_account=account,
                    image_url="",
                    expires_at=0,
                    diagnostics={"source": "stored_cookie", "check_message": message},
                )
                return dict(self._qr_login_state)

            session_id = uuid.uuid4().hex
            created_at = _now_wall_ts()
            expires_at = created_at + QR_LOGIN_SESSION_TIMEOUT_SECONDS
            timeout = aiohttp.ClientTimeout(total=QR_LOGIN_HTTP_TIMEOUT_SECONDS)
            ssl_context, tls_diag = self._build_qr_ssl_context()
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            client = aiohttp.ClientSession(
                timeout=timeout,
                cookie_jar=aiohttp.CookieJar(unsafe=True),
                connector=connector,
            )
            context: Dict[str, Any] = {
                "session_id": session_id,
                "client": client,
                "created_at": created_at,
                "expires_at": expires_at,
                "poll_count": 0,
                "tls_diag": tls_diag,
            }

            try:
                bootstrap = await self._bootstrap_qr_login_context(context)
                context.update(bootstrap)
                context["image_url"] = f"/api/tianyi/login/qr/image?session_id={session_id}&_ts={_now_wall_ts()}"
                self._qr_login_context = context

                await self._set_qr_login_state(
                    session_id=session_id,
                    stage="running",
                    message="请使用天翼云盘 App 扫码登录",
                    reason="waiting_scan",
                    next_action="scan_qr",
                    user_account="",
                    image_url=str(context.get("image_url", "")),
                    expires_at=expires_at,
                    diagnostics={
                        "source": "qr_api",
                        "created_at": created_at,
                        "expires_at": expires_at,
                        "req_id": str(context.get("req_id", "")),
                        "tls": tls_diag,
                    },
                )
                return dict(self._qr_login_state)
            except Exception as exc:
                await self._safe_close_client_session(client)
                error_text = str(exc)
                reason = "qr_start_failed"
                if "CERTIFICATE_VERIFY_FAILED" in error_text.upper() or "certificate verify failed" in error_text.lower():
                    reason = "ssl_verify_failed"
                await self._set_qr_login_state(
                    session_id="",
                    stage="failed",
                    message=f"二维码会话启动失败：{exc}",
                    reason=reason,
                    next_action="retry",
                    user_account="",
                    image_url="",
                    expires_at=0,
                    diagnostics={
                        "exception": error_text,
                        "tls": tls_diag,
                    },
                )
                return dict(self._qr_login_state)

    async def poll_qr_login(self, session_id: str = "") -> Dict[str, Any]:
        """轮询二维码登录状态。"""
        async with self._qr_login_lock:
            context = self._qr_login_context
            if context is None:
                return dict(self._qr_login_state)

            current_id = str(context.get("session_id", ""))
            if session_id and session_id != current_id:
                return dict(self._qr_login_state)

            expires_at = int(context.get("expires_at") or 0)
            now_ts = _now_wall_ts()
            if expires_at > 0 and now_ts >= expires_at:
                await self._set_qr_login_state(
                    session_id=current_id,
                    stage="failed",
                    message="二维码已过期，请刷新后重试",
                    reason="qr_expired",
                    next_action="retry",
                    user_account="",
                    image_url=str(context.get("image_url", "")),
                    expires_at=expires_at,
                    diagnostics={"poll_count": int(context.get("poll_count") or 0)},
                )
                await self._close_qr_login_context_locked()
                return dict(self._qr_login_state)

            client = context.get("client")
            if not isinstance(client, aiohttp.ClientSession):
                await self._set_qr_login_state(
                    session_id=current_id,
                    stage="failed",
                    message="二维码会话异常，请刷新后重试",
                    reason="qr_context_invalid",
                    next_action="retry",
                    user_account="",
                    image_url=str(context.get("image_url", "")),
                    expires_at=expires_at,
                    diagnostics={},
                )
                await self._close_qr_login_context_locked()
                return dict(self._qr_login_state)

            state_payload = dict(context.get("state_payload") or {})
            now_ms = str(int(time.time() * 1000))
            state_payload["date"] = now_ms
            state_payload["timeStamp"] = now_ms

            req_id = str(context.get("req_id", ""))
            lt = str(context.get("lt", ""))
            login_page_url = str(context.get("login_page_url", ""))
            headers = self._build_qr_headers(req_id=req_id, lt=lt, referer=login_page_url)

            try:
                async with client.post(
                    "https://open.e.189.cn/api/logbox/oauth2/qrcodeLoginState.do",
                    data=state_payload,
                    headers=headers,
                ) as resp:
                    raw_text = await resp.text()
                    if resp.status >= 400:
                        raise TianyiApiError(f"二维码状态接口失败 status={resp.status}")
            except Exception as exc:
                await self._set_qr_login_state(
                    session_id=current_id,
                    stage="running",
                    message="状态轮询失败，正在重试...",
                    reason="poll_exception",
                    next_action="wait",
                    user_account="",
                    image_url=str(context.get("image_url", "")),
                    expires_at=expires_at,
                    diagnostics={"exception": str(exc), "poll_count": int(context.get("poll_count") or 0)},
                )
                return dict(self._qr_login_state)

            try:
                payload = self._parse_json_like_text(raw_text)
            except Exception as exc:
                await self._set_qr_login_state(
                    session_id=current_id,
                    stage="running",
                    message="状态解析失败，正在重试...",
                    reason="poll_parse_failed",
                    next_action="wait",
                    user_account="",
                    image_url=str(context.get("image_url", "")),
                    expires_at=expires_at,
                    diagnostics={"exception": str(exc), "raw": str(raw_text)[:320]},
                )
                return dict(self._qr_login_state)

            status_code = self._extract_qr_status_code(payload)
            context["poll_count"] = int(context.get("poll_count") or 0) + 1

            poll_diag: Dict[str, Any] = {
                "poll_count": int(context.get("poll_count") or 0),
                "status_code": status_code,
            }

            if status_code == QR_STATUS_SUCCESS:
                redirect_url = self._extract_qr_redirect_url(payload)
                account, cookie, verify_reason = await self._finalize_qr_login_success(
                    context=context,
                    redirect_url=redirect_url,
                )
                poll_diag["redirect_url"] = redirect_url
                if verify_reason:
                    poll_diag["verify_reason"] = verify_reason

                if account and cookie:
                    self.store.set_login(cookie, account)
                    await self._set_qr_login_state(
                        session_id=current_id,
                        stage="completed",
                        message=f"登录成功：{account}",
                        reason="",
                        next_action="",
                        user_account=account,
                        image_url=str(context.get("image_url", "")),
                        expires_at=expires_at,
                        diagnostics=poll_diag,
                    )
                    await self._close_qr_login_context_locked()
                    return dict(self._qr_login_state)

                await self._set_qr_login_state(
                    session_id=current_id,
                    stage="failed",
                    message="扫码已确认，但未拿到有效登录态",
                    reason="qr_cookie_verify_failed",
                    next_action="retry",
                    user_account="",
                    image_url=str(context.get("image_url", "")),
                    expires_at=expires_at,
                    diagnostics=poll_diag,
                )
                await self._close_qr_login_context_locked()
                return dict(self._qr_login_state)

            if status_code in QR_STATUS_EXPIRED:
                await self._set_qr_login_state(
                    session_id=current_id,
                    stage="failed",
                    message="二维码已失效，请刷新后重试",
                    reason="qr_expired",
                    next_action="retry",
                    user_account="",
                    image_url=str(context.get("image_url", "")),
                    expires_at=expires_at,
                    diagnostics=poll_diag,
                )
                await self._close_qr_login_context_locked()
                return dict(self._qr_login_state)

            if status_code in QR_STATUS_SCANNED_WAIT_CONFIRM:
                await self._set_qr_login_state(
                    session_id=current_id,
                    stage="running",
                    message="已扫码，请在手机上确认登录",
                    reason="await_confirm",
                    next_action="confirm_on_phone",
                    user_account="",
                    image_url=str(context.get("image_url", "")),
                    expires_at=expires_at,
                    diagnostics=poll_diag,
                )
                return dict(self._qr_login_state)

            if status_code in QR_STATUS_NEED_EXTRA_VERIFY:
                await self._set_qr_login_state(
                    session_id=current_id,
                    stage="failed",
                    message="账号触发二次验证，请在天翼云官方页面完成验证后重试",
                    reason="need_extra_verify",
                    next_action="open_official_login",
                    user_account="",
                    image_url=str(context.get("image_url", "")),
                    expires_at=expires_at,
                    diagnostics=poll_diag,
                )
                return dict(self._qr_login_state)

            if status_code in QR_STATUS_WAITING:
                await self._set_qr_login_state(
                    session_id=current_id,
                    stage="running",
                    message="等待扫码登录",
                    reason="waiting_scan",
                    next_action="scan_qr",
                    user_account="",
                    image_url=str(context.get("image_url", "")),
                    expires_at=expires_at,
                    diagnostics=poll_diag,
                )
                return dict(self._qr_login_state)

            await self._set_qr_login_state(
                session_id=current_id,
                stage="running",
                message="正在等待登录状态更新...",
                reason="polling",
                next_action="wait",
                user_account="",
                image_url=str(context.get("image_url", "")),
                expires_at=expires_at,
                diagnostics=poll_diag,
            )
            return dict(self._qr_login_state)

    async def stop_qr_login(self, session_id: str = "") -> Dict[str, Any]:
        """停止二维码登录会话。"""
        async with self._qr_login_lock:
            context = self._qr_login_context
            if context is not None:
                current_id = str(context.get("session_id", ""))
                if not session_id or session_id == current_id:
                    await self._close_qr_login_context_locked()
                    await self._set_qr_login_state(
                        session_id=current_id,
                        stage="stopped",
                        message="已停止二维码登录",
                        reason="qr_stopped",
                        next_action="retry",
                        user_account="",
                        image_url="",
                        expires_at=0,
                        diagnostics={},
                    )
                    return dict(self._qr_login_state)
            return dict(self._qr_login_state)

    async def get_qr_login_state(self) -> Dict[str, Any]:
        """读取二维码登录状态。"""
        return dict(self._qr_login_state)

    async def get_qr_login_image(self, session_id: str = "") -> Tuple[bytes, str]:
        """读取二维码图片二进制。"""
        async with self._qr_login_lock:
            context = self._qr_login_context
            if context is None:
                raise TianyiApiError("二维码会话不存在，请先刷新二维码")

            current_id = str(context.get("session_id", ""))
            if session_id and session_id != current_id:
                raise TianyiApiError("二维码会话已更新，请刷新页面")

            client = context.get("client")
            if not isinstance(client, aiohttp.ClientSession):
                raise TianyiApiError("二维码会话异常，请刷新二维码")

            image_remote_url = str(context.get("image_remote_url", ""))
            if not image_remote_url:
                raise TianyiApiError("二维码地址缺失，请刷新二维码")

            headers = self._build_qr_headers(
                req_id=str(context.get("req_id", "")),
                lt=str(context.get("lt", "")),
                referer=str(context.get("login_page_url", "")),
            )
            async with client.get(image_remote_url, headers=headers) as resp:
                if resp.status >= 400:
                    raise TianyiApiError(f"二维码图片获取失败 status={resp.status}")
                content_type = str(resp.headers.get("Content-Type", "image/jpeg") or "image/jpeg")
                body = await resp.read()
                if not body:
                    raise TianyiApiError("二维码图片为空，请刷新二维码")
                return body, content_type

    async def start_login_capture(self, timeout_seconds: int = CAPTURE_DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
        """启动自动 Cookie 采集流程。"""
        try:
            timeout = int(timeout_seconds or CAPTURE_DEFAULT_TIMEOUT_SECONDS)
        except Exception:
            timeout = CAPTURE_DEFAULT_TIMEOUT_SECONDS
        timeout = max(CAPTURE_MIN_TIMEOUT_SECONDS, min(CAPTURE_MAX_TIMEOUT_SECONDS, timeout))

        async with self._capture_lock:
            if self._capture_task and not self._capture_task.done():
                self._capture_task.cancel()
                try:
                    await self._capture_task
                except BaseException:
                    pass

            quick_diag: Dict[str, Any] = {"timeout_seconds": timeout}
            await self._set_capture_state(
                stage="starting",
                message="正在检查当前登录态...",
                reason="",
                next_action="",
                user_account="",
                diagnostics=quick_diag,
            )

            # 优先走本地已存登录态的快速校验，避免用户已登录却仍等待超时。
            login_ok, account, login_message = await self.check_login_state()
            quick_diag["check_message"] = login_message
            if login_ok and account:
                await self._set_capture_state(
                    stage="completed",
                    message=f"检测到有效登录态：{account}",
                    reason="",
                    next_action="",
                    user_account=account,
                    diagnostics={"source": "stored_cookie", "check_message": login_message},
                    source_attempts=["stored_cookie"],
                    success_source="stored_cookie",
                    source_diagnostics={
                        "stored_cookie": {
                            "ok": True,
                            "reason": "",
                            "message": login_message,
                        }
                    },
                )
                return dict(self._capture_state)

            # 入页后立即执行一次双通道采集尝试，命中即马上回传并落盘。
            initial_attempt = await self._attempt_capture_sources_once()
            quick_diag["initial_reason"] = str(initial_attempt.get("reason", ""))
            quick_diag["main_landing_detected"] = bool(initial_attempt.get("main_landing_detected"))
            quick_diag["source_diagnostics"] = dict(initial_attempt.get("source_diagnostics") or {})

            if bool(initial_attempt.get("success")):
                resolved_cookie = str(initial_attempt.get("cookie", "") or "")
                resolved_account = str(initial_attempt.get("account", "") or "")
                success_source = str(initial_attempt.get("success_source", "") or "")
                if resolved_cookie and resolved_account:
                    self.store.set_login(resolved_cookie, resolved_account)
                    await self._set_capture_state(
                        stage="completed",
                        message=f"登录成功：{resolved_account}",
                        reason="",
                        next_action="",
                        user_account=resolved_account,
                        diagnostics={
                            "source": "initial_dual_source_probe",
                            "success_source": success_source,
                            "main_landing_detected": bool(initial_attempt.get("main_landing_detected")),
                        },
                        source_attempts=list(initial_attempt.get("source_attempts") or []),
                        success_source=success_source,
                        source_diagnostics=dict(initial_attempt.get("source_diagnostics") or {}),
                    )
                    return dict(self._capture_state)

            await self._set_capture_state(
                stage="starting",
                message="正在启动持续采集，请在网页完成扫码登录...",
                reason="",
                next_action="",
                user_account="",
                diagnostics=quick_diag,
                source_attempts=list(initial_attempt.get("source_attempts") or []),
                success_source="",
                source_diagnostics=dict(initial_attempt.get("source_diagnostics") or {}),
            )
            self._capture_task = asyncio.create_task(
                self._capture_loop(timeout_seconds=timeout, seed_diagnostics=quick_diag),
                name="freedeckcy_tianyi_capture",
            )
            return dict(self._capture_state)

    async def stop_login_capture(self) -> Dict[str, Any]:
        """停止自动 Cookie 采集流程。"""
        async with self._capture_lock:
            if self._capture_task and not self._capture_task.done():
                self._capture_task.cancel()
                try:
                    await self._capture_task
                except BaseException:
                    pass
            self._capture_task = None

            await self._set_capture_state(
                stage="stopped",
                message="已停止自动采集，可改用手动 Cookie",
                reason="capture_stopped",
                next_action="manual_cookie",
                user_account="",
                diagnostics={},
            )
            return dict(self._capture_state)

    async def get_login_capture_status(self) -> Dict[str, Any]:
        """读取当前自动采集状态。"""
        return dict(self._capture_state)

    @staticmethod
    def _parse_catalog_rows(data: bytes) -> list[Dict[str, str]]:
        try:
            import io

            text = data.decode("utf-8-sig")
            return list(csv.DictReader(io.StringIO(text)))
        except Exception:
            return []

    @staticmethod
    def _validate_catalog_csv(data: bytes) -> Dict[str, Any]:
        """校验服务器目录 CSV，返回 (ok, message, row_count)。"""
        if not data:
            return {"ok": False, "message": "服务器返回空文件"}
        if len(data) > 64 * 1024 * 1024:
            return {"ok": False, "message": "目录 CSV 超过 64MB 限制"}
        try:
            text = data.decode("utf-8-sig")
        except Exception as exc:
            return {"ok": False, "message": f"目录 CSV 不是 UTF-8: {exc}"}
        import csv as _csv
        import io as _io

        reader = _csv.DictReader(_io.StringIO(text))
        required = {"game_id", "title", "down_url", "openpath"}
        fields = set(reader.fieldnames or [])
        missing = required - fields
        if missing:
            return {"ok": False, "message": f"目录 CSV 缺少字段: {', '.join(sorted(missing))}"}
        count = 0
        for row in reader:
            if not str(row.get("game_id", "") or "").strip():
                continue
            if not str(row.get("title", "") or "").strip():
                return {"ok": False, "message": f"第 {count + 2} 行标题为空"}
            if not str(row.get("down_url", "") or "").strip().startswith(("http://", "https://")):
                return {"ok": False, "message": f"第 {count + 2} 行分享链接非法"}
            count += 1
        if count < 10:
            return {"ok": False, "message": f"目录 CSV 有效条目过少（{count}）"}
        return {"ok": True, "message": "", "row_count": count}

    async def _fetch_catalog_csv(
        self, url: str, *, etag: str = "", last_modified: str = ""
    ) -> tuple[Optional[bytes], Dict[str, str], int]:
        """条件下载目录 CSV；304 时 data=None。"""
        headers: Dict[str, str] = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        timeout = aiohttp.ClientTimeout(total=60, connect=15)
        connector = aiohttp.TCPConnector(ssl=build_tls_context())
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.get(url, headers=headers) as response:
                response_headers = {str(k): str(v) for k, v in response.headers.items()}
                if response.status == 304:
                    return None, response_headers, 304
                if response.status >= 400:
                    raise RuntimeError(f"下载目录失败 HTTP {response.status}")
                data = await response.read()
        return data, response_headers, 200

    async def _fetch_catalog_signature(self, url: str) -> str:
        """下载目录签名文件 catalog.csv.sig。"""
        signature_url = str(url or "").rstrip("/") + ".sig"
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(ssl=build_tls_context())
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.get(signature_url) as response:
                if response.status != 200:
                    raise RuntimeError(f"目录签名下载失败 HTTP {response.status}")
                data = await response.read()
        if len(data) > 4096:
            raise RuntimeError("目录签名文件异常过大")
        return data.decode("ascii", errors="strict").strip()

    async def _download_catalog_csv(self, url: str) -> bytes:
        """兼容旧调用：无条件下载。"""
        data, _headers, _status = await self._fetch_catalog_csv(url)
        if data is None:
            raise RuntimeError("服务器返回 304 但没有本地目录")
        return data

    @staticmethod
    def _catalog_update_meta_path(state_dir: str) -> str:
        return os.path.join(state_dir, "catalog.csv.meta.json")

    def get_catalog_update(self, max_items: int = 12) -> Dict[str, Any]:
        """返回上次目录更新的新增游戏（用于最近更新 shelf/提醒）。"""
        state_dir = os.path.dirname(self.store.state_file)
        meta_path = self._catalog_update_meta_path(state_dir)
        payload: Dict[str, Any] = {}
        if os.path.isfile(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as fh:
                    loaded = json.load(fh)
                if isinstance(loaded, dict):
                    payload = loaded
            except Exception:
                payload = {}
        items = []
        for item in list(payload.get("added") or [])[: max(0, int(max_items or 12))]:
            if not isinstance(item, dict):
                continue
            game_id = str(item.get("game_id", "") or "").strip()
            if not game_id:
                continue
            entry = self.catalog.get_by_game_id(game_id)
            if entry is None:
                continue
            items.append(
                {
                    "game_id": entry.game_id,
                    "title": entry.title,
                    "platform": entry.platform,
                    "categories": entry.categories,
                    "size_text": _format_size_bytes(max(0, int(entry.size_bytes or 0))) if int(entry.size_bytes or 0) > 0 else "",
                    "cover_url": entry.cover_url,
                    "cover_portrait_url": entry.cover_portrait_url,
                }
            )
        return {
            "updated_at": int(payload.get("updated_at", 0) or 0),
            "added_count": int(payload.get("added_count", 0) or 0),
            "added": list(payload.get("added") or []),
            "items": items,
        }

    async def update_catalog_csv(self, url: str = "") -> Dict[str, Any]:
        """检查服务器目录是否比本地新，只有变化才下载替换。"""
        target_url = str(url or "").strip()
        if not target_url:
            target_url = str(getattr(self.store.settings, "catalog_url", "") or "").strip()
        if not target_url:
            target_url = str(os.environ.get("FREEDECKCY_CATALOG_CSV_URL", "") or "").strip()
        if not target_url:
            target_url = str(getattr(config, "DEFAULT_CATALOG_CSV_URL", "") or "").strip()
        if not target_url.startswith(("http://", "https://")):
            raise ValueError("目录 CSV 下载地址无效")

        state_dir = os.path.dirname(self.store.state_file)
        os.makedirs(state_dir, exist_ok=True)
        target_path = os.path.join(state_dir, "catalog.csv")
        meta_path = f"{target_path}.meta.json"
        local_meta: Dict[str, Any] = {}
        if os.path.isfile(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as fh:
                    loaded = json.load(fh)
                if isinstance(loaded, dict):
                    local_meta = loaded
            except Exception:
                local_meta = {}

        local_exists = os.path.isfile(target_path)
        etag = str(local_meta.get("etag", "") or "") if local_exists else ""
        last_modified = str(local_meta.get("last_modified", "") or "") if local_exists else ""
        data, headers, status = await self._fetch_catalog_csv(
            target_url, etag=etag, last_modified=last_modified
        )
        local_sha = str(local_meta.get("sha256", "") or "")
        if not local_sha and local_exists:
            try:
                local_sha = hashlib.sha256(Path(target_path).read_bytes()).hexdigest()
            except Exception:
                local_sha = ""

        if status == 304 and local_exists:
            return {
                "updated": False,
                "reason": "not_modified",
                "path": _redact_text(target_path),
                "total": len(getattr(self.catalog, "entries", []) or []),
                "source": str(getattr(self.catalog, "source", "") or "csv"),
                "server_last_modified": headers.get("Last-Modified", last_modified),
                "local_updated_at": int(os.path.getmtime(target_path)),
                "message": "服务器目录未变化",
            }

        if data is None:
            raise RuntimeError("服务器返回 304 但没有本地目录")
        validation = self._validate_catalog_csv(data)
        if not validation.get("ok"):
            raise ValueError(str(validation.get("message") or "目录 CSV 校验失败"))
        signature = await self._fetch_catalog_signature(target_url)
        if not catalog_signature.verify_signature(data, signature):
            raise RuntimeError("目录签名校验失败，已保留本地目录")
        server_sha = hashlib.sha256(data).hexdigest()
        old_ids: set[str] = set()
        if local_exists:
            try:
                with open(target_path, "rb") as fh:
                    old_rows = self._parse_catalog_rows(fh.read())
                old_ids = {str(row.get("game_id", "") or "").strip() for row in old_rows if str(row.get("game_id", "") or "").strip()}
            except Exception:
                old_ids = set()
        added: list[Dict[str, str]] = []
        if local_exists:
            for row in self._parse_catalog_rows(data):
                game_id = str(row.get("game_id", "") or "").strip()
                if not game_id or game_id in old_ids:
                    continue
                added.append({"game_id": game_id, "title": str(row.get("title", "") or "").strip()})
        added_meta = {
            "added_count": len(added),
            "added": added[:500],
        }
        if local_exists and local_sha and server_sha == local_sha:
            preserved_added = local_meta.get("added") if local_meta.get("sha256") == server_sha else []
            preserved_count = local_meta.get("added_count", 0) if local_meta.get("sha256") == server_sha else 0
            new_meta = {
                "url": target_url,
                "etag": headers.get("ETag", ""),
                "last_modified": headers.get("Last-Modified", ""),
                "sha256": server_sha,
                "updated_at": int(time.time()),
                "rows": int(validation.get("row_count", 0) or 0),
                "added_count": int(preserved_count or 0),
                "added": list(preserved_added or [])[:500],
            }
            self._write_catalog_meta(meta_path, new_meta)
            return {
                "updated": False,
                "reason": "already_latest",
                "path": _redact_text(target_path),
                "total": len(getattr(self.catalog, "entries", []) or []),
                "source": str(getattr(self.catalog, "source", "") or "csv"),
                "server_last_modified": headers.get("Last-Modified", ""),
                "local_updated_at": int(os.path.getmtime(target_path)),
                "message": "本地已是最新目录",
            }

        fd, temp_path = tempfile.mkstemp(prefix=".catalog_", suffix=".csv", dir=state_dir)
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(temp_path, target_path)
        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
        try:
            os.chmod(target_path, 0o644)
        except Exception:
            pass
        new_meta = {
            "url": target_url,
            "etag": headers.get("ETag", ""),
            "last_modified": headers.get("Last-Modified", ""),
            "sha256": server_sha,
            "updated_at": int(time.time()),
            "rows": int(validation.get("row_count", 0) or 0),
            **added_meta,
        }
        self._write_catalog_meta(meta_path, new_meta)
        # 本地下载的 CSV 优先；清掉内存中的 JSON 覆盖，立即生效。
        self.catalog.csv_path = target_path
        self.catalog.json_path = ""
        await asyncio.to_thread(self.catalog.load)
        self._invalidate_panel_cache()
        if int(added_meta.get("added_count", 0) or 0) > 0:
            self._catalog_update_notice = {
                "added_count": int(added_meta.get("added_count", 0) or 0),
                "titles": [str(item.get("title", "") or "") for item in list(added_meta.get("added") or [])[:5]],
                "updated_at": int(time.time()),
            }
        return {
            "updated": True,
            "reason": "updated",
            "path": _redact_text(target_path),
            "total": len(getattr(self.catalog, "entries", []) or []),
            "source": str(getattr(self.catalog, "source", "") or "csv"),
            "rows": int(validation.get("row_count", 0) or 0),
            "updated_at": int(time.time()),
            "server_last_modified": headers.get("Last-Modified", ""),
            "sha256": server_sha,
            "url": target_url,
            "added_count": int(added_meta["added_count"]),
            "added": list(added_meta["added"]),
            "message": "已下载服务器最新目录",
        }

    @staticmethod
    def _write_catalog_meta(path: str, payload: Dict[str, Any]) -> None:
        temp_path = f"{path}.tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(temp_path, path)
        except Exception as exc:
            config.logger.warning("写入目录元数据失败 %s: %s", path, exc)
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    async def refresh_catalog(self) -> Dict[str, Any]:
        """强制刷新游戏目录（删除远程缓存后重新加载）。"""
        cache_path = str(getattr(self.catalog, "json_cache_path", "") or "").strip()
        if cache_path and os.path.isfile(cache_path):
            try:
                os.remove(cache_path)
            except Exception as exc:
                config.logger.warning("删除目录远程缓存失败 %s: %s", cache_path, exc)
        await asyncio.to_thread(self.catalog.load)
        self._invalidate_panel_cache()
        return {
            "source": str(getattr(self.catalog, "source", "") or ""),
            "total": len(getattr(self.catalog, "entries", []) or []),
            "invalid": int(getattr(self.catalog, "invalid_rows", 0) or 0),
        }

    async def list_catalog(
        self,
        query: str,
        page: int,
        page_size: int,
        platform: str = "",
        category: str = "",
        sort: str = "",
    ) -> Dict[str, Any]:
        """查询游戏目录（支持平台/分类筛选与排序）。"""
        # page_size 默认跟随设置，但允许前端覆盖。
        if page_size <= 0:
            page_size = self.store.settings.page_size
        allowed = ["pc", *available_platforms()]
        return self.catalog.list(
            query=query,
            page=page,
            page_size=page_size,
            platform=platform,
            category=category,
            sort=sort,
            allowed_platforms=allowed,
        )

    def _load_cover_cache(self) -> None:
        """加载封面磁盘缓存（仅保留未过期项）。"""
        path = str(getattr(self, "_cover_cache_path", "") or "").strip()
        if not path or not os.path.isfile(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception as exc:
            config.logger.warning("读取封面缓存失败: %s", exc)
            return
        if not isinstance(payload, dict):
            return
        now_ts = _now_wall_ts()
        loaded = 0
        for key, value in payload.items():
            if not isinstance(value, dict):
                continue
            try:
                expires_at = int(value.get("expires_at", 0) or 0)
            except Exception:
                expires_at = 0
            if expires_at <= now_ts:
                continue
            self._catalog_cover_cache[str(key)] = value
            loaded += 1
        if loaded:
            config.logger.info("已加载封面缓存: %s 条", loaded)

    def _save_cover_cache(self) -> None:
        """把封面缓存原子写回磁盘。"""
        path = str(getattr(self, "_cover_cache_path", "") or "").strip()
        if not path:
            return
        try:
            payload = {
                key: value
                for key, value in self._catalog_cover_cache.items()
                if isinstance(value, dict)
            }
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp_path = f"{path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False)
            try:
                os.chmod(tmp_path, 0o600)
            except Exception:
                pass
            os.replace(tmp_path, path)
        except Exception as exc:
            config.logger.warning("写入封面缓存失败: %s", exc)

    def _catalog_entry_cover(self, game_id: str) -> Dict[str, Any]:
        """目录/封面索引里自带的封面（无需联网）。"""
        target = str(game_id or "").strip()
        if not target:
            return {}
        entry = self.catalog.get_by_game_id(target)
        if entry is None:
            return {}
        app_id = max(0, _safe_int(entry.steam_appid, 0))
        cover_url = str(entry.cover_url or "").strip()
        square_url = str(entry.cover_portrait_url or "").strip()
        if app_id > 0 and (not cover_url or not square_url):
            if not square_url:
                square_url = self._build_store_square_cover_url(app_id)
            if not cover_url:
                cover_url = f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{app_id}/header.jpg"
        if not cover_url and not square_url:
            return {}
        return {
            "cover_url": cover_url,
            "square_cover_url": square_url,
            "source": "catalog",
            "matched_title": str(entry.title or ""),
            "app_id": app_id,
            "protondb_tier": "",
            "cached": True,
        }

    async def resolve_catalog_cover(
        self,
        *,
        game_id: str = "",
        title: str = "",
        categories: str = "",
    ) -> Dict[str, Any]:
        """按游戏标题解析封面 URL（优先 Steam 商店），并做内存缓存。"""
        static_cover = self._catalog_entry_cover(game_id)
        if static_cover:
            return static_cover

        cache_key = str(game_id or title or "").strip().lower()
        now_ts = _now_wall_ts()
        if not cache_key:
            return {
                "cover_url": "",
                "square_cover_url": "",
                "source": "",
                "matched_title": "",
                "app_id": 0,
                "protondb_tier": "",
                "cached": False,
            }

        async with self._catalog_cover_lock:
            cached = self._catalog_cover_cache.get(cache_key)
            if isinstance(cached, dict) and int(cached.get("expires_at", 0)) > now_ts:
                return {
                    "cover_url": str(cached.get("cover_url", "") or ""),
                    "square_cover_url": str(cached.get("square_cover_url", "") or ""),
                    "source": str(cached.get("source", "") or ""),
                    "matched_title": str(cached.get("matched_title", "") or ""),
                    "app_id": _safe_int(cached.get("app_id"), 0),
                    "protondb_tier": str(cached.get("protondb_tier", "") or ""),
                    "cached": True,
                }

        cover_url = ""
        square_cover_url = ""
        source = ""
        matched_title = ""
        app_id = 0
        protondb_tier = ""
        terms = self._build_catalog_cover_terms(title=title, categories=categories)

        if terms:
            try:
                ssl_context, _ = self._build_qr_ssl_context()
                timeout = aiohttp.ClientTimeout(total=CATALOG_COVER_HTTP_TIMEOUT_SECONDS)
                connector = aiohttp.TCPConnector(ssl=ssl_context)
                async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                    for term in terms:
                        search_url = str(
                            URL("https://store.steampowered.com/api/storesearch/").with_query(
                                {"term": term, "l": "schinese", "cc": "cn"}
                            )
                        )
                        headers = {
                            "Accept": "application/json, text/plain, */*",
                            "User-Agent": "Mozilla/5.0 (freedeckCY/1.0; +https://cloud.189.cn)",
                            "Referer": "https://store.steampowered.com/",
                        }
                        try:
                            async with session.get(search_url, headers=headers) as resp:
                                if int(resp.status) != 200:
                                    continue
                                payload = await resp.json(content_type=None)
                        except Exception:
                            continue

                        items = payload.get("items") if isinstance(payload, dict) else []
                        resolved = self._pick_catalog_cover_candidate(term=term, items=items)
                        if not resolved:
                            continue
                        cover_url = str(resolved.get("cover_url", "") or "").strip()
                        matched_title = str(resolved.get("matched_title", "") or "").strip()
                        source = str(resolved.get("source", "") or "").strip()
                        app_id = _safe_int(resolved.get("app_id"), 0)
                        if cover_url or app_id > 0:
                            square_cover_url = self._build_store_square_cover_url(app_id)
                            if app_id > 0:
                                proton_summary = await self._fetch_protondb_summary(session=session, app_id=app_id)
                                protondb_tier = str(proton_summary.get("tier", "") or "").strip()
                            break
            except Exception as exc:
                config.logger.warning("解析游戏封面失败: title=%s error=%s", title, exc)

        has_positive_payload = bool(cover_url or square_cover_url or app_id > 0 or protondb_tier)
        expires_at = now_ts + (
            CATALOG_COVER_CACHE_TTL_SECONDS if has_positive_payload else CATALOG_COVER_NEGATIVE_TTL_SECONDS
        )
        cache_value = {
            "cover_url": cover_url,
            "square_cover_url": square_cover_url,
            "source": source,
            "matched_title": matched_title,
            "app_id": int(app_id),
            "protondb_tier": protondb_tier,
            "expires_at": int(expires_at),
        }
        async with self._catalog_cover_lock:
            self._catalog_cover_cache[cache_key] = cache_value
        try:
            await asyncio.to_thread(self._save_cover_cache)
        except Exception as exc:
            config.logger.warning("保存封面缓存失败: %s", exc)

        return {
            "cover_url": cover_url,
            "square_cover_url": square_cover_url,
            "source": source,
            "matched_title": matched_title,
            "app_id": int(app_id),
            "protondb_tier": protondb_tier,
            "cached": False,
        }

    def _build_catalog_cover_terms(self, *, title: str, categories: str = "") -> List[str]:
        """生成封面检索候选词，优先英文名。"""
        raw_title = str(title or "").strip()
        raw_categories = str(categories or "").strip()
        if not raw_title:
            return []

        def sanitize(value: str) -> str:
            text = str(value or "").strip()
            text = re.sub(r"\s+", " ", text)
            text = re.sub(r"(?i)\b(v|ver|version)\s*\d+(?:\.\d+){0,3}\b", "", text).strip()
            text = re.sub(r"\s+", " ", text).strip()
            return text

        parts = [sanitize(raw_title)]
        parts.extend(sanitize(part) for part in re.split(r"[\/／|｜]+", raw_title))
        if raw_categories:
            parts.extend(sanitize(part) for part in re.split(r"[\/／|｜,，]+", raw_categories))

        ascii_parts = [part for part in parts if re.search(r"[A-Za-z]", part)]
        ordered: List[str] = []
        for value in ascii_parts + parts:
            if not value:
                continue
            if value not in ordered:
                ordered.append(value)
        return ordered[:6]

    def _normalize_cover_text(self, value: str) -> str:
        text = str(value or "").lower()
        text = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", text)
        return " ".join(text.split())

    def _pick_catalog_cover_candidate(self, *, term: str, items: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(items, list) or not items:
            return None

        query_norm = self._normalize_cover_text(term)
        query_tokens = set(query_norm.split()) if query_norm else set()
        best_score = -1
        best: Optional[Dict[str, str]] = None

        for item in items[:CATALOG_COVER_SEARCH_LIMIT]:
            if not isinstance(item, dict):
                continue
            cover_url = self._extract_store_cover_url(item)
            app_id = self._extract_store_app_id(item)
            if not cover_url:
                continue
            name = str(item.get("name", "") or "").strip()
            name_norm = self._normalize_cover_text(name)
            name_tokens = set(name_norm.split()) if name_norm else set()

            score = 1
            if query_norm and name_norm:
                if query_norm == name_norm:
                    score += 120
                elif query_norm in name_norm or name_norm in query_norm:
                    score += 80
            if query_tokens and name_tokens:
                score += len(query_tokens & name_tokens) * 12

            if score > best_score:
                best_score = score
                best = {
                    "cover_url": cover_url,
                    "matched_title": name,
                    "source": "steam_store_search",
                    "app_id": int(app_id),
                }

        return best

    def _extract_store_app_id(self, item: Dict[str, Any]) -> int:
        app_id = _safe_int(item.get("id"), 0)
        if app_id <= 0:
            app_id = _safe_int(item.get("appid"), 0)
        return app_id

    def _extract_store_cover_url(self, item: Dict[str, Any]) -> str:
        for key in (
            "large_capsule_image",
            "header_image",
            "capsule_image",
            "small_capsule_image",
            "tiny_image",
        ):
            value = str(item.get(key, "") or "").strip()
            if value.startswith("http://") or value.startswith("https://"):
                return value

        app_id = self._extract_store_app_id(item)
        if app_id > 0:
            return f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{app_id}/capsule_616x353.jpg"
        return ""

    def get_cover_proxy_base(self) -> str:
        """返回封面代理 URL 前缀；本地服务未运行时返回空。"""
        if not bool(getattr(self.plugin, "server_running", False)):
            return ""
        port = int(getattr(self.plugin, "server_port", 0) or 0)
        if port <= 0:
            return ""
        return f"http://127.0.0.1:{port}/api/tianyi/cover-image"

    async def fetch_cover_image(self, url: str, *, max_bytes: int = 8 * 1024 * 1024) -> Tuple[bytes, str]:
        """拉取并磁盘缓存封面图（仅允许 Steam/封面 CDN 域名）。"""
        raw = str(url or "").strip()
        if not raw or len(raw) > 2048:
            raise ValueError("封面 URL 无效")
        parsed = urlparse(raw)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("封面 URL 协议不支持")
        host = str(parsed.hostname or "").strip().lower().rstrip(".")
        allowed_suffixes = (
            "steamstatic.com",
            "steamcdn-a.akamaihd.net",
            "akamaihd.net",
            "steamgriddb.com",
            "steamusercontent.com",
        )
        if not any(host == suffix or host.endswith("." + suffix) for suffix in allowed_suffixes):
            raise ValueError("封面域名不允许")
        state_dir = os.path.dirname(self.store.state_file)
        cache_dir = os.path.join(state_dir, "cover_cache")
        os.makedirs(cache_dir, exist_ok=True)
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        cached_path = ""
        cached_type = ""
        for ext, content_type in ((".jpg", "image/jpeg"), (".png", "image/png"), (".webp", "image/webp"), (".gif", "image/gif")):
            candidate = os.path.join(cache_dir, digest + ext)
            if os.path.isfile(candidate):
                try:
                    if time.time() - os.path.getmtime(candidate) < 30 * 86400:
                        cached_path, cached_type = candidate, content_type
                        break
                except OSError:
                    pass
        if cached_path:
            try:
                with open(cached_path, "rb") as fh:
                    return fh.read(), cached_type
            except OSError:
                pass
        timeout = aiohttp.ClientTimeout(total=20, connect=10)
        connector = aiohttp.TCPConnector(ssl=build_tls_context())
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.get(raw, headers={"User-Agent": "freedeckCY/cover-proxy"}, allow_redirects=False) as response:
                if response.status >= 400:
                    raise RuntimeError(f"封面下载失败 HTTP {response.status}")
                content_type = str(response.headers.get("Content-Type", "") or "").split(";", 1)[0].strip().lower()
                if not content_type.startswith("image/"):
                    raise RuntimeError("服务器返回的不是图片")
                data = bytearray()
                async for chunk in response.content.iter_chunked(64 * 1024):
                    data.extend(chunk)
                    if len(data) > max_bytes:
                        raise RuntimeError("封面图片超过大小限制")
        ext = { "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif" }.get(content_type, ".jpg")
        temp_path = os.path.join(cache_dir, digest + ext + ".tmp")
        final_path = os.path.join(cache_dir, digest + ext)
        try:
            with open(temp_path, "wb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(temp_path, final_path)
        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        return bytes(data), content_type

    def _build_store_square_cover_url(self, app_id: int) -> str:
        """优先返回更适合方形裁切的 Steam 竖版素材 URL。"""
        if _safe_int(app_id, 0) <= 0:
            return ""
        app = _safe_int(app_id, 0)
        return f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{app}/library_600x900.jpg"

    async def _fetch_protondb_summary(self, *, session: aiohttp.ClientSession, app_id: int) -> Dict[str, Any]:
        """读取 ProtonDB 摘要信息。"""
        if app_id <= 0:
            return {}
        api_url = f"https://www.protondb.com/api/v1/reports/summaries/{int(app_id)}.json"
        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (freedeckCY/1.0; +https://cloud.189.cn)",
            "Referer": "https://www.protondb.com/",
        }
        try:
            timeout = aiohttp.ClientTimeout(total=PROTONDB_HTTP_TIMEOUT_SECONDS)
            async with session.get(api_url, headers=headers, timeout=timeout) as resp:
                if int(resp.status) != 200:
                    return {}
                payload = await resp.json(content_type=None)
                if not isinstance(payload, dict):
                    return {}
                tier = str(payload.get("tier", "") or "").strip()
                return {"tier": tier}
        except Exception:
            return {}

    def _build_hltb_search_payload(self, term: str) -> Dict[str, Any]:
        """构建 HLTB 搜索请求体。"""
        text = str(term or "").strip()
        words = [item for item in re.split(r"\s+", text) if item]
        if not words and text:
            words = [text]
        return {
            "searchType": "games",
            "searchTerms": words[:8],
            "searchPage": 1,
            "size": 20,
            "searchOptions": {
                "games": {
                    "userId": 0,
                    "platform": "",
                    "sortCategory": "popular",
                    "rangeCategory": "main",
                    "rangeTime": {"min": 0, "max": 0},
                    "gameplay": {
                        "perspective": "",
                        "flow": "",
                        "genre": "",
                        "difficulty": "",
                    },
                    "rangeYear": {"min": "", "max": ""},
                    "modifier": "hide_dlc",
                },
                "users": {"sortCategory": "postcount"},
                "lists": {"sortCategory": "follows"},
                "filter": "",
                "sort": 0,
                "randomizer": 0,
            },
            "useCache": True,
        }

    async def _fetch_hltb_token(self, *, session: aiohttp.ClientSession, headers: Dict[str, str]) -> str:
        """获取 HLTB finder API 的短期鉴权 token。"""
        init_url = f"{HLTB_TOKEN_URL}?t={int(time.time() * 1000)}"
        try:
            async with session.get(init_url, headers=headers) as resp:
                if int(resp.status) != 200:
                    return ""
                data = await resp.json(content_type=None)
        except Exception:
            return ""
        if not isinstance(data, dict):
            return ""
        token = str(data.get("token", "") or "").strip()
        return token

    async def _post_hltb_search(
        self,
        *,
        session: aiohttp.ClientSession,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        token: str,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """请求 HLTB finder 搜索接口。"""
        req_headers = dict(headers)
        if token:
            req_headers["x-auth-token"] = token
        try:
            async with session.post(HLTB_SEARCH_URL, headers=req_headers, json=payload) as resp:
                status = int(resp.status)
                if status != 200:
                    return status, []
                data = await resp.json(content_type=None)
        except Exception:
            return 0, []
        rows = data.get("data") if isinstance(data, dict) else []
        if isinstance(rows, list):
            return 200, [item for item in rows if isinstance(item, dict)]
        return 200, []

    async def _post_hltb_search_legacy(
        self,
        *,
        session: aiohttp.ClientSession,
        payload: Dict[str, Any],
        headers: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """兼容旧版 HLTB /api/search 接口。"""
        try:
            async with session.post(HLTB_LEGACY_SEARCH_URL, headers=headers, json=payload) as resp:
                if int(resp.status) != 200:
                    return []
                data = await resp.json(content_type=None)
        except Exception:
            return []
        rows = data.get("data") if isinstance(data, dict) else []
        if isinstance(rows, list):
            return [item for item in rows if isinstance(item, dict)]
        return []

    def _pick_hltb_candidate(
        self,
        *,
        title: str,
        term: str,
        app_id: int,
        rows: Any,
    ) -> Optional[Dict[str, Any]]:
        """从 HLTB 搜索结果中选取最佳候选。"""
        if not isinstance(rows, list) or not rows:
            return None

        query_norm = self._normalize_cover_text(title or term)
        query_tokens = set(query_norm.split()) if query_norm else set()
        best_score = -1
        best_item: Optional[Dict[str, Any]] = None

        for item in rows[:HLTB_SEARCH_LIMIT]:
            if not isinstance(item, dict):
                continue
            game_name = str(item.get("game_name", "") or "").strip()
            if not game_name:
                continue

            candidate_app_id = _safe_int(item.get("profile_steam"), 0)
            name_norm = self._normalize_cover_text(game_name)
            name_tokens = set(name_norm.split()) if name_norm else set()

            score = 1
            if app_id > 0 and candidate_app_id == app_id:
                score += 260
            if query_norm and name_norm:
                if query_norm == name_norm:
                    score += 120
                elif query_norm in name_norm or name_norm in query_norm:
                    score += 80
            if query_tokens and name_tokens:
                score += len(query_tokens & name_tokens) * 14
            score += min(20, max(0, _safe_int(item.get("comp_all_count"), 0)) // 500)

            if score > best_score:
                best_score = score
                best_item = dict(item)

        return best_item

    async def resolve_hltb_stats(
        self,
        *,
        game_id: str = "",
        title: str = "",
        categories: str = "",
        app_id: int = 0,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """查询并缓存 HLTB 时长数据。"""
        cache_key = str(game_id or title or "").strip().lower()
        now_ts = _now_wall_ts()
        if not cache_key or not str(title or "").strip():
            return {
                "main_story_hours": 0.0,
                "main_story_text": "-",
                "total_hours": 0.0,
                "total_time_text": "-",
                "hltb_game_id": 0,
                "matched_title": "",
                "source_term": "",
                "cached": False,
            }

        if not force_refresh:
            async with self._hltb_lock:
                cached = self._hltb_cache.get(cache_key)
                if isinstance(cached, dict) and _safe_int(cached.get("expires_at"), 0) > now_ts:
                    main_hours = float(cached.get("main_story_hours", 0.0) or 0.0)
                    total_hours = float(cached.get("total_hours", 0.0) or 0.0)
                    return {
                        "main_story_hours": main_hours,
                        "main_story_text": _format_hours_value(main_hours),
                        "total_hours": total_hours,
                        "total_time_text": _format_hours_value(total_hours),
                        "hltb_game_id": _safe_int(cached.get("hltb_game_id"), 0),
                        "matched_title": str(cached.get("matched_title", "") or ""),
                        "source_term": str(cached.get("source_term", "") or ""),
                        "cached": True,
                    }

        main_hours = 0.0
        total_hours = 0.0
        hltb_game_id = 0
        matched_title = ""
        source_term = ""
        terms = self._build_catalog_cover_terms(title=title, categories=categories)
        if not terms:
            terms = [str(title or "").strip()]

        if terms:
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "Origin": "https://howlongtobeat.com",
                "Referer": "https://howlongtobeat.com/",
                "User-Agent": "Mozilla/5.0 (freedeckCY/1.0; +https://cloud.189.cn)",
            }
            try:
                timeout = aiohttp.ClientTimeout(total=HLTB_HTTP_TIMEOUT_SECONDS)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    for term in terms:
                        payload = self._build_hltb_search_payload(term)
                        rows: List[Dict[str, Any]] = []

                        # 优先走 legacy 接口（参考 hltb-for-deck），成功率与速度在 Deck 端更稳定。
                        rows = await self._post_hltb_search_legacy(
                            session=session,
                            payload=payload,
                            headers=headers,
                        )

                        if not rows:
                            token = await self._fetch_hltb_token(session=session, headers=headers)
                            status, rows = await self._post_hltb_search(
                                session=session,
                                payload=payload,
                                headers=headers,
                                token=token,
                            )
                            if status in {401, 403}:
                                token = await self._fetch_hltb_token(session=session, headers=headers)
                                if token:
                                    status, rows = await self._post_hltb_search(
                                        session=session,
                                        payload=payload,
                                        headers=headers,
                                        token=token,
                                    )

                        candidate = self._pick_hltb_candidate(
                            title=title,
                            term=term,
                            app_id=app_id,
                            rows=rows,
                        )
                        if not candidate:
                            continue

                        comp_main = max(0, _safe_int(candidate.get("comp_main"), 0))
                        comp_all = max(0, _safe_int(candidate.get("comp_all"), 0))
                        comp_100 = max(0, _safe_int(candidate.get("comp_100"), 0))
                        comp_plus = max(0, _safe_int(candidate.get("comp_plus"), 0))
                        total_seconds = comp_all or comp_100 or comp_plus or comp_main
                        main_hours = round((comp_main / 3600.0), 1) if comp_main > 0 else 0.0
                        total_hours = round((total_seconds / 3600.0), 1) if total_seconds > 0 else 0.0
                        hltb_game_id = max(0, _safe_int(candidate.get("game_id"), 0))
                        matched_title = str(candidate.get("game_name", "") or "").strip()
                        source_term = str(term or "").strip()
                        break
            except Exception as exc:
                config.logger.warning("解析 HLTB 时长失败: title=%s error=%s", title, exc)

        has_positive_payload = bool(main_hours > 0 or total_hours > 0 or hltb_game_id > 0)
        expires_at = now_ts + (
            HLTB_CACHE_TTL_SECONDS if has_positive_payload else HLTB_NEGATIVE_TTL_SECONDS
        )
        cache_value = {
            "main_story_hours": float(main_hours),
            "total_hours": float(total_hours),
            "hltb_game_id": int(hltb_game_id),
            "matched_title": matched_title,
            "source_term": source_term,
            "expires_at": int(expires_at),
        }
        async with self._hltb_lock:
            self._hltb_cache[cache_key] = cache_value

        return {
            "main_story_hours": float(main_hours),
            "main_story_text": _format_hours_value(main_hours),
            "total_hours": float(total_hours),
            "total_time_text": _format_hours_value(total_hours),
            "hltb_game_id": int(hltb_game_id),
            "matched_title": matched_title,
            "source_term": source_term,
            "cached": False,
        }

    async def get_settings(self) -> Dict[str, Any]:
        """获取下载设置（附带当前环境的 Proton 工具解析结果）。"""
        data = asdict(self.store.settings)
        try:
            steam_root = ""
            data["proton_tool_resolved"] = detect_proton_tool(steam_root)
            data["droiddeck_detected"] = is_droiddeck(steam_root)
        except Exception as exc:
            config.logger.warning("解析 Proton 工具失败: %s", exc)
        return data

    def _new_cloud_save_state(self) -> Dict[str, Any]:
        """构建云存档任务默认状态。"""
        return {
            "stage": "idle",
            "message": "未开始",
            "reason": "",
            "running": False,
            "progress": 0.0,
            "current_game": "",
            "total_games": 0,
            "processed_games": 0,
            "uploaded": 0,
            "skipped": 0,
            "failed": 0,
            "results": [],
            "diagnostics": {},
            "updated_at": _now_wall_ts(),
            "last_result": dict(self.store.cloud_save_last_result or {}),
        }

    def _copy_cloud_save_result(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """复制单游戏上传结果并规范字段。"""
        result = dict(item or {})
        result["game_id"] = str(result.get("game_id", "") or "")
        result["game_title"] = str(result.get("game_title", "") or "")
        result["game_key"] = str(result.get("game_key", "") or "")
        result["status"] = str(result.get("status", "") or "")
        result["reason"] = str(result.get("reason", "") or "")
        result["cloud_path"] = str(result.get("cloud_path", "") or "")
        source_paths = result.get("source_paths", [])
        if isinstance(source_paths, list):
            result["source_paths"] = [str(path or "") for path in source_paths if str(path or "").strip()]
        else:
            result["source_paths"] = []
        diagnostics = result.get("diagnostics", {})
        result["diagnostics"] = dict(diagnostics) if isinstance(diagnostics, dict) else {}
        return result

    def _cloud_save_state_snapshot_locked(self) -> Dict[str, Any]:
        """在已持锁场景下复制云存档状态。"""
        state = dict(self._cloud_save_state or {})
        results = state.get("results", [])
        if isinstance(results, list):
            state["results"] = [self._copy_cloud_save_result(item) for item in results if isinstance(item, dict)]
        else:
            state["results"] = []
        diagnostics = state.get("diagnostics", {})
        state["diagnostics"] = dict(diagnostics) if isinstance(diagnostics, dict) else {}
        last_result = state.get("last_result", {})
        state["last_result"] = dict(last_result) if isinstance(last_result, dict) else {}
        return state

    async def _set_cloud_save_state(self, **patch: Any) -> Dict[str, Any]:
        """更新云存档状态并返回快照。"""
        async with self._cloud_save_lock:
            state = self._cloud_save_state
            for key, value in patch.items():
                if key == "stage":
                    stage = str(value or "idle")
                    if stage not in CLOUD_SAVE_TASK_STAGES:
                        stage = "idle"
                    state["stage"] = stage
                    continue
                if key == "running":
                    state["running"] = bool(value)
                    continue
                if key == "progress":
                    try:
                        progress = float(value)
                    except Exception:
                        progress = 0.0
                    progress = max(0.0, min(100.0, progress))
                    state["progress"] = round(progress, 2)
                    continue
                if key in {"total_games", "processed_games", "uploaded", "skipped", "failed"}:
                    state[key] = max(0, _safe_int(value, 0))
                    continue
                if key in {"message", "reason", "current_game"}:
                    state[key] = str(value or "")
                    continue
                if key == "results":
                    rows = value if isinstance(value, list) else []
                    state["results"] = [self._copy_cloud_save_result(item) for item in rows if isinstance(item, dict)]
                    continue
                if key == "diagnostics":
                    state["diagnostics"] = dict(value) if isinstance(value, dict) else {}
                    continue
                if key == "last_result":
                    state["last_result"] = dict(value) if isinstance(value, dict) else {}
                    continue
                state[key] = value

            state["updated_at"] = _now_wall_ts()
            return self._cloud_save_state_snapshot_locked()

    async def _get_cloud_save_state_snapshot(self) -> Dict[str, Any]:
        """获取云存档状态快照。"""
        async with self._cloud_save_lock:
            return self._cloud_save_state_snapshot_locked()

    async def _cancel_cloud_save_task(self) -> None:
        """取消当前云存档任务（如有）。"""
        target: Optional[asyncio.Task] = None
        async with self._cloud_save_lock:
            if self._cloud_save_task and not self._cloud_save_task.done():
                target = self._cloud_save_task
            self._cloud_save_task = None

        if target is not None:
            target.cancel()
            try:
                await target
            except BaseException:
                pass

    def _new_cloud_save_restore_state(self) -> Dict[str, Any]:
        """构建云存档恢复任务默认状态。"""
        return {
            "stage": "idle",
            "message": "未开始",
            "reason": "",
            "running": False,
            "progress": 0.0,
            "target_game_id": "",
            "target_game_title": "",
            "target_game_key": "",
            "target_version": "",
            "selected_entry_ids": [],
            "selected_target_dir": "",
            "requires_confirmation": False,
            "conflict_count": 0,
            "conflict_samples": [],
            "restored_files": 0,
            "restored_entries": 0,
            "results": [],
            "diagnostics": {},
            "updated_at": _now_wall_ts(),
            "last_result": dict(self.store.cloud_save_restore_last_result or {}),
        }

    def _copy_cloud_save_restore_result(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """复制单条恢复结果并规范字段。"""
        result = dict(item or {})
        result["entry_id"] = str(result.get("entry_id", "") or "")
        result["entry_name"] = str(result.get("entry_name", "") or "")
        result["status"] = str(result.get("status", "") or "")
        result["reason"] = str(result.get("reason", "") or "")
        result["file_count"] = max(0, _safe_int(result.get("file_count"), 0))
        diagnostics = result.get("diagnostics", {})
        result["diagnostics"] = dict(diagnostics) if isinstance(diagnostics, dict) else {}
        return result

    def _cloud_save_restore_state_snapshot_locked(self) -> Dict[str, Any]:
        """在已持锁场景下复制恢复状态。"""
        state = dict(self._cloud_save_restore_state or {})
        selected_entry_ids = state.get("selected_entry_ids", [])
        if isinstance(selected_entry_ids, list):
            state["selected_entry_ids"] = [str(item or "") for item in selected_entry_ids if str(item or "").strip()]
        else:
            state["selected_entry_ids"] = []

        conflict_samples = state.get("conflict_samples", [])
        if isinstance(conflict_samples, list):
            state["conflict_samples"] = [str(item or "") for item in conflict_samples if str(item or "").strip()]
        else:
            state["conflict_samples"] = []

        results = state.get("results", [])
        if isinstance(results, list):
            state["results"] = [
                self._copy_cloud_save_restore_result(item)
                for item in results
                if isinstance(item, dict)
            ]
        else:
            state["results"] = []

        diagnostics = state.get("diagnostics", {})
        state["diagnostics"] = dict(diagnostics) if isinstance(diagnostics, dict) else {}
        last_result = state.get("last_result", {})
        state["last_result"] = dict(last_result) if isinstance(last_result, dict) else {}
        return state

    async def _set_cloud_save_restore_state(self, **patch: Any) -> Dict[str, Any]:
        """更新恢复状态并返回快照。"""
        async with self._cloud_save_restore_lock:
            state = self._cloud_save_restore_state
            for key, value in patch.items():
                if key == "stage":
                    stage = str(value or "idle")
                    if stage not in CLOUD_SAVE_RESTORE_TASK_STAGES:
                        stage = "idle"
                    state["stage"] = stage
                    continue
                if key == "running":
                    state["running"] = bool(value)
                    continue
                if key == "progress":
                    try:
                        progress = float(value)
                    except Exception:
                        progress = 0.0
                    state["progress"] = max(0.0, min(100.0, round(progress, 2)))
                    continue
                if key in {"message", "reason", "target_game_id", "target_game_title", "target_game_key", "target_version", "selected_target_dir"}:
                    state[key] = str(value or "")
                    continue
                if key in {"requires_confirmation"}:
                    state[key] = bool(value)
                    continue
                if key in {"conflict_count", "restored_files", "restored_entries"}:
                    state[key] = max(0, _safe_int(value, 0))
                    continue
                if key == "selected_entry_ids":
                    rows = value if isinstance(value, list) else []
                    state["selected_entry_ids"] = [str(item or "") for item in rows if str(item or "").strip()]
                    continue
                if key == "conflict_samples":
                    rows = value if isinstance(value, list) else []
                    state["conflict_samples"] = [str(item or "") for item in rows if str(item or "").strip()]
                    continue
                if key == "results":
                    rows = value if isinstance(value, list) else []
                    state["results"] = [
                        self._copy_cloud_save_restore_result(item)
                        for item in rows
                        if isinstance(item, dict)
                    ]
                    continue
                if key == "diagnostics":
                    state["diagnostics"] = dict(value) if isinstance(value, dict) else {}
                    continue
                if key == "last_result":
                    state["last_result"] = dict(value) if isinstance(value, dict) else {}
                    continue
                state[key] = value

            state["updated_at"] = _now_wall_ts()
            return self._cloud_save_restore_state_snapshot_locked()

    async def _get_cloud_save_restore_state_snapshot(self) -> Dict[str, Any]:
        """获取云存档恢复状态快照。"""
        async with self._cloud_save_restore_lock:
            return self._cloud_save_restore_state_snapshot_locked()

    async def _clear_cloud_save_restore_plan(self) -> None:
        """清理恢复计划临时资源。"""
        async with self._cloud_save_restore_lock:
            plan = dict(self._cloud_save_restore_plan or {})
            self._cloud_save_restore_plan = {}
        self._cleanup_cloud_save_temp_paths(list(plan.get("temp_paths") or []))

    async def get_cloud_save_upload_status(self) -> Dict[str, Any]:
        """返回云存档上传任务状态。"""
        return {"state": await self._get_cloud_save_state_snapshot()}

    async def start_cloud_save_upload(self, *, game_ids: Optional[Sequence[str]] = None) -> Dict[str, Any]:
        """启动云存档上传任务；可只上传指定游戏。"""
        login_ok, account, _message = await self.check_login_state()
        if not login_ok:
            raise TianyiApiError("未登录，请先登录天翼云账号")

        cookie = str(self.store.login.cookie or "").strip()
        if not cookie:
            raise TianyiApiError("缺少有效登录态，请重新登录")

        async with self._cloud_save_lock:
            task = self._cloud_save_task
            if task is not None and task.done():
                self._cloud_save_task = None
                task = None

            if task is not None:
                return {
                    "accepted": False,
                    "message": "已有云存档上传任务正在运行",
                    "state": self._cloud_save_state_snapshot_locked(),
                }

            self._cloud_save_state = self._new_cloud_save_state()
            self._cloud_save_state.update(
                {
                    "stage": "scanning",
                    "message": "正在准备云存档上传任务",
                    "reason": "",
                    "running": True,
                    "progress": 0.0,
                    "current_game": "",
                    "diagnostics": {"user_account": account},
                    "updated_at": _now_wall_ts(),
                }
            )
            self._cloud_save_task = asyncio.create_task(
                self._run_cloud_save_upload_task(
                    cookie=cookie,
                    user_account=account,
                    game_ids=list(game_ids or []),
                ),
                name="freedeckcy-cloud-save-upload",
            )
            snapshot = self._cloud_save_state_snapshot_locked()

        return {
            "accepted": True,
            "message": "云存档上传任务已启动",
            "state": snapshot,
        }

    async def get_cloud_save_restore_status(self) -> Dict[str, Any]:
        """返回云存档恢复任务状态。"""
        return {"state": await self._get_cloud_save_restore_state_snapshot()}

    async def list_cloud_save_restore_options(self) -> Dict[str, Any]:
        """列出可恢复的云存档版本（按游戏分组）。"""
        login_ok, _account, _message = await self.check_login_state()
        if not login_ok:
            raise TianyiApiError("未登录，请先登录天翼云账号")

        cookie = str(self.store.login.cookie or "").strip()
        if not cookie:
            raise TianyiApiError("缺少有效登录态，请重新登录")

        await self._set_cloud_save_restore_state(
            stage="listing",
            running=True,
            message="正在拉取云存档版本列表",
            reason="",
            progress=0.0,
            diagnostics={},
        )

        games = self._collect_cloud_restore_games()
        grouped: List[Dict[str, Any]] = []
        diagnostics: List[Dict[str, Any]] = []

        try:
            total = len(games)
            for index, game in enumerate(games, start=1):
                game_id = str(game.get("game_id", "") or "").strip()
                game_title = str(game.get("game_title", "") or "").strip() or "未命名游戏"
                game_key = str(game.get("game_key", "") or "").strip()

                item: Dict[str, Any] = {
                    "game_id": game_id,
                    "game_title": game_title,
                    "game_key": game_key,
                    "versions": [],
                    "available": False,
                    "reason": "",
                }

                try:
                    listed = await list_cloud_archives(cookie=cookie, remote_folder_parts=[game_key])
                    files = listed.get("files")
                    if not isinstance(files, list):
                        files = []
                    versions: List[Dict[str, Any]] = []
                    for file_row in files:
                        if not isinstance(file_row, dict):
                            continue
                        name = str(file_row.get("name", "") or "").strip()
                        if not name.lower().endswith(".7z"):
                            continue
                        ts = self._parse_cloud_save_version_timestamp(name)
                        versions.append(
                            {
                                "version_name": name,
                                "timestamp": ts,
                                "display_time": self._format_cloud_save_version_time(ts, name),
                                "size_bytes": max(0, _safe_int(file_row.get("size"), 0)),
                                "file_id": str(file_row.get("file_id", "") or ""),
                                "last_op_time": str(file_row.get("last_op_time", "") or ""),
                            }
                        )
                    versions.sort(
                        key=lambda row: (
                            -_safe_int(row.get("timestamp"), 0),
                            str(row.get("version_name", "") or ""),
                        )
                    )

                    item["versions"] = versions
                    item["available"] = bool(versions)
                    if not versions:
                        item["reason"] = "no_valid_versions"
                    diagnostics.append(
                        {
                            "game_key": game_key,
                            "exists": bool(listed.get("exists", False)),
                            "file_count": len(versions),
                            "trace": listed.get("trace", []),
                        }
                    )
                except TianyiApiError as exc:
                    item["available"] = False
                    item["reason"] = "list_failed"
                    diagnostics.append(
                        {
                            "game_key": game_key,
                            "error": str(exc),
                            "api_diagnostics": dict(getattr(exc, "diagnostics", {}) or {}),
                        }
                    )

                grouped.append(item)
                progress = 100.0 if total <= 0 else (float(index) / float(total)) * 100.0
                await self._set_cloud_save_restore_state(
                    stage="listing",
                    running=True,
                    message=f"正在拉取版本列表 {index}/{total}",
                    progress=progress,
                )
        finally:
            await self._set_cloud_save_restore_state(
                stage="completed",
                running=False,
                progress=100.0,
                message="云存档版本列表已更新",
                diagnostics={"games": len(grouped), "details": diagnostics},
            )

        return {
            "games": grouped,
            "updated_at": _now_wall_ts(),
        }

    async def mark_cloud_save_restore_failed(self, message: str) -> None:
        """RPC 异常兜底：把恢复状态从 running 复位为 failed。"""
        try:
            await self._set_cloud_save_restore_state(
                stage="failed",
                running=False,
                progress=100.0,
                message=str(message or "云存档恢复失败")[:500],
                reason="rpc_failed",
            )
        except Exception:
            pass

    async def list_cloud_save_restore_entries(
        self,
        *,
        game_id: str,
        game_key: str,
        game_title: str,
        version_name: str,
    ) -> Dict[str, Any]:
        """读取指定版本的可选存档项。"""
        login_ok, _account, _message = await self.check_login_state()
        if not login_ok:
            raise TianyiApiError("未登录，请先登录天翼云账号")

        cookie = str(self.store.login.cookie or "").strip()
        if not cookie:
            raise TianyiApiError("缺少有效登录态，请重新登录")

        normalized_game_id = str(game_id or "").strip()
        normalized_game_title = str(game_title or "").strip()
        normalized_game_key = str(game_key or "").strip()
        normalized_version = str(version_name or "").strip()
        if not normalized_game_key:
            normalized_game_key = self._build_cloud_save_game_key(normalized_game_id, normalized_game_title)
        if not normalized_version:
            raise TianyiApiError("缺少版本名称")

        await self._set_cloud_save_restore_state(
            stage="planning",
            running=True,
            message="正在读取存档项",
            reason="",
            progress=0.0,
            target_game_id=normalized_game_id,
            target_game_title=normalized_game_title,
            target_game_key=normalized_game_key,
            target_version=normalized_version,
            diagnostics={},
        )

        try:
            bundle = await self._download_and_extract_cloud_restore_version(
                cookie=cookie,
                game_key=normalized_game_key,
                version_name=normalized_version,
            )
        except Exception as exc:
            await self._set_cloud_save_restore_state(
                stage="failed",
                running=False,
                progress=100.0,
                message=f"读取存档项失败：{exc}",
                reason="entries_failed",
            )
            raise
        try:
            extract_dir = str(bundle.get("extract_dir", "") or "")
            entries = [dict(item) for item in list(bundle.get("entries") or []) if isinstance(item, dict)]
            entry_views: List[Dict[str, Any]] = []
            for item in entries:
                entry_id = str(item.get("entry_id", "") or "").strip()
                entry_name = str(item.get("entry_name", "") or "").strip() or entry_id
                rel_path = str(item.get("archive_rel_path", "") or "").strip().replace("\\", "/").strip("/")
                entry_root = os.path.realpath(os.path.join(extract_dir, rel_path)) if rel_path else extract_dir
                file_count = 0
                if os.path.isfile(entry_root):
                    file_count = 1
                elif os.path.isdir(entry_root):
                    for _dirpath, _dirnames, filenames in os.walk(entry_root):
                        file_count += len(filenames)
                entry_views.append(
                    {
                        "entry_id": entry_id,
                        "entry_name": entry_name,
                        "archive_rel_path": rel_path,
                        "file_count": max(0, file_count),
                    }
                )

            await self._set_cloud_save_restore_state(
                stage="ready",
                running=False,
                progress=100.0,
                message=f"已读取 {len(entry_views)} 个存档项",
                selected_entry_ids=[str(row.get("entry_id", "") or "") for row in entry_views],
                diagnostics={},
            )

            return {
                "game_id": normalized_game_id,
                "game_key": normalized_game_key,
                "game_title": normalized_game_title,
                "version_name": normalized_version,
                "entries": entry_views,
            }
        finally:
            self._cleanup_cloud_save_temp_paths([str(bundle.get("temp_dir", "") or "")])

    async def _plan_emulator_save_restore(
        self,
        *,
        bundle: Dict[str, Any],
        manifest: Dict[str, Any],
        entries: List[Dict[str, Any]],
        selected_ids: Sequence[str],
        game_id: str,
        game_key: str,
        game_title: str,
        version_name: str,
        manifest_playtime: Dict[str, Any],
    ) -> Dict[str, Any]:
        """模拟器存档恢复计划：同机恢复到原路径，跨机落到平台默认根目录。"""
        temp_dir = str(bundle.get("temp_dir", "") or "")
        extract_dir = str(bundle.get("extract_dir", "") or "")
        record = next(
            (
                item
                for item in list(self.store.installed_games or [])
                if str(item.game_id or "") == game_id
            ),
            None,
        )
        if record is None:
            self._cleanup_cloud_save_temp_paths([temp_dir])
            raise TianyiApiError("未找到该模拟器游戏的安装记录，无法恢复存档")

        roots, entry_targets = build_restore_targets(record, entries)
        if not roots:
            self._cleanup_cloud_save_temp_paths([temp_dir])
            raise TianyiApiError("未找到该平台的模拟器存档目录")
        target_dir = roots[0]
        try:
            copy_plan = self._build_restore_copy_plan(
                extract_dir=extract_dir,
                entries=entries,
                selected_entry_ids=selected_ids,
                target_dir=target_dir,
                entry_target_dirs=entry_targets,
            )
        except Exception as exc:
            self._cleanup_cloud_save_temp_paths([temp_dir])
            raise TianyiApiError(f"模拟器存档恢复计划生成失败：{exc}") from exc

        copy_pairs = list(copy_plan.get("copy_pairs") or [])
        plan_items = [dict(item) for item in list(copy_plan.get("plan_items") or []) if isinstance(item, dict)]
        conflict_count = max(0, _safe_int(copy_plan.get("conflict_count"), 0))
        conflict_samples = [str(item or "") for item in list(copy_plan.get("conflict_samples") or []) if str(item or "").strip()]
        requires_confirmation = conflict_count > 0
        plan_id = uuid.uuid4().hex
        async with self._cloud_save_restore_lock:
            self._cloud_save_restore_plan = {
                "plan_id": plan_id,
                "temp_paths": [temp_dir],
                "copy_pairs": copy_pairs,
                "plan_items": plan_items,
                "requires_confirmation": requires_confirmation,
                "conflict_count": conflict_count,
                "conflict_samples": conflict_samples,
                "target_dir": target_dir,
                "entry_target_dirs": dict(entry_targets),
                "game_id": game_id,
                "game_key": game_key,
                "game_title": game_title,
                "version_name": version_name,
                "selected_entry_ids": list(selected_ids),
                "manifest_playtime": dict(manifest_playtime or {}),
            }

        await self._set_cloud_save_restore_state(
            stage="ready",
            running=False,
            progress=100.0,
            message="模拟器存档恢复计划已生成",
            reason="",
            selected_entry_ids=list(selected_ids),
            selected_target_dir=target_dir,
            requires_confirmation=requires_confirmation,
            conflict_count=conflict_count,
            conflict_samples=conflict_samples,
            restored_files=0,
            restored_entries=0,
            diagnostics={
                "source_strategy": "emulator_saves",
                "target_candidates": roots,
                "plan_items": plan_items,
                "manifest_playtime": dict(manifest_playtime or {}),
            },
        )
        return {
            "accepted": True,
            "plan_id": plan_id,
            "message": "模拟器存档恢复计划已生成",
            "reason": "",
            "requires_confirmation": requires_confirmation,
            "conflict_count": conflict_count,
            "conflict_samples": conflict_samples,
            "target_candidates": roots,
            "selected_target_dir": target_dir,
            "selected_entry_ids": list(selected_ids),
            "available_entries": entries,
            "restorable_files": len(copy_pairs),
            "restorable_entries": len(plan_items),
        }

    async def plan_cloud_save_restore(
        self,
        *,
        game_id: str,
        game_key: str,
        game_title: str,
        version_name: str,
        selected_entry_ids: Sequence[str],
        target_dir: str = "",
    ) -> Dict[str, Any]:
        """生成恢复计划（冲突探测，不写入）。"""
        login_ok, _account, _message = await self.check_login_state()
        if not login_ok:
            raise TianyiApiError("未登录，请先登录天翼云账号")

        cookie = str(self.store.login.cookie or "").strip()
        if not cookie:
            raise TianyiApiError("缺少有效登录态，请重新登录")

        normalized_game_id = str(game_id or "").strip()
        normalized_game_title = str(game_title or "").strip() or "未命名游戏"
        normalized_game_key = str(game_key or "").strip()
        normalized_version = str(version_name or "").strip()
        if not normalized_game_key:
            normalized_game_key = self._build_cloud_save_game_key(normalized_game_id, normalized_game_title)
        if not normalized_version:
            raise TianyiApiError("缺少版本名称")

        await self._clear_cloud_save_restore_plan()
        await self._set_cloud_save_restore_state(
            stage="planning",
            running=True,
            progress=0.0,
            message="正在生成恢复计划",
            reason="",
            target_game_id=normalized_game_id,
            target_game_title=normalized_game_title,
            target_game_key=normalized_game_key,
            target_version=normalized_version,
            selected_target_dir="",
            selected_entry_ids=[],
            requires_confirmation=False,
            conflict_count=0,
            conflict_samples=[],
            restored_files=0,
            restored_entries=0,
            results=[],
            diagnostics={},
        )

        try:
            bundle = await self._download_and_extract_cloud_restore_version(
                cookie=cookie,
                game_key=normalized_game_key,
                version_name=normalized_version,
            )
        except Exception as exc:
            await self._set_cloud_save_restore_state(
                stage="failed",
                running=False,
                progress=100.0,
                message=f"生成恢复计划失败：{exc}",
                reason="plan_failed",
            )
            raise

        temp_dir = str(bundle.get("temp_dir", "") or "")
        extract_dir = str(bundle.get("extract_dir", "") or "")
        manifest = dict(bundle.get("manifest") or {})
        manifest_playtime = self._extract_manifest_playtime_payload(manifest)
        entries = [dict(item) for item in list(bundle.get("entries") or []) if isinstance(item, dict)]
        available_entry_ids = [str(item.get("entry_id", "") or "").strip() for item in entries if str(item.get("entry_id", "") or "").strip()]
        selected_ids = [str(item or "").strip() for item in list(selected_entry_ids or []) if str(item or "").strip()]
        if not selected_ids:
            selected_ids = list(available_entry_ids)

        if str(manifest.get("source_strategy", "") or "").strip() == "emulator_saves":
            try:
                return await self._plan_emulator_save_restore(
                    bundle=bundle,
                    manifest=manifest,
                    entries=entries,
                    selected_ids=selected_ids,
                    game_id=normalized_game_id,
                    game_key=normalized_game_key,
                    game_title=normalized_game_title,
                    version_name=normalized_version,
                    manifest_playtime=manifest_playtime,
                )
            except Exception as exc:
                await self._set_cloud_save_restore_state(
                    stage="failed",
                    running=False,
                    progress=100.0,
                    message=f"模拟器存档恢复计划失败：{exc}",
                    reason="plan_failed",
                )
                raise

        entry_target_dirs: Dict[str, str] = {}
        compat_user_dir = self._resolve_current_compat_user_dir(normalized_game_id)
        selected_set = {str(item or "").strip() for item in list(selected_ids or []) if str(item or "").strip()}
        if compat_user_dir and selected_set:
            for entry in entries:
                entry_id = str(entry.get("entry_id", "") or "").strip()
                if not entry_id or entry_id not in selected_set:
                    continue
                source_path = str(entry.get("source_path", "") or "").strip()
                archive_rel_path = str(entry.get("archive_rel_path", "") or "").strip().replace("\\", "/").strip("/")
                relative = self._extract_proton_relative_path(
                    source_path=source_path,
                    archive_rel_path=archive_rel_path,
                )
                if not relative:
                    continue
                candidate = os.path.join(compat_user_dir, *[part for part in relative.split("/") if part])
                normalized_candidate = self._normalize_dir_path(candidate)
                if normalized_candidate:
                    entry_target_dirs[entry_id] = normalized_candidate

        auto_target_ready = bool(selected_set) and len(entry_target_dirs) >= len(selected_set)
        target_candidates: List[str] = []
        diagnostics: Dict[str, Any] = {
            "compat_user_dir": compat_user_dir,
            "auto_target_from_manifest": auto_target_ready,
            "entry_target_dirs": dict(entry_target_dirs),
        }

        normalized_target = self._normalize_dir_path(str(target_dir or "").strip())
        if auto_target_ready:
            if normalized_target and normalized_target not in set(entry_target_dirs.values()):
                diagnostics["requested_target_dir"] = normalized_target
                diagnostics["target_dir_stale"] = True
            normalized_target = compat_user_dir or self._normalize_dir_path(next(iter(entry_target_dirs.values()), ""))
        else:
            target_result = self._resolve_cloud_restore_target_candidates(
                game_id=normalized_game_id,
                game_key=normalized_game_key,
                game_title=normalized_game_title,
                entries=entries,
            )
            target_candidates = [str(item or "") for item in list(target_result.get("candidates") or []) if str(item or "").strip()]
            diagnostics = {
                **diagnostics,
                **dict(target_result.get("diagnostics") or {}),
            }

            if not target_candidates:
                self._cleanup_cloud_save_temp_paths([temp_dir])
                await self._set_cloud_save_restore_state(
                    stage="failed",
                    running=False,
                    progress=100.0,
                    message="未找到可恢复的目标目录",
                    reason="target_not_found",
                    selected_entry_ids=selected_ids,
                    diagnostics=diagnostics,
                )
                return {
                    "accepted": False,
                    "reason": "target_not_found",
                    "message": "未找到可恢复的目标目录，请确保游戏已安装并至少启动过一次",
                    "target_candidates": [],
                    "available_entries": entries,
                }

            if normalized_target and normalized_target not in target_candidates:
                diagnostics["requested_target_dir"] = normalized_target
                diagnostics["target_dir_stale"] = True
                normalized_target = ""

            if not normalized_target:
                if len(target_candidates) == 1:
                    normalized_target = target_candidates[0]
                else:
                    self._cleanup_cloud_save_temp_paths([temp_dir])
                    await self._set_cloud_save_restore_state(
                        stage="ready",
                        running=False,
                        progress=100.0,
                        message="检测到多个目标目录，请先选择",
                        reason="target_selection_required",
                        selected_entry_ids=selected_ids,
                        diagnostics=diagnostics,
                    )
                    return {
                        "accepted": False,
                        "reason": "target_selection_required",
                        "message": "检测到多个目标目录，请先选择恢复目标",
                        "target_candidates": target_candidates,
                        "available_entries": entries,
                    }

        copy_plan = self._build_restore_copy_plan(
            extract_dir=extract_dir,
            entries=entries,
            selected_entry_ids=selected_ids,
            target_dir=normalized_target,
            entry_target_dirs=entry_target_dirs,
        )
        copy_pairs = list(copy_plan.get("copy_pairs") or [])
        plan_items = [dict(item) for item in list(copy_plan.get("plan_items") or []) if isinstance(item, dict)]
        conflict_count = max(0, _safe_int(copy_plan.get("conflict_count"), 0))
        conflict_samples = [str(item or "") for item in list(copy_plan.get("conflict_samples") or []) if str(item or "").strip()]
        requires_confirmation = conflict_count > 0

        plan_id = uuid.uuid4().hex
        async with self._cloud_save_restore_lock:
            self._cloud_save_restore_plan = {
                "plan_id": plan_id,
                "temp_paths": [temp_dir],
                "copy_pairs": copy_pairs,
                "plan_items": plan_items,
                "requires_confirmation": requires_confirmation,
                "conflict_count": conflict_count,
                "conflict_samples": conflict_samples,
                "target_dir": normalized_target,
                "entry_target_dirs": dict(entry_target_dirs),
                "game_id": normalized_game_id,
                "game_key": normalized_game_key,
                "game_title": normalized_game_title,
                "version_name": normalized_version,
                "selected_entry_ids": selected_ids,
                "manifest_playtime": manifest_playtime,
            }

        await self._set_cloud_save_restore_state(
            stage="ready",
            running=False,
            progress=100.0,
            message="恢复计划已生成",
            reason="",
            selected_entry_ids=selected_ids,
            selected_target_dir=normalized_target,
            requires_confirmation=requires_confirmation,
            conflict_count=conflict_count,
            conflict_samples=conflict_samples,
            restored_files=0,
            restored_entries=0,
            diagnostics={
                **diagnostics,
                "target_candidates": target_candidates,
                "plan_items": plan_items,
                "manifest_playtime": manifest_playtime,
            },
        )

        return {
            "accepted": True,
            "plan_id": plan_id,
            "message": "恢复计划已生成",
            "reason": "",
            "requires_confirmation": requires_confirmation,
            "conflict_count": conflict_count,
            "conflict_samples": conflict_samples,
            "target_candidates": target_candidates,
            "selected_target_dir": normalized_target,
            "selected_entry_ids": selected_ids,
            "available_entries": entries,
            "restorable_files": len(copy_pairs),
            "restorable_entries": len(plan_items),
        }

    async def apply_cloud_save_restore(
        self,
        *,
        plan_id: str,
        confirm_overwrite: bool = False,
    ) -> Dict[str, Any]:
        """执行恢复计划（确认后写入）。"""
        normalized_plan_id = str(plan_id or "").strip()
        if not normalized_plan_id:
            raise TianyiApiError("缺少 plan_id")

        async with self._cloud_save_restore_lock:
            plan = dict(self._cloud_save_restore_plan or {})

        if not plan or str(plan.get("plan_id", "") or "").strip() != normalized_plan_id:
            raise TianyiApiError("恢复计划不存在或已过期，请重新规划")

        requires_confirmation = bool(plan.get("requires_confirmation", False))
        if requires_confirmation and not bool(confirm_overwrite):
            result_payload = {
                "status": "cancelled",
                "reason": "user_cancelled",
                "message": "用户已取消覆盖恢复",
                "game_id": str(plan.get("game_id", "") or ""),
                "game_key": str(plan.get("game_key", "") or ""),
                "game_title": str(plan.get("game_title", "") or ""),
                "version_name": str(plan.get("version_name", "") or ""),
                "target_dir": str(plan.get("target_dir", "") or ""),
                "selected_entry_ids": list(plan.get("selected_entry_ids") or []),
                "restored_files": 0,
                "restored_entries": 0,
                "conflicts_overwritten": 0,
                "results": [],
                "diagnostics": {"requires_confirmation": True},
                "finished_at": _now_wall_ts(),
            }
            await asyncio.to_thread(self.store.set_cloud_save_restore_last_result, result_payload)
            await self._set_cloud_save_restore_state(
                stage="failed",
                running=False,
                progress=100.0,
                message=result_payload["message"],
                reason=result_payload["reason"],
                restored_files=0,
                restored_entries=0,
                results=[],
                diagnostics=dict(result_payload.get("diagnostics", {}) or {}),
                last_result=result_payload,
            )
            await self._clear_cloud_save_restore_plan()
            return result_payload

        copy_pairs = list(plan.get("copy_pairs") or [])
        plan_items = [dict(item) for item in list(plan.get("plan_items") or []) if isinstance(item, dict)]
        target_dir = str(plan.get("target_dir", "") or "")
        restored_files = 0
        backed_up_files = 0
        backup_suffix = f"cloud-save-{time.strftime('%Y%m%d_%H%M%S')}-{uuid.uuid4().hex[:6]}"
        backup_root = os.path.join(str(config.DECKY_SEND_DIR), "backups", backup_suffix)
        results: List[Dict[str, Any]] = []
        exception_text = ""

        await self._set_cloud_save_restore_state(
            stage="applying",
            running=True,
            progress=0.0,
            message="正在恢复存档",
            reason="",
            restored_files=0,
            restored_entries=0,
            results=[],
        )

        try:
            total_files = len(copy_pairs)
            failed_files = 0
            for index, (src, dst) in enumerate(copy_pairs, start=1):
                src_file = os.path.realpath(os.path.expanduser(str(src or "").strip()))
                dst_file = os.path.realpath(os.path.expanduser(str(dst or "").strip()))
                if not src_file or not os.path.isfile(src_file):
                    failed_files += 1
                    continue
                parent = os.path.dirname(dst_file)
                os.makedirs(parent, exist_ok=True)
                # 覆盖前备份到独立目录（不放在存档树里，避免被下次云上传打包）。
                if os.path.isdir(dst_file) or os.path.exists(dst_file):
                    try:
                        os.makedirs(backup_root, exist_ok=True)
                        digest = hashlib.sha1(dst_file.encode("utf-8", "replace")).hexdigest()[:12]
                        backup_path = os.path.join(backup_root, f"{digest}_{os.path.basename(dst_file.rstrip('/\\'))}")
                        if os.path.exists(backup_path):
                            if os.path.isdir(backup_path):
                                shutil.rmtree(backup_path, ignore_errors=True)
                            else:
                                os.remove(backup_path)
                        # 存档可能在 SD 卡，备份目录在 HOME：move 支持跨文件系统。
                        shutil.move(dst_file, backup_path)
                        backed_up_files += 1
                    except Exception as exc:
                        raise RuntimeError(f"备份原存档失败：{exc}") from exc
                shutil.copy2(src_file, dst_file)
                restored_files += 1
                progress = 100.0 if total_files <= 0 else (float(index) / float(total_files)) * 100.0
                await self._set_cloud_save_restore_state(
                    stage="applying",
                    running=True,
                    progress=progress,
                    message=f"正在恢复文件 {index}/{total_files}",
                    restored_files=restored_files,
                )

            if failed_files > 0:
                raise RuntimeError(
                    f"存档源文件缺失/不可读 {failed_files}/{total_files}，已恢复 {restored_files} 个，未上报成功"
                )

            for item in plan_items:
                results.append(
                    {
                        "entry_id": str(item.get("entry_id", "") or ""),
                        "entry_name": str(item.get("entry_name", "") or ""),
                        "status": "restored",
                        "reason": "",
                        "file_count": max(0, _safe_int(item.get("file_count"), 0)),
                        "diagnostics": {},
                    }
                )

            if backed_up_files:
                self._prune_cloud_save_backups()
            manifest_playtime = dict(plan.get("manifest_playtime") or {})
            playtime_merge: Dict[str, Any] = {}
            try:
                playtime_merge = await self._merge_cloud_restore_playtime(
                    game_id=str(plan.get("game_id", "") or ""),
                    game_key=str(plan.get("game_key", "") or ""),
                    target_dir=target_dir,
                    manifest_playtime=manifest_playtime,
                )
            except Exception as exc:
                playtime_merge = {
                    "merged": False,
                    "reason": "playtime_merge_failed",
                    "message": f"游玩时长合并失败：{exc}",
                }

            result_payload = {
                "status": "success",
                "reason": "",
                "message": (
                    f"云存档恢复完成（恢复文件 {restored_files}）"
                    + (f"，覆盖前已备份 {backed_up_files} 个同名路径" if backed_up_files else "")
                ),
                "game_id": str(plan.get("game_id", "") or ""),
                "game_key": str(plan.get("game_key", "") or ""),
                "game_title": str(plan.get("game_title", "") or ""),
                "version_name": str(plan.get("version_name", "") or ""),
                "target_dir": target_dir,
                "selected_entry_ids": list(plan.get("selected_entry_ids") or []),
                "restored_files": restored_files,
                "backed_up_files": backed_up_files,
                "backup_suffix": backup_suffix if backed_up_files else "",
                "backup_dir": backup_root if backed_up_files else "",
                "restored_entries": len(plan_items),
                "conflicts_overwritten": max(0, _safe_int(plan.get("conflict_count"), 0)),
                "results": results,
                "diagnostics": {
                    "requires_confirmation": requires_confirmation,
                    "backup_suffix": backup_suffix,
                    "backup_dir": backup_root if backed_up_files else "",
                    "backed_up_files": backed_up_files,
                    "conflict_samples": list(plan.get("conflict_samples") or []),
                    "entry_target_dirs": dict(plan.get("entry_target_dirs") or {}),
                    "playtime_merge": playtime_merge,
                },
                "finished_at": _now_wall_ts(),
            }
            await asyncio.to_thread(self.store.set_cloud_save_restore_last_result, result_payload)
            await self._set_cloud_save_restore_state(
                stage="completed",
                running=False,
                progress=100.0,
                message=str(result_payload.get("message", "") or "恢复完成"),
                reason="",
                restored_files=restored_files,
                restored_entries=len(plan_items),
                results=results,
                diagnostics=dict(result_payload.get("diagnostics", {}) or {}),
                last_result=result_payload,
            )
            return result_payload
        except Exception as exc:
            exception_text = str(exc)
            result_payload = {
                "status": "failed",
                "reason": "apply_failed",
                "message": f"云存档恢复失败：{exc}",
                "game_id": str(plan.get("game_id", "") or ""),
                "game_key": str(plan.get("game_key", "") or ""),
                "game_title": str(plan.get("game_title", "") or ""),
                "version_name": str(plan.get("version_name", "") or ""),
                "target_dir": target_dir,
                "selected_entry_ids": list(plan.get("selected_entry_ids") or []),
                "restored_files": restored_files,
                "restored_entries": 0,
                "conflicts_overwritten": 0,
                "results": results,
                "diagnostics": {"exception": exception_text},
                "finished_at": _now_wall_ts(),
            }
            await asyncio.to_thread(self.store.set_cloud_save_restore_last_result, result_payload)
            await self._set_cloud_save_restore_state(
                stage="failed",
                running=False,
                progress=100.0,
                message=str(result_payload.get("message", "") or "恢复失败"),
                reason=str(result_payload.get("reason", "") or "apply_failed"),
                restored_files=restored_files,
                restored_entries=0,
                results=results,
                diagnostics=dict(result_payload.get("diagnostics", {}) or {}),
                last_result=result_payload,
            )
            return result_payload
        finally:
            await self._clear_cloud_save_restore_plan()

    def _normalize_existing_dir(self, path: str) -> str:
        """规范化并校验目录存在。"""
        normalized = self._normalize_dir_path(path)
        if not normalized or not os.path.isdir(normalized):
            return ""
        return normalized

    def _normalize_dir_path(self, path: str) -> str:
        """规范化目录路径（允许目录暂不存在）。"""
        raw = str(path or "").strip()
        if not raw:
            return ""
        try:
            normalized = os.path.realpath(os.path.expanduser(raw))
        except Exception:
            return ""
        return str(normalized or "").strip()

    def _dedupe_paths(self, paths: Sequence[str], *, require_existing: bool = False) -> List[str]:
        """目录去重并去除被父目录覆盖的子目录。"""
        normalized: List[str] = []
        seen = set()
        for raw in list(paths or []):
            path = self._normalize_dir_path(str(raw or ""))
            if not path:
                continue
            if require_existing and not os.path.isdir(path):
                continue
            if path in seen:
                continue
            seen.add(path)
            normalized.append(path)

        normalized.sort(key=lambda item: (len(item), item))
        compacted: List[str] = []
        for path in normalized:
            covered = False
            for parent in compacted:
                if path == parent or path.startswith(parent + os.sep):
                    covered = True
                    break
            if not covered:
                compacted.append(path)
            if len(compacted) >= CLOUD_SAVE_MAX_SOURCE_PATHS:
                break
        return compacted

    def _extract_proton_relative_path(self, *, source_path: str, archive_rel_path: str = "") -> str:
        """从 source_path / archive_rel_path 提取 Proton 用户目录下的相对路径。"""

        patterns: Tuple[Tuple[str, ...], ...] = (
            ("Documents", "My Games"),
            ("Saved Games",),
            ("AppData", "Roaming"),
            ("AppData", "LocalLow"),
            ("AppData", "Local"),
        )

        def _match(parts: Sequence[str]) -> str:
            seq = [str(item or "").strip() for item in list(parts or []) if str(item or "").strip()]
            if not seq:
                return ""
            lowered = [item.lower() for item in seq]
            for pattern in patterns:
                token = [str(item or "").strip().lower() for item in pattern if str(item or "").strip()]
                if not token:
                    continue
                max_start = len(lowered) - len(token)
                for idx in range(max(0, max_start + 1)):
                    if lowered[idx: idx + len(token)] == token:
                        return "/".join(seq[idx:])
            return ""

        source_parts = [part for part in Path(self._normalize_dir_path(source_path)).parts if str(part or "").strip()]
        matched = _match(source_parts)
        if matched:
            return matched

        rel_parts = [
            part
            for part in str(archive_rel_path or "").replace("\\", "/").split("/")
            if part and part not in {".", ".."}
        ]
        return _match(rel_parts)

    def _resolve_current_compat_user_dir(self, game_id: str) -> str:
        """解析当前游戏对应的 Proton 用户目录。"""
        target_game_id = str(game_id or "").strip()
        if not target_game_id:
            return ""
        try:
            result = resolve_tianyi_shortcut_sync(game_id=target_game_id)
        except Exception:
            return ""
        return self._normalize_existing_dir(str(result.get("compat_user_dir", "") or ""))

    def _build_cloud_save_game_key(self, game_id: str, game_title: str) -> str:
        """生成稳定 game-key。"""
        token = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(game_id or "").strip()).strip("_")
        if token:
            return token.lower()

        title_token = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(game_title or "").strip()).strip("_")
        if title_token:
            return title_token.lower()

        return f"game_{_now_wall_ts()}"

    def _parse_cloud_save_version_timestamp(self, version_name: str) -> int:
        """从云端版本名中提取时间戳（秒）。"""
        raw_name = str(version_name or "").strip()
        if not raw_name:
            return 0
        stem = raw_name
        if stem.lower().endswith(".7z"):
            stem = stem[:-3]
        stem = stem.strip()
        if not re.fullmatch(r"\d{8}_\d{6}", stem):
            return 0
        try:
            return int(time.mktime(time.strptime(stem, CLOUD_SAVE_DATE_FORMAT)))
        except Exception:
            return 0

    def _format_cloud_save_version_time(self, ts: int, fallback: str) -> str:
        """格式化版本时间显示。"""
        value = _safe_int(ts, 0)
        if value <= 0:
            return str(fallback or "")
        try:
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(value))
        except Exception:
            return str(fallback or "")

    def _collect_cloud_restore_games(self) -> List[Dict[str, Any]]:
        """按 game_key 聚合当前已安装游戏。"""
        records = list(self.store.installed_games or [])
        records.sort(key=lambda item: int(item.updated_at or 0), reverse=True)

        grouped: Dict[str, Dict[str, Any]] = {}
        for record in records:
            game_id = str(record.game_id or "").strip()
            game_title = str(record.game_title or "").strip() or "未命名游戏"
            game_key = self._build_cloud_save_game_key(game_id, game_title)
            install_path = self._normalize_existing_dir(str(record.install_path or "").strip())
            if not install_path:
                continue

            item = grouped.get(game_key)
            if item is None:
                item = {
                    "game_id": game_id,
                    "game_title": game_title,
                    "game_key": game_key,
                    "install_paths": [],
                    "updated_at": _safe_int(record.updated_at, 0),
                }
                grouped[game_key] = item

            paths = item.get("install_paths")
            if not isinstance(paths, list):
                paths = []
                item["install_paths"] = paths
            if install_path not in paths:
                paths.append(install_path)

            if game_id and not str(item.get("game_id", "") or "").strip():
                item["game_id"] = game_id
            if _safe_int(record.updated_at, 0) > _safe_int(item.get("updated_at"), 0):
                item["updated_at"] = _safe_int(record.updated_at, 0)
                if game_title:
                    item["game_title"] = game_title
                if game_id:
                    item["game_id"] = game_id

        games = list(grouped.values())
        games.sort(
            key=lambda row: (
                -_safe_int(row.get("updated_at"), 0),
                str(row.get("game_title", "") or "").lower(),
                str(row.get("game_key", "") or ""),
            )
        )
        return games

    def _migrate_legacy_backup_roots(self, roots: Sequence[str]) -> int:
        """把旧版本留在存档树里的 .freedeckcy-bak-* 移到中央备份目录。"""
        destination_root = Path(config.DECKY_SEND_DIR) / "backups" / "legacy"
        moved = 0
        for raw in roots:
            root = os.path.realpath(os.path.expanduser(str(raw or "").strip()))
            if not root or not os.path.isdir(root):
                continue
            for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
                backup_dirs = [name for name in dirnames if ".freedeckcy-bak-" in name]
                backup_files = [name for name in filenames if ".freedeckcy-bak-" in name]
                dirnames[:] = [name for name in dirnames if name not in backup_dirs]
                for name in backup_dirs + backup_files:
                    source = os.path.join(dirpath, name)
                    if os.path.islink(source) or not os.path.exists(source):
                        continue
                    try:
                        digest = hashlib.sha1(source.encode("utf-8", "replace")).hexdigest()[:12]
                        destination_root.mkdir(parents=True, exist_ok=True)
                        destination = destination_root / f"{digest}_{name}"
                        if destination.exists():
                            continue
                        shutil.move(source, destination)
                        moved += 1
                    except Exception as exc:
                        config.logger.warning("迁移旧云存档备份失败 %s: %s", source, exc)
        return moved

    def _migrate_all_legacy_backups(self) -> int:
        if self._legacy_backup_migration_done:
            return 0
        self._legacy_backup_migration_done = True
        moved = 0
        for record in list(self.store.installed_games or []):
            try:
                roots = restore_roots(record)
            except Exception:
                continue
            moved += self._migrate_legacy_backup_roots(roots)
        if moved:
            config.logger.info("已迁移旧云存档备份到中央目录: %s", moved)
            self._prune_cloud_save_backups()
        return moved

    @staticmethod
    def _prune_cloud_save_backups(keep: int = 10) -> None:
        """保留最近 N 份云存档恢复备份，避免备份目录无限增长。"""
        root = Path(config.DECKY_SEND_DIR) / "backups"
        try:
            if not root.is_dir():
                return
            dirs = sorted(
                [
                    item for item in root.iterdir()
                    if item.is_dir() and item.name.startswith("cloud-save-")
                ],
                key=lambda item: item.stat().st_mtime,
                reverse=True,
            )
            for old in dirs[max(1, int(keep)):]:
                shutil.rmtree(old, ignore_errors=True)
        except Exception as exc:
            config.logger.warning("清理云存档备份失败: %s", exc)

    def _normalize_cloud_restore_entries(self, *, manifest: Dict[str, Any], extract_dir: str) -> List[Dict[str, Any]]:
        """从 manifest 或归档目录生成可选存档项。"""
        result: List[Dict[str, Any]] = []
        extract_root = self._normalize_existing_dir(extract_dir)
        if not extract_root:
            return result

        entries = manifest.get("entries")
        missing_entries: List[Dict[str, Any]] = []
        if isinstance(entries, list):
            for idx, item in enumerate(entries, start=1):
                if not isinstance(item, dict):
                    continue
                entry_id = str(item.get("entry_id", "") or "").strip() or f"entry_{idx}"
                entry_name = str(item.get("name", "") or item.get("entry_name", "") or "").strip() or entry_id
                rel_path = str(item.get("archive_rel_path", "") or "").strip().replace("\\", "/").strip("/")
                if not rel_path:
                    rel_path = str(item.get("relative_path", "") or "").strip().replace("\\", "/").strip("/")
                # 兼容旧 manifest：archive_rel_path 缺失/过旧时，尝试用条目名定位实际目录。
                candidates = [rel_path] if rel_path else []
                if entry_name and entry_name not in candidates:
                    candidates.append(entry_name)
                abs_path = ""
                resolved_rel = rel_path
                for candidate in candidates:
                    if not candidate:
                        continue
                    possible = os.path.realpath(os.path.join(extract_root, candidate))
                    if _is_within_dir(possible, extract_root) and os.path.exists(possible):
                        abs_path = possible
                        resolved_rel = candidate
                        break
                if not abs_path:
                    missing_entries.append(
                        {
                            "entry_id": entry_id,
                            "entry_name": entry_name,
                            "source_path": str(item.get("source_path", "") or ""),
                        }
                    )
                    continue
                result.append(
                    {
                        "entry_id": entry_id,
                        "entry_name": entry_name,
                        "archive_rel_path": resolved_rel,
                        "source_path": str(item.get("source_path", "") or ""),
                    }
                )

        if not result and missing_entries:
            # 更老的包可能把游戏目录内容直接放在归档根，manifest 只记了目录名。
            try:
                root_has_entries = bool(os.listdir(extract_root))
            except Exception:
                root_has_entries = False
            if root_has_entries:
                for item in missing_entries:
                    result.append(
                        {
                            "entry_id": item["entry_id"],
                            "entry_name": item["entry_name"],
                            "archive_rel_path": "",
                            "source_path": item["source_path"],
                        }
                    )
        if result:
            return result

        source_paths = manifest.get("source_paths")
        if isinstance(source_paths, list):
            for idx, raw in enumerate(source_paths, start=1):
                source_path = str(raw or "").strip()
                if not source_path:
                    continue
                name = os.path.basename(source_path.rstrip("/\\")).strip() or f"entry_{idx}"
                result.append(
                    {
                        "entry_id": f"entry_{idx}",
                        "entry_name": name,
                        "archive_rel_path": "",
                        "source_path": source_path,
                    }
                )

        if result:
            fallback_entries: List[Dict[str, Any]] = []
            try:
                roots = sorted(os.listdir(extract_root))
            except Exception:
                roots = []
            for idx, name in enumerate(roots, start=1):
                root_name = str(name or "").strip()
                if not root_name or root_name == "manifest.json":
                    continue
                abs_path = os.path.join(extract_root, root_name)
                if not os.path.exists(abs_path):
                    continue
                fallback_entries.append(
                    {
                        "entry_id": f"entry_{idx}",
                        "entry_name": root_name,
                        "archive_rel_path": root_name.replace("\\", "/"),
                        "source_path": "",
                    }
                )
            if fallback_entries:
                return fallback_entries

        return [
            {
                "entry_id": "entry_all",
                "entry_name": "全部存档",
                "archive_rel_path": "",
                "source_path": "",
            }
        ]

    def _extract_manifest_playtime_payload(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """从云存档 manifest 中提取游玩时长信息。"""
        if not isinstance(manifest, dict):
            return {}

        playtime_raw = manifest.get("playtime")
        playtime = playtime_raw if isinstance(playtime_raw, dict) else {}

        seconds = max(0, _safe_int(playtime.get("seconds"), _safe_int(manifest.get("playtime_seconds"), 0)))
        sessions = max(0, _safe_int(playtime.get("sessions"), _safe_int(manifest.get("playtime_sessions"), 0)))
        last_played_at = max(
            0,
            _safe_int(playtime.get("last_played_at"), _safe_int(manifest.get("playtime_last_played_at"), 0)),
        )
        captured_at = max(
            0,
            _safe_int(playtime.get("captured_at"), _safe_int(manifest.get("playtime_captured_at"), 0)),
        )

        if seconds <= 0 and sessions <= 0 and last_played_at <= 0:
            return {}

        return {
            "seconds": seconds,
            "sessions": sessions,
            "last_played_at": last_played_at,
            "captured_at": captured_at,
        }

    async def _merge_cloud_restore_playtime(
        self,
        *,
        game_id: str,
        game_key: str,
        target_dir: str,
        manifest_playtime: Dict[str, Any],
    ) -> Dict[str, Any]:
        """将云存档中的游玩时长合并到本地记录（不降级覆盖）。"""
        payload = dict(manifest_playtime or {})
        if not payload:
            return {"merged": False, "reason": "playtime_missing", "message": "manifest 未包含游玩时长"}

        cloud_seconds = max(0, _safe_int(payload.get("seconds"), 0))
        cloud_sessions = max(0, _safe_int(payload.get("sessions"), 0))
        cloud_last_played_at = max(0, _safe_int(payload.get("last_played_at"), 0))
        if cloud_seconds <= 0 and cloud_sessions <= 0 and cloud_last_played_at <= 0:
            return {"merged": False, "reason": "playtime_empty", "message": "云端游玩时长为空"}

        target_game_id = str(game_id or "").strip()
        target_game_key = str(game_key or "").strip()
        normalized_target_dir = self._normalize_dir_path(str(target_dir or "").strip())

        record = self._find_installed_record(game_id=target_game_id, install_path=normalized_target_dir)
        if record is None and target_game_id:
            record = self._find_installed_record(game_id=target_game_id)
        if record is None and target_game_key:
            for item in list(self.store.installed_games or []):
                item_key = self._build_cloud_save_game_key(
                    str(item.game_id or "").strip(),
                    str(item.game_title or "").strip(),
                )
                if item_key == target_game_key:
                    record = item
                    break

        if record is None:
            return {"merged": False, "reason": "record_not_found", "message": "未找到本地安装记录"}

        local_seconds_before = max(0, _safe_int(record.playtime_seconds, 0))
        local_sessions_before = max(0, _safe_int(record.playtime_sessions, 0))
        local_last_played_before = max(0, _safe_int(record.playtime_last_played_at, 0))

        local_seconds_after = max(local_seconds_before, cloud_seconds)
        local_sessions_after = max(local_sessions_before, cloud_sessions)
        local_last_played_after = max(local_last_played_before, cloud_last_played_at)
        changed = (
            local_seconds_after != local_seconds_before
            or local_sessions_after != local_sessions_before
            or local_last_played_after != local_last_played_before
        )

        if not changed:
            return {
                "merged": False,
                "reason": "already_up_to_date",
                "message": "本地游玩时长不低于云端",
                "local_seconds": local_seconds_before,
                "cloud_seconds": cloud_seconds,
            }

        now_ts = _now_wall_ts()
        record.playtime_seconds = local_seconds_after
        record.playtime_sessions = local_sessions_after
        record.playtime_last_played_at = local_last_played_after
        record.updated_at = now_ts
        await asyncio.to_thread(self.store.save)
        self._invalidate_panel_cache(installed=True)
        return {
            "merged": True,
            "reason": "",
            "message": "已合并云端游玩时长",
            "local_seconds_before": local_seconds_before,
            "local_seconds_after": local_seconds_after,
            "cloud_seconds": cloud_seconds,
        }

    def _build_cloud_save_match_tokens(self, *, game_id: str, game_title: str, install_path: str) -> List[str]:
        """构建存档目录匹配词元。"""
        raw_values = [
            str(game_id or "").strip(),
            str(game_title or "").strip(),
            os.path.basename(str(install_path or "").strip()),
        ]

        token_set = set()
        for raw in raw_values:
            if not raw:
                continue
            lower = raw.lower()
            compact = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", lower)
            if len(compact) >= 3:
                token_set.add(compact)
            for part in re.split(r"[^0-9a-z\u4e00-\u9fff]+", lower):
                text = str(part or "").strip()
                if len(text) >= 2:
                    token_set.add(text)

        return sorted(token_set, key=lambda item: (-len(item), item))

    def _dedupe_existing_paths(self, paths: Sequence[str]) -> List[str]:
        """目录去重并去除被父目录覆盖的子目录。"""
        return self._dedupe_paths(paths, require_existing=True)

    def _should_keep_cloud_save_dir(
        self,
        *,
        root: str,
        current: str,
        tokens: Sequence[str],
        keywords: Sequence[str],
    ) -> bool:
        """判断当前目录是否应作为存档候选。"""
        root_dir = str(root or "").strip()
        current_dir = str(current or "").strip()
        if not root_dir or not current_dir:
            return False
        if current_dir == root_dir:
            return False

        name = os.path.basename(current_dir).lower()
        try:
            rel = os.path.relpath(current_dir, root_dir).replace("\\", "/").lower()
        except Exception:
            rel = name

        token_hit = False
        for token in list(tokens or []):
            text = str(token or "").strip().lower()
            if len(text) < 2:
                continue
            if text in name or text in rel:
                token_hit = True
                break

        keyword_hit = False
        for keyword in list(keywords or []):
            text = str(keyword or "").strip().lower()
            if len(text) < 2:
                continue
            if text in name or text in rel:
                keyword_hit = True
                break

        if not token_hit and not keyword_hit:
            return False

        try:
            with os.scandir(current_dir) as it:
                for _ in it:
                    return True
        except Exception:
            return False
        return False

    def _scan_cloud_save_paths(
        self,
        *,
        root: str,
        tokens: Sequence[str],
        keywords: Sequence[str],
    ) -> List[str]:
        """在限定深度内扫描存档候选目录。"""
        root_dir = self._normalize_existing_dir(root)
        if not root_dir:
            return []

        base_depth = root_dir.count(os.sep)
        matches: List[str] = []
        for dirpath, dirnames, _filenames in os.walk(root_dir):
            depth = max(0, dirpath.count(os.sep) - base_depth)
            if depth >= CLOUD_SAVE_SCAN_MAX_DEPTH:
                dirnames[:] = []

            if self._should_keep_cloud_save_dir(
                root=root_dir,
                current=dirpath,
                tokens=tokens,
                keywords=keywords,
            ):
                matches.append(dirpath)
                if len(matches) >= CLOUD_SAVE_SCAN_MAX_MATCHES:
                    break

        return self._dedupe_existing_paths(matches)

    def _collect_cloud_save_paths_from_proton(
        self,
        *,
        compat_user_dir: str,
        tokens: Sequence[str],
    ) -> Tuple[List[str], Dict[str, Any]]:
        """从 Proton 前缀白名单目录采集存档路径。"""
        root = self._normalize_existing_dir(compat_user_dir)
        diagnostics: Dict[str, Any] = {"compat_user_dir": root, "scanned_bases": [], "matched": []}
        if not root:
            diagnostics["reason"] = "compat_user_dir_missing"
            return [], diagnostics

        collected: List[str] = []
        for parts in CLOUD_SAVE_PROTON_BASE_DIRS:
            base = os.path.join(root, *parts)
            if not os.path.isdir(base):
                continue
            diagnostics["scanned_bases"].append(base)
            collected.extend(self._scan_cloud_save_paths(root=base, tokens=tokens, keywords=()))

        merged = self._dedupe_existing_paths(collected)
        diagnostics["matched"] = list(merged)
        if not merged:
            diagnostics["reason"] = "save_path_not_found"
        return merged, diagnostics

    def _collect_cloud_save_paths_from_install(
        self,
        *,
        install_path: str,
        tokens: Sequence[str],
    ) -> Tuple[List[str], Dict[str, Any]]:
        """在安装目录白名单兜底采集存档路径。"""
        root = self._normalize_existing_dir(install_path)
        diagnostics: Dict[str, Any] = {
            "install_path": root,
            "keywords": list(CLOUD_SAVE_INSTALL_FALLBACK_DIRS),
            "matched": [],
        }
        if not root:
            diagnostics["reason"] = "install_path_missing"
            return [], diagnostics

        collected = self._scan_cloud_save_paths(
            root=root,
            tokens=tokens,
            keywords=CLOUD_SAVE_INSTALL_FALLBACK_DIRS,
        )
        diagnostics["matched"] = list(collected)
        if not collected:
            diagnostics["reason"] = "save_path_not_found"
        return collected, diagnostics

    async def _collect_cloud_save_candidates(self) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """基于已安装记录构建云存档候选。"""
        records = list(self.store.installed_games or [])
        records.sort(key=lambda item: int(item.updated_at or 0), reverse=True)

        try:
            manifest_data = await asyncio.to_thread(load_manifest, self.plugin_dir)
        except Exception as exc:
            manifest_data = {}
            config.logger.warning("Ludusavi 清单加载失败: %s", exc)

        candidates: List[Dict[str, Any]] = []
        ignored: List[Dict[str, Any]] = []
        dedupe_keys = set()
        shared_emulator_saves = set()

        for record in records:
            game_id = str(record.game_id or "").strip()
            game_title = str(record.game_title or "").strip() or "未命名游戏"
            install_path = self._normalize_existing_dir(str(record.install_path or "").strip())
            if not install_path:
                ignored.append(
                    {
                        "game_id": game_id,
                        "game_title": game_title,
                        "reason": "install_path_missing",
                    }
                )
                continue

            dedupe_key = f"{game_id}|{install_path}"
            if dedupe_key in dedupe_keys:
                continue
            dedupe_keys.add(dedupe_key)

            game_key = self._build_cloud_save_game_key(game_id, game_title)
            tokens = self._build_cloud_save_match_tokens(
                game_id=game_id,
                game_title=game_title,
                install_path=install_path,
            )

            platform = str(record.platform or "pc").strip().lower() or "pc"
            if platform != "pc" and not bool(getattr(self.store.settings, "cloud_save_include_emulators", True)):
                ignored.append(
                    {
                        "game_id": game_id,
                        "game_title": game_title,
                        "reason": "emulator_saves_disabled",
                    }
                )
                continue
            if platform != "pc":
                emulator_result = await asyncio.to_thread(collect_emulator_save_paths, record)
                signature = tuple(emulator_result.paths)
                if emulator_result.paths and not emulator_result.per_game:
                    if signature in shared_emulator_saves:
                        ignored.append(
                            {
                                "game_id": game_id,
                                "game_title": game_title,
                                "reason": "emulator_saves_shared",
                            }
                        )
                        continue
                    shared_emulator_saves.add(signature)
                playtime = self._snapshot_record_playtime(record)
                candidates.append(
                    {
                        "game_id": game_id,
                        "game_title": game_title,
                        "game_key": game_key,
                        "install_path": install_path,
                        "source_paths": list(emulator_result.paths),
                        "source_strategy": "emulator_saves",
                        "skip_reason": "" if emulator_result.paths else emulator_result.reason,
                        "playtime": {
                            "seconds": max(0, _safe_int(playtime.get("seconds"), 0)),
                            "sessions": max(0, _safe_int(playtime.get("sessions"), 0)),
                            "last_played_at": max(0, _safe_int(playtime.get("last_played_at"), 0)),
                            "captured_at": _now_wall_ts(),
                        },
                        "diagnostics": {"emulator_saves": emulator_result.to_dict()},
                    }
                )
                continue

            shortcut_result: Dict[str, Any] = {}
            compat_user_dir = ""
            if game_id:
                try:
                    shortcut_result = await asyncio.to_thread(resolve_tianyi_shortcut_sync, game_id=game_id)
                except Exception as exc:
                    shortcut_result = {"ok": False, "message": str(exc)}
                compat_user_dir = self._normalize_existing_dir(str(shortcut_result.get("compat_user_dir", "") or ""))
            else:
                shortcut_result = {"ok": False, "message": "game_id_missing"}

            app_id = _safe_int(shortcut_result.get("appid_unsigned"), 0)
            manifest_key = ""
            manifest_paths: List[str] = []
            if compat_user_dir and manifest_data:
                manifest_key, manifest_info = match_manifest(
                    manifest_data,
                    titles=[game_title, os.path.basename(install_path)],
                    app_id=app_id,
                )
                if manifest_info:
                    manifest_paths = await asyncio.to_thread(
                        resolve_manifest_paths,
                        manifest_info,
                        prefix_dir=compat_user_dir,
                        install_dir=install_path,
                    )

            source_paths: List[str] = []
            source_strategy = ""
            skip_reason = ""
            diagnostics: Dict[str, Any] = {
                "tokens": list(tokens),
                "install_path": install_path,
                "shortcut": {
                    "ok": bool(shortcut_result.get("ok")),
                    "message": str(shortcut_result.get("message", "") or ""),
                    "appid_unsigned": _safe_int(shortcut_result.get("appid_unsigned"), 0),
                    "compat_user_dir": str(shortcut_result.get("compat_user_dir", "") or ""),
                },
            }

            if compat_user_dir:
                source_paths, proton_diag = self._collect_cloud_save_paths_from_proton(
                    compat_user_dir=compat_user_dir,
                    tokens=tokens,
                )
                diagnostics["proton_scan"] = proton_diag
                source_strategy = "proton_prefix"
                if manifest_paths:
                    source_paths = self._dedupe_existing_paths([*manifest_paths, *source_paths])
                    source_strategy = "ludusavi" if not proton_diag.get("matched") else "ludusavi+proton"
                if not source_paths:
                    skip_reason = "save_path_not_found"
            else:
                source_paths, fallback_diag = self._collect_cloud_save_paths_from_install(
                    install_path=install_path,
                    tokens=tokens,
                )
                diagnostics["fallback_scan"] = fallback_diag
                source_strategy = "install_fallback"
                if not source_paths:
                    skip_reason = "prefix_unresolved"

            diagnostics["ludusavi"] = {
                "matched": manifest_key,
                "path_count": len(manifest_paths),
            }

            playtime = self._snapshot_record_playtime(record)

            candidates.append(
                {
                    "game_id": game_id,
                    "game_title": game_title,
                    "game_key": game_key,
                    "install_path": install_path,
                    "source_paths": list(source_paths),
                    "source_strategy": source_strategy,
                    "skip_reason": skip_reason,
                    "playtime": {
                        "seconds": max(0, _safe_int(playtime.get("seconds"), 0)),
                        "sessions": max(0, _safe_int(playtime.get("sessions"), 0)),
                        "last_played_at": max(0, _safe_int(playtime.get("last_played_at"), 0)),
                        "captured_at": _now_wall_ts(),
                    },
                    "diagnostics": diagnostics,
                }
            )

        diagnostics = {
            "installed_total": len(records),
            "candidate_total": len(candidates),
            "ignored_total": len(ignored),
            "ignored": ignored,
        }
        return candidates, diagnostics

    async def _download_and_extract_cloud_restore_version(
        self,
        *,
        cookie: str,
        game_key: str,
        version_name: str,
    ) -> Dict[str, Any]:
        """下载并解压指定云存档版本，返回清单与临时路径。"""
        normalized_key = str(game_key or "").strip()
        normalized_version = str(version_name or "").strip()
        if not normalized_key:
            raise TianyiApiError("缺少 game_key")
        if not normalized_version or not normalized_version.lower().endswith(".7z"):
            raise TianyiApiError("版本文件无效，仅支持 .7z")

        listed = await list_cloud_archives(cookie=cookie, remote_folder_parts=[normalized_key])
        files = listed.get("files")
        if not isinstance(files, list):
            files = []

        target_file: Dict[str, Any] = {}
        for item in files:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "") or "").strip()
            if name == normalized_version:
                target_file = dict(item)
                break
        if not target_file:
            raise TianyiApiError("未找到指定版本，请刷新后重试")

        file_id = str(target_file.get("file_id", "") or "").strip()
        if not file_id:
            raise TianyiApiError("云端版本缺少 file_id")

        temp_dir = tempfile.mkdtemp(prefix=f"freedeckcy_cloudrestore_{normalized_key}_")
        archive_path = os.path.join(temp_dir, normalized_version)
        extract_dir = os.path.join(temp_dir, "extracted")
        manifest_path = os.path.join(extract_dir, "manifest.json")
        os.makedirs(extract_dir, exist_ok=True)
        try:
            await download_cloud_archive(
                cookie=cookie,
                file_id=file_id,
                local_file_path=archive_path,
            )
            await asyncio.to_thread(self.seven_zip.extract_archive, archive_path, extract_dir)

            manifest: Dict[str, Any] = {}
            if os.path.isfile(manifest_path):
                try:
                    with open(manifest_path, "r", encoding="utf-8") as fp:
                        loaded = json.load(fp)
                    if isinstance(loaded, dict):
                        manifest = loaded
                except Exception:
                    manifest = {}

            entries = self._normalize_cloud_restore_entries(manifest=manifest, extract_dir=extract_dir)
            return {
                "temp_dir": temp_dir,
                "archive_path": archive_path,
                "extract_dir": extract_dir,
                "manifest_path": manifest_path,
                "manifest": manifest,
                "entries": entries,
                "version_name": normalized_version,
                "game_key": normalized_key,
                "file_id": file_id,
                "cloud_list": listed,
            }
        except Exception:
            self._cleanup_cloud_save_temp_paths([temp_dir])
            raise

    def _resolve_cloud_restore_target_candidates(
        self,
        *,
        game_id: str,
        game_key: str,
        game_title: str,
        entries: Sequence[Dict[str, Any]] = (),
    ) -> Dict[str, Any]:
        """为恢复流程解析当前可用目标目录候选。"""
        records = list(self.store.installed_games or [])
        matched_records: List[TianyiInstalledGame] = []
        for record in records:
            record_game_id = str(record.game_id or "").strip()
            record_title = str(record.game_title or "").strip() or "未命名游戏"
            record_key = self._build_cloud_save_game_key(record_game_id, record_title)
            if game_id and record_game_id and game_id == record_game_id:
                matched_records.append(record)
                continue
            if game_key and record_key and game_key == record_key:
                matched_records.append(record)
                continue

        matched_records.sort(key=lambda item: int(item.updated_at or 0), reverse=True)

        candidates: List[str] = []
        diagnostics: Dict[str, Any] = {
            "matched_records": [],
            "proton_scans": [],
            "fallback_scans": [],
        }

        for record in matched_records:
            install_path = self._normalize_existing_dir(str(record.install_path or "").strip())
            if not install_path:
                continue

            record_game_id = str(record.game_id or "").strip() or str(game_id or "").strip()
            record_title = str(record.game_title or "").strip() or str(game_title or "").strip() or "未命名游戏"
            tokens = self._build_cloud_save_match_tokens(
                game_id=record_game_id,
                game_title=record_title,
                install_path=install_path,
            )

            shortcut_result: Dict[str, Any] = {}
            compat_user_dir = ""
            if record_game_id:
                try:
                    shortcut_result = resolve_tianyi_shortcut_sync(game_id=record_game_id)
                except Exception as exc:
                    shortcut_result = {"ok": False, "message": str(exc)}
                compat_user_dir = self._normalize_existing_dir(str(shortcut_result.get("compat_user_dir", "") or ""))

            diagnostics["matched_records"].append(
                {
                    "game_id": record_game_id,
                    "game_title": record_title,
                    "install_path": install_path,
                    "shortcut": {
                        "ok": bool(shortcut_result.get("ok")),
                        "message": str(shortcut_result.get("message", "") or ""),
                        "appid_unsigned": _safe_int(shortcut_result.get("appid_unsigned"), 0),
                        "compat_user_dir": str(shortcut_result.get("compat_user_dir", "") or ""),
                    },
                }
            )

            if compat_user_dir:
                paths, proton_diag = self._collect_cloud_save_paths_from_proton(
                    compat_user_dir=compat_user_dir,
                    tokens=tokens,
                )
                diagnostics["proton_scans"].append(proton_diag)
                candidates.extend(paths)

                inferred_candidates: List[str] = []
                for entry in list(entries or []):
                    if not isinstance(entry, dict):
                        continue
                    source_path = str(entry.get("source_path", "") or "").strip()
                    archive_rel_path = str(entry.get("archive_rel_path", "") or "").strip().replace("\\", "/").strip("/")
                    relative = self._extract_proton_relative_path(
                        source_path=source_path,
                        archive_rel_path=archive_rel_path,
                    )
                    if not relative:
                        continue
                    inferred_candidates.append(
                        os.path.join(compat_user_dir, *[part for part in relative.split("/") if part]),
                    )

                if inferred_candidates:
                    candidates.extend(inferred_candidates)
                    diagnostics.setdefault("inferred_candidates", [])
                    diagnostics["inferred_candidates"].extend(
                        self._dedupe_paths(inferred_candidates, require_existing=False),
                    )
            else:
                paths, fallback_diag = self._collect_cloud_save_paths_from_install(
                    install_path=install_path,
                    tokens=tokens,
                )
                diagnostics["fallback_scans"].append(fallback_diag)
                candidates.extend(paths)

        merged = self._dedupe_paths(candidates, require_existing=False)
        diagnostics["candidate_count"] = len(merged)
        diagnostics["candidates"] = list(merged)
        return {
            "candidates": merged,
            "diagnostics": diagnostics,
        }

    def _build_restore_copy_plan(
        self,
        *,
        extract_dir: str,
        entries: Sequence[Dict[str, Any]],
        selected_entry_ids: Sequence[str],
        target_dir: str,
        entry_target_dirs: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """将所选存档项映射为复制计划。"""
        extract_root = self._normalize_existing_dir(extract_dir)
        target_root = self._normalize_dir_path(target_dir)
        if not extract_root:
            raise ValueError("解压目录不存在")
        has_entry_targets = isinstance(entry_target_dirs, dict) and bool(entry_target_dirs)
        if not target_root and not has_entry_targets:
            raise ValueError("目标目录无效")

        selected = {str(item or "").strip() for item in list(selected_entry_ids or []) if str(item or "").strip()}
        if not selected:
            raise ValueError("未选择任何存档项")

        normalized_entries = [dict(item) for item in list(entries or []) if isinstance(item, dict)]
        selected_entries = [item for item in normalized_entries if str(item.get("entry_id", "") or "") in selected]
        if not selected_entries:
            raise ValueError("未匹配到所选存档项")

        copy_pairs: List[Tuple[str, str]] = []
        plan_items: List[Dict[str, Any]] = []
        for entry in selected_entries:
            entry_id = str(entry.get("entry_id", "") or "").strip()
            entry_name = str(entry.get("entry_name", "") or entry_id).strip() or entry_id
            rel_path = str(entry.get("archive_rel_path", "") or "").strip().replace("\\", "/").strip("/")
            entry_root = os.path.realpath(os.path.join(extract_root, rel_path)) if rel_path else extract_root
            if not _is_within_dir(entry_root, extract_root):
                continue
            if not os.path.exists(entry_root):
                continue

            preferred_target = ""
            if isinstance(entry_target_dirs, dict):
                preferred_target = str(entry_target_dirs.get(entry_id, "") or "").strip()
            entry_target_root = self._normalize_dir_path(preferred_target) or target_root
            if not entry_target_root:
                continue

            pairs_for_entry: List[Tuple[str, str]] = []
            if os.path.isfile(entry_root):
                if os.path.basename(entry_root) == "manifest.json":
                    continue
                dest = os.path.join(entry_target_root, os.path.basename(entry_root))
                pairs_for_entry.append((entry_root, dest))
            else:
                # 目录型存档：按游戏拆分的目录（SAVEDATA/<TITLEID>、title/<hi>/<lo>）
                # 需要恢复出 entry_name 这一层；共享根（memcards）则直接回填内容。
                target_basename = os.path.basename(os.path.normpath(entry_target_root))
                restore_root = entry_target_root
                if entry_name and entry_name != target_basename:
                    restore_root = os.path.realpath(os.path.join(entry_target_root, entry_name))
                if not _is_within_dir(restore_root, entry_target_root):
                    continue
                for dirpath, _dirnames, filenames in os.walk(entry_root):
                    for filename in filenames:
                        if filename == "manifest.json":
                            continue
                        src_file = os.path.join(dirpath, filename)
                        rel_file = os.path.relpath(src_file, entry_root)
                        dst_file = os.path.realpath(os.path.join(restore_root, rel_file))
                        if not _is_within_dir(dst_file, restore_root):
                            continue
                        pairs_for_entry.append((src_file, dst_file))

            if not pairs_for_entry:
                continue
            copy_pairs.extend(pairs_for_entry)
            plan_items.append(
                {
                    "entry_id": entry_id,
                    "entry_name": entry_name,
                    "file_count": len(pairs_for_entry),
                    "target_dir": entry_target_root,
                }
            )

        if not copy_pairs:
            raise ValueError("选中的存档项没有可恢复文件")

        conflict_paths: List[str] = []
        for _src, dst in copy_pairs:
            if os.path.exists(dst):
                conflict_paths.append(dst)
        dedup_conflicts = sorted(set(conflict_paths))

        return {
            "copy_pairs": copy_pairs,
            "plan_items": plan_items,
            "conflict_count": len(dedup_conflicts),
            "conflict_samples": dedup_conflicts[:CLOUD_SAVE_RESTORE_CONFLICT_SAMPLES],
        }

    def _compute_common_working_dir(self, paths: Sequence[str]) -> str:
        """计算 7z 工作目录。"""
        normalized = [
            os.path.realpath(os.path.expanduser(str(item or "").strip()))
            for item in list(paths or [])
            if str(item or "").strip()
        ]
        if not normalized:
            raise ValueError("缺少待打包路径")
        # 单个目录存档：以父目录为工作目录，归档内保留目录名（PSP/PS3/3DS 恢复需要）。
        if len(normalized) == 1 and os.path.isdir(normalized[0]):
            parent = os.path.dirname(normalized[0])
            if parent and os.path.isdir(parent):
                return parent

        try:
            common = os.path.commonpath(normalized)
        except Exception:
            common = ""
        if common and os.path.isdir(common):
            return common

        first = normalized[0]
        if os.path.isdir(first):
            return first
        parent = os.path.dirname(first)
        if parent and os.path.isdir(parent):
            return parent
        raise ValueError("无法确定打包工作目录")

    def _maybe_schedule_launcher_repair(self) -> None:
        """升级后自动修复已有 3DS 快捷方式（AppImage → Flatpak）。"""
        if self._launcher_repair_done:
            return
        if self._launcher_repair_task is not None and not self._launcher_repair_task.done():
            return
        records = [
            record
            for record in list(self.store.installed_games or [])
            if str(record.platform or "pc") == "3ds" and str(record.rom_path or "").strip()
        ]
        if not records:
            self._launcher_repair_done = True
            return
        self._launcher_repair_task = asyncio.create_task(
            self._repair_emulator_launchers(records),
            name="freedeckcy-repair-3ds-launchers",
        )

    async def _repair_emulator_launchers(self, records: Sequence[Any]) -> None:
        changed = False
        for record in records:
            try:
                command = await ensure_emulator("3ds", self.plugin_dir, allow_download=True)
                wrapper_path = str(record.launcher_path or "").strip()
                if not wrapper_path:
                    wrapper_path = os.path.join(str(record.install_path or ""), "launch-freedeckcy.sh")
                if not wrapper_path:
                    continue
                try:
                    if "org.azahar_emu.Azahar" in Path(wrapper_path).read_text(encoding="utf-8"):
                        continue
                except Exception:
                    pass
                await asyncio.to_thread(
                    create_launch_wrapper,
                    command=command,
                    rom_path=str(record.rom_path or ""),
                    wrapper_path=wrapper_path,
                    platform_name="3ds",
                )
                record.launcher_path = wrapper_path
                record.updated_at = _now_wall_ts()
                changed = True
                config.logger.info("Repaired 3DS launcher for %s -> %s", record.game_title, command[0])
            except Exception as exc:
                config.logger.warning("Repair 3DS launcher failed game=%s: %s", record.game_id, exc)
        self._launcher_repair_done = True
        if changed:
            await asyncio.to_thread(self.store.save)
            self._invalidate_panel_cache(installed=True)

    def _poll_game_watch(self) -> None:
        """后台维护周期里检查游戏进程起停（失败不影响下载/安装）。"""
        try:
            events = self._game_watcher.poll(list(self.store.installed_games or []))
        except Exception as exc:
            config.logger.warning("gamewatch poll failed: %s", exc)
            return
        for event in events:
            if not isinstance(event, dict):
                continue
            if str(event.get("type", "")) == "end":
                record = event.get("record")
                self._maybe_auto_cloud_upload(record)

    def _maybe_auto_cloud_upload(self, record: Any) -> None:
        """游戏退出后按设置自动上传云存档。"""
        if not bool(getattr(self.store.settings, "cloud_save_auto_upload", False)):
            return
        if not str(getattr(self.store.login, "cookie", "") or "").strip():
            return
        if self._cloud_save_task is not None and not self._cloud_save_task.done():
            return
        if self._auto_cloud_upload_task is not None and not self._auto_cloud_upload_task.done():
            return
        now = time.time()
        if now - self._last_auto_cloud_upload_at < 30:
            return
        self._last_auto_cloud_upload_at = now
        title = str(getattr(record, "game_title", "") or getattr(record, "game_id", "") or "game")

        async def _runner() -> None:
            try:
                result = await self.start_cloud_save_upload(
                    game_ids=[str(getattr(record, "game_id", "") or "").strip()]
                )
                config.logger.info(
                    "auto cloud save upload after exit game=%s accepted=%s message=%s",
                    title,
                    bool(result.get("accepted")),
                    str(result.get("message", "")),
                )
            except Exception as exc:
                config.logger.warning("auto cloud save upload failed game=%s: %s", title, exc)

        self._auto_cloud_upload_task = asyncio.create_task(
            _runner(),
            name="freedeckcy-auto-cloud-upload",
        )

    def _cloud_save_fingerprint(self, source_paths: Sequence[str]) -> str:
        """计算存档内容指纹（相对路径 + 大小 + mtime），用于跳过未变化的上传。"""
        digest = hashlib.sha256()
        count = 0
        for raw in list(source_paths or []):
            root = os.path.realpath(os.path.expanduser(str(raw or "").strip()))
            if not root or not os.path.exists(root):
                continue
            if os.path.isfile(root):
                files = [root]
                base = os.path.dirname(root)
            else:
                files = []
                for dirpath, _dirnames, filenames in os.walk(root):
                    for name in filenames:
                        files.append(os.path.join(dirpath, name))
                base = root
            for file_path in sorted(files):
                try:
                    stat = os.stat(file_path)
                except Exception:
                    continue
                rel = os.path.relpath(file_path, base).replace("\\", "/")
                digest.update(f"{rel}|{stat.st_size}|{stat.st_mtime_ns}\n".encode("utf-8"))
                count += 1
                if count >= 5000:
                    break
            if count >= 5000:
                break
        return digest.hexdigest() if count > 0 else ""

    async def _archive_single_game_saves(
        self,
        *,
        candidate: Dict[str, Any],
        timestamp: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """打包单游戏存档并写入 manifest。"""
        game_key = str(candidate.get("game_key", "") or "game")
        game_id = str(candidate.get("game_id", "") or "")
        game_title = str(candidate.get("game_title", "") or "")
        source_paths = [str(path or "") for path in list(candidate.get("source_paths") or []) if str(path or "").strip()]
        playtime_raw = candidate.get("playtime")
        playtime: Dict[str, Any] = playtime_raw if isinstance(playtime_raw, dict) else {}
        if not source_paths:
            raise SevenZipError("缺少可打包的存档目录")

        temp_dir = tempfile.mkdtemp(prefix=f"freedeckcy_cloudsave_{game_key}_")
        archive_name = f"{game_key}_{timestamp}.7z"
        archive_path = os.path.join(temp_dir, archive_name)
        manifest_path = os.path.join(temp_dir, "manifest.json")
        try:
            working_dir = self._compute_common_working_dir(source_paths)

            await asyncio.to_thread(
                self.seven_zip.create_archive,
                archive_path,
                source_paths,
                working_dir,
                excludes=["*.freedeckcy-bak-*"],
            )

            entry_items: List[Dict[str, Any]] = []
            for idx, source_path in enumerate(source_paths, start=1):
                normalized_source = os.path.realpath(os.path.expanduser(str(source_path or "").strip()))
                rel_path = ""
                try:
                    rel_path = os.path.relpath(normalized_source, working_dir).replace("\\", "/")
                except Exception:
                    rel_path = os.path.basename(normalized_source.rstrip("/\\"))
                rel_path = str(rel_path or "").replace("\\", "/").strip("./")
                if not rel_path:
                    rel_path = os.path.basename(normalized_source.rstrip("/\\"))
                entry_name = os.path.basename(normalized_source.rstrip("/\\")).strip() or f"entry_{idx}"
                entry_items.append(
                    {
                        "entry_id": f"entry_{idx}",
                        "name": entry_name,
                        "source_path": normalized_source,
                        "archive_rel_path": rel_path,
                    }
                )

            manifest = {
                "game_id": game_id,
                "game_title": game_title,
                "game_key": game_key,
                "manifest_version": 2,
                "generated_at": _now_wall_ts(),
                "source_paths": list(source_paths),
                "source_strategy": str(candidate.get("source_strategy", "") or ""),
                "install_path": str(candidate.get("install_path", "") or ""),
                "working_dir": working_dir,
                "entries": entry_items,
                "playtime": {
                    "seconds": max(0, _safe_int(playtime.get("seconds"), 0)),
                    "sessions": max(0, _safe_int(playtime.get("sessions"), 0)),
                    "last_played_at": max(0, _safe_int(playtime.get("last_played_at"), 0)),
                    "captured_at": max(0, _safe_int(playtime.get("captured_at"), 0)) or _now_wall_ts(),
                },
            }
            with open(manifest_path, "w", encoding="utf-8") as fp:
                json.dump(manifest, fp, ensure_ascii=False, indent=2)

            await asyncio.to_thread(
                self.seven_zip.create_archive,
                archive_path,
                [manifest_path],
                temp_dir,
            )

            archive_size = 0
            try:
                archive_size = max(0, int(os.path.getsize(archive_path)))
            except Exception:
                archive_size = 0

            return archive_path, {
                "temp_dir": temp_dir,
                "manifest_path": manifest_path,
                "archive_name": archive_name,
                "archive_size_bytes": archive_size,
            }
        except Exception:
            self._cleanup_cloud_save_temp_paths([temp_dir])
            raise

    def _cleanup_cloud_save_temp_paths(self, temp_paths: Sequence[str]) -> None:
        """清理临时文件与目录。"""
        for raw in list(temp_paths or []):
            path = os.path.realpath(os.path.expanduser(str(raw or "").strip()))
            if not path:
                continue
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                elif os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

    async def _run_cloud_save_upload_task(
        self,
        *,
        cookie: str,
        user_account: str,
        game_ids: Optional[Sequence[str]] = None,
    ) -> None:
        """执行云存档上传任务。"""
        started_at = _now_wall_ts()
        timestamp = time.strftime(CLOUD_SAVE_DATE_FORMAT, time.localtime(started_at))
        candidates: List[Dict[str, Any]] = []
        collect_diagnostics: Dict[str, Any] = {}
        results: List[Dict[str, Any]] = []
        uploaded = 0
        skipped = 0
        failed = 0
        final_stage = "completed"
        final_reason = ""
        final_message = "云存档上传完成"
        exception_text = ""
        cancelled = False

        try:
            candidates, collect_diagnostics = await self._collect_cloud_save_candidates()
            wanted_ids = {str(game_id).strip() for game_id in (game_ids or []) if str(game_id).strip()}
            if wanted_ids:
                candidates = [item for item in candidates if str(item.get("game_id", "")).strip() in wanted_ids]
                collect_diagnostics = {
                    **collect_diagnostics,
                    "filtered_game_ids": sorted(wanted_ids),
                }
            total_games = len(candidates)

            await self._set_cloud_save_state(
                stage="scanning",
                running=True,
                message=f"发现 {total_games} 个候选游戏",
                reason="",
                current_game="",
                total_games=total_games,
                processed_games=0,
                uploaded=0,
                skipped=0,
                failed=0,
                progress=0.0 if total_games > 0 else 100.0,
                results=[],
                diagnostics={
                    "started_at": started_at,
                    "timestamp": timestamp,
                    "user_account": user_account,
                    "collect": collect_diagnostics,
                },
            )

            if total_games <= 0:
                final_message = "未找到可上传的已安装游戏"

            for index, candidate in enumerate(candidates, start=1):
                game_title = str(candidate.get("game_title", "") or "未命名游戏")
                game_key = str(candidate.get("game_key", "") or "")
                source_paths = [str(path or "") for path in list(candidate.get("source_paths") or []) if str(path or "").strip()]
                skip_reason = str(candidate.get("skip_reason", "") or "").strip()
                entry: Dict[str, Any] = {
                    "game_id": str(candidate.get("game_id", "") or ""),
                    "game_title": game_title,
                    "game_key": game_key,
                    "status": "",
                    "reason": "",
                    "cloud_path": "",
                    "source_paths": source_paths,
                    "diagnostics": dict(candidate.get("diagnostics") or {}),
                }

                await self._set_cloud_save_state(
                    stage="packaging",
                    running=True,
                    message=f"正在处理 {index}/{total_games}：{game_title}",
                    current_game=game_title,
                )

                fingerprint = ""
                if not skip_reason:
                    try:
                        fingerprint = await asyncio.to_thread(self._cloud_save_fingerprint, source_paths)
                    except Exception:
                        fingerprint = ""
                    if fingerprint and fingerprint == str(self.store.cloud_save_fingerprints.get(game_key, "")):
                        skip_reason = "unchanged"

                if skip_reason:
                    entry["status"] = "skipped"
                    entry["reason"] = skip_reason
                    skipped += 1
                else:
                    cleanup_paths: List[str] = []
                    try:
                        archive_path, archive_meta = await self._archive_single_game_saves(
                            candidate=candidate,
                            timestamp=timestamp,
                        )
                        cleanup_paths.append(str(archive_meta.get("temp_dir", "") or ""))
                        archive_name = str(archive_meta.get("archive_name", "") or "")
                        archive_size = _safe_int(archive_meta.get("archive_size_bytes"), 0)

                        await self._set_cloud_save_state(
                            stage="uploading",
                            running=True,
                            message=f"正在上传 {index}/{total_games}：{game_title}",
                            current_game=game_title,
                        )

                        remote_name = f"{timestamp}.7z"
                        upload_result = await upload_archive_to_cloud(
                            cookie=cookie,
                            local_file_path=archive_path,
                            remote_folder_parts=[game_key],
                            remote_name=remote_name,
                        )

                        cloud_path = str(upload_result.get("cloud_path", "") or "").strip()
                        if not cloud_path:
                            cloud_path = f"/{CLOUD_SAVE_UPLOAD_ROOT}/{game_key}/{remote_name}"

                        entry["status"] = "uploaded"
                        entry["reason"] = ""
                        entry["cloud_path"] = cloud_path
                        entry["diagnostics"] = {
                            **dict(entry.get("diagnostics") or {}),
                            "archive_name": archive_name,
                            "archive_size_bytes": archive_size,
                            "upload_result": dict(upload_result),
                        }
                        uploaded += 1
                        if fingerprint:
                            self.store.cloud_save_fingerprints[game_key] = fingerprint
                    except asyncio.CancelledError:
                        cancelled = True
                        raise
                    except SevenZipError as exc:
                        entry["status"] = "failed"
                        entry["reason"] = "package_failed"
                        entry["diagnostics"] = {
                            **dict(entry.get("diagnostics") or {}),
                            "exception": str(exc),
                        }
                        failed += 1
                    except TianyiApiError as exc:
                        entry["status"] = "failed"
                        entry["reason"] = "upload_failed"
                        entry["diagnostics"] = {
                            **dict(entry.get("diagnostics") or {}),
                            "exception": str(exc),
                            "api_diagnostics": dict(getattr(exc, "diagnostics", {}) or {}),
                        }
                        failed += 1
                    except Exception as exc:
                        entry["status"] = "failed"
                        entry["reason"] = "unexpected_error"
                        entry["diagnostics"] = {
                            **dict(entry.get("diagnostics") or {}),
                            "exception": str(exc),
                        }
                        failed += 1
                    finally:
                        self._cleanup_cloud_save_temp_paths(cleanup_paths)

                results.append(self._copy_cloud_save_result(entry))
                processed = len(results)
                progress = 100.0 if total_games <= 0 else (float(processed) / float(total_games)) * 100.0
                await self._set_cloud_save_state(
                    stage="uploading" if processed < total_games else "scanning",
                    running=True,
                    message=f"已处理 {processed}/{total_games}",
                    current_game=game_title,
                    processed_games=processed,
                    uploaded=uploaded,
                    skipped=skipped,
                    failed=failed,
                    progress=progress,
                    results=results,
                )

                if cancelled:
                    break
        except asyncio.CancelledError:
            cancelled = True
            final_stage = "failed"
            final_reason = "task_cancelled"
            final_message = "云存档上传任务已取消"
        except Exception as exc:
            final_stage = "failed"
            final_reason = "task_exception"
            final_message = f"云存档上传任务异常：{exc}"
            exception_text = str(exc)
            config.logger.exception("Cloud save upload task failed: %s", exc)
        else:
            if failed > 0:
                final_stage = "failed"
                final_reason = "partial_failed"
                final_message = f"云存档上传完成（成功 {uploaded}，失败 {failed}，跳过 {skipped}）"
            else:
                final_stage = "completed"
                final_reason = ""
                final_message = f"云存档上传完成（成功 {uploaded}，跳过 {skipped}）"
        finally:
            finished_at = _now_wall_ts()
            total_games = len(candidates)
            final_payload = {
                "stage": final_stage,
                "reason": final_reason,
                "message": final_message,
                "started_at": started_at,
                "finished_at": finished_at,
                "timestamp": timestamp,
                "total_games": total_games,
                "processed_games": len(results),
                "uploaded": uploaded,
                "skipped": skipped,
                "failed": failed,
                "results": results,
                "diagnostics": {
                    "collect": collect_diagnostics,
                    "exception": exception_text,
                    "cancelled": cancelled,
                },
            }

            try:
                await asyncio.to_thread(self.store.save)
            except Exception as exc:
                config.logger.warning("Persist cloud save fingerprints failed: %s", exc)

            try:
                await asyncio.to_thread(self.store.set_cloud_save_last_result, final_payload)
            except Exception as exc:
                config.logger.warning("Persist cloud save upload result failed: %s", exc)

            await self._set_cloud_save_state(
                stage=final_stage,
                running=False,
                message=final_message,
                reason=final_reason,
                current_game="",
                total_games=total_games,
                processed_games=len(results),
                uploaded=uploaded,
                skipped=skipped,
                failed=failed,
                progress=100.0 if total_games <= 0 else (float(len(results)) / float(total_games)) * 100.0,
                results=results,
                diagnostics={
                    "collect": collect_diagnostics,
                    "exception": exception_text,
                    "cancelled": cancelled,
                },
                last_result=final_payload,
            )

            async with self._cloud_save_lock:
                current = asyncio.current_task()
                if self._cloud_save_task is current:
                    self._cloud_save_task = None

            if cancelled:
                raise asyncio.CancelledError()

    def _resolve_record_app_id(self, record: TianyiInstalledGame) -> int:
        """已安装记录对应的 Steam AppID（缺失时回查快捷方式）。"""
        app_id = max(0, _safe_int(record.steam_app_id, 0))
        if app_id > 0:
            return app_id
        try:
            result = resolve_tianyi_shortcut_sync(game_id=str(record.game_id or ""))
        except Exception:
            result = {}
        return max(0, _safe_int(result.get("appid_unsigned"), 0))

    def _can_remove_compatdata_dir(self, path: str, app_id: int) -> bool:
        """只允许删除 <library>/steamapps/compatdata/<appid> 这种结构。"""
        resolved = os.path.realpath(os.path.expanduser(str(path or "").strip()))
        if not resolved or os.path.islink(resolved) or not os.path.isdir(resolved):
            return False
        parts = resolved.replace("\\", "/").split("/")
        if len(parts) < 4:
            return False
        return parts[-3] == "steamapps" and parts[-2] == "compatdata" and parts[-1] == str(int(app_id))

    async def preview_uninstall(self, *, game_id: str = "", install_path: str = "") -> Dict[str, Any]:
        """卸载前预览：安装目录与 Proton 前缀各占多少空间。"""
        record = self._find_installed_record(game_id=str(game_id or "").strip(), install_path=str(install_path or "").strip())
        if record is None:
            raise ValueError("未找到已安装游戏记录")

        resolved_path = os.path.realpath(os.path.expanduser(str(record.install_path or "").strip()))
        install_size = await asyncio.to_thread(_dir_size_bytes, resolved_path)
        app_id = self._resolve_record_app_id(record)
        compat_dirs: List[str] = []
        compat_size = 0
        if app_id > 0:
            compat_dirs = await asyncio.to_thread(find_compatdata_dirs, app_id)
            for compat_dir in compat_dirs:
                compat_size += await asyncio.to_thread(_dir_size_bytes, compat_dir)

        return {
            "game_id": str(record.game_id or ""),
            "title": str(record.game_title or ""),
            "install_path": str(record.install_path or ""),
            "install_size_bytes": int(install_size),
            "steam_app_id": int(app_id),
            "compatdata_paths": list(compat_dirs),
            "compatdata_size_bytes": int(compat_size),
        }

    async def uninstall_installed_game(
        self,
        *,
        game_id: str = "",
        install_path: str = "",
        delete_files: bool = True,
        delete_compatdata: bool = False,
    ) -> Dict[str, Any]:
        """卸载已安装游戏；与同目录的安装收尾串行，避免解压/注册竞态。"""
        record = self._find_installed_record(
            game_id=str(game_id or "").strip(),
            install_path=str(install_path or "").strip(),
        )
        if record is None:
            raise ValueError("未找到已安装游戏记录")
        async with self._install_lock_for(str(record.install_path or "")):
            return await self._uninstall_installed_game_impl(
                game_id=game_id,
                install_path=install_path,
                delete_files=delete_files,
                delete_compatdata=delete_compatdata,
                record=record,
            )

    async def _uninstall_installed_game_impl(
        self,
        *,
        game_id: str = "",
        install_path: str = "",
        delete_files: bool = True,
        delete_compatdata: bool = False,
        record: Optional[TianyiInstalledGame] = None,
    ) -> Dict[str, Any]:
        """卸载实现（调用方需持有安装目录锁）。

        `record` 由加锁前的初始查询传入：等锁期间记录可能被另一路卸载/面板清理删掉，
        此时继续用初始记录完成剩余清理，避免“文件已删但接口报错、Steam 快捷方式残留”。
        """
        target_game_id = str(game_id or "").strip()
        target_install_path = str(install_path or "").strip()
        if not target_game_id and not target_install_path:
            raise ValueError("缺少卸载目标")

        record = self._find_installed_record(game_id=target_game_id, install_path=target_install_path) or record
        if record is None:
            raise ValueError("未找到已安装游戏记录")

        resolved_path = os.path.realpath(os.path.expanduser(str(record.install_path or "").strip()))
        removed_files = False
        if bool(delete_files):
            allow, reason = self._can_remove_install_path(resolved_path)
            if not allow:
                raise ValueError(reason or "卸载路径不安全，已拒绝删除")

            if os.path.lexists(resolved_path):
                try:
                    if os.path.islink(resolved_path) or os.path.isfile(resolved_path):
                        os.remove(resolved_path)
                    elif os.path.isdir(resolved_path):
                        shutil.rmtree(resolved_path, ignore_errors=False)
                    else:
                        os.remove(resolved_path)
                    removed_files = True
                except Exception as exc:
                    raise RuntimeError(f"删除安装文件失败: {exc}") from exc

        compatdata_cleanup: Dict[str, Any] = {
            "requested": bool(delete_compatdata),
            "app_id": 0,
            "paths": [],
            "removed_paths": [],
            "freed_bytes": 0,
        }
        compatdata_warning = ""
        if bool(delete_compatdata):
            app_id = self._resolve_record_app_id(record)
            compatdata_cleanup["app_id"] = int(app_id)
            if app_id > 0:
                compat_dirs = await asyncio.to_thread(find_compatdata_dirs, app_id)
                compatdata_cleanup["paths"] = list(compat_dirs)
                for compat_dir in compat_dirs:
                    if not self._can_remove_compatdata_dir(compat_dir, app_id):
                        compatdata_warning = "Proton 前缀路径校验失败，已跳过删除"
                        continue
                    size_bytes = await asyncio.to_thread(_dir_size_bytes, compat_dir)
                    try:
                        await asyncio.to_thread(shutil.rmtree, compat_dir)
                    except Exception as exc:
                        compatdata_warning = f"删除 Proton 前缀失败: {exc}"
                        continue
                    compatdata_cleanup["removed_paths"].append(compat_dir)
                    compatdata_cleanup["freed_bytes"] += int(size_bytes)
            else:
                compatdata_warning = "未找到 Steam AppID，跳过 Proton 前缀清理"

        removed = await asyncio.to_thread(
            self.store.remove_installed_game,
            game_id=record.game_id,
            install_path=record.install_path,
        )
        persist_warning = ""
        if removed is None:
            # 某些异常场景下 remove 可能返回空，回退为内存移除避免前端直接报错。
            removed = self._remove_installed_record_in_memory(
                game_id=record.game_id,
                install_path=record.install_path,
            )
            if removed is not None:
                try:
                    await asyncio.to_thread(self.store.save)
                except Exception as exc:
                    persist_warning = str(exc)
                    config.logger.warning("Installed record fallback save failed: %s", exc)
            else:
                # 记录已被并发清理（另一路卸载/面板刷新裁剪掉已删目录）：
                # 文件都删完了，继续清理 Steam 快捷方式即可，不要在这里报错。
                removed = record
                config.logger.info(
                    "Uninstall record already gone, continue cleanup game=%s path=%s",
                    record.game_id,
                    record.install_path,
                )

        steam_cleanup: Dict[str, Any] = {}
        steam_warning = ""
        record_game_id = str(record.game_id or "").strip()
        if record_game_id:
            try:
                steam_cleanup = await remove_tianyi_shortcut(game_id=record_game_id)
            except Exception as exc:
                steam_cleanup = {"ok": False, "removed": False, "message": str(exc)}

            if not bool(steam_cleanup.get("ok")):
                steam_warning = f"Steam 快捷方式清理失败：{str(steam_cleanup.get('message', '') or '未知错误')}"
            elif not bool(steam_cleanup.get("cleanup_ok", True)):
                steam_warning = "Steam 快捷方式已删除，但 Proton 映射或封面清理失败"
        else:
            steam_cleanup = {"ok": False, "removed": False, "message": "缺少 game_id，跳过 Steam 快捷方式清理"}
            steam_warning = "Steam 快捷方式清理已跳过：缺少 game_id"

        removed_key = self._installed_record_session_key(record)
        if removed_key:
            async with self._playtime_lock:
                self._playtime_sessions.pop(removed_key, None)

        self._invalidate_panel_cache(installed=True)
        summary = self._build_installed_summary(limit=60, persist=False)
        self._panel_installed_cache = {
            "total": int(summary.get("total", 0) or 0),
            "preview": list(summary.get("preview") or []),
        }
        self._panel_installed_cache_at = time.monotonic()
        response: Dict[str, Any] = {
            "removed": True,
            "game_id": str(record.game_id or ""),
            "title": str(record.game_title or ""),
            "install_path": str(record.install_path or ""),
            "files_deleted": bool(removed_files),
            "installed": summary,
            "steam": steam_cleanup,
            "compatdata": compatdata_cleanup,
        }
        warnings: List[str] = []
        if persist_warning:
            warnings.append(f"卸载记录回退保存失败：{persist_warning}")
        if steam_warning:
            warnings.append(steam_warning)
        if compatdata_warning:
            warnings.append(compatdata_warning)
        if warnings:
            response["warning"] = "；".join(warnings)
        return response

    async def update_settings(
        self,
        *,
        download_dir: Optional[str] = None,
        install_dir: Optional[str] = None,
        split_count: Optional[int] = None,
        page_size: Optional[int] = None,
        auto_delete_package: Optional[bool] = None,
        auto_install: Optional[bool] = None,
        proton_tool: Optional[str] = None,
        cloud_save_auto_upload: Optional[bool] = None,
        cloud_save_include_emulators: Optional[bool] = None,
        catalog_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """更新下载设置。"""
        if download_dir is not None:
            raw = str(download_dir).strip()
            if not raw:
                raise ValueError("下载目录不能为空")
            path = os.path.realpath(os.path.expanduser(raw))
            if not path:
                raise ValueError("下载目录无效")
            os.makedirs(path, exist_ok=True)
            download_dir = path
            # 同步插件原有下载目录，避免路径分裂。
            self.plugin.downloads_dir = path
            await self.plugin.set_download_dir(path)
        if install_dir is not None:
            raw = str(install_dir).strip()
            if not raw:
                raise ValueError("安装目录不能为空")
            path = os.path.realpath(os.path.expanduser(raw))
            if not path:
                raise ValueError("安装目录无效")
            os.makedirs(path, exist_ok=True)
            install_dir = path

        self.store.set_settings(
            download_dir=download_dir,
            install_dir=install_dir,
            split_count=split_count,
            page_size=page_size,
            auto_delete_package=auto_delete_package,
            auto_install=True,
            proton_tool=proton_tool,
            cloud_save_auto_upload=cloud_save_auto_upload,
            cloud_save_include_emulators=cloud_save_include_emulators,
            catalog_url=catalog_url,
        )
        self._invalidate_panel_cache(all_data=True)
        return asdict(self.store.settings)

    async def prepare_install(
        self,
        *,
        game_id: str = "",
        share_url: str = "",
        file_ids: Optional[Sequence[str]] = None,
        download_dir: Optional[str] = None,
        install_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """生成安装前确认数据（不创建任务）。"""
        return await self._build_install_plan(
            game_id=game_id,
            share_url=share_url,
            file_ids=file_ids,
            download_dir=download_dir,
            install_dir=install_dir,
        )

    async def start_install(
        self,
        *,
        game_id: str = "",
        share_url: str = "",
        file_ids: Optional[Sequence[str]] = None,
        split_count: Optional[int] = None,
        download_dir: Optional[str] = None,
        install_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """确认后创建下载任务并进入安装链路。"""
        async with self._lock:
            plan = await self._build_install_plan(
                game_id=game_id,
                share_url=share_url,
                file_ids=file_ids,
                download_dir=download_dir,
                install_dir=install_dir,
            )
            if not bool(plan.get("can_install")):
                raise TianyiApiError("空间不足，无法开始安装")

            settings = self.store.settings
            split = int(split_count or settings.split_count or 16)
            split = max(1, min(64, split))

            plan_game_id = str(plan.get("game_id", "") or game_id or "").strip()
            if plan_game_id:
                active_existing = [
                    task for task in list(self.store.tasks)
                    if str(task.game_id or "").strip() == plan_game_id
                    and (
                        not _is_terminal(task.status)
                        # 下载完成但还没安装完的任务仍是“活动安装”，不能再建一份下载。
                        or (
                            str(task.status or "") == "complete"
                            and not bool(task.post_processed)
                        )
                    )
                ]
                if active_existing:
                    # 双击/双入口重复安装：复用正在下载的任务，避免两个 aria2 写同一文件。
                    return {
                        "plan": plan,
                        "tasks": [_task_to_view(task) for task in active_existing],
                        "reused": True,
                    }

            async with self._refresh_lock:
                created = await self._create_tasks_from_plan(plan=plan, split=split)
                self.store.upsert_tasks(created)
                self._invalidate_panel_cache(tasks=True)
            await self.refresh_tasks(sync_aria2=True)

            created_ids = {task.task_id for task in created}
            created_view = [_task_to_view(task) for task in self.store.tasks if task.task_id in created_ids]
            return {
                "plan": plan,
                "tasks": created_view,
            }

    async def create_tasks_for_game(
        self,
        *,
        game_id: str = "",
        share_url: str = "",
        file_ids: Optional[Sequence[str]] = None,
        split_count: Optional[int] = None,
        download_dir: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """兼容旧接口：直接创建下载任务。"""
        result = await self.start_install(
            game_id=game_id,
            share_url=share_url,
            file_ids=file_ids,
            split_count=split_count,
            download_dir=download_dir,
            install_dir=None,
        )
        tasks = result.get("tasks")
        if isinstance(tasks, list):
            return [item for item in tasks if isinstance(item, dict)]
        return []

    async def _build_install_plan(
        self,
        *,
        game_id: str = "",
        share_url: str = "",
        file_ids: Optional[Sequence[str]] = None,
        download_dir: Optional[str] = None,
        install_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """构建安装计划与空间探针信息。"""
        open_path = ""
        executable_name = ""
        platform = "pc"
        if not share_url:
            item = self.catalog.get_by_game_id(game_id)
            if not item:
                raise ValueError("未找到对应游戏条目")
            share_url = item.down_url
            game_title = item.title
            game_id = item.game_id
            open_path = str(item.openpath or "")
            executable_name = str(getattr(item, "executable_name", "") or "")
            platform = str(item.platform or "pc")
        else:
            normalized_share_url = str(share_url or "").strip()
            if not _share_provider(normalized_share_url):
                raise ValueError("只支持天翼云盘（cloud.189.cn）或百度网盘（pan.baidu.com）分享链接")
            matched_item = None
            for entry in self.catalog.entries:
                if game_id and str(entry.game_id) != str(game_id):
                    continue
                if str(entry.down_url or "").strip() == normalized_share_url:
                    matched_item = entry
                    break
            if matched_item is None:
                for entry in self.catalog.entries:
                    if str(entry.down_url or "").strip() == normalized_share_url:
                        matched_item = entry
                        break

            if matched_item is not None:
                game_title = str(matched_item.title or game_id or "自定义分享")
                game_id = str(matched_item.game_id or game_id or normalized_share_url)
                open_path = str(matched_item.openpath or "")
                executable_name = str(getattr(matched_item, "executable_name", "") or "")
                platform = str(matched_item.platform or "pc")
                if "pwd=" not in normalized_share_url and str(matched_item.pwd or "").strip():
                    joiner = "&" if "?" in normalized_share_url else "?"
                    normalized_share_url = f"{normalized_share_url}{joiner}pwd={matched_item.pwd.strip()}"
                share_url = normalized_share_url
            else:
                game_title = game_id or "自定义分享"
                game_id = game_id or normalized_share_url

        platform = str(platform or "pc").strip().lower() or "pc"
        emulator = emulator_name_for_platform(platform)
        if platform != "pc" and not emulator:
            raise ValueError(
                f"当前只支持 PC 与已接入模拟器的平台（GBA/PSP/NDS/PS1/FC/MD/3DS/PS2/PS3/Switch），{platform.upper()} 暂未接入模拟器"
            )
        emulator_info: Dict[str, Any] = {}
        if emulator:
            emulator_info = await asyncio.to_thread(emulator_status, platform, self.plugin_dir)
            if not emulator_info.get("available"):
                raise ValueError(str(emulator_info.get("message") or "mGBA 不可用"))

        settings = self.store.settings
        target_download = (download_dir or settings.download_dir or self.plugin.downloads_dir).strip()
        if not target_download:
            raise ValueError("下载目录为空")
        target_download = os.path.realpath(os.path.expanduser(target_download))
        os.makedirs(target_download, exist_ok=True)

        target_install = (install_dir or settings.install_dir or target_download).strip()
        if not target_install:
            raise ValueError("安装目录为空")
        target_install = os.path.realpath(os.path.expanduser(target_install))
        os.makedirs(target_install, exist_ok=True)

        rom_target = ""
        if emulator:
            rom_target = os.path.basename(str(open_path or "").replace("\\", "/")).strip()
            if not rom_target:
                raise ValueError("资源缺少 ROM 文件名（openpath），无法从分享中定位文件")
        provider = _share_provider(share_url)
        if not provider:
            raise ValueError("分享链接来源不受支持")
        share_ctx: Dict[str, Any] = {}
        if provider == "baidu":
            baidu_cookie = str(self.store.baidu_login.cookie or "").strip()
            if "BDUSS=" in baidu_cookie.upper():
                provider = "baidu"
            elif self.store.baidu_openapi.configured:
                provider = "baidu_openapi"
            else:
                raise TianyiApiError("请先扫码登录百度网盘（设置 → 百度网盘扫码登录）")
        if provider == "tianyi":
            login_ok, _, message = await self.check_login_state()
            if not login_ok:
                raise TianyiApiError(message or "请先登录天翼账号")
            try:
                resolved = await resolve_share(
                    share_url,
                    self.store.login.cookie,
                    target_name=rom_target,
                )
            except TianyiApiError as exc:
                diagnostics = dict(getattr(exc, "diagnostics", {}) or {})
                diagnostics.setdefault("stage", "resolve_share")
                raise TianyiApiError(str(exc), diagnostics=diagnostics) from exc
        elif provider == "baidu":
            baidu_cookie = str(self.store.baidu_login.cookie or "").strip()
            try:
                resolved, share_ctx = await resolve_baidu_share(share_url, baidu_cookie)
            except BaiduApiError as exc:
                diagnostics = dict(getattr(exc, "diagnostics", {}) or {})
                diagnostics.setdefault("stage", "baidu_resolve_share")
                raise TianyiApiError(f"百度网盘解析失败：{exc}", diagnostics=diagnostics) from exc
        else:
            try:
                await self._ensure_baidu_openapi_access_token()
                resolved, share_ctx = await resolve_baidu_openapi_share_url(share_url=share_url)
            except BaiduOpenApiError as exc:
                diagnostics = dict(getattr(exc, "diagnostics", {}) or {})
                diagnostics.setdefault("stage", "baidu_resolve_share")
                raise TianyiApiError(f"百度网盘解析失败：{exc}", diagnostics=diagnostics) from exc
        if emulator:
            target_key = os.path.basename(rom_target).lower()
            matched = [
                file_item
                for file_item in resolved.files
                if not file_item.is_folder
                and os.path.basename(str(file_item.name or "")).lower() == target_key
            ]
            if not matched:
                sample = "、".join(
                    str(file_item.name or "")
                    for file_item in resolved.files
                    if not file_item.is_folder
                )[:300]
                raise TianyiApiError(
                    f"分享中没有找到 ROM「{rom_target}」，可能资源包已更新。"
                    + (f" 已扫描示例：{sample}" if sample else "")
                )
            files = matched[:1]
        else:
            selected = {str(v).strip() for v in (file_ids or []) if str(v).strip()}
            files = [
                file_item
                for file_item in resolved.files
                if not file_item.is_folder and (not selected or file_item.file_id in selected)
            ]
        if not files:
            raise TianyiApiError("未找到可下载文件，可能所选条目是目录")

        required_download_bytes = sum(max(0, int(file_item.size or 0)) for file_item in files)
        required_install_bytes = required_download_bytes
        # 解压后通常比压缩包大，给用户一个估算值（不作为硬性拦截，避免误伤高压缩比资源）。
        required_install_estimate_bytes = int(required_download_bytes * INSTALL_SPACE_ESTIMATE_FACTOR)
        free_download_bytes = _disk_free_bytes(target_download)
        free_install_bytes = _disk_free_bytes(target_install)
        download_dir_ok = free_download_bytes >= required_download_bytes
        install_dir_ok = free_install_bytes >= required_install_bytes
        can_install = bool(download_dir_ok and install_dir_ok)
        same_storage = os.path.realpath(target_download) == os.path.realpath(target_install)
        # 同一块盘时，压缩包和解压内容会同时存在，估算值要叠加。
        install_estimate_required_bytes = required_install_estimate_bytes
        if same_storage:
            install_estimate_required_bytes = required_download_bytes + required_install_estimate_bytes
        install_estimate_ok = free_install_bytes >= install_estimate_required_bytes

        plan_files: List[Dict[str, Any]] = []
        for file_item in files:
            plan_files.append(
                {
                    "file_id": str(file_item.file_id or ""),
                    "name": str(file_item.name or ""),
                    "size": max(0, int(file_item.size or 0)),
                    "is_folder": bool(file_item.is_folder),
                }
            )

        return {
            "game_id": game_id,
            "game_title": game_title,
            "provider": provider,
            "share_ctx": share_ctx,
            "platform": platform,
            "emulator": emulator,
            "emulator_info": emulator_info,
            "rom_target": rom_target,
            "openpath": open_path,
            "executable_name": executable_name,
            "share_url": share_url,
            "share_code": resolved.share_code,
            "share_id": resolved.share_id,
            "pwd": resolved.pwd,
            "download_dir": target_download,
            "install_dir": target_install,
            "required_download_bytes": required_download_bytes,
            "required_install_bytes": required_install_bytes,
            "required_download_human": _format_size_bytes(required_download_bytes),
            "required_install_human": _format_size_bytes(required_install_bytes),
            "free_download_bytes": free_download_bytes,
            "free_install_bytes": free_install_bytes,
            "free_download_human": _format_size_bytes(free_download_bytes),
            "free_install_human": _format_size_bytes(free_install_bytes),
            "required_install_estimate_bytes": required_install_estimate_bytes,
            "required_install_estimate_human": _format_size_bytes(required_install_estimate_bytes),
            "install_estimate_required_bytes": install_estimate_required_bytes,
            "install_estimate_required_human": _format_size_bytes(install_estimate_required_bytes),
            "install_estimate_ok": install_estimate_ok,
            "same_storage": bool(same_storage),
            "download_dir_ok": download_dir_ok,
            "install_dir_ok": install_dir_ok,
            "can_install": can_install,
            "file_count": len(plan_files),
            "files": plan_files,
        }

    def _compact_baidu_share_ctx(self, share_ctx: Dict[str, Any]) -> Dict[str, Any]:
        """持久化任务时去掉 dlink（内含 access_token），只保留重新取链所需字段。"""
        if not isinstance(share_ctx, dict):
            return {}
        result = {
            key: value
            for key, value in share_ctx.items()
            if key not in {"files", "dlink"} and not str(key).startswith("_")
        }
        files: Dict[str, Any] = {}
        raw_files = share_ctx.get("files")
        if isinstance(raw_files, dict):
            for file_id, meta in raw_files.items():
                if not isinstance(meta, dict):
                    continue
                files[str(file_id)] = {
                    key: value
                    for key, value in meta.items()
                    if key not in {"dlink"} and not str(key).startswith("_")
                }
        result["files"] = files
        return result

    async def _fetch_baidu_web_direct_url(self, share_ctx: Dict[str, Any], file_id: str, file_name: str = "") -> str:
        cookie = str(self.store.baidu_login.cookie or "").strip()
        if "BDUSS=" not in cookie.upper():
            raise BaiduApiError("未登录百度网盘，请先扫码登录", diagnostics={"stage": "login"})
        return await fetch_baidu_download_url(cookie, share_ctx, file_id, file_name=file_name)

    async def _fetch_baidu_direct_url(self, share_ctx: Dict[str, Any], file_id: str) -> str:
        access_token = await self._ensure_baidu_openapi_access_token()
        try:
            return await fetch_baidu_openapi_download_url(
                access_token=access_token,
                share_ctx=share_ctx,
                file_id=file_id,
            )
        except BaiduOpenApiError as exc:
            if not is_baidu_openapi_auth_error(exc):
                raise
            access_token = await self._ensure_baidu_openapi_access_token(force_refresh=True)
            return await fetch_baidu_openapi_download_url(
                access_token=access_token,
                share_ctx=share_ctx,
                file_id=file_id,
            )

    async def _create_tasks_from_plan(self, *, plan: Dict[str, Any], split: int) -> List[TianyiTaskRecord]:
        """根据安装计划创建 aria2 下载任务。"""
        await self.aria2.ensure_running()
        await self.apply_saved_download_speed_limit()
        provider = str(plan.get("provider", "tianyi") or "tianyi").strip()
        share_ctx = plan.get("share_ctx") if isinstance(plan.get("share_ctx"), dict) else {}
        share_url = str(plan.get("share_url", "") or "").strip()
        access_token = ""
        if provider == "tianyi":
            access_token = await fetch_access_token(self.store.login.cookie)

        share_id = str(plan.get("share_id", "")).strip()
        share_code = str(plan.get("share_code", "")).strip()
        game_id = str(plan.get("game_id", "")).strip()
        game_title = str(plan.get("game_title", "")).strip() or game_id or "未命名游戏"
        open_path = str(plan.get("openpath", "") or "")
        executable_name = str(plan.get("executable_name", "") or "")
        target_dir = str(plan.get("download_dir", "")).strip()

        plan_files = [
            item
            for item in list(plan.get("files", []))
            if isinstance(item, dict) and str(item.get("file_id", "")).strip()
        ]
        # 同一安装计划（尤其是分卷/多包）共用一个 group_id：全部下载完成后才一起安装。
        group_id = uuid.uuid4().hex if plan_files else ""
        group_total = len(plan_files)

        created: List[TianyiTaskRecord] = []
        try:
            for file_item in plan_files:
                file_id = str(file_item.get("file_id", "")).strip()
                name = str(file_item.get("name", "")).strip() or f"file-{file_id}"
                file_size = max(0, _safe_int(file_item.get("size"), 0))

                if provider == "baidu":
                    direct_url = await self._fetch_baidu_web_direct_url(share_ctx, file_id, name)
                    gid = await self.aria2.add_uri(
                        direct_url=direct_url,
                        cookie=str(self.store.baidu_login.cookie or "").strip(),
                        download_dir=target_dir,
                        out_name=name,
                        split=split,
                        referer="https://pan.baidu.com/disk/home",
                        user_agent="pan.baidu.com",
                    )
                elif provider == "baidu_openapi":
                    direct_url = await self._fetch_baidu_direct_url(share_ctx, file_id)
                    gid = await self.aria2.add_uri(
                        direct_url=direct_url,
                        cookie="",
                        download_dir=target_dir,
                        out_name=name,
                        split=split,
                        referer="https://pan.baidu.com/disk/home",
                        user_agent="pan.baidu.com",
                    )
                else:
                    direct_url = await fetch_download_url(
                        self.store.login.cookie,
                        access_token,
                        share_id,
                        file_id,
                    )
                    gid = await self.aria2.add_uri(
                        direct_url=direct_url,
                        cookie=self.store.login.cookie,
                        download_dir=target_dir,
                        out_name=name,
                        split=split,
                    )
                now = _now_wall_ts()
                created.append(
                    TianyiTaskRecord(
                        task_id=str(uuid.uuid4()),
                        gid=gid,
                        game_id=game_id,
                        game_title=game_title,
                        share_code=share_code,
                        share_id=share_id,
                        file_id=file_id,
                        file_name=name,
                        download_dir=target_dir,
                        local_path=os.path.join(target_dir, name),
                        status="waiting",
                        progress=0.0,
                        speed=0,
                        openpath=open_path,
                        executable_name=executable_name,
                        file_size=file_size,
                        group_id=group_id,
                        group_total=group_total,
                        platform=str(plan.get("platform", "pc") or "pc"),
                        provider=provider,
                        share_url=share_url,
                        share_ctx=self._compact_baidu_share_ctx(share_ctx) if provider in {"baidu", "baidu_openapi"} else {},
                        created_at=now,
                        updated_at=now,
                    )
                )
        except Exception:
            # 任一分卷/文件失败：回滚已加入 aria2 的任务，避免孤儿下载。
            for _task in created:
                try:
                    await self.aria2.remove(str(_task.gid or ""))
                except Exception:
                    pass
            raise
        return created

    def _tasks_persist_signature(self, tasks: Sequence[TianyiTaskRecord]) -> tuple:
        """任务列表的持久化指纹，用于避免后台维护每轮都重写 state.json。"""
        return tuple(
            (
                task.task_id,
                task.status,
                round(float(task.progress or 0.0), 2),
                int(task.speed or 0),
                task.error_reason,
                task.install_status,
                task.install_message,
                bool(task.post_processed),
                task.installed_path,
                int(task.updated_at or 0),
            )
            for task in tasks
        )

    def _task_local_path(self, task: TianyiTaskRecord) -> str:
        """任务最终落盘路径（兼容旧记录里 local_path 为空的情况）。"""
        local_path = str(task.local_path or "").strip()
        if not local_path:
            local_path = os.path.join(str(task.download_dir or "").strip(), str(task.file_name or "").strip())
        if not local_path:
            return ""
        return os.path.realpath(os.path.expanduser(local_path))

    def _file_matches_expected_size(self, task: TianyiTaskRecord) -> bool:
        """文件是否已存在且大小与资源记录一致（用于重启后判定“其实已下完”）。"""
        expected = max(0, _safe_int(task.file_size, 0))
        path = self._task_local_path(task)
        if expected <= 0 or not path or not os.path.isfile(path):
            return False
        try:
            return int(os.path.getsize(path)) == expected
        except Exception:
            return False

    def _verify_downloaded_file(self, task: TianyiTaskRecord) -> Tuple[bool, str]:
        """下载完整性校验：按资源记录的文件大小比对实际落盘大小。"""
        expected = max(0, _safe_int(task.file_size, 0))
        if expected <= 0:
            return True, ""
        path = self._task_local_path(task)
        if not path or not os.path.isfile(path):
            return False, "下载文件缺失"
        try:
            actual = int(os.path.getsize(path))
        except Exception as exc:
            return False, f"无法读取下载文件大小: {exc}"
        if actual != expected:
            return False, (
                f"文件大小校验失败：期望 {_format_size_bytes(expected)}，实际 {_format_size_bytes(actual)}；"
                "文件可能不完整，请移除任务后重新下载"
            )
        return True, ""

    def clear_catalog_update_notice(self) -> Dict[str, Any]:
        """清除目录更新提示（前端弹窗后调用）。"""
        self._catalog_update_notice = {}
        return {"ok": True, "pending": False}

    def clear_steam_restart_pending(self) -> Dict[str, Any]:
        """清除安装完成后的重启提示状态。"""
        self._steam_restart_pending = {}
        return {"ok": True, "pending": False}

    def _recover_unfinished_install_tasks(self) -> int:
        """恢复旧版本留下的“已下载完成但安装失败”任务。

        v0.26.1 及更早版本在安装收尾异常时会把 ``post_processed=True``，
        但并没有真正完成安装；升级后这些任务会永远不再调度。
        """
        installed_games = {
            str(record.game_id or "").strip()
            for record in list(self.store.installed_games)
            if str(record.game_id or "").strip()
        }
        recovered = 0
        for task in list(self.store.tasks):
            if str(task.status or "") != "complete" or not bool(task.post_processed):
                continue
            if str(task.install_status or "pending") not in {"failed", "pending"}:
                continue
            game_id = str(task.game_id or "").strip()
            installed_path = str(task.installed_path or "").strip()
            if game_id and game_id in installed_games:
                continue
            if installed_path and os.path.isdir(installed_path):
                continue
            task.post_processed = False
            task.install_status = "pending"
            task.install_message = "检测到上次安装未完成，已重新排队"
            task.updated_at = _now_wall_ts()
            recovered += 1
        if recovered:
            config.logger.info("恢复 %s 个未完成安装任务", recovered)
        return recovered

    def _install_group_members(self, task: TianyiTaskRecord) -> List[TianyiTaskRecord]:
        """同一安装计划（分卷/多包）的全部任务；无分组时只有自己。"""
        group_id = str(getattr(task, "group_id", "") or "").strip()
        if not group_id:
            return [task]
        members = [
            item
            for item in list(self.store.tasks)
            if str(getattr(item, "group_id", "") or "").strip() == group_id
            and str(item.status or "") != "removed"
        ]
        if not members:
            return [task]
        members.sort(key=lambda item: (int(item.created_at or 0), str(item.task_id or "")))
        return members

    @staticmethod
    def _group_install_lead(members: Sequence[TianyiTaskRecord]) -> TianyiTaskRecord:
        """安装收尾的 lead：优先主卷/入口文件（非 bundled 成员）。

        分卷任务的排序是 created_at+task_id，同秒创建且非主卷 task_id 更小时，
        members[0] 会是非主卷；若直接拿它当 lead，收尾会把它的 ``bundled``
        状态覆盖成 ``installed``（展示语义错误），也可能让 Steam 注册用错文件。
        """
        candidates = list(members or [])
        for member in candidates:
            if str(member.install_status or "") != "bundled":
                return member
        return candidates[0]

    @staticmethod
    def _post_process_group_key(task: TianyiTaskRecord) -> str:
        return str(task.group_id or task.task_id or "").strip()

    def _post_process_backoff_active(self, task: TianyiTaskRecord) -> bool:
        key = self._post_process_group_key(task)
        state = self._post_process_failures.get(key)
        if not state:
            return False
        return float(state.get("next_retry_at", 0) or 0) > time.time()

    def _record_post_process_failure(self, task: TianyiTaskRecord, exc: Exception) -> int:
        """记录一次安装收尾失败并返回累计失败次数（用于判定是否放弃自动重试）。"""
        key = self._post_process_group_key(task)
        state = self._post_process_failures.get(key) or {"count": 0}
        count = int(state.get("count", 0) or 0) + 1
        delay = min(300.0, 8.0 * (2 ** min(count, 5)))
        self._post_process_failures[key] = {
            "count": count,
            "last_error": str(exc)[:300],
            "next_retry_at": time.time() + delay,
        }
        config.logger.warning("Post-process backoff group=%s count=%s next=%ss: %s", key, count, int(delay), exc)
        return count

    def _clear_post_process_failure(self, task: TianyiTaskRecord) -> None:
        self._post_process_failures.pop(self._post_process_group_key(task), None)

    def _give_up_post_process(self, task: TianyiTaskRecord, exc: Exception, *, attempt: int) -> None:
        """自动重试次数用尽：标记终态失败并停止调度，避免永久重试。

        安装根不可用/磁盘写满这类问题可能长期存在，后台每 5 分钟重试一次既刷日志
        又永远不结束；到上限后转成用户可见的失败，修复环境后点击“重试”即可重新开始。
        """
        key = self._post_process_group_key(task)
        self._post_process_failures.pop(key, None)
        reason = _redact_text(str(exc or "未知错误")).strip()[:300] or "未知错误"
        for member in self._install_group_members(task):
            if bool(member.post_processed) and str(member.install_status or "") == "installed":
                continue
            member.post_processed = True
            member.install_status = "gave_up"
            member.install_message = (
                f"安装收尾连续失败 {int(attempt)} 次，已停止自动重试：{reason}；"
                "请检查安装目录/磁盘空间后点击重试"
            )
            member.updated_at = _now_wall_ts()
        config.logger.error(
            "Post-process gave up after %s attempts group=%s: %s", int(attempt), key, reason
        )

    def _maybe_schedule_group_post_process(self, task: TianyiTaskRecord) -> None:
        """组内全部文件都下完了才调度安装，避免分卷包缺文件就开始解压。"""
        members = self._install_group_members(task)
        if not members:
            return
        if all(bool(member.post_processed) for member in members):
            return
        if self._post_process_backoff_active(task):
            return

        failed = [
            member for member in members if str(member.status or "") == "error"
        ]
        if failed:
            # 组里有分卷下载失败：不安装，但给已完成的分卷一个可读提示。
            # 用户移除失败任务后，组里剩下的 complete 分卷会被重新调度安装。
            for member in members:
                if (
                    str(member.status or "") == "complete"
                    and not member.post_processed
                    and not str(member.install_message or "").strip()
                ):
                    member.install_message = "同一安装计划中有分卷下载失败，移除失败任务后可继续安装"
            return

        if any(str(member.status or "") != "complete" for member in members):
            return

        lead = members[0]
        self._schedule_post_process_task(lead.task_id)

    async def _try_recover_task(self, task: TianyiTaskRecord) -> bool:
        """aria2 丢失会话后，按文件路径重新认领任务并更新 gid。"""
        path = self._task_local_path(task)
        if not path:
            return False
        if self._aria2_path_index is None:
            index: Dict[str, Dict[str, Any]] = {}
            try:
                downloads = await self.aria2.list_downloads()
            except Exception as exc:
                config.logger.warning("aria2 list_downloads failed: %s", exc)
                downloads = []
            for item in downloads:
                if not isinstance(item, dict):
                    continue
                for file_item in list(item.get("files") or []):
                    if not isinstance(file_item, dict):
                        continue
                    raw_path = str(file_item.get("path", "") or "").strip()
                    if raw_path:
                        index[os.path.realpath(raw_path)] = item
            self._aria2_path_index = index
        item = self._aria2_path_index.get(path)
        if item is None:
            return False
        new_gid = str(item.get("gid", "") or "").strip()
        if not new_gid or new_gid == task.gid:
            return False
        config.logger.info(
            "Recovered aria2 gid for task %s: %s -> %s", task.task_id, task.gid, new_gid
        )
        task.gid = new_gid
        task.updated_at = _now_wall_ts()
        self._task_sync_misses.pop(task.task_id, None)
        return True

    def _quarantine_download_file(self, task: TianyiTaskRecord, reason: str = "bad") -> str:
        """把损坏/过期的半成品文件挪到一边，避免 aria2 继续续传垃圾数据。"""
        path = self._task_local_path(task)
        if not path or not os.path.isfile(path):
            return ""
        target = f"{path}.freedeckcy-{reason}-{_now_wall_ts()}"
        try:
            os.replace(path, target)
        except Exception as exc:
            config.logger.warning("隔离下载文件失败 task=%s: %s", task.task_id, exc)
            return ""
        for suffix in (".aria2",):
            try:
                if os.path.exists(f"{path}{suffix}"):
                    os.replace(f"{path}{suffix}", f"{target}{suffix}")
            except Exception:
                pass
        config.logger.info("已隔离下载文件 task=%s -> %s", task.task_id, target)
        return target

    async def _readd_task_download(self, task: TianyiTaskRecord, *, consume_attempt: bool = True) -> bool:
        """重新获取直链并恢复下载。

        - gid 还在时优先 `aria2.changeUri` 原地换链，保留进度；
        - 否则重新 addUri（`continue=true` 可续传）；
        - aria2 报控制文件缺失时，隔离半成品后再试一次。

        每个任务每个进程默认只尝试一次，避免接口异常时在刷新循环里反复请求。
        """
        provider = str(task.provider or "tianyi").strip() or "tianyi"
        file_id = str(task.file_id or "").strip()
        share_ctx = task.share_ctx if isinstance(task.share_ctx, dict) else {}
        cookie = str(self.store.login.cookie or "").strip()
        if provider == "tianyi":
            if str(task.share_id or "").strip() == "" or file_id == "" or not cookie:
                return False
        elif not file_id or not share_ctx:
            return False
        if consume_attempt:
            if int(self._readd_attempts.get(task.task_id, 0)) >= 1:
                return False
            self._readd_attempts[task.task_id] = 1

        try:
            if provider == "baidu":
                direct_url = await self._fetch_baidu_web_direct_url(share_ctx, file_id)
            elif provider == "baidu_openapi":
                direct_url = await self._fetch_baidu_direct_url(share_ctx, file_id)
            else:
                access_token = await fetch_access_token(cookie)
                direct_url = await fetch_download_url(
                    cookie, access_token, str(task.share_id or ""), file_id
                )
        except Exception as exc:
            config.logger.warning("重新获取直链失败 task=%s: %s", task.task_id, exc)
            return False

        # 1) 原地换链：gid 与已下载进度都不丢
        if str(task.gid or "").strip():
            try:
                await self.aria2.replace_uri(task.gid, direct_url)
                config.logger.info("Refreshed direct url in place for task %s (gid=%s)", task.task_id, task.gid)
                task.status = "waiting"
                task.speed = 0
                task.error_reason = ""
                task.updated_at = _now_wall_ts()
                self._task_sync_misses.pop(task.task_id, None)
                return True
            except Exception as exc:
                config.logger.info("replace_uri 失败，回退 addUri task=%s: %s", task.task_id, exc)

        # 2) 重新加入下载
        split = max(1, min(64, int(self.store.settings.split_count or 16)))
        add_kwargs = {
            "direct_url": direct_url,
            "cookie": (
                str(self.store.baidu_login.cookie or "").strip()
                if provider == "baidu"
                else ("" if provider == "baidu_openapi" else cookie)
            ),
            "download_dir": str(task.download_dir or "").strip(),
            "out_name": str(task.file_name or "").strip(),
            "split": split,
        }
        if provider in {"baidu", "baidu_openapi"}:
            add_kwargs["referer"] = "https://pan.baidu.com/disk/home"
            add_kwargs["user_agent"] = "pan.baidu.com"
        try:
            gid = await self.aria2.add_uri(**add_kwargs)
        except Exception as exc:
            message = str(exc or "").lower()
            if "control file" in message or "truncated" in message:
                quarantined = self._quarantine_download_file(task, "stale")
                if not quarantined:
                    return False
                try:
                    gid = await self.aria2.add_uri(**add_kwargs)
                except Exception as retry_exc:
                    config.logger.warning("隔离后重新加入仍失败 task=%s: %s", task.task_id, retry_exc)
                    return False
            else:
                config.logger.warning("重新加入下载失败 task=%s: %s", task.task_id, exc)
                return False

        config.logger.info("Re-added aria2 download for task %s (gid=%s)", task.task_id, gid)
        task.gid = gid
        task.status = "waiting"
        task.progress = 0.0
        task.speed = 0
        task.error_reason = ""
        task.updated_at = _now_wall_ts()
        self._task_sync_misses.pop(task.task_id, None)
        return True

    async def refresh_tasks(self, sync_aria2: bool = True, persist: bool = True) -> List[Dict[str, Any]]:
        """刷新任务列表并同步状态（与创建任务串行，避免旧快照覆盖新任务）。"""
        async with self._refresh_lock:
            return await self._refresh_tasks_locked(sync_aria2=sync_aria2, persist=persist)

    async def _refresh_tasks_locked(self, sync_aria2: bool = True, persist: bool = True) -> List[Dict[str, Any]]:
        """刷新任务列表实现；调用方需持有 _refresh_lock。"""
        tasks = list(self.store.tasks)
        before_signature = self._tasks_persist_signature(tasks)
        if sync_aria2 and any(not _is_terminal(task.status) for task in tasks):
            # 插件重启后 aria2 可能不在运行：先确保子进程可用，否则会把在跑的任务误判为失败。
            try:
                await self.aria2.ensure_running()
            except Exception as exc:
                config.logger.warning("aria2 ensure_running failed during refresh: %s", exc)
        if sync_aria2 and tasks:
            self._aria2_path_index = None
            for task in tasks:
                if _is_terminal(task.status):
                    continue
                try:
                    info = await self.aria2.tell_status(task.gid)
                except Aria2Error as exc:
                    # 1) 插件/设备重启后 gid 会变：按文件路径重新认领再查一次。
                    if await self._try_recover_task(task):
                        try:
                            info = await self.aria2.tell_status(task.gid)
                        except Aria2Error:
                            continue
                    elif self._file_matches_expected_size(task):
                        # 2) 文件已完整落盘：重启前其实已经下完。
                        task.status = "complete"
                        task.progress = 100.0
                        task.speed = 0
                        task.error_reason = ""
                        task.updated_at = _now_wall_ts()
                        self._task_sync_misses.pop(task.task_id, None)
                        self._maybe_schedule_group_post_process(task)
                        continue
                    else:
                        # 3) 会话文件丢失：用原直链重新加入（可续传），每任务只试一次。
                        if task.status in {"waiting", "active", "paused"} and await self._readd_task_download(task):
                            continue
                        # 4) 连续多次都查不到，才判定失败。
                        misses = int(self._task_sync_misses.get(task.task_id, 0)) + 1
                        self._task_sync_misses[task.task_id] = misses
                        if task.status in {"active", "waiting"} and misses >= TASK_SYNC_ERROR_THRESHOLD:
                            task.status = "error"
                            task.error_reason = (
                                f"{exc}（连续 {misses} 次查询失败，且 aria2 任务列表中找不到该文件；"
                                "请移除任务后重新下载）"
                            )
                            task.updated_at = _now_wall_ts()
                        continue

                status = str(info.get("status", task.status) or task.status)
                total = _safe_int(info.get("totalLength"), 0)
                completed = _safe_int(info.get("completedLength"), 0)
                speed = _safe_int(info.get("downloadSpeed"), 0)
                progress = 0.0
                if total > 0:
                    progress = (completed * 100.0) / total
                if status == "complete":
                    progress = 100.0
                task.status = status
                task.progress = round(progress, 2)
                task.speed = speed
                task.error_reason = str(info.get("errorMessage", "") or "")
                task.updated_at = _now_wall_ts()
                self._task_sync_misses.pop(task.task_id, None)

                if status == "complete":
                    ok, reason = self._verify_downloaded_file(task)
                    if not ok:
                        # 先自愈一次：隔离坏文件后用原直链重下；失败才标错。
                        if int(self._readd_attempts.get(task.task_id, 0)) < 1:
                            self._readd_attempts[task.task_id] = 1
                            try:
                                await self.aria2.remove(task.gid)
                            except Exception:
                                pass
                            self._quarantine_download_file(task, "size-mismatch")
                            if await self._readd_task_download(task, consume_attempt=False):
                                config.logger.info(
                                    "Size mismatch on task %s, re-download scheduled", task.task_id
                                )
                                continue
                        task.status = "error"
                        task.progress = 100.0
                        task.speed = 0
                        task.error_reason = reason
                        task.updated_at = _now_wall_ts()
                        continue
                    if not task.post_processed:
                        self._maybe_schedule_group_post_process(task)

            self._cleanup_tasks(tasks)
            after_signature = self._tasks_persist_signature(tasks)
            if persist and before_signature != after_signature:
                self.store.replace_tasks(tasks)
            else:
                self.store.tasks = list(tasks)
        else:
            self._cleanup_tasks(tasks)
            if before_signature != self._tasks_persist_signature(tasks):
                if persist:
                    self.store.replace_tasks(tasks)
                else:
                    self.store.tasks = list(tasks)

        views = [_task_to_view(t) for t in tasks]
        self._panel_tasks_cache = list(views)
        self._panel_tasks_cache_at = time.monotonic()
        self._panel_last_active_tasks = self._count_active_tasks(views)
        return views

    def _schedule_post_process_task(self, task_id: str) -> None:
        """将下载后安装流程调度为后台任务，避免阻塞面板刷新。"""
        target = str(task_id or "").strip()
        if not target:
            return
        current = self._post_process_jobs.get(target)
        if current is not None and not current.done():
            return
        job = asyncio.create_task(
            self._run_post_process_task(target),
            name=f"freedeckcy_post_process_{target[:8]}",
        )
        self._post_process_jobs[target] = job

        def _cleanup(done_job: asyncio.Task, key: str = target) -> None:
            if self._post_process_jobs.get(key) is done_job:
                self._post_process_jobs.pop(key, None)

        job.add_done_callback(_cleanup)

    async def _run_post_process_task(self, task_id: str) -> None:
        """执行后台安装流程并在结束后持久化状态。"""
        task = self._find_task(task_id)
        if task is None:
            return
        if task.post_processed and all(
            member.post_processed for member in self._install_group_members(task)
        ):
            return
        try:
            await self._post_process_completed_task(task)
            self._clear_post_process_failure(task)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            config.logger.exception("Post-process failed for task %s: %s", task_id, exc)
            attempts = self._record_post_process_failure(task, exc)
            if attempts >= POST_PROCESS_MAX_ATTEMPTS:
                self._give_up_post_process(task, exc, attempt=attempts)
            else:
                task.install_status = "failed"
                task.install_message = (
                    f"安装流程异常: {_redact_text(str(exc))[:300]}；"
                    f"将在后台自动重试（第 {attempts}/{POST_PROCESS_MAX_ATTEMPTS} 次）"
                )
                task.updated_at = _now_wall_ts()
        finally:
            try:
                await asyncio.to_thread(self.store.save)
            except Exception as exc:
                # 后台任务里的状态写入失败不能冒泡成未处理异常，否则整个“后台自动重试”
                # 机制会静默失效；下一次刷新/维护会把状态重新落盘。
                config.logger.warning("Post-process state save failed: %s", exc)

    async def pause_task(self, task_id: str) -> Dict[str, Any]:
        """暂停任务。"""
        task = self._find_task(task_id)
        if task is None:
            raise ValueError("任务不存在")
        await self.aria2.pause(task.gid)
        task.status = "paused"
        task.updated_at = _now_wall_ts()
        self.store.save()
        self._invalidate_panel_cache(tasks=True)
        return _task_to_view(task)

    async def resume_task(self, task_id: str) -> Dict[str, Any]:
        """恢复任务。"""
        task = self._find_task(task_id)
        if task is None:
            raise ValueError("任务不存在")
        await self.aria2.resume(task.gid)
        task.status = "active"
        task.updated_at = _now_wall_ts()
        self.store.save()
        self._invalidate_panel_cache(tasks=True)
        return _task_to_view(task)

    async def pause_all_tasks(self) -> Dict[str, Any]:
        """暂停全部下载任务。"""
        await self.aria2.pause_all()
        changed = 0
        for task in self.store.tasks:
            if task.status in {"active", "queued", "waiting", "downloading", "pending"}:
                task.status = "paused"
                task.updated_at = _now_wall_ts()
                changed += 1
        self.store.save()
        self._invalidate_panel_cache(tasks=True)
        return {"paused": changed}

    async def resume_all_tasks(self) -> Dict[str, Any]:
        """恢复全部已暂停任务。"""
        await self.aria2.resume_all()
        changed = 0
        for task in self.store.tasks:
            if task.status == "paused":
                task.status = "active"
                task.updated_at = _now_wall_ts()
                changed += 1
        self.store.save()
        self._invalidate_panel_cache(tasks=True)
        return {"resumed": changed}

    async def apply_saved_download_speed_limit(self) -> None:
        """把持久化的限速应用到当前 aria2 实例。"""
        limit = max(0, int(getattr(self.store.settings, "download_speed_limit", 0) or 0))
        if limit <= 0:
            return
        try:
            await self.aria2.set_global_download_limit(limit)
        except Exception as exc:
            config.logger.debug("应用下载限速失败: %s", exc)

    async def set_download_speed_limit(self, limit: int) -> Dict[str, Any]:
        """设置全局下载限速（KB/s，0=不限）。"""
        value = max(0, min(10 * 1024 * 1024, int(limit or 0)))
        self.store.set_settings(download_speed_limit=value * 1024)
        try:
            await self.aria2.set_global_download_limit(value * 1024)
        except Exception as exc:
            config.logger.debug("aria2 未运行时暂存下载限速: %s", exc)
        return {"limit": value, "limit_bytes": value * 1024}

    async def remove_task(self, task_id: str) -> Dict[str, Any]:
        """移除任务。"""
        task = self._find_task(task_id)
        if task is None:
            raise ValueError("任务不存在")
        try:
            await asyncio.wait_for(self.aria2.remove(task.gid), timeout=3.0)
        except Exception as exc:
            # aria2 未运行、RPC 挂起或 gid 已消失时，仍允许移除本地记录。
            config.logger.warning("aria2 remove failed for task %s: %s", task_id, _describe_exception(exc))
        task.status = "removed"
        task.updated_at = _now_wall_ts()
        # removed 任务不应再保留到 7 天过期列表里；从本地任务列表立即删除。
        self.store.tasks = [item for item in self.store.tasks if item.task_id != task_id]
        self.store.save()
        self._invalidate_panel_cache(tasks=True)
        return _task_to_view(task)

    async def retry_task(self, task_id: str) -> Dict[str, Any]:
        """重试失败/中断的任务：重置状态并重新获取直链。

        文件已完整时跳过下载，直接重新进入安装流程。
        """
        task = self._find_task(task_id)
        if task is None:
            raise ValueError("任务不存在")
        if str(task.status or "") in {"active", "waiting", "paused"}:
            raise ValueError("任务尚未结束，无需重试")

        self._readd_attempts.pop(task.task_id, None)
        self._task_sync_misses.pop(task.task_id, None)
        self._clear_post_process_failure(task)
        task.post_processed = False
        task.install_status = "pending"
        task.install_message = "正在重试..."
        task.error_reason = ""
        task.progress = 0.0
        task.speed = 0
        task.updated_at = _now_wall_ts()

        if self._file_matches_expected_size(task):
            task.status = "complete"
            task.progress = 100.0
            task.install_message = "文件已完整，重新安装..."
            self.store.save()
            self._maybe_schedule_group_post_process(task)
            self._invalidate_panel_cache(tasks=True)
            return _task_to_view(task)

        if not await self._readd_task_download(task):
            task.install_status = "failed"
            task.install_message = "重试失败：无法重新获取下载直链"
            task.updated_at = _now_wall_ts()
            self.store.save()
            self._invalidate_panel_cache(tasks=True)
            raise RuntimeError("重试失败：无法重新获取下载直链（登录可能已失效）")

        self.store.save()
        self._invalidate_panel_cache(tasks=True)
        return _task_to_view(task)

    def _find_task(self, task_id: str) -> Optional[TianyiTaskRecord]:
        """查找任务对象。"""
        target = (task_id or "").strip()
        if not target:
            return None
        for task in self.store.tasks:
            if task.task_id == target:
                return task
        return None

    def _cleanup_tasks(self, tasks: List[TianyiTaskRecord]) -> None:
        """清理过旧终态任务（下载已完成但安装收尾未完成的除外）。"""
        now = _now_wall_ts()
        # 同一安装计划里还有“已下完但没装完”的成员时，组内失败分卷不能单独清掉：
        # 否则 7 天后会自动把残缺分卷组放行去解压，结果是安装失败/重下。
        pending_group_ids = {
            str(task.group_id or "").strip()
            for task in tasks
            if str(task.status or "") == "complete"
            and not bool(task.post_processed)
            and str(task.group_id or "").strip()
        }
        filtered: List[TianyiTaskRecord] = []
        for task in tasks:
            if str(task.status or "") == "removed":
                continue
            if not _is_terminal(task.status):
                filtered.append(task)
                continue
            if str(task.status or "") == "complete" and not bool(task.post_processed):
                # 下载完成但安装还没收尾：即使插件很久没开机也不能丢，重启后要继续补装。
                filtered.append(task)
                continue
            if str(task.status or "") == "error" and str(task.group_id or "").strip() in pending_group_ids:
                filtered.append(task)
                continue
            if now - int(task.updated_at) <= TASK_RETENTION_SECONDS:
                filtered.append(task)
        tasks[:] = filtered

    def _build_installed_summary(self, limit: int = 8, persist: bool = True) -> Dict[str, Any]:
        """构建已安装游戏预览。

        persist=False 是纯读路径（主界面轮询）：只过滤展示，不修改内存里的
        installed_games。否则 SD 卡瞬时未挂载时面板刷新会把记录从内存裁掉，
        之后任意一次 store.save（设置/任务状态）都会把丢记录落盘。
        """
        normalized_limit = max(0, int(limit or 0))
        visible_items: List[Dict[str, Any]] = []
        kept_records: List[TianyiInstalledGame] = []

        # 过滤已不存在的安装目录，避免主界面展示脏数据。
        records = sorted(self.store.installed_games, key=lambda item: int(item.updated_at or 0), reverse=True)
        for record in records:
            install_path = str(record.install_path or "").strip()
            if not install_path or not os.path.exists(install_path):
                continue
            kept_records.append(record)
            visible_items.append(self._installed_record_to_view(record))

        if persist and len(kept_records) != len(self.store.installed_games):
            self.store.installed_games = kept_records
            self.store.save()

        return {
            "total": len(visible_items),
            "preview": visible_items[:normalized_limit],
        }

    def _find_installed_record(self, *, game_id: str = "", install_path: str = "") -> Optional[TianyiInstalledGame]:
        """查找已安装游戏记录。"""
        target_game_id = str(game_id or "").strip()
        target_install_path = os.path.realpath(os.path.expanduser(str(install_path or "").strip())) if install_path else ""
        for record in self.store.installed_games:
            same_game = bool(target_game_id and str(record.game_id or "") == target_game_id)
            current_install_path = os.path.realpath(os.path.expanduser(str(record.install_path or "").strip()))
            same_path = bool(target_install_path and current_install_path == target_install_path)
            if same_game or same_path:
                return record
        return None

    def _remove_installed_record_in_memory(
        self,
        *,
        game_id: str = "",
        install_path: str = "",
    ) -> Optional[TianyiInstalledGame]:
        """仅在内存中移除已安装记录，供持久化异常时回退。"""
        target_game_id = str(game_id or "").strip()
        target_install_path = os.path.realpath(os.path.expanduser(str(install_path or "").strip())) if install_path else ""
        for idx, record in enumerate(list(self.store.installed_games)):
            same_game = bool(target_game_id and str(record.game_id or "") == target_game_id)
            current_path = os.path.realpath(os.path.expanduser(str(record.install_path or "").strip()))
            same_path = bool(target_install_path and current_path == target_install_path)
            if same_game or same_path:
                return self.store.installed_games.pop(idx)
        return None

    def _can_remove_install_path(self, path: str) -> Tuple[bool, str]:
        """卸载前校验路径安全性，避免误删根目录。"""
        raw = str(path or "").strip()
        if not raw:
            return False, "安装路径为空"
        target = os.path.realpath(os.path.expanduser(raw))
        if not target:
            return False, "安装路径无效"

        normalized = target.rstrip(os.sep)
        if not normalized:
            return False, "安装路径无效"

        home_dir = os.path.realpath(os.path.expanduser("~")).rstrip(os.sep)
        install_raw = str(self.store.settings.install_dir or "").strip()
        download_raw = str(self.store.settings.download_dir or "").strip()
        # 空设置不能 realpath("") 变成进程 CWD，否则会把 CWD 误加入保护/允许集合。
        install_root = os.path.realpath(os.path.expanduser(install_raw)).rstrip(os.sep) if install_raw else ""
        download_root = os.path.realpath(os.path.expanduser(download_raw)).rstrip(os.sep) if download_raw else ""

        blocked = {"/", "/home", "/home/deck", home_dir}
        if install_root:
            blocked.add(install_root)
        if download_root:
            blocked.add(download_root)

        if normalized in blocked:
            return False, "目标路径为系统或根目录级路径，已拒绝删除"

        parts = [part for part in normalized.split(os.sep) if part]
        if len(parts) < 2:
            return False, "目标路径层级过浅，已拒绝删除"

        return True, ""

    def _installed_record_to_view(self, record: TianyiInstalledGame) -> Dict[str, Any]:
        """转换已安装游戏展示结构。"""
        size_bytes = max(0, int(record.size_bytes or 0))
        playtime = self._snapshot_record_playtime(record)
        playtime_seconds = max(0, _safe_int(playtime.get("seconds"), 0))
        return {
            "game_id": record.game_id,
            "title": record.game_title,
            "install_path": record.install_path,
            "source_path": record.source_path,
            "status": record.status,
            "size_bytes": size_bytes,
            "size_text": _format_size_bytes(size_bytes) if size_bytes > 0 else "",
            "steam_app_id": max(0, _safe_int(record.steam_app_id, 0)),
            "playtime_seconds": playtime_seconds,
            "playtime_text": _format_playtime_seconds(playtime_seconds),
            "playtime_sessions": max(0, _safe_int(playtime.get("sessions"), 0)),
            "playtime_last_played_at": max(0, _safe_int(playtime.get("last_played_at"), 0)),
            "playtime_active": bool(playtime.get("active")),
            "platform": str(record.platform or "pc"),
            "emulator": str(record.emulator or ""),
            "rom_path": str(record.rom_path or ""),
            "launcher_path": str(record.launcher_path or ""),
            "updated_at": int(record.updated_at or 0),
        }

    async def list_installed_games(self) -> Dict[str, Any]:
        """已安装游戏完整列表（含目录封面/平台信息）。"""
        records = sorted(
            list(self.store.installed_games),
            key=lambda item: int(item.updated_at or 0),
            reverse=True,
        )
        items: List[Dict[str, Any]] = []
        for record in records:
            view = self._installed_record_to_view(record)
            install_path = str(record.install_path or "").strip()
            view["exists"] = bool(install_path and os.path.isdir(install_path))
            entry = self.catalog.get_by_game_id(record.game_id)
            if entry is not None:
                view["platform"] = entry.platform
                view["cover_url"] = entry.cover_url
                portrait = str(entry.cover_portrait_url or "")
                if not portrait and entry.steam_appid > 0:
                    portrait = self._build_store_square_cover_url(entry.steam_appid)
                view["cover_portrait_url"] = portrait
                if not view.get("steam_appid"):
                    view["steam_appid"] = max(0, _safe_int(entry.steam_appid, 0))
            items.append(view)
        return {"total": len(items), "items": items}

    async def launch_installed_game(self, game_id: str) -> Dict[str, Any]:
        """通过 Steam 拉起已安装游戏。"""
        record = self._find_installed_record(game_id=str(game_id or "").strip())
        if record is None:
            raise ValueError("未找到已安装游戏记录")
        app_id = self._resolve_record_app_id(record)
        if app_id <= 0:
            raise ValueError("该游戏缺少 Steam AppID，请从 Steam 库手动启动")

        if str(record.platform or "pc") == "3ds":
            wrapper_path = str(record.launcher_path or "").strip()
            wrapper_text = ""
            if wrapper_path:
                try:
                    wrapper_text = Path(wrapper_path).read_text(encoding="utf-8")
                except Exception:
                    wrapper_text = ""
            if "org.azahar_emu.Azahar" not in wrapper_text:
                if flatpak_installed("org.azahar_emu.Azahar"):
                    try:
                        command = await ensure_emulator("3ds", self.plugin_dir, allow_download=False)
                        await asyncio.to_thread(
                            create_launch_wrapper,
                            command=command,
                            rom_path=str(record.rom_path or ""),
                            wrapper_path=wrapper_path or os.path.join(str(record.install_path or ""), "launch-freedeckcy.sh"),
                            platform_name="3ds",
                        )
                        record.launcher_path = wrapper_path or os.path.join(str(record.install_path or ""), "launch-freedeckcy.sh")
                        await asyncio.to_thread(self.store.save)
                    except Exception as exc:
                        raise ValueError(f"3DS 启动器修复失败：{exc}") from exc
                else:
                    self._maybe_schedule_launcher_repair()
                    raise ValueError("正在安装 Azahar Flatpak，请等待 1–2 分钟后重试")

        await asyncio.to_thread(_launch_external, f"steam://rungameid/{app_id}")
        return {
            "game_id": str(record.game_id or ""),
            "title": str(record.game_title or ""),
            "steam_app_id": app_id,
            "launched": True,
        }

    @staticmethod
    def _normalize_scan_title(value: str) -> str:
        return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", str(value or "").lower())

    async def get_storage_options(self) -> Dict[str, Any]:
        """返回内置存储与可写 SD/外置挂载，供下载/安装目录一键选择。"""
        data = await asyncio.to_thread(detect_storage_options, home=os.path.expanduser("~"))
        data["download_dir"] = str(self.store.settings.download_dir or "")
        data["install_dir"] = str(self.store.settings.install_dir or "")
        return data

    def _find_scanned_executable(self, install_path: str, entry: Any) -> str:
        """在扫描到的安装目录里找可执行文件（优先 openpath 的 exe）。"""
        root = os.path.realpath(os.path.expanduser(str(install_path or "").strip()))
        if not root or not os.path.isdir(root):
            return ""
        declared = str(getattr(entry, "executable_name", "") or "").strip()
        if declared:
            declared_path = self._find_declared_executable(root, declared)
            if declared_path:
                return declared_path
        openpath = str(getattr(entry, "openpath", "") or "").replace("\\", "/").strip("/")
        if openpath and openpath.lower().endswith(".exe"):
            parts = [part for part in openpath.split("/") if part not in {"", "."}]
            if ".." in parts or openpath.startswith("/"):
                return ""
            target = os.path.realpath(os.path.join(root, *parts))
            if os.path.isfile(target) and _is_within_dir(target, root):
                return target
            target_name = os.path.basename(openpath).lower()
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in filenames:
                    if name.lower() == target_name:
                        return os.path.join(dirpath, name)
        candidates: List[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            if dirpath.count(os.sep) - root.count(os.sep) >= 4:
                dirnames[:] = []
            for name in filenames:
                if not name.lower().endswith(".exe"):
                    continue
                lower = name.lower()
                if any(token in lower for token in ("unins", "setup", "redist", "vcredist", "crashreport", "dxsetup")):
                    continue
                candidates.append(os.path.join(dirpath, name))
                if len(candidates) >= 200:
                    break
            if len(candidates) >= 200:
                break
        if not candidates:
            return ""
        title_key = self._normalize_scan_title(str(getattr(entry, "title", "") or ""))
        dir_key = self._normalize_scan_title(os.path.basename(root))
        def rank(path: str):
            stem = self._normalize_scan_title(os.path.splitext(os.path.basename(path))[0])
            score = 0
            if title_key and (stem == title_key or stem.startswith(title_key) or title_key.startswith(stem)):
                score -= 100
            if dir_key and (stem == dir_key or stem.startswith(dir_key) or dir_key.startswith(stem)):
                score -= 50
            try:
                size = os.path.getsize(path)
            except Exception:
                size = 0
            return (score, -size, path)
        return sorted(candidates, key=rank)[0]

    async def scan_installed_games(self) -> Dict[str, Any]:
        """扫描安装目录，把旧版本/手动安装的游戏补回已安装列表。"""
        install_root = self._normalize_existing_dir(str(self.store.settings.install_dir or "").strip())
        if not install_root:
            raise ValueError("当前未设置有效的安装目录")
        records = list(self.store.installed_games or [])
        existing_paths = {
            self._normalize_dir_path(str(record.install_path or "").strip())
            for record in records
            if str(record.install_path or "").strip()
        }
        existing_ids = {str(record.game_id or "").strip() for record in records}

        title_index: Dict[str, Any] = {}
        for entry in list(self.catalog.entries or []):
            for part in re.split(r"[/|｜]", str(entry.title or "")):
                key = self._normalize_scan_title(part)
                if len(key) >= 4 and key not in title_index:
                    title_index[key] = entry

        shortcut_by_name: Dict[str, int] = {}
        shortcut_by_exe: Dict[str, int] = {}
        try:
            shortcut_result = await asyncio.to_thread(list_all_shortcuts_sync)
            for row in list(shortcut_result.get("rows") or []):
                if not isinstance(row, dict):
                    continue
                name_key = self._normalize_scan_title(str(row.get("app_name", "") or ""))
                appid = _safe_int(row.get("appid_unsigned"), 0)
                if name_key and appid > 0:
                    shortcut_by_name.setdefault(name_key, appid)
                exe_real = str(row.get("exe_real", "") or "").strip()
                if exe_real and appid > 0:
                    shortcut_by_exe.setdefault(exe_real, appid)
        except Exception as exc:
            config.logger.warning("扫描 Steam 快捷方式失败: %s", exc)

        skip_names = {"compatdata", "steamapps", "downloads", "lost+found", ".freedeckcy", ".cache"}
        added: List[Dict[str, Any]] = []
        unresolved: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []
        try:
            children = sorted(os.listdir(install_root))
        except Exception as exc:
            raise ValueError(f"读取安装目录失败：{exc}") from exc

        for name in children[:500]:
            normalized_name = str(name or "").strip()
            if not normalized_name or normalized_name.startswith("."):
                continue
            if normalized_name.lower() in skip_names:
                continue
            install_path = self._normalize_existing_dir(os.path.join(install_root, normalized_name))
            if not install_path:
                continue
            if install_path in existing_paths:
                skipped.append({"install_path": install_path, "reason": "already_recorded"})
                continue
            try:
                size_bytes = _dir_size_bytes(install_path)
            except Exception:
                size_bytes = 0
            if size_bytes <= 0:
                continue

            directory_key = self._normalize_scan_title(normalized_name)
            match = None
            best_len = 0
            for key, entry in title_index.items():
                if directory_key == key or (len(directory_key) >= len(key) and directory_key.startswith(key)):
                    if len(key) > best_len:
                        match = entry
                        best_len = len(key)
            if match is None:
                unresolved.append({"install_path": install_path, "name": normalized_name, "reason": "catalog_no_match"})
                continue
            game_id = str(match.game_id or "").strip()
            if not game_id:
                unresolved.append({"install_path": install_path, "name": normalized_name, "reason": "catalog_missing_game_id"})
                continue
            if game_id in existing_ids:
                skipped.append({"install_path": install_path, "game_id": game_id, "reason": "game_id_recorded"})
                continue

            platform = str(match.platform or "pc").strip().lower() or "pc"
            rom_path = ""
            if platform != "pc":
                try:
                    rom_path = find_rom_file(
                        install_path,
                        str(match.openpath or ""),
                        platform,
                        strict=True,
                        title=str(match.title or ""),
                    )
                except Exception:
                    rom_path = ""
            display_title = self._derive_display_title_for_steam(str(match.title or normalized_name))
            appid = shortcut_by_name.get(self._normalize_scan_title(str(match.title or "")), 0)
            exe_path = ""
            launcher_path = ""
            shortcut_added = False
            shortcut_error = ""
            if appid <= 0 and platform == "pc":
                exe_path = self._find_scanned_executable(install_path, match)
                if exe_path:
                    appid = shortcut_by_exe.get(os.path.realpath(exe_path), 0)
            if appid <= 0:
                try:
                    launch_options = ""
                    shortcut_appid = 0
                    if platform == "pc":
                        if not exe_path:
                            shortcut_error = "exe_not_found"
                        else:
                            launch_token = re.sub(r"[^a-zA-Z0-9._-]+", "_", game_id or normalized_name).strip("_") or "game"
                            launch_options = f"freedeckcy:tianyi:{launch_token}"
                            shortcut = await add_or_update_tianyi_shortcut(
                                game_id=game_id,
                                display_name=display_title,
                                exe_path=exe_path,
                                launch_options=launch_options,
                                proton_tool=str(self.store.settings.proton_tool or "auto"),
                                cover_landscape_url=str(match.cover_url or ""),
                                cover_portrait_url=str(match.cover_portrait_url or ""),
                                steam_app_id=_safe_int(match.steam_appid, 0),
                            )
                            if shortcut.get("ok"):
                                shortcut_appid = _safe_int(shortcut.get("appid_unsigned"), 0)
                                shortcut_added = shortcut_appid > 0
                            else:
                                shortcut_error = str(shortcut.get("message", "") or "shortcut_failed")
                    elif rom_path:
                        try:
                            command = await ensure_emulator(platform, self.plugin_dir, allow_download=False)
                            launcher_path = os.path.join(install_path, "launch-freedeckcy.sh")
                            await asyncio.to_thread(
                                create_launch_wrapper,
                                command=command,
                                rom_path=rom_path,
                                wrapper_path=launcher_path,
                                platform_name=platform,
                            )
                            launch_token = re.sub(r"[^a-zA-Z0-9._-]+", "_", game_id or normalized_name).strip("_") or "game"
                            shortcut = await add_or_update_tianyi_shortcut(
                                game_id=game_id,
                                display_name=display_title,
                                exe_path=launcher_path,
                                launch_options=f"freedeckcy:tianyi:{launch_token}",
                                proton_tool="none",
                                cover_landscape_url=str(match.cover_url or ""),
                                cover_portrait_url=str(match.cover_portrait_url or ""),
                                steam_app_id=_safe_int(match.steam_appid, 0),
                            )
                            if shortcut.get("ok"):
                                shortcut_appid = _safe_int(shortcut.get("appid_unsigned"), 0)
                                shortcut_added = shortcut_appid > 0
                            else:
                                shortcut_error = str(shortcut.get("message", "") or "shortcut_failed")
                        except Exception as exc:
                            shortcut_error = f"emulator_not_ready: {exc}"
                    else:
                        shortcut_error = "rom_not_found"
                    if shortcut_added and shortcut_appid > 0:
                        appid = shortcut_appid
                except Exception as exc:
                    shortcut_error = f"shortcut_failed: {exc}"

            record = TianyiInstalledGame(
                game_id=game_id,
                game_title=str(match.title or normalized_name),
                install_path=install_path,
                source_path=install_path,
                size_bytes=size_bytes,
                steam_app_id=appid,
                platform=platform,
                emulator=emulator_name_for_platform(platform) if platform != "pc" else "",
                rom_path=rom_path,
                launcher_path=launcher_path,
            )
            self.store.upsert_installed_game(record)
            existing_paths.add(install_path)
            existing_ids.add(game_id)
            added.append(
                {
                    "game_id": game_id,
                    "title": record.game_title,
                    "platform": platform,
                    "install_path": install_path,
                    "steam_app_id": appid,
                    "steam_added": shortcut_added,
                    "shortcut_error": shortcut_error,
                }
            )

        # 第二遍：已存在记录但 Steam 里没有快捷方式的 PC 游戏，也补一个。
        shortcut_recovered: List[Dict[str, Any]] = []
        for record in list(self.store.installed_games or []):
            if str(record.platform or "pc").lower() != "pc" or _safe_int(record.steam_app_id, 0) > 0:
                continue
            record_path = self._normalize_dir_path(str(record.install_path or "").strip())
            if not record_path or not (record_path == install_root or record_path.startswith(install_root.rstrip(os.sep) + os.sep)):
                continue
            try:
                entry = self.catalog.get_by_game_id(record.game_id)
            except Exception:
                entry = None
            if entry is None:
                entry = next(
                    (item for item in list(self.catalog.entries or []) if str(item.game_id) == str(record.game_id)),
                    None,
                )
            if entry is None:
                continue
            exe_path = self._find_scanned_executable(record_path, entry)
            if not exe_path:
                continue
            try:
                launch_token = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(record.game_id or "")).strip("_") or "game"
                shortcut = await add_or_update_tianyi_shortcut(
                    game_id=str(record.game_id or ""),
                    display_name=self._derive_display_title_for_steam(str(record.game_title or entry.title or "")),
                    exe_path=exe_path,
                    launch_options=f"freedeckcy:tianyi:{launch_token}",
                    proton_tool=str(self.store.settings.proton_tool or "auto"),
                    cover_landscape_url=str(entry.cover_url or ""),
                    cover_portrait_url=str(entry.cover_portrait_url or ""),
                    steam_app_id=_safe_int(entry.steam_appid, 0),
                )
                if shortcut.get("ok"):
                    appid = _safe_int(shortcut.get("appid_unsigned"), 0)
                    if appid > 0:
                        record.steam_app_id = appid
                        record.updated_at = _now_wall_ts()
                        shortcut_recovered.append({"game_id": record.game_id, "title": record.game_title, "steam_app_id": appid})
            except Exception as exc:
                config.logger.warning("扫描补 Steam 快捷方式失败 game=%s: %s", record.game_id, exc)

        if added or shortcut_recovered:
            await asyncio.to_thread(self.store.save)
            self._invalidate_panel_cache(all_data=True)
        return {
            "install_root": install_root,
            "scanned": len(children),
            "added_count": len(added),
            "added_games": added[:24],
            "steam_recovered_count": len(shortcut_recovered),
            "steam_recovered": shortcut_recovered[:24],
            "skipped_count": len(skipped),
            "unresolved_count": len(unresolved),
            "unresolved_dirs": unresolved[:24],
            "installed_total": len(self.store.installed_games or []),
            "message": (
                f"已补回 {len(added)} 个已安装游戏，补建 {len(shortcut_recovered)} 个 Steam 快捷方式"
                if added or shortcut_recovered
                else "没有发现可补回的已安装游戏（目录名需与目录标题匹配）"
            ),
        }

    async def open_installed_folder(self, game_id: str) -> Dict[str, Any]:
        """用系统文件管理器打开安装目录。"""
        record = self._find_installed_record(game_id=str(game_id or "").strip())
        if record is None:
            raise ValueError("未找到已安装游戏记录")
        path = os.path.realpath(os.path.expanduser(str(record.install_path or "").strip()))
        if not path or not os.path.isdir(path):
            raise ValueError("安装目录不存在")
        await asyncio.to_thread(_launch_external, path)
        return {"game_id": str(record.game_id or ""), "path": _redact_text(path), "opened": True}

    def _plugin_version(self) -> str:
        """读取插件版本（package.json）。"""
        root = ""
        try:
            root = str(getattr(decky, "DECKY_PLUGIN_DIR", "") or "")
        except Exception:
            root = ""
        if not root:
            root = str(os.getenv("DECKY_PLUGIN_DIR", "") or "")
        path = os.path.join(root, "package.json") if root else ""
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return str(data.get("version") or "").strip()
        except Exception:
            return ""

    async def get_diagnostics(self) -> Dict[str, Any]:
        """收集诊断信息（日志与路径已脱敏，不含 cookie）。"""
        root = ""
        try:
            root = str(getattr(decky, "DECKY_PLUGIN_DIR", "") or "")
        except Exception:
            root = ""
        if not root:
            root = str(os.getenv("DECKY_PLUGIN_DIR", "") or "")

        arch = _runtime_arch_name()
        runtime: Dict[str, Dict[str, Any]] = {}
        for component, rel in (("aria2", "aria2c"), ("7z", "7zz"), ("node", os.path.join("bin", "node"))):
            path = os.path.join(root, "defaults", "runtime", component, arch, rel)
            exists = os.path.isfile(path)
            runtime[component] = {
                "path": _redact_text(path),
                "exists": exists,
                "size": os.path.getsize(path) if exists else 0,
            }

        log_file = "/tmp/freedeckcy.log"
        log_tail = _redact_text(await asyncio.to_thread(_tail_text, log_file, 300))
        recent_errors = [
            line for line in log_tail.splitlines() if re.search(r"ERROR|Exception|失败", line)
        ][-20:]

        task_counts: Dict[str, int] = {}
        for task in self.store.tasks:
            status = str(task.status or "unknown")
            task_counts[status] = task_counts.get(status, 0) + 1

        installed_bytes = sum(max(0, int(record.size_bytes or 0)) for record in self.store.installed_games)
        installed_missing = sum(
            1
            for record in self.store.installed_games
            if not os.path.isdir(str(record.install_path or ""))
        )

        steam_root = ""
        try:
            steam_root = await asyncio.to_thread(_find_steam_root)
        except Exception:
            steam_root = ""

        shortcut_titles: List[str] = []
        try:
            shortcut_info = await asyncio.to_thread(list_all_shortcuts_sync)
            shortcut_titles = [
                _redact_text(str(row.get("app_name", "") or ""))[:120]
                for row in list(shortcut_info.get("rows") or [])[:50]
                if str(row.get("app_name", "") or "").strip()
            ]
        except Exception:
            shortcut_titles = []

        settings: Dict[str, Any] = {}
        for key, value in asdict(self.store.settings).items():
            settings[key] = _redact_text(value) if isinstance(value, str) else value

        return {
            "generated_at": int(time.time()),
            "version": self._plugin_version(),
            "python": platform.python_version(),
            "system": platform.platform(),
            "arch": arch,
            "paths": {
                "plugin_dir": _redact_text(root),
                "state_file": _redact_text(self.store.state_file),
                "log_file": log_file,
                "steam_root": _redact_text(steam_root),
            },
            "runtime": runtime,
            "steam": {
                "root_exists": bool(steam_root and os.path.isdir(steam_root)),
                "proton_tool": detect_proton_tool(steam_root),
                "droiddeck": is_droiddeck(steam_root),
                "shortcut_titles": shortcut_titles,
            },
            "catalog": {
                "source": str(getattr(self.catalog, "source", "csv")),
                "json_path": _redact_text(str(getattr(self.catalog, "json_path", "") or "")),
                "total": len(self.catalog.entries),
                "platforms": self.catalog.platform_counts(),
                "cover_index_total": self.catalog.cover_index_total,
                "with_cover": sum(
                    1 for entry in self.catalog.entries if entry.cover_url or entry.cover_portrait_url
                ),
            },
            "tasks": {
                "counts": task_counts,
                "total": len(self.store.tasks),
                "recent": [
                    {
                        key: (_redact_text(value) if isinstance(value, str) else value)
                        for key, value in _task_to_view(task).items()
                    }
                    for task in sorted(
                        self.store.tasks,
                        key=lambda item: int(getattr(item, "updated_at", 0) or 0),
                        reverse=True,
                    )[:10]
                ],
            },
            "installed": {
                "total": len(self.store.installed_games),
                "bytes": installed_bytes,
                "missing_paths": installed_missing,
            },
            "settings": settings,
            "emulators": {
                name: emulator_status(name, root) for name in supported_platforms()
            },
            "recent_errors": recent_errors,
            "log_tail": log_tail,
        }

    async def _runtime_version_check(self, path: str, args: Sequence[str]) -> Tuple[bool, str]:
        """运行运行时 --version，返回 (ok, 摘要)。"""
        if not path or not os.path.isfile(path):
            return False, "文件不存在"
        if not os.access(path, os.X_OK):
            return False, "没有执行权限"
        try:
            proc = await asyncio.create_subprocess_exec(
                path,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return False, "执行超时"
            text = (stdout or b"").decode("utf-8", "replace").strip().splitlines()
            return proc.returncode == 0, (text[0][:160] if text else f"exit={proc.returncode}")
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"[:200]

    async def run_diagnostics(self, include_network: bool = True) -> Dict[str, Any]:
        """运行可用性自检，供 QAM/诊断包定位问题（不输出 cookie/token）。"""
        checks: List[Dict[str, str]] = []

        def add(check_id: str, label: str, status: str, detail: str, fix: str = "") -> None:
            checks.append(
                {
                    "id": check_id,
                    "label": label,
                    "status": status,
                    "detail": _redact_text(detail)[:500],
                    "fix": fix[:300],
                }
            )

        root = ""
        try:
            root = str(getattr(decky, "DECKY_PLUGIN_DIR", "") or "")
        except Exception:
            root = ""
        if not root:
            root = str(os.getenv("DECKY_PLUGIN_DIR", "") or "")
        arch = _runtime_arch_name()

        # 插件版本/目录
        version = self._plugin_version()
        add("plugin", "插件版本", "ok" if version else "warn", f"v{version or '未知'}；{root or '未获取插件目录'}", "确认已通过 Decky 安装并重启插件")

        # 状态目录可写
        state_dir = os.path.dirname(os.path.abspath(self.store.state_file))
        try:
            os.makedirs(state_dir, exist_ok=True)
            probe = os.path.join(state_dir, ".diag-write-test")
            with open(probe, "w", encoding="utf-8") as fh:
                fh.write("ok")
            os.remove(probe)
            mode = oct(os.stat(self.store.state_file).st_mode & 0o777) if os.path.isfile(self.store.state_file) else "未创建"
            add("state_dir", "状态目录", "ok", f"{_redact_text(state_dir)} 可写；state={mode}", "检查 ~/.local/share/freedeckCY 权限")
        except Exception as exc:
            add("state_dir", "状态目录", "fail", f"{_redact_text(state_dir)} 不可写：{exc}", "修复目录权限或磁盘空间")

        # 下载/安装目录
        for key, label in (("download_dir", "下载目录"), ("install_dir", "安装目录")):
            value = str(getattr(self.store.settings, key, "") or "").strip()
            if not value:
                add(key, label, "warn", "未设置", "在设置 → 路径里选择目录")
                continue
            path = os.path.realpath(os.path.expanduser(value))
            try:
                os.makedirs(path, exist_ok=True)
                usage = shutil.disk_usage(path)
                free_gb = usage.free / (1024 ** 3)
                status = "ok"
                detail = f"{_redact_text(path)}；剩余 {free_gb:.1f} GB"
                fix = ""
                if not os.access(path, os.W_OK):
                    status, detail, fix = "fail", f"{_redact_text(path)} 不可写", "重新选择目录/修复权限"
                elif free_gb < 2:
                    status, detail, fix = "warn", f"{_redact_text(path)} 剩余仅 {free_gb:.2f} GB", "清理空间或换 SD 卡"
                add(key, label, status, detail, fix)
            except Exception as exc:
                add(key, label, "fail", f"{_redact_text(path)} 不可用：{exc}", "重新选择目录")

        # 运行时
        for component, rel, args in (
            ("aria2", "aria2c", ("--version",)),
            ("7z", "7zz", ("i",)),
            ("node", os.path.join("bin", "node"), ("--version",)),
        ):
            path = os.path.join(root, "defaults", "runtime", component, arch, rel)
            ok, detail = await self._runtime_version_check(path, list(args))
            add(
                f"runtime_{component}",
                f"运行时 {component}",
                "ok" if ok else "fail",
                f"{detail}；{_redact_text(path)}",
                "重新安装插件包，或执行 make runtime 后重打包",
            )

        # 目录
        try:
            total = len(self.catalog.entries)
            add(
                "catalog",
                "游戏目录",
                "ok" if total > 0 else "fail",
                f"{total} 条，平台 {len(self.catalog.platform_counts())} 个，封面 {self.catalog.cover_index_total} 个",
                "检查 defaults/tianyi_catalog 是否存在",
            )
        except Exception as exc:
            add("catalog", "游戏目录", "fail", f"读取失败：{exc}", "重新安装插件包")

        # Steam
        try:
            steam_root = await asyncio.to_thread(_find_steam_root)
            if not steam_root:
                add("steam", "Steam 目录", "fail", "未找到 Steam 安装目录", "确认 Steam 已安装/路径可访问")
            else:
                shortcut_info = await asyncio.to_thread(list_all_shortcuts_sync)
                rows = shortcut_info.get("rows") if isinstance(shortcut_info, dict) else []
                count = len(rows or [])
                if shortcut_info.get("ok"):
                    titles = [
                        str(row.get("app_name", "") or "").strip()
                        for row in list(rows or [])[:5]
                        if str(row.get("app_name", "") or "").strip()
                    ]
                    title_text = f"（{'、'.join(_redact_text(title) for title in titles)}）" if titles else ""
                    add(
                        "steam",
                        "Steam 快捷方式",
                        "ok",
                        f"{_redact_text(steam_root)}；{count} 个快捷方式{title_text}",
                        "",
                    )
                else:
                    add(
                        "steam",
                        "Steam 快捷方式",
                        "warn",
                        f"{_redact_text(steam_root)}；{shortcut_info.get('message', '读取失败')}",
                        "确认 Steam 已登录且 userdata 可读",
                    )
        except Exception as exc:
            add("steam", "Steam 快捷方式", "warn", f"检查失败：{exc}", "查看日志 shortcuts 相关错误")

        # 存储挂载
        try:
            storage = await asyncio.to_thread(detect_storage_options, home=os.path.expanduser("~"))
            external = storage.get("external") or []
            labels = "，".join(str(item.get("label", "")) for item in external[:5]) or "无"
            add("storage", "SD/外置存储", "ok", f"检测到 {len(external)} 个：{labels}", "如未挂载，先在 SteamOS 挂载 SD 卡")
        except Exception as exc:
            add("storage", "SD/外置存储", "warn", f"检测失败：{exc}", "")

        # 网络 / 百度二维码
        if include_network:
            try:
                timeout = aiohttp.ClientTimeout(total=8, connect=5)
                connector = aiohttp.TCPConnector(ssl=build_tls_context())
                async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                    async with session.get("https://cloud.189.cn/") as response:
                        add(
                            "network_tianyi",
                            "天翼云网络",
                            "ok" if int(response.status) < 500 else "warn",
                            f"HTTP {int(response.status)}",
                            "检查网络/DNS/代理",
                        )
            except Exception as exc:
                add(
                    "network_tianyi",
                    "天翼云网络",
                    "warn",
                    f"{type(exc).__name__}: {exc}",
                    "检查网络/DNS/代理；如证书链失败，设置 SSL_CERT_FILE 或 FREEDECKCY_TLS_CA_FILE 指向系统 CA",
                )

            try:
                qr = await asyncio.wait_for(request_qr(), timeout=12)
                add("baidu_qr", "百度扫码接口", "ok", f"getqrcode 正常（sign 长度 {len(qr.get('sign', ''))}）", "")
            except Exception as exc:
                add(
                    "baidu_qr",
                    "百度扫码接口",
                    "fail",
                    f"{type(exc).__name__}: {exc}",
                    "检查 passport.baidu.com 连通性/证书；v0.19.2+ 已内置 TLS 回退",
                )
        else:
            add("baidu_qr", "百度扫码接口", "skip", "未执行网络检查", "")

        # 任务/已安装
        failed_tasks = sum(1 for task in self.store.tasks if str(getattr(task, "status", "")).lower() in {"failed", "error"})
        failed_installs = [
            task for task in self.store.tasks
            if str(getattr(task, "status", "") or "") == "complete"
            and str(getattr(task, "install_status", "") or "") == "failed"
        ]
        pending_installs = [
            task for task in self.store.tasks
            if str(getattr(task, "status", "") or "") == "complete"
            and not bool(getattr(task, "post_processed", False))
        ]
        task_status = "warn" if (failed_tasks or failed_installs or pending_installs) else "ok"
        task_detail = (
            f"{len(self.store.tasks)} 个任务（失败 {failed_tasks}，"
            f"安装失败 {len(failed_installs)}，待安装 {len(pending_installs)}），"
            f"{len(self.store.installed_games)} 个已安装"
        )
        if failed_installs:
            task_detail += "；" + "；".join(
                _redact_text(str(getattr(task, "install_message", "") or ""))[:160]
                for task in failed_installs[:2]
            )
        add(
            "tasks",
            "任务与已安装",
            task_status,
            task_detail,
            "查看主页任务安装失败原因/日志" if task_status == "warn" else "",
        )

        # 日志
        try:
            log_tail = await asyncio.to_thread(_tail_text, "/tmp/freedeckcy.log", 300)
            error_lines = [line for line in log_tail.splitlines() if re.search(r"ERROR|Exception|失败", line)]
            add(
                "log",
                "日志",
                "warn" if error_lines else "ok",
                f"最近错误行 {len(error_lines)} 条；/tmp/freedeckcy.log",
                "导出诊断包查看 log-tail.txt" if error_lines else "",
            )
        except Exception as exc:
            add("log", "日志", "warn", f"读取失败：{exc}", "")

        summary = {"ok": 0, "warn": 0, "fail": 0, "skip": 0}
        for check in checks:
            status = str(check.get("status", "") or "warn")
            summary[status] = summary.get(status, 0) + 1
        return {
            "generated_at": int(time.time()),
            "version": version,
            "arch": arch,
            "summary": summary,
            "checks": checks,
        }

    async def export_diagnostics(self) -> bytes:
        """导出诊断 zip（diagnostics.json + log-tail.txt + README）。"""
        diagnostics = await self.get_diagnostics()
        self_check = await self.run_diagnostics(include_network=True)
        log_tail = str(diagnostics.pop("log_tail", "") or "")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "diagnostics.json",
                json.dumps(diagnostics, ensure_ascii=False, indent=2),
            )
            archive.writestr("self-check.json", json.dumps(self_check, ensure_ascii=False, indent=2))
            archive.writestr("log-tail.txt", log_tail)
            archive.writestr(
                "README.txt",
                "freedeckCY 诊断包\n\n"
                "diagnostics.json：版本/路径/运行时/任务/已安装统计（cookie 与 token 已脱敏，HOME 替换为 ~）\n"
                "self-check.json：自检结果（插件/目录/运行时/Steam/存储/网络/百度扫码/任务/日志）\n"
                "log-tail.txt：/tmp/freedeckcy.log 末尾 300 行（同样脱敏）\n\n"
                "提交 issue 时请附上本 zip；如需进一步排查，可在 Deck 桌面终端运行 make doctor。\n",
            )
        return buffer.getvalue()

    async def export_diagnostics_to_downloads(self) -> Dict[str, Any]:
        """把诊断包写到下载目录，供 QAM 一键导出。"""
        data = await self.export_diagnostics()
        target_dir = str(self.store.settings.download_dir or "").strip()
        if not target_dir:
            target_dir = str(getattr(self.plugin, "downloads_dir", "") or "").strip()
        if not target_dir:
            target_dir = os.path.expanduser("~/Downloads")
        target_dir = os.path.realpath(os.path.expanduser(target_dir))
        await asyncio.to_thread(os.makedirs, target_dir, exist_ok=True)
        filename = f"freedeckcy-diagnostics-{time.strftime('%Y%m%d-%H%M%S')}.zip"
        path = os.path.join(target_dir, filename)
        await asyncio.to_thread(_write_private_file, path, data)
        return {
            "path": _redact_text(path),
            "filename": filename,
            "size": len(data),
            "message": f"诊断包已导出：{_redact_text(path)}",
        }

    def _install_lock_for(self, target_dir: str) -> asyncio.Lock:
        """获取某个安装目录的互斥锁（分卷/多包游戏会共用同一目标目录）。"""
        key = os.path.realpath(os.path.expanduser(str(target_dir or "")))
        lock = self._install_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._install_locks[key] = lock
        return lock

    def _resolve_install_root(self) -> str:
        """解析安装根目录并确保存在。"""
        settings = self.store.settings
        install_root = str(settings.install_dir or "").strip() or str(settings.download_dir or "").strip()
        if not install_root:
            install_root = str(
                getattr(self.plugin, "downloads_dir", config.DOWNLOADS_DIR) or config.DOWNLOADS_DIR
            )
        install_root = os.path.realpath(os.path.expanduser(install_root))
        os.makedirs(install_root, exist_ok=True)
        return install_root

    async def _post_process_completed_task(self, task: TianyiTaskRecord) -> None:
        """下载完成后执行安装与清理。

        - 同一安装目录串行：分卷/多包的多个文件不会并发解压互相覆盖；
        - 同一安装计划（group）一次性处理：全部文件都下完才进来，装完只注册一次 Steam；
        - 多分卷归档（.7z.001 / .part1.rar / .z01+zip ...）只解主卷，其余标记为 bundled。
        """
        install_root = self._resolve_install_root()
        target_dir = self._resolve_install_target_dir(task, install_root)
        os.makedirs(target_dir, exist_ok=True)

        lock = self._install_lock_for(target_dir)
        async with lock:
            all_members = self._install_group_members(task)
            members = [item for item in all_members if not item.post_processed]
            if not members:
                return

            member_paths = [self._task_local_path(member) for member in members if self._task_local_path(member)]
            bundle_index = build_bundle_index(member_paths)
            bundle_errors: Dict[str, str] = {}
            for path, (archive_set, _is_entry) in bundle_index.items():
                if archive_set.missing_parts:
                    missing_text = "、".join(archive_set.missing_parts[:3])
                    bundle_errors[path] = f"分卷不完整，缺少: {missing_text}"

            cancelled = False
            # finished=True 只在整个安装收尾（含 Steam 注册/记录写入）走完时置位；
            # 中途抛异常时保持 False，让未完成的成员留到退避重试，而不是被误标已处理。
            finished = False
            repaired_members: set[str] = set()
            try:
                failed = 0
                for member in members:
                    member_path = self._task_local_path(member)
                    bundle_entry = bundle_index.get(member_path)

                    if member_path in bundle_errors:
                        ok, message = False, bundle_errors[member_path]
                    elif bundle_entry is not None and not bundle_entry[1]:
                        # 非主卷：由主卷统一解压，避免把 .002 当成独立压缩包。
                        member.install_status = "bundled"
                        member.install_message = "分卷文件，由主卷统一解压"
                        member.updated_at = _now_wall_ts()
                        continue
                    else:
                        try:
                            ok, message = await self._install_payload(
                                member, target_dir, bundle_index=bundle_index
                            )
                        except ArchiveRepairScheduled as exc:
                            # 归档校验失败后已安排重新下载：不标记失败/已处理，
                            # 等重下完成会重新进入安装流程。
                            member.install_status = "waiting"
                            member.install_message = str(exc)
                            member.updated_at = _now_wall_ts()
                            repaired_members.add(member.task_id)
                            continue

                    member.install_status = "installed" if ok else "failed"
                    member.install_message = "安装完成" if ok else message
                    member.updated_at = _now_wall_ts()
                    if not ok:
                        failed += 1
                        config.logger.warning(
                            "Install member failed task=%s file=%s: %s",
                            member.task_id,
                            member.file_name,
                            _redact_text(str(message or ""))[:300],
                        )

                lead = self._group_install_lead(all_members or members)
                if failed == 0 and not repaired_members:
                    # 用整组（含此前已装好的分卷）计算体积/写记录，避免部分修复后体积只剩一个包
                    await self._finalize_group_install(lead=lead, members=all_members, target_dir=target_dir)
                    await self._cleanup_baidu_transfer_files(all_members)
                elif repaired_members:
                    title = str(lead.game_title or lead.file_name or "游戏")
                    lead.install_message = "归档校验失败，正在重新下载，完成后会自动安装"
                    for member in members:
                        if member.task_id in repaired_members:
                            continue
                        member.install_message = f"「{title}」有文件正在重新下载，已暂停 Steam 注册"
                else:
                    title = str(lead.game_title or lead.file_name or "游戏")
                    if len(members) == 1:
                        # 单文件场景保留具体失败原因（文件不存在/空间不足/解压失败）。
                        lead.install_message = lead.install_message or "安装失败"
                    else:
                        reasons = "；".join(
                            str(member.install_message or "")
                            for member in members
                            if member.install_status == "failed" and member.install_message
                        )
                        lead.install_message = (
                            f"安装失败（{failed}/{len(members)} 个文件包出错），未注册到 Steam"
                            + (f"：{reasons}" if reasons else "")
                        )
                        for member in members:
                            if member.install_status == "failed":
                                continue
                            member.install_message = f"「{title}」有文件安装失败，已跳过 Steam 注册"
                finished = True
                config.logger.info(
                    "Post-process finished task=%s status=%s message=%s",
                    lead.task_id,
                    lead.install_status,
                    _redact_text(str(lead.install_message or ""))[:300],
                )
            except asyncio.CancelledError:
                # 插件卸载/取消时不要把任务标记成已完成，重启后还能继续。
                cancelled = True
                raise
            finally:
                if not cancelled:
                    # 标记放在工作结束之后：解压中崩溃时任务仍未处理，下次启动会被重新拾起。
                    # 只有整组收尾真正完成才标记 post_processed；异常中断时保持未处理，
                    # 由 _run_post_process_task 的退避重试继续推进，避免“提示会自动重试但永不再试”。
                    for member in members:
                        if finished and member.task_id not in repaired_members:
                            member.post_processed = True
                        else:
                            member.post_processed = False
                            if not finished and str(member.install_status or "") in {"installing", "waiting"}:
                                member.install_status = "failed"
                                member.install_message = "安装流程异常中断，稍后自动重试"
                        member.updated_at = _now_wall_ts()
                    self._invalidate_panel_cache(tasks=True)

    async def _cleanup_baidu_transfer_files(self, members: Sequence[TianyiTaskRecord]) -> None:
        """安装结束后清理百度网盘转存目录，避免占满用户网盘。"""
        for member in members:
            provider = str(member.provider or "")
            if provider not in {"baidu", "baidu_openapi"}:
                continue
            share_ctx = member.share_ctx if isinstance(member.share_ctx, dict) else {}
            if not share_ctx:
                continue
            try:
                if provider == "baidu":
                    transfer_path = str(share_ctx.get("baidu_transfer_path") or "").strip()
                    if not transfer_path:
                        continue
                    await delete_baidu_home_file(
                        cookie=str(self.store.baidu_login.cookie or "").strip(),
                        path=transfer_path,
                    )
                else:
                    access_token = await self._ensure_baidu_openapi_access_token()
                    await delete_baidu_openapi_transfer_file(
                        access_token=access_token,
                        share_ctx=share_ctx,
                        file_id=str(member.file_id or ""),
                    )
            except Exception as exc:
                config.logger.warning("清理百度转存文件失败 task=%s: %s", member.task_id, exc)

    def _quarantine_stale_aria2_sidecars(self, paths: Sequence[str]) -> bool:
        """把已完成文件旁残留的 .aria2 控制文件改名隔离，返回是否处理过。"""
        moved = 0
        for raw in paths:
            path = str(raw or "").strip()
            if not path:
                continue
            sidecar = f"{path}.aria2"
            if not os.path.isfile(sidecar):
                continue
            target = f"{sidecar}.stale-{_now_wall_ts()}"
            try:
                os.replace(sidecar, target)
                moved += 1
            except Exception as exc:
                config.logger.warning("隔离残留 aria2 控制文件失败 %s: %s", sidecar, exc)
        return moved > 0

    async def _wait_payload_settled(
        self,
        paths: Sequence[str],
        *,
        timeout_seconds: float = 30.0,
        poll_seconds: float = 0.5,
        stable_required: int = 2,
    ) -> Tuple[bool, str]:
        """等待 aria2 释放控制文件、且文件大小连续两次不变，再开始解压。

        aria2 报 complete 后仍可能在做写盘收尾；直接解压有概率读到半写入文件。
        """
        normalized = [str(path or "").strip() for path in paths if str(path or "").strip()]
        if not normalized:
            return True, ""
        deadline = time.monotonic() + max(0.5, float(timeout_seconds))
        previous_sizes: Optional[Tuple[int, ...]] = None
        stable_hits = 0
        while time.monotonic() < deadline:
            if any(os.path.exists(f"{path}.aria2") for path in normalized):
                previous_sizes = None
                stable_hits = 0
            else:
                sizes: List[int] = []
                for path in normalized:
                    try:
                        sizes.append(int(os.path.getsize(path)) if os.path.isfile(path) else -1)
                    except Exception:
                        sizes.append(-1)
                current = tuple(sizes)
                if (
                    previous_sizes is not None
                    and current == previous_sizes
                    and all(size >= 0 for size in current)
                ):
                    stable_hits += 1
                    if stable_hits >= max(1, int(stable_required)):
                        return True, ""
                else:
                    stable_hits = 0
                previous_sizes = current
            await asyncio.sleep(max(0.05, float(poll_seconds)))
        return False, "下载文件仍在写入或收尾中（.aria2 控制文件未释放），请稍后重试"

    def _precheck_archive_payload(self, archive_path: str) -> Tuple[bool, str]:
        """解压前的最小预检：空文件 / HTML 错误页。"""
        path = str(archive_path or "").strip()
        if not path or not os.path.isfile(path):
            return False, "归档文件不存在"
        try:
            size = max(0, int(os.path.getsize(path)))
        except Exception as exc:
            return False, f"无法读取归档文件大小: {exc}"
        if size <= 0:
            return False, "归档文件为空，疑似下载未完成"
        try:
            with open(path, "rb") as handle:
                header = handle.read(64)
        except Exception as exc:
            return False, f"无法读取归档文件头: {exc}"
        lowered = header.lower().lstrip()
        if lowered.startswith(b"<!doctype") or lowered.startswith(b"<html") or b"<html" in lowered[:32]:
            return False, "下载内容疑似网页错误页（登录可能已失效），请重新登录后移除任务重下"
        return True, ""

    async def _schedule_archive_repair(self, task: TianyiTaskRecord, reason: str) -> bool:
        """归档校验失败：隔离坏文件并用原直链重下一次（每任务仅一次）。"""
        if int(self._readd_attempts.get(task.task_id, 0)) >= 1:
            return False
        self._readd_attempts[task.task_id] = 1
        try:
            await self.aria2.remove(task.gid)
        except Exception:
            pass
        self._quarantine_download_file(task, "archive-invalid")
        if not await self._readd_task_download(task, consume_attempt=False):
            return False
        task.status = "waiting"
        task.progress = 0.0
        task.speed = 0
        task.post_processed = False
        task.install_status = "waiting"
        task.install_message = f"{reason}，已自动重新下载"
        task.updated_at = _now_wall_ts()
        config.logger.info("Archive validation failed, re-download scheduled task=%s", task.task_id)
        return True

    async def _install_payload(
        self,
        task: TianyiTaskRecord,
        target_dir: str,
        *,
        bundle_index: Optional[Dict[str, Tuple[Any, bool]]] = None,
    ) -> Tuple[bool, str]:
        """把单个文件包解压/复制到目标目录（不写记录、不注册 Steam）。"""
        local_path = self._task_local_path(task)
        if not local_path or not os.path.isfile(local_path):
            return False, "下载文件不存在，无法安装"

        bundle_entry = (bundle_index or {}).get(local_path)
        archive_set = bundle_entry[0] if bundle_entry else None
        part_paths = (
            [str(part.path) for part in archive_set.parts]
            if archive_set is not None
            else [local_path]
        )

        settled, settle_message = await self._wait_payload_settled(part_paths)
        if not settled:
            # 大文件在 SD 卡上可能已经完整，但 aria2 的 .aria2 控制文件
            # 还没释放；文件大小已匹配时把它隔离，避免用户看到一次假失败。
            if self._file_matches_expected_size(task):
                if self._quarantine_stale_aria2_sidecars(part_paths):
                    settled = True
                    settled_message_note = "已清理残留的 aria2 控制文件"
                    config.logger.info(
                        "清理残留 aria2 控制文件 task=%s: %s",
                        task.task_id,
                        settled_message_note,
                    )
            if not settled:
                raise InstallRetryable(settle_message)

        task.install_status = "installing"
        task.install_message = "正在安装..."
        task.updated_at = _now_wall_ts()

        if self._is_archive_file(local_path) or archive_set is not None:
            ok, reason = self._precheck_archive_payload(local_path)
            if not ok:
                return False, reason

            # 解压前用 `7z t` 做完整性校验；失败先自动重下一次。
            verified, verify_reason = await asyncio.to_thread(self.seven_zip.test_archive, local_path)
            if not verified:
                if await self._schedule_archive_repair(task, verify_reason):
                    raise ArchiveRepairScheduled(task.install_message)
                return False, verify_reason

            # 解压前先检查剩余空间（多分卷按所有分卷之和估算）。
            archive_size = 0
            for part_path in part_paths:
                try:
                    if os.path.isfile(part_path):
                        archive_size += max(0, int(os.path.getsize(part_path)))
                except Exception:
                    continue
            if archive_size <= 0:
                try:
                    archive_size = max(0, int(os.path.getsize(local_path)))
                except Exception:
                    archive_size = 0
            free_bytes = _disk_free_bytes(target_dir)
            required_bytes = int(archive_size * EXTRACT_FREE_SPACE_MARGIN)
            if free_bytes < required_bytes:
                return False, (
                    f"安装目录空间不足：至少需要 {_format_size_bytes(required_bytes)}，"
                    f"当前剩余 {_format_size_bytes(free_bytes)}"
                )
            ok, reason = await asyncio.to_thread(
                self._extract_archive_to_dir,
                local_path,
                target_dir,
                force_seven_zip=bool(archive_set) or looks_like_multi_volume_name(local_path),
            )
            if not ok:
                return False, reason
            return True, ""

        # 非压缩包按普通文件归档到安装目录。
        file_name = os.path.basename(local_path)
        dest_file = os.path.join(target_dir, file_name)
        try:
            if os.path.realpath(local_path) != os.path.realpath(dest_file):
                shutil.copy2(local_path, dest_file)
        except Exception as exc:
            return False, f"复制安装文件失败: {exc}"
        return True, ""

    def _compute_group_size_bytes(self, members: Sequence[TianyiTaskRecord]) -> int:
        """安装体积：组内所有文件包大小之和（优先用清单里的预期大小）。"""
        total = 0
        for member in members:
            size = max(0, _safe_int(member.file_size, 0))
            if size <= 0:
                path = self._task_local_path(member)
                try:
                    if path and os.path.isfile(path):
                        size = max(0, int(os.path.getsize(path)))
                except Exception:
                    size = 0
            total += size
        return total

    async def _finalize_group_install(
        self,
        *,
        lead: TianyiTaskRecord,
        members: Sequence[TianyiTaskRecord],
        target_dir: str,
    ) -> None:
        """整组文件安装完成后：写已安装记录、注册 Steam、按设置清理安装包。"""
        settings = self.store.settings
        game_id = str(lead.game_id or "").strip()
        game_title = str(lead.game_title or lead.file_name or "未命名游戏")

        installed_size_bytes = self._compute_group_size_bytes(members)
        existing_record = self._find_installed_record(game_id=game_id, install_path=target_dir)
        if installed_size_bytes <= 0 and existing_record is not None:
            installed_size_bytes = max(0, _safe_int(existing_record.size_bytes, 0))

        existing_playtime_seconds = 0
        existing_playtime_sessions = 0
        existing_playtime_last_played_at = 0
        existing_playtime_active_started_at = 0
        existing_playtime_active_app_id = 0
        existing_steam_app_id = 0
        if existing_record is not None:
            existing_playtime_seconds = max(0, _safe_int(existing_record.playtime_seconds, 0))
            existing_playtime_sessions = max(0, _safe_int(existing_record.playtime_sessions, 0))
            existing_playtime_last_played_at = max(0, _safe_int(existing_record.playtime_last_played_at, 0))
            existing_playtime_active_started_at = max(0, _safe_int(existing_record.playtime_active_started_at, 0))
            existing_playtime_active_app_id = max(0, _safe_int(existing_record.playtime_active_app_id, 0))
            existing_steam_app_id = max(0, _safe_int(existing_record.steam_app_id, 0))

        self.store.upsert_installed_game(
            TianyiInstalledGame(
                game_id=game_id,
                game_title=game_title,
                install_path=target_dir,
                source_path=self._task_local_path(lead),
                status="installed",
                size_bytes=installed_size_bytes,
                steam_app_id=existing_steam_app_id,
                playtime_seconds=existing_playtime_seconds,
                playtime_sessions=existing_playtime_sessions,
                playtime_last_played_at=existing_playtime_last_played_at,
                playtime_active_started_at=existing_playtime_active_started_at,
                playtime_active_app_id=existing_playtime_active_app_id,
                platform=str(lead.platform or "pc"),
                emulator=emulator_name_for_platform(str(lead.platform or "")),
            )
        )
        self._invalidate_panel_cache(tasks=True, installed=True)

        message_parts: List[str] = ["安装完成"]
        if len(members) > 1:
            message_parts.append(f"{len(members)} 个文件包")

        steam_result = await self._auto_register_task_to_steam(task=lead, target_dir=target_dir)
        if steam_result.get("ok"):
            app_id = _safe_int(steam_result.get("appid_unsigned"), 0)
            if app_id > 0:
                installed_record = self._find_installed_record(game_id=game_id, install_path=target_dir)
                if installed_record is not None:
                    changed = False
                    if max(0, _safe_int(installed_record.steam_app_id, 0)) != app_id:
                        installed_record.steam_app_id = app_id
                        changed = True
                    for attr in ("rom_path", "launcher_path", "emulator"):
                        value = str(steam_result.get(attr, "") or "")
                        if value and getattr(installed_record, attr, "") != value:
                            setattr(installed_record, attr, value)
                            changed = True
                    if changed:
                        installed_record.updated_at = _now_wall_ts()
                        await asyncio.to_thread(self.store.save)
                        self._invalidate_panel_cache(installed=True)
                self._steam_restart_pending = {
                    "pending": True,
                    "game_id": game_id,
                    "title": game_title,
                    "app_id": app_id,
                    "updated_at": _now_wall_ts(),
                }
                message_parts.append(
                    f"已写入 Steam 快捷方式（AppID {app_id}）；"
                    "Steam 运行中不会立即刷新，请重启 Steam 后在库中查看"
                )
            else:
                message_parts.append(str(steam_result.get("message") or "已加入 Steam"))
        else:
            reason = str(steam_result.get("message", "") or "").strip() or "未知错误"
            message_parts.append(f"Steam 导入失败: {reason}")
        warning = str(steam_result.get("warning", "") or "").strip()
        if warning:
            message_parts.append(warning)
        for item in list(steam_result.get("setup_messages", []) or []):
            text = str(item or "").strip()
            if text:
                message_parts.append(text)

        if bool(settings.auto_delete_package):
            deleted = 0
            for member in members:
                path = self._task_local_path(member)
                if not path or not os.path.isfile(path):
                    continue
                try:
                    os.remove(path)
                    deleted += 1
                except Exception as exc:
                    message_parts.append(f"删除安装包失败: {exc}")
            if deleted:
                message_parts.append(f"已删除 {deleted} 个下载压缩包")

        # 非主卷（bundled）的 lead 不能被覆盖成 installed：那只是主卷解压出来的分卷文件。
        if str(lead.install_status or "") != "bundled":
            lead.install_status = "installed"
        lead.installed_path = target_dir
        lead.install_message = "，".join(message_parts)
        lead.updated_at = _now_wall_ts()
        for member in members:
            member.installed_path = target_dir
            member.updated_at = _now_wall_ts()
            if member.install_status == "bundled":
                # 非主卷：保持 bundled 语义，不覆盖“由主卷统一解压”的说明。
                continue
            member.install_status = "installed"
            if member.task_id != lead.task_id:
                member.install_message = f"已随「{game_title}」安装完成"

    def _resolve_install_target_dir(self, task: TianyiTaskRecord, install_root: str) -> str:
        """解析任务的目标安装目录。"""
        raw_openpath = str(task.openpath or "").strip().replace("\\", "/")
        if raw_openpath:
            parts = [
                self._sanitize_path_segment(part)
                for part in raw_openpath.split("/")
                if part and part not in {".", ".."}
            ]
            parts = [part for part in parts if part]
            if parts:
                # openpath 仅用于确定游戏根目录，避免把 exe 名当成目录继续拼接。
                root_part = parts[0]
                if len(parts) == 1:
                    stem, ext = os.path.splitext(root_part)
                    if ext:
                        normalized_stem = self._sanitize_path_segment(stem)
                        if normalized_stem:
                            root_part = normalized_stem
                return os.path.join(install_root, root_part)

        title = self._sanitize_path_segment(str(task.game_title or task.file_name or task.game_id or "game"))
        if not title:
            title = "game"
        game_id = self._sanitize_path_segment(str(task.game_id or ""))
        if game_id:
            return os.path.join(install_root, f"{title}_{game_id[:12]}")
        return os.path.join(install_root, title)

    async def _auto_register_task_to_steam(self, *, task: TianyiTaskRecord, target_dir: str) -> Dict[str, Any]:
        """安装完成后自动写入 Steam 快捷方式、Proton 和封面。"""
        platform = str(getattr(task, "platform", "pc") or "pc").strip().lower()
        if emulator_name_for_platform(platform):
            return await self._auto_register_emulator_to_steam(
                task=task,
                target_dir=target_dir,
                platform=platform,
            )

        exe_path = self._resolve_installed_executable_path(task=task, target_dir=target_dir)
        if not exe_path:
            return {"ok": False, "message": "安装目录未找到可执行文件"}

        game_id = str(task.game_id or "").strip()
        launch_token = re.sub(r"[^a-zA-Z0-9._-]+", "_", game_id or task.task_id or "game").strip("_")
        if not launch_token:
            launch_token = "game"
        launch_options = f"freedeckcy:tianyi:{launch_token}"

        display_name = self._derive_display_title_for_steam(str(task.game_title or task.file_name or "freedeckCY Game"))

        categories = ""
        try:
            entry = self.catalog.get_by_game_id(game_id)
            if entry is not None:
                categories = str(entry.categories or "")
        except Exception:
            categories = ""

        cover_info: Dict[str, Any] = {}
        try:
            cover_info = await self.resolve_catalog_cover(
                game_id=game_id,
                title=str(task.game_title or display_name),
                categories=categories,
            )
        except Exception as exc:
            config.logger.warning("Resolve catalog cover failed for %s: %s", game_id or display_name, exc)
            cover_info = {}

        cover_landscape = str(cover_info.get("cover_url", "") or "").strip()
        cover_portrait = str(cover_info.get("square_cover_url", "") or "").strip()
        steam_app_id = _safe_int(cover_info.get("app_id"), 0)

        try:
            result = await add_or_update_tianyi_shortcut(
                game_id=game_id or task.task_id,
                display_name=display_name,
                exe_path=exe_path,
                launch_options=launch_options,
                proton_tool=str(self.store.settings.proton_tool or "auto"),
                cover_landscape_url=cover_landscape,
                cover_portrait_url=cover_portrait,
                steam_app_id=steam_app_id,
            )
            if not result.get("ok"):
                config.logger.warning(
                    "Auto add to Steam failed game=%s exe=%s reason=%s",
                    game_id or display_name,
                    exe_path,
                    result.get("message", ""),
                )
            return result
        except Exception as exc:
            config.logger.exception("Auto add to Steam exception game=%s exe=%s", game_id or display_name, exe_path)
            return {"ok": False, "message": str(exc)}

    async def _auto_register_emulator_to_steam(
        self,
        *,
        task: TianyiTaskRecord,
        target_dir: str,
        platform: str,
    ) -> Dict[str, Any]:
        """模拟器资源：生成启动脚本并注册原生 Linux 快捷方式（不写 Proton 映射）。"""
        rom_path = find_rom_file(
            target_dir,
            open_path=str(task.openpath or ""),
            platform_name=platform,
            strict=True,
            title=str(task.game_title or ""),
        )
        cia_files: List[Path] = []
        if not rom_path and str(platform).lower() == "3ds":
            try:
                cia_files = sorted(
                    {path for path in Path(target_dir).rglob("*.cia") if path.is_file()},
                    key=lambda path: (len(str(path)), str(path)),
                )
            except Exception:
                cia_files = []
        if not rom_path and not cia_files:
            return {
                "ok": False,
                "message": f"安装目录未找到可唯一定位的 {str(platform).upper()} ROM 或 .cia，请检查目录/openpath",
            }
        try:
            command = await ensure_emulator(platform, self.plugin_dir)
        except Exception as exc:
            return {"ok": False, "message": f"模拟器不可用: {exc}"}

        if cia_files:
            setup_messages: List[str] = []
            try:
                setup_messages = await asyncio.to_thread(
                    setup_emulator,
                    platform,
                    command,
                    seven_zip=self.seven_zip,
                )
            except Exception as exc:
                setup_messages = [f"模拟器初始化失败: {exc}"]
            env = dict(os.environ)
            # Azahar --install 在 Qt 前端内执行；Decky 后端无 DISPLAY，
            # 必须用 offscreen，否则 QApplication 初始化就会退出。
            env["QT_QPA_PLATFORM"] = "offscreen"
            env["SDL_VIDEODRIVER"] = "dummy"
            installed = 0
            failures: List[str] = []
            for cia_path in cia_files:
                try:
                    process = await asyncio.to_thread(
                        subprocess.run,
                        [*command, "--install", str(cia_path)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        timeout=600,
                        env=env,
                    )
                    if process.returncode == 0:
                        installed += 1
                    else:
                        output = (process.stdout or b"").decode("utf-8", "replace").strip()
                        failures.append(f"{cia_path.name}: {output[:160] or f'exit={process.returncode}'}")
                except Exception as exc:
                    failures.append(f"{cia_path.name}: {exc}")
            if installed <= 0:
                return {
                    "ok": False,
                    "message": "Azahar CIA 自动安装失败：" + "；".join(failures[:3]),
                }
            message = f"CIA 已自动安装到 Azahar：{installed} 个"
            if failures:
                message += f"（失败 {len(failures)} 个）"
            message += "；请从 Azahar 游戏列表启动"
            if setup_messages:
                message += "；" + "，".join(str(item) for item in setup_messages[:3] if str(item).strip())
            return {"ok": True, "appid_unsigned": 0, "message": message}

        spec = get_spec(platform)
        setup_messages: List[str] = []
        try:
            setup_messages = await asyncio.to_thread(
                setup_emulator,
                platform,
                command,
                seven_zip=self.seven_zip,
            )
        except Exception as exc:
            setup_messages = [f"模拟器初始化失败: {exc}"]

        wrapper_path = os.path.join(target_dir, "launch-freedeckcy.sh")
        try:
            create_launch_wrapper(
                command=command,
                rom_path=rom_path,
                wrapper_path=wrapper_path,
                platform_name=platform,
            )
        except Exception as exc:
            return {"ok": False, "message": f"生成启动脚本失败: {exc}"}

        game_id = str(task.game_id or "").strip()
        launch_token = re.sub(r"[^a-zA-Z0-9._-]+", "_", game_id or task.task_id or "game").strip("_")
        if not launch_token:
            launch_token = "game"
        # 启动脚本会忽略 Steam 传入的参数；token 仅用于卸载时定位快捷方式。
        launch_options = f"freedeckcy:tianyi:{launch_token}"
        display_name = self._derive_display_title_for_steam(
            str(task.game_title or task.file_name or "freedeckCY GBA")
        )
        categories = ""
        try:
            entry = self.catalog.get_by_game_id(game_id)
            if entry is not None:
                categories = str(entry.categories or "")
        except Exception:
            categories = ""

        cover_info: Dict[str, Any] = {}
        try:
            cover_info = await self.resolve_catalog_cover(
                game_id=game_id,
                title=str(task.game_title or display_name),
                categories=categories,
            )
        except Exception as exc:
            config.logger.warning("Resolve emulator cover failed for %s: %s", game_id or display_name, exc)

        try:
            result = await add_or_update_tianyi_shortcut(
                game_id=game_id or task.task_id,
                display_name=display_name,
                exe_path=wrapper_path,
                launch_options=launch_options,
                proton_tool="none",
                cover_landscape_url=str(cover_info.get("cover_url", "") or ""),
                cover_portrait_url=str(cover_info.get("square_cover_url", "") or ""),
                steam_app_id=_safe_int(cover_info.get("app_id"), 0),
            )
            if not result.get("ok"):
                config.logger.warning(
                    "Auto add emulator game to Steam failed game=%s exe=%s reason=%s",
                    game_id or display_name,
                    wrapper_path,
                    result.get("message", ""),
                )
            result["rom_path"] = rom_path
            result["launcher_path"] = wrapper_path
            result["emulator"] = spec.adapter if spec else emulator_name_for_platform(platform)
            if setup_messages:
                result["setup_messages"] = setup_messages
            return result
        except Exception as exc:
            config.logger.exception("Auto add emulator game to Steam exception game=%s", game_id or display_name)
            return {"ok": False, "message": str(exc)}

    def _derive_display_title_for_steam(self, title: str) -> str:
        """优先取中文标题片段。"""
        raw = " ".join(str(title or "").replace("\u3000", " ").split())
        if not raw:
            return "freedeckCY Game"

        parts = [part.strip() for part in re.split(r"[\\/|｜丨]+", raw) if part and part.strip()]
        if not parts:
            return raw

        for part in parts:
            if re.search(r"[\u4e00-\u9fff]", part):
                return part
        return parts[0]

    def _find_declared_executable(self, root_dir: str, declared: str) -> str:
        """按目录里的 executable_name 定位启动文件；找不到返回空。"""
        root = os.path.realpath(os.path.expanduser(str(root_dir or "").strip()))
        raw = str(declared or "").strip().replace("\\", "/").strip("/")
        if not root or not raw or not os.path.isdir(root):
            return ""
        parts = [part for part in raw.split("/") if part and part not in {".", ".."}]
        if not parts or ".." in parts:
            return ""
        candidate = os.path.realpath(os.path.join(root, *parts))
        if os.path.isfile(candidate) and _is_within_dir(candidate, root):
            return candidate
        leaf = parts[-1]
        matched = self._find_path_by_leaf_name(root, leaf, max_depth=8)
        if matched and _is_within_dir(matched, root):
            return matched
        return ""

    def _resolve_installed_executable_path(self, *, task: TianyiTaskRecord, target_dir: str) -> str:
        """基于 openpath 优先定位安装后的可执行文件。"""
        root = os.path.realpath(os.path.expanduser(str(target_dir or "").strip()))
        if not root or not os.path.isdir(root):
            return ""

        declared = str(getattr(task, "executable_name", "") or "").strip()
        if declared:
            declared_path = self._find_declared_executable(root, declared)
            if declared_path:
                return declared_path

        raw_openpath = str(task.openpath or "").strip().replace("\\", "/")
        if raw_openpath:
            parts = [
                self._sanitize_path_segment(part)
                for part in raw_openpath.split("/")
                if part and part not in {".", ".."}
            ]
            parts = [part for part in parts if part]

            if parts:
                rel_parts = parts[1:] if len(parts) > 1 else parts
                if rel_parts:
                    candidate = os.path.realpath(os.path.join(root, *rel_parts))
                    if os.path.isfile(candidate):
                        return candidate
                    leaf = rel_parts[-1]
                    matched_leaf = self._find_path_by_leaf_name(root, leaf, max_depth=8)
                    if matched_leaf:
                        return matched_leaf

        fallback = self._find_first_executable_candidate(root, max_depth=8)
        if fallback:
            return fallback
        return ""

    def _find_path_by_leaf_name(self, root_dir: str, leaf_name: str, max_depth: int = 6) -> str:
        """在目录树中按文件名查找（大小写不敏感）。"""
        root = os.path.realpath(os.path.expanduser(str(root_dir or "").strip()))
        leaf = str(leaf_name or "").strip().lower()
        if not root or not leaf or not os.path.isdir(root):
            return ""

        base_depth = root.count(os.sep)
        for dirpath, dirnames, filenames in os.walk(root):
            depth = dirpath.count(os.sep) - base_depth
            if depth >= max_depth:
                dirnames[:] = []
            for name in filenames:
                if str(name).lower() != leaf:
                    continue
                return os.path.realpath(os.path.join(dirpath, name))
        return ""

    def _find_first_executable_candidate(self, root_dir: str, max_depth: int = 6) -> str:
        """回退查找首个可执行文件候选（优先 .exe）。"""
        root = os.path.realpath(os.path.expanduser(str(root_dir or "").strip()))
        if not root or not os.path.isdir(root):
            return ""

        best_path = ""
        best_rank: Tuple[int, int, int] = (9, 999, 99999)
        base_depth = root.count(os.sep)

        for dirpath, dirnames, filenames in os.walk(root):
            depth = dirpath.count(os.sep) - base_depth
            if depth >= max_depth:
                dirnames[:] = []

            for name in filenames:
                lower = str(name).lower()
                ext_rank = 9
                if lower.endswith(".exe"):
                    ext_rank = 0
                elif lower.endswith(".bat") or lower.endswith(".cmd"):
                    ext_rank = 1
                elif lower.endswith(".sh") or lower.endswith(".x86_64"):
                    ext_rank = 2
                elif lower.endswith(".appimage"):
                    ext_rank = 3
                else:
                    continue

                candidate = os.path.realpath(os.path.join(dirpath, name))
                rank = (ext_rank, max(0, depth), len(candidate))
                if rank < best_rank:
                    best_rank = rank
                    best_path = candidate

        return best_path

    def _sanitize_path_segment(self, text: str) -> str:
        """清理路径片段，避免非法字符。"""
        raw = str(text or "").strip()
        if not raw:
            return ""
        cleaned_chars: List[str] = []
        for ch in raw:
            if ord(ch) < 32:
                continue
            if ch in '<>:"/\\|?*':
                continue
            cleaned_chars.append(ch)
        value = "".join(cleaned_chars).strip().strip(".")
        return value

    def _is_archive_file(self, file_path: str) -> bool:
        """判断文件是否为支持的压缩包（含多分卷命名）。"""
        normalized = str(file_path or "").strip().lower()
        if any(normalized.endswith(ext) for ext in ARCHIVE_SUFFIXES):
            return True
        # game.7z.001 / game.part1.rar / game.z01 / game.r00 这类分卷
        return looks_like_multi_volume_name(file_path)

    def _safe_extract_tar(self, archive_path: str, staging_dir: str) -> None:
        """安全解压 tar 系归档：拒绝绝对路径、..、链接/设备文件。"""
        with tarfile.open(archive_path, "r:*") as archive:
            for member in archive.getmembers():
                name = str(member.name or "").replace("\\", "/")
                parts = [part for part in name.split("/") if part not in {"", "."}]
                if name.startswith("/") or ".." in parts:
                    raise ValueError(f"压缩包包含越界路径: {name[:200]}")
                if member.issym() or member.islnk() or member.isdev():
                    raise ValueError(f"压缩包包含链接/设备文件，已拒绝: {name[:200]}")
            try:
                archive.extractall(staging_dir, filter="data")
            except TypeError:
                # Python < 3.12 没有 filter；上面的成员校验已挡住链接与越界路径。
                archive.extractall(staging_dir)

    @staticmethod
    def _assert_staging_safe(staging_dir: str) -> None:
        """解压后再次确认 staging 中没有符号链接。"""
        for dirpath, dirnames, filenames in os.walk(staging_dir, followlinks=False):
            for name in list(dirnames) + list(filenames):
                path = os.path.join(dirpath, name)
                if os.path.islink(path):
                    raise ValueError(f"压缩包包含符号链接，已拒绝: {os.path.relpath(path, staging_dir)[:200]}")

    def _extract_archive_to_dir(
        self,
        archive_path: str,
        target_dir: str,
        *,
        force_seven_zip: bool = False,
    ) -> Tuple[bool, str]:
        """解压压缩包到目标目录。

        多分卷归档（如 .7z.001）必须交给 7z 统一处理，不能按扩展名走 shutil。
        """
        normalized = str(archive_path or "").strip().lower()
        try:
            os.makedirs(target_dir, exist_ok=True)
        except Exception as exc:
            return False, f"创建安装目录失败: {exc}"

        parent_dir = os.path.dirname(target_dir)
        staging_parent = parent_dir if parent_dir and os.path.isdir(parent_dir) else None
        try:
            staging_dir = tempfile.mkdtemp(prefix="freedeckcy_extract_", dir=staging_parent)
        except Exception:
            staging_dir = tempfile.mkdtemp(prefix="freedeckcy_extract_")

        try:
            if force_seven_zip or normalized.endswith(".7z") or normalized.endswith(".rar"):
                try:
                    self.seven_zip.extract_archive(archive_path, staging_dir)
                except SevenZipError as exc:
                    return False, str(exc)
                except Exception as exc:
                    return False, f"7z 解压异常: {exc}"
            else:
                try:
                    if normalized.endswith((".tar", ".tgz", ".tar.gz", ".tbz2", ".tar.bz2", ".tar.xz", ".txz")):
                        self._safe_extract_tar(archive_path, staging_dir)
                    else:
                        shutil.unpack_archive(archive_path, staging_dir)
                except Exception as exc:
                    return False, f"解压失败: {exc}"

            try:
                self._assert_staging_safe(staging_dir)
                self._merge_extracted_content(staging_dir, target_dir)
            except Exception as exc:
                return False, f"整理解压目录失败: {exc}"
            return True, ""
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)

    def _merge_extracted_content(self, staging_dir: str, target_dir: str) -> None:
        """将临时解压目录内容合并到目标目录，并尽量去掉一层包内同名根目录。"""
        if not staging_dir or not os.path.isdir(staging_dir):
            return
        os.makedirs(target_dir, exist_ok=True)

        entries = [name for name in os.listdir(staging_dir) if name not in {".", ".."}]
        if not entries:
            return

        source_root = staging_dir
        target_base = os.path.basename(os.path.normpath(target_dir))
        preferred = os.path.join(staging_dir, target_base)
        if target_base and os.path.isdir(preferred) and not os.path.islink(preferred):
            source_root = preferred
        else:
            dir_entries = [
                name for name in entries
                if os.path.isdir(os.path.join(staging_dir, name)) and not os.path.islink(os.path.join(staging_dir, name))
            ]
            file_entries = [
                name for name in entries
                if not (os.path.isdir(os.path.join(staging_dir, name)) and not os.path.islink(os.path.join(staging_dir, name)))
            ]
            if len(dir_entries) == 1 and not file_entries:
                source_root = os.path.join(staging_dir, dir_entries[0])

        for name in os.listdir(source_root):
            source_path = os.path.join(source_root, name)
            target_path = os.path.join(target_dir, name)
            self._merge_path(source_path, target_path)

    def _merge_path(self, source_path: str, target_path: str) -> None:
        """将 source_path 合并到 target_path，目录递归合并，文件冲突时覆盖。"""
        if os.path.islink(source_path):
            raise ValueError("拒绝合并符号链接")
        if not os.path.exists(source_path):
            return

        if not os.path.exists(target_path):
            shutil.move(source_path, target_path)
            return

        source_is_dir = os.path.isdir(source_path) and not os.path.islink(source_path)
        target_is_dir = os.path.isdir(target_path) and not os.path.islink(target_path)
        if source_is_dir and target_is_dir:
            for child in os.listdir(source_path):
                self._merge_path(
                    os.path.join(source_path, child),
                    os.path.join(target_path, child),
                )
            try:
                os.rmdir(source_path)
            except Exception:
                pass
            return

        if target_is_dir:
            shutil.rmtree(target_path, ignore_errors=True)
        else:
            try:
                os.remove(target_path)
            except Exception:
                pass
        shutil.move(source_path, target_path)

    async def _set_qr_login_state(
        self,
        *,
        session_id: str,
        stage: str,
        message: str,
        reason: str,
        next_action: str,
        user_account: str,
        image_url: str,
        expires_at: int,
        diagnostics: Optional[Dict[str, Any]],
    ) -> None:
        """更新二维码登录状态。"""
        self._qr_login_state = {
            "session_id": str(session_id or ""),
            "stage": str(stage or "idle"),
            "message": str(message or ""),
            "reason": str(reason or ""),
            "next_action": str(next_action or ""),
            "user_account": str(user_account or ""),
            "image_url": str(image_url or ""),
            "expires_at": int(expires_at or 0),
            "updated_at": _now_wall_ts(),
            "diagnostics": diagnostics or {},
        }

    async def _safe_close_client_session(self, client: Optional[aiohttp.ClientSession]) -> None:
        """安全关闭 aiohttp 会话。"""
        if not isinstance(client, aiohttp.ClientSession):
            return
        if client.closed:
            return
        try:
            await client.close()
        except Exception:
            pass

    async def _close_qr_login_context_locked(self) -> None:
        """关闭并清理二维码登录上下文（需持有锁）。"""
        context = self._qr_login_context
        self._qr_login_context = None
        if not isinstance(context, dict):
            return
        await self._safe_close_client_session(context.get("client"))

    def _build_qr_ssl_context(self) -> Tuple[ssl.SSLContext, Dict[str, Any]]:
        """构建二维码登录用 TLS 上下文并输出证书链诊断。"""
        diagnostics: Dict[str, Any] = {
            "mode": "verify",
            "selected_ca_file": "",
            "candidate_ca_files": [],
            "candidate_errors": [],
        }

        env_cert_file = str(os.environ.get("SSL_CERT_FILE", "") or "").strip()
        candidates: List[str] = [str(Path(__file__).resolve().with_name("cacert.pem"))]
        if env_cert_file:
            candidates.append(env_cert_file)
        candidates.extend(list(QR_CA_CANDIDATE_FILES))

        try:
            import certifi  # type: ignore

            certifi_path = str(certifi.where() or "").strip()
            if certifi_path:
                candidates.append(certifi_path)
        except Exception:
            pass

        dedup_candidates: List[str] = []
        seen = set()
        for raw in candidates:
            path = os.path.realpath(os.path.expanduser(str(raw).strip()))
            if not path or path in seen:
                continue
            seen.add(path)
            dedup_candidates.append(path)

        diagnostics["candidate_ca_files"] = dedup_candidates
        for path in dedup_candidates:
            if not os.path.isfile(path):
                continue
            try:
                context = ssl.create_default_context(cafile=path)
                diagnostics["selected_ca_file"] = path
                return context, diagnostics
            except Exception as exc:
                diagnostics["candidate_errors"].append({"path": path, "error": str(exc)})

        context = ssl.create_default_context()
        diagnostics["selected_ca_file"] = "system_default"

        # 仅用于紧急排障，默认不关闭校验。
        insecure_flag = str(os.environ.get("FREEDECKCY_QR_INSECURE_TLS", "") or "").strip().lower()
        if insecure_flag in {"1", "true", "yes"}:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            diagnostics["mode"] = "insecure"
            diagnostics["selected_ca_file"] = "insecure_env_override"

        return context, diagnostics

    def _build_qr_headers(self, *, req_id: str, lt: str, referer: str) -> Dict[str, str]:
        """构建二维码相关请求头。"""
        headers: Dict[str, str] = {
            "User-Agent": "Mozilla/5.0 (freedeckCY/1.0)",
            "Accept": "application/json, text/plain, */*",
            "Referer": referer or "https://open.e.189.cn/",
        }
        if req_id:
            headers["reqId"] = req_id
            headers["REQID"] = req_id
        if lt:
            headers["lt"] = lt
        return headers

    def _parse_json_like_text(self, raw_text: str) -> Dict[str, Any]:
        """解析 text/html 包裹的 JSON 返回。"""
        text = str(raw_text or "").strip()
        if not text:
            raise TianyiApiError("接口返回为空")
        try:
            payload = json.loads(text)
        except Exception as exc:
            raise TianyiApiError(f"JSON 解析失败: {exc}") from exc
        if not isinstance(payload, dict):
            raise TianyiApiError("接口返回结构异常")
        return payload

    def _extract_qr_status_code(self, payload: Dict[str, Any]) -> int:
        """提取二维码轮询状态码。"""
        for key in ("status", "result", "code", "res_code"):
            if key not in payload:
                continue
            try:
                return int(str(payload.get(key)))
            except Exception:
                continue
        return -99999

    def _extract_qr_redirect_url(self, payload: Dict[str, Any]) -> str:
        """提取扫码成功后的跳转地址。"""
        direct_keys = ("redirectUrl", "redirectURL", "url", "targetUrl", "jumpUrl")
        for key in direct_keys:
            value = str(payload.get(key, "") or "").strip()
            if value:
                return value
        data_obj = payload.get("data")
        if isinstance(data_obj, dict):
            for key in direct_keys:
                value = str(data_obj.get(key, "") or "").strip()
                if value:
                    return value
        return ""

    def _build_tianyi_cookie_from_cookie_jar(self, jar: aiohttp.CookieJar) -> str:
        """从 aiohttp CookieJar 组装 189 域 Cookie 头。"""
        kv_map: Dict[str, str] = {}

        # 优先按目标域筛选，兼容 host-only cookie（无 Domain 属性）。
        for target in (
            URL("https://cloud.189.cn/"),
            URL("https://h5.cloud.189.cn/"),
            URL("https://open.e.189.cn/"),
        ):
            try:
                scoped = jar.filter_cookies(target)
            except Exception:
                scoped = {}
            for key, morsel in scoped.items():
                name = str(key or "").strip()
                value = str(getattr(morsel, "value", "") or "").strip()
                if not name or not value:
                    continue
                # 保留 cloud/h5 首次命中的同名值，避免被 open.e 同名 cookie 覆盖。
                if name not in kv_map:
                    kv_map[name] = value

        # 兜底：补充所有 189 域 cookie（防止某些环境 filter 丢失）。
        for morsel in jar:
            try:
                domain = str(morsel["domain"] or "").lower()
            except Exception:
                domain = ""
            if domain and "189.cn" not in domain:
                continue
            name = str(getattr(morsel, "key", "") or "").strip()
            value = str(getattr(morsel, "value", "") or "").strip()
            if not name or not value:
                continue
            if name not in kv_map:
                kv_map[name] = value

        if not kv_map:
            return ""
        ordered = [f"{k}={v}" for k, v in sorted(kv_map.items(), key=lambda item: item[0].lower())]
        return "; ".join(ordered)

    async def _bootstrap_qr_login_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """初始化二维码登录上下文。"""
        client = context.get("client")
        if not isinstance(client, aiohttp.ClientSession):
            raise TianyiApiError("二维码会话未初始化")

        redirect_url = quote("https://cloud.189.cn/web/main/", safe="")
        bootstrap_url = f"https://cloud.189.cn/api/portal/loginUrl.action?redirectURL={redirect_url}&pageId=1"

        base_headers = {
            "User-Agent": "Mozilla/5.0 (freedeckCY/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        async with client.get(bootstrap_url, headers=base_headers, allow_redirects=False) as resp:
            if resp.status in {301, 302, 303, 307, 308}:
                login_entry_url = str(resp.headers.get("Location", "") or "").strip()
            else:
                login_entry_url = str(resp.url)
            if not login_entry_url:
                raise TianyiApiError("未获取到天翼登录入口地址")

        async with client.get(login_entry_url, headers=base_headers, allow_redirects=True) as resp:
            login_page_url = str(resp.url)
            await resp.text()

        query = parse_qs(urlparse(login_page_url).query or "", keep_blank_values=True)
        app_id = str((query.get("appId") or [""])[0] or "").strip()
        lt = str((query.get("lt") or [""])[0] or "").strip()
        req_id = str((query.get("reqId") or [""])[0] or "").strip()
        if not app_id or not lt or not req_id:
            raise TianyiApiError("登录页面参数缺失（appId/lt/reqId）")

        api_headers = self._build_qr_headers(req_id=req_id, lt=lt, referer=login_page_url)

        async with client.post(
            "https://open.e.189.cn/api/logbox/oauth2/appConf.do",
            data={"version": "2.0", "appKey": app_id},
            headers=api_headers,
        ) as resp:
            app_conf_text = await resp.text()
            if resp.status >= 400:
                raise TianyiApiError(f"appConf 请求失败 status={resp.status}")
        app_conf_payload = self._parse_json_like_text(app_conf_text)
        app_conf_data = app_conf_payload.get("data")
        if not isinstance(app_conf_data, dict):
            raise TianyiApiError("appConf 返回异常")

        async with client.post(
            "https://open.e.189.cn/api/logbox/oauth2/getUUID.do",
            data={"appId": app_id},
            headers=api_headers,
        ) as resp:
            uuid_text = await resp.text()
            if resp.status >= 400:
                raise TianyiApiError(f"getUUID 请求失败 status={resp.status}")
        uuid_payload = self._parse_json_like_text(uuid_text)
        if self._extract_qr_status_code(uuid_payload) != QR_STATUS_SUCCESS:
            msg = str(uuid_payload.get("msg", "") or "二维码生成失败")
            raise TianyiApiError(msg)

        uuid_value = str(uuid_payload.get("uuid", "") or "").strip()
        encryuuid = str(uuid_payload.get("encryuuid", "") or "").strip()
        encodeuuid = str(uuid_payload.get("encodeuuid", "") or "").strip()
        if not uuid_value or not encryuuid or not encodeuuid:
            raise TianyiApiError("二维码参数缺失（uuid/encryuuid/encodeuuid）")

        image_remote_url = f"https://open.e.189.cn/api/logbox/oauth2/image.do?uuid={encodeuuid}&REQID={req_id}"
        state_payload = {
            "appId": app_id,
            "encryuuid": encryuuid,
            "date": str(int(time.time() * 1000)),
            "uuid": uuid_value,
            "returnUrl": str(app_conf_data.get("returnUrl") or ""),
            "clientType": str(app_conf_data.get("clientType") or "1"),
            "timeStamp": str(int(time.time() * 1000)),
            "cb_SaveName": str(app_conf_data.get("defaultSaveName") or ""),
            "isOauth2": "false" if str(app_conf_data.get("isOauth2")).lower() == "false" else "true",
            "state": str(app_conf_data.get("state") or ""),
            "paramId": str(app_conf_data.get("paramId") or ""),
        }

        return {
            "app_id": app_id,
            "lt": lt,
            "req_id": req_id,
            "login_page_url": login_page_url,
            "image_remote_url": image_remote_url,
            "state_payload": state_payload,
        }

    async def _finalize_qr_login_success(
        self,
        *,
        context: Dict[str, Any],
        redirect_url: str,
    ) -> Tuple[str, str, str]:
        """扫码成功后拉起回调并验证账号。"""
        client = context.get("client")
        if not isinstance(client, aiohttp.ClientSession):
            return "", "", "qr_client_invalid"

        req_id = str(context.get("req_id", ""))
        lt = str(context.get("lt", ""))
        login_page_url = str(context.get("login_page_url", ""))
        headers = self._build_qr_headers(req_id=req_id, lt=lt, referer=login_page_url)
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"

        candidate_urls: List[str] = []
        redirect = str(redirect_url or "").strip()
        if redirect:
            candidate_urls.append(redirect)
        candidate_urls.append("https://cloud.189.cn/web/main/")

        for url in candidate_urls:
            try:
                async with client.get(url, headers=headers, allow_redirects=True) as resp:
                    await resp.read()
            except Exception:
                continue

        cloud_scoped_count = 0
        open_scoped_count = 0
        try:
            cloud_scoped_count = len(client.cookie_jar.filter_cookies(URL("https://cloud.189.cn/")).items())
        except Exception:
            cloud_scoped_count = 0
        try:
            open_scoped_count = len(client.cookie_jar.filter_cookies(URL("https://open.e.189.cn/")).items())
        except Exception:
            open_scoped_count = 0

        cookie = self._build_tianyi_cookie_from_cookie_jar(client.cookie_jar)
        if not cookie:
            return "", "", f"cookie_missing:cloud={cloud_scoped_count},open={open_scoped_count}"

        account, verify_reason = await self._verify_cookie_candidate(cookie)
        if not account:
            scoped = f"cloud={cloud_scoped_count},open={open_scoped_count}"
            return "", cookie, f"{verify_reason or 'account_verify_failed'}:{scoped}"
        return account, cookie, ""

    async def _set_capture_state(
        self,
        *,
        stage: str,
        message: str,
        reason: str,
        next_action: str,
        user_account: str,
        diagnostics: Optional[Dict[str, Any]],
        source_attempts: Optional[List[str]] = None,
        success_source: str = "",
        source_diagnostics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """更新自动采集状态。"""
        attempts = [str(item) for item in (source_attempts or []) if str(item).strip()]
        source_diag = dict(source_diagnostics or {})
        self._capture_state = {
            "stage": str(stage or "idle"),
            "message": str(message or ""),
            "reason": str(reason or ""),
            "next_action": str(next_action or ""),
            "user_account": str(user_account or ""),
            "updated_at": _now_wall_ts(),
            "diagnostics": diagnostics or {},
            "source_attempts": attempts,
            "success_source": str(success_source or ""),
            "source_diagnostics": source_diag,
        }

    def _normalize_capture_host(self, host: str) -> str:
        """归一化采集探测中的 host，便于识别互跳。"""
        raw = str(host or "").strip().lower()
        if not raw:
            return ""
        if raw.endswith(".h5.cloud.189.cn") or raw == "h5.cloud.189.cn":
            return "h5.cloud.189.cn"
        if raw.endswith(".cloud.189.cn") or raw == "cloud.189.cn":
            return "cloud.189.cn"
        return raw

    def _extract_probe_hosts(self, probe: Dict[str, Any]) -> List[str]:
        """从探针结果提取 host 列表。"""
        hosts: List[str] = []
        pages = probe.get("page_candidates")
        if isinstance(pages, list):
            for item in pages:
                if not isinstance(item, dict):
                    continue
                host = self._normalize_capture_host(item.get("host", ""))
                if host and host not in hosts:
                    hosts.append(host)
        matched = probe.get("matched_page")
        if isinstance(matched, dict):
            host = self._normalize_capture_host(matched.get("host", ""))
            if host and host not in hosts:
                hosts.insert(0, host)
        return hosts

    def _is_capture_redirect_loop(self, host_history: List[str]) -> bool:
        """判断是否命中 cloud/h5 互跳。"""
        if len(host_history) < CAPTURE_LOOP_WINDOW:
            return False

        tail = host_history[-CAPTURE_LOOP_WINDOW:]
        if any(host not in CAPTURE_LOOP_CORE_HOSTS for host in tail):
            return False
        if len(set(tail)) != 2:
            return False
        for idx in range(1, len(tail)):
            if tail[idx] == tail[idx - 1]:
                return False
        return True

    def _build_capture_diag_payload(
        self,
        *,
        reason: str,
        source_diagnostics: Dict[str, Any],
        main_landing_detected: bool,
        host_history: Optional[List[str]] = None,
        elapsed_seconds: Optional[int] = None,
        remaining_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """构建统一诊断结构，便于前端展示。"""
        payload: Dict[str, Any] = {
            "reason": str(reason or ""),
            "main_landing_detected": bool(main_landing_detected),
            "source_diagnostics": dict(source_diagnostics or {}),
        }
        if host_history:
            payload["host_history"] = list(host_history)
        if elapsed_seconds is not None:
            payload["elapsed_seconds"] = int(elapsed_seconds)
        if remaining_seconds is not None:
            payload["remaining_seconds"] = int(remaining_seconds)
        return payload

    async def _verify_cookie_candidate(self, cookie: str) -> Tuple[str, str]:
        """校验候选 Cookie，返回账号与失败原因。"""
        normalized = str(cookie or "").strip()
        if not normalized:
            return "", "empty_cookie"
        try:
            account = await get_user_account(normalized)
        except Exception as exc:
            return "", f"account_verify_exception:{exc}"
        if not account:
            return "", "account_verify_failed"
        return account, ""

    def _derive_capture_failure_reason(
        self,
        source_diagnostics: Dict[str, Any],
        *,
        main_landing_detected: bool,
    ) -> str:
        """根据来源级探测信息生成失败原因。"""
        if main_landing_detected:
            return "main_landing_verify_failed"

        cdp_reason = str((source_diagnostics.get("cdp") or {}).get("reason", "")).strip()
        cookie_db_reason = str((source_diagnostics.get("cookie_db") or {}).get("reason", "")).strip()

        cdp_unavailable_reasons = {"cdp_endpoints_unreachable", "cdp_no_pages", "cdp_probe_exception"}
        cookie_db_unavailable_reasons = {"cookie_db_not_found", "cookie_db_read_failed", "cookie_db_probe_exception"}

        if cdp_reason in cdp_unavailable_reasons and cookie_db_reason in cookie_db_unavailable_reasons:
            return "all_sources_unavailable"
        if cdp_reason in cdp_unavailable_reasons and not cookie_db_reason:
            return "cdp_unavailable"
        if cookie_db_reason in cookie_db_unavailable_reasons and not cdp_reason:
            return "cookie_db_unavailable"
        return "no_valid_cookie"

    async def _attempt_capture_sources_once(self) -> Dict[str, Any]:
        """执行一次双来源采集并做统一账号校验。"""
        source_attempts: List[str] = []
        source_diagnostics: Dict[str, Any] = {}
        main_landing_detected = False

        for source in COOKIE_CAPTURE_SOURCES:
            source_attempts.append(source)
            try:
                if source == "cdp":
                    cookie, diag = await self._collect_tianyi_cookie_from_cdp()
                    if bool((diag or {}).get("main_landing_detected")):
                        main_landing_detected = True
                else:
                    cookie, diag = await self._collect_tianyi_cookie_from_cookie_db()
            except Exception as exc:
                cookie = ""
                diag = {
                    "ok": False,
                    "reason": f"{source}_probe_exception",
                    "error": str(exc),
                }

            source_diag = dict(diag or {})
            source_diagnostics[source] = source_diag

            if not cookie:
                continue

            source_diag["cookie_found"] = True
            account, verify_reason = await self._verify_cookie_candidate(cookie)
            source_diag["verify_reason"] = verify_reason
            if account:
                source_diag["ok"] = True
                source_diag["reason"] = ""
                return {
                    "success": True,
                    "cookie": cookie,
                    "account": account,
                    "reason": "",
                    "success_source": source,
                    "source_attempts": source_attempts,
                    "source_diagnostics": source_diagnostics,
                    "main_landing_detected": main_landing_detected,
                }
            if not str(source_diag.get("reason", "")).strip():
                source_diag["reason"] = "account_verify_failed"

        return {
            "success": False,
            "cookie": "",
            "account": "",
            "reason": self._derive_capture_failure_reason(
                source_diagnostics,
                main_landing_detected=main_landing_detected,
            ),
            "success_source": "",
            "source_attempts": source_attempts,
            "source_diagnostics": source_diagnostics,
            "main_landing_detected": main_landing_detected,
        }

    async def _capture_loop(
        self,
        timeout_seconds: int,
        seed_diagnostics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """后台采集循环。"""
        diagnostics: Dict[str, Any] = {"timeout_seconds": int(timeout_seconds)}
        if isinstance(seed_diagnostics, dict):
            diagnostics["entry_seed"] = seed_diagnostics
        await self._set_capture_state(
            stage="running",
            message="请在网页中完成天翼登录，系统将自动采集登录态...",
            reason="",
            next_action="",
            user_account="",
            diagnostics=diagnostics,
        )

        deadline = time.monotonic() + float(timeout_seconds)
        last_source_diagnostics: Dict[str, Any] = {}
        last_source_attempts: List[str] = []
        last_reason = ""
        host_history: List[str] = []
        main_landing_seen = False

        try:
            while time.monotonic() < deadline:
                attempt = await self._attempt_capture_sources_once()
                last_reason = str(attempt.get("reason", "") or "")
                last_source_attempts = list(attempt.get("source_attempts") or [])
                last_source_diagnostics = dict(attempt.get("source_diagnostics") or {})
                main_landing_seen = bool(main_landing_seen or attempt.get("main_landing_detected"))

                cdp_probe = dict((last_source_diagnostics.get("cdp") or {}))
                probe_hosts = self._extract_probe_hosts(cdp_probe)
                if probe_hosts:
                    host_history.append(probe_hosts[0])
                    if len(host_history) > CAPTURE_LOOP_WINDOW + 4:
                        host_history = host_history[-(CAPTURE_LOOP_WINDOW + 4):]

                if self._is_capture_redirect_loop(host_history):
                    reason = "redirect_loop_detected"
                    loop_diag = self._build_capture_diag_payload(
                        reason=reason,
                        source_diagnostics=last_source_diagnostics,
                        main_landing_detected=main_landing_seen,
                        host_history=host_history[-CAPTURE_LOOP_WINDOW:],
                    )
                    await self._set_capture_state(
                        stage="failed",
                        message="检测到 cloud.189.cn 与 h5.cloud.189.cn 持续互跳",
                        reason=reason,
                        next_action="manual_cookie",
                        user_account="",
                        diagnostics=loop_diag,
                        source_attempts=last_source_attempts,
                        success_source="",
                        source_diagnostics=last_source_diagnostics,
                    )
                    return

                if bool(attempt.get("success")):
                    resolved_cookie = str(attempt.get("cookie", "") or "")
                    resolved_account = str(attempt.get("account", "") or "")
                    success_source = str(attempt.get("success_source", "") or "")
                    if resolved_cookie and resolved_account:
                        self.store.set_login(resolved_cookie, resolved_account)
                        done_diag = self._build_capture_diag_payload(
                            reason="",
                            source_diagnostics=last_source_diagnostics,
                            main_landing_detected=main_landing_seen,
                            host_history=host_history[-CAPTURE_LOOP_WINDOW:] if host_history else None,
                        )
                        await self._set_capture_state(
                            stage="completed",
                            message=f"登录成功：{resolved_account}",
                            reason="",
                            next_action="",
                            user_account=resolved_account,
                            diagnostics=done_diag,
                            source_attempts=last_source_attempts,
                            success_source=success_source,
                            source_diagnostics=last_source_diagnostics,
                        )
                        return

                elapsed = int(max(0.0, float(timeout_seconds) - max(0.0, deadline - time.monotonic())))
                remaining = int(max(0.0, deadline - time.monotonic()))
                running_diag = self._build_capture_diag_payload(
                    reason=last_reason,
                    source_diagnostics=last_source_diagnostics,
                    main_landing_detected=main_landing_seen,
                    host_history=host_history[-CAPTURE_LOOP_WINDOW:] if host_history else None,
                    elapsed_seconds=elapsed,
                    remaining_seconds=remaining,
                )
                running_message = "等待登录完成并同步登录态..."
                if last_reason == "main_landing_verify_failed":
                    running_message = "检测到已到达主站，正在持续校验账号登录态..."
                await self._set_capture_state(
                    stage="running",
                    message=running_message,
                    reason=last_reason,
                    next_action="",
                    user_account="",
                    diagnostics=running_diag,
                    source_attempts=last_source_attempts,
                    success_source="",
                    source_diagnostics=last_source_diagnostics,
                )
                await asyncio.sleep(1.8)

            timeout_reason = "capture_timeout"
            timeout_message = "自动采集超时，请改用手动 Cookie"
            if main_landing_seen or last_reason == "main_landing_verify_failed":
                timeout_reason = "main_landing_verify_failed"
                timeout_message = "检测到已跳转主站，但账号校验未通过，请重试登录或改用手动 Cookie"
            timeout_diag = self._build_capture_diag_payload(
                reason=timeout_reason,
                source_diagnostics=last_source_diagnostics,
                main_landing_detected=main_landing_seen,
                host_history=host_history[-CAPTURE_LOOP_WINDOW:] if host_history else None,
            )
            await self._set_capture_state(
                stage="failed",
                message=timeout_message,
                reason=timeout_reason,
                next_action="manual_cookie",
                user_account="",
                diagnostics=timeout_diag,
                source_attempts=last_source_attempts,
                success_source="",
                source_diagnostics=last_source_diagnostics,
            )
        except asyncio.CancelledError:
            stopped_diag = self._build_capture_diag_payload(
                reason="capture_stopped",
                source_diagnostics=last_source_diagnostics,
                main_landing_detected=main_landing_seen,
                host_history=host_history[-CAPTURE_LOOP_WINDOW:] if host_history else None,
            )
            await self._set_capture_state(
                stage="stopped",
                message="采集已停止，可改用手动 Cookie",
                reason="capture_stopped",
                next_action="manual_cookie",
                user_account="",
                diagnostics=stopped_diag,
                source_attempts=last_source_attempts,
                success_source="",
                source_diagnostics=last_source_diagnostics,
            )
            raise
        except Exception as exc:
            error_diag = self._build_capture_diag_payload(
                reason="capture_exception",
                source_diagnostics=last_source_diagnostics,
                main_landing_detected=main_landing_seen,
                host_history=host_history[-CAPTURE_LOOP_WINDOW:] if host_history else None,
            )
            error_diag["exception"] = str(exc)
            await self._set_capture_state(
                stage="failed",
                message=f"自动采集异常：{exc}",
                reason="capture_exception",
                next_action="manual_cookie",
                user_account="",
                diagnostics=error_diag,
                source_attempts=last_source_attempts,
                success_source="",
                source_diagnostics=last_source_diagnostics,
            )

    async def _collect_tianyi_cookie_from_cdp(self) -> tuple[str, Dict[str, Any]]:
        """从 CEF DevTools 端点尝试提取天翼 cookie。"""
        diagnostics: Dict[str, Any] = {
            "source": "cdp",
            "candidate_ports": list(CDP_ENDPOINT_PORTS),
            "probe_results": [],
            "page_candidates": [],
            "main_landing_detected": False,
            "ok": False,
            "reason": "",
        }
        pages: List[Dict[str, Any]] = []

        timeout = aiohttp.ClientTimeout(total=LOCAL_WEB_PROBE_TIMEOUT_SECONDS)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for port in CDP_ENDPOINT_PORTS:
                url = f"http://127.0.0.1:{port}/json"
                probe_item: Dict[str, Any] = {"port": port, "url": url, "ok": False}
                try:
                    async with session.get(url) as resp:
                        probe_item["status"] = int(resp.status)
                        text = await resp.text()
                        if 200 <= resp.status < 300:
                            payload = json.loads(text)
                            if isinstance(payload, list):
                                for item in payload:
                                    if isinstance(item, dict):
                                        item["_cdp_port"] = port
                                        pages.append(item)
                                probe_item["ok"] = True
                                probe_item["page_count"] = len(payload)
                            else:
                                probe_item["error"] = "cdp_json_not_list"
                        else:
                            probe_item["error"] = "http_status_not_ok"
                except Exception as exc:
                    probe_item["error"] = str(exc)
                diagnostics["probe_results"].append(probe_item)

        if not pages:
            probe_results = diagnostics.get("probe_results", [])
            if isinstance(probe_results, list) and probe_results and all(not bool(item.get("ok")) for item in probe_results if isinstance(item, dict)):
                diagnostics["reason"] = "cdp_endpoints_unreachable"
            else:
                diagnostics["reason"] = "cdp_no_pages"
            return "", diagnostics

        preferred_pages: List[Dict[str, Any]] = []
        fallback_pages: List[Dict[str, Any]] = []
        all_hosts: List[str] = []
        for page in pages:
            page_url = str(page.get("url", "") or "")
            ws_url = str(page.get("webSocketDebuggerUrl", "") or "")
            if not ws_url:
                continue

            host = ""
            try:
                host = str(urlparse(page_url).hostname or "").lower()
            except Exception:
                host = ""
            if host and host not in all_hosts:
                all_hosts.append(host)
            if page_url.startswith("https://cloud.189.cn/web/main/") or page_url.startswith("http://cloud.189.cn/web/main/"):
                diagnostics["main_landing_detected"] = True
            entry = {
                "title": str(page.get("title", "") or ""),
                "url": page_url,
                "host": host,
                "ws_url": ws_url,
                "port": int(page.get("_cdp_port") or 0),
            }
            if host and any(key in host for key in TIANYI_HOST_KEYWORDS):
                preferred_pages.append(entry)
            else:
                fallback_pages.append(entry)

        diagnostics["page_candidates"] = preferred_pages[:6]
        diagnostics["all_hosts"] = all_hosts[:12]
        selected_pages = preferred_pages + fallback_pages[:3]

        for page in selected_pages:
            ws_url = str(page.get("ws_url", "") or "")
            try:
                cookies = await self._get_all_cookies_from_ws(ws_url)
                cookie_str = self._build_tianyi_cookie_string(cookies)
                if cookie_str:
                    diagnostics["matched_page"] = {
                        "host": page.get("host", ""),
                        "url": page.get("url", ""),
                        "port": page.get("port", 0),
                    }
                    diagnostics["ok"] = True
                    diagnostics["reason"] = ""
                    return cookie_str, diagnostics
            except Exception as exc:
                diagnostics.setdefault("ws_errors", []).append(
                    {
                        "port": page.get("port", 0),
                        "url": page.get("url", ""),
                        "error": str(exc),
                    }
                )

        diagnostics["reason"] = "cdp_no_tianyi_cookie"
        return "", diagnostics

    def _cookie_db_candidate_paths(self) -> List[str]:
        """生成 CookieDB 候选路径列表。"""
        home_dir = str(Path.home())
        raw_paths = [
            os.path.join(home_dir, ".local", "share", "Steam", "config", "htmlcache", "Cookies"),
            os.path.join(home_dir, ".steam", "steam", "config", "htmlcache", "Cookies"),
            os.path.join(home_dir, ".steam", "root", "config", "htmlcache", "Cookies"),
            os.path.join(home_dir, ".steam", "steam", "config", "htmlcache", "Default", "Cookies"),
            os.path.join(home_dir, ".config", "chromium", "Default", "Cookies"),
            os.path.join(
                home_dir,
                ".var",
                "app",
                "com.valvesoftware.Steam",
                ".local",
                "share",
                "Steam",
                "config",
                "htmlcache",
                "Cookies",
            ),
        ]
        dedup: List[str] = []
        seen = set()
        for item in raw_paths:
            path = os.path.realpath(os.path.expanduser(item))
            if path in seen:
                continue
            seen.add(path)
            dedup.append(path)
        return dedup

    def _read_cookie_db_rows(self, db_path: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """从 CookieDB 快照读取天翼域行。"""
        diagnostics: Dict[str, Any] = {"db_path": db_path, "snapshot_path": "", "row_count": 0}
        temp_path = ""
        conn: Optional[sqlite3.Connection] = None
        try:
            with tempfile.NamedTemporaryFile(prefix="freedeckcy_cookie_", suffix=".db", delete=False) as temp_file:
                temp_path = temp_file.name
            diagnostics["snapshot_path"] = temp_path

            shutil.copy2(db_path, temp_path)

            conn = sqlite3.connect(f"file:{temp_path}?mode=ro", uri=True)
            cursor = conn.execute("PRAGMA table_info(cookies)")
            columns = [str(row[1]) for row in cursor.fetchall()]
            diagnostics["columns"] = columns
            if "host_key" not in columns or "name" not in columns:
                diagnostics["reason"] = "cookie_db_schema_invalid"
                return [], diagnostics

            select_cols = ["host_key", "name"]
            if "value" in columns:
                select_cols.append("value")
            if "encrypted_value" in columns:
                select_cols.append("encrypted_value")
            order_col = "last_access_utc" if "last_access_utc" in columns else "rowid"

            sql = (
                f"SELECT {', '.join(select_cols)} "
                f"FROM cookies "
                f"WHERE host_key LIKE ? "
                f"ORDER BY {order_col} DESC "
                f"LIMIT {COOKIE_DB_MAX_ROWS}"
            )
            rows_raw = conn.execute(sql, ("%189.cn%",)).fetchall()
            rows: List[Dict[str, Any]] = []
            for raw in rows_raw:
                item: Dict[str, Any] = {}
                for idx, col_name in enumerate(select_cols):
                    item[col_name] = raw[idx]
                rows.append(item)
            diagnostics["row_count"] = len(rows)
            diagnostics["reason"] = ""
            return rows, diagnostics
        except Exception as exc:
            diagnostics["reason"] = "cookie_db_read_failed"
            diagnostics["error"] = str(exc)
            return [], diagnostics
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            if temp_path:
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    async def _collect_tianyi_cookie_from_cookie_db(self) -> tuple[str, Dict[str, Any]]:
        """从本地 CookieDB 尝试提取天翼 Cookie。"""
        candidate_paths = self._cookie_db_candidate_paths()
        diagnostics: Dict[str, Any] = {
            "source": "cookie_db",
            "candidate_paths": candidate_paths,
            "probe_results": [],
            "ok": False,
            "reason": "",
        }

        any_existing = False
        any_read_failed = False
        for path in candidate_paths:
            probe_item: Dict[str, Any] = {"path": path, "exists": False}
            if not os.path.isfile(path):
                diagnostics["probe_results"].append(probe_item)
                continue

            any_existing = True
            probe_item["exists"] = True
            rows, row_diag = await asyncio.to_thread(self._read_cookie_db_rows, path)
            probe_item.update(row_diag)
            if str(row_diag.get("reason", "")).strip():
                any_read_failed = True
                diagnostics["probe_results"].append(probe_item)
                continue

            kv_map: Dict[str, str] = {}
            encrypted_only_count = 0
            for row in rows:
                name = str(row.get("name", "") or "").strip()
                if not name:
                    continue

                raw_value = row.get("value", "")
                value = str(raw_value or "").strip()
                if not value:
                    encrypted_value = row.get("encrypted_value", b"")
                    if isinstance(encrypted_value, memoryview):
                        encrypted_value = encrypted_value.tobytes()
                    if isinstance(encrypted_value, (bytes, bytearray)) and encrypted_value:
                        blob = bytes(encrypted_value)
                        if blob.startswith(b"v10") or blob.startswith(b"v11"):
                            encrypted_only_count += 1
                            continue
                        try:
                            decoded = blob.decode("utf-8", errors="ignore").strip()
                        except Exception:
                            decoded = ""
                        if not decoded:
                            encrypted_only_count += 1
                            continue
                        value = decoded
                if not value:
                    continue
                if name not in kv_map:
                    kv_map[name] = value

            probe_item["cookie_name_count"] = len(kv_map)
            probe_item["encrypted_only_count"] = encrypted_only_count
            diagnostics["probe_results"].append(probe_item)

            if kv_map:
                diagnostics["ok"] = True
                diagnostics["reason"] = ""
                diagnostics["selected_path"] = path
                diagnostics["cookie_name_count"] = len(kv_map)
                ordered = [f"{k}={v}" for k, v in sorted(kv_map.items(), key=lambda item: item[0].lower())]
                return "; ".join(ordered), diagnostics

        if not any_existing:
            diagnostics["reason"] = "cookie_db_not_found"
        elif any_read_failed:
            diagnostics["reason"] = "cookie_db_read_failed"
        else:
            diagnostics["reason"] = "cookie_db_no_tianyi_cookie"
        return "", diagnostics

    async def _get_all_cookies_from_ws(self, ws_url: str) -> List[Dict[str, Any]]:
        """通过 CDP WebSocket 获取所有 cookie。"""
        timeout = aiohttp.ClientTimeout(total=6.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.ws_connect(ws_url, autoping=True, heartbeat=10.0) as ws:
                request_id = 1

                async def cdp_call(method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
                    nonlocal request_id
                    current_id = request_id
                    request_id += 1
                    await ws.send_json({"id": current_id, "method": method, "params": params or {}})

                    while True:
                        msg = await ws.receive(timeout=5.0)
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            payload = json.loads(str(msg.data))
                            if int(payload.get("id", 0) or 0) != current_id:
                                continue
                            if "error" in payload:
                                raise RuntimeError(str(payload.get("error")))
                            return payload.get("result") or {}
                        if msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED):
                            raise RuntimeError("cdp websocket closed")
                        if msg.type == aiohttp.WSMsgType.ERROR:
                            raise RuntimeError("cdp websocket error")

                await cdp_call("Network.enable")
                result = await cdp_call("Network.getAllCookies")
                cookies = result.get("cookies")
                if isinstance(cookies, list):
                    return [item for item in cookies if isinstance(item, dict)]
                return []

    def _build_tianyi_cookie_string(self, cookies: List[Dict[str, Any]]) -> str:
        """从 cookies 中筛出天翼域并组装 Cookie 头。"""
        kv_map: Dict[str, str] = {}
        for item in cookies:
            domain = str(item.get("domain", "") or "").lower()
            if "189.cn" not in domain:
                continue
            name = str(item.get("name", "") or "").strip()
            value = str(item.get("value", "") or "").strip()
            if not name or not value:
                continue
            kv_map[name] = value

        if not kv_map:
            return ""

        ordered = [f"{k}={v}" for k, v in sorted(kv_map.items(), key=lambda x: x[0].lower())]
        return "; ".join(ordered)

    async def _ensure_local_web_ready(self, route_path: str) -> str:
        """确保本地网页服务与目标页面可访问。"""
        diagnostics: Dict[str, Any] = {
            "host_candidates": ["127.0.0.1"],
            "route": route_path,
            "probe_results": [],
        }

        status = await self.plugin.get_server_status()
        diagnostics["status_before"] = dict(status)
        if not bool(status.get("running")):
            start_result = await self.plugin.start_server(self.plugin.server_port)
            diagnostics["start_result"] = dict(start_result)
            if start_result.get("status") != "success":
                raise LocalWebNotReadyError(
                    str(start_result.get("message", "本地网页服务启动失败")),
                    reason="local_server_start_failed",
                    diagnostics=diagnostics,
                )
            status = await self.plugin.get_server_status()
            diagnostics["status_after"] = dict(status)

        if not bool(status.get("running")):
            raise LocalWebNotReadyError(
                "本地网页服务未就绪，请稍后再试",
                reason="local_server_not_running",
                diagnostics=diagnostics,
            )

        port = int(status.get("port") or self.plugin.server_port)
        diagnostics["port"] = port

        health_probe = await self._probe_local_route(port, "/_healthz")
        page_probe = await self._probe_local_route(port, route_path.split("?", 1)[0])
        diagnostics["probe_results"].append(health_probe)
        diagnostics["probe_results"].append(page_probe)

        if not health_probe.get("ok"):
            raise LocalWebNotReadyError(
                "本地网页基础探针未通过，请稍后再试",
                reason="health_probe_failed",
                diagnostics=diagnostics,
            )

        if not page_probe.get("ok"):
            raise LocalWebNotReadyError(
                "本地网页页面探针未通过，请稍后再试",
                reason="page_probe_failed",
                diagnostics=diagnostics,
            )

        return f"http://127.0.0.1:{port}{route_path}"

    async def _peek_local_web_url(self, route_path: str) -> str:
        """仅检查当前服务状态，不主动拉起服务。"""
        status = await self.plugin.get_server_status()
        if not bool(status.get("running")):
            return ""

        port = int(status.get("port") or self.plugin.server_port)
        probe = await self._probe_local_route(port, route_path.split("?", 1)[0])
        if not probe.get("ok"):
            return ""

        return f"http://127.0.0.1:{port}{route_path}"

    async def _probe_local_route(self, port: int, path: str) -> Dict[str, Any]:
        """探测本地路由是否可访问。"""
        url = f"http://127.0.0.1:{int(port)}{path}"
        result: Dict[str, Any] = {
            "url": url,
            "path": path,
            "ok": False,
        }

        timeout = aiohttp.ClientTimeout(total=LOCAL_WEB_READY_TIMEOUT_SECONDS)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, allow_redirects=False) as resp:
                    result["status"] = int(resp.status)
                    result["ok"] = 200 <= resp.status < 400
        except Exception as exc:
            result["error"] = str(exc)
        return result
