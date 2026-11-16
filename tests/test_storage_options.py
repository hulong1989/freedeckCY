"""SD 卡/外置存储检测。"""

from __future__ import annotations

from types import SimpleNamespace

import storage_options


def test_detect_external_mount(tmp_path, monkeypatch):
    mount = tmp_path / "sd"
    mount.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(storage_options, "_MOUNT_PREFIXES", (str(tmp_path) + "/",))
    data = storage_options.detect_storage_options(
        mounts_text=f"/dev/mmcblk0p1 {mount} ext4 rw 0 0\n",
        home=str(home),
        disk_usage=lambda path: SimpleNamespace(free=10 * 1024**3, total=100 * 1024**3),
    )
    assert len(data["external"]) == 1
    item = data["external"][0]
    assert item["mount"] == str(mount)
    assert item["free_text"] == "10.0 GB"
    assert item["download_dir"].endswith("/freedeckCY/downloads")
    assert item["install_dir"].endswith("/freedeckCY/installed")


def test_detect_ignores_system_mounts(tmp_path, monkeypatch):
    monkeypatch.setattr(storage_options, "_MOUNT_PREFIXES", (str(tmp_path) + "/",))
    data = storage_options.detect_storage_options(
        mounts_text="/dev/root / ext4 rw 0 0\nproc /proc proc rw 0 0\n",
        home=str(tmp_path),
        disk_usage=lambda path: SimpleNamespace(free=1, total=2),
    )
    assert data["external"] == []
    assert data["internal"]["kind"] == "internal"
