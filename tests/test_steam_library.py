"""Steam 多库 / Flatpak / SD 卡路径识别测试。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import steam_shortcuts as sc

APP_ID = 1234567890


def _write_library_folders(main_root: Path, libraries: list[Path]) -> None:
    entries = []
    for index, path in enumerate(libraries):
        entries.append(f'\t"{index}"\n\t{{\n\t\t"path"\t\t"{path}"\n\t}}\n')
    content = '"libraryfolders"\n{\n' + "".join(entries) + "}\n"
    (main_root / "steamapps" / "libraryfolders.vdf").write_text(content, encoding="utf-8")


def _make_compat(library: Path, user: str = "steamuser") -> Path:
    path = (
        library
        / "steamapps"
        / "compatdata"
        / str(APP_ID)
        / "pfx"
        / "drive_c"
        / "users"
        / user
    )
    path.mkdir(parents=True)
    return path


def test_finds_compat_dir_in_secondary_library(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    main_root = home / ".steam" / "steam"
    (main_root / "steamapps").mkdir(parents=True)
    sd_library = home / "sdcard" / "SteamLibrary"
    (sd_library / "steamapps").mkdir(parents=True)

    _write_library_folders(main_root, [main_root, sd_library])
    sd_users = _make_compat(sd_library)

    result = sc.find_compat_user_dir(APP_ID)

    assert result["ok"] is True
    assert result["steam_root"] == os.path.realpath(main_root)
    assert os.path.realpath(sd_library) in result["libraries"]
    assert result["compat_user_dir"] == os.path.realpath(sd_users)


def test_prefers_main_library_when_present(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    main_root = home / ".steam" / "steam"
    (main_root / "steamapps").mkdir(parents=True)
    main_users = _make_compat(main_root, user="deck")
    sd_library = home / "sd"
    (sd_library / "steamapps").mkdir(parents=True)
    _make_compat(sd_library)

    result = sc.find_compat_user_dir(APP_ID)
    assert result["compat_user_dir"] == os.path.realpath(main_users)


def test_detects_flatpak_steam_root(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    flatpak_root = (
        home / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam"
    )
    (flatpak_root / "steamapps").mkdir(parents=True)

    assert sc._find_steam_root() == os.path.realpath(flatpak_root)
    libs = sc._steam_library_paths(flatpak_root)
    assert os.path.realpath(flatpak_root) in libs


def test_env_override_wins(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    custom = tmp_path / "custom-steam"
    (custom / "steamapps").mkdir(parents=True)
    monkeypatch.setenv("FREEDECKCY_STEAM_ROOT", str(custom))

    assert sc._find_steam_root() == os.path.realpath(custom)


def test_legacy_library_folders_format(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    main_root = home / ".steam" / "steam"
    (main_root / "steamapps").mkdir(parents=True)
    legacy = home / "legacy-library"
    (legacy / "steamapps").mkdir(parents=True)

    content = (
        '"LibraryFolders"\n{\n'
        '\t"TimeNextStatsReport"\t\t"123"\n'
        f'\t"1"\t\t"{legacy}"\n'
        "}\n"
    )
    (main_root / "config").mkdir(parents=True, exist_ok=True)
    (main_root / "config" / "libraryfolders.vdf").write_text(content, encoding="utf-8")

    libs = sc._steam_library_paths(main_root)
    assert os.path.realpath(legacy) in libs
    assert all("TimeNextStatsReport" not in item for item in libs)


def test_finds_custom_proton_username(tmp_path, monkeypatch):
    """非 steamuser/deck 的自定义 Wine 用户名也要能命中。"""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    main_root = home / ".steam" / "steam"
    (main_root / "steamapps").mkdir(parents=True)

    users_root = (
        main_root / "steamapps" / "compatdata" / str(APP_ID) / "pfx" / "drive_c" / "users"
    )
    (users_root / "public").mkdir(parents=True)
    custom = users_root / "customuser"
    (custom / "AppData" / "Roaming").mkdir(parents=True)
    (custom / "Documents").mkdir()

    result = sc.find_compat_user_dir(APP_ID)
    assert result["compat_user_dir"] == os.path.realpath(custom)
