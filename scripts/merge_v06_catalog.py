#!/usr/bin/env python3
"""merge_v06_catalog.py - 把上游 v0.6 的目录与封面索引合并成本仓库格式。

用法：
  python3 scripts/merge_v06_catalog.py \
      --v06-dir ../0.6/freedeck-plugin/defaults/tianyi_catalog \
      --base defaults/tianyi_catalog/gamebox_all_links_20260221_234730.csv \
      --out defaults/tianyi_catalog/freedeckcy_catalog.csv \
      --cover-out defaults/tianyi_catalog/cover_index.csv

规则：
1. 以 v0.6 的 freedeck_catalog.csv 为主（28 列、含 platform/封面/appid）；
2. 只保留天翼云盘链接（本插件当前唯一支持的下载源）；
3. 按 game_id 去重；v0.6 没有的旧目录条目会补在后面（platform=pc）；
4. 封面索引转换为本仓库的 6 列格式，按 game_id 去重。
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import types
from typing import Dict, List

# game_catalog 顶部 import decky；脚本环境里给个最小桩
sys.modules.setdefault("decky", types.ModuleType("decky"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "py_modules"))

from game_catalog import normalize_categories  # noqa: E402

OUT_COLUMNS = [
    "game_id",
    "title",
    "category_parent",
    "categories",
    "package_name",
    "server",
    "down_url",
    "shorturl",
    "pwd",
    "openpath",
    "filesize_z",
    "list_filesize",
    "platform",
    "cover_url",
    "cover_portrait_url",
    "steam_appid",
]

COVER_COLUMNS = [
    "game_id",
    "title",
    "steam_appid",
    "cover_url",
    "cover_portrait_url",
    "platform",
]

PLATFORM_ALIASES = {"ns": "switch", "nsx": "switch"}


def _norm_platform(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "pc"
    return PLATFORM_ALIASES.get(text, text)


def _str(row: Dict[str, str], *names: str, default: str = "") -> str:
    for name in names:
        value = str(row.get(name, "") or "").strip()
        if value:
            return value
    return default


def _is_tianyi(url: str) -> bool:
    value = str(url or "").strip().lower()
    return value.startswith("https://cloud.189.cn/") or value.startswith("http://cloud.189.cn/")


def _read_csv(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def _from_v06(row: Dict[str, str]) -> Dict[str, str]:
    return {
        "game_id": _str(row, "game_id"),
        "title": _str(row, "title", "title_zh"),
        "category_parent": _str(row, "category_parent"),
        "package_name": _str(row, "package_name"),
        "server": _str(row, "server", default="t"),
        "down_url": _str(row, "down_url"),
        "shorturl": _str(row, "shorturl"),
        "pwd": _str(row, "pwd"),
        "openpath": _str(row, "openpath"),
        "filesize_z": _str(row, "filesize_z", "size_bytes", default="0"),
        "list_filesize": _str(row, "list_filesize", "size_text"),
        "platform": _norm_platform(row.get("platform")),
        "categories": normalize_categories(row.get("categories"), _norm_platform(row.get("platform"))),
        "cover_url": _str(row, "cover_url"),
        "cover_portrait_url": _str(row, "square_cover_url", "cover_portrait_url"),
        "steam_appid": _str(row, "steam_appid", "app_id", default="0"),
    }


def _from_base(row: Dict[str, str]) -> Dict[str, str]:
    return {
        "game_id": _str(row, "game_id"),
        "title": _str(row, "title"),
        "category_parent": _str(row, "category_parent"),
        "package_name": _str(row, "package_name"),
        "server": _str(row, "server", default="t"),
        "down_url": _str(row, "down_url"),
        "shorturl": _str(row, "shorturl"),
        "pwd": _str(row, "pwd"),
        "openpath": _str(row, "openpath"),
        "filesize_z": _str(row, "filesize_z", default="0"),
        "list_filesize": _str(row, "list_filesize"),
        "platform": _norm_platform(row.get("platform")),
        "categories": normalize_categories(row.get("categories"), _norm_platform(row.get("platform"))),
        "cover_url": _str(row, "cover_url"),
        "cover_portrait_url": _str(row, "cover_portrait_url"),
        "steam_appid": _str(row, "steam_appid", default="0"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="合并 v0.6 目录到 freedeckCY 格式")
    parser.add_argument("--v06-dir", required=True)
    parser.add_argument("--base", default="defaults/tianyi_catalog/gamebox_all_links_20260221_234730.csv")
    parser.add_argument("--out", default="defaults/tianyi_catalog/freedeckcy_catalog.csv")
    parser.add_argument("--cover-out", default="defaults/tianyi_catalog/cover_index.csv")
    args = parser.parse_args()

    v06_catalog = os.path.join(args.v06_dir, "freedeck_catalog.csv")
    v06_cover = os.path.join(args.v06_dir, "freedeck_cover_index.csv")
    for path in (v06_catalog, v06_cover):
        if not os.path.isfile(path):
            print(f"[merge] 缺少文件: {path}", file=sys.stderr)
            return 2

    merged: Dict[str, Dict[str, str]] = {}
    order: List[str] = []
    skipped = 0

    for row in _read_csv(v06_catalog):
        item = _from_v06(row)
        if not item["game_id"] or not item["title"] or not _is_tianyi(item["down_url"]):
            skipped += 1
            continue
        if item["game_id"] in merged:
            continue
        merged[item["game_id"]] = item
        order.append(item["game_id"])
    v06_count = len(order)

    added_from_base = 0
    if os.path.isfile(args.base):
        for row in _read_csv(args.base):
            item = _from_base(row)
            if not item["game_id"] or not item["title"] or not _is_tianyi(item["down_url"]):
                skipped += 1
                continue
            if item["game_id"] in merged:
                continue
            merged[item["game_id"]] = item
            order.append(item["game_id"])
            added_from_base += 1

    # 排序：PC 优先，再按平台/标题，方便浏览
    def sort_key(game_id: str):
        item = merged[game_id]
        platform = item["platform"]
        return (0 if platform == "pc" else 1, platform, item["title"].lower())

    order.sort(key=sort_key)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUT_COLUMNS)
        writer.writeheader()
        for game_id in order:
            writer.writerow(merged[game_id])

    # 封面索引
    cover_rows: Dict[str, Dict[str, str]] = {}
    for row in _read_csv(v06_cover):
        game_id = _str(row, "game_id")
        if not game_id or game_id in cover_rows:
            continue
        cover_rows[game_id] = {
            "game_id": game_id,
            "title": _str(row, "title"),
            "steam_appid": _str(row, "steam_appid", "app_id", default="0"),
            "cover_url": _str(row, "cover_url"),
            "cover_portrait_url": _str(row, "square_cover_url", "cover_portrait_url"),
            "platform": _norm_platform(row.get("platform")),
        }
    os.makedirs(os.path.dirname(args.cover_out), exist_ok=True)
    with open(args.cover_out, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COVER_COLUMNS)
        writer.writeheader()
        for game_id in sorted(cover_rows):
            writer.writerow(cover_rows[game_id])

    platforms: Dict[str, int] = {}
    for item in merged.values():
        platforms[item["platform"]] = platforms.get(item["platform"], 0) + 1

    print(f"[merge] v0.6 条目: {v06_count}")
    print(f"[merge] 旧目录补充: {added_from_base}")
    print(f"[merge] 合并后总数: {len(merged)}（跳过 {skipped} 行无效数据）")
    print(f"[merge] 平台分布: {sorted(platforms.items(), key=lambda kv: -kv[1])}")
    print(f"[merge] 输出: {args.out}")
    print(f"[merge] 封面索引: {len(cover_rows)} 行 -> {args.cover_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
