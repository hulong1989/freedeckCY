"""Steam 快捷方式写入链路的端到端测试（用临时 HOME 模拟 Steam 目录）。"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

import steam_shortcuts as sc
from py_modules import vdf  # noqa: F401  (确保 vdf 可用)

STEAM64 = "76561198000000000"


def _account_id() -> str:
    return str(int(STEAM64) & 0xFFFFFFFF)


@pytest.fixture()
def fake_steam(tmp_path, monkeypatch):
    """构造一个最小可用的 Steam 目录，并把 HOME 指向它。"""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    root = home / ".steam" / "steam"
    (root / "steamapps").mkdir(parents=True)
    user_id = _account_id()
    (root / "userdata" / user_id / "config").mkdir(parents=True)
    (root / "config").mkdir(parents=True, exist_ok=True)

    (root / "config" / "loginusers.vdf").write_text(
        f'''"users"
{{
\t"{STEAM64}"
\t{{
\t\t"MostRecent"\t\t"1"
\t\t"PersonaName"\t\t"deck"
\t}}
}}
''',
        encoding="utf-8",
    )
    (root / "config" / "config.vdf").write_text(
        '''"InstallConfigStore"
{
\t"Software"
\t{
\t\t"Valve"
\t\t{
\t\t\t"Steam"
\t\t\t{
\t\t\t\t"CompatToolMapping"
\t\t\t\t{
\t\t\t\t}
\t\t\t}
\t\t}
\t}
}
''',
        encoding="utf-8",
    )
    return root, user_id


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """封面下载全部跳过，保证测试离线。"""

    async def _fail(*args, **kwargs):
        return False

    monkeypatch.setattr(sc, "_download_image_to", _fail)
    monkeypatch.setattr(sc, "_copy_file_sync", lambda *a, **k: False)


def _make_exe(tmp_path: Path) -> Path:
    exe = tmp_path / "DemoGame" / "bin" / "Demo.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"MZ fake exe")
    return exe


def test_add_shortcut_writes_vdf_and_proton(fake_steam, tmp_path):
    root, user_id = fake_steam
    exe = _make_exe(tmp_path)

    result = asyncio.run(
        sc.add_or_update_tianyi_shortcut(
            game_id="1001",
            display_name="DemoGame",
            exe_path=str(exe),
            launch_options="freedeckcy:tianyi:1001",
            proton_tool="proton_experimental",
        )
    )
    assert result["ok"] is True, result

    shortcuts_path = root / "userdata" / user_id / "config" / "shortcuts.vdf"
    assert shortcuts_path.is_file()
    payload = vdf.binary_loads(shortcuts_path.read_bytes())
    entries = list(payload["shortcuts"].values())
    assert len(entries) == 1
    assert entries[0]["AppName"] == "DemoGame"
    assert entries[0]["exe"] == f'"{os.path.realpath(str(exe))}"'
    assert entries[0]["LaunchOptions"] == "freedeckcy:tianyi:1001"

    app_id = int(result["appid_unsigned"])
    assert app_id >= 0x80000000

    config_text = (root / "config" / "config.vdf").read_text(encoding="utf-8")
    assert str(app_id) in config_text
    assert "proton_experimental" in config_text


def test_add_shortcut_is_idempotent(fake_steam, tmp_path):
    root, user_id = fake_steam
    exe = _make_exe(tmp_path)

    kwargs = dict(
        game_id="1002",
        display_name="SameGame",
        exe_path=str(exe),
        launch_options="freedeckcy:tianyi:1002",
    )
    first = asyncio.run(sc.add_or_update_tianyi_shortcut(**kwargs))
    second = asyncio.run(sc.add_or_update_tianyi_shortcut(**kwargs))
    assert first["appid_unsigned"] == second["appid_unsigned"]

    payload = vdf.binary_loads((root / "userdata" / user_id / "config" / "shortcuts.vdf").read_bytes())
    assert len(payload["shortcuts"]) == 1


def test_remove_shortcut(fake_steam, tmp_path):
    root, user_id = fake_steam
    exe = _make_exe(tmp_path)
    asyncio.run(
        sc.add_or_update_tianyi_shortcut(
            game_id="1003",
            display_name="Removable",
            exe_path=str(exe),
            launch_options="freedeckcy:tianyi:1003",
        )
    )

    removed = asyncio.run(sc.remove_tianyi_shortcut(game_id="1003"))
    assert removed.get("ok") is True, removed

    payload = vdf.binary_loads((root / "userdata" / user_id / "config" / "shortcuts.vdf").read_bytes())
    assert len(payload.get("shortcuts") or {}) == 0


def test_second_add_is_unchanged(fake_steam, tmp_path):
    root, user_id = fake_steam
    exe = _make_exe(tmp_path)
    kwargs = dict(
        game_id="2001",
        display_name="Idempotent",
        exe_path=str(exe),
        launch_options="freedeckcy:tianyi:2001",
    )
    first = asyncio.run(sc.add_or_update_tianyi_shortcut(**kwargs))
    second = asyncio.run(sc.add_or_update_tianyi_shortcut(**kwargs))

    assert first["action"] == "created"
    assert second["action"] == "unchanged"

    payload = vdf.binary_loads((root / "userdata" / user_id / "config" / "shortcuts.vdf").read_bytes())
    assert len(payload["shortcuts"]) == 1
    entry = list(payload["shortcuts"].values())[0]
    assert entry["DevkitGameID"] == "2001"


def test_dedupe_survives_user_edited_launch_options(fake_steam, tmp_path):
    """用户手动改过启动项后，再装一次不应该重复建条目。"""
    root, user_id = fake_steam
    exe = _make_exe(tmp_path)
    kwargs = dict(
        game_id="2002",
        display_name="Edited",
        exe_path=str(exe),
        launch_options="freedeckcy:tianyi:2002",
    )
    asyncio.run(sc.add_or_update_tianyi_shortcut(**kwargs))

    shortcuts_path = root / "userdata" / user_id / "config" / "shortcuts.vdf"
    payload = vdf.binary_loads(shortcuts_path.read_bytes())
    entry = list(payload["shortcuts"].values())[0]
    entry["LaunchOptions"] = "--user-args"
    shortcuts_path.write_bytes(vdf.binary_dumps(payload))

    result = asyncio.run(sc.add_or_update_tianyi_shortcut(**kwargs))
    assert result["action"] == "updated"

    payload = vdf.binary_loads(shortcuts_path.read_bytes())
    assert len(payload["shortcuts"]) == 1


def test_backup_created_before_rewrite(fake_steam, tmp_path):
    root, user_id = fake_steam
    exe = _make_exe(tmp_path)
    first_exe = exe
    second_exe = tmp_path / "OtherGame" / "Other.exe"
    second_exe.parent.mkdir()
    second_exe.write_bytes(b"MZ")

    asyncio.run(
        sc.add_or_update_tianyi_shortcut(
            game_id="2003",
            display_name="Backup-A",
            exe_path=str(first_exe),
            launch_options="freedeckcy:tianyi:2003",
        )
    )
    asyncio.run(
        sc.add_or_update_tianyi_shortcut(
            game_id="2004",
            display_name="Backup-B",
            exe_path=str(second_exe),
            launch_options="freedeckcy:tianyi:2004",
        )
    )

    config_dir = root / "userdata" / user_id / "config"
    backups = list(config_dir.glob("shortcuts.vdf.freedeckcy-bak-*"))
    assert backups, "写入 shortcuts.vdf 前应留备份"
    config_backups = list((root / "config").glob("config.vdf.freedeckcy-bak-*"))
    assert config_backups, "写入 config.vdf 前应留备份"
