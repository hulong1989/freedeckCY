# -*- coding: utf-8 -*-
"""game_catalog（游戏目录 CSV 加载/检索）单元测试。

全部使用 tmp_path 下的临时 CSV：不读取仓库里的默认目录、不联网、不写用户目录。
覆盖点：
  - utf-8-sig（BOM）读取；
  - 非法行统计（缺 title / 非 189 链接 / 缺列）；
  - title 空白标准化、game_id 缺失回退标题、size 字段回退格式化；
  - summary / list（关键词搜索 + 分页 + 参数归一化）/ get_by_game_id；
  - resolve_default_catalog_path 的候选路径优先级。
"""

from __future__ import annotations

import codecs
import csv
from pathlib import Path

import pytest

import decky
import game_catalog
from game_catalog import (
    GameCatalog,
    _format_size,
    _is_valid_tianyi_url,
    _normalize_title,
    _safe_int,
    resolve_default_catalog_path,
)

HEADER = [
    "game_id",
    "title",
    "category_parent",
    "categories",
    "down_url",
    "pwd",
    "openpath",
    "filesize_z",
    "list_filesize",
]

# 3 条合法行（第 3 条 game_id 为空，加载时应回退为 title）
VALID_ROWS = [
    [
        "1001",
        " 塞尔达\u3000传说 ",
        "主机游戏",
        "冒险,动作",
        "https://cloud.189.cn/t/zelda",
        "1234",
        "/games/zelda",
        "1073741824",
        "",
    ],
    [
        "1002",
        "Half-Life 2",
        "PC",
        "动作,射击",
        "http://cloud.189.cn/t/hl2",
        "",
        "",
        "",
        "12.5GB",
    ],
    ["", "  只 有 标题  ", "", "", "https://cloud.189.cn/t/titleonly", "", "", "2048", ""],
]

# 4 条非法行：缺 title / 非 189 链接 / 缺链接 / 缺列
INVALID_ROWS = [
    ["9001", "", "x", "y", "https://cloud.189.cn/t/missing-title", "", "", "0", ""],
    ["9002", "外部游戏", "x", "y", "https://example.com/game.zip", "", "", "0", ""],
    ["9003", "无链接游戏", "", "", "", "", "", "0", ""],
    ["9004"],
]


def write_catalog_csv(path: Path, rows, header=HEADER) -> Path:
    """写出带 UTF-8 BOM 的目录 CSV。"""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    return path


@pytest.fixture()
def catalog_csv(tmp_path: Path) -> Path:
    """合法 + 非法混合的临时 CSV。"""
    return write_catalog_csv(tmp_path / "catalog.csv", VALID_ROWS + INVALID_ROWS)


@pytest.fixture()
def catalog(catalog_csv: Path) -> GameCatalog:
    """已加载临时 CSV 的 GameCatalog 实例。"""
    instance = GameCatalog(str(catalog_csv))
    instance.load()
    return instance


# ---------------------------------------------------------------------------
# 加载与字段解析
# ---------------------------------------------------------------------------


def test_load_parses_valid_rows_and_counts_invalid(catalog: GameCatalog, catalog_csv: Path) -> None:
    assert len(catalog.entries) == 3
    assert catalog.invalid_rows == 4

    first = catalog.entries[0]
    assert first.game_id == "1001"
    assert first.title == "塞尔达 传说"  # 全角空格与首尾空白被标准化
    assert first.category_parent == "主机游戏"
    assert first.categories == "冒险,动作"
    assert first.down_url == "https://cloud.189.cn/t/zelda"
    assert first.pwd == "1234"
    assert first.openpath == "/games/zelda"
    assert first.size_bytes == 1073741824
    assert first.size_text == "1.00 GB"  # filesize_z 回退格式化

    second = catalog.entries[1]
    assert second.game_id == "1002"
    assert second.size_bytes == 0  # filesize_z 为空 -> 0
    assert second.size_text == "12.5GB"  # 有 list_filesize 时原样使用

    third = catalog.entries[2]
    assert third.game_id == third.title == "只 有 标题"  # game_id 缺省回退 title
    assert third.size_text == "2.00 KB"


def test_catalog_csv_has_utf8_bom(catalog_csv: Path) -> None:
    """确认 fixture 真实写出 BOM，并验证带 BOM 文件仍能正确解析表头。"""
    assert catalog_csv.read_bytes().startswith(codecs.BOM_UTF8)
    instance = GameCatalog(str(catalog_csv))
    instance.load()
    assert [entry.game_id for entry in instance.entries] == ["1001", "1002", "只 有 标题"]


