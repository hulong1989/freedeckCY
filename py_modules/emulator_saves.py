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
from param_sfo import find_param_sfo, read_param_sfo

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
        # Azahar 的 Linux/XDG 用户目录是 azahar-emu（见上游 src/common/common_paths.h）；
        # azahar 是早期移植误写的路径，保留兼容。
        "~/.local/share/azahar-emu/sdmc",
        "~/.local/share/azahar-emu/nand/user/save",
        "~/.local/share/azahar/sdmc",
        "~/.local/share/azahar/nand/user/save",
        "~/.var/app/org.azahar_emu.Azahar/data/azahar-emu/sdmc",
        "~/.var/app/org.azahar_emu.Azahar/data/azahar-emu/nand/user/save",
        "~/.var/app/org.azahar_emu.Azahar/data/azahar/sdmc",
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
PARAM_SFO_PLATFORMS = {"psp", "ps3"}
TITLE_ID_PLATFORMS = {"3ds"}
SAVE_SUFFIXES = (".sav", ".srm", ".dsv", ".mcd", ".ps2", ".bin", ".state", ".st")

# 跨设备恢复：这些目录锚点之后的相对层级必须保留。
# 例如 3DS 的 .../sdmc/Nintendo 3DS/id0/id1/title/<hi>/<lo>/data、
# PS3 的 .../dev_hdd0/home/<user>/savedata/<TITLE>、PSP 的 .../PSP/SAVEDATA/<TITLE>。
_RESTORE_ANCHORS: Dict[str, Tuple[Tuple[str, ...], ...]] = {
    "psp": (("PSP", "SAVEDATA"),),
    "ps3": (("dev_hdd0", "home"),),
    "3ds": (("sdmc",), ("nand", "user", "save")),
}

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
    raw = str(path or "").strip()
    if not raw:
        # os.path.realpath("") 会返回当前工作目录，绝不能把插件 cwd 当成存档目录。
        return ""
    try:
        real = os.path.realpath(os.path.expanduser(raw))
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
        raw = str(path or "").strip()
        if not raw:
            continue
        try:
            normalized = os.path.realpath(os.path.expanduser(raw))
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


def _dir_contains_path(directory: str, target: str) -> bool:
    """target（已 realpath）是否位于 directory 之内。"""
    try:
        base = os.path.realpath(directory)
    except Exception:
        return False
    if not base or not target:
        return False
    return target == base or target.startswith(base.rstrip(os.sep) + os.sep)


def _per_game_entries(root: str, stem: str, rom_path: str = "") -> List[str]:
    """在共享目录里找与 ROM 同名的存档文件/目录。

    注意：不能把“与 ROM 同名、且包含 ROM 本体”的游戏目录当成存档 ——
    解压后的 ROM 常在 <target>/<Game Name>/<Game Name>.gba，那样会把整个
    游戏目录（含 ROM）上传成云存档。
    """
    key = stem.lower().strip()
    if not key:
        return []
    rom_real = ""
    raw_rom = str(rom_path or "").strip()
    if raw_rom:
        try:
            rom_real = os.path.realpath(os.path.expanduser(raw_rom))
        except Exception:
            rom_real = ""
    matches: List[str] = []
    try:
        entries = sorted(os.scandir(root), key=lambda item: item.name.lower())
    except Exception:
        return []
    for entry in entries:
        name = entry.name.lower()
        entry_stem, _suffix = os.path.splitext(name)
        if entry_stem != key and name != key:
            continue
        try:
            if entry.is_dir():
                if rom_real and _dir_contains_path(entry.path, rom_real):
                    continue
                matches.append(entry.path)
            elif name.endswith(SAVE_SUFFIXES):
                matches.append(entry.path)
        except Exception:
            continue
    return matches


def _norm_title(value: str) -> str:
    raw = str(value or "").strip().lower()
    return "".join(char for char in raw if char.isalnum() or "\u4e00" <= char <= "\u9fff")


def _iter_savedata_dirs(platform: str, root: str):
    """遍历 PSP SAVEDATA/PSP 或 PS3 dev_hdd0/home 下的存档目录。"""
    base = os.path.realpath(root)
    if platform == "psp":
        try:
            for entry in os.scandir(base):
                if entry.is_dir():
                    yield entry.path
        except Exception:
            return
        return
    # PS3: dev_hdd0/home/<user>/savedata/<TITLEID>
    for dirpath, _dirnames, _filenames in os.walk(base):
        parts = os.path.relpath(dirpath, base).split(os.sep)
        if len(parts) >= 3 and parts[1] == "savedata":
            yield dirpath


