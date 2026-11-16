"""mGBA 运行时管理与 GBA 启动封装。

GBA 资源来自天翼分享里的大量 ROM，安装流程：
  下载目标 zip → 解压得到 .gba → 生成启动脚本 → 写入 Steam 快捷方式（不走 Proton）。

mGBA 优先使用插件内置的 AppImage（`defaults/runtime/mgba/<arch>/mGBA.AppImage`），
首次使用时用 `--appimage-extract` 解包到用户目录（不依赖 FUSE，DroidDeck 的 proot 也能用）；
也支持系统 mGBA、Flatpak 与 `FREEDECKCY_MGBA_BIN` 覆盖。
"""

from __future__ import annotations

import asyncio
import os
import platform
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import aiohttp

import config

MGBA_PLATFORM = "gba"
MGBA_VERSION = "0.10.5"
MGBA_FLATPAK_APP = "io.mgba.mGBA"
MGBA_ASSETS = {
    "x86_64": f"mGBA-{MGBA_VERSION}-appimage-x64.appimage",
    "aarch64": f"mGBA-{MGBA_VERSION}-appimage-arm64.appimage",
}
MGBA_DOWNLOAD_BASE = f"https://github.com/mgba-emu/mgba/releases/download/{MGBA_VERSION}"
ROM_EXTENSIONS = (".gba",)

_MIN_APPIMAGE_BYTES = 8 * 1024 * 1024
_APPIMAGE_NAME = "mGBA.AppImage"


def runtime_arch() -> str:
    """运行时目录使用的架构名。"""
    machine = str(platform.machine() or "").strip().lower()
    if machine in {"x86_64", "amd64"}:
        return "x86_64"
    if machine in {"aarch64", "arm64"}:
        return "aarch64"
    return machine


def emulator_name_for_platform(platform_name: str) -> str:
    """平台 → 模拟器标识（当前只接 GBA/mGBA）。"""
    return "mgba" if str(platform_name or "").strip().lower() == MGBA_PLATFORM else ""


def emulator_state_dir() -> Path:
    """用户级模拟器目录（AppImage 解包产物）。"""
    return Path(config.DECKY_SEND_DIR) / "emulators"


def _plugin_dir(plugin_dir: str = "") -> Path:
    value = str(plugin_dir or "").strip()
    if not value:
        value = str(os.getenv("DECKY_PLUGIN_DIR", "") or "").strip()
    if not value:
        value = str(Path(__file__).resolve().parent.parent)
    return Path(value)


def bundled_appimage(plugin_dir: str = "", arch: str = "") -> Optional[str]:
    """插件内置的 mGBA AppImage。"""
    target_arch = arch or runtime_arch()
    path = _plugin_dir(plugin_dir) / "defaults" / "runtime" / "mgba" / target_arch / _APPIMAGE_NAME
    return str(path) if path.is_file() else None


def _extracted_binary_dir(arch: str = "") -> Path:
    return emulator_state_dir() / (arch or runtime_arch()) / "squashfs-root"


def extracted_command(arch: str = "") -> Optional[str]:
    """已解包的 mGBA 可执行文件。"""
    root = _extracted_binary_dir(arch)
    for candidate in (root / "AppRun", root / "usr" / "bin" / "mgba", root / "usr" / "bin" / "mgba-qt"):
        if candidate.is_file():
            return str(candidate)
    return None


def system_command() -> Optional[str]:
    for name in ("mgba", "mgba-qt"):
        found = shutil.which(name)
        if found:
            return found
    return None


def flatpak_command() -> Optional[List[str]]:
    if not shutil.which("flatpak"):
        return None
    try:
        result = subprocess.run(
            ["flatpak", "info", MGBA_FLATPAK_APP],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
        )
    except Exception:
        return None
    if result.returncode == 0:
        return ["flatpak", "run", MGBA_FLATPAK_APP]
    return None


def resolve_mgba_command(plugin_dir: str = "", *, allow_download: bool = False) -> Optional[List[str]]:
    """同步解析可用的 mGBA 启动命令（下载/解包走 ensure_mgba）。"""
    env_path = str(os.getenv("FREEDECKCY_MGBA_BIN", "") or "").strip()
    if env_path and os.path.isfile(env_path):
        return [env_path]

    extracted = extracted_command()
    if extracted:
        return [extracted]

    appimage = bundled_appimage(plugin_dir)
    if appimage:
        return [appimage]

    system = system_command()
    if system:
        return [system]

    flatpak = flatpak_command()
    if flatpak:
        return flatpak

    if allow_download:
        return ["__download__"]
    return None


