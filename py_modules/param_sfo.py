"""最小 PARAM.SFO 解析（PSP/PS3 存档标题识别）。"""

from __future__ import annotations

import os
import struct
from typing import Any, Dict

_MAGIC = b"\x00PSF"


def read_param_sfo(path: str) -> Dict[str, Any]:
    """读取 PARAM.SFO，返回 key -> 值；格式异常返回空 dict。"""
    try:
        with open(path, "rb") as fh:
            data = fh.read(256 * 1024)
    except Exception:
        return {}
    if len(data) < 20 or not data.startswith(_MAGIC):
        return {}
    try:
        _version, key_start, data_start, count = struct.unpack_from("<IIII", data, 4)
        result: Dict[str, Any] = {}
        for index in range(min(count, 256)):
            offset = 20 + index * 16
            if offset + 16 > len(data):
                break
            key_offset, data_fmt, data_len, _max_len, value_offset = struct.unpack_from("<HHIII", data, offset)
            key_end = data.find(b"\x00", key_start + key_offset)
            if key_end < 0:
                continue
            key = data[key_start + key_offset:key_end].decode("utf-8", "replace")
            start = data_start + value_offset
            raw = data[start:start + data_len]
            if data_fmt == 0x0204:
                result[key] = raw.split(b"\x00", 1)[0].decode("utf-8", "replace")
            elif data_fmt == 0x0404:
                result[key] = int.from_bytes(raw[:4], "little") if len(raw) >= 4 else 0
            else:
                result[key] = raw
        return result
    except Exception:
        return {}


def find_param_sfo(directory: str, *, max_depth: int = 3) -> str:
    """在目录内找 PARAM.SFO（优先直接子文件）。"""
    direct = os.path.join(directory, "PARAM.SFO")
    if os.path.isfile(direct):
        return direct
    base = os.path.realpath(directory)
    for dirpath, dirnames, filenames in os.walk(base):
        if dirpath.count(os.sep) - base.count(os.sep) >= max_depth:
            dirnames[:] = []
        for name in filenames:
            if name.upper() == "PARAM.SFO":
                return os.path.join(dirpath, name)
    return ""