_3DS_CART_EXTENSIONS = {".3ds", ".cci", ".cxi", ".app"}


def _read_cia_title_id(path: str) -> str:
    """从 CIA 安装包里读第一条 NCCH 内容的 Program ID。

    CIA 头部 0x00..0x20 之后是证书链/ticket/TMD/meta，内容数据从
    header_size + cert + ticket + tmd + meta 开始，第一条内容是应用 NCCH，
    Program ID 位于其 0x118 偏移。
    """
    try:
        with open(path, "rb") as fh:
            header = fh.read(0x2020)
            if len(header) < 0x20:
                return ""
            header_size = int.from_bytes(header[0x00:0x04], "little")
            cert_size = int.from_bytes(header[0x08:0x0C], "little")
            ticket_size = int.from_bytes(header[0x0C:0x10], "little")
            tmd_size = int.from_bytes(header[0x10:0x14], "little")
            meta_size = int.from_bytes(header[0x14:0x18], "little")
            if header_size < 0x20 or header_size > 0x10000:
                return ""
            content_offset = header_size + cert_size + ticket_size + tmd_size + meta_size
            fh.seek(content_offset + 0x100)
            ncch = fh.read(0x20)
    except Exception:
        return ""
    if len(ncch) < 0x20 or ncch[:4] != b"NCCH":
        return ""
    program_id = int.from_bytes(ncch[0x18:0x20], "little")
    if program_id <= 0:
        return ""
    return f"{program_id:016x}"


def _read_3ds_title_id(rom_path: str) -> str:
    """从 NCSD（.3ds/.cci）/NCCH（.cxi/.app）头，或 CIA 内容里读 Program ID。"""
    path = str(rom_path or "").strip()
    if not path or not os.path.isfile(path):
        return ""
    extension = os.path.splitext(path)[1].lower()
    if extension == ".cia":
        return _read_cia_title_id(path)
    if extension not in _3DS_CART_EXTENSIONS:
        return ""
    try:
        with open(path, "rb") as fh:
            fh.seek(0x100)
            header = fh.read(0x20)
    except Exception:
        return ""
    if len(header) < 0x20:
        return ""
    try:
        if header[:4] == b"NCSD":
            # CCI 的 NCSD 头 0x108 存 Title/Program ID。
            program_id = int.from_bytes(header[8:16], "little")
        elif header[:4] == b"NCCH":
            # NCCH（.cxi/.app）Program ID 在 0x118（相对 0x100 的 0x18）。
            program_id = int.from_bytes(header[0x18:0x20], "little")
        else:
            return ""
    except Exception:
        return ""
    if program_id <= 0:
        return ""
    return f"{program_id:016x}"


def _find_3ds_install_rom(record: Any) -> str:
    """CIA 安装的游戏没有 rom_path：从安装目录里的 .cia 读取 Program ID。"""
    install_path = str(getattr(record, "install_path", "") or "").strip()
    if not install_path:
        return ""
    root = os.path.realpath(os.path.expanduser(install_path))
    if not os.path.isdir(root):
        return ""
    candidates: List[str] = []
    base_depth = root.count(os.sep)
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            if dirpath.count(os.sep) - base_depth >= 3:
                dirnames[:] = []
            for name in filenames:
                if name.lower() == "manifest.json":
                    continue
                if name.lower().endswith(".cia"):
                    candidates.append(os.path.join(dirpath, name))
            if len(candidates) > 8:
                break
    except Exception:
        return ""
    for candidate in sorted(candidates, key=lambda item: (len(item), item)):
        if _read_3ds_title_id(candidate):
            return candidate
    return ""


def _split_3ds(roots: Sequence[str], rom_path: str) -> List[str]:
    title_id = _read_3ds_title_id(rom_path)
    if not title_id:
        return []
    low = title_id[-8:]
    matches: List[str] = []
    for root in roots:
        for dirpath, dirnames, _filenames in os.walk(root):
            if "title" in dirnames:
                title_dir = os.path.join(dirpath, "title")
                for high in os.listdir(title_dir) if os.path.isdir(title_dir) else []:
                    candidate = os.path.join(title_dir, high, low)
                    if os.path.isdir(candidate):
                        # 只上传 data/，避免把 content/（游戏本体）当存档打包。
                        data_dir = os.path.join(candidate, "data")
                        chosen = data_dir if os.path.isdir(data_dir) else candidate
                        if chosen not in matches:
                            matches.append(chosen)
    return matches