def emulator_status(plugin_dir: str = "") -> Dict[str, Any]:
    """给安装计划/诊断用的 mGBA 状态。"""
    env_path = str(os.getenv("FREEDECKCY_MGBA_BIN", "") or "").strip()
    if env_path and os.path.isfile(env_path):
        return {"available": True, "source": "env", "command": env_path, "version": MGBA_VERSION}
    extracted = extracted_command()
    if extracted:
        return {"available": True, "source": "extracted", "command": extracted, "version": MGBA_VERSION}
    appimage = bundled_appimage(plugin_dir)
    if appimage:
        return {"available": True, "source": "bundled", "command": appimage, "version": MGBA_VERSION}
    system = system_command()
    if system:
        return {"available": True, "source": "system", "command": system, "version": "system"}
    flatpak = flatpak_command()
    if flatpak:
        return {"available": True, "source": "flatpak", "command": " ".join(flatpak), "version": "flatpak"}
    return {
        "available": False,
        "source": "",
        "command": "",
        "version": "",
        "message": "未找到 mGBA：请运行 make emulator-runtime（或设置 FREEDECKCY_MGBA_BIN / 安装 Flatpak io.mgba.mGBA）",
    }


def _run_appimage_extract(appimage: str, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [appimage, "--appimage-extract"],
        cwd=str(dest_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=300,
    )
    if result.returncode != 0:
        message = (result.stderr or b"").decode("utf-8", "replace").strip()
        raise RuntimeError(f"解包 mGBA AppImage 失败: {message[:300]}")


def _ensure_extracted(appimage: str) -> str:
    arch = runtime_arch()
    existing = extracted_command(arch)
    if existing:
        return existing
    _run_appimage_extract(appimage, emulator_state_dir() / arch)
    found = extracted_command(arch)
    if not found:
        raise RuntimeError("mGBA AppImage 解包后未找到可执行文件")
    try:
        os.chmod(found, 0o755)
    except Exception:
        pass
    return found


async def _download_appimage(arch: str) -> str:
    asset = MGBA_ASSETS.get(arch)
    if not asset:
        raise RuntimeError(f"不支持的架构: {arch}")
    target_dir = emulator_state_dir() / arch
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / _APPIMAGE_NAME
    url = f"{MGBA_DOWNLOAD_BASE}/{asset}"
    timeout = aiohttp.ClientTimeout(total=600, sock_read=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, allow_redirects=True) as response:
            if int(response.status) != 200:
                raise RuntimeError(f"下载 mGBA 失败: HTTP {int(response.status)}")
            with open(target, "wb") as fh:
                async for chunk in response.content.iter_chunked(1024 * 256):
                    if chunk:
                        fh.write(chunk)
    if not target.is_file() or target.stat().st_size < _MIN_APPIMAGE_BYTES:
        raise RuntimeError("mGBA 下载不完整")
    os.chmod(target, 0o755)
    return str(target)


async def ensure_mgba(plugin_dir: str = "", *, allow_download: bool = True) -> List[str]:
    """确保 mGBA 可用，返回启动命令 argv。"""
    command = resolve_mgba_command(plugin_dir, allow_download=False)
    if command:
        if command[0] == "__download__":
            command = None
        elif command[0].endswith(".AppImage") or command[0].endswith(".appimage"):
            return [_ensure_extracted(command[0])]
        else:
            return command

    appimage = bundled_appimage(plugin_dir)
    if appimage:
        return [_ensure_extracted(appimage)]

    if allow_download:
        downloaded = await _download_appimage(runtime_arch())
        return [_ensure_extracted(downloaded)]

    raise RuntimeError(emulator_status(plugin_dir).get("message", "mGBA 不可用"))


def find_rom_file(target_dir: str, open_path: str = "") -> str:
    """在安装目录里找 ROM，优先匹配 openpath 的同名文件。"""
    root = Path(target_dir)
    if not root.is_dir():
        return ""
    roms: List[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in ROM_EXTENSIONS:
            roms.append(path)
    if not roms:
        return ""
    wanted_stem = Path(str(open_path or "").replace("\\", "/")).stem.lower()
    if wanted_stem:
        for path in roms:
            if path.stem.lower() == wanted_stem:
                return str(path)
    roms.sort(key=lambda item: (len(str(item)), str(item)))
    return str(roms[0])


def create_launch_wrapper(
    *,
    command: Sequence[str],
    rom_path: str,
    wrapper_path: str,
    fullscreen: bool = True,
) -> str:
    """生成 Steam 快捷方式用的启动脚本，返回脚本路径。"""
    argv = [str(part) for part in command if str(part)]
    if not argv:
        raise ValueError("模拟器启动命令为空")
    if fullscreen:
        argv.append("-f")
    argv.append(str(rom_path))
    script = (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'exec ' + " ".join(shlex.quote(part) for part in argv) + "\n"
    )
    wrapper = Path(wrapper_path)
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    wrapper.write_text(script, encoding="utf-8")
    os.chmod(wrapper, 0o755)
    return str(wrapper)