def test_load_missing_or_empty_path_is_safe(tmp_path: Path) -> None:
    empty_path = GameCatalog("")
    empty_path.load()
    assert empty_path.entries == []
    assert empty_path.invalid_rows == 0

    missing = GameCatalog(str(tmp_path / "not-exists.csv"))
    missing.load()
    assert missing.entries == []
    assert missing.invalid_rows == 0


def test_to_dict_contains_frontend_fields(catalog: GameCatalog) -> None:
    payload = catalog.entries[0].to_dict()
    assert set(payload) == {
        "game_id",
        "title",
        "category_parent",
        "categories",
        "down_url",
        "pwd",
        "openpath",
        "size_bytes",
        "size_text",
    }
    assert payload["game_id"] == "1001"


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------


def test_summary_reports_totals_and_preview(catalog: GameCatalog, catalog_csv: Path) -> None:
    summary = catalog.summary()
    assert summary["path"] == str(catalog_csv)
    assert summary["total"] == 3
    assert summary["invalid"] == 4
    assert len(summary["preview"]) == 3
    assert summary["preview"][0]["game_id"] == "1001"


def test_summary_preview_is_capped_at_eight(tmp_path: Path) -> None:
    rows = [
        [str(2000 + index), f"游戏 {index}", "", "", "https://cloud.189.cn/t/x", "", "", "0", ""]
        for index in range(10)
    ]
    path = write_catalog_csv(tmp_path / "many.csv", rows)
    instance = GameCatalog(str(path))
    instance.load()
    assert len(instance.entries) == 10
    assert len(instance.summary()["preview"]) == 8


# ---------------------------------------------------------------------------
# list（关键词 + 分页）
# ---------------------------------------------------------------------------


def test_list_returns_all_when_query_empty(catalog: GameCatalog) -> None:
    result = catalog.list()
    assert result["total"] == 3
    assert result["page"] == 1
    assert result["page_size"] == 50
    assert [item["game_id"] for item in result["items"]] == ["1001", "1002", "只 有 标题"]


@pytest.mark.parametrize(
    ("query", "expected_ids"),
    [
        ("塞尔达", ["1001"]),  # 标题
        ("half", ["1002"]),  # 标题大小写不敏感
        ("射击", ["1002"]),  # categories
        ("1001", ["1001"]),  # game_id
        ("只 有", ["只 有 标题"]),  # 标准化后的标题
        ("不存在", []),
        ("  half  ", ["1002"]),  # query 首尾空白被忽略
    ],
)
def test_list_keyword_search(catalog: GameCatalog, query: str, expected_ids: list[str]) -> None:
    result = catalog.list(query=query)
    assert result["total"] == len(expected_ids)
    assert [item["game_id"] for item in result["items"]] == expected_ids


def test_list_pagination(catalog: GameCatalog) -> None:
    first_page = catalog.list(page=1, page_size=2)
    assert first_page["total"] == 3
    assert [item["game_id"] for item in first_page["items"]] == ["1001", "1002"]

    second_page = catalog.list(page=2, page_size=2)
    assert [item["game_id"] for item in second_page["items"]] == ["只 有 标题"]

    beyond = catalog.list(page=99, page_size=2)
    assert beyond["total"] == 3
    assert beyond["items"] == []


def test_list_normalizes_page_params(catalog: GameCatalog) -> None:
    assert catalog.list(page=0, page_size=0)["page"] == 1
    assert catalog.list(page=0, page_size=0)["page_size"] == 1
    # page_size 上限 200
    assert catalog.list(page_size=1000)["page_size"] == 200
    # 负数同样归一
    assert catalog.list(page=-3, page_size=-5)["page"] == 1
    assert catalog.list(page=-3, page_size=-5)["page_size"] == 1


# ---------------------------------------------------------------------------
# get_by_game_id
# ---------------------------------------------------------------------------


def test_get_by_game_id(catalog: GameCatalog) -> None:
    entry = catalog.get_by_game_id("1002")
    assert entry is not None
    assert entry.title == "Half-Life 2"

    # 首尾空白被忽略
    assert catalog.get_by_game_id(" 1002 ").game_id == "1002"  # type: ignore[union-attr]
    # game_id 缺省回退后的标题也可命中
    assert catalog.get_by_game_id("只 有 标题").game_id == "只 有 标题"  # type: ignore[union-attr]
    # 空值 / 不存在
    assert catalog.get_by_game_id("") is None
    assert catalog.get_by_game_id("   ") is None
    assert catalog.get_by_game_id("nope") is None
    assert catalog.get_by_game_id(None) is None  # type: ignore[arg-type]


