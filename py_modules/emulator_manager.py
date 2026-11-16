"""模拟器运行时注册表与启动封装（GBA / PSP / NDS）。

设计：
  - 每个平台一条 EmulatorSpec（官方 release 资产、启动参数、ROM 扩展名）。
  - GBA（mGBA）默认随包内置；PSP（PPSSPP）/ NDS（melonDS）首次安装时按需下载官方 AppImage。
  - AppImage 统一用 `--appimage-extract` 解包运行，不依赖 FUSE（DroidDeck/proot 可用）。
  - 启动脚本由安装流程生成，Steam 快捷方式不写 Proton 映射。
"""

from __future__ import annotations

import asyncio
import os
import platform
import shlex
import shutil
import subprocess
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
        rom_extensions=(".cue", ".m3u", ".chd", ".iso", ".pbp", ".bin"),
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
        rom_extensions=(".3ds", ".cia", ".cci", ".cxi", ".app"),
        env_var="FREEDECKCY_AZAHAR_BIN",
        notes="Azahar 官方 AppImage（仅 x86_64）；需要 3DS system files",
        min_bytes=60 * 1024 * 1024,
        state_key="azahar",
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


def resolve_command(spec: EmulatorSpec, plugin_dir: str = "") -> Optional[List[str]]:
    env_path = str(os.getenv(spec.env_var, "") or "").strip()
    if env_path and os.path.isfile(env_path):
        return [env_path]
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
        "message": f"首次安装会从官方 release 下载 {spec.name}（{asset}）",
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
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, allow_redirects=True) as response:
            if int(response.status) != 200:
                raise RuntimeError(f"下载 {spec.name} 失败: HTTP {int(response.status)}")
            with open(target, "wb") as fh:
                async for chunk in response.content.iter_chunked(1024 * 256):
                    if chunk:
                        fh.write(chunk)
    if not target.is_file() or target.stat().st_size < spec.min_bytes:
        try:
            target.unlink()
        except Exception:
            pass
        raise RuntimeError(f"{spec.name} 下载不完整")
    os.chmod(target, 0o755)
    return str(target)


def _ensure_extracted(spec: EmulatorSpec, appimage: str) -> List[str]:
    arch = runtime_arch()
    existing = installed_command(spec, arch)
    if existing:
        return [existing]
    try:
        _run_appimage_extract(appimage, _state_root(spec, arch))
    except Exception:
        # 某些 AppImage 不带 runtime（或当前环境不允许执行），尝试直接运行下载的 AppImage
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


def find_rom_file(target_dir: str, open_path: str = "", platform_name: str = "gba") -> str:
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

    if wanted_stem:
        exact = [path for path in roms if path.stem.lower() == wanted_stem]
        if exact:
            return str(sorted(exact, key=sort_key)[0])
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

    script = (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'exec ' + " ".join(shlex.quote(part) for part in [*argv, *args]) + "\n"
    )
    wrapper = Path(wrapper_path)
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    wrapper.write_text(script, encoding="utf-8")
    os.chmod(wrapper, 0o755)
    return str(wrapper)
