# server_manager.py - freedeckCY 本地 HTTP 服务管理

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlparse

from aiohttp import web
import decky

import config
import tianyi_http
import utils


# 本地服务只服务本机页面：Host 必须是回环地址，跨站写请求直接拒绝。
_ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}
_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _host_only(value: str) -> str:
    """从 Host/Origin 中取出主机名（去掉端口与 IPv6 方括号）。"""
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.startswith("["):
        return raw.split("]")[0].lstrip("[").lower()
    return raw.split(":")[0].strip().lower()


def _origin_allowed(origin: str) -> bool:
    """只允许来自本机回环地址页面的跨域请求。"""
    try:
        parsed = urlparse(str(origin or "").strip())
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    return str(parsed.hostname or "").strip().lower() in _ALLOWED_HOSTS


def _forbidden(message: str) -> web.Response:
    """返回 403 JSON。"""
    return web.json_response(
        {"status": "error", "message": message},
        status=403,
    )


@web.middleware
async def cors_middleware(request: web.Request, handler):
    """本地 API 的安全边界与 CORS 头。

    - Host 必须是回环地址（挡住 DNS rebinding）
    - 写请求若带 Origin，必须是本机页面（挡住任意网页 POST 改设置/下单）
    - 不再返回 `Access-Control-Allow-Origin: *`
    """
    try:
        request_host = _host_only(request.host)
    except Exception:
        request_host = ""
    if request_host and request_host not in _ALLOWED_HOSTS:
        return _forbidden("仅允许本机访问本地服务")

    origin = str(request.headers.get("Origin", "") or "").strip()
    fetch_site = str(request.headers.get("Sec-Fetch-Site", "") or "").strip().lower()
    if request.method in _MUTATING_METHODS:
        if fetch_site == "cross-site":
            return _forbidden("拒绝跨站写入请求")
        if origin and not _origin_allowed(origin):
            return _forbidden("拒绝来自非本机页面的写入请求")

    if request.method == "OPTIONS":
        if origin and not _origin_allowed(origin):
            return _forbidden("拒绝跨站预检请求")
        response = web.Response(status=204)
    else:
        try:
            response = await handler(request)
        except web.HTTPException as exc:
            response = exc

    if origin and _origin_allowed(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Max-Age"] = "600"
        response.headers["Vary"] = "Origin"
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    return response


async def _handle_index(request: web.Request) -> web.Response:
    """本地服务首页。"""
    return web.json_response(
        {
            "status": "success",
            "name": "freedeckCY",
            "message": "freedeckCY local server running",
        }
    )


async def _handle_health(request: web.Request) -> web.Response:
    """基础健康检查接口。"""
    return web.json_response({"status": "ok"})


def setup_main_server_routes(app: web.Application, plugin: Any) -> None:
    """挂载 freedeckCY 需要的全部路由。"""
    app.router.add_get("/", _handle_index)
    app.router.add_get("/_healthz", _handle_health)

    # 天翼页面和业务 API
    tianyi_http.setup_routes(app, plugin)

    # CORS 预检
    app.router.add_route("OPTIONS", "/{path:.*}", lambda request: web.Response(status=204))


async def _cleanup_server(plugin: Any) -> None:
    """安全清理 aiohttp 资源。"""
    runner = getattr(plugin, "runner", None)
    if runner is not None:
        try:
            await runner.cleanup()
        except Exception as exc:
            config.logger.warning(f"Server cleanup warning: {exc}")

    plugin.site = None
    plugin.runner = None
    plugin.app = None


def _normalize_port(port: int) -> int:
    value = int(port)
    if value < 1 or value > 65535:
        raise ValueError("端口范围应为 1-65535")
    return value


async def start_server(plugin: Any, port: int = config.DEFAULT_SERVER_PORT) -> dict:
    """启动本地 HTTP 服务。"""
    try:
        target_port = _normalize_port(port)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    if bool(getattr(plugin, "server_running", False)) and getattr(plugin, "runner", None) is not None:
        if int(getattr(plugin, "server_port", target_port)) == target_port:
            return {
                "status": "success",
                "message": "服务器已在运行",
                "ip_address": "127.0.0.1",
                "port": target_port,
                "url": f"http://127.0.0.1:{target_port}",
            }
        await _cleanup_server(plugin)

    if utils.is_port_in_use(target_port):
        config.logger.warning("Local web start rejected: port %s already in use", target_port)
        return {"status": "error", "message": f"端口 {target_port} 已被占用"}

    try:
        plugin.server_port = target_port
        plugin.app = web.Application(
            middlewares=[cors_middleware],
            # 本地 API 只需要传路径/ID/小 JSON，不需要 1GB 上限。
            client_max_size=16 * 1024 * 1024,
        )
        plugin.app["plugin_state"] = plugin
        setup_main_server_routes(plugin.app, plugin)

        plugin.runner = web.AppRunner(plugin.app)
        await plugin.runner.setup()
        plugin.site = web.TCPSite(plugin.runner, plugin.server_host, plugin.server_port)
        await plugin.site.start()

        plugin.server_running = True
        await save_settings(plugin)

        url = f"http://127.0.0.1:{plugin.server_port}"
        config.logger.info(f"HTTP server started: {url}")
        return {
            "status": "success",
            "message": "服务器已启动",
            "ip_address": "127.0.0.1",
            "port": plugin.server_port,
            "url": url,
        }
    except Exception as exc:
        await _cleanup_server(plugin)
        plugin.server_running = False
        await save_settings(plugin)
        config.logger.error(f"Failed to start server: {exc}")
        return {"status": "error", "message": str(exc)}


async def stop_server(plugin: Any) -> dict:
    """停止本地 HTTP 服务。"""
    await _cleanup_server(plugin)
    plugin.server_running = False

    try:
        await utils.wait_for_port_release(int(getattr(plugin, "server_port", config.DEFAULT_SERVER_PORT)))
    except Exception:
        pass

    await save_settings(plugin)
    return {"status": "success", "message": "服务器已停止"}


async def get_server_status(plugin: Any) -> dict:
    """返回本地 HTTP 服务状态。"""
    current_port = int(getattr(plugin, "server_port", config.DEFAULT_SERVER_PORT))
    own_runner_alive = bool(getattr(plugin, "runner", None) is not None and getattr(plugin, "server_running", False))
    port_alive = utils.is_port_in_use(current_port)
    running = bool(own_runner_alive and port_alive)

    if bool(getattr(plugin, "server_running", False)) != running:
        plugin.server_running = running
        await save_settings(plugin)

    return {
        "running": running,
        "port": current_port,
        "host": getattr(plugin, "server_host", config.DEFAULT_SERVER_HOST),
        "ip_address": "127.0.0.1",
        "port_in_use": port_alive,
    }


def _get_settings_store(plugin: Any):
    """获取 Decky 设置存储对象。"""
    plugin_store = getattr(plugin, "settings", None)
    if plugin_store and hasattr(plugin_store, "getSetting") and hasattr(plugin_store, "setSetting"):
        return plugin_store

    decky_store = getattr(decky, "settings", None)
    if decky_store and hasattr(decky_store, "getSetting") and hasattr(decky_store, "setSetting"):
        return decky_store

    return None


def _backup_settings_path(plugin: Any) -> str:
    """获取本地设置备份路径。"""
    settings_dir = getattr(decky, "DECKY_PLUGIN_SETTINGS_DIR", None) or getattr(
        plugin,
        "decky_send_dir",
        config.DECKY_SEND_DIR,
    )
    return os.path.join(settings_dir, "settings.json")


def _load_settings_backup(plugin: Any) -> dict:
    """从文件读取设置备份。"""
    path = _backup_settings_path(plugin)
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        config.logger.warning(f"Load backup settings failed: {exc}")
        return {}


def _save_settings_backup(plugin: Any, settings: dict) -> None:
    """写入设置备份文件。"""
    path = _backup_settings_path(plugin)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)


