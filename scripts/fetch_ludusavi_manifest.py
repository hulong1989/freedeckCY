#!/usr/bin/env python3
"""fetch_ludusavi_manifest.py - 下载并转换 Ludusavi 存档清单。

输出：
  defaults/ludusavi/manifest.json.gz  精简 JSON 的 gzip（运行时读取；压缩后约 2MB）
  defaults/ludusavi/LICENSE         Ludusavi Manifest 的 MIT 许可证
  defaults/ludusavi/README.md       来源/版本/哈希/字段说明

用法：
  python3 scripts/fetch_ludusavi_manifest.py [--out defaults/ludusavi] [--force]

运行时不会联网；清单随插件包分发（MIT，见 LICENSE）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

DEFAULT_URL = "https://raw.githubusercontent.com/mtkennerly/ludusavi-manifest/data/data/manifest.yaml"
LICENSE_URL = "https://raw.githubusercontent.com/mtkennerly/ludusavi-manifest/master/LICENSE"
PROJECT_URL = "https://github.com/mtkennerly/ludusavi-manifest"


def _download(url: str, timeout: int = 180) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "freedeckCY/ludusavi-fetch"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description="下载并转换 Ludusavi 清单")
    parser.add_argument("--out", default="defaults/ludusavi")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--input", default="", help="本地 YAML 路径（给出则不联网下载）")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        import yaml
    except Exception:
        print("[ludusavi] 缺少 PyYAML：pip install pyyaml（仅构建时需要）", file=sys.stderr)
        return 2

    out = Path(args.out)
    manifest_path = out / "manifest.json.gz"
    if manifest_path.is_file() and not args.force:
        print(f"[ludusavi] 已存在，跳过（--force 重新生成）: {manifest_path}")
        return 0

    if args.input:
        print(f"[ludusavi] 读取本地清单: {args.input}")
        raw = Path(args.input).read_bytes()
    else:
        print(f"[ludusavi] 下载清单: {args.url}")
        raw = _download(args.url)
    try:
        data = yaml.safe_load(raw)
    except Exception as exc:
        print(f"[ludusavi] YAML 解析失败: {exc}", file=sys.stderr)
        return 1

    if not isinstance(data, dict) or len(data) < 1000:
        print(f"[ludusavi] 清单格式异常（entries={len(data) if isinstance(data, dict) else 'n/a'}）", file=sys.stderr)
        return 1

    out.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    import gzip

    with open(manifest_path, "wb") as raw_file:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_file, mtime=0) as gz:
            gz.write(text.encode("utf-8"))
    stale_plain = out / "manifest.json"
    if stale_plain.is_file():
        stale_plain.unlink()

    try:
        license_text = _download(LICENSE_URL, timeout=60).decode("utf-8", "replace")
    except Exception as exc:
        license_text = f"Ludusavi Manifest is MIT licensed ({PROJECT_URL}); LICENSE 下载失败: {exc}\n"
    (out / "LICENSE").write_text(license_text, encoding="utf-8")

    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    (out / "README.md").write_text(
        "# Ludusavi manifest\n\n"
        f"- 来源: {args.url}\n"
        f"- 项目: {PROJECT_URL}（MIT）\n"
        f"- 游戏条目: {len(data)}\n"
        f"- 未压缩 JSON 字节: {len(text.encode('utf-8'))}\n"
        f"- gzip 字节: {os.path.getsize(manifest_path)}\n"
        f"- 未压缩 JSON sha256: {sha}\n\n"
        "该文件由 `scripts/fetch_ludusavi_manifest.py` 从上游 YAML 转换而来，"
        "仅用于本地存档路径匹配；重新生成：`make ludusavi-manifest`。\n",
        encoding="utf-8",
    )
    print(f"[ludusavi] 完成: {manifest_path}（{len(data)} 条，{os.path.getsize(manifest_path)/1048576:.1f}MB）")
    print(f"[ludusavi] sha256: {sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
