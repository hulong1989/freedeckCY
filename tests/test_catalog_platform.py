"""目录平台化 / 封面索引 / 封面磁盘缓存测试。"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path


import tianyi_service as svc_module
from game_catalog import GameCatalog, GameCatalogEntry
from tianyi_service import TianyiService


CSV_HEADER = (
    "game_id,title,category_parent,categories,package_name,server,down_url,shorturl,pwd,"
    "openpath,filesize_z,list_filesize,platform,cover_url,cover_portrait_url,steam_appid\n"
)


def _tmp_dir() -> Path:
    import tempfile

    return Path(tempfile.mkdtemp(prefix="catalog-test-"))


def _write_catalog(tmp_path: Path, rows: list[str]) -> str:
    path = tmp_path / "catalog.csv"
    path.write_text(CSV_HEADER + "\n".join(rows) + "\n", encoding="utf-8-sig")
    return str(path)


def _row(
    game_id: str,
    title: str,
    categories: str = "动作冒险",
    platform: str = "pc",
    cover_url: str = "",
    portrait: str = "",
    appid: str = "0",
) -> str:
    return (
        f"{game_id},{title},5,{categories},,t,https://cloud.189.cn/t/abc{game_id},abc{game_id},pwd,"
        f"{title}/game.exe,1000,1 KB,{platform},{cover_url},{portrait},{appid}"
    )


def test_reads_platform_and_cover_columns(tmp_path):
    csv_path = _write_catalog(
        tmp_path,
        [
            _row("1", "GameA", platform="pc", cover_url="https://cdn/a.jpg", portrait="https://cdn/a9.jpg", appid="100"),
            _row("2", "GameB", platform="switch"),
            _row("3", "GameC", platform=""),
        ],
    )
    catalog = GameCatalog(csv_path)
    catalog.load()

    by_id = {entry.game_id: entry for entry in catalog.entries}
    assert by_id["1"].platform == "pc"
    assert by_id["1"].cover_url == "https://cdn/a.jpg"
    assert by_id["1"].cover_portrait_url == "https://cdn/a9.jpg"
    assert by_id["1"].steam_appid == 100
    assert by_id["2"].platform == "switch"
    # 空平台默认为 pc
    assert by_id["3"].platform == "pc"

    summary = catalog.summary()
    assert summary["with_cover"] == 1
    assert summary["platforms"] == [
        {"value": "pc", "label": "PC", "count": 2},
        {"value": "switch", "label": "switch", "count": 1},
    ]


def test_cover_index_merge_does_not_override_csv(tmp_path):
    csv_path = _write_catalog(
        tmp_path,
        [
            _row("10", "WithCover", cover_url="https://csv/cover.jpg", appid="0"),
            _row("11", "ByTitle"),
        ],
    )
    index_path = tmp_path / "cover_index.csv"
    index_path.write_text(
        "game_id,title,steam_appid,cover_url,cover_portrait_url,platform\n"
        "10,WithCover,999,https://index/cover.jpg,https://index/p.jpg,pc\n"
        "11,ByTitle,888,https://index/b.jpg,https://index/b9.jpg,pc\n",
        encoding="utf-8",
    )
    catalog = GameCatalog(csv_path, cover_index_path=str(index_path))
    catalog.load()

    by_id = {entry.game_id: entry for entry in catalog.entries}
    # CSV 已有封面不被覆盖，但 appid 会被补上
    assert by_id["10"].cover_url == "https://csv/cover.jpg"
    assert by_id["10"].steam_appid == 999
    # 标题匹配
    assert by_id["11"].steam_appid == 888
    assert by_id["11"].cover_url == "https://index/b.jpg"
    assert by_id["11"].cover_portrait_url == "https://index/b9.jpg"
    assert catalog.cover_index_total == 2


def test_list_filters_by_platform_and_category(tmp_path):
    csv_path = _write_catalog(
        tmp_path,
        [
            _row("1", "PC Action", categories="动作冒险", platform="pc"),
            _row("2", "PC RPG", categories="角色扮演", platform="pc"),
            _row("3", "Switch Action", categories="动作冒险", platform="switch"),
        ],
    )
    catalog = GameCatalog(csv_path)
    catalog.load()

    action = catalog.list(query="", page=1, page_size=10, category="动作冒险")
    assert action["total"] == 2
    assert {item["game_id"] for item in action["items"]} == {"1", "3"}
    assert isinstance(action["categories"], list)
    assert any(row["value"] == "动作冒险" for row in action["categories"])

    switch_only = catalog.list(query="", page=1, page_size=10, platform="switch")
    assert switch_only["total"] == 1
    assert switch_only["items"][0]["platform"] == "switch"

    combined = catalog.list(query="action", page=1, page_size=10, platform="switch", category="动作冒险")
    assert combined["total"] == 1
    assert combined["items"][0]["game_id"] == "3"

    assert catalog.list(query="", page=1, page_size=10, platform="all")["total"] == 3


def test_category_counts_are_sorted(tmp_path):
    csv_path = _write_catalog(
        tmp_path,
        [
            _row("1", "A", categories="动作冒险"),
            _row("2", "B", categories="动作冒险"),
            _row("3", "C", categories="策略战棋"),
        ],
    )
    catalog = GameCatalog(csv_path)
    catalog.load()
    counts = catalog.category_counts()
    assert counts[0]["value"] == "动作冒险"
    assert counts[0]["count"] == 2


def test_cover_cache_roundtrip_and_expiry(tmp_path):
    service = TianyiService.__new__(TianyiService)
    service._cover_cache_path = str(tmp_path / "cover_cache.json")
    service._catalog_cover_cache = {
        "fresh": {"cover_url": "https://a", "expires_at": 9_999_999_999},
        "stale": {"cover_url": "https://b", "expires_at": 1},
    }

    service._save_cover_cache()
    payload = json.loads(Path(service._cover_cache_path).read_text(encoding="utf-8"))
    assert "fresh" in payload and "stale" in payload
    mode = stat.S_IMODE(os.stat(service._cover_cache_path).st_mode)
    assert mode == 0o600

    reloaded = TianyiService.__new__(TianyiService)
    reloaded._cover_cache_path = service._cover_cache_path
    reloaded._catalog_cover_cache = {}
    reloaded._load_cover_cache()

    assert "fresh" in reloaded._catalog_cover_cache
    assert "stale" not in reloaded._catalog_cover_cache


def test_static_cover_from_catalog_appid(tmp_path):
    service = TianyiService.__new__(TianyiService)

    class _FakeCatalog:
        def get_by_game_id(self, game_id: str):
            if game_id != "42":
                return None
            return GameCatalogEntry(
                game_id="42",
                title="Demo",
                category_parent="",
                categories="",
                down_url="https://cloud.189.cn/t/x",
                pwd="",
                openpath="",
                size_bytes=0,
                size_text="",
                platform="pc",
                cover_url="",
                cover_portrait_url="",
                steam_appid=777,
            )

    service.catalog = _FakeCatalog()
    cover = service._catalog_entry_cover("42")

    assert cover["source"] == "catalog"
    assert cover["app_id"] == 777
    assert cover["cover_url"].endswith("/777/header.jpg")
    assert cover["square_cover_url"].endswith("/777/library_600x900_2x.jpg")
    assert service._catalog_entry_cover("404") == {}


def test_default_catalog_loads_merged_file_with_platforms():
    """仓库自带的合并目录应包含多平台与封面索引。"""
    from game_catalog import resolve_default_catalog_path, resolve_default_cover_index_path

    catalog = GameCatalog(
        resolve_default_catalog_path(),
        cover_index_path=resolve_default_cover_index_path(),
    )
    catalog.load()

    assert len(catalog.entries) > 6000
    platforms = {row["value"] for row in catalog.platform_counts()}
    assert {"pc", "fc", "nds", "psp", "gba", "ps1", "ps2", "ps3", "md", "switch"} <= platforms
    assert catalog.cover_index_total > 3000
    assert sum(1 for entry in catalog.entries if entry.cover_url) > 3000


def test_web_share_url_is_accepted():
    from game_catalog import _is_valid_tianyi_url
    from tianyi_client import parse_share_url

    url = "https://cloud.189.cn/web/share?code=3MzqU3YjMn6v&pwd=lqe3"
    assert _is_valid_tianyi_url(url) is True
    code, pwd = parse_share_url(url)
    assert code == "3MzqU3YjMn6v"
    assert pwd == "lqe3"
