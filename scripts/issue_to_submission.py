#!/usr/bin/env python3
"""把 GitHub Issue 表单内容转成 submissions/*.json。

仓库维护者给 Issue 打 `auto-merge` 标签后，workflow 调用本脚本；
脚本只做解析/落盘，真正的校验与合并由 validate_submissions/merge_submissions 完成。
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict

# Issue 表单 heading -> submission 字段
FIELD_MAP = {
    "游戏名称（中文）": "name",
    "英文名 / 原名": "english_name",
    "平台": "platform",
    "分享链接": "share_url",
    "提取码": "access_code",
    "分享用户版本（可选）": "share_user_version",
    "可执行文件名（仅 PC）": "executable_name",
    "网盘内路径": "openpath",
    "分类（可选）": "categories",
    "压缩包大小（字节，可选）": "filesize_z",
    "备注": "notes",
}
_SECTION_RE = re.compile(r"^###\s+(.+?)\s*$", re.MULTILINE)


def parse_issue_body(body: str) -> Dict[str, str]:
    text = str(body or "").replace("\r\n", "\n").replace("\r", "\n")
    matches = list(_SECTION_RE.finditer(text))
    values: Dict[str, str] = {}
    for index, match in enumerate(matches):
        heading = match.group(1).strip()
        field = FIELD_MAP.get(heading)
        if not field:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        value = text[start:end].strip()
        if value in {"_No response_", "No response"}:
            value = ""
        values[field] = value
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description="Issue 表单转 submission JSON")
    parser.add_argument("--body-file", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--issue-number", default="")
    args = parser.parse_args()

    body = Path(args.body_file).read_text(encoding="utf-8")
    data = parse_issue_body(body)
    missing = [field for field in ("name", "platform", "share_url", "openpath") if not data.get(field)]
    if missing:
        print(f"[issue-submission] 缺少必填字段: {', '.join(missing)}")
        return 2
    if args.issue_number:
        data["notes"] = (data.get("notes", "") + f"\nIssue #{args.issue_number}").strip()
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[issue-submission] wrote {output} fields={','.join(sorted(data))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
