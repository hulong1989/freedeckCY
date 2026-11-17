"""模拟器运行时注册表与启动封装（GBA / PSP / NDS）。

设计：
  - 每个平台一条 EmulatorSpec（官方 release 资产、启动参数、ROM 扩展名）。
  - 所有模拟器首次安装时在线获取；3DS 在 SteamOS 上优先官方 Flatpak，其余用 AppImage。
  - AppImage 统一用 `--appimage-extract` 解包运行，不依赖 FUSE（DroidDeck/proot 可用）。
  - 启动脚本由安装流程生成，Steam 快捷方式不写 Proton 映射。
"""

from __future__ import annotations

import asyncio
import os
import platform
import re
import shlex
import shutil
import subprocess
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import aiohttp

import config


@dataclass(frozen=True)
class EmulatorSpec:
    platform: str
    name: str
    adapter: str
    repo: str
    download_base: str
    assets: Dict[str, str]
    archive: str  # appimage | zip
    launch_args: Tuple[str, ...]
    rom_extensions: Tuple[str, ...]
    env_var: str = ""
    notes: str = ""
    min_bytes: int = 8 * 1024 * 1024
    state_key: str = ""
    executables: Tuple[str, ...] = ()
    bios_required: bool = False
    flatpak_id: str = ""
    setup_required: bool = False
    setup_hint: str = ""


MGBA_VERSION = "0.10.5"
PPSSPP_VERSION = "1.20.4"
MELONDS_VERSION = "1.1"

