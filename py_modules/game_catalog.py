# game_catalog.py - 游戏目录加载与检索
#
# 该模块负责读取 CSV 并提供搜索/筛选能力，支持可选的封面索引（cover_index.csv）。

from __future__ import annotations

import csv
import json
import os
import re
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

import decky

import config

DEFAULT_PLATFORM = "pc"
CATEGORY_FILTER_LIMIT = 12
REMOTE_CATALOG_TTL_SECONDS = 6 * 3600
CATEGORY_EMULATOR_LABEL = "模拟器"
PLATFORM_TOKENS = frozenset(
    {"pc", "fc", "nds", "psp", "gba", "3ds", "ps1", "ps2", "ps3", "md", "switch", "ns", "arcade", "psx"}
)
_CATEGORY_SPLIT_RE = re.compile(r"[,，/、;；|]+")

# 封面索引列名兼容多种写法
_COVER_URL_FIELDS = ("cover_url", "landscape_cover_url", "cover")
_PORTRAIT_FIELDS = ("cover_portrait_url", "square_cover_url", "portrait_url", "portrait")
_APPID_FIELDS = ("steam_appid", "app_id", "appid")


@dataclass
class GameCatalogEntry:
    """单条游戏目录记录。"""

    game_id: str
    title: str
    category_parent: str
    categories: str
    down_url: str
    pwd: str
    openpath: str
    size_bytes: int
    size_text: str
    # 平台：pc / switch / ps1 / ps2 / ps3 / psp / 3ds / gba / md / nds / fc / arcade ...
    platform: str = DEFAULT_PLATFORM
    cover_url: str = ""
    cover_portrait_url: str = ""
    steam_appid: int = 0

    def to_dict(self) -> Dict[str, object]:
        """转为前端可用字典。"""
        return asdict(self)


def _safe_int(value: object) -> int:
    """安全解析整数字段。"""
    try:
        return int(str(value).strip())
    except Exception:
        return 0


def _normalize_title(raw: str) -> str:
    """标准化标题，去除多余空白。"""
    return " ".join((raw or "").replace("\u3000", " ").strip().split())


def _normalize_platform(value: object, default: str = DEFAULT_PLATFORM) -> str:
    """归一化平台标识。"""
    text = str(value or "").strip().lower()
    if not text:
        return default
    # 常见别名归一
    aliases = {
        "steam": "pc",
        "windows": "pc",
        "win": "pc",
        "switch": "switch",
        "ns": "switch",
    }
    return aliases.get(text, text)


def normalize_categories(raw: object, platform: str = DEFAULT_PLATFORM) -> str:
    """清洗分类字段：去掉平台名、去重、统一分隔符。

    0.6 的目录里 FC/GBA 等模拟器资源的 categories 会错误地写成平台名（如 "GBA"），
    这里统一剔除；模拟器行清洗后为空时补一个 "模拟器" 分类，方便筛选。
    """
    normalized_platform = _normalize_platform(platform)
    tokens: List[str] = []
    seen = set()
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
    if not tokens and normalized_platform != DEFAULT_PLATFORM:
        return CATEGORY_EMULATOR_LABEL
    return ",".join(tokens)


def _first_value(row: Dict[str, object], fields: tuple, default: str = "") -> str:
    """按列名候选取第一个非空值。"""
    for name in fields:
        value = str(row.get(name, "") or "").strip()
        if value:
            return value
    return default


def _is_valid_baidu_url(url: str) -> bool:
    try:
        parsed = urlparse(str(url or "").strip())
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = str(parsed.hostname or "").strip().lower()
    return host in {"pan.baidu.com", "yun.baidu.com", "eyun.baidu.com"} or host.endswith(".pan.baidu.com")


def _is_valid_share_url(url: str) -> bool:
    return _is_valid_tianyi_url(url) or _is_valid_baidu_url(url)


def _is_valid_tianyi_url(url: str) -> bool:
    """判断是否是支持的天翼分享链接（/t/ 或 /web/share?code=）。"""
    value = (url or "").strip().lower()
    if not (value.startswith("https://cloud.189.cn/") or value.startswith("http://cloud.189.cn/")):
        return False
    if "/t/" in value:
        return True
    return "/web/share" in value and "code=" in value


def _pick_existing(candidates: List[Path]) -> str:
    for path in candidates:
        try:
            resolved = path.expanduser().resolve()
        except Exception:
            continue
        if resolved.is_file():
            return str(resolved)
    return ""


