#!/usr/bin/env python3
"""validate_catalog.py - 目录 CSV 数据体检。

检查项：
  - 必需列 / 行数 / 平台分布
  - game_id、down_url 重复
  - 链接是否为支持的天翼分享格式
  - 标题、分类为空
  - 分类里是否混入平台名
  - 封面覆盖率（可选 cover_index.csv）

用法：
  python3 scripts/validate_catalog.py defaults/tianyi_catalog/freedeckcy_catalog.csv
  python3 scripts/validate_catalog.py ... --cover-index defaults/tianyi_catalog/cover_index.csv --strict

默认退出码 0；--strict 时发现硬错误（重复 game_id、非法链接、空标题、平台名混入分类）返回 1。
"""

from __future__ import annotations

import argparse
import collections
import csv
import os
import sys
from typing import Dict, List

REQUIRED_COLUMNS = {"game_id", "title", "down_url", "platform", "categories"}
PLATFORM_TOKENS = {
    "pc",
    "fc",
    "nds",
    "psp",
    "gba",
    "3ds",
    "ps1",
    "ps2",
    "ps3",
    "md",
    "switch",
    "ns",
    "arcade",
    "psx",
}


def _is_tianyi_url(url: str) -> bool:
    value = str(url or "").strip().lower()
    if not (value.startswith("https://cloud.189.cn/") or value.startswith("http://cloud.189.cn/")):
        return False
    return "/t/" in value or ("/web/share" in value and "code=" in value)


def _load_cover_ids(path: str) -> set:
    ids = set()
    if not path or not os.path.isfile(path):
        return ids
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            game_id = str(row.get("game_id") or "").strip()
            if game_id:
                ids.add(game_id)
    return ids


def main() -> int:
    parser = argparse.ArgumentParser(description="目录 CSV 数据体检")
    parser.add_argument("csv_path")
    parser.add_argument("--cover-index", default="")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    path = os.path.abspath(args.csv_path)
    if not os.path.isfile(path):
        print(f"[validate] 文件不存在: {path}", file=sys.stderr)
        return 2

    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        columns = set(reader.fieldnames or [])
        rows: List[Dict[str, str]] = [dict(row) for row in reader]

    errors: List[str] = []
    warnings: List[str] = []

    missing_columns = REQUIRED_COLUMNS - columns
    if missing_columns:
        errors.append(f"缺少必需列: {sorted(missing_columns)}")

    ids: collections.Counter = collections.Counter()
    urls: collections.Counter = collections.Counter()
    platforms: collections.Counter = collections.Counter()
    categories: collections.Counter = collections.Counter()
    empty_title = 0
    empty_category = 0
    bad_url = 0
    with_cover = 0
    total_size = 0
    platform_in_category = 0

    for row in rows:
        game_id = str(row.get("game_id") or "").strip()
        title = str(row.get("title") or "").strip()
        down_url = str(row.get("down_url") or "").strip()
        platform = str(row.get("platform") or "pc").strip().lower() or "pc"
        category = str(row.get("categories") or "").strip()

        ids[game_id] += 1
        urls[down_url] += 1
        platforms[platform] += 1
        try:
            total_size += max(0, int(str(row.get("filesize_z") or "0").strip() or 0))
        except Exception:
            pass

        if not title:
            empty_title += 1
        if not category:
            empty_category += 1
        if not _is_tianyi_url(down_url):
            bad_url += 1
        if str(row.get("cover_url") or "").strip() or str(row.get("cover_portrait_url") or "").strip():
            with_cover += 1
        for token in category.split(","):
            name = token.strip()
            if not name:
                continue
            categories[name] += 1
            if name.lower() in PLATFORM_TOKENS:
                platform_in_category += 1

    duplicate_ids = [game_id for game_id, count in ids.items() if game_id and count > 1]
    duplicate_urls = [url for url, count in urls.items() if url and count > 1]
    empty_id = ids.get("", 0)

    if duplicate_ids:
        errors.append(f"重复 game_id: {len(duplicate_ids)} 个（示例 {duplicate_ids[:3]}）")
    if empty_id:
        errors.append(f"空 game_id: {empty_id} 行")
    if bad_url:
        errors.append(f"非法/不支持的链接: {bad_url} 行")
    if empty_title:
        errors.append(f"空标题: {empty_title} 行")
    if platform_in_category:
        errors.append(f"分类里混入平台名: {platform_in_category} 处")
    if empty_category:
        warnings.append(f"空分类: {empty_category} 行")
    if duplicate_urls:
        warnings.append(f"重复 down_url: {len(duplicate_urls)} 个（同一分享多条目属正常）")

    cover_ids = _load_cover_ids(args.cover_index)
    cover_index_hits = sum(1 for row in rows if str(row.get("game_id") or "").strip() in cover_ids)
    covered_total = sum(
        1
        for row in rows
        if str(row.get("cover_url") or "").strip()
        or str(row.get("cover_portrait_url") or "").strip()
        or str(row.get("game_id") or "").strip() in cover_ids
    )

    print(f"文件: {path}")
    print(f"行数: {len(rows)}，列数: {len(columns)}")
    print(f"平台分布: {sorted(platforms.items(), key=lambda kv: -kv[1])}")
    print(f"分类 Top10: {categories.most_common(10)}")
    print(f"自带封面: {with_cover}/{len(rows)}（{with_cover * 100.0 / max(1, len(rows)):.1f}%）")
    print(f"封面覆盖（含 cover_index）: {covered_total}/{len(rows)}（{covered_total * 100.0 / max(1, len(rows)):.1f}%）")
    if args.cover_index:
        print(f"命中 cover_index: {cover_index_hits}（索引 {len(cover_ids)} 行）")
    print(f"资源总大小: {total_size / (1024 ** 3):.1f} GB")

    if errors:
        print("\n[错误]")
        for item in errors:
            print(f"  - {item}")
    if warnings:
        print("\n[警告]")
        for item in warnings:
            print(f"  - {item}")
    if not errors:
        print("\n目录校验通过。")

    return 1 if (args.strict and errors) else 0


if __name__ == "__main__":
    raise SystemExit(main())
