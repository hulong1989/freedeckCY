"""仓库游戏提交：字段校验、目录行生成与合并。

对应原版资源池投稿字段：
  name / english_name / platform / share_url / access_code
  / share_user_version / executable_name
额外字段（目录需要）：
  openpath / categories / category_parent / filesize_z / list_filesize / notes

提交文件放在 `submissions/*.json`；Issue 表单见
`.github/ISSUE_TEMPLATE/submit-game.yml`。
"""

from __future__ import annotations

import csv
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from urllib.parse import parse_qs, urlparse

SUBMISSION_DIR = Path("submissions")
CATALOG_PATH = Path("defaults/tianyi_catalog/freedeckcy_catalog.csv")
MERGED_DIRNAME = "merged"
ALLOWED_PLATFORMS = ("pc", "gba", "psp", "nds", "ps1", "fc", "md", "3ds", "ps2", "ps3", "switch")
PLATFORM_TOKENS = frozenset({*ALLOWED_PLATFORMS, "ns", "psx", "arcade"})
_CATEGORY_SPLIT_RE = re.compile(r"[,，/、;；|]+")
PLATFORM_ALIASES = {
    "windows": "pc",
    "win": "pc",
    "ns": "switch",
    "switch2": "switch",
    "3d": "3ds",
    "psx": "ps1",
    "playstation": "ps1",
    "playstation2": "ps2",
    "playstation3": "ps3",
    "mega-drive": "md",
    "genesis": "md",
}
CATALOG_FIELDS = (
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
)
_SLUG_RE = re.compile(r"[^a-z0-9\u4e00-\u9fff]+")


def normalize_platform(value: Any) -> str:
    raw = str(value or "").strip().lower().replace("_", "-")
    raw = PLATFORM_ALIASES.get(raw, raw)
    return raw if raw in ALLOWED_PLATFORMS else ""


def normalize_categories(raw: Any, platform: str = "pc") -> str:
    """与目录清洗规则一致：去掉平台名、去重；模拟器空分类补“模拟器”。"""
    tokens: List[str] = []
    seen = set()
    normalized_platform = normalize_platform(platform) or str(platform or "").strip().lower()
    for part in _CATEGORY_SPLIT_RE.split(str(raw or "")):
        name = part.strip()
        if not name:
            continue
        key = name.lower()
        if key in PLATFORM_TOKENS or key == normalized_platform:
            continue
        if key in seen:
            continue
        seen.add(key)
        tokens.append(name)
    if not tokens and normalized_platform and normalized_platform != "pc":
        return "模拟器"
    return ",".join(tokens)


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_share_url(value: str) -> str:
    raw = _normalize_text(value)
    if raw and not re.match(r"^[a-z][a-z0-9+.-]*://", raw, flags=re.I):
        raw = "https://" + raw.lstrip("/")
    return raw


class ShareUrlError(ValueError):
    pass


def _share_provider(share_url: str) -> str:
    try:
        host = str(urlparse(str(share_url or "").strip()).hostname or "").lower()
    except Exception:
        return ""
    if host in {"cloud.189.cn", "www.cloud.189.cn"} or host.endswith(".189.cn"):
        return "tianyi"
    if host in {"pan.baidu.com", "yun.baidu.com", "eyun.baidu.com"}:
        return "baidu"
    return ""


def _parse_share_url(share_url: str) -> Tuple[str, str]:
    raw = str(share_url or "").strip()
    parsed = urlparse(raw)
    host = (parsed.netloc or "").lower()
    parts = [part for part in (parsed.path or "").split("/") if part]
    query = parse_qs(parsed.query or "", keep_blank_values=True)
    pwd = str((query.get("pwd") or [""])[0] or "").strip()
    if host in {"cloud.189.cn", "www.cloud.189.cn"}:
        if parts[:2] == ["web", "share"]:
            code = str((query.get("code") or [""])[0] or "").strip()
            if not code:
                raise ShareUrlError("链接缺少 shareCode")
            return code, pwd
        if len(parts) < 2 or parts[0] != "t":
            raise ShareUrlError("链接缺少 shareCode")
        return parts[1], pwd
    if host in {"pan.baidu.com", "yun.baidu.com", "eyun.baidu.com"}:
        if "s" in parts:
            index = parts.index("s")
            if index + 1 < len(parts) and parts[index + 1]:
                return parts[index + 1], pwd
        surl = str((query.get("surl") or [""])[0] or "").strip()
        if surl:
            return surl, pwd
        raise ShareUrlError("百度链接缺少 shareCode/surl")
    raise ShareUrlError("仅支持 cloud.189.cn 或 pan.baidu.com 分享链接")


def _share_code(share_url: str) -> str:
    try:
        code, _pwd = _parse_share_url(share_url)
        return code
    except ShareUrlError:
        return ""


def _canonical_share_code(share_url: str) -> str:
    """用于去重的分享码：百度 /s/1xxxx 与 ?surl=xxxx 归一。"""
    code = _share_code(share_url)
    if code and _share_provider(share_url) == "baidu" and code.startswith("1"):
        return code[1:]
    return code


