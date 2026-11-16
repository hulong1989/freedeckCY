"""模拟器 BIOS/固件/keys 与 portable 配置整理（参考 v0.6 / NewFreedeck）。

在安装流程中调用：把用户放到 `~/.local/share/freedeckCY/bios/<platform>/` 的
原始文件或压缩包部署到模拟器实际读取的位置，并写最小 portable 配置。

设计原则：
  - 只创建缺失的配置，不覆盖用户已有设置；
  - 找不到模拟器可写目录时只复制到用户数据目录，并返回提示；
  - 不自动下载 BIOS/固件/keys（版权原因），只做部署。
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import config
from emulator_manager import bios_dir, bios_present, get_spec, prepare_bios

ARCHIVE_SUFFIXES = (".zip", ".7z", ".rar", ".tar", ".gz", ".tgz", ".xz", ".bz2")
KEY_NAMES = ("prod.keys", "title.keys")
PS1_BIOS_HINTS = ("scph", "bios")
PS2_BIOS_HINTS = ("scph", "ps2", "bios")
NDS_BIOS_NAMES = ("bios7.bin", "bios9.bin", "firmware.bin", "dsi_firmware.bin", "dsi_bios7.bin", "dsi_bios9.bin")

_EDEN_DATA = Path.home() / ".local" / "share" / "eden"
_EDEN_KEYS = _EDEN_DATA / "keys"
_EDEN_REGISTERED = _EDEN_DATA / "nand" / "system" / "Contents" / "registered"
_RPCS3_CONFIG = Path.home() / ".config" / "rpcs3"
_DUCKSTATION_DATA = Path.home() / ".local" / "share" / "duckstation"
_AZAHAR_DATA = Path.home() / ".local" / "share" / "azahar"


def _resolve_root(command: Sequence[str]) -> str:
    if not command:
        return ""
    path = str(command[0] or "").strip()
    if not path:
        return ""
    return os.path.dirname(os.path.realpath(os.path.expanduser(path)))


def _writable_dir(path: str) -> bool:
    return bool(path) and os.path.isdir(path) and os.access(path, os.W_OK)


def _write_if_missing(path: str, content: str) -> bool:
    if os.path.isfile(path):
        return False
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    return True


def _set_ini_value(path: str, section: str, key: str, value: str) -> None:
    """在已有 INI 中修复单个键，保留其它配置；缺失时追加。"""
    if not os.path.isfile(path):
        return
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except Exception:
        return
    section_header = f"[{section}]"
    key_prefix = f"{key} ="
    in_section = False
    replaced = False
    insert_at = len(lines)
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if in_section and not replaced:
                insert_at = index
                break
            in_section = stripped.lower() == section_header.lower()
            continue
        if in_section:
            if stripped.lower().startswith(key_prefix.lower()) or stripped.lower().startswith(f"{key.lower()}="):
                lines[index] = f"{key} = {value}"
                replaced = True
                break
            insert_at = index + 1
    if not replaced:
        if insert_at >= len(lines):
            if lines and lines[-1].strip():
                lines.append("")
            lines.append(section_header)
            lines.append(f"{key} = {value}")
        else:
            lines.insert(insert_at, f"{key} = {value}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _walk_all_files(root: str, *, max_depth: int = 6) -> List[str]:
    result: List[str] = []
    base = os.path.realpath(os.path.expanduser(root))
    if not os.path.isdir(base):
        return result
    base_depth = base.count(os.sep)
    for dirpath, dirnames, filenames in os.walk(base):
        depth = dirpath.count(os.sep) - base_depth
        if depth >= max_depth:
            dirnames[:] = []
        for name in filenames:
            if not name.lower().endswith(ARCHIVE_SUFFIXES):
                result.append(os.path.join(dirpath, name))
    return sorted(result, key=lambda path: (len(path), path))


def _find_named(root: str, suffixes: Sequence[str], *, max_depth: int = 6) -> List[str]:
    result: List[str] = []
    base = os.path.realpath(os.path.expanduser(root))
    if not os.path.isdir(base):
        return result
    base_depth = base.count(os.sep)
    for dirpath, dirnames, filenames in os.walk(base):
        depth = dirpath.count(os.sep) - base_depth
        if depth >= max_depth:
            dirnames[:] = []
        for name in filenames:
            lower = name.lower()
            if lower.endswith(tuple(suffixes)):
                result.append(os.path.join(dirpath, name))
    return sorted(result, key=lambda path: (len(path), path))


def _copy_files(files: Iterable[str], targets: Sequence[Path], *, max_count: int = 40) -> List[str]:
    copied: List[str] = []
    for target in targets:
        try:
            target.mkdir(parents=True, exist_ok=True)
        except Exception:
            continue
        for path in list(files)[:max_count]:
            if not os.path.isfile(path):
                continue
            destination = target / os.path.basename(path)
            try:
                if not destination.is_file():
                    shutil.copy2(path, destination)
                copied.append(str(destination))
            except Exception as exc:
                config.logger.warning("复制模拟器文件失败 %s -> %s: %s", path, destination, exc)
    return copied


def _extract_archives(
    archives: Sequence[str],
    seven_zip: Any,
    temp_root: str,
    *,
    include_all: bool = False,
) -> List[str]:
    extracted: List[str] = []
    if seven_zip is None:
        return extracted
    for archive in archives:
        out_dir = os.path.join(temp_root, f"extract_{len(extracted)}")
        try:
            seven_zip.extract_archive(archive, out_dir)
        except Exception as exc:
            config.logger.warning("解压 BIOS/固件压缩包失败 %s: %s", archive, exc)
            continue
        if include_all:
            for dirpath, _dirnames, filenames in os.walk(out_dir):
                extracted.extend(os.path.join(dirpath, name) for name in filenames)
        else:
            extracted.extend(_find_named(out_dir, (".bin", ".rom", ".bios", ".keys", ".key", ".pup", ".nca")))
    return extracted


def _source_files(platform: str, *, seven_zip: Any = None) -> List[str]:
    """收集 bios/<platform>/ 下的原始文件与压缩包解压产物。"""
    root = bios_dir(platform)
    if not root.is_dir():
        return []
    if platform == "3ds":
        raw = _walk_all_files(str(root))
    else:
        raw = _find_named(str(root), (".bin", ".rom", ".bios", ".keys", ".key", ".pup", ".nca"))
    archives = _find_named(str(root), ARCHIVE_SUFFIXES)
    if not archives or seven_zip is None:
        return raw
    temp_root = tempfile.mkdtemp(prefix=f"freedeckcy_emusetup_{platform}_")
    try:
        extracted = _extract_archives(
            archives,
            seven_zip,
            temp_root,
            include_all=(platform == "3ds"),
        )
        # 解压内容需要临时保留到复制完成；调用方在本函数返回后立即复制，
        # 因此把临时目录挂到返回值之外并延迟清理不可靠。这里直接复制到
        # bios_root/_extracted 作为持久缓存，避免文件悬空。
        cache = root / "_extracted"
        cache.mkdir(parents=True, exist_ok=True)
        persistent: List[str] = []
        for path in extracted:
            try:
                destination = cache / os.path.basename(path)
                if not destination.is_file():
                    shutil.copy2(path, destination)
                persistent.append(str(destination))
            except Exception:
                continue
        return raw + persistent
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def _write_duckstation(root: str, bios_files: Sequence[str]) -> List[str]:
    messages: List[str] = []
    if not _writable_dir(root):
        return messages
    _write_if_missing(os.path.join(root, "portable.txt"), "")
    target = Path(root) / "bios"
    copied = _copy_files(bios_files, [target])
    if copied:
        messages.append(f"DuckStation BIOS 已部署：{len(copied)} 个文件")
    settings = Path(root) / "portable_data" / "settings" / "settings.ini"
    if not settings.is_file():
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            "[Main]\n"
            "Language = zh-CN\n\n"
            "[BIOS]\n"
            "SearchDirectory = ./bios\n\n"
            "[Display]\n"
            "Fullscreen = true\n\n"
            "[Console]\n"
            "Region = Auto\n",
            encoding="utf-8",
        )
        messages.append("DuckStation portable 配置已写入（BIOS 搜索目录/全屏）")
    _set_ini_value(str(settings), "BIOS", "SearchDirectory", "./bios")
    _set_ini_value(str(settings), "Display", "Fullscreen", "true")
    return messages


def _write_pcsx2(root: str, bios_files: Sequence[str]) -> List[str]:
    messages: List[str] = []
    targets = [Path(root) / "bios", Path.home() / ".local" / "share" / "PCSX2" / "bios", Path.home() / ".config" / "PCSX2" / "bios"]
    copied = _copy_files(bios_files, targets)
    if copied:
        messages.append(f"PCSX2 BIOS 已部署：{len(copied)} 个文件")
    if _writable_dir(root):
        _write_if_missing(os.path.join(root, "portable.ini"), "")
        ini = Path(root) / "inis" / "PCSX2.ini"
        if not ini.is_file():
            ini.parent.mkdir(parents=True, exist_ok=True)
            ini.write_text(
                "[UI]\n"
                "Fullscreen = true\n"
                "ConfirmShutdown = false\n\n"
                "[Folders]\n"
                f"Bios = {Path(root) / 'bios'}\n\n"
                "[EmuCore]\n"
                "CdvdSource = Iso\n",
                encoding="utf-8",
            )
            messages.append("PCSX2 portable 配置已写入（BIOS 目录/全屏）")
        _set_ini_value(str(ini), "Folders", "Bios", str(Path(root) / "bios"))
        _set_ini_value(str(ini), "UI", "Fullscreen", "true")
    return messages


def _write_mgba_config(root: str) -> List[str]:
    if not _writable_dir(root):
        return []
    _write_if_missing(os.path.join(root, "portable.ini"), "")
    ini = Path(root) / "qt.ini"
    if _write_if_missing(
        str(ini),
        "[General]\nfullScreen = true\npauseOnFocusLoss = false\n",
    ):
        return ["mGBA portable 配置已写入（全屏）"]
    return []


def _write_ppsspp_config(root: str) -> List[str]:
    if not _writable_dir(root):
        return []
    _write_if_missing(os.path.join(root, "portable.txt"), "")
    ini = Path(root) / "memstick" / "PSP" / "SYSTEM" / "ppsspp.ini"
    if _write_if_missing(str(ini), "[General]\nFullScreen = True\n"):
        return ["PPSSPP portable 配置已写入（全屏）"]
    return []


def _deploy_nds(root: str, files: Sequence[str]) -> List[str]:
    targets = [Path(root), Path.home() / ".local" / "share" / "melonDS"]
    candidates = [path for path in files if os.path.basename(path).lower() in NDS_BIOS_NAMES]
    copied = _copy_files(candidates or files, targets)
    if copied:
        return [f"melonDS BIOS/固件已部署：{len(copied)} 个文件"]
    return []


def _deploy_switch(files: Sequence[str]) -> List[str]:
    messages: List[str] = []
    keys = [path for path in files if path.lower().endswith((".keys", ".key"))]
    if keys:
        copied = _copy_files(keys, [_EDEN_KEYS])
        if copied:
            messages.append(f"Eden keys 已部署：{len(copied)} 个文件")

    archives = _find_named(str(bios_dir("switch")), ARCHIVE_SUFFIXES)
    registered = _EDEN_REGISTERED
    if archives and not (registered.is_dir() and any(registered.iterdir())):
        # 固件压缩包由调用方通过 seven_zip 解压；此处只处理已解出的 .nca 目录结构。
        nca_dirs = {
            os.path.dirname(path)
            for path in files
            if path.lower().endswith(".nca")
        }
        copied = 0
        for source_dir in nca_dirs:
            try:
                shutil.copytree(source_dir, registered, dirs_exist_ok=True)
                copied += 1
            except Exception as exc:
                config.logger.warning("复制 Eden 固件失败 %s: %s", source_dir, exc)
        if copied:
            messages.append("Eden 固件已部署到 registered 目录")
    if not (registered.is_dir() and any(registered.iterdir())):
        messages.append("未找到 Eden 固件（固件 zip 放到 bios/switch/，会自动解压部署）")
    if not keys:
        messages.append("未找到 Eden keys（prod.keys 放到 bios/switch/）")
    return messages


def _install_rpcs3_firmware(root: str, command: Sequence[str], files: Sequence[str]) -> List[str]:
    pups = [path for path in files if path.lower().endswith(".pup")]
    if not pups:
        return ["未找到 PS3 固件（PS3UPDAT.PUP 放到 bios/ps3/）"]
    dev_flash = _RPCS3_CONFIG / "dev_flash"
    if dev_flash.is_dir() and any(dev_flash.iterdir()):
        return []
    executable = str(command[0]) if command else ""
    if not executable or not os.path.isfile(executable):
        return [f"已找到 PS3 固件但 RPCS3 不可执行，请手动安装：{pups[0]}"]
    try:
        result = subprocess.run(
            [executable, "--installfw", pups[0]],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=600,
        )
        if result.returncode == 0:
            return ["PS3 固件已安装到 RPCS3"]
        error = (result.stderr or b"").decode("utf-8", "replace").strip()
        return [f"PS3 固件安装失败：{error[:200] or 'unknown'}"]
    except Exception as exc:
        return [f"PS3 固件安装失败：{exc}"]


def _deploy_3ds(files: Sequence[str]) -> List[str]:
    targets = [_AZAHAR_DATA / "sysdata", Path.home() / ".local" / "share" / "citra" / "sysdata"]
    copied = _copy_files(files, targets)
    source_tree = bios_dir("3ds") / "sysdata"
    if source_tree.is_dir():
        for target in targets:
            try:
                shutil.copytree(source_tree, target, dirs_exist_ok=True)
                copied += 1
            except Exception as exc:
                config.logger.warning("复制 3DS sysdata 失败 %s: %s", source_tree, exc)
    if copied:
        return [f"3DS system files 已部署：{copied} 项"]
    return ["未找到 3DS system files（sysdata 文件/目录放到 bios/3ds/）"]


def setup_emulator(
    platform: str,
    command: Sequence[str],
    *,
    seven_zip: Any = None,
) -> List[str]:
    """部署 BIOS/固件/keys 并写 portable 配置，返回面向用户的提示。"""
    spec = get_spec(platform)
    if spec is None:
        return []
    root = _resolve_root(command)
    files = _source_files(platform, seven_zip=seven_zip)
    messages: List[str] = []

    # 保留旧的 BIOS 复制逻辑（PS1/PS2 用户数据目录），再补充 portable 目录。
    try:
        messages.extend(prepare_bios(spec))
    except Exception as exc:
        messages.append(f"BIOS 处理失败: {exc}")

    if platform == "ps1":
        messages.extend(_write_duckstation(root, files))
    elif platform == "ps2":
        messages.extend(_write_pcsx2(root, files))
    elif platform == "nds":
        messages.extend(_deploy_nds(root, files))
    elif platform == "switch":
        messages.extend(_deploy_switch(files))
    elif platform == "ps3":
        messages.extend(_install_rpcs3_firmware(root, command, files))
    elif platform == "3ds":
        messages.extend(_deploy_3ds(files))
    elif platform == "gba":
        messages.extend(_write_mgba_config(root))
    elif platform == "psp":
        messages.extend(_write_ppsspp_config(root))

    if spec.bios_required and not bios_present(platform):
        messages.append(f"未检测到 {spec.name} BIOS（放到 {bios_dir(platform)}）")
    return messages
