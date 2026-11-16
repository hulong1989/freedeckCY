"""后端游戏进程检测（云存档自动同步的触发源）。

不依赖前端 Steam 事件：直接扫描 /proc/*/cmdline，判断命令行是否包含
已安装游戏的 install_path；状态从“运行”变为“退出”时产出 end 事件。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence


def _read_cmdline(pid: str) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except Exception:
        return ""
    return raw.replace(b"\x00", b" ").decode("utf-8", "replace")


_CMDLINE_CACHE: List[Any] = [0.0, []]
_CACHE_LOCK = threading.Lock()


def _snapshot_cmdlines(max_age: float = 2.0) -> List[str]:
    """一次读取 /proc 里所有命令行，短时间缓存（避免每个游戏重复扫 /proc）。"""
    now = time.monotonic()
    with _CACHE_LOCK:
        cached_at = float(_CMDLINE_CACHE[0] or 0)
        if now - cached_at < max_age:
            return list(_CMDLINE_CACHE[1])
        lines: List[str] = []
        proc = Path("/proc")
        if proc.is_dir():
            for entry in proc.iterdir():
                if not entry.name.isdigit():
                    continue
                cmdline = _read_cmdline(entry.name)
                if cmdline:
                    lines.append(cmdline)
        _CMDLINE_CACHE[0] = now
        _CMDLINE_CACHE[1] = lines
        return lines


def _is_running_proc(install_path: str) -> bool:
    target = os.path.realpath(os.path.expanduser(install_path))
    if len(target) < 4:
        return False
    return any(target in cmdline for cmdline in _snapshot_cmdlines())


def _is_running_pgrep(install_path: str) -> bool:
    target = os.path.realpath(os.path.expanduser(install_path))
    if len(target) < 4 or not shutil.which("pgrep"):
        return False
    try:
        result = subprocess.run(
            ["pgrep", "-f", target],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except Exception:
        return False
    return result.returncode == 0


def is_game_running(install_path: str) -> bool:
    """检测 install_path 是否出现在任意进程命令行中。"""
    if Path("/proc").is_dir():
        return _is_running_proc(install_path)
    return _is_running_pgrep(install_path)


class GameWatcher:
    """维护每个已安装游戏的运行状态，并在状态切换时产出事件。"""

    def __init__(self, detector: Optional[Callable[[str], bool]] = None):
        self._detector = detector or is_game_running
        self._states: Dict[str, bool] = {}

    def poll(self, records: Sequence[Any]) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for record in records:
            game_id = str(getattr(record, "game_id", "") or "").strip()
            install_path = str(getattr(record, "install_path", "") or "").strip()
            if not game_id or not install_path:
                continue
            seen.add(game_id)
            running = bool(self._detector(install_path))
            previous = self._states.get(game_id)
            if previous is None:
                self._states[game_id] = running
                continue
            if running and not previous:
                events.append({"type": "start", "game_id": game_id, "record": record})
            elif not running and previous:
                events.append({"type": "end", "game_id": game_id, "record": record})
            self._states[game_id] = running

        for game_id in list(self._states):
            if game_id not in seen:
                del self._states[game_id]
        return events

    def reset(self) -> None:
        self._states.clear()
