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


def _fake_mount_env(monkeypatch, realpaths=None, identity=None):
    mapping = dict(realpaths or {})

    def _realpath(path, *args, **kwargs):
        value = str(path)
        return mapping.get(value, value)

    monkeypatch.setattr(storage_options.os.path, "realpath", _realpath)
    monkeypatch.setattr(storage_options.os.path, "isdir", lambda path: True)
    monkeypatch.setattr(storage_options, "_probe_writable", lambda path: True)
    if identity is not None:
        monkeypatch.setattr(storage_options, "_mount_identity", lambda path: identity.get(str(path)))


def _usage(_path):
    return SimpleNamespace(free=5 * 1024**3, total=50 * 1024**3)


def test_android_internal_storage_aliases_are_not_offered(tmp_path, monkeypatch):
    _fake_mount_env(monkeypatch)
    mounts = "\n".join(
        [
            "/dev/block/dm-0 /storage/emulated/0 f2fs rw 0 0",
            "/dev/block/dm-0 /storage/self/primary f2fs rw 0 0",
            "/dev/block/dm-1 /mnt/runtime/default/emulated/0 f2fs rw 0 0",
            "/dev/block/dm-1 /mnt/pass_through/0/emulated/0 fuse rw 0 0",
            "/dev/block/mmcblk1p1 /storage/1A2B-3C4D vfat rw 0 0",
        ]
    )
    data = storage_options.detect_storage_options(mounts_text=mounts, home=str(tmp_path), disk_usage=_usage)
    assert [item["mount"] for item in data["external"]] == ["/storage/1A2B-3C4D"]


def test_bind_mount_alias_deduped_by_identity(tmp_path, monkeypatch):
    mounts = "\n".join(
        [
            "/dev/sda1 /run/media/deck/SD ext4 rw 0 0",
            "/dev/sda1 /run/media/deck/SD-bind ext4 rw 0 0",
        ]
    )
    _fake_mount_env(
        monkeypatch,
        identity={
            "/run/media/deck/SD": (7, 11),
            "/run/media/deck/SD-bind": (7, 11),
        },
    )
    data = storage_options.detect_storage_options(mounts_text=mounts, home=str(tmp_path), disk_usage=_usage)
    assert len(data["external"]) == 1
    assert data["external"][0]["mount"] == "/run/media/deck/SD"


def test_readonly_and_system_fstype_mounts_skipped(tmp_path, monkeypatch):
    _fake_mount_env(monkeypatch)
    mounts = "\n".join(
        [
            "/dev/sda1 /run/media/deck/RO ext4 ro 0 0",
            "/dev/sda2 /run/media/deck/tmp tmpfs rw 0 0",
            "/dev/sda3 /run/media/deck/RW ext4 rw 0 0",
        ]
    )
    data = storage_options.detect_storage_options(mounts_text=mounts, home=str(tmp_path), disk_usage=_usage)
    assert [item["mount"] for item in data["external"]] == ["/run/media/deck/RW"]


def test_mount_path_with_control_chars_rejected(tmp_path, monkeypatch):
    _fake_mount_env(monkeypatch)
    # /proc/mounts 会把空格转义成 \040，换行转义成 \012。
    mounts = "/dev/sda1 /run/media/deck/Bad\\012Name ext4 rw 0 0\n"
    data = storage_options.detect_storage_options(mounts_text=mounts, home=str(tmp_path), disk_usage=_usage)
    assert data["external"] == []


def test_sanitize_label_strips_control_chars():
    assert storage_options._sanitize_label(" SD\ttab\nname \x00 ") == "SD tab name"


def test_symlinked_mount_alias_deduped(tmp_path, monkeypatch):
    real = tmp_path / "sd-real"
    real.mkdir()
    alias = tmp_path / "sd-link"
    alias.symlink_to(real)
    monkeypatch.setattr(storage_options, "_MOUNT_PREFIXES", (str(real) + "/",))
    monkeypatch.setattr(storage_options, "_probe_writable", lambda path: True)
    mounts = f"/dev/sda1 {real} ext4 rw 0 0\n/dev/sda1 {alias} ext4 rw 0 0\n"
    data = storage_options.detect_storage_options(mounts_text=mounts, home=str(tmp_path), disk_usage=_usage)
    assert len(data["external"]) == 1


def test_internal_option_uses_home_downloads(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    data = storage_options.detect_storage_options(
        mounts_text="",
        home=str(home),
        disk_usage=lambda path: SimpleNamespace(free=5 * 1024**3, total=50 * 1024**3),
    )
    internal = data["internal"]
    assert internal["label"] == "内置硬盘"
    assert internal["download_dir"] == str(home / "Downloads")
