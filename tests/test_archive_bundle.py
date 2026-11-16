"""多分卷归档识别测试（archive_bundle）。"""

from __future__ import annotations

from pathlib import Path

from archive_bundle import (
    build_bundle_index,
    detect_archive_sets,
    looks_like_multi_volume_name,
)


def _touch_files(tmp_path: Path, *names: str) -> list[str]:
    paths = []
    for name in names:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"PK\x03\x04fake")
        paths.append(str(path))
    return paths


def test_detects_numbered_7z_volumes(tmp_path):
    paths = _touch_files(tmp_path, "game.7z.001", "game.7z.002", "game.7z.003")
    sets = detect_archive_sets(paths)

    assert len(sets) == 1
    archive_set = sets[0]
    assert archive_set.archive_type == "seven_zip_numbered"
    assert archive_set.entry_file.endswith("game.7z.001")
    assert archive_set.complete is True
    assert [part.index for part in archive_set.parts] == [1, 2, 3]


def test_reports_missing_volume(tmp_path):
    paths = _touch_files(tmp_path, "game.7z.001", "game.7z.003")
    sets = detect_archive_sets(paths)

    assert len(sets) == 1
    assert sets[0].complete is False
    assert sets[0].missing_parts == ["game.7z.002"]


def test_detects_rar_part_naming(tmp_path):
    paths = _touch_files(tmp_path, "game.part1.rar", "game.part2.rar")
    sets = detect_archive_sets(paths)

    assert len(sets) == 1
    assert sets[0].archive_type == "rar_part"
    assert sets[0].entry_file.endswith("game.part1.rar")
    assert sets[0].complete is True


def test_detects_zip_spanned_with_entry(tmp_path):
    paths = _touch_files(tmp_path, "game.z01", "game.z02", "game.zip")
    sets = detect_archive_sets(paths)

    assert len(sets) == 1
    assert sets[0].archive_type == "zip_spanned"
    assert sets[0].entry_file.endswith("game.zip")
    assert sets[0].complete is True


def test_zip_spanned_without_entry_is_incomplete(tmp_path):
    paths = _touch_files(tmp_path, "game.z01", "game.z02")
    sets = detect_archive_sets(paths)

    assert len(sets) == 1
    assert sets[0].complete is False
    assert "game.zip" in sets[0].missing_parts


def test_detects_rar_legacy_naming(tmp_path):
    paths = _touch_files(tmp_path, "game.r00", "game.r01", "game.rar")
    sets = detect_archive_sets(paths)

    assert len(sets) == 1
    assert sets[0].archive_type == "rar_legacy"
    assert sets[0].entry_file.endswith("game.rar")


def test_single_file_is_not_a_bundle(tmp_path):
    paths = _touch_files(tmp_path, "game.7z")
    assert detect_archive_sets(paths) == []
    assert build_bundle_index(paths) == {}


def test_bundle_index_marks_entry(tmp_path):
    paths = _touch_files(tmp_path, "game.7z.001", "game.7z.002")
    index = build_bundle_index(paths)

    assert len(index) == 2
    entry_path, (entry_set, is_entry) = next(
        (path, value) for path, value in index.items() if path.endswith("game.7z.001")
    )
    assert is_entry is True
    assert entry_set.entry_file.endswith("game.7z.001")

    other = next(path for path in index if path.endswith("game.7z.002"))
    assert index[other][1] is False


def test_two_independent_bundles_in_same_dir(tmp_path):
    paths = _touch_files(
        tmp_path,
        "a.7z.001",
        "a.7z.002",
        "b.7z.001",
        "b.7z.002",
    )
    sets = detect_archive_sets(paths)
    assert len(sets) == 2
    assert {Path(item.base_name).name for item in sets} == {"a.7z", "b.7z"}


def test_multi_volume_name_helper():
    assert looks_like_multi_volume_name("game.7z.001") is True
    assert looks_like_multi_volume_name("game.part2.rar") is True
    assert looks_like_multi_volume_name("game.z01") is True
    assert looks_like_multi_volume_name("game.r00") is True
    assert looks_like_multi_volume_name("game.7z") is False
    assert looks_like_multi_volume_name("readme.txt") is False


def test_single_first_volume_reports_missing_followup(tmp_path):
    """只有 game.7z.001 时也应识别成分卷并提示缺 .002。"""
    paths = _touch_files(tmp_path, "game.7z.001")
    sets = detect_archive_sets(paths)

    assert len(sets) == 1
    assert sets[0].complete is False
    assert sets[0].entry_file.endswith("game.7z.001")
    assert sets[0].missing_parts == ["game.7z.002"]


def test_orphan_non_first_volume_is_ignored(tmp_path):
    paths = _touch_files(tmp_path, "game.7z.003")
    assert detect_archive_sets(paths) == []
