# archive_bundle.py - 多分卷归档识别
#
# 参考上游 Freedeck v0.6 的 archive_detector 做的精简版：只负责"把同一安装计划里的
# 若干文件识别成多分卷归档集合"，并给出主卷（入口卷）与缺失分卷。
#
# 典型命名：
#   game.7z.001 / game.7z.002 ...
#   game.zip.001 / game.zip.002 ...
#   game.rar.001 / game.rar.002 ...
#   game.part1.rar / game.part2.rar ...
#   game.z01 + game.zip（ZIP 分卷）
#   game.r00 + game.rar（RAR 老式分卷）

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

_NUMBERED_RE = re.compile(r"^(?P<base>.+\.(?:7z|zip|rar))\.(?P<idx>\d{2,4})$", re.IGNORECASE)
_RAR_PART_RE = re.compile(r"^(?P<prefix>.+)\.part(?P<idx>\d+)\.rar$", re.IGNORECASE)
_ZIP_SPANNED_RE = re.compile(r"^(?P<prefix>.+)\.z(?P<idx>\d{2})$", re.IGNORECASE)
_RAR_LEGACY_RE = re.compile(r"^(?P<prefix>.+)\.r(?P<idx>\d{2})$", re.IGNORECASE)


@dataclass
class ArchivePart:
    """多分卷归档中的一个分卷。"""

    path: str
    index: int


