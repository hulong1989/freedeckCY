"""目录/任务里的可选启动文件 executable_name。"""

from __future__ import annotations

import types
from pathlib import Path

from game_catalog import GameCatalog
from tianyi_service import TianyiService

HEADER = (
    "game_id,title,category_parent,categories,package_name,server,down_url,shorturl,pwd,"
    "openpath,filesize_z,list_filesize,platform,cover_url,cover_portrait_url,steam_appid,executable_name\n"
)


def test_catalog_reads_optional_executable_name(tmp_path):
    path = tmp_path / "catalog.csv"
    path.write_text(
        HEADER
        + "1,GameA,5,动作,,t,https://cloud.189.cn/t/abc1,abc1,pwd,GameA/GameA.7z,0,,pc,,,0,GameA/Launcher.exe\n"
        + "2,GameB,5,动作,,t,https://cloud.189.cn/t/abc2,abc2,pwd,GameB/GameB.7z,0,,pc,,,0,\n",
        encoding="utf-8-sig",
    )
    catalog = GameCatalog(str(path))
    catalog.load()
    by_id = {entry.game_id: entry for entry in catalog.entries}
    assert by_id["1"].executable_name == "GameA/Launcher.exe"
    assert by_id["2"].executable_name == ""


def test_declared_executable_is_preferred(tmp_path):
    root = tmp_path / "installed" / "GameA"
    (root / "bin").mkdir(parents=True)
    launcher = root / "bin" / "Launcher.exe"
    launcher.write_bytes(b"MZ")
    (root / "Other.exe").write_bytes(b"MZ")

    service = TianyiService.__new__(TianyiService)
    task = types.SimpleNamespace(executable_name="bin/Launcher.exe", openpath="GameA/GameA.7z")
    resolved = service._resolve_installed_executable_path(task=task, target_dir=str(root))
    assert resolved == str(launcher.resolve())

    entry = types.SimpleNamespace(executable_name="bin/Launcher.exe", openpath="GameA/GameA.7z", title="GameA")
    assert service._find_scanned_executable(str(root), entry) == str(launcher.resolve())