EMULATORS: Dict[str, EmulatorSpec] = {
    "gba": EmulatorSpec(
        platform="gba",
        name="mGBA",
        adapter="mgba",
        repo="mgba-emu/mgba",
        download_base=f"https://github.com/mgba-emu/mgba/releases/download/{MGBA_VERSION}",
        assets={
            "x86_64": f"mGBA-{MGBA_VERSION}-appimage-x64.appimage",
            "aarch64": f"mGBA-{MGBA_VERSION}-appimage-arm64.appimage",
        },
        archive="appimage",
        launch_args=("-f", "{rom}"),
        rom_extensions=(".gba",),
        env_var="FREEDECKCY_MGBA_BIN",
        notes="mGBA 官方 AppImage；首次安装按需下载",
        min_bytes=20 * 1024 * 1024,
    ),
    "psp": EmulatorSpec(
        platform="psp",
        name="PPSSPP",
        adapter="ppsspp",
        repo="hrydgard/ppsspp",
        download_base=f"https://github.com/hrydgard/ppsspp/releases/download/v{PPSSPP_VERSION}",
        assets={
            "x86_64": f"PPSSPP-v{PPSSPP_VERSION}-anylinux-x86_64.AppImage",
            "aarch64": f"PPSSPP-v{PPSSPP_VERSION}-anylinux-aarch64.AppImage",
        },
        archive="appimage",
        launch_args=("--fullscreen", "{rom}"),
        rom_extensions=(".iso", ".cso", ".pbp", ".elf"),
        env_var="FREEDECKCY_PPSSPP_BIN",
        notes="PPSSPP 官方 AppImage；首次安装按需下载",
        min_bytes=30 * 1024 * 1024,
    ),
    "nds": EmulatorSpec(
        platform="nds",
        name="melonDS",
        adapter="melonds",
        repo="melonDS-emu/melonDS",
        download_base=f"https://github.com/melonDS-emu/melonDS/releases/download/{MELONDS_VERSION}",
        assets={
            "x86_64": f"melonDS-{MELONDS_VERSION}-appimage-x86_64.zip",
            "aarch64": f"melonDS-{MELONDS_VERSION}-appimage-aarch64.zip",
        },
        archive="zip",
        launch_args=("{rom}",),
        rom_extensions=(".nds", ".dsi", ".srl"),
        env_var="FREEDECKCY_MELONDS_BIN",
        notes="melonDS 官方 AppImage（zip 内）；首次安装按需下载",
        min_bytes=15 * 1024 * 1024,
    ),
    "ps1": EmulatorSpec(
        platform="ps1",
        name="DuckStation",
        adapter="duckstation",
        repo="stenzek/duckstation",
        download_base="https://github.com/stenzek/duckstation/releases/download/latest",
        assets={
            "x86_64": "DuckStation-x64.AppImage",
            "aarch64": "DuckStation-arm64.AppImage",
        },
        archive="appimage",
        launch_args=("-batch", "-fullscreen", "{rom}"),
        rom_extensions=(".m3u", ".cue", ".chd", ".iso", ".pbp", ".bin"),
        env_var="FREEDECKCY_DUCKSTATION_BIN",
        notes="DuckStation 官方 AppImage；需要自备 PS1 BIOS（scph*.bin）",
        min_bytes=40 * 1024 * 1024,
        state_key="duckstation",
        bios_required=True,
    ),
    "fc": EmulatorSpec(
        platform="fc",
        name="Mesen2",
        adapter="mesen",
        repo="SourMesen/Mesen2",
        download_base="https://github.com/SourMesen/Mesen2/releases/download/2.1.1",
        assets={
            "x86_64": "Mesen_2.1.1_Linux_x64.zip",
            "aarch64": "Mesen_2.1.1_Linux_ARM64.zip",
        },
        archive="zip",
        launch_args=("/fullscreen", "{rom}"),
        rom_extensions=(".nes", ".fds", ".unf", ".unif"),
        env_var="FREEDECKCY_MESEN_BIN",
        notes="Mesen2 官方 zip（x64/arm64）；FC/NES",
        min_bytes=10 * 1024 * 1024,
        state_key="mesen",
        executables=("Mesen",),
    ),
    "md": EmulatorSpec(
        platform="md",
        name="Mesen2",
        adapter="mesen",
        repo="SourMesen/Mesen2",
        download_base="https://github.com/SourMesen/Mesen2/releases/download/2.1.1",
        assets={
            "x86_64": "Mesen_2.1.1_Linux_x64.zip",
            "aarch64": "Mesen_2.1.1_Linux_ARM64.zip",
        },
        archive="zip",
        launch_args=("/fullscreen", "{rom}"),
        rom_extensions=(".md", ".gen", ".smd", ".bin", ".32x"),
        env_var="FREEDECKCY_MESEN_BIN",
        notes="Mesen2 官方 zip（x64/arm64）；MD/Genesis",
        min_bytes=10 * 1024 * 1024,
        state_key="mesen",
        executables=("Mesen",),
    ),
    "3ds": EmulatorSpec(
        platform="3ds",
        name="Azahar",
        adapter="azahar",
        repo="azahar-emu/azahar",
        download_base="https://github.com/azahar-emu/azahar/releases/download/2126.2",
        assets={"x86_64": "azahar.AppImage"},
        archive="appimage",
        launch_args=("{rom}",),
        # Azahar 不支持直接启动 .cia（需先安装）；只收录可当 ROM 加载的格式。
        rom_extensions=(".3ds", ".cci", ".cxi", ".app", ".3dsx", ".elf", ".axf"),
        env_var="FREEDECKCY_AZAHAR_BIN",
        notes="Azahar 官方 AppImage（仅 x86_64）；需要 3DS system files",
        min_bytes=60 * 1024 * 1024,
        state_key="azahar",
        flatpak_id="org.azahar_emu.Azahar",
        setup_required=True,
        setup_hint="3DS 需要 system files：请在 Azahar 首次启动时按提示配置（或把 sysdata 放入其数据目录）",
    ),
    "ps2": EmulatorSpec(
        platform="ps2",
        name="PCSX2",
        adapter="pcsx2",
        repo="PCSX2/pcsx2",
        download_base="https://github.com/PCSX2/pcsx2/releases/download/v2.8.2",
        assets={"x86_64": "pcsx2-v2.8.2-linux-appimage-x64-Qt.AppImage"},
        archive="appimage",
        launch_args=("-batch", "-fullscreen", "{rom}"),
        rom_extensions=(".iso", ".chd", ".cue", ".bin", ".gz"),
        env_var="FREEDECKCY_PCSX2_BIN",
        notes="PCSX2 官方 AppImage（仅 x86_64）；需要 PS2 BIOS",
        min_bytes=40 * 1024 * 1024,
        state_key="pcsx2",
        bios_required=True,
    ),
    "ps3": EmulatorSpec(
        platform="ps3",
        name="RPCS3",
        adapter="rpcs3",
        repo="RPCS3/rpcs3-binaries-linux",
        download_base="https://github.com/RPCS3/rpcs3-binaries-linux/releases/download/build-8d6b42e78adae5cc4685b45ecf2f370273e91810",
        assets={"x86_64": "rpcs3-v0.0.43-20606-8d6b42e7_linux64.AppImage"},
        archive="appimage",
        launch_args=("--no-gui", "{rom}"),
        rom_extensions=(".iso", ".pkg", ".elf", ".self"),
        env_var="FREEDECKCY_RPCS3_BIN",
        notes="RPCS3 官方 AppImage（仅 x86_64）；需要 PS3 固件",
        min_bytes=60 * 1024 * 1024,
        state_key="rpcs3",
        setup_required=True,
        setup_hint="PS3 需要固件：请在 RPCS3 首次启动时安装 PS3UPDAT.PUP",
    ),
    "switch": EmulatorSpec(
        platform="switch",
        name="Eden",
        adapter="eden",
        repo="eden-emu/eden",
        download_base="https://stable.eden-emu.dev/v0.2.1",
        assets={
            "x86_64": "Eden-Linux-v0.2.1-amd64-gcc-standard.AppImage",
            "aarch64": "Eden-Linux-v0.2.1-aarch64-gcc-standard.AppImage",
        },
        archive="appimage",
        launch_args=("{rom}",),
        rom_extensions=(".nsp", ".xci"),
        env_var="FREEDECKCY_EDEN_BIN",
        notes="Eden 官方 AppImage（x64/arm64）；需要 prod.keys 与固件",
        min_bytes=50 * 1024 * 1024,
        state_key="eden",
        setup_required=True,
        setup_hint="Switch 需要 prod.keys 与固件：请在 Eden 首次启动时配置（keys 放 Eden 数据目录）",
    ),
}