@dataclass
class ArchiveSet:
    """一组多分卷归档（parts >= 2 才会被识别出来）。"""

    base_name: str
    archive_type: str
    entry_file: str
    parts: List[ArchivePart] = field(default_factory=list)
    missing_parts: List[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return bool(self.entry_file) and not self.missing_parts

    def to_dict(self) -> Dict[str, object]:
        return {
            "base_name": self.base_name,
            "archive_type": self.archive_type,
            "entry_file": self.entry_file,
            "parts": [part.path for part in self.parts],
            "missing_parts": list(self.missing_parts),
            "complete": self.complete,
        }


def _numbered_name(base: str, index: int, width: int) -> str:
    return f"{base}.{index:0{width}d}"


def _finalize(
    *,
    base_name: str,
    archive_type: str,
    parts: Sequence[Tuple[int, str]],
    entry_file: str,
    expected_names: Sequence[str],
) -> ArchiveSet:
    ordered = sorted(parts, key=lambda item: item[0])
    present = {os.path.basename(name) for _, name in ordered}
    # zip 分卷/rar 老式分卷的“入口文件”不在 parts 里（如 game.zip、game.rar），
    # 需要单独确认它是否存在。
    if entry_file and os.path.isfile(entry_file):
        present.add(os.path.basename(entry_file))
    missing = [name for name in expected_names if name not in present]
    return ArchiveSet(
        base_name=base_name,
        archive_type=archive_type,
        entry_file=entry_file,
        parts=[ArchivePart(path=name, index=index) for index, name in ordered],
        missing_parts=missing,
    )


def detect_archive_sets(paths: Sequence[str]) -> List[ArchiveSet]:
    """从一批文件路径里识别多分卷归档集合（单个文件不算）。"""
    numbered: Dict[Tuple[str, str], List[Tuple[int, str]]] = {}
    rar_parts: Dict[Tuple[str, str], List[Tuple[int, str]]] = {}
    zip_spanned: Dict[Tuple[str, str], List[Tuple[int, str]]] = {}
    zip_entries: Dict[Tuple[str, str], str] = {}
    rar_legacy: Dict[Tuple[str, str], List[Tuple[int, str]]] = {}
    rar_entries: Dict[Tuple[str, str], str] = {}

    for raw_path in paths:
        path = str(raw_path or "").strip()
        if not path:
            continue
        name = os.path.basename(path)
        parent = os.path.dirname(os.path.abspath(path)).lower()

        match = _NUMBERED_RE.match(name)
        if match:
            base = str(match.group("base") or "")
            numbered.setdefault((parent, base.lower()), []).append((int(match.group("idx")), path))
            continue

        match = _RAR_PART_RE.match(name)
        if match:
            prefix = str(match.group("prefix") or "")
            rar_parts.setdefault((parent, prefix.lower()), []).append((int(match.group("idx")), path))
            continue

        match = _ZIP_SPANNED_RE.match(name)
        if match:
            prefix = str(match.group("prefix") or "")
            zip_spanned.setdefault((parent, prefix.lower()), []).append((int(match.group("idx")), path))
            continue

        match = _RAR_LEGACY_RE.match(name)
        if match:
            prefix = str(match.group("prefix") or "")
            rar_legacy.setdefault((parent, prefix.lower()), []).append((int(match.group("idx")), path))
            continue

        if name.lower().endswith(".zip"):
            zip_entries[(parent, name[:-4].lower())] = path
        elif name.lower().endswith(".rar"):
            rar_entries[(parent, name[:-4].lower())] = path

    sets: List[ArchiveSet] = []

    for (_parent, _key), items in sorted(numbered.items()):
        # 只有 .001 一个分卷时也要识别：几乎可以肯定是缺了后续分卷，
        # 交给上层报“分卷不完整”，而不是当成普通压缩包去解压。
        if len(items) < 2 and int(items[0][0]) != 1:
            continue
        first_name = os.path.basename(items[0][1])
        base_name = re.sub(r"(?i)\.\d{2,4}$", "", first_name)
        width = max(3, min(4, len(first_name) - len(base_name) - 1))
        max_index = max(index for index, _ in items)
        upper = max_index + 1 if len(items) == 1 else max_index
        expected = [_numbered_name(base_name, index, width) for index in range(1, upper + 1)]
        entry = next(
            (path for index, path in items if index == 1),
            os.path.join(os.path.dirname(items[0][1]), expected[0]),
        )
        lower_base = base_name.lower()
        if lower_base.endswith(".7z"):
            archive_type = "seven_zip_numbered"
        elif lower_base.endswith(".zip"):
            archive_type = "zip_numbered"
        else:
            archive_type = "rar_numbered"
        sets.append(
            _finalize(
                base_name=base_name,
                archive_type=archive_type,
                parts=[(index, path) for index, path in items],
                entry_file=entry,
                expected_names=expected,
            )
        )

    for (_parent, _key), items in sorted(rar_parts.items()):
        if len(items) < 2:
            continue
        prefix_display = re.sub(r"(?i)\.part\d+\.rar$", "", os.path.basename(items[0][1]))
        max_index = max(index for index, _ in items)
        width = max(1, max(len(str(index)) for index, _ in items))
        expected = [f"{prefix_display}.part{index:0{width}d}.rar" for index in range(1, max_index + 1)]
        entry = next((path for index, path in items if index == 1), "")
        sets.append(
            _finalize(
                base_name=prefix_display,
                archive_type="rar_part",
                parts=[(index, path) for index, path in items],
                entry_file=entry,
                expected_names=expected,
            )
        )

    for key, items in sorted(zip_spanned.items()):
        if len(items) < 2:
            continue
        _parent, prefix_lower = key
        prefix_display = re.sub(r"(?i)\.z\d{2}$", "", os.path.basename(items[0][1]))
        max_index = max(index for index, _ in items)
        width = max(2, max(len(str(index)) for index, _ in items))
        expected = [f"{prefix_display}.z{index:0{width}d}" for index in range(1, max_index + 1)]
        entry = zip_entries.get((_parent, prefix_lower), "")
        expected.append(f"{prefix_display}.zip")
        sets.append(
            _finalize(
                base_name=prefix_display,
                archive_type="zip_spanned",
                parts=[(index, path) for index, path in items],
                entry_file=entry or os.path.join(os.path.dirname(items[0][1]), f"{prefix_display}.zip"),
                expected_names=expected,
            )
        )

    for key, items in sorted(rar_legacy.items()):
        if len(items) < 2:
            continue
        _parent, prefix_lower = key
        prefix_display = re.sub(r"(?i)\.r\d{2}$", "", os.path.basename(items[0][1]))
        max_index = max(index for index, _ in items)
        width = max(2, max(len(str(index)) for index, _ in items))
        expected = [f"{prefix_display}.r{index:0{width}d}" for index in range(0, max_index + 1)]
        entry = rar_entries.get((_parent, prefix_lower), "")
        expected.append(f"{prefix_display}.rar")
        sets.append(
            _finalize(
                base_name=prefix_display,
                archive_type="rar_legacy",
                parts=[(index, path) for index, path in items],
                entry_file=entry or os.path.join(os.path.dirname(items[0][1]), f"{prefix_display}.rar"),
                expected_names=expected,
            )
        )

    return sets


def build_bundle_index(paths: Sequence[str]) -> Dict[str, Tuple[ArchiveSet, bool]]:
    """路径 -> (所属分卷集合, 是否主卷)。非分卷文件不会出现在索引里。"""
    index: Dict[str, Tuple[ArchiveSet, bool]] = {}
    for archive_set in detect_archive_sets(paths):
        entry = os.path.realpath(archive_set.entry_file) if archive_set.entry_file else ""
        for part in archive_set.parts:
            real = os.path.realpath(part.path)
            index[real] = (archive_set, bool(entry and real == entry))
    return index


def looks_like_multi_volume_name(file_name: str) -> bool:
    """仅按文件名判断是否像分卷（用于 _is_archive_file 的兜底）。"""
    name = os.path.basename(str(file_name or "").strip())
    return bool(
        _NUMBERED_RE.match(name)
        or _RAR_PART_RE.match(name)
        or _ZIP_SPANNED_RE.match(name)
        or _RAR_LEGACY_RE.match(name)
    )