def _split_param_sfo(platform: str, roots: Sequence[str], title: str) -> List[str]:
    wanted = _norm_title(title)
    if not wanted:
        return []
    exact: List[str] = []
    fuzzy: List[str] = []
    for root in roots:
        for directory in _iter_savedata_dirs(platform, root):
            param = find_param_sfo(directory)
            if not param:
                continue
            meta = read_param_sfo(param)
            current = _norm_title(str(meta.get("TITLE", "") or ""))
            if not current:
                continue
            if current == wanted:
                if directory not in exact:
                    exact.append(directory)
            elif wanted in current or current in wanted:
                if directory not in fuzzy:
                    fuzzy.append(directory)
    # 只有唯一模糊命中才采用，避免“最终幻想”把“最终幻想2/零式”一起打包。
    if exact:
        return exact
    return fuzzy if len(fuzzy) == 1 else []


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
    if platform == "gba":
        # mGBA 默认把 .sav 放在 ROM 同目录（不是 saves/ 子目录）。
        for root in roots:
            path = _normalize_existing(root)
            if path and path not in candidates and _has_entries(path):
                candidates.append(path)
    for root in roots:
        for sub in PORTABLE_SUBDIRS.get(platform, ()):
            path = _normalize_existing(os.path.join(root, sub))
            if path and path not in candidates and _has_entries(path):
                candidates.append(path)

    candidates = _dedupe(candidates)
    if not candidates:
        return EmulatorSaveResult([], platform, emulator, False, searched, "save_dir_missing")

    if platform in TITLE_ID_PLATFORMS:
        rom_path = str(getattr(record, "rom_path", "") or "")
        if not _read_3ds_title_id(rom_path):
            # CIA 安装的游戏 rom_path 为空，记录里只有安装目录；从目录里的 .cia 读 Program ID。
            fallback_rom = _find_3ds_install_rom(record)
            if fallback_rom:
                rom_path = fallback_rom
        matched = _split_3ds(candidates, rom_path)
        if matched:
            return EmulatorSaveResult(matched, platform, emulator, True, candidates, "")

    if platform in PARAM_SFO_PLATFORMS:
        matched = _split_param_sfo(platform, candidates, str(getattr(record, "game_title", "") or ""))
        if matched:
            return EmulatorSaveResult(matched, platform, emulator, True, candidates, "")

    if platform in PER_GAME_PLATFORMS:
        rom_path = str(getattr(record, "rom_path", "") or "").strip()
        stem = Path(rom_path).stem if rom_path else ""
        per_game: List[str] = []
        for root in candidates:
            per_game.extend(_per_game_entries(root, stem, rom_path))
        per_game = _dedupe(per_game)
        if per_game:
            return EmulatorSaveResult(per_game, platform, emulator, True, candidates, "")
        # 还没有存档文件时不要退化成整目录，否则会把同平台其它游戏一起上传。
        return EmulatorSaveResult([], platform, emulator, True, candidates, "game_save_not_found")

    # 共享记忆卡/标题目录：返回整个目录，调用方按路径签名去重。
    return EmulatorSaveResult(candidates, platform, emulator, False, candidates, "")


def _last_subsequence(parts: Sequence[str], needle: Sequence[str]) -> int:
    size = len(needle)
    for index in range(len(parts) - size, -1, -1):
        if tuple(parts[index : index + size]) == tuple(needle):
            return index
    return -1


def _relative_restore_parent(platform: str, source_path: str, roots: Sequence[str]) -> str:
    """跨设备恢复：按平台目录锚点把 manifest 里的绝对路径映射回本机根目录。

    只做“同平台目录结构”的重建，例如：
      /home/old/.local/share/azahar-emu/sdmc/Nintendo 3DS/<id0>/<id1>/title/<hi>/<lo>/data
      -> ~/.local/share/azahar-emu/sdmc/Nintendo 3DS/<id0>/<id1>/title/<hi>/<lo>
    返回目标父目录；无法映射时返回空字符串（调用方回退到默认根目录）。
    """
    anchors = _RESTORE_ANCHORS.get(platform, ())
    if not anchors:
        return ""
    raw_source = str(source_path or "").strip()
    if not raw_source:
        return ""
    try:
        resolved = os.path.realpath(os.path.expanduser(raw_source))
    except Exception:
        return ""
    parts = Path(resolved).parts
    best: Optional[Tuple[int, str]] = None
    for root in roots:
        if not root:
            continue
        root_parts = Path(os.path.realpath(os.path.expanduser(root))).parts
        for anchor in anchors:
            size = len(anchor)
            if len(root_parts) < size or tuple(root_parts[-size:]) != anchor:
                continue
            anchor_index = _last_subsequence(parts, anchor)
            if anchor_index < 0:
                continue
            relative = parts[anchor_index + size :]
            if not relative:
                continue
            # 锚点之前的路径前缀越接近本机根目录，说明平台/Flatpak 变体选得越准。
            score = 0
            prefix = root_parts[:-size]
            for expected, actual in zip(reversed(prefix), reversed(parts[:anchor_index])):
                if expected != actual:
                    break
                score += 1
            parent_relative = relative[:-1]
            candidate = os.path.join(root, *parent_relative) if parent_relative else root
            if best is None or score > best[0]:
                best = (score, candidate)
    return best[1] if best else ""


