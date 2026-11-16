"""模拟器存档发现：把 GBA/PSP/NDS/PS1/FC/MD/3DS/PS2/PS3/Switch 的存档
纳入云存档候选。

策略：
  - 每平台一组标准数据目录 + portable/Flatpak 目录；
  - GBA/FC/MD/NDS 优先按 ROM 文件名找单游戏存档（避免把同目录其它游戏一起打包）；
  - PSP/PS1/PS2/3DS/PS3/Switch 多为共享记忆卡/标题目录，返回整个目录，
    由调用方按路径签名去重，避免每个游戏重复上传同一份共享存档。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import config
from emulator_manager import installed_command, get_spec

# 标准数据目录（Linux）
STANDARD_SAVE_DIRS: Dict[str, Tuple[str, ...]] = {
    "gba": (
        "~/.local/share/mgba/saves",
        "~/.config/mgba/saves",
        "~/.var/app/io.mgba.mGBA/data/mgba/saves",
    ),
    "psp": (
        "~/.local/share/ppsspp/PSP/SAVEDATA",
        "~/.config/ppsspp/PSP/SAVEDATA",
        "~/.var/app/org.ppsspp.PPSSPP/config/ppsspp/PSP/SAVEDATA",
        "~/.var/app/org.ppsspp.PPSSPP/data/ppsspp/PSP/SAVEDATA",
    ),
    "nds": (
        "~/.local/share/melonDS/saves",
        "~/.config/melonDS/saves",
    ),
    "ps1": (
        "~/.local/share/duckstation/memcards",
        "~/.var/app/org.duckstation.DuckStation/data/duckstation/memcards",
    ),
    "fc": (
        "~/.local/share/Mesen2/Saves",
        "~/.config/Mesen2/Saves",
        "~/.local/share/mesen2/Saves",
    ),
    "md": (
        "~/.local/share/Mesen2/Saves",
        "~/.config/Mesen2/Saves",
        "~/.local/share/mesen2/Saves",
    ),
    "ps2": (
        "~/.local/share/PCSX2/memcards",
        "~/.config/PCSX2/memcards",
        "~/.var/app/net.pcsx2.PCSX2/config/PCSX2/memcards",
    ),
    "ps3": (
        "~/.config/rpcs3/dev_hdd0/home",
        "~/.local/share/rpcs3/dev_hdd0/home",
    ),
    "switch": (
        "~/.local/share/eden/nand/user/save",
        "~/.local/share/eden/saves",
    ),
    "3ds": (
        "~/.local/share/azahar/sdmc",
        "~/.local/share/azahar/nand/user/save",
        "~/.var/app/org.azahar_emu.Azahar/data/azahar/sdmc",
        "~/.var/app/org.azahar_emu.Azahar/data/azahar/nand/user/save",
        "~/.var/app/org.azahar_emu.Azahar/data/azahar-emu/sdmc",
    ),
}

# portable 子目录（相对模拟器 AppDir/安装根目录）
PORTABLE_SUBDIRS: Dict[str, Tuple[str, ...]] = {
    "gba": ("saves",),
    "psp": ("memstick/PSP/SAVEDATA",),
    "nds": ("saves",),
    "ps1": ("memcards",),
    "fc": ("Saves", "saves"),
    "md": ("Saves", "saves"),
    "ps2": ("memcards",),
    "ps3": ("dev_hdd0/home",),
    "switch": ("nand/user/save", "saves"),
    "3ds": ("sdmc",),
}

# 按单游戏文件名过滤的平台（避免共享目录把其它游戏一起打包）
PER_GAME_PLATFORMS = {"gba", "fc", "md", "nds"}
SAVE_SUFFIXES = (".sav", ".srm", ".dsv", ".mcd", ".ps2", ".bin", ".state", ".st")

_MAX_PATHS = 12


@dataclass(frozen=True)
class EmulatorSaveResult:
    paths: List[str]
    platform: str
    emulator: str
    per_game: bool
    searched: List[str]
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "paths": list(self.paths),
            "platform": self.platform,
            "emulator": self.emulator,
            "per_game": self.per_game,
            "searched": list(self.searched),
            "reason": self.reason,
        }


def _normalize_existing(path: str) -> str:
    try:
        real = os.path.realpath(os.path.expanduser(str(path or "").strip()))
    except Exception:
        return ""
    return real if real and os.path.isdir(real) else ""


def _has_entries(path: str) -> bool:
    try:
        with os.scandir(path) as it:
            for _ in it:
                return True
    except Exception:
        return False
    return False


def _dedupe(paths: Sequence[str]) -> List[str]:
    result: List[str] = []
    for path in paths:
        try:
            normalized = os.path.realpath(os.path.expanduser(str(path or "").strip()))
        except Exception:
            continue
        if normalized and os.path.exists(normalized) and normalized not in result:
            result.append(normalized)
    return result[: _MAX_PATHS]


def _portable_roots(record: Any) -> List[str]:
    roots: List[str] = []
    install_path = _normalize_existing(str(getattr(record, "install_path", "") or ""))
    if install_path:
        roots.append(install_path)
    rom_path = str(getattr(record, "rom_path", "") or "").strip()
    if rom_path:
        roots.append(os.path.dirname(os.path.realpath(os.path.expanduser(rom_path))))
    launcher = str(getattr(record, "launcher_path", "") or "").strip()
    if launcher:
        roots.append(os.path.dirname(os.path.realpath(os.path.expanduser(launcher))))
    spec = get_spec(str(getattr(record, "platform", "") or ""))
    if spec is not None:
        try:
            command = installed_command(spec)
        except Exception:
            command = None
        if command:
            roots.append(os.path.dirname(os.path.realpath(os.path.expanduser(command))))
    result: List[str] = []
    for root in roots:
        if root and root not in result:
            result.append(root)
    return result


def _per_game_entries(root: str, stem: str) -> List[str]:
    """在共享目录里找与 ROM 同名的存档文件/目录。"""
    key = stem.lower().strip()
    if not key:
        return []
    matches: List[str] = []
    try:
        entries = sorted(os.scandir(root), key=lambda item: item.name.lower())
    except Exception:
        return []
    for entry in entries:
        name = entry.name.lower()
        if key in name or name.startswith(key):
            try:
                if entry.is_dir() or entry.name.lower().endswith(SAVE_SUFFIXES):
                    matches.append(entry.path)
            except Exception:
                continue
    return matches


def collect_emulator_save_paths(record: Any) -> EmulatorSaveResult:
    """返回已安装模拟器游戏的存档路径。"""
    platform = str(getattr(record, "platform", "") or "pc").strip().lower()
    spec = get_spec(platform)
    emulator = spec.name if spec else ""
    searched: List[str] = []
    candidates: List[str] = []

    for raw in STANDARD_SAVE_DIRS.get(platform, ()):
        path = _normalize_existing(raw)
        if path:
            searched.append(path)
            if _has_entries(path):
                candidates.append(path)

    roots = _portable_roots(record)
    for root in roots:
        for sub in PORTABLE_SUBDIRS.get(platform, ()):
            path = _normalize_existing(os.path.join(root, sub))
            if path and path not in candidates and _has_entries(path):
                candidates.append(path)

    candidates = _dedupe(candidates)
    if not candidates:
        return EmulatorSaveResult([], platform, emulator, False, searched, "save_dir_missing")

    if platform in PER_GAME_PLATFORMS:
        rom_path = str(getattr(record, "rom_path", "") or "").strip()
        stem = Path(rom_path).stem if rom_path else ""
        per_game: List[str] = []
        for root in candidates:
            per_game.extend(_per_game_entries(root, stem))
        per_game = _dedupe(per_game)
        if per_game:
            return EmulatorSaveResult(per_game, platform, emulator, True, candidates, "")
        # 还没有存档文件时不要退化成整目录，否则会把同平台其它游戏一起上传。
        return EmulatorSaveResult([], platform, emulator, True, candidates, "game_save_not_found")

    # 共享记忆卡/标题目录：返回整个目录，调用方按路径签名去重。
    return EmulatorSaveResult(candidates, platform, emulator, False, candidates, "")
