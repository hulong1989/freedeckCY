"""插件更新检查与下载流程。

从 tianyi_service.TianyiService 拆出的第一块（P0 渐进拆分）：
- 自有服务器签名清单
- GitHub Release 回退
- 更新包下载与 SHA256 校验

只依赖 self.plugin / self.store / self._update_cache，不反向导入 tianyi_service。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import platform
import re
import tempfile
import time
from typing import Any, Dict, Optional
from urllib.parse import urljoin, urlparse

import aiohttp

import catalog_signature
import config
from tianyi_client import build_tls_context


logger = logging.getLogger("freedeckcy")


def _parse_version(value: str):
    """把 1.2.3 / 1.2.3-beta 解析成可比较元组。"""
    parts = []
    for token in re.split(r"[.\-+]", str(value or "").strip().lstrip("vV")):
        match = re.match(r"\d+", token)
        if match:
            parts.append(int(match.group(0)))
    return tuple(parts)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _redact_update_path(value: str) -> str:
    text = str(value or "")
    home = os.path.expanduser("~")
    if home and text.startswith(home):
        return "~" + text[len(home):]
    return text


def _default_update_download_dir() -> str:
    """插件更新包固定写本机内置硬盘 ~/Downloads，不跟随 SD 卡下载目录。"""
    return os.path.join(os.path.expanduser("~"), "Downloads")


def _describe_exception(exc: BaseException) -> str:
    text = str(exc).strip()
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__


class UpdateFlowMixin:
    """更新检查/下载；由 TianyiService 继承。"""

    async def _check_server_update(self, current: str) -> Optional[Dict[str, Any]]:
        """从自有目录服务器读取并验签插件更新清单。"""
        catalog_url = str(getattr(self.store.settings, "catalog_url", "") or "").strip()
        if not catalog_url:
            catalog_url = str(getattr(config, "DEFAULT_CATALOG_CSV_URL", "") or "").strip()
        parsed = urlparse(catalog_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None
        base = f"{parsed.scheme}://{parsed.netloc}"
        latest_url = base + "/api/update/latest"
        headers = {"Accept": "application/json", "User-Agent": "freedeckCY"}
        try:
            timeout = aiohttp.ClientTimeout(total=12)
            connector = aiohttp.TCPConnector(ssl=build_tls_context())
            async with aiohttp.ClientSession(timeout=timeout, connector=connector, headers=headers) as session:
                async with session.get(latest_url) as response:
                    if int(response.status) != 200:
                        return None
                    raw = await response.read()
                async with session.get(latest_url + ".json.sig") as response:
                    if int(response.status) != 200:
                        return None
                    signature = (await response.text()).strip()
        except Exception as exc:
            logger.info("自有服务器更新检查不可用: %s", _describe_exception(exc))
            return None
        if not catalog_signature.verify_signature(raw, signature):
            logger.warning("自有服务器更新清单签名无效")
            return None
        try:
            manifest = json.loads(raw.decode("utf-8"))
        except Exception:
            return None
        if not isinstance(manifest, dict):
            return None
        latest = str(manifest.get("version", "") or "").strip().lstrip("vV")
        if not latest:
            return None
        assets = []
        for item in list(manifest.get("assets") or []):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "") or "").strip()
            url = str(item.get("url", "") or "").strip()
            sha256 = str(item.get("sha256", "") or "").strip().lower()
            if not name or not url or not sha256:
                continue
            absolute_url = urljoin(base + "/", url)
            assets.append({
                "name": name,
                "url": absolute_url,
                "size": max(0, _safe_int(item.get("size"), 0)),
                "digest": f"sha256:{sha256}",
                "arch": str(item.get("arch", "") or "").strip(),
            })
        return {
            "ok": True,
            "source": "server",
            "current": current,
            "latest": latest,
            "has_update": _parse_version(latest) > _parse_version(current),
            "url": latest_url,
            "name": str(manifest.get("notes", "") or ""),
            "published_at": str(manifest.get("published_at", "") or ""),
            "assets": assets,
        }

    async def check_update(self, force: bool = False) -> Dict[str, Any]:
        """检查自有服务器/GitHub 最新版本（默认 2 分钟缓存）。"""
        now = time.time()
        if not force and self._update_cache and now - self._update_cache_at < 120:
            return dict(self._update_cache)

        current = self._plugin_version() or "0.0.0"
        server_result = await self._check_server_update(current)
        if server_result and server_result.get("ok"):
            self._update_cache = server_result
            self._update_cache_at = now
            return dict(server_result)
        api_url = "https://api.github.com/repos/hulong1989/freedeckCY/releases/latest"
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "freedeckCY",
        }
        payload = None
        tls_insecure = False
        last_error = ""
        for insecure in (False, True):
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                connector = aiohttp.TCPConnector(ssl=False if insecure else build_tls_context())
                async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                    async with session.get(api_url, headers=headers) as response:
                        if int(response.status) != 200:
                            return {
                                "ok": False,
                                "current": current,
                                "message": f"GitHub API HTTP {int(response.status)}",
                                "tls_insecure": bool(insecure),
                            }
                        data = await response.json(content_type=None)
                        if not isinstance(data, dict):
                            raise ValueError("GitHub API 返回不是 JSON 对象")
                        payload = data
                        tls_insecure = insecure
                        break
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                # 仅证书链失败时做一次降级；连接超时/HTTP 错误不重试。
                cert_failed = "CERTIFICATE_VERIFY_FAILED" in str(exc).upper() or "CERTIFICATE" in str(exc).upper()
                if not insecure and cert_failed:
                    continue
                break
        if payload is None:
            return {"ok": False, "current": current, "message": f"检查更新失败: {last_error}"}
        self._update_tls_insecure = bool(tls_insecure)

        latest = str(payload.get("tag_name") or "").strip().lstrip("vV")
        assets = []
        for item in list(payload.get("assets") or []):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            url = str(item.get("browser_download_url") or "").strip()
            if not name or not url:
                continue
            assets.append({
                "name": name,
                "url": url,
                "size": max(0, _safe_int(item.get("size"), 0)),
                "digest": str(item.get("digest") or "").strip(),
            })
        result = {
            "ok": True,
            "current": current,
            "latest": latest,
            "has_update": _parse_version(latest) > _parse_version(current),
            "url": str(payload.get("html_url") or ""),
            "name": str(payload.get("name") or ""),
            "published_at": str(payload.get("published_at") or ""),
            "assets": assets,
            "tls_insecure": bool(tls_insecure),
        }
        self._update_cache = result
        self._update_cache_at = now
        return dict(result)

    async def download_update(self) -> Dict[str, Any]:
        """下载并校验官方 Release 更新包，返回本地路径（不自动覆盖插件）。"""
        update = await self.check_update()
        if not update.get("ok"):
            return {"ok": False, "message": str(update.get("message") or "检查更新失败")}
        if not update.get("has_update"):
            return {
                "ok": False,
                "current": update.get("current", ""),
                "latest": update.get("latest", ""),
                "message": "当前已经是最新版本",
            }
        assets = [item for item in list(update.get("assets") or []) if isinstance(item, dict)]
        machine = str(platform.machine() or "").lower()
        arch_suffix = "-arm64.zip" if machine in {"aarch64", "arm64"} else ".zip"
        if arch_suffix == "-arm64.zip":
            candidates = [item for item in assets if str(item.get("name") or "").endswith("-arm64.zip")]
        else:
            candidates = [
                item
                for item in assets
                if str(item.get("name") or "").endswith(".zip")
                and not str(item.get("name") or "").endswith("-arm64.zip")
            ]
        if not candidates:
            return {"ok": False, "message": "Release 中没有匹配当前架构的插件包"}
        asset = candidates[0]
        update_insecure = bool(getattr(self, "_update_tls_insecure", False) or update.get("tls_insecure"))
        asset_name = str(asset.get("name") or "")
        asset_url = str(asset.get("url") or "")
        expected_sha = ""
        digest = str(asset.get("digest") or "").strip()
        if digest.lower().startswith("sha256:"):
            expected_sha = digest.split(":", 1)[1].strip().lower()
        if not expected_sha:
            sha_asset = next((item for item in assets if str(item.get("name") or "") == asset_name + ".sha256"), None)
            if sha_asset:
                try:
                    timeout = aiohttp.ClientTimeout(total=15)
                    sha_connector = aiohttp.TCPConnector(ssl=False if update_insecure else build_tls_context())
                    async with aiohttp.ClientSession(timeout=timeout, connector=sha_connector) as session:
                        async with session.get(str(sha_asset.get("url")), headers={"User-Agent": "freedeckCY"}) as resp:
                            if int(resp.status) == 200:
                                text = (await resp.text())[:4096]
                                match = re.search(r"\b([0-9a-fA-F]{64})\b", text)
                                if match:
                                    expected_sha = match.group(1).lower()
                except Exception as exc:
                    return {"ok": False, "message": f"读取 SHA256 失败: {exc}"}
        if not expected_sha:
            return {"ok": False, "message": "Release 缺少 SHA256 校验值，已拒绝下载"}
        target_dir = os.path.realpath(_default_update_download_dir())
        await asyncio.to_thread(os.makedirs, target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, asset_name)
        digest_calc = hashlib.sha256()
        total = 0
        timeout = aiohttp.ClientTimeout(total=300, connect=20)
        try:
            connector = aiohttp.TCPConnector(ssl=False if update_insecure else build_tls_context())
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.get(asset_url, headers={"User-Agent": "freedeckCY"}) as resp:
                    if int(resp.status) != 200:
                        return {"ok": False, "message": f"下载更新包失败 HTTP {int(resp.status)}"}
                    fd, temp_path = tempfile.mkstemp(prefix=".freedeckcy_update_", suffix=".zip", dir=target_dir)
                    try:
                        with os.fdopen(fd, "wb") as fh:
                            async for chunk in resp.content.iter_chunked(1024 * 1024):
                                total += len(chunk)
                                if total > 256 * 1024 * 1024:
                                    raise ValueError("更新包超过 256MB")
                                digest_calc.update(chunk)
                                fh.write(chunk)
                            fh.flush()
                            os.fsync(fh.fileno())
                        actual_sha = digest_calc.hexdigest()
                        if expected_sha and actual_sha != expected_sha:
                            raise ValueError("更新包 SHA256 校验失败")
                        os.replace(temp_path, target_path)
                    except Exception:
                        try:
                            os.unlink(temp_path)
                        except OSError:
                            pass
                        raise
        except Exception as exc:
            return {"ok": False, "message": f"下载更新包失败: {exc}"}
        return {
            "ok": True,
            "current": update.get("current", ""),
            "latest": update.get("latest", ""),
            "path": _redact_update_path(target_path),
            "filename": asset_name,
            "size": total,
            "sha256": digest_calc.hexdigest(),
            "tls_insecure": bool(update_insecure),
            "message": "更新包已下载并校验；请用 Decky → 开发者 → 从文件安装插件",
        }

