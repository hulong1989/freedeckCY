"""双网盘目录分组。"""

from __future__ import annotations

import csv
from pathlib import Path

from game_catalog import GameCatalog

FIELDS = [
    "game_id", "title", "category_parent", "categories", "package_name", "server",
    "down_url", "shorturl", "pwd", "openpath", "filesize_z", "list_filesize",
    "platform", "cover_url", "cover_portrait_url", "steam_appid",
]


def _write_catalog(path: Path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _row(game_id, server, url, title="Same Game"):
    return {
        "game_id": game_id, "title": title, "server": server, "down_url": url,
        "openpath": "Game/Game.7z", "platform": "pc", "filesize_z": "1024",
        "list_filesize": "1 KB",
    }


def test_dual_provider_title_is_one_item_with_choices(tmp_path):
    path = tmp_path / "catalog.csv"
    _write_catalog(path, [
        _row("t1", "t", "https://cloud.189.cn/t/abc123"),
        _row("b1", "b", "https://pan.baidu.com/s/1AbCdEf"),
    ])
    catalog = GameCatalog(str(path))
    catalog.load()
    result = catalog.list(page_size=10)
    assert result["total"] == 1
    item = result["items"][0]
    assert item["provider"] == "tianyi"
    assert [p["provider"] for p in item["providers"]] == ["tianyi", "baidu"]
    assert [p["game_id"] for p in item["providers"]] == ["t1", "b1"]


def test_same_provider_duplicates_are_not_merged(tmp_path):
    path = tmp_path / "catalog.csv"
    _write_catalog(path, [
        _row("t1", "t", "https://cloud.189.cn/t/abc123"),
        _row("t2", "t", "https://cloud.189.cn/t/def456"),
    ])
    catalog = GameCatalog(str(path))
    catalog.load()
    result = catalog.list(page_size=10)
    assert result["total"] == 2
    assert all("providers" not in item for item in result["items"])
