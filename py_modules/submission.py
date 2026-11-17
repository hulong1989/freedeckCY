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
# CSV 公式注入前缀（Excel/LibreOffice 会把以这些字符开头的单元格当公式执行）。
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
# 目录 CSV 只接受单行纯文本：控制字符（含换行/NUL）会破坏行语义或下游路径拼接。
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")
# 分享码只允许字母/数字（天翼/百度实际都是 base62，允许 _- 以兼容个别变体）。
_SHARE_CODE_RE = re.compile(r"[A-Za-z0-9_-]{1,128}")
# Windows 盘符/UNC 绝对路径不属于网盘分享内的相对路径。
_ABSOLUTE_PATH_RE = re.compile(r"^(?:[A-Za-z]:/|//)")
TIANYI_HOSTS = ("cloud.189.cn", "www.cloud.189.cn", "189.cn", "h5.cloud.189.cn")
BAIDU_HOSTS = ("pan.baidu.com", "www.pan.baidu.com", "yun.baidu.com", "eyun.baidu.com")
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


def _url_host(parsed) -> str:
    """取小写主机名（自动去掉端口与 userinfo）。"""
    try:
        host = str(parsed.hostname or "").strip().lower()
    except Exception:
        return ""
    return host.rstrip(".")


def _is_tianyi_host(host: str) -> bool:
    value = str(host or "").strip().lower().rstrip(".")
    return value in TIANYI_HOSTS or value.endswith(".189.cn")


def _is_baidu_host(host: str) -> bool:
    return str(host or "").strip().lower().rstrip(".") in BAIDU_HOSTS


def _share_provider(share_url: str) -> str:
    try:
        host = _url_host(urlparse(str(share_url or "").strip()))
    except Exception:
        return ""
    if _is_tianyi_host(host):
        return "tianyi"
    if _is_baidu_host(host):
        return "baidu"
    return ""


def _validate_share_code(code: str) -> str:
    value = str(code or "").strip()
    if not value or not _SHARE_CODE_RE.fullmatch(value):
        raise ShareUrlError("shareCode 含非法字符（只允许字母/数字/_/-）")
    return value


def _parse_share_url(share_url: str) -> Tuple[str, str]:
    raw = str(share_url or "").strip()
    parsed = urlparse(raw)
    host = _url_host(parsed)
    parts = [part for part in (parsed.path or "").split("/") if part]
    query = parse_qs(parsed.query or "", keep_blank_values=True)
    pwd = str((query.get("pwd") or [""])[0] or "").strip()
    if _is_tianyi_host(host):
        if parts[:2] == ["web", "share"]:
            code = str((query.get("code") or [""])[0] or "").strip()
            if not code:
                raise ShareUrlError("链接缺少 shareCode")
            return _validate_share_code(code), pwd
        if len(parts) < 2 or parts[0] != "t":
            raise ShareUrlError("链接缺少 shareCode")
        return _validate_share_code(parts[1]), pwd
    if _is_baidu_host(host):
        if "s" in parts:
            index = parts.index("s")
            if index + 1 < len(parts) and parts[index + 1]:
                return _validate_share_code(parts[index + 1]), pwd
        surl = str((query.get("surl") or [""])[0] or "").strip()
        if surl:
            return _validate_share_code(surl), pwd
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
    """把提取码写入分享链接；已有 pwd 参数时以 access_code 为准覆盖。"""
    code = _normalize_text(access_code)
    if not code:
        return share_url
    if re.search(r"(?i)([?&])pwd=[^&#]*", share_url):
        return re.sub(
            r"(?i)([?&])pwd=[^&#]*",
            lambda match: f"{match.group(1)}pwd={code}",
            share_url,
            count=1,
        )
    joiner = "&" if "?" in share_url else "?"
    return f"{share_url}{joiner}pwd={code}"


def _has_formula_prefix(value: Any) -> bool:
    return str(value or "").lstrip().startswith(_FORMULA_PREFIXES)


def _has_control_chars(value: Any) -> bool:
    return bool(_CONTROL_CHARS_RE.search(str(value or "")))


def _normalize_openpath(value: Any) -> str:
    return _normalize_text(value).replace("\\", "/")