def available_platforms(arch: str = "") -> Tuple[str, ...]:
    """当前架构有官方包的平台列表。"""
    target = arch or runtime_arch()
    return tuple(platform for platform, spec in EMULATORS.items() if target in spec.assets)

SUPPORTED_PLATFORMS: Tuple[str, ...] = tuple(EMULATORS.keys())



def runtime_arch() -> str:
    machine = str(platform.machine() or "").strip().lower()
    if machine in {"x86_64", "amd64"}:
        return "x86_64"
    if machine in {"aarch64", "arm64"}:
        return "aarch64"
    return machine


def get_spec(platform_name: str) -> Optional[EmulatorSpec]:
    return EMULATORS.get(str(platform_name or "").strip().lower())


def emulator_name_for_platform(platform_name: str) -> str:
    spec = get_spec(platform_name)
    return spec.adapter if spec else ""


def supported_platforms() -> Tuple[str, ...]:
    return SUPPORTED_PLATFORMS


def emulator_state_dir() -> Path:
    return Path(config.DECKY_SEND_DIR) / "emulators"


def _state_root(spec: EmulatorSpec, arch: str = "") -> Path:
    return emulator_state_dir() / (spec.state_key or spec.platform) / (arch or runtime_arch())


def _legacy_state_root(arch: str = "") -> Path:
    """mGBA 旧版解包目录：~/.local/share/freedeckCY/emulators/<arch>/。"""
    return emulator_state_dir() / (arch or runtime_arch())


def _find_binary(root: Path) -> Optional[str]:
    for candidate in (
        root / "AppRun",
        root / "usr" / "bin" / "mgba",
        root / "usr" / "bin" / "mgba-qt",
        root / "usr" / "bin" / "ppsspp",
        root / "usr" / "bin" / "PPSSPP",
        root / "usr" / "bin" / "melonDS",
        root / "usr" / "bin" / "melonds",
    ):
        if candidate.is_file():
            return str(candidate)
    bin_dir = root / "usr" / "bin"
    if bin_dir.is_dir():
        for path in sorted(bin_dir.iterdir()):
            if path.is_file() and os.access(path, os.X_OK) and path.suffix.lower() not in {".so", ".dll"}:
                return str(path)
    if root.is_dir():
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".appimage", ".bin"}:
                return str(path)
    return None


def _find_spec_executable(spec: EmulatorSpec, root: Path) -> Optional[str]:
    if not root.is_dir():
        return None
    for name in spec.executables:
        for path in root.rglob(name):
            if path.is_file():
                try:
                    os.chmod(path, 0o755)
                except Exception:
                    pass
                return str(path)
    return None


def installed_command(spec: EmulatorSpec, arch: str = "") -> Optional[str]:
    roots = [_state_root(spec, arch)]
    if spec.platform == "gba":
        roots.append(_legacy_state_root(arch))
    for root in roots:
        found = _find_spec_executable(spec, root)
        if found:
            return found
        found = _find_binary(root / "squashfs-root")
        if found:
            return found
    return None