def restore_roots(record: Any) -> List[str]:
    """恢复时可写入的模拟器存档根目录（存在优先，返回绝对路径）。"""
    platform = str(getattr(record, "platform", "") or "pc").strip().lower()
    roots: List[str] = []
    for raw in STANDARD_SAVE_DIRS.get(platform, ()):
        path = os.path.realpath(os.path.expanduser(raw))
        if path and path not in roots:
            roots.append(path)
    if platform == "gba":
        for root in _portable_roots(record):
            path = os.path.realpath(os.path.expanduser(root))
            if path and path not in roots:
                roots.append(path)
    for root in _portable_roots(record):
        for sub in PORTABLE_SUBDIRS.get(platform, ()):
            path = os.path.realpath(os.path.join(root, sub))
            if path and path not in roots:
                roots.append(path)
    if platform == "ps3":
        # RPCS3 的存档实际在 .../dev_hdd0/home/<user>/savedata/，发现已有用户目录后
        # 把它放到默认根目录（否则跨设备/旧 manifest 会少了 <user>/savedata 两层）。
        discovered: List[str] = []
        for raw in list(roots):
            base = os.path.realpath(os.path.expanduser(raw))
            if not os.path.isdir(base):
                continue
            try:
                with os.scandir(base) as scanner:
                    users = sorted(scanner, key=lambda item: item.name.lower())
            except OSError:
                continue
            for user in users:
                savedata = os.path.join(base, user.name, "savedata")
                if os.path.isdir(savedata) and savedata not in roots and savedata not in discovered:
                    discovered.append(savedata)
        if discovered:
            roots = discovered + roots
    # 存在的目录优先，方便 UI 默认选择；PS3 savedata 层优先于 dev_hdd0/home。
    def root_order(path: str) -> Tuple[int, int, int]:
        existing = 0 if os.path.isdir(path) else 1
        preferred = 0 if (platform == "ps3" and path.rstrip(os.sep).endswith(os.sep + "savedata")) else 1
        return (existing, preferred, len(path))

    roots.sort(key=root_order)
    return roots


def build_restore_targets(
    record: Any,
    entries: Sequence[Dict[str, Any]],
) -> Tuple[List[str], Dict[str, str]]:
    """把云端 manifest 条目映射到本机目标父目录。

    - 如果 source_path 仍在本机 HOME 下（同机恢复），优先恢复到原位置；
    - 跨设备/路径不存在时，按平台目录锚点重建相对层级（PSP/PS3/3DS），
      再回退到该平台第一个可写根目录。
    """
    platform = str(getattr(record, "platform", "") or "pc").strip().lower()
    roots = restore_roots(record)
    entry_targets: Dict[str, str] = {}
    for entry in entries:
        entry_id = str(entry.get("entry_id", "") or "").strip()
        if not entry_id:
            continue
        source = str(entry.get("source_path", "") or "").strip()
        target_parent = ""
        if source:
            try:
                resolved = os.path.realpath(os.path.expanduser(source))
                parent = os.path.dirname(resolved)
                # 只允许恢复到已知模拟器存档根目录内，避免被恶意 manifest 写到 HOME 任意位置。
                for root in roots:
                    if parent == root or parent.startswith(root.rstrip(os.sep) + os.sep):
                        target_parent = parent
                        break
                if not target_parent:
                    target_parent = _relative_restore_parent(platform, source, roots)
            except Exception:
                target_parent = ""
        if not target_parent:
            target_parent = roots[0] if roots else ""
        if target_parent:
            entry_targets[entry_id] = target_parent
    return roots, entry_targets
