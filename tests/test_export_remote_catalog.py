"""远程目录导出（NewFreedeck 兼容）测试。"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "export_remote_catalog.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("export_remote_catalog", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_split_titles():
    mod = _load_module()
    assert mod.split_titles("行走的贸易/The Walking Trade") == ("行走的贸易", "The Walking Trade")
    assert mod.split_titles("Fate/Unlimited Codes") == ("", "Fate/Unlimited Codes")
    assert mod.split_titles("纯中文名") == ("纯中文名", "")
    assert mod.split_titles("English Only") == ("", "English Only")
    assert mod.split_titles("中文/English/Extra") == ("中文", "English / Extra")


def test_to_remote_item_mapping():
    mod = _load_module()
    row = {
        "game_id": "42",
        "title": "测试/Test Game",
        "categories": "角色扮演",
        "down_url": "https://cloud.189.cn/t/abc",
        "pwd": "x1",
        "server": "t",
        "openpath": "Test Game/game.exe",
        "filesize_z": "2048",
        "list_filesize": "2 KB",
        "platform": "pc",
        "cover_url": "https://cdn/cover.jpg",
    }
    item = mod.to_remote_item(row)
    assert item["game_id"] == "42"
    assert item["title_zh"] == "测试"
    assert item["title_en"] == "Test Game"
    assert item["genre"] == "角色扮演"
    assert item["file_name"] == "game.exe"
    assert item["size_bytes"] == 2048
    assert item["cover_url"] == "https://cdn/cover.jpg"


def test_build_outputs_and_manifest(tmp_path):
    mod = _load_module()
    items = [
        {
            "game_id": "1",
            "title": "A",
            "title_zh": "",
            "title_en": "A",
            "platform": "gba",
            "cover_url": "",
            "size_text": "1 MB",
            "genre": "",
            "down_url": "https://cloud.189.cn/t/a",
            "file_name": "a.zip",
            "size_bytes": 100,
            "pwd": "",
            "server": "t",
            "version": "",
            "validity": "",
            "install_size_text": "",
            "install_size_bytes": 0,
        },
        {
            "game_id": "2",
            "title": "B",
            "title_zh": "",
            "title_en": "B",
            "platform": "gba",
            "cover_url": "https://cdn/b.jpg",
            "size_text": "2 MB",
            "genre": "",
            "down_url": "https://cloud.189.cn/t/b",
            "file_name": "b.zip",
            "size_bytes": 200,
            "pwd": "",
            "server": "t",
            "version": "",
            "validity": "",
            "install_size_text": "",
            "install_size_bytes": 0,
        },
        {
            "game_id": "3",
            "title": "C",
            "title_zh": "C",
            "title_en": "",
            "platform": "pc",
            "cover_url": "",
            "size_text": "3 MB",
            "genre": "",
            "down_url": "https://cloud.189.cn/t/c",
            "file_name": "c.zip",
            "size_bytes": 300,
            "pwd": "",
            "server": "t",
            "version": "",
            "validity": "",
            "install_size_text": "",
            "install_size_bytes": 0,
        },
    ]

    manifest = mod.build_outputs(items, str(tmp_path), curated_limit=1)

    assert manifest["total"] == 3
    assert manifest["platforms"] == {"gba": 2, "pc": 1}
    assert json.loads((tmp_path / "all.json").read_text()) == items

    gba = json.loads((tmp_path / "platform/gba.json").read_text())
    assert [item["game_id"] for item in gba] == ["1", "2"]

    curated = json.loads((tmp_path / "curated/gba.json").read_text())
    assert len(curated) == 1
    # 有封面的优先
    assert curated[0]["game_id"] == "2"

    for rel, info in manifest["files"].items():
        raw = (tmp_path / rel).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == info["sha256"]
        assert info["count"] >= 0


def test_load_items_skips_invalid(tmp_path):
    mod = _load_module()
    csv_path = tmp_path / "catalog.csv"
    csv_path.write_text(
        "game_id,title,platform,down_url,pwd,openpath,filesize_z,list_filesize,categories,cover_url,server\n"
        "1,Good,gba,https://cloud.189.cn/t/a,,a.zip,100,1 KB,模拟器,,\n"
        "2,Bad,gba,,,,,,,, ,\n",
        encoding="utf-8-sig",
    )
    items = mod.load_items(str(csv_path))
    assert [item["game_id"] for item in items] == ["1"]
