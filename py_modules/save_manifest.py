"""Ludusavi 存档清单匹配与 Proton 路径解析。

清单来源：mtkennerly/ludusavi-manifest（MIT），由
`scripts/fetch_ludusavi_manifest.py` 转换为 JSON 后随包分发。
运行时只读本地 JSON，不联网。
"""

from __future__ import annotations

import glob
import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import config

_DEFAULT_RELATIVE = os.path.join("defaults", "ludusavi", "manifest.json.gz")
_MANIFEST_LOCK = threading.Lock()
_MANIFEST_PATH = ""
_MANIFEST_DATA: Optional[Dict[str, Any]] = None
_TITLE_INDEX: Dict[str, str] = {}
_STEAM_INDEX: Dict[int, str] = {}
_MAX_PATHS = 200

_CJK_ALNUM = re.compile(r"[^0-9a-z\u3400-\u9fff]+")


def normalize_title(value: str) -> str:
    return _CJK_ALNUM.sub("", str(value or "").lower())


def manifest_path(plugin_dir: str = "") -> str:
    env_path = str(os.getenv("FREEDECKCY_LUDUSAVI_MANIFEST", "") or "").strip()
    if env_path:
        try:
            return str(Path(env_path).expanduser().resolve())
        except Exception:
            return env_path
    root = str(plugin_dir or "").strip()
    if not root:
        root = str(os.getenv("DECKY_PLUGIN_DIR", "") or "").strip()
    if not root:
        root = str(Path(__file__).resolve().parent.parent)
    return str(Path(root) / _DEFAULT_RELATIVE)


def load_manifest(plugin_dir: str = "") -> Dict[str, Any]:
    """加载清单并构建标题/SteamID 索引（进程内缓存）。"""
    global _MANIFEST_PATH, _MANIFEST_DATA, _TITLE_INDEX, _STEAM_INDEX
    path = manifest_path(plugin_dir)
    with _MANIFEST_LOCK:
        if _MANIFEST_DATA is not None and _MANIFEST_PATH == path:
            return _MANIFEST_DATA
        data: Dict[str, Any] = {}
        try:
            if str(path).lower().endswith(".gz"):
                import gzip

                with gzip.open(path, "rt", encoding="utf-8") as fh:
                    raw = json.load(fh)
            else:
                with open(path, "r", encoding="utf-8") as fh:
                    raw = json.load(fh)
            if isinstance(raw, dict):
                data = raw
        except Exception as exc:
            config.logger.warning("Ludusavi 清单加载失败 %s: %s", path, exc)
            data = {}

        title_index: Dict[str, str] = {}
        steam_index: Dict[int, str] = {}
        for name, info in data.items():
            key = normalize_title(str(name))
            if key:
                title_index.setdefault(key, str(name))
            if isinstance(info, dict):
                steam = info.get("steam")
                if isinstance(steam, dict):
                    try:
                        sid = int(steam.get("id", 0) or 0)
                    except Exception:
                        sid = 0
                    if sid > 0:
                        steam_index.setdefault(sid, str(name))

        _MANIFEST_PATH = path
        _MANIFEST_DATA = data
        _TITLE_INDEX = title_index
        _STEAM_INDEX = steam_index
        if data:
            config.logger.info("Ludusavi 清单已加载: %s 款游戏 (%s)", len(data), path)
        return data


def match_manifest(
    data: Dict[str, Any],
    *,
    titles: Sequence[str] = (),
    app_id: int = 0,
) -> Tuple[str, Dict[str, Any]]:
    """按 Steam ID / 标题匹配清单条目，返回 (manifest_key, info)。"""
    if not isinstance(data, dict) or not data:
        return "", {}
    if app_id > 0:
        name = _STEAM_INDEX.get(int(app_id))
        if name and isinstance(data.get(name), dict):
            return name, data[name]

    candidates: List[str] = []
    for raw in titles:
        text = str(raw or "").strip()
        if not text:
            continue
        candidates.append(text)
        for part in re.split(r"[/|｜丨]", text):
            part = part.strip()
            if part and part not in candidates:
                candidates.append(part)
    for candidate in candidates:
        key = normalize_title(candidate)
        if not key:
            continue
        name = _TITLE_INDEX.get(key)
        if name and isinstance(data.get(name), dict):
            return name, data[name]
    return "", {}


def _placeholder_bases(prefix_dir: str, install_dir: str) -> Dict[str, str]:
    user_dir = os.path.join(prefix_dir, "drive_c", "users", "steamuser")
    bases = {
        "<base>": install_dir,
        "<home>": user_dir,
        "<winAppData>": os.path.join(user_dir, "AppData", "Roaming"),
        "<winLocalAppData>": os.path.join(user_dir, "AppData", "Local"),
        "<winDocuments>": os.path.join(user_dir, "Documents"),
        "<winSavedGames>": os.path.join(user_dir, "Saved Games"),
        "<winProgramData>": os.path.join(prefix_dir, "drive_c", "ProgramData"),
        "<winPublic>": os.path.join(prefix_dir, "drive_c", "Users", "Public"),
        "<winDir>": os.path.join(prefix_dir, "drive_c", "Windows"),
        "<root>": os.path.join(prefix_dir, "drive_c"),
    }
    return {key: value for key, value in bases.items() if value}


def _when_allows_proton(value: Any) -> bool:
    """Proton 下按 Windows 路径处理；显式只写 linux/mac 的条目跳过。"""
    if not isinstance(value, dict):
        return True
    whens = value.get("when")
    if not isinstance(whens, list) or not whens:
        return True
    for when in whens:
        if not isinstance(when, dict):
            continue
        os_name = str(when.get("os", "") or "").strip().lower()
        if os_name in {"", "windows"}:
            return True
    return False


def resolve_manifest_paths(
    info: Dict[str, Any],
    *,
    prefix_dir: str,
    install_dir: str,
) -> List[str]:
    """把清单里的 files 模板展开为 Proton 前缀下实际存在的路径。"""
    if not isinstance(info, dict):
        return []
    files = info.get("files")
    if not isinstance(files, dict):
        return []
    prefix = str(prefix_dir or "").strip()
    install = str(install_dir or "").strip()
    if not prefix or not install:
        return []
    bases = _placeholder_bases(prefix, install)

    found: List[str] = []

    def add(path: str) -> None:
        if not path:
            return
        resolved = os.path.realpath(os.path.expanduser(path))
        if not os.path.exists(resolved):
            return
        if os.path.isdir(resolved):
            try:
                with os.scandir(resolved) as it:
                    if not any(it):
                        return
            except Exception:
                return
        if resolved not in found:
            found.append(resolved)

    for template, value in files.items():
        if not _when_allows_proton(value if isinstance(value, dict) else None):
            continue
        text = str(template or "").strip()
        if not text:
            continue
        for placeholder, base in bases.items():
            if text.startswith(placeholder):
                text = text.replace(placeholder, base, 1)
                break
        if "<" in text and ">" in text:
            continue
        if any(char in text for char in ("*", "?", "[")):
            try:
                matches = glob.glob(text, recursive=True)
            except Exception:
                matches = []
            for match in matches:
                add(match)
                if len(found) >= _MAX_PATHS:
                    break
        else:
            add(text)
        if len(found) >= _MAX_PATHS:
            break
    return found