def resolve_default_catalog_path() -> str:
    """解析默认目录文件路径。"""
    candidates: List[Path] = []

    for env_name in ("FREEDECKCY_GAME_CATALOG_CSV", "FRIENDECK_GAME_CATALOG_CSV"):
        env_path = (os.getenv(env_name) or "").strip()
        if env_path:
            candidates.append(Path(env_path))

    plugin_dir = getattr(decky, "DECKY_PLUGIN_DIR", None)
    if plugin_dir:
        root = Path(plugin_dir)
        candidates.append(root / "defaults" / "tianyi_catalog" / "freedeckcy_catalog.csv")
        candidates.append(root / "defaults" / "tianyi_catalog" / "gamebox_all_links_20260221_234730.csv")
        candidates.append(root / "defaults" / "tianyi_catalog.csv")

    cwd = Path.cwd()
    candidates.append(cwd / "defaults" / "tianyi_catalog" / "freedeckcy_catalog.csv")
    candidates.append(cwd / "exports" / "gamebox_all_links_20260221_234730.csv")
    candidates.append(cwd / "gamebox_all_links_20260221_234730.csv")

    return _pick_existing(candidates)


def resolve_default_catalog_json_path() -> str:
    """解析可选的 NewFreedeck 兼容 JSON 目录。

    仅通过 `FREEDECKCY_CATALOG_JSON` 显式开启；默认仍读 CSV，避免发布包行为漂移。
    """
    for env_name in ("FREEDECKCY_CATALOG_JSON", "FRIENDECK_CATALOG_JSON"):
        env_path = (os.getenv(env_name) or "").strip()
        if not env_path:
            continue
        if env_path.lower().startswith(("http://", "https://")):
            return env_path
        try:
            resolved = Path(env_path).expanduser().resolve()
        except Exception:
            continue
        if resolved.is_file():
            return str(resolved)
        config.logger.warning("FREEDECKCY_CATALOG_JSON 指向的文件不存在: %s", env_path)
    return ""


def resolve_default_cover_index_path() -> str:
    """解析封面索引文件路径（可选；不存在时返回空串）。"""
    candidates: List[Path] = []

    for env_name in ("FREEDECKCY_COVER_INDEX_CSV", "FRIENDECK_COVER_INDEX_CSV"):
        env_path = (os.getenv(env_name) or "").strip()
        if env_path:
            candidates.append(Path(env_path))

    plugin_dir = getattr(decky, "DECKY_PLUGIN_DIR", None)
    if plugin_dir:
        root = Path(plugin_dir)
        candidates.append(root / "defaults" / "tianyi_catalog" / "cover_index.csv")
        candidates.append(root / "defaults" / "tianyi_catalog" / "cover_index.json")

    cwd = Path.cwd()
    candidates.append(cwd / "defaults" / "tianyi_catalog" / "cover_index.csv")

    return _pick_existing(candidates)


def _entry_from_json_item(item: object) -> Optional[GameCatalogEntry]:
    """NewFreedeck 兼容 JSON item → GameCatalogEntry。"""
    if not isinstance(item, dict):
        return None
    game_id = str(item.get("game_id") or item.get("id") or "").strip()
    title = _normalize_title(
        str(item.get("title") or item.get("title_zh") or item.get("title_en") or "")
    )
    down_url = str(item.get("down_url") or "").strip()
    if not title or not _is_valid_share_url(down_url):
        return None
    platform = _normalize_platform(item.get("platform"))
    size_bytes = _safe_int(item.get("size_bytes") or item.get("filesize_z") or 0)
    size_text = str(item.get("size_text") or item.get("list_filesize") or "").strip()
    if not size_text and size_bytes > 0:
        size_text = _format_size(size_bytes)
    return GameCatalogEntry(
        game_id=game_id or title,
        title=title,
        category_parent=str(item.get("category_parent") or "").strip(),
        categories=normalize_categories(item.get("genre") or item.get("categories"), platform),
        down_url=down_url,
        pwd=str(item.get("pwd") or "").strip(),
        openpath=str(item.get("openpath") or item.get("file_name") or "").strip(),
        size_bytes=size_bytes,
        size_text=size_text,
        platform=platform,
        cover_url=str(item.get("cover_url") or "").strip(),
        cover_portrait_url=str(
            item.get("cover_portrait_url") or item.get("square_cover_url") or ""
        ).strip(),
        steam_appid=_safe_int(item.get("steam_appid") or item.get("app_id") or 0),
    )