def _with_access_code(share_url: str, access_code: str) -> str:
    if not access_code or "pwd=" in share_url:
        return share_url
    joiner = "&" if "?" in share_url else "?"
    return f"{share_url}{joiner}pwd={access_code}"


def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for key, value in row.items():
        if key in {"filesize_z", "category_parent"}:
            normalized[key] = _normalize_text(value)
        else:
            normalized[key] = _normalize_text(value)
    return normalized


def validate_submission(
    data: Any,
    *,
    catalog_share_codes: Optional[set] = None,
    other_share_codes: Optional[set] = None,
    filename: str = "",
) -> Tuple[Dict[str, Any], List[str], List[str]]:
    """返回 (normalized, errors, warnings)。"""
    errors: List[str] = []
    warnings: List[str] = []
    if not isinstance(data, dict):
        return {}, ["提交内容必须是 JSON 对象"], warnings

    normalized = _normalize_row(data)
    name = normalized.get("name", "")
    platform = normalize_platform(normalized.get("platform", ""))
    share_url = _normalize_share_url(normalized.get("share_url", ""))
    access_code = normalized.get("access_code", "")
    raw_openpath = normalized.get("openpath", "")
    openpath = raw_openpath.replace("\\", "/").lstrip("/")

    if not name:
        errors.append("缺少 name（游戏名称）")
    if len(name) > 200:
        errors.append("name 过长（最多 200 字符）")
    if not platform:
        errors.append(f"platform 无效，可选：{', '.join(ALLOWED_PLATFORMS)}")
    if not share_url:
        errors.append("缺少 share_url（天翼云盘或百度网盘分享链接）")
    else:
        try:
            _parse_share_url(share_url)
        except ShareUrlError as exc:
            errors.append(f"share_url 无效：{exc}")
        else:
            if access_code and not re.fullmatch(r"[A-Za-z0-9]{4,8}", access_code):
                errors.append("access_code 应为 4–8 位字母/数字")
            if not access_code and "pwd=" not in share_url:
                warnings.append("未填写 access_code，且链接里没有 pwd，下载时可能需要提取码")
    if not openpath:
        errors.append("缺少 openpath（网盘内游戏文件/目录的相对路径）")
    elif raw_openpath.replace("\\", "/").startswith("/") or ".." in openpath.split("/"):
        errors.append("openpath 必须是分享内相对路径，不能以 / 开头或包含 ..")
    for field, label in (("name", "name"), ("english_name", "english_name"), ("categories", "categories"), ("notes", "notes")):
        value = str(normalized.get(field, "") or "").lstrip()
        if value.startswith(("=", "+", "@", "\t", "\r")):
            errors.append(f"{label} 不能以 = + @ 或制表符开头（CSV 公式注入）")
    if normalized.get("executable_name") and platform != "pc":
        warnings.append("executable_name 仅 PC 游戏需要，模拟器游戏可留空")
    filesize = normalized.get("filesize_z", "")
    if filesize and not filesize.isdigit():
        errors.append("filesize_z 必须是非负整数（字节）")

    share_code = _canonical_share_code(share_url) if share_url else ""
    if share_code and catalog_share_codes and share_code in catalog_share_codes:
        errors.append(f"该分享链接已存在目录中（shareCode={share_code}）")
    if share_code and other_share_codes and share_code in other_share_codes:
        errors.append(f"该分享链接与其他提交重复（shareCode={share_code}）")
    if filename and not filename.endswith(".json"):
        warnings.append("建议提交文件使用 .json 后缀")

    normalized.update(
        {
            "name": name,
            "platform": platform,
            "share_url": share_url,
            "access_code": access_code,
            "openpath": openpath,
            "english_name": normalized.get("english_name", ""),
            "share_user_version": normalized.get("share_user_version", ""),
            "executable_name": normalized.get("executable_name", ""),
            "categories": normalize_categories(normalized.get("categories", ""), platform) if platform else normalized.get("categories", ""),
            "notes": normalized.get("notes", ""),
        }
    )
    return normalized, errors, warnings


def load_catalog(path: Path = CATALOG_PATH) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def catalog_share_codes(rows: Iterable[Dict[str, str]]) -> set:
    codes = set()
    for row in rows:
        code = _canonical_share_code(str(row.get("down_url", "") or ""))
        if not code:
            code = str(row.get("shorturl", "") or "").strip()
            if code.startswith("1") and _share_provider(str(row.get("down_url", "") or "")) == "baidu":
                code = code[1:]
        if code:
            codes.add(code)
    return codes


def iter_submission_files(directory: Path = SUBMISSION_DIR) -> List[Path]:
    if not directory.is_dir():
        return []
    ignored = {"schema.json"}
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file()
        and path.suffix.lower() == ".json"
        and path.name not in ignored
        and not path.name.startswith(("_", "."))
    )


