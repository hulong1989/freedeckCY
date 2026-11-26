"""存储清理扫描/安全删除测试。"""

from __future__ import annotations

import os

from storage_cleanup import clean_storage_cleanup, scan_storage_cleanup


def _paths(tmp_path):
    download = tmp_path / "downloads"
    install = tmp_path / "installed"
    update = tmp_path / "updates"
    backup = tmp_path / "backups"
    for path in (download, install, update, backup):
        path.mkdir(parents=True, exist_ok=True)
    return {
        "download_dir": str(download),
        "install_dir": str(install),
        "update_dir": str(update),
        "backup_dir": str(backup),
    }


def _write(path, size=10):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    return path


def test_scan_groups_safe_and_unsafe(tmp_path):
    paths = _paths(tmp_path)
    _write(tmp_path / "updates" / "freedeckCY-v0.28.16.zip", 100)
    _write(tmp_path / "updates" / "freedeckCY-v0.28.16.zip.sha256", 5)
    _write(tmp_path / "downloads" / "demo.bin.freedeckcy-size-mismatch-123", 40)
    _write(tmp_path / "installed" / "Game" / "old.dll.freedeckcy-noresume-456", 20)
    _write(tmp_path / "backups" / "abc_demo.freedeckcy-bak-1", 7)

    result = scan_storage_cleanup(**paths)
    groups = {group["id"]: group for group in result["groups"]}
    assert groups["update_packages"]["count"] == 2
    assert groups["update_packages"]["safe"] is True
    assert groups["quarantine"]["count"] == 2
    assert groups["quarantine"]["safe"] is True
    assert groups["legacy_backups"]["count"] == 1
    assert groups["legacy_backups"]["safe"] is False
    assert result["safe_count"] == 4
    assert result["safe_bytes"] == 165


def test_clean_deletes_only_safe_categories(tmp_path):
    paths = _paths(tmp_path)
    update_zip = _write(tmp_path / "updates" / "freedeckCY-v0.28.16.zip", 100)
    quarantine = _write(tmp_path / "downloads" / "demo.bin.freedeckcy-bad-1", 40)
    backup = _write(tmp_path / "backups" / "abc_demo.freedeckcy-bak-1", 7)

    result = clean_storage_cleanup(categories=["update_packages", "quarantine", "legacy_backups"], **paths)
    assert result["deleted_files"] == 2
    assert result["freed_bytes"] == 140
    assert not update_zip.exists()
    assert not quarantine.exists()
    assert backup.exists(), "legacy backups are not safe to delete"
    assert result["errors"] == []


def test_clean_rejects_empty_selection(tmp_path):
    paths = _paths(tmp_path)
    result = clean_storage_cleanup(categories=[], **paths)
    assert result["deleted_files"] == 0
    assert result["freed_bytes"] == 0


def test_scan_does_not_follow_symlinks(tmp_path):
    paths = _paths(tmp_path)
    outside = tmp_path / "outside.bin.freedeckcy-bad-1"
    _write(outside, 33)
    link = tmp_path / "downloads" / "link.freedeckcy-bad-2"
    os.symlink(str(outside), str(link))

    result = scan_storage_cleanup(**paths)
    paths_found = [item["path"] for group in result["groups"] for item in group["items"]]
    assert str(link) not in paths_found
    clean = clean_storage_cleanup(categories=["quarantine"], **paths)
    assert outside.exists()
    assert clean["deleted_files"] == 0
