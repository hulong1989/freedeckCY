"""可移动存储（SD 卡）检测：给下载/安装目录提供一键选择。"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from typing import Any, Dict, List, Optional, Sequence, Tuple

_MOUNT_PREFIXES = (
    "/run/media/",
    "/media/",
    "/mnt/",
    "/storage/",
    "/sdcard",
)
_SKIP_FSTYPES = {
    "proc",
    "sysfs",
    "devtmpfs",
    "devpts",
    "tmpfs",
    "cgroup",
    "cgroup2",
    "pstore",
    "bpf",
    "debugfs",
    "tracefs",
    "securityfs",
    "configfs",
    "fusectl",
    "mqueue",
    "hugetlbfs",
    "overlay",
    "squashfs",
    "autofs",
    "ramfs",
    "binder",
    "binderfs",
    "functionfs",
    "nsfs",
}
_SKIP_MOUNTS = {"/", "/run", "/mnt", "/media", "/storage", "/sdcard"}
# Android 内部共享存储的别名（root/proot 下可写，但不是可移动 SD 卡）。
# /mnt/media_rw/<卷> 是 Android 物理 SD 的 root 视图，保留（与 /storage/<卷> 由身份去重合并）。
_INTERNAL_STORAGE_PREFIXES = (
    "/storage/emulated",
    "/storage/self",
    "/sdcard",
    "/mnt/user",
    "/mnt/runtime",
    "/mnt/pass_through",
    "/mnt/installer",
    "/mnt/androidwritable",
    "/mnt/obb",
    "/mnt/asec",
    "/mnt/expand",
)
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")


def _unescape_mount(value: str) -> str:
    return (
        str(value or "")
        .replace("\\040", " ")
        .replace("\\011", "\t")
        .replace("\\012", "\n")
        .replace("\\134", "\\")
    )


def _read_mounts() -> str:
    try:
        with open("/proc/mounts", "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except Exception:
        return ""


def _path_is_under(path: str, prefix: str) -> bool:
    """路径是否等于 prefix 或位于其下（按目录边界，避免 /storageX 误命中）。"""
    base = str(prefix or "").rstrip("/")
    value = str(path or "").rstrip("/")
    if not base or not value:
        return False
    return value == base or value.startswith(base + "/")


def _is_android_internal_storage(real: str) -> bool:
    return any(_path_is_under(real, prefix) for prefix in _INTERNAL_STORAGE_PREFIXES)


def _mount_identity(path: str) -> Optional[Tuple[int, int]]:
    """返回挂载点的 (dev, inode)：bind mount / 多层别名会指向同一目录。"""
    try:
        stat = os.stat(path)
        return int(stat.st_dev), int(stat.st_ino)
    except Exception:
        return None


def _sanitize_label(value: str) -> str:
    """卷标可能来自用户/U 盘，去掉控制字符避免 UI 注入或换行。"""
    return re.sub(r"\s+", " ", _CONTROL_CHARS_RE.sub(" ", str(value or ""))).strip()


def _probe_writable(path: str) -> bool:
    """实际创建临时文件验证可写（os.access 在 root/FUSE 下不可靠）。"""
    probe = ""
    try:
        fd, probe = tempfile.mkstemp(prefix=".freedeckcy-write-", dir=path)
        os.close(fd)
        os.remove(probe)
        return True
    except Exception:
        if probe:
            try:
                os.remove(probe)
            except Exception:
                pass
        return False


def _human_size(value: int) -> str:
    size = float(max(0, value))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def detect_storage_options(
    *,
    mounts_text: Optional[str] = None,
    home: Optional[str] = None,
    disk_usage=None,
) -> Dict[str, Any]:
    """返回内置存储 + 可写 SD/外置挂载选项。"""
    home_dir = os.path.realpath(os.path.expanduser(home or "~"))
    usage_func = disk_usage or shutil.disk_usage
    text = mounts_text if mounts_text is not None else _read_mounts()

    options: List[Dict[str, Any]] = []
    seen: set = set()
    seen_ids: set = set()
    for line in str(text or "").splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        mount = _unescape_mount(parts[1])
        if not mount.startswith("/") or _CONTROL_CHARS_RE.search(mount):
            # 挂载点必须是绝对路径且不含控制字符，否则拒绝拼进下载/安装目录。
            continue
        fstype = str(parts[2] or "").lower()
        mount_options = str(parts[3] or "").lower().split(",") if len(parts) > 3 else []
        if mount in _SKIP_MOUNTS or fstype in _SKIP_FSTYPES or "ro" in mount_options:
            continue
        if not any(mount == prefix.rstrip("/") or mount.startswith(prefix) for prefix in _MOUNT_PREFIXES):
            continue
        real = os.path.realpath(mount)
        if real in seen or real in _SKIP_MOUNTS:
            continue
        if _is_android_internal_storage(real):
            continue
        identity = _mount_identity(real)
        if identity is not None and identity in seen_ids:
            # bind mount/别名指向同一目录时只保留一个选项。
            continue
        if not os.path.isdir(real) or not _probe_writable(real):
            continue
        try:
            usage = usage_func(real)
            free_bytes = int(usage.free)
            total_bytes = int(usage.total)
        except Exception:
            continue
        if total_bytes <= 0:
            continue
        seen.add(real)
        if identity is not None:
            seen_ids.add(identity)
        label = _sanitize_label(os.path.basename(real.rstrip("/"))) or "外置存储"
        options.append(
            {
                "kind": "external",
                "label": f"SD 卡 / 外置：{label}",
                "mount": real,
                "download_dir": os.path.join(real, "freedeckCY", "downloads"),
                "install_dir": os.path.join(real, "freedeckCY", "installed"),
                "free_bytes": free_bytes,
                "total_bytes": total_bytes,
                "free_text": _human_size(free_bytes),
                "total_text": _human_size(total_bytes),
            }
        )

    options.sort(key=lambda item: str(item.get("label", "")).lower())
    try:
        internal_usage = usage_func(home_dir)
        internal_free = int(internal_usage.free)
        internal_total = int(internal_usage.total)
    except Exception:
        internal_free = 0
        internal_total = 0
    internal = {
        "kind": "internal",
        "label": "内置存储",
        "mount": home_dir,
        "download_dir": os.path.join(home_dir, "Downloads", "freedeckCY"),
        "install_dir": os.path.join(home_dir, "Games", "freedeckCY"),
        "free_bytes": internal_free,
        "total_bytes": internal_total,
        "free_text": _human_size(internal_free),
        "total_text": _human_size(internal_total),
    }
    return {"internal": internal, "external": options, "options": [internal, *options]}
