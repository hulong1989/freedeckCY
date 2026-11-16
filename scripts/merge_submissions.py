#!/usr/bin/env python3
"""把校验通过的 submissions/*.json 合并进目录 CSV。

默认 dry-run；确认后加 --apply 才会写入目录并移动文件到 submissions/merged/。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "py_modules"))

from submission import CATALOG_PATH, SUBMISSION_DIR, merge_submissions  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="合并仓库游戏提交")
    parser.add_argument("--dir", default=str(SUBMISSION_DIR))
    parser.add_argument("--catalog", default=str(CATALOG_PATH))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="写入 CSV 并移动已合并文件")
    mode.add_argument("--dry-run", action="store_true", help="只预览（默认）")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = merge_submissions(Path(args.dir), Path(args.catalog), apply=args.apply)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif not result.get("ok"):
        print(f"[submissions] 合并失败：{result.get('message', '校验错误')}")
        for item in (result.get("validation") or {}).get("files", []):
            for error in item.get("errors", []):
                print(f"  {item.get('file')}: {error}")
    else:
        rows = result.get("rows", [])
        if not rows:
            print("[submissions] 没有待合并的提交")
        for item in rows:
            row = item["row"]
            print(
                f"{item['file']} -> game_id={row['game_id']} "
                f"title={row['title']} platform={row['platform']} openpath={row['openpath']}"
            )
        print(f"[submissions] {'已写入' if result.get('applied') else 'dry-run'}：{len(rows)} 条")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
