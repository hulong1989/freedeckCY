#!/usr/bin/env python3
"""normalize_catalog_categories.py - 清洗目录 CSV 的 categories 字段。

- 去掉混进分类里的平台名（GBA / Switch / FC ...）
- 统一逗号分隔、去重
- 模拟器行清洗后为空时补 "模拟器"

用法：
  python3 scripts/normalize_catalog_categories.py \
      defaults/tianyi_catalog/freedeckcy_catalog.csv

默认原地改写（先写临时文件再原子替换），加 --check 只检查不写入。
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import tempfile
import types

# game_catalog 顶部 import decky；脚本环境里给个最小桩
sys.modules.setdefault("decky", types.ModuleType("decky"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "py_modules"))

from game_catalog import normalize_categories  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="清洗目录 categories 字段")
    parser.add_argument("csv_path")
    parser.add_argument("--check", action="store_true", help="只报告差异，不写文件")
    args = parser.parse_args()

    path = os.path.abspath(args.csv_path)
    if not os.path.isfile(path):
        print(f"[normalize] 文件不存在: {path}", file=sys.stderr)
        return 2

    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]

    if "categories" not in fieldnames or "platform" not in fieldnames:
        print("[normalize] CSV 缺少 categories/platform 列", file=sys.stderr)
        return 2

    changed = 0
    emptied_pc = 0
    filled_emu = 0
    for row in rows:
        old = str(row.get("categories") or "").strip()
        platform = str(row.get("platform") or "pc").strip().lower() or "pc"
        new = normalize_categories(old, platform)
        if new != old:
            changed += 1
            if not new:
                emptied_pc += 1
            elif not old and new:
                filled_emu += 1
            row["categories"] = new

    print(f"[normalize] 总行数: {len(rows)}，改动: {changed}")
    print(f"[normalize] 清洗后为空(PC): {emptied_pc}，补为“模拟器”: {filled_emu}")

    if args.check:
        return 0

    directory = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".catalog-", suffix=".csv", dir=directory)
    os.close(fd)
    try:
        with open(tmp_path, "w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    print(f"[normalize] 已写入: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