def system_command(spec: EmulatorSpec) -> Optional[str]:
    names = {
        "mgba": ("mgba", "mgba-qt"),
        "ppsspp": ("ppsspp", "PPSSPP", "ppsspp-sdl"),
        "melonds": ("melonds", "melonDS"),
        "duckstation": ("duckstation", "DuckStation", "duckstation-qt"),
        "mesen": ("Mesen", "mesen"),
    }.get(spec.adapter, ())
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def flatpak_command(spec: EmulatorSpec) -> Optional[List[str]]:
    if spec.platform != "gba":
        return None
    if not shutil.which("flatpak"):
        return None
    try:
        result = subprocess.run(
            ["flatpak", "info", "io.mgba.mGBA"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
        )
    except Exception:
        return None
    return ["flatpak", "run", "io.mgba.mGBA"] if result.returncode == 0 else None


_FLATPAK_CACHE: Dict[str, Tuple[float, bool]] = {}


def _is_steamos() -> bool:
    try:
        text = Path("/etc/os-release").read_text(encoding="utf-8", errors="replace").lower()
    except Exception:
        return False
    return "id=steamos" in text or "steamos" in text


def _flatpak_binary() -> str:
    return shutil.which("flatpak") or ""


def flatpak_installed(app_id: str, *, max_age: float = 30.0) -> bool:
    app_id = str(app_id or "").strip()
    binary = _flatpak_binary()
    if not app_id or not binary:
        return False
    now = time.monotonic()
    cached = _FLATPAK_CACHE.get(app_id)
    if cached and now - cached[0] < max_age:
        return cached[1]
    try:
        result = subprocess.run(
            [binary, "info", app_id],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
        installed = result.returncode == 0
    except Exception:
        installed = False
    _FLATPAK_CACHE[app_id] = (now, installed)
    return installed


async def _run_flatpak(args: Sequence[str], *, timeout: float = 600.0) -> Tuple[int, str]:
    try:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            output, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return 124, "flatpak 操作超时"
        return int(process.returncode or 0), (output or b"").decode("utf-8", "replace")
    except Exception as exc:
        return 1, str(exc)


async def _ensure_flatpak(spec: EmulatorSpec, *, allow_download: bool) -> Optional[List[str]]:
    """优先使用官方 Flatpak；SteamOS 上可自动安装，避免 AppImage glibc 兼容问题。"""
    if not spec.flatpak_id:
        return None
    binary = _flatpak_binary()
    if not binary:
        return None
    if flatpak_installed(spec.flatpak_id):
        return [binary, "run", spec.flatpak_id]
    if not allow_download:
        return None

    config.logger.info("Installing Flatpak %s for %s", spec.flatpak_id, spec.name)
    await _run_flatpak(
        [binary, "remote-add", "--user", "--if-not-exists", "flathub", "https://flathub.org/repo/flathub.flatpakrepo"],
        timeout=120,
    )
    code, output = await _run_flatpak(
        [binary, "install", "-y", "--user", "flathub", spec.flatpak_id],
        timeout=1200,
    )
    if code != 0:
        config.logger.warning("Flatpak user install failed for %s: %s", spec.flatpak_id, output[-500:])
        code, output = await _run_flatpak(
            [binary, "install", "-y", "flathub", spec.flatpak_id],
            timeout=1200,
        )
    if flatpak_installed(spec.flatpak_id, max_age=0):
        return [binary, "run", spec.flatpak_id]
    if code != 0:
        config.logger.warning("Flatpak install failed for %s: %s", spec.flatpak_id, output[-500:])
    return None


def resolve_command(spec: EmulatorSpec, plugin_dir: str = "") -> Optional[List[str]]:
    env_path = str(os.getenv(spec.env_var, "") or "").strip()
    if env_path and os.path.isfile(env_path):
        return [env_path]
    if spec.flatpak_id and flatpak_installed(spec.flatpak_id):
        return [_flatpak_binary(), "run", spec.flatpak_id]
    installed = installed_command(spec)
    if installed:
        return [installed]
    system = system_command(spec)
    if system:
        return [system]
    return flatpak_command(spec)


def bios_dir(platform_name: str) -> Path:
    return Path(config.DECKY_SEND_DIR) / "bios" / str(platform_name)


def bios_present(platform_name: str) -> bool:
    root = bios_dir(platform_name)
    if not root.is_dir():
        return False
    return any(
        path.is_file() and path.suffix.lower() in {".bin", ".rom"}
        for path in root.iterdir()
    )


def prepare_bios(spec: EmulatorSpec) -> List[str]:
    """把用户 BIOS 拷到模拟器默认目录（目前仅 PS1/DuckStation）。"""
    if not spec.bios_required:
        return []
    source = bios_dir(spec.platform)
    if not source.is_dir():
        return [f"未找到 BIOS 目录: {source}"]
    messages: List[str] = []
    if spec.platform == "ps1":
        target = Path.home() / ".local" / "share" / "duckstation" / "bios"
        target.mkdir(parents=True, exist_ok=True)
        copied = 0
        for path in source.iterdir():
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".bin", ".rom"}:
                continue
            destination = target / path.name
            if destination.is_file():
                continue
            try:
                shutil.copy2(path, destination)
                copied += 1
            except Exception as exc:
                messages.append(f"复制 BIOS 失败 {path.name}: {exc}")
        if copied:
            messages.append(f"已复制 {copied} 个 BIOS 到 {target}")
        elif not any(target.iterdir()):
            messages.append(f"未找到可用的 PS1 BIOS（请把 scph*.bin 放到 {source}）")
    elif spec.platform == "ps2":
        targets = [
            Path.home() / ".local" / "share" / "PCSX2" / "bios",
            Path.home() / ".config" / "PCSX2" / "bios",
        ]
        copied = 0
        for target in targets:
            target.mkdir(parents=True, exist_ok=True)
            for path in source.iterdir():
                if not path.is_file() or path.suffix.lower() not in {".bin", ".rom"}:
                    continue
                destination = target / path.name
                if destination.is_file():
                    continue
                try:
                    shutil.copy2(path, destination)
                    copied += 1
                except Exception as exc:
                    messages.append(f"复制 BIOS 失败 {path.name}: {exc}")
        if copied:
            messages.append(f"已复制 {copied} 个 PS2 BIOS")
        elif not any(target.is_dir() and any(target.iterdir()) for target in targets):
            messages.append(f"未找到可用的 PS2 BIOS（请把 *.bin 放到 {source}）")
    return messages


def emulator_status(platform_name: str, plugin_dir: str = "") -> Dict[str, Any]:
    spec = get_spec(platform_name)
    if spec is None:
        return {
            "available": False,
            "source": "",
            "message": f"暂不支持 {str(platform_name).upper()} 平台",
        }
    command = resolve_command(spec, plugin_dir)
    if command:
        env_path = str(os.getenv(spec.env_var, "") or "").strip()
        if env_path and os.path.isfile(env_path):
            source = "env"
        elif installed_command(spec):
            source = "installed"
        elif system_command(spec):
            source = "system"
        else:
            source = "flatpak"
        return {
            "available": True,
            "source": source,
            "command": command[0],
            "name": spec.name,
            "version": spec.download_base.rsplit("/", 1)[-1],
            "notes": spec.notes,
            "bios_required": spec.bios_required,
            "bios_present": bios_present(spec.platform) if spec.bios_required else True,
            "bios_dir": str(bios_dir(spec.platform)) if spec.bios_required else "",
            "setup_required": spec.setup_required,
            "setup_hint": spec.setup_hint,
            "flatpak_id": spec.flatpak_id,
            "flatpak_available": bool(_flatpak_binary()),
            "flatpak_installed": flatpak_installed(spec.flatpak_id) if spec.flatpak_id else False,
        }
    arch = runtime_arch()
    asset = spec.assets.get(arch)
    if not asset:
        return {
            "available": False,
            "source": "",
            "name": spec.name,
            "message": f"当前架构（{arch}）没有 {spec.name} 官方包，已隐藏该平台",
        }
    return {
        "available": True,
        "source": "download",
        "command": "",
        "name": spec.name,
        "requires_setup": True,
        "asset": asset,
        "url": f"{spec.download_base}/{asset}",
        "notes": spec.notes,
        "bios_required": spec.bios_required,
        "bios_present": bios_present(spec.platform) if spec.bios_required else True,
        "bios_dir": str(bios_dir(spec.platform)) if spec.bios_required else "",
        "setup_required": spec.setup_required,
        "setup_hint": spec.setup_hint,
        "flatpak_id": spec.flatpak_id,
        "flatpak_available": bool(_flatpak_binary()),
        "flatpak_installed": flatpak_installed(spec.flatpak_id) if spec.flatpak_id else False,
        "message": (
            f"首次安装会通过官方 Flatpak 安装 {spec.name}（推荐，避开 AppImage 兼容问题）"
            if spec.flatpak_id and _flatpak_binary()
            else f"首次安装会从官方 release 下载 {spec.name}（{asset}）"
        ),
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
        raise RuntimeError(f"解包 AppImage 失败: {message[:300]}")


def _extract_zip_emulator(spec: EmulatorSpec, archive: str, dest_dir: Path) -> str:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(dest_dir)
    for name in spec.executables:
        for path in dest_dir.rglob(name):
            if path.is_file():
                os.chmod(path, 0o755)
                return str(path)
    for path in dest_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() == ".appimage":
            os.chmod(path, 0o755)
            return str(path)
    raise RuntimeError("压缩包内未找到可执行文件")


async def _download_asset(spec: EmulatorSpec, arch: str) -> str:
    asset = spec.assets.get(arch)
    if not asset:
        raise RuntimeError(f"{spec.name} 暂无 {arch} 官方包")
    root = _state_root(spec, arch)
    root.mkdir(parents=True, exist_ok=True)
    target = root / asset
    if target.is_file() and target.stat().st_size >= spec.min_bytes:
        return str(target)

    url = f"{spec.download_base}/{asset}"
    timeout = aiohttp.ClientTimeout(total=1800, sock_read=120)
    part = target.with_name(target.name + ".part")
    try:
        if part.exists():
            part.unlink()
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, allow_redirects=True) as response:
                if int(response.status) != 200:
                    raise RuntimeError(f"下载 {spec.name} 失败: HTTP {int(response.status)}")
                with open(part, "wb") as fh:
                    async for chunk in response.content.iter_chunked(1024 * 256):
                        if chunk:
                            fh.write(chunk)
        if not part.is_file() or part.stat().st_size < spec.min_bytes:
            raise RuntimeError(f"{spec.name} 下载不完整")
        os.replace(part, target)
    except Exception:
        try:
            part.unlink()
        except Exception:
            pass
        raise
    os.chmod(target, 0o755)
    return str(target)


def _ensure_extracted(spec: EmulatorSpec, appimage: str) -> List[str]:
    arch = runtime_arch()
    existing = installed_command(spec, arch)
    if existing:
        return [existing]
    try:
        _run_appimage_extract(appimage, _state_root(spec, arch))
    except Exception as exc:
        # 某些 AppImage 不带 runtime（或当前环境不允许执行），尝试直接运行下载的 AppImage；
        # 记录原因，安装消息仍会走到 Steam 注册，后续启动失败可据此排查。
        config.logger.warning("%s AppImage 解包失败，回退直接运行: %s", spec.name, exc)
        return [appimage]
    found = installed_command(spec, arch)
    if not found:
        raise RuntimeError(f"{spec.name} 解包后未找到可执行文件")
    try:
        os.chmod(found, 0o755)
    except Exception:
        pass
    return [found]


async def ensure_emulator(
    platform_name: str,
    plugin_dir: str = "",
    *,
    allow_download: bool = True,
) -> List[str]:
    spec = get_spec(platform_name)
    if spec is None:
        raise RuntimeError(f"暂不支持 {str(platform_name).upper()} 平台")

    env_override = str(os.getenv(spec.env_var, "") or "").strip() if spec.env_var else ""
    if (
        spec.flatpak_id
        and not (env_override and os.path.isfile(env_override))
        and (flatpak_installed(spec.flatpak_id) or (_is_steamos() and allow_download))
    ):
        flatpak_command = await _ensure_flatpak(spec, allow_download=allow_download)
        if flatpak_command:
            config.logger.info("Using Flatpak %s for %s", spec.flatpak_id, spec.name)
            return flatpak_command

    command = resolve_command(spec, plugin_dir)
    if command:
        first = command[0]
        if first.lower().endswith((".appimage", ".appimage")):
            return _ensure_extracted(spec, first)
        return command

    if not allow_download:
        raise RuntimeError(emulator_status(spec.platform, plugin_dir).get("message", f"{spec.name} 不可用"))

    asset_path = await _download_asset(spec, runtime_arch())
    if spec.archive == "zip":
        executable = _extract_zip_emulator(spec, asset_path, _state_root(spec))
        if executable.lower().endswith(".appimage"):
            return _ensure_extracted(spec, executable)
        return [executable]
    return _ensure_extracted(spec, asset_path)


async def ensure_mgba(plugin_dir: str = "", *, allow_download: bool = True) -> List[str]:
    """兼容旧接口：确保 mGBA 可用。"""
    return await ensure_emulator("gba", plugin_dir, allow_download=allow_download)


def _common_parent(paths: Sequence[Path]) -> Path:
    try:
        common = os.path.commonpath([str(path.parent) for path in paths])
    except Exception:
        common = str(paths[0].parent)
    return Path(common)


def _ps1_game_key(value: str) -> str:
    """去掉 Disc 1/CD2 等碟号后的游戏名，用于平铺目录分组。"""
    import re

    text = Path(str(value or "")).stem.lower()
    text = re.sub(r"\b(?:disc|disk|cd)\s*[-_ ]?\s*\d+\b", "", text)
    text = re.sub(r"[\(\[].*?[\)\]]", "", text)
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", text)


def _natural_disc_key(name: str):
    """Disc 1/2/10、CD1/CD2 自然排序。"""
    import re

    parts = re.split(r"(\d+)", str(name or "").lower())
    return [int(part) if part.isdigit() else part for part in parts]


def find_rom_file(
    target_dir: str,
    open_path: str = "",
    platform_name: str = "gba",
    *,
    strict: bool = False,
    title: str = "",
) -> str:
    spec = get_spec(platform_name)
    if spec is None:
        return ""
    root = Path(target_dir)
    if not root.is_dir():
        return ""
    preference = {ext: idx for idx, ext in enumerate(spec.rom_extensions)}
    roms: List[Path] = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in preference
    ]
    if not roms:
        return ""
    wanted_stem = Path(str(open_path or "").replace("\\", "/")).stem.lower()

    def sort_key(path: Path):
        return (preference.get(path.suffix.lower(), 99), len(str(path)), str(path))

    if wanted_stem and str(platform_name or "").lower() != "ps1":
        exact = [path for path in roms if path.stem.lower() == wanted_stem]
        if exact:
            roms = exact
        elif strict:
            # 扫描/自动注册时不在多个不同 ROM 中随便选第一个，避免注册错游戏。
            distinct_stems = {path.stem.lower() for path in roms}
            if len(distinct_stems) > 1:
                config.logger.warning("ROM 歧义：openpath=%s 未精确匹配，候选 %s", open_path, sorted(distinct_stems)[:8])
                return ""

    if str(platform_name or "").lower() == "ps1":
        playlists = [path for path in roms if path.suffix.lower() == ".m3u"]
        discs = [path for path in roms if path.suffix.lower() in {".cue", ".chd"}]
        wanted_rel = str(open_path or "").replace("\\", "/").strip("/").lower()
        title_keys = {
            _ps1_game_key(part)
            for part in re.split(r"[/|｜]", str(title or ""))
            if _ps1_game_key(part)
        }

        def rel_norm(path: Path) -> str:
            try:
                return os.path.relpath(path, root).replace(os.sep, "/").strip("/").lower()
            except Exception:
                return str(path).replace("\\", "/").strip("/").lower()

        def is_disc_dir(name: str) -> bool:
            return bool(name) and any(token in name.lower() for token in ("disc", "disk", "cd"))

        # 按“游戏根目录 + 去碟号名称”分组，而不是把所有 cue/chd 混在一起。
        groups: Dict[tuple, List[Path]] = {}
        for disc in discs:
            group_dir = disc.parent
            if group_dir != root and is_disc_dir(group_dir.name):
                group_dir = group_dir.parent
            if group_dir == root:
                game_key = _ps1_game_key(disc.stem) or "__discs__"
            else:
                game_key = _ps1_game_key(group_dir.name) or _ps1_game_key(disc.stem) or "__discs__"
            groups.setdefault((rel_norm(group_dir), game_key), []).append(disc)

        def choose_group_by_title(candidates: List[tuple]) -> Optional[tuple]:
            if not title_keys or not candidates:
                return None
            exact = [group_id for group_id, game_key in candidates if game_key in title_keys]
            if len(exact) == 1:
                return exact[0]
            fuzzy = [
                group_id for group_id, game_key in candidates
                if game_key and any(key in game_key or game_key in key for key in title_keys)
            ]
            return fuzzy[0] if len(fuzzy) == 1 else None

        selected: Optional[tuple] = None
        if wanted_rel:
            # 1) openpath 完整相对路径命中碟文件。
            for group_id, items in groups.items():
                if any(rel_norm(item) == wanted_rel for item in items):
                    selected = group_id
                    break
            # 2) openpath 指向目录 / 碟目录。
            if selected is None:
                wanted_parent = os.path.dirname(wanted_rel).strip("/")
                if wanted_rel.endswith((".cue", ".chd", ".bin", ".m3u")):
                    wanted_dir = wanted_parent
                else:
                    wanted_dir = wanted_rel
                dir_matches = [
                    group_id for group_id in groups
                    if group_id[0] == wanted_dir or (wanted_parent and group_id[0] == wanted_parent)
                ]
                if len(dir_matches) == 1:
                    selected = dir_matches[0]
                elif len(dir_matches) > 1:
                    selected = choose_group_by_title(dir_matches)
            # 3) openpath 的碟文件名在多组中出现时，用标题消歧。
            if selected is None:
                matches = [
                    group_id for group_id, items in groups.items()
                    if any(_ps1_game_key(item.stem) == _ps1_game_key(wanted_rel) for item in items)
                ]
                if len(matches) == 1:
                    selected = matches[0]
                elif len(matches) > 1:
                    selected = choose_group_by_title([(group_id, group_id[1]) for group_id in matches])

        # 4) 标题唯一匹配。
        if selected is None and title_keys and groups:
            selected = choose_group_by_title([(group_id, group_id[1]) for group_id in groups])

        # 5) 只有一组才可直接使用；否则明确歧义，不能注册错游戏。
        if selected is None:
            if len(groups) == 1:
                selected = next(iter(groups))
            elif groups:
                config.logger.warning(
                    "PS1 存档/ROM 分组歧义：openpath=%s title=%s groups=%s",
                    open_path,
                    title,
                    sorted(f"{key[1]}@{key[0]}" for key in groups)[:8],
                )
                return ""
            elif len(playlists) == 1:
                return str(playlists[0])
            elif playlists:
                config.logger.warning("PS1 m3u 歧义：openpath=%s title=%s count=%s", open_path, title, len(playlists))
                return ""
            return ""

        discs = groups[selected]
        # 同一张碟同时有 cue/chd 时只保留一个，避免重复行。
        deduped: Dict[tuple, Path] = {}
        for disc in discs:
            key = (str(disc.parent), disc.stem.lower())
            previous = deduped.get(key)
            if previous is None or (previous.suffix.lower() == ".chd" and disc.suffix.lower() == ".cue"):
                deduped[key] = disc
        discs = list(deduped.values())

        if len(discs) > 1:
            parent = _common_parent(discs)
            playlist_key = selected[1] if selected[1] != "__discs__" else ""
            playlist = parent / (f"freedeckcy-{playlist_key}-multidisc.m3u" if playlist_key else "freedeckcy-multidisc.m3u")
            try:
                def disc_key(path: Path):
                    rel = os.path.relpath(path, parent).replace(os.sep, "/")
                    return tuple(_natural_disc_key(part) for part in rel.split("/"))

                lines = ["#EXTM3U"]
                for disc in sorted(discs, key=disc_key):
                    lines.append(os.path.relpath(disc, parent).replace(os.sep, "/"))
                playlist.write_text("\n".join(lines) + "\n", encoding="utf-8")
                config.logger.info("PS1 multi-disc playlist generated: %s (%d discs)", playlist, len(discs))
                return str(playlist)
            except Exception as exc:
                config.logger.warning("PS1 m3u 生成失败，回退单碟: %s", exc)

        if playlists:
            matching = [
                path for path in playlists
                if rel_norm(path.parent) == selected[0]
                and (not selected[1] or selected[1] == "__discs__" or selected[1] in _ps1_game_key(path.stem))
            ]
            if len(matching) == 1:
                return str(matching[0])
            if len(matching) > 1:
                config.logger.warning("PS1 m3u 歧义：openpath=%s title=%s matching=%s", open_path, title, [path.name for path in matching[:8]])
                return ""
            if len(playlists) == 1:
                return str(playlists[0])
        return str(sorted(discs, key=sort_key)[0])
    return str(sorted(roms, key=sort_key)[0])


