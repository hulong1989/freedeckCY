"""全模拟测试替身：aria2 / 7z / Steam shortcut / 天翼云盘 / 模拟器。

目标是不联网、不执行 Linux 二进制，也能跑通安装、故障、恢复、云存档链路。

约定：
- 真实 ``Aria2Manager`` 的错误都是 :class:`aria2_manager.Aria2Error`，假 aria2 也必须
  抛同一类型，否则 ``tianyi_service.refresh_tasks`` 的 ``except Aria2Error`` 分支不会被覆盖。
- 真实 ``SevenZipManager`` 用 zip 系命令，这里统一用 ``zipfile`` 模拟；分卷 ``.001``
  文件可以是合法 zip，``extract_archive`` 不关心扩展名。
"""

from __future__ import annotations

import fnmatch
import json
import os
import struct
import zipfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from aria2_manager import Aria2Error
from seven_zip_manager import SevenZipError
from tianyi_client import TianyiApiError


# ---------------------------------------------------------------------------
# 归档构造工具
# ---------------------------------------------------------------------------


def write_zip_archive(archive_path: Union[str, Path], entries: Mapping[str, Union[bytes, str]]) -> str:
    """按 ``arcname -> content`` 写一个合法 zip（模拟 7z 包）。"""
    path = Path(archive_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        for arcname, content in entries.items():
            data = content.encode("utf-8") if isinstance(content, str) else content
            zf.writestr(arcname, data)
    return str(path)


def corrupt_archive(path: Union[str, Path], *, keep_bytes: int = 40, marker: bytes = b"\x00CORRUPTED-BY-SIM") -> str:
    """把归档改成损坏文件（保留一小段合法头，让 ``7z t``/zipfile 解压失败）。"""
    target = Path(path)
    try:
        raw = target.read_bytes()
    except Exception:
        raw = b""
    target.write_bytes(raw[: max(0, int(keep_bytes))] + marker)
    return str(target)


def archive_names(archive_path: Union[str, Path]) -> List[str]:
    """列出 zip 归档内条目名；损坏归档返回空列表。"""
    try:
        with zipfile.ZipFile(archive_path) as zf:
            return zf.namelist()
    except Exception:
        return []


def read_archive_manifest(archive_path: Union[str, Path]) -> Dict[str, Any]:
    """读取归档根目录的 manifest.json；不存在返回空 dict。"""
    try:
        with zipfile.ZipFile(archive_path) as zf:
            return json.loads(zf.read("manifest.json").decode("utf-8"))
    except Exception:
        return {}


def build_param_sfo(title: str) -> bytes:
    """构造最小合法 PARAM.SFO（只有 TITLE 字段），供 PSP/PS3 存档标题识别。"""
    count = 1
    data_blob = str(title).encode("utf-8") + b"\x00"
    data_start = 20 + count * 16
    key_blob = b"TITLE\x00"
    key_start = data_start + len(data_blob)
    header = b"\x00PSF" + struct.pack("<IIII", 0x00000101, key_start, data_start, count)
    entry = struct.pack("<HHIII", 0, 0x0204, len(data_blob), 256, 0)
    return header + entry + data_blob + key_blob


def write_3ds_rom(rom_path: Union[str, Path], title_id: str = "0004000000033600") -> str:
    """写一个带 NCSD 头的最小 .3ds ROM（只用于 3DS title-id 存档识别）。"""
    path = Path(rom_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    header = bytearray(0x120)
    header[0x100:0x104] = b"NCSD"
    header[0x108:0x110] = int(str(title_id), 16).to_bytes(8, "little")
    path.write_bytes(bytes(header))
    return str(path)


# ---------------------------------------------------------------------------
# aria2
# ---------------------------------------------------------------------------


class FakeAria2:
    """内存 aria2：``add_uri`` 立即生成可控的假归档，``tell_status`` 可配置。

    故障开关（兼容旧字段）：
    - ``fail_add_at``：第 N 次 ``add_uri`` 失败；
    - ``status_error_at``：第 N 次 ``tell_status`` 返回 status=error；
    - ``lose_gid_at``：第 N 次 ``tell_status`` 抛“gid 不存在”。

    新增能力：
    - ``initial_status``：新加入的下载默认状态（``complete`` / ``active`` / ``waiting`` 等）；
    - ``inject_download``：模拟 aria2 重启后仍有会话（旧 gid 丢失、新 gid 在跑）；
    - ``forget_gid`` / ``hidden_gids``：模拟 gid 永久丢失；
    - ``set_download_status``：把某个 gid 推进到 complete/error/paused；
    - ``add_errors``：按顺序消费的 add 失败（如控制文件损坏）；
    - ``replace_uri`` 对不存在的 gid 抛 Aria2Error（与真实 changeUri 一致）。
    """

    def __init__(
        self,
        payload_builder: Optional[Callable[[str, str], None]] = None,
        *,
        initial_status: str = "complete",
    ):
        self.payload_builder = payload_builder
        self.initial_status = str(initial_status or "complete")
        self.downloads: Dict[str, Dict[str, Any]] = {}
        self.added: List[Dict[str, Any]] = []
        self.removed: List[str] = []
        self.replaced: List[Tuple[str, str]] = []
        self.add_errors: List[Union[str, Exception]] = []
        self.hidden_gids: set[str] = set()
        self.fail_add_at: int = 0       # 第 N 个 add 抛错（1-based）
        self.status_error_at: int = 0   # 第 N 个 tell_status 返回 error
        self.lose_gid_at: int = 0       # 第 N 个 tell_status 抛 gid 不存在
        self.fail_replace = False       # changeUri 失败（走 addUri 回退）
        self.add_calls = 0
        self.status_calls = 0
        self.remove_calls = 0
        self._gid = 0

    # -- 生命周期 ---------------------------------------------------------
    async def ensure_running(self) -> Dict[str, str]:
        return {"status": "running", "rpc_url": "http://127.0.0.1:0/jsonrpc"}

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
        self.add_calls += 1
        if self.add_errors:
            error = self.add_errors.pop(0)
            raise error if isinstance(error, Exception) else Aria2Error(str(error))
        if self.fail_add_at and self.add_calls == self.fail_add_at:
            raise Aria2Error("fake aria2 add failed")
        self._gid += 1
        gid = f"gid-{self._gid}"
        path = Path(download_dir) / out_name
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.payload_builder:
            self.payload_builder(str(path), out_name)
        complete = self.initial_status == "complete"
        self.downloads[gid] = {
            "path": str(path),
            "status": self.initial_status,
            "totalLength": "100",
            "completedLength": "100" if complete else "0",
            "downloadSpeed": "0",
            "direct_url": direct_url,
            "cookie": cookie,
            "referer": referer,
            "user_agent": user_agent,
            "out_name": out_name,
        }
        self.added.append(
            {
                "gid": gid,
                "path": str(path),
                "out_name": out_name,
                "direct_url": direct_url,
                "referer": referer,
                "user_agent": user_agent,
            }
        )
        return gid

    async def tell_status(self, gid: str) -> Dict[str, Any]:
        self.status_calls += 1
        if self.lose_gid_at and self.status_calls == self.lose_gid_at:
            raise Aria2Error("fake aria2 gid lost")
        if self.status_error_at and self.status_calls == self.status_error_at:
            return {"status": "error", "errorMessage": "fake aria2 error", "files": []}
        item = self.downloads.get(gid)
        if not item or gid in self.hidden_gids:
            raise Aria2Error(f"gid not found: {gid}")
        return {
            "status": item["status"],
            "totalLength": item["totalLength"],
            "completedLength": item["completedLength"],
            "downloadSpeed": item["downloadSpeed"],
            "errorMessage": item.get("errorMessage", ""),
            "files": [{"path": item["path"]}],
        }

    async def list_downloads(self, *, max_stopped: int = 500) -> List[Dict[str, Any]]:
        rows = []
        for gid, item in self.downloads.items():
            if gid in self.hidden_gids:
                continue
            rows.append(
                {
                    "gid": gid,
                    "status": item["status"],
                    "totalLength": item["totalLength"],
                    "completedLength": item["completedLength"],
                    "files": [{"path": item["path"]}],
                }
            )
        return rows

    async def pause(self, gid: str) -> None:
        item = self.downloads.get(gid)
        if not item or gid in self.hidden_gids:
            raise Aria2Error(f"gid not found: {gid}")
        item["status"] = "paused"

    async def resume(self, gid: str) -> None:
        item = self.downloads.get(gid)
        if not item or gid in self.hidden_gids:
            raise Aria2Error(f"gid not found: {gid}")
        item["status"] = "active"

    async def remove(self, gid: str) -> None:
        self.remove_calls += 1
        self.removed.append(gid)
        self.downloads.pop(gid, None)

    async def replace_uri(self, gid: str, direct_url: str) -> None:
        if self.fail_replace:
            raise Aria2Error("fake changeUri failed")
        item = self.downloads.get(gid)
        if not item or gid in self.hidden_gids:
            raise Aria2Error(f"gid not found: {gid}")
        item["direct_url"] = direct_url
        self.replaced.append((gid, direct_url))

    async def get_uris(self, gid: str) -> List[str]:
        item = self.downloads.get(gid)
        if not item or gid in self.hidden_gids:
            raise Aria2Error(f"gid not found: {gid}")
        return [str(item.get("direct_url", "") or "")]

    def stop(self) -> None:
        return None

    # -- 模拟控制 ---------------------------------------------------------
    def inject_download(
        self,
        gid: str,
        path: Union[str, Path],
        *,
        status: str = "active",
        total: int = 100,
        completed: int = 0,
        speed: int = 0,
        ensure_file: bool = False,
        direct_url: str = "",
    ) -> Dict[str, Any]:
        """注入一个“重启后仍然存在”的 aria2 会话。"""
        target = Path(path)
        if ensure_file:
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_bytes(b"")
        self.downloads[gid] = {
            "path": str(target),
            "status": str(status or "active"),
            "totalLength": str(int(total)),
            "completedLength": str(int(completed)),
            "downloadSpeed": str(int(speed)),
            "direct_url": direct_url,
            "cookie": "",
            "referer": "",
            "user_agent": "",
            "out_name": target.name,
        }
        return self.downloads[gid]

    def forget_gid(self, gid: str, *, hide: bool = False) -> None:
        """模拟 gid 从 aria2 会话中消失（重启后默认不会再出现）。"""
        self.downloads.pop(gid, None)
        if hide:
            self.hidden_gids.add(gid)

    def hide_gid(self, gid: str) -> None:
        self.hidden_gids.add(gid)

    def set_download_status(
        self,
        gid: str,
        status: str,
        *,
        completed: Optional[int] = None,
        total: Optional[int] = None,
        speed: int = 0,
        error_message: str = "",
    ) -> None:
        """推进某个 gid 的状态（never complete → complete / error / paused）。"""
        item = self.downloads.get(gid)
        if item is None:
            raise AssertionError(f"fake aria2 没有 gid: {gid}")
        item["status"] = str(status or "active")
        if total is not None:
            item["totalLength"] = str(max(0, int(total)))
        if completed is not None:
            item["completedLength"] = str(max(0, int(completed)))
        elif status == "complete":
            item["completedLength"] = item["totalLength"]
        item["downloadSpeed"] = str(max(0, int(speed)))
        item["errorMessage"] = str(error_message or "")

    def gid_for_path(self, path: Union[str, Path]) -> str:
        target = os.path.realpath(str(path))
        for gid, item in self.downloads.items():
            if os.path.realpath(str(item.get("path", ""))) == target:
                return gid
        return ""


# ---------------------------------------------------------------------------
# 7z
# ---------------------------------------------------------------------------


class FakeSevenZip:
    """用 zipfile 模拟 7z；保留目录层级/排除规则，macOS 可运行。"""

    def __init__(self) -> None:
        self.created: List[str] = []
        self.extracted: List[str] = []
        self.tested: List[str] = []
        self.fail_extract = False
        self.fail_create = False
        self.fail_test_archive = False
        self.test_reason = "fake 7z archive test failed"
        self.corrupt_on_create = False
        self.extract_error: Optional[Exception] = None

    # -- 创建 -------------------------------------------------------------
    def create_archive(
        self,
        archive_path: str,
        source_paths: Sequence[str],
        working_dir: str = "",
        progress_cb: Optional[Callable[[float], None]] = None,
        excludes: Optional[Sequence[str]] = None,
    ) -> None:
        if self.fail_create:
            raise SevenZipError("fake 7z create failed")
        archive = Path(archive_path)
        archive.parent.mkdir(parents=True, exist_ok=True)
        if self.corrupt_on_create:
            archive.write_bytes(b"not-a-zip-at-all")
            self.created.append(str(archive))
            if progress_cb:
                progress_cb(100.0)
            return
        sources = [Path(path) for path in source_paths]
        sources = [source for source in sources if source.exists()] or sources
        if working_dir:
            base = Path(working_dir)
        else:
            first = sources[0]
            base = first if first.is_dir() else first.parent
        patterns = [str(item) for item in (excludes or []) if str(item).strip()]

        def _is_excluded(path: Path) -> bool:
            try:
                rel = str(path.relative_to(base)).replace("\\", "/")
            except ValueError:
                rel = path.name
            candidates = (path.name, rel)
            for pattern in patterns:
                for candidate in candidates:
                    if fnmatch.fnmatch(candidate, pattern):
                        return True
            # 父目录命中排除规则时目录整体排除（与 7z 的 -xr! 行为近似）
            for parent in path.parents:
                try:
                    parent_rel = str(parent.relative_to(base)).replace("\\", "/")
                except ValueError:
                    break
                if parent_rel in {"", "."}:
                    continue
                for pattern in patterns:
                    if fnmatch.fnmatch(parent_rel, pattern) or fnmatch.fnmatch(parent.name, pattern):
                        return True
            return False

        with zipfile.ZipFile(archive, "a") as zf:
            for source in sources:
                if source.is_dir():
                    for current, dirnames, filenames in os.walk(source):
                        dirnames[:] = [
                            name for name in dirnames
                            if not _is_excluded(Path(current) / name)
                        ]
                        for name in filenames:
                            path = Path(current) / name
                            if _is_excluded(path):
                                continue
                            try:
                                arcname = str(path.relative_to(base))
                            except ValueError:
                                arcname = path.name
                            zf.write(path, arcname)
                elif source.is_file() and not _is_excluded(source):
                    try:
                        arcname = str(source.relative_to(base))
                    except ValueError:
                        arcname = source.name
                    zf.write(source, arcname)
        self.created.append(str(archive))
        if progress_cb:
            progress_cb(100.0)

    # -- 解压 / 校验 ------------------------------------------------------
    def extract_archive(
        self,
        archive_path: str,
        output_dir: str,
        progress_cb: Optional[Callable[[float], None]] = None,
    ) -> None:
        if self.extract_error is not None:
            raise self.extract_error
        if self.fail_extract:
            # 默认抛普通异常，覆盖 tianyi_service 的“7z 解压异常”兜底分支；
            # 需要七牛错误语义时用 extract_error 显式传 SevenZipError。
            raise RuntimeError("fake 7z extract failed")
        target = Path(output_dir)
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path) as zf:
            zf.extractall(target)
        self.extracted.append(str(archive_path))
        if progress_cb:
            progress_cb(100.0)

    def test_archive(self, archive_path: str, timeout: float = 900.0):
        self.tested.append(str(archive_path))
        if self.fail_test_archive:
            return False, self.test_reason
        try:
            with zipfile.ZipFile(archive_path) as zf:
                zf.namelist()
            return True, ""
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"

    def archive_entries(self, archive_path: str) -> List[str]:
        return archive_names(archive_path)

    def read_manifest(self, archive_path: str) -> Dict[str, Any]:
        return read_archive_manifest(archive_path)


# ---------------------------------------------------------------------------
# 天翼云盘（云存档上传/版本列表/下载）
# ---------------------------------------------------------------------------


class FakeCloud:
    """内存天翼云盘：只实现云存档链路用到的三个接口。

    - ``files``：``"game_key/子目录" -> {远端文件名: bytes}``；
    - 与真实 ``tianyi_client`` 同名函数签名一致（keyword-only），可直接 monkeypatch。
    """

    def __init__(self) -> None:
        self.files: Dict[str, Dict[str, bytes]] = {}
        self._file_ids: Dict[str, Tuple[str, str]] = {}
        self.upload_calls: List[Dict[str, Any]] = []
        self.list_calls: List[Dict[str, Any]] = []
        self.download_calls: List[Dict[str, Any]] = []
        self.fail_upload = False
        self.fail_list = False
        self.fail_download = False
        self._next_id = 0

    @staticmethod
    def _folder_key(parts: Sequence[str]) -> str:
        return "/".join(str(item or "").strip() for item in parts if str(item or "").strip())

    def _new_file_id(self) -> str:
        self._next_id += 1
        return f"cloud-file-{self._next_id}"

    def add_archive(self, folder_parts: Sequence[str], name: str, data: bytes) -> str:
        """预置一份云端文件（用于构造旧版本/旧 manifest 场景）。"""
        key = self._folder_key(folder_parts)
        self.files.setdefault(key, {})[str(name)] = bytes(data)
        file_id = self._new_file_id()
        self._file_ids[file_id] = (key, str(name))
        return file_id

    def versions(self, game_key: str) -> List[str]:
        rows = self.files.get(str(game_key), {})
        return sorted(rows.keys(), reverse=True)

    async def upload(
        self,
        *,
        cookie: str,
        local_file_path: str,
        remote_folder_parts: Sequence[str],
        remote_name: str,
    ) -> Dict[str, Any]:
        self.upload_calls.append(
            {
                "cookie": cookie,
                "local_file_path": str(local_file_path),
                "remote_folder_parts": [str(item) for item in remote_folder_parts],
                "remote_name": str(remote_name),
            }
        )
        if self.fail_upload:
            raise TianyiApiError("fake cloud upload failed")
        path = Path(local_file_path)
        if not path.is_file():
            raise TianyiApiError("待上传压缩包不存在")
        data = path.read_bytes()
        file_id = self.add_archive(remote_folder_parts, remote_name, data)
        key = self._folder_key(remote_folder_parts)
        return {
            "file_id": file_id,
            "cloud_path": f"/freedeckCYCloudSaves/{key}/{remote_name}",
            "file_size": len(data),
        }

    async def list(self, *, cookie: str, remote_folder_parts: Sequence[str]) -> Dict[str, Any]:
        key = self._folder_key(remote_folder_parts)
        self.list_calls.append({"cookie": cookie, "remote_folder_parts": list(remote_folder_parts)})
        if self.fail_list:
            raise TianyiApiError("fake cloud list failed")
        rows: List[Dict[str, Any]] = []
        for file_id, (folder, name) in sorted(self._file_ids.items()):
            if folder != key:
                continue
            data = self.files.get(folder, {}).get(name, b"")
            rows.append(
                {
                    "file_id": file_id,
                    "name": name,
                    "size": len(data),
                    "last_op_time": "2026-01-01 00:00:00",
                }
            )
        return {"exists": bool(rows), "files": rows, "remote_folder_parts": list(remote_folder_parts)}

    async def download(self, *, cookie: str, file_id: str, local_file_path: str) -> Dict[str, Any]:
        self.download_calls.append(
            {"cookie": cookie, "file_id": file_id, "local_file_path": str(local_file_path)}
        )
        if self.fail_download:
            raise TianyiApiError("fake cloud download failed")
        target = self._file_ids.get(str(file_id))
        if target is None:
            raise TianyiApiError("fake cloud 文件不存在")
        data = self.files.get(target[0], {}).get(target[1], b"")
        path = Path(local_file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return {"file_id": file_id, "local_file_path": str(path), "file_size": len(data)}