def validate_submission_files(
    directory: Path = SUBMISSION_DIR,
    catalog_path: Path = CATALOG_PATH,
) -> Dict[str, Any]:
    rows = load_catalog(catalog_path) if catalog_path.is_file() else []
    existing = catalog_share_codes(rows)
    seen: set = set()
    results: List[Dict[str, Any]] = []
    for path in iter_submission_files(directory):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            results.append({"file": path.name, "errors": [f"JSON 解析失败：{exc}"], "warnings": []})
            continue
        normalized, errors, warnings = validate_submission(
            data,
            catalog_share_codes=existing,
            other_share_codes=seen,
            filename=path.name,
        )
        code = _canonical_share_code(normalized.get("share_url", "")) if normalized else ""
        if code:
            seen.add(code)
        results.append(
            {
                "file": path.name,
                "errors": errors,
                "warnings": warnings,
                "normalized": normalized,
            }
        )
    error_count = sum(len(item["errors"]) for item in results)
    return {
        "ok": error_count == 0,
        "files": results,
        "error_count": error_count,
        "warning_count": sum(len(item["warnings"]) for item in results),
    }


def _next_game_id(rows: Sequence[Dict[str, str]]) -> str:
    maximum = 0
    for row in rows:
        try:
            maximum = max(maximum, int(str(row.get("game_id", "") or "0")))
        except Exception:
            continue
    return str(maximum + 1)


def _csv_safe(value: str) -> str:
    text = str(value or "")
    if text.lstrip().startswith(("=", "+", "@", "\t", "\r")):
        return "'" + text
    return text


def build_catalog_row(data: Dict[str, Any], game_id: str) -> Dict[str, str]:
    name = _normalize_text(data.get("name"))
    english = _normalize_text(data.get("english_name"))
    title = f"{name}/{english}" if english and english.lower() not in name.lower() else name
    platform = normalize_platform(data.get("platform"))
    access_code = _normalize_text(data.get("access_code"))
    share_url = _with_access_code(_normalize_share_url(data.get("share_url")), access_code)
    share_code = _share_code(share_url)
    try:
        _code, parsed_pwd = _parse_share_url(share_url)
    except ShareUrlError:
        parsed_pwd = ""
    pwd = access_code or parsed_pwd
    row = {field: "" for field in CATALOG_FIELDS}
    row.update(
        {
            "game_id": str(game_id),
            "title": _csv_safe(title),
            "category_parent": _normalize_text(data.get("category_parent")) or "5",
            "categories": _csv_safe(normalize_categories(data.get("categories", ""), platform) or "未分类"),
            "package_name": "",
            "server": "b" if _share_provider(share_url) == "baidu" else "t",
            "down_url": share_url,
            "shorturl": share_code,
            "pwd": pwd,
            "openpath": _normalize_text(data.get("openpath")).replace("\\", "/").lstrip("/"),
            "filesize_z": _normalize_text(data.get("filesize_z")) or "0",
            "list_filesize": _normalize_text(data.get("list_filesize")),
            "platform": platform,
            "cover_url": "",
            "cover_portrait_url": "",
            "steam_appid": "0",
        }
    )
    return row


def merge_submissions(
    directory: Path = SUBMISSION_DIR,
    catalog_path: Path = CATALOG_PATH,
    *,
    apply: bool = False,
) -> Dict[str, Any]:
    validation = validate_submission_files(directory, catalog_path)
    if not validation["ok"]:
        return {"ok": False, "message": "存在校验错误，未合并", "validation": validation}
    rows = load_catalog(catalog_path)
    next_id = _next_game_id(rows)
    merged: List[Dict[str, Any]] = []
    for item in validation["files"]:
        data = item.get("normalized") or {}
        row = build_catalog_row(data, next_id)
        merged.append({"file": item["file"], "row": row})
        next_id = str(int(next_id) + 1)

    if not apply:
        return {"ok": True, "applied": False, "rows": merged, "validation": validation}

    if not merged:
        return {"ok": True, "applied": True, "rows": [], "validation": validation}

    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    temp_fd, temp_name = tempfile.mkstemp(prefix="freedeckcy_catalog_", suffix=".csv", dir=str(catalog_path.parent))
    os.close(temp_fd)
    try:
        with open(catalog_path, "r", encoding="utf-8-sig", newline="") as src, open(
            temp_name, "w", encoding="utf-8-sig", newline=""
        ) as dst:
            reader = csv.DictReader(src)
            fieldnames = reader.fieldnames or list(CATALOG_FIELDS)
            writer = csv.DictWriter(dst, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            for row in reader:
                writer.writerow(row)
            for item in merged:
                writer.writerow(item["row"])
        os.replace(temp_name, catalog_path)
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)

    merged_dir = directory / MERGED_DIRNAME
    merged_dir.mkdir(parents=True, exist_ok=True)
    for item in merged:
        source = directory / item["file"]
        target = merged_dir / item["file"]
        if source.is_file():
            os.replace(source, target)
    index_path = merged_dir / "index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.is_file() else []
    except Exception:
        index = []
    for item in merged:
        index.append(
            {
                "file": item["file"],
                "game_id": item["row"].get("game_id", ""),
                "title": item["row"].get("title", ""),
                "merged_at": int(time.time()),
            }
        )
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "applied": True, "rows": merged, "validation": validation}