def create_launch_wrapper(
    *,
    command: Sequence[str],
    rom_path: str,
    wrapper_path: str,
    platform_name: str = "gba",
) -> str:
    spec = get_spec(platform_name)
    argv = [str(part) for part in command if str(part)]
    if not argv:
        raise ValueError("模拟器启动命令为空")

    args: List[str] = []
    used_rom = False
    for token in (spec.launch_args if spec else ("{rom}",)):
        if "{rom}" in token:
            used_rom = True
            args.append(token.replace("{rom}", str(rom_path)))
        else:
            args.append(token)
    if not used_rom:
        args.append(str(rom_path))

    env_lines = ""
    if platform_name == "3ds":
        # SteamOS/Game Mode 下强制 XWayland，避开 Azahar Wayland 后端的兼容问题。
        env_lines = "export QT_QPA_PLATFORM=xcb\nexport SDL_VIDEODRIVER=x11\n"
    # portable.ini / qt.ini 写在可执行文件所在目录；部分模拟器按 cwd 探测 portable 模式。
    cwd_line = ""
    command_dir = os.path.dirname(os.path.realpath(os.path.expanduser(argv[0])))
    if command_dir and os.path.isdir(command_dir) and os.path.basename(argv[0]) != "flatpak":
        cwd_line = f"cd {shlex.quote(command_dir)}\n"
    script = (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        + env_lines
        + cwd_line
        + 'exec ' + " ".join(shlex.quote(part) for part in [*argv, *args]) + "\n"
    )
    wrapper = Path(wrapper_path)
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    wrapper.write_text(script, encoding="utf-8")
    os.chmod(wrapper, 0o755)
    return str(wrapper)