async def load_settings(plugin: Any) -> None:
    """加载 freedeckCY 设置。"""
    settings: dict = {}
    store = _get_settings_store(plugin)

    if store is not None:
        try:
            value = store.getSetting(plugin.SETTINGS_KEY, {})
            if isinstance(value, dict):
                settings = value
        except Exception as exc:
            config.logger.warning(f"Read settings from Decky store failed: {exc}")

    if not settings:
        settings = _load_settings_backup(plugin)

    plugin.server_running = bool(settings.get(plugin.SETTING_RUNNING, False))

    try:
        plugin.server_port = _normalize_port(settings.get(plugin.SETTING_PORT, config.DEFAULT_SERVER_PORT))
    except Exception:
        plugin.server_port = config.DEFAULT_SERVER_PORT

    download_dir = settings.get(plugin.SETTING_DOWNLOAD_DIR, config.DOWNLOADS_DIR)
    if isinstance(download_dir, str) and download_dir.strip():
        plugin.downloads_dir = os.path.realpath(os.path.expanduser(download_dir.strip()))
    else:
        plugin.downloads_dir = config.DOWNLOADS_DIR

    try:
        os.makedirs(plugin.downloads_dir, exist_ok=True)
    except Exception as exc:
        config.logger.warning(f"Ensure download directory failed: {exc}")


async def save_settings(plugin: Any) -> None:
    """保存 freedeckCY 设置。"""
    settings = {
        plugin.SETTING_RUNNING: bool(getattr(plugin, "server_running", False)),
        plugin.SETTING_PORT: int(getattr(plugin, "server_port", config.DEFAULT_SERVER_PORT)),
        plugin.SETTING_DOWNLOAD_DIR: str(getattr(plugin, "downloads_dir", config.DOWNLOADS_DIR)),
    }

    store = _get_settings_store(plugin)
    if store is not None:
        try:
            store.setSetting(plugin.SETTINGS_KEY, settings)
        except Exception as exc:
            config.logger.warning(f"Save settings to Decky store failed: {exc}")

    try:
        _save_settings_backup(plugin, settings)
    except Exception as exc:
        config.logger.warning(f"Save backup settings failed: {exc}")
