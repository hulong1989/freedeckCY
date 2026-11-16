#!/usr/bin/env python3
"""校验 submissions/*.json（CI 与本地使用）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "py_modules"))

from submission import CATALOG_PATH, SUBMISSION_DIR, validate_submission_files  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="校验仓库游戏提交 JSON")
    parser.add_argument("--dir", default=str(SUBMISSION_DIR))
    parser.add_argument("--catalog", default=str(CATALOG_PATH))
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    result = validate_submission_files(Path(args.dir), Path(args.catalog))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if not result["files"]:
            print("[submissions] 没有待校验的 JSON")
        for item in result["files"]:
            status = "OK" if not item["errors"] else "FAIL"
            print(f"[{status}] {item['file']}")
            for warning in item["warnings"]:
                print(f"  warn: {warning}")
            for error in item["errors"]:
                print(f"  error: {error}")
        print(
            f"[submissions] files={len(result['files'])} "
            f"errors={result['error_count']} warnings={result['warning_count']}"
        )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
