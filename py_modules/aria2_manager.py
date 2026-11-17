# aria2_manager.py - aria2 进程与 RPC 管理
#
# 该模块负责启动/复用 aria2、执行 RPC、同步状态。
#
# 与 v0.6 对齐的两个关键点：
# 1. 运行时元数据（rpc_url/secret/pid）落盘 + flock 所有权锁：
#    插件重载后可以附着到仍然存活的 aria2，避免 gid 丢失和重复下载；
# 2. `aria2.changeUri`：直链过期时原地换链，保留 gid 与已下载进度。

from __future__ import annotations

import asyncio
import json
import os
import platform
import shutil
import socket
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

import config

try:
    import fcntl
except Exception:  # pragma: no cover - 非 Linux 平台
    fcntl = None  # type: ignore[assignment]


ARIA2_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.6478.183 Safari/537.36"
)
ARIA2_MAX_TRIES = "10"
ARIA2_RETRY_WAIT = "5"
ARIA2_CONNECT_TIMEOUT = "10"
ARIA2_READ_TIMEOUT = "60"


@dataclass
class Aria2Runtime:
    """运行中的 aria2 信息。"""

    process: Optional[subprocess.Popen]
    rpc_url: str
    rpc_secret: str
    binary_path: str
    started_at: int
    pid: int = 0
    owned: bool = True


class Aria2Error(RuntimeError):
    """aria2 相关异常。"""