def _validate_openpath(raw_openpath: str, errors: List[str]) -> str:
    """把网盘内相对路径归一化并校验；返回写入目录的 openpath。"""
    normalized = _normalize_openpath(raw_openpath)
    openpath = normalized.lstrip("/")
    if not openpath:
        errors.append("缺少 openpath（网盘内游戏文件/目录的相对路径）")
        return ""
    if _has_control_chars(normalized):
        errors.append("openpath 含控制字符（换行/制表符等），请填写单行相对路径")
        return openpath
    if normalized.startswith("/") or _ABSOLUTE_PATH_RE.match(normalized):
        errors.append("openpath 必须是分享内相对路径，不能是绝对路径（/ 或盘符开头）")
    if ".." in openpath.split("/"):
        errors.append("openpath 不能包含 ..")
    if _has_formula_prefix(openpath):
        errors.append("openpath 不能以 = + - @ 或制表符开头（CSV 公式注入）")
    return openpath


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

    if not name:
        errors.append("缺少 name（游戏名称）")
    if len(name) > 200:
        errors.append("name 过长（最多 200 字符）")
    if _has_control_chars(name) or _has_control_chars(normalized.get("english_name", "")):
        errors.append("name/english_name 不能包含换行或控制字符")
    if not platform:
        errors.append(f"platform 无效，可选：{', '.join(ALLOWED_PLATFORMS)}")
    if not share_url:
        errors.append("缺少 share_url（天翼云盘或百度网盘分享链接）")
    elif _has_control_chars(share_url) or re.search(r"\s", share_url):
        errors.append("share_url 不能包含空白或控制字符（换行/空格等）")
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
    openpath = _validate_openpath(raw_openpath, errors)
    for field, label in (
        ("name", "name"),
        ("english_name", "english_name"),
        ("categories", "categories"),
        ("notes", "notes"),
    ):
        value = str(normalized.get(field, "") or "").lstrip()
        if value.startswith(_FORMULA_PREFIXES):
            errors.append(f"{label} 不能以 = + - @ 或制表符开头（CSV 公式注入）")
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
        if code and _SHARE_CODE_RE.fullmatch(code):
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
    if text.lstrip().startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def _clean_multiline_text(value: Any) -> str:
    """把字段压成单行，避免换行破坏 CSV 行/日志。"""
    return _CONTROL_CHARS_RE.sub(" ", str(value or "")).strip()


def build_catalog_row(data: Dict[str, Any], game_id: str) -> Dict[str, str]:
    name = _clean_multiline_text(data.get("name"))
    english = _clean_multiline_text(data.get("english_name"))
    title = f"{name}/{english}" if english and english.lower() not in name.lower() else name
    platform = normalize_platform(data.get("platform"))
    access_code = _clean_multiline_text(data.get("access_code"))
    share_url = _with_access_code(_normalize_share_url(data.get("share_url")), access_code)
    share_code = _share_code(share_url)
    try:
        _code, parsed_pwd = _parse_share_url(share_url)
    except ShareUrlError:
        parsed_pwd = ""
    pwd = access_code or parsed_pwd
    openpath = _normalize_openpath(data.get("openpath")).lstrip("/")
    row = {field: "" for field in CATALOG_FIELDS}
    row.update(
        {
            "game_id": str(game_id),
            "title": title,
            "category_parent": _normalize_text(data.get("category_parent")) or "5",
            "categories": normalize_categories(data.get("categories", ""), platform) or "未分类",
            "package_name": "",
            "server": "b" if _share_provider(share_url) == "baidu" else "t",
            "down_url": share_url,
            "shorturl": share_code,
            "pwd": _clean_multiline_text(pwd),
            "openpath": _clean_multiline_text(openpath),
            "filesize_z": _normalize_text(data.get("filesize_z")) or "0",
            "list_filesize": _normalize_text(data.get("list_filesize")),
            "platform": platform,
            "cover_url": "",
            "cover_portrait_url": "",
            "steam_appid": "0",
        }
    )
    # 统一兜底：所有写入目录 CSV 的文本列都做公式注入转义。
    return {key: (_csv_safe(value) if isinstance(value, str) else value) for key, value in row.items()}


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
