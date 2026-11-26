"""扫描并安全清理下载/安装残留。

只处理插件自己产生的、可重新获取的临时文件：
- 已下载的插件更新包（freedeckCY-v*.zip / .sha256）
- 隔离出来的坏文件 / 不支持续传的半成品（*.freedeckcy-<reason>-<ts>）
- 历史云存档备份（只统计，不默认删除）

所有删除路径都必须落在调用方给的已知根目录内，且拒绝符号链接。
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Iterable, List, Sequence

# 插件自己产生的隔离文件命名标记（见 tianyi_service._quarantine_download_file）。
QUARANTINE_MARKERS = (
    ".freedeckcy-size-mismatch-",
    ".freedeckcy-archive-invalid-",
    ".freedeckcy-noresume-",
    ".freedeckcy-stale-",
    ".freedeckcy-bad-",
)
UPDATE_FILE_PREFIX = "freedeckCY-v"
MAX_GROUP_ITEMS = 200
MAX_SCAN_ENTRIES = 30000
MAX_SCAN_DEPTH = 4


def _real(path: str) -> str:
    return os.path.realpath(os.path.expanduser(str(path or "").strip()))


def _is_within(path: str, root: str) -> bool:
    if not path or not root:
        return False
    try:
        return os.path.commonpath([os.path.realpath(path), os.path.realpath(root)]) == os.path.realpath(root)
    except (OSError, ValueError):
        return False


def _display_path(path: str) -> str:
    home = os.path.expanduser("~")
    text = str(path or "")
    if home and text.startswith(home):
        return "~" + text[len(home):]
    return text


def _file_size(path: str) -> int:
    try:
        return max(0, int(os.path.getsize(path)))
    except OSError:
        return 0


def _mtime(path: str) -> int:
    try:
        return max(0, int(os.path.getmtime(path)))
    except OSError:
        return 0


def _scan_marked_files(root: str, markers: Sequence[str]) -> List[Dict[str, Any]]:
    """在 root 下有深度/数量上限地查找隔离文件，不跟随符号链接。"""
    base = _real(root)
    if not base or not os.path.isdir(base):
        return []
    found: List[Dict[str, Any]] = []
    seen_entries = 0
    for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
        depth = dirpath[len(base):].count(os.sep)
        if depth >= MAX_SCAN_DEPTH:
            dirnames[:] = []
        dirnames[:] = [name for name in dirnames if not os.path.islink(os.path.join(dirpath, name))]
        for name in filenames:
            seen_entries += 1
            if seen_entries > MAX_SCAN_ENTRIES:
                return found
            if not any(marker in name for marker in markers):
                continue
            path = os.path.join(dirpath, name)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            found.append({
                "path": path,
                "display_path": _display_path(path),
                "size": _file_size(path),
                "mtime": _mtime(path),
                "root": base,
            })
    return found


def _scan_update_packages(update_dir: str) -> List[Dict[str, Any]]:
    base = _real(update_dir)
    if not base or not os.path.isdir(base):
        return []
    found: List[Dict[str, Any]] = []
    try:
        entries = list(os.scandir(base))
    except OSError:
        return []
    for entry in entries:
        name = entry.name
        if not (name.startswith(UPDATE_FILE_PREFIX) and (name.endswith(".zip") or name.endswith(".zip.sha256"))):
            continue
        try:
            if not entry.is_file(follow_symlinks=False):
                continue
        except OSError:
            continue
        path = entry.path
        found.append({
            "path": path,
            "display_path": _display_path(path),
            "size": _file_size(path),
            "mtime": _mtime(path),
            "root": base,
        })
    return found


def _scan_legacy_backups(backup_dir: str) -> List[Dict[str, Any]]:
    base = _real(backup_dir)
    if not base or not os.path.isdir(base):
        return []
    found: List[Dict[str, Any]] = []
    for name in sorted(os.listdir(base))[:MAX_GROUP_ITEMS]:
        path = os.path.join(base, name)
        if os.path.islink(path):
            continue
        size = 0
        try:
            if os.path.isdir(path):
                for dirpath, _dirnames, filenames in os.walk(path, followlinks=False):
                    for filename in filenames:
                        size += _file_size(os.path.join(dirpath, filename))
            elif os.path.isfile(path):
                size = _file_size(path)
            else:
                continue
        except OSError:
            continue
        found.append({
            "path": path,
            "display_path": _display_path(path),
            "size": size,
            "mtime": _mtime(path),
            "root": base,
        })
    return found


def _group(group_id: str, label: str, description: str, items: List[Dict[str, Any]], *, safe: bool) -> Dict[str, Any]:
    items = sorted(items, key=lambda item: (-int(item.get("mtime") or 0), str(item.get("path") or "")))
    total = sum(max(0, int(item.get("size") or 0)) for item in items)
    trimmed = items[:MAX_GROUP_ITEMS]
    return {
        "id": group_id,
        "label": label,
        "description": description,
        "safe": bool(safe),
        "count": len(items),
        "bytes": total,
        "items": trimmed,
        "truncated": len(items) > len(trimmed),
    }


def scan_storage_cleanup(
    *,
    download_dir: str,
    install_dir: str,
    update_dir: str,
    backup_dir: str,
) -> Dict[str, Any]:
    """返回按类别聚合的可清理项。"""
    download = _real(download_dir)
    install = _real(install_dir)
    quarantine: List[Dict[str, Any]] = []
    for root in (download, install):
        for item in _scan_marked_files(root, QUARANTINE_MARKERS):
            if all(existing["path"] != item["path"] for existing in quarantine):
                quarantine.append(item)
    groups = [
        _group(
            "update_packages",
            "插件更新包",
            "已下载的 freedeckCY 安装包；安装完成或不需要回滚时可删除，之后可重新下载。",
            _scan_update_packages(update_dir),
            safe=True,
        ),
        _group(
            "quarantine",
            "隔离的坏文件 / 半成品",
            "下载校验失败、归档损坏或不支持续传时被隔离的文件；插件不会再使用。",
            quarantine,
            safe=True,
        ),
        _group(
            "legacy_backups",
            "历史云存档备份",
            "旧版本迁移到中央目录的存档备份；可能用于手动找回，默认不删除。",
            _scan_legacy_backups(backup_dir),
            safe=False,
        ),
    ]
    safe_bytes = sum(int(group["bytes"]) for group in groups if group.get("safe"))
    safe_count = sum(int(group["count"]) for group in groups if group.get("safe"))
    return {
        "ok": True,
        "roots": {
            "download_dir": _display_path(download),
            "install_dir": _display_path(install),
            "update_dir": _display_path(_real(update_dir)),
            "backup_dir": _display_path(_real(backup_dir)),
        },
        "groups": groups,
        "safe_bytes": safe_bytes,
        "safe_count": safe_count,
        "total_bytes": sum(int(group["bytes"]) for group in groups),
        "generated_at": int(time.time()),
    }


def clean_storage_cleanup(
    *,
    categories: Iterable[str],
    download_dir: str,
    install_dir: str,
    update_dir: str,
    backup_dir: str,
) -> Dict[str, Any]:
    """只删除 safe 类别；每个路径都重新校验根目录边界。"""
    requested = {str(item or "").strip() for item in categories if str(item or "").strip()}
    scan = scan_storage_cleanup(
        download_dir=download_dir,
        install_dir=install_dir,
        update_dir=update_dir,
        backup_dir=backup_dir,
    )
    roots = {
        "update_packages": _real(update_dir),
        "quarantine": [_real(download_dir), _real(install_dir)],
        "legacy_backups": _real(backup_dir),
    }
    deleted_files = 0
    freed_bytes = 0
    errors: List[Dict[str, str]] = []
    for group in list(scan.get("groups") or []):
        group_id = str(group.get("id") or "")
        if group_id not in requested or not group.get("safe"):
            continue
        allowed_roots = roots.get(group_id) or []
        if isinstance(allowed_roots, str):
            allowed_roots = [allowed_roots]
        for item in list(group.get("items") or []):
            path = str(item.get("path") or "")
            if not path or os.path.islink(path):
                continue
            if not any(_is_within(path, root) for root in allowed_roots):
                errors.append({"path": _display_path(path), "message": "路径不在允许范围内，已跳过"})
                continue
            size = _file_size(path)
            try:
                os.unlink(path)
                deleted_files += 1
                freed_bytes += size
            except OSError as exc:
                errors.append({"path": _display_path(path), "message": str(exc)})
    return {
        "ok": True,
        "deleted_files": deleted_files,
        "freed_bytes": freed_bytes,
        "errors": errors,
        "categories": sorted(requested),
    }