def _pick_free_port() -> int:
    """申请本机空闲端口。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _is_alive(proc: Optional[subprocess.Popen]) -> bool:
    """判断进程是否仍在运行。"""
    return bool(proc and proc.poll() is None)


def _is_pid_alive(pid: int) -> bool:
    """判断 pid 是否仍然存活（用于附着到其它实例启动的 aria2）。"""
    if int(pid or 0) <= 0:
        return False
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False
    return True


def _now_ts() -> int:
    """返回当前秒级时间戳。"""
    return int(time.time())


class Aria2Manager:
    """aria2 进程管理器。"""

    def __init__(self, plugin_dir: str, work_dir: str):
        self._plugin_dir = plugin_dir
        self._work_dir = work_dir
        self._lock = threading.RLock()
        self._runtime: Optional[Aria2Runtime] = None
        self._runtime_meta_path = os.path.join(work_dir, "aria2-runtime.json")
        self._runtime_lock_path = os.path.join(work_dir, "aria2-runtime.lock")
        self._runtime_lock_fp: Optional[Any] = None

    def _resolve_binary_path(self) -> str:
        """优先解析内置 aria2，可回退系统命令。"""
        # 兼容历史拼写：早期版本环境变量名是 FRIENDECK_ARIA2_BIN。
        for env_name in ("FREEDECKCY_ARIA2_BIN", "FRIENDECK_ARIA2_BIN"):
            env_path = (os.getenv(env_name) or "").strip()
            if env_path and os.path.isfile(env_path):
                return env_path

        root = Path(self._plugin_dir)
        machine = platform.machine().lower()
        if machine in {"x86_64", "amd64"}:
            arch = "x86_64"
        elif machine in {"aarch64", "arm64"}:
            arch = "aarch64"
        else:
            arch = machine

        # 首选 scripts/fetch_runtime.sh 落地的统一运行时目录。
        candidates: List[Path] = [
            root / "defaults" / "runtime" / "aria2" / arch / "aria2c",
            root / "defaults" / "runtime" / "aria2" / "aria2c",
        ]

        if arch == "x86_64":
            candidates.append(root / "defaults" / "aria2" / "linux-x64" / "aria2c")
        if arch == "aarch64":
            candidates.append(root / "defaults" / "aria2" / "linux-arm64" / "aria2c")

        candidates.extend(
            [
                root / "defaults" / "aria2" / "aria2c",
                root / "defaults" / "aria2c",
            ]
        )

        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)

        system_path = shutil.which("aria2c")
        if system_path:
            return system_path
        raise Aria2Error(
            "下载组件不可用：未找到内置 aria2c 或系统 aria2c。"
            "请先执行 `make runtime`，或用 FREEDECKCY_ARIA2_BIN 指定路径"
        )

    # ------------------------------------------------------------------
    # 运行时元数据：插件重载后复用同一个 aria2 进程
    # ------------------------------------------------------------------

    def _read_runtime_meta(self) -> Optional[Aria2Runtime]:
        try:
            with open(self._runtime_meta_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        rpc_url = str(payload.get("rpc_url", "") or "").strip()
        rpc_secret = str(payload.get("rpc_secret", "") or "").strip()
        if not rpc_url or not rpc_secret:
            return None
        return Aria2Runtime(
            process=None,
            rpc_url=rpc_url,
            rpc_secret=rpc_secret,
            binary_path=str(payload.get("binary_path", "") or "").strip(),
            started_at=int(payload.get("started_at") or 0),
            pid=int(payload.get("pid") or 0),
            owned=False,
        )

    def _write_runtime_meta(self, runtime: Aria2Runtime) -> None:
        try:
            os.makedirs(self._work_dir, exist_ok=True)
            payload = {
                "rpc_url": runtime.rpc_url,
                "rpc_secret": runtime.rpc_secret,
                "binary_path": runtime.binary_path,
                "started_at": int(runtime.started_at or 0),
                "pid": int(runtime.pid or 0),
            }
            tmp_path = f"{self._runtime_meta_path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False)
            os.replace(tmp_path, self._runtime_meta_path)
        except Exception as exc:
            config.logger.warning("写入 aria2 运行时元数据失败: %s", exc)

    def _clear_runtime_meta(self) -> None:
        try:
            os.remove(self._runtime_meta_path)
        except FileNotFoundError:
            pass
        except Exception:
            pass

    def _try_acquire_owner_lock(self) -> bool:
        """同 work_dir 只允许一个实例负责启动 aria2。"""
        if self._runtime_lock_fp is not None:
            return True
        try:
            os.makedirs(self._work_dir, exist_ok=True)
            lock_fp = open(self._runtime_lock_path, "a+", encoding="utf-8")
        except Exception:
            # 锁文件不可用时不阻塞启动。
            return True
        if fcntl is not None:
            try:
                fcntl.flock(lock_fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except Exception:
                lock_fp.close()
                return False
        self._runtime_lock_fp = lock_fp
        return True

    def _release_owner_lock(self) -> None:
        lock_fp = self._runtime_lock_fp
        self._runtime_lock_fp = None
        if lock_fp is None:
            return
        try:
            if fcntl is not None:
                fcntl.flock(lock_fp.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            lock_fp.close()
        except Exception:
            pass

    def _runtime_looks_alive(self, runtime: Optional[Aria2Runtime]) -> bool:
        if runtime is None:
            return False
        if runtime.process is not None:
            return _is_alive(runtime.process)
        if int(runtime.pid or 0) > 0:
            return _is_pid_alive(int(runtime.pid))
        return True

    async def _attach_existing(self) -> Optional[Aria2Runtime]:
        """附着到元数据里记录的、仍然存活的 aria2 实例。"""
        runtime = self._read_runtime_meta()
        if runtime is None:
            return None
        if not self._runtime_looks_alive(runtime):
            self._clear_runtime_meta()
            return None
        with self._lock:
            self._runtime = runtime
        try:
            await self._rpc_call("aria2.getVersion", [])
        except Exception as exc:
            config.logger.info("附着已有 aria2 失败，将重新启动: %s", exc)
            with self._lock:
                if self._runtime is runtime:
                    self._runtime = None
            self._clear_runtime_meta()
            return None
        config.logger.info("已附着到运行中的 aria2: %s", runtime.rpc_url)
        return runtime

    def _start_process(self) -> Aria2Runtime:
        """启动 aria2 进程。"""
        binary_path = self._resolve_binary_path()
        os.makedirs(self._work_dir, exist_ok=True)
        try:
            mode = os.stat(binary_path).st_mode
            if mode & 0o111 == 0:
                os.chmod(binary_path, mode | 0o755)
        except Exception:
            # 权限设置失败不立即中断，让后续启动给出真实报错。
            pass

        port = _pick_free_port()
        rpc_secret = uuid.uuid4().hex
        session_file = os.path.join(self._work_dir, "aria2.session")
        input_file = session_file if os.path.exists(session_file) else "/dev/null"

        args = [
            binary_path,
            "--enable-rpc=true",
            "--rpc-listen-all=false",
            "--rpc-allow-origin-all=true",
            "--rpc-listen-port",
            str(port),
            "--rpc-secret",
            rpc_secret,
            "--dir",
            self._work_dir,
            "--continue=true",
            "--max-concurrent-downloads=3",
            # SD 卡/exFAT 上预分配很慢，直接关掉
            "--file-allocation=none",
            "--check-certificate=true",
            f"--connect-timeout={ARIA2_CONNECT_TIMEOUT}",
            f"--timeout={ARIA2_READ_TIMEOUT}",
            f"--retry-wait={ARIA2_RETRY_WAIT}",
            f"--max-tries={ARIA2_MAX_TRIES}",
            "--input-file",
            input_file,
            "--save-session",
            session_file,
            "--save-session-interval=15",
            "--auto-file-renaming=false",
            "--allow-overwrite=true",
            "--daemon=false",
            "--summary-interval=0",
            "--log",
            os.path.join(self._work_dir, "aria2.log"),
            "--log-level=notice",
        ]

        for candidate in (
            "/etc/ssl/certs/ca-certificates.crt",
            "/etc/pki/tls/certs/ca-bundle.crt",
            "/etc/ssl/cert.pem",
        ):
            if os.path.isfile(candidate):
                args.extend(["--ca-certificate", candidate])
                break

        proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=self._work_dir,
        )

        return Aria2Runtime(
            process=proc,
            rpc_url=f"http://127.0.0.1:{port}/jsonrpc",
            rpc_secret=rpc_secret,
            binary_path=binary_path,
            started_at=_now_ts(),
            pid=int(getattr(proc, "pid", 0) or 0),
            owned=True,
        )

    async def _rpc_call(self, method: str, params: Optional[List[Any]] = None) -> Any:
        """调用 aria2 JSON-RPC。"""
        with self._lock:
            runtime = self._runtime
        if not self._runtime_looks_alive(runtime):
            raise Aria2Error("aria2 未运行")

        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": str(_now_ts()),
            "method": method,
            "params": [f"token:{runtime.rpc_secret}"] + (params or []),
        }
        timeout = aiohttp.ClientTimeout(total=12)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(runtime.rpc_url, json=payload) as resp:
                if resp.status >= 400:
                    text = (await resp.text())[:240]
                    raise Aria2Error(f"aria2 rpc 请求失败 status={resp.status} body={text}")
                try:
                    data = await resp.json(content_type=None)
                except Exception as exc:
                    text = (await resp.text())[:240]
                    raise Aria2Error(f"aria2 rpc 解析失败: {exc}; body={text}") from exc

        if not isinstance(data, dict):
            raise Aria2Error("aria2 rpc 响应格式异常")
        if data.get("error"):
            err = data.get("error")
            if isinstance(err, dict):
                message = str(err.get("message", "unknown"))
                code = err.get("code")
                raise Aria2Error(f"aria2 rpc 错误 code={code} message={message}")
            raise Aria2Error("aria2 rpc 返回错误")
        return data.get("result")

    async def ensure_running(self) -> Dict[str, str]:
        """确保 aria2 可用：复用运行中的实例，必要时才启动。"""
        with self._lock:
            runtime = self._runtime

        if runtime is not None and self._runtime_looks_alive(runtime):
            try:
                await self._rpc_call("aria2.getVersion", [])
                if runtime.owned:
                    self._write_runtime_meta(runtime)
                return {
                    "rpc_url": runtime.rpc_url,
                    "binary_path": runtime.binary_path,
                    "attached": not runtime.owned,
                }
            except Exception:
                with self._lock:
                    if self._runtime is runtime:
                        self._runtime = None
                if runtime.owned:
                    self._clear_runtime_meta()
                    proc = runtime.process
                    if _is_alive(proc):
                        try:
                            proc.terminate()  # type: ignore[union-attr]
                            proc.wait(timeout=2.0)  # type: ignore[union-attr]
                        except Exception:
                            try:
                                proc.kill()  # type: ignore[union-attr]
                            except Exception:
                                pass

        # 插件重载后：旧进程可能仍然活着，直接复用。
        attached = await self._attach_existing()
        if attached is not None:
            return {
                "rpc_url": attached.rpc_url,
                "binary_path": attached.binary_path,
                "attached": True,
            }

        # 同 work_dir 只允许一个实例启动 aria2，避免起出两个进程。
        if not self._try_acquire_owner_lock():
            for _ in range(20):
                await _sleep_short()
                attached = await self._attach_existing()
                if attached is not None:
                    return {
                        "rpc_url": attached.rpc_url,
                        "binary_path": attached.binary_path,
                        "attached": True,
                    }
            raise Aria2Error("aria2 正在被其它插件实例启动，请稍后重试")

        try:
            runtime = self._start_process()
            with self._lock:
                self._runtime = runtime
            self._write_runtime_meta(runtime)
        except Exception:
            self._release_owner_lock()
            raise

        last_error = ""
        for _ in range(25):
            try:
                await self._rpc_call("aria2.getVersion", [])
                return {
                    "rpc_url": runtime.rpc_url,
                    "binary_path": runtime.binary_path,
                    "attached": False,
                }
            except Exception as exc:
                last_error = str(exc)
                await _sleep_short()

        self._release_owner_lock()
        proc = runtime.process
        if _is_alive(proc):
            try:
                proc.terminate()  # type: ignore[union-attr]
                proc.wait(timeout=2.0)  # type: ignore[union-attr]
            except Exception:
                try:
                    proc.kill()  # type: ignore[union-attr]
                except Exception:
                    pass
        raise Aria2Error(f"下载组件不可用，aria2 启动失败: {last_error}")

    async def add_uri(
        self,
        direct_url: str,
        cookie: str,
        download_dir: str,
        out_name: str,
        split: int,
        *,
        referer: str = "",
        user_agent: str = "",
    ) -> str:
        """创建下载任务并返回 gid。"""
        split = max(1, min(64, int(split)))
        await self.ensure_running()

        header_map: Dict[str, str] = {
            "User-Agent": str(user_agent or "").strip() or ARIA2_DEFAULT_USER_AGENT,
            "Referer": str(referer or "").strip() or "https://cloud.189.cn/",
        }
        cookie_text = str(cookie or "").strip()
        if cookie_text:
            header_map["Cookie"] = cookie_text
        headers = [f"{key}: {value}" for key, value in header_map.items()]

        options = {
            "dir": download_dir,
            "out": out_name,
            "header": headers,
            "split": str(split),
            "max-connection-per-server": str(split),
            "min-split-size": "1M",
            "continue": "true",
            "allow-overwrite": "true",
            "auto-file-renaming": "false",
            "connect-timeout": ARIA2_CONNECT_TIMEOUT,
            "timeout": ARIA2_READ_TIMEOUT,
            "retry-wait": ARIA2_RETRY_WAIT,
            "max-tries": ARIA2_MAX_TRIES,
            "max-file-not-found": ARIA2_MAX_TRIES,
        }
        result = await self._rpc_call("aria2.addUri", [[direct_url], options])
        gid = str(result or "").strip()
        if not gid:
            raise Aria2Error("aria2.addUri 返回空 gid")
        return gid

    async def get_uris(self, gid: str) -> List[str]:
        """读取任务当前使用的直链列表。"""
        result = await self._rpc_call("aria2.getUris", [gid])
        uris: List[str] = []
        for item in list(result or []):
            if not isinstance(item, dict):
                continue
            uri = str(item.get("uri", "") or "").strip()
            if uri:
                uris.append(uri)
        return uris

    async def replace_uri(self, gid: str, direct_url: str) -> None:
        """原地替换直链（用于直链过期/换线路），保留 gid 与已下载进度。"""
        url = str(direct_url or "").strip()
        if not url:
            raise Aria2Error("replace_uri 直链为空")
        uris = await self.get_uris(gid)
        # fileIndex 从 1 开始，单文件下载通常为 1。
        await self._rpc_call("aria2.changeUri", [gid, 1, uris, [url], 0])

    async def tell_status(self, gid: str) -> Dict[str, Any]:
        """查询任务状态。"""
        keys = [
            "status",
            "totalLength",
            "completedLength",
            "downloadSpeed",
            "errorMessage",
            "errorCode",
        ]
        result = await self._rpc_call("aria2.tellStatus", [gid, keys])
        if not isinstance(result, dict):
            raise Aria2Error("aria2.tellStatus 返回格式异常")
        return result

    async def list_downloads(self, *, max_stopped: int = 500) -> List[Dict[str, Any]]:
        """列出 aria2 当前所有下载（active / waiting / stopped）。

        插件重载或设备重启后 aria2 会用 `--save-session` 重新拉起下载，但 gid 会变，
        这里提供全量列表给上层按文件路径重新认领任务。
        """
        keys = [
            "gid",
            "status",
            "files",
            "dir",
            "totalLength",
            "completedLength",
            "downloadSpeed",
            "errorMessage",
        ]
        items: List[Dict[str, Any]] = []

        try:
            active = await self._rpc_call("aria2.tellActive", [keys])
            if isinstance(active, list):
                items.extend(item for item in active if isinstance(item, dict))
        except Aria2Error:
            pass

        for method in ("aria2.tellWaiting", "aria2.tellStopped"):
            offset = 0
            page_size = 100
            while offset < max_stopped:
                try:
                    page = await self._rpc_call(method, [offset, page_size, keys])
                except Aria2Error:
                    break
                if not isinstance(page, list) or not page:
                    break
                items.extend(item for item in page if isinstance(item, dict))
                if len(page) < page_size:
                    break
                offset += len(page)
        return items

    async def pause(self, gid: str) -> None:
        """暂停任务。"""
        await self._rpc_call("aria2.forcePause", [gid])

    async def resume(self, gid: str) -> None:
        """恢复任务。"""
        await self._rpc_call("aria2.unpause", [gid])

    async def remove(self, gid: str) -> None:
        """移除任务。"""
        try:
            await self._rpc_call("aria2.remove", [gid])
        except Exception:
            pass
        try:
            await self._rpc_call("aria2.removeDownloadResult", [gid])
        except Exception:
            pass

    def stop(self) -> None:
        """停止 aria2 进程（只停止自己启动的实例）。"""
        with self._lock:
            runtime = self._runtime
            self._runtime = None

        if runtime is not None and runtime.owned:
            self._clear_runtime_meta()
        self._release_owner_lock()

        if runtime is None or not runtime.owned:
            return
        proc = runtime.process
        if _is_alive(proc):
            try:
                proc.terminate()  # type: ignore[union-attr]
                proc.wait(timeout=2.0)  # type: ignore[union-attr]
            except Exception:
                try:
                    proc.kill()  # type: ignore[union-attr]
                except Exception:
                    pass


async def _sleep_short() -> None:
    """短暂等待，避免启动探测忙等。"""
    await asyncio.sleep(0.2)