def _is_http_url(value: str) -> bool:
    text = str(value or "").strip().lower()
    return text.startswith("https://") or text.startswith("http://")


def _download_json(url: str, *, timeout: float = 10.0, max_bytes: int = 64 * 1024 * 1024) -> object:
    """下载 JSON（仅用于显式配置的目录 URL）。"""
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "freedeckCY/0.6 catalog-loader",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - 用户显式配置
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError(f"目录 JSON 超过 {max_bytes // 1024 // 1024}MB 限制")
    return json.loads(data.decode("utf-8"))


class GameCatalog:
    """游戏目录仓库。"""

    def __init__(
        self,
        csv_path: str,
        cover_index_path: str = "",
        json_path: str = "",
        json_cache_path: str = "",
    ):
        self.csv_path = csv_path
        self.cover_index_path = cover_index_path
        self.json_path = json_path
        self.json_cache_path = json_cache_path or os.path.join(
            config.DECKY_SEND_DIR, "catalog-remote-cache.json"
        )
        self.source = "csv"
        self._json_loaded_from = ""
        self.entries: List[GameCatalogEntry] = []
        self._by_id: Dict[str, GameCatalogEntry] = {}
        self.invalid_rows = 0
        self.cover_index_total = 0

    def load(self) -> None:
        """加载目录：优先显式指定的 JSON，否则 CSV；两者都兼容封面索引。"""
        self.entries = []
        self.invalid_rows = 0
        self.cover_index_total = 0
        self.source = "csv"

        json_path = str(self.json_path or "").strip()
        if json_path:
            remote = _is_http_url(json_path)
            if remote or os.path.isfile(json_path):
                self._load_json(json_path)
                if self.entries:
                    if remote:
                        self.source = "json-url-cache" if self._json_loaded_from == "cache" else "json-url"
                    else:
                        self.source = "json"
                else:
                    config.logger.warning("JSON 目录没有有效条目，回退 CSV: %s", json_path)
            else:
                config.logger.warning("JSON 目录不存在，回退 CSV: %s", json_path)

        if not self.entries:
            self._load_csv()

        self._merge_cover_index()
        self._by_id = {entry.game_id: entry for entry in self.entries}

        config.logger.info(
            "已加载游戏目录: source=%s total=%s invalid=%s cover_index=%s file=%s",
            self.source,
            len(self.entries),
            self.invalid_rows,
            self.cover_index_total,
            json_path if self.source == "json" else self.csv_path,
        )

    def _load_json(self, path: str) -> None:
        """加载 NewFreedeck 兼容 JSON（本地文件或 https URL，支持 variants）。"""
        payload = None
        if _is_http_url(path):
            entry = self._read_remote_cache_entry(path)
            cached = entry.get("payload") if isinstance(entry, dict) else None
            fetched_at = int(entry.get("fetched_at", 0)) if isinstance(entry, dict) else 0
            fresh = bool(cached is not None and time.time() - fetched_at < REMOTE_CATALOG_TTL_SECONDS)
            if fresh:
                payload = cached
                self._json_loaded_from = "cache"
            else:
                try:
                    payload = _download_json(path)
                    self._json_loaded_from = "network"
                    self._write_remote_cache(path, payload)
                except Exception as exc:
                    config.logger.warning("下载 JSON 目录失败 %s: %s", path, exc)
                    if cached is not None:
                        payload = cached
                        self._json_loaded_from = "cache"
                        config.logger.warning("已使用上次缓存的 JSON 目录: %s", self.json_cache_path)
        else:
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    payload = json.load(fh)
            except Exception as exc:
                config.logger.warning("读取 JSON 目录失败 %s: %s", path, exc)
                self.invalid_rows += 1
                return

        if payload is None:
            self.invalid_rows += 1
            return

        if isinstance(payload, dict):
            raw_items = payload.get("games") or payload.get("items") or payload.get("data") or []
        elif isinstance(payload, list):
            raw_items = payload
        else:
            raw_items = []

        if not isinstance(raw_items, list):
            config.logger.warning("JSON 目录格式不支持（顶层不是数组）: %s", path)
            self.invalid_rows += 1
            return

        seen = set()

        def add_item(item: object) -> None:
            entry = _entry_from_json_item(item)
            if entry is None:
                self.invalid_rows += 1
                return
            if entry.game_id in seen:
                return
            seen.add(entry.game_id)
            self.entries.append(entry)

        for item in raw_items:
            if not isinstance(item, dict):
                self.invalid_rows += 1
                continue
            variants = item.get("variants")
            if isinstance(variants, list) and variants:
                for variant in variants:
                    add_item(variant)
            else:
                add_item(item)

    def _write_remote_cache(self, url: str, payload: object) -> None:
        path = str(self.json_cache_path or "").strip()
        if not path:
            return
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp_path = f"{path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(
                    {"url": url, "fetched_at": int(time.time()), "payload": payload},
                    fh,
                    ensure_ascii=False,
                )
            os.replace(tmp_path, path)
        except Exception as exc:
            config.logger.warning("写入远程目录缓存失败: %s", exc)

    def _read_remote_cache_entry(self, url: str) -> object:
        path = str(self.json_cache_path or "").strip()
        if not path or not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict) or str(data.get("url", "")) != url:
                return None
            return data
        except Exception:
            return None

    def _read_remote_cache(self, url: str) -> object:
        entry = self._read_remote_cache_entry(url)
        return entry.get("payload") if isinstance(entry, dict) else None

    def _load_csv(self) -> None:
        """加载 CSV 目录。"""
        if not self.csv_path:
            config.logger.warning("未找到游戏目录 CSV 路径")
            return
        if not os.path.isfile(self.csv_path):
            config.logger.warning("游戏目录 CSV 不存在: %s", self.csv_path)
            return

        with open(self.csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not isinstance(row, dict):
                    self.invalid_rows += 1
                    continue

                title = _normalize_title(str(row.get("title", "") or ""))
                down_url = (row.get("down_url") or "").strip()
                if not title or not _is_valid_share_url(down_url):
                    self.invalid_rows += 1
                    continue

                game_id = str(row.get("game_id", "")).strip()
                platform = _normalize_platform(row.get("platform"))
                size_bytes = _safe_int(row.get("filesize_z", "0"))
                size_text = (row.get("list_filesize") or "").strip()
                if not size_text and size_bytes > 0:
                    size_text = _format_size(size_bytes)

                entry = GameCatalogEntry(
                    game_id=game_id or title,
                    title=title,
                    category_parent=str(row.get("category_parent", "")).strip(),
                    categories=normalize_categories(row.get("categories"), platform),
                    down_url=down_url,
                    pwd=str(row.get("pwd", "")).strip(),
                    openpath=str(row.get("openpath", "")).strip(),
                    size_bytes=size_bytes,
                    size_text=size_text,
                    platform=platform,
                    cover_url=str(row.get("cover_url", "") or "").strip(),
                    cover_portrait_url=str(row.get("cover_portrait_url", "") or "").strip(),
                    steam_appid=_safe_int(row.get("steam_appid", "0")),
                )
                self.entries.append(entry)

    def _merge_cover_index(self) -> None:
        """把 cover_index.csv 的封面/平台/appid 合并进目录条目（不覆盖已有值）。"""
        path = str(self.cover_index_path or "").strip()
        if not path or not os.path.isfile(path):
            return

        by_id: Dict[str, Dict[str, str]] = {}
        by_title: Dict[str, Dict[str, str]] = {}
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    if not isinstance(row, dict):
                        continue
                    game_id = str(row.get("game_id", "") or "").strip()
                    title_key = _normalize_title(str(row.get("title", "") or "")).lower()
                    record = {
                        "cover_url": _first_value(row, _COVER_URL_FIELDS),
                        "cover_portrait_url": _first_value(row, _PORTRAIT_FIELDS),
                        "steam_appid": _first_value(row, _APPID_FIELDS, "0"),
                        "platform": _first_value(row, ("platform",)),
                    }
                    if not any(record.values()):
                        continue
                    self.cover_index_total += 1
                    if game_id:
                        by_id[game_id] = record
                    if title_key:
                        by_title[title_key] = record
        except Exception as exc:
            config.logger.warning("读取封面索引失败 %s: %s", path, exc)
            return

        for entry in self.entries:
            record = by_id.get(entry.game_id) or by_title.get(entry.title.lower())
            if not record:
                continue
            if not entry.cover_url:
                entry.cover_url = record.get("cover_url", "") or ""
            if not entry.cover_portrait_url:
                entry.cover_portrait_url = record.get("cover_portrait_url", "") or ""
            if entry.steam_appid <= 0:
                entry.steam_appid = _safe_int(record.get("steam_appid", "0"))
            # 平台以主目录为准，封面索引只补封面/appid，避免索引里的平台标注覆盖主表

    def summary(self) -> Dict[str, object]:
        """返回目录摘要。"""
        return {
            "source": self.source,
            "path": self.csv_path,
            "json_path": self.json_path,
            "cover_index_path": self.cover_index_path,
            "cover_index_total": self.cover_index_total,
            "total": len(self.entries),
            "invalid": self.invalid_rows,
            "with_cover": sum(1 for e in self.entries if e.cover_url or e.cover_portrait_url),
            "platforms": self.platform_counts(),
            "preview": [e.to_dict() for e in self.entries[:8]],
        }

    def platform_counts(self, entries: Optional[List[GameCatalogEntry]] = None) -> List[Dict[str, object]]:
        """各平台条目数（按数量降序）。"""
        counter: Dict[str, int] = {}
        for entry in (entries if entries is not None else self.entries):
            counter[entry.platform] = counter.get(entry.platform, 0) + 1
        rows = [
            {"value": platform, "label": platform.upper() if len(platform) <= 4 else platform, "count": count}
            for platform, count in counter.items()
        ]
        rows.sort(key=lambda item: (-int(item["count"]), str(item["value"])))
        return rows

    def category_counts(
        self,
        limit: int = CATEGORY_FILTER_LIMIT,
        entries: Optional[List[GameCatalogEntry]] = None,
    ) -> List[Dict[str, object]]:
        """分类条目数（取前 N 个，按数量降序）。"""
        counter: Dict[str, int] = {}
        for entry in (entries if entries is not None else self.entries):
            for name in _CATEGORY_SPLIT_RE.split(str(entry.categories or "")):
                text = name.strip()
                if text:
                    counter[text] = counter.get(text, 0) + 1
        rows = [{"value": name, "label": name, "count": count} for name, count in counter.items()]
        rows.sort(key=lambda item: (-int(item["count"]), str(item["value"])))
        return rows[: max(1, int(limit))]

    def list(
        self,
        query: str = "",
        page: int = 1,
        page_size: int = 50,
        platform: str = "",
        category: str = "",
        sort: str = "",
        allowed_platforms: Optional[List[str]] = None,
    ) -> Dict[str, object]:
        """按关键词/平台/分类分页检索，支持排序与平台白名单。"""
        q = (query or "").strip().lower()
        platform_filter = _normalize_platform(platform, default="") if str(platform or "").strip() else ""
        category_filter = str(category or "").strip().lower()
        normalized_page = max(1, int(page))
        normalized_size = max(1, min(200, int(page_size)))

        allowed = {str(item).strip().lower() for item in (allowed_platforms or []) if str(item).strip()}
        base_entries = [
            entry for entry in self.entries if not allowed or entry.platform in allowed
        ]

        matched: List[GameCatalogEntry] = []
        for item in base_entries:
            if platform_filter and platform_filter not in {"all", "*"} and item.platform != platform_filter:
                continue
            if category_filter and category_filter not in item.categories.lower():
                continue
            if q and not (
                q in item.title.lower()
                or q in item.categories.lower()
                or q in item.game_id.lower()
                or q in item.platform.lower()
            ):
                continue
            matched.append(item)

        sort_key = str(sort or "").strip().lower()
        if sort_key == "title":
            matched = sorted(matched, key=lambda item: (item.title.lower(), item.game_id))
        elif sort_key in {"size_desc", "size_asc"}:
            matched = sorted(
                matched,
                key=lambda item: int(item.size_bytes or 0),
                reverse=sort_key == "size_desc",
            )
        elif sort_key == "platform":
            matched = sorted(matched, key=lambda item: (item.platform, item.title.lower()))

        start = (normalized_page - 1) * normalized_size
        end = start + normalized_size

        return {
            "total": len(matched),
            "page": normalized_page,
            "page_size": normalized_size,
            "platform": platform_filter,
            "category": str(category or "").strip(),
            "sort": sort_key,
            "platforms": self.platform_counts(base_entries),
            "categories": self.category_counts(entries=base_entries),
            "items": [e.to_dict() for e in matched[start:end]],
        }

    def get_by_game_id(self, game_id: str) -> Optional[GameCatalogEntry]:
        """按 game_id 查找条目（O(1)）。"""
        target = (game_id or "").strip()
        if not target:
            return None
        return self._by_id.get(target)


def _format_size(size_bytes: int) -> str:
    """格式化字节大小显示。"""
    value = float(size_bytes)
    units = ["B", "KB", "MB", "GB", "TB"]
    unit = units[0]
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            break
        value /= 1024.0
    if unit == "B":
        return f"{int(value)} {unit}"
    return f"{value:.2f} {unit}"
