#!/usr/bin/env python3
"""export_remote_catalog.py - 把本地目录导出成 NewFreedeck 兼容的远程目录 JSON。

用途：不再依赖作者服务器 panyiwei.xyz，可把导出的静态 JSON 放到任意
GitHub Pages / 静态服务器 / Release 资产上，供 NewFreedeck 或类似前端读取。

输出结构：
  <out>/all.json                      全部条目（list）
  <out>/platform/<platform>.json      按平台拆分（list）
  <out>/curated/<platform>.json       每个平台精选（按封面/体积排序 top N）
  <out>/manifest.json                 统计 + 每个文件的 sha256

用法：
  python3 scripts/export_remote_catalog.py \
      --catalog defaults/tianyi_catalog/freedeckcy_catalog.csv \
      --out dist-artifacts/catalog-server
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

TITLE_SEPARATORS = re.compile(r"\s*[/|｜丨]\s*")
CJK = re.compile(r"[\u3400-\u9fff]")
SCHEMA_VERSION = 1
CURATED_LIMIT = 60


def _safe_int(value: Any) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return 0


def _str(row: Dict[str, str], key: str, default: str = "") -> str:
    return str(row.get(key, "") or default).strip()


def split_titles(raw: str) -> Tuple[str, str]:
    """从 "中文/English" 形式里拆出 title_zh / title_en。"""
    title = " ".join(str(raw or "").replace("\u3000", " ").split())
    if not title:
        return "", ""
    parts = [part.strip() for part in TITLE_SEPARATORS.split(title) if part.strip()]
    if len(parts) >= 2:
        zh_parts = [part for part in parts if CJK.search(part)]
        en_parts = [part for part in parts if not CJK.search(part)]
        # 只有“中文 + 非中文”混排才拆；纯英文里的斜杠（Fate/Unlimited Codes）保留原样
        if zh_parts and en_parts:
            return zh_parts[0], " / ".join(en_parts)
        if zh_parts and not en_parts:
            return " ".join(zh_parts), ""
    if CJK.search(title):
        return title, ""
    return "", title


def to_remote_item(row: Dict[str, str]) -> Dict[str, Any]:
    """本地 CSV 行 → NewFreedeck catalog item。"""
    title = _str(row, "title")
    title_zh, title_en = split_titles(title)
    openpath = _str(row, "openpath").replace("\\", "/")
    file_name = os.path.basename(openpath) if openpath else ""
    size_bytes = _safe_int(row.get("filesize_z", "0"))
    return {
        "game_id": _str(row, "game_id") or title,
        "title": title,
        "title_zh": title_zh,
        "title_en": title_en,
        "platform": _str(row, "platform", "pc").lower() or "pc",
        "cover_url": _str(row, "cover_url"),
        "size_text": _str(row, "list_filesize"),
        "genre": _str(row, "categories"),
        "down_url": _str(row, "down_url"),
        "file_name": file_name,
        "size_bytes": size_bytes,
        "pwd": _str(row, "pwd"),
        "server": _str(row, "server"),
        "version": "",
        "validity": "",
        "install_size_text": "",
        "install_size_bytes": 0,
    }


def load_items(catalog_path: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    with open(catalog_path, "r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if not isinstance(row, dict):
                continue
            item = to_remote_item(row)
            if not item["title"] or not item["down_url"]:
                continue
            items.append(item)
    return items


def _write_json(path: Path, payload: Any, *, pretty: bool = False) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if pretty:
        text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    else:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_outputs(
    items: List[Dict[str, Any]],
    out_dir: str,
    *,
    curated_limit: int = CURATED_LIMIT,
    source_path: str = "",
) -> Dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    by_platform: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        by_platform.setdefault(str(item.get("platform") or "unknown"), []).append(item)

    files: Dict[str, Dict[str, Any]] = {}
    files["all.json"] = {"count": len(items), "sha256": _write_json(out / "all.json", items)}

    for platform, rows in sorted(by_platform.items()):
        rel = f"platform/{platform}.json"
        files[rel] = {"count": len(rows), "sha256": _write_json(out / rel, rows)}

        curated = sorted(
            rows,
            key=lambda item: (
                0 if item.get("cover_url") else 1,
                -int(item.get("size_bytes") or 0),
                str(item.get("title") or ""),
            ),
        )[: max(1, int(curated_limit))]
        rel_curated = f"curated/{platform}.json"
        files[rel_curated] = {
            "count": len(curated),
            "sha256": _write_json(out / rel_curated, curated),
        }

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": int(time.time()),
        "generated_at_text": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": os.path.basename(source_path) if source_path else "",
        "source_sha256": _sha256_file(source_path) if source_path else "",
        "total": len(items),
        "platforms": {platform: len(rows) for platform, rows in sorted(by_platform.items())},
        "curated_limit": int(curated_limit),
        "files": files,
    }
    _write_json(out / "manifest.json", manifest, pretty=True)
    return manifest


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="导出 NewFreedeck 兼容目录 JSON（不依赖作者服务器）")
    parser.add_argument(
        "--catalog",
        default="defaults/tianyi_catalog/freedeckcy_catalog.csv",
        help="本地目录 CSV",
    )
    parser.add_argument("--out", default="catalog-json", help="输出目录（默认仓库内 catalog-json/）")
    parser.add_argument("--curated-limit", type=int, default=CURATED_LIMIT, help="每个平台精选数量")
    args = parser.parse_args()

    if not os.path.isfile(args.catalog):
        print(f"[export] 目录不存在: {args.catalog}", file=sys.stderr)
        return 2

    items = load_items(args.catalog)
    if not items:
        print("[export] 目录为空", file=sys.stderr)
        return 2

    manifest = build_outputs(
        items,
        args.out,
        curated_limit=args.curated_limit,
        source_path=args.catalog,
    )

    total_bytes = sum(
        os.path.getsize(os.path.join(args.out, rel)) for rel in manifest["files"]
    )
    print(f"[export] 条目: {manifest['total']}，平台: {len(manifest['platforms'])}")
    print(f"[export] 输出: {os.path.abspath(args.out)}（{total_bytes / 1048576:.1f} MB JSON）")
    for platform, count in manifest["platforms"].items():
        print(f"  - {platform}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