def test_get_by_game_id_on_empty_catalog() -> None:
    assert GameCatalog("").get_by_game_id("1001") is None


# ---------------------------------------------------------------------------
# 纯函数
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        (0, "0 B"),
        (1023, "1023 B"),
        (1024, "1.00 KB"),
        (1536, "1.50 KB"),
        (1048576, "1.00 MB"),
        (1073741824, "1.00 GB"),
        (1099511627776, "1.00 TB"),
    ],
)
def test_format_size(size: int, expected: str) -> None:
    assert _format_size(size) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("42", 42),
        (" 42 ", 42),
        ("-7", -7),
        ("", 0),
        ("abc", 0),
        ("12.5", 0),  # 非整数按 0 处理
        (None, 0),
    ],
)
def test_safe_int(raw, expected: int) -> None:
    assert _safe_int(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" 塞尔达\u3000传说 ", "塞尔达 传说"),
        ("a   b\tc", "a b c"),
        ("", ""),
        (None, ""),  # type: ignore[arg-type]
    ],
)
def test_normalize_title(raw, expected: str) -> None:
    assert _normalize_title(raw) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://cloud.189.cn/t/abc", True),
        ("http://cloud.189.cn/t/abc", True),
        ("  https://cloud.189.cn/t/abc  ", True),  # 首尾空白被忽略
        ("https://cloud.189.cn/web/share?code=x", False),  # 非 /t/ 分享链接
        ("https://example.com/t/abc", False),
        ("https://cloud.189.cn.evil.com/t/abc", False),
        ("", False),
        (None, False),  # type: ignore[arg-type]
    ],
)
def test_is_valid_tianyi_url(url, expected: bool) -> None:
    assert _is_valid_tianyi_url(url) is expected


# ---------------------------------------------------------------------------
# resolve_default_catalog_path
# ---------------------------------------------------------------------------


def test_resolve_default_catalog_path_prefers_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    csv_path = write_catalog_csv(tmp_path / "env.csv", VALID_ROWS)
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()
    monkeypatch.setenv("FRIENDECK_GAME_CATALOG_CSV", str(csv_path))
    monkeypatch.setattr(decky, "DECKY_PLUGIN_DIR", str(plugin_dir))
    monkeypatch.chdir(tmp_path)

    assert resolve_default_catalog_path() == str(csv_path.resolve())


def test_resolve_default_catalog_path_falls_back_to_plugin_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FRIENDECK_GAME_CATALOG_CSV", raising=False)
    plugin_dir = tmp_path / "plugin"
    default_csv = plugin_dir / "defaults" / "tianyi_catalog" / "gamebox_all_links_20260221_234730.csv"
    default_csv.parent.mkdir(parents=True)
    default_csv.write_text("header\n", encoding="utf-8")
    monkeypatch.setattr(decky, "DECKY_PLUGIN_DIR", str(plugin_dir))
    monkeypatch.chdir(tmp_path)

    assert resolve_default_catalog_path() == str(default_csv.resolve())


def test_resolve_default_catalog_path_returns_empty_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FRIENDECK_GAME_CATALOG_CSV", raising=False)
    plugin_dir = tmp_path / "empty-plugin"
    plugin_dir.mkdir()
    empty_cwd = tmp_path / "empty-cwd"
    empty_cwd.mkdir()
    monkeypatch.setattr(decky, "DECKY_PLUGIN_DIR", str(plugin_dir))
    monkeypatch.chdir(empty_cwd)

    assert resolve_default_catalog_path() == ""


def test_resolve_default_catalog_path_skips_invalid_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """env 指向不存在的文件时继续尝试后续候选，而不是直接报错。"""
    monkeypatch.setenv("FRIENDECK_GAME_CATALOG_CSV", str(tmp_path / "missing.csv"))
    plugin_dir = tmp_path / "plugin"
    default_csv = plugin_dir / "defaults" / "tianyi_catalog.csv"
    default_csv.parent.mkdir(parents=True)
    default_csv.write_text("header\n", encoding="utf-8")
    monkeypatch.setattr(decky, "DECKY_PLUGIN_DIR", str(plugin_dir))
    monkeypatch.chdir(tmp_path)

    assert resolve_default_catalog_path() == str(default_csv.resolve())


def test_module_public_symbols_are_importable() -> None:
    """冒烟：模块可独立导入，关键符号存在。"""
    assert hasattr(game_catalog, "GameCatalog")
    assert hasattr(game_catalog, "GameCatalogEntry")
