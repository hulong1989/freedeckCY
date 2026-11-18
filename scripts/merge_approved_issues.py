#!/usr/bin/env python3
"""定时合并带 auto-merge 标签的 GitHub Issue 到服务器目录 CSV。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "py_modules"))

from issue_to_submission import parse_issue_body  # noqa: E402
from submission import CATALOG_PATH, SUBMISSION_DIR, merge_submissions  # noqa: E402


def _gh(*args: str) -> None:
    subprocess.run(["gh", *args], check=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("issues_json")
    args = parser.parse_args()
    try:
        issues = json.loads(Path(args.issues_json).read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[scheduled-merge] 读取 issues 失败: {exc}")
        return 2
    if not isinstance(issues, list):
        return 2

    merged = 0
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        number = str(issue.get("number", "") or "").strip()
        title = str(issue.get("title", "") or "").strip()
        body = str(issue.get("body", "") or "")
        if not number or not title.startswith("[游戏提交]"):
            continue
        data = parse_issue_body(body)
        missing = [field for field in ("name", "platform", "share_url", "openpath") if not data.get(field)]
        if missing:
            _gh("issue", "comment", number, "--body", f"❌ 定时合并失败：缺少字段 {', '.join(missing)}")
            _gh("issue", "edit", number, "--remove-label", "auto-merge")
            continue
        data["notes"] = (data.get("notes", "") + f"\nIssue #{number}").strip()
        target = SUBMISSION_DIR / f"issue-{number}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result = merge_submissions(SUBMISSION_DIR, CATALOG_PATH, apply=True)
        if result.get("ok"):
            merged += 1
            _gh(
                "issue",
                "comment",
                number,
                "--body",
                "✅ 已定时合并进服务器 CSV。玩家在插件设置页点「更新游戏列表」下载最新 CSV 后即可看到。",
            )
            _gh("issue", "close", number)
        else:
            errors = []
            for item in (result.get("validation") or {}).get("files", []):
                errors.extend(item.get("errors") or [])
            _gh("issue", "comment", number, "--body", "❌ 定时合并校验失败：\n\n" + "\n".join(f"- {e}" for e in errors[:8]))
            _gh("issue", "edit", number, "--remove-label", "auto-merge")
            try:
                target.unlink()
            except OSError:
                pass
    print(f"[scheduled-merge] merged={merged}")
    return 0 if merged >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
