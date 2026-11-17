"""本地 HTTP 全模拟：aiohttp 测试服务器 + 假 service + Origin/Host/诊断端点。

覆盖本地服务安全边界（真实 ``server_manager.cors_middleware``）：
- Host 必须是回环地址（防 DNS rebinding）；
- 写请求 Origin 必须是本服务端口的本机页面；Sec-Fetch-Site: cross-site 直接拒绝；
- CORS 预检只对允许的来源放行；
- 诊断端点（JSON / 自检 / 导出 zip）与错误诊断脱敏。
"""

from __future__ import annotations

import asyncio
import json

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

import server_manager
import tianyi_http


class _FakeDiagnosticsError(RuntimeError):
    def __init__(self, message: str, diagnostics: dict):
        super().__init__(message)
        self.diagnostics = diagnostics


class _FakeService:
    def __init__(self) -> None:
        self.fail_run = False
        self.diagnostics_payload = {
            "generated_at": 1700000000,
            "version": "0.3.1",
            "paths": {"state_file": "/home/deck/.local/share/freedeckCY/tianyi/state.json"},
            "runtime": {"aria2": {"exists": True}},
            "recent_errors": [],
        }
        self.run_payload = {
            "summary": {"ok": 1, "warn": 0, "fail": 0, "skip": 0},
            "checks": [{"id": "plugin", "status": "ok", "detail": "v0.3.1"}],
        }
        self.export_bytes = b"PK\x03\x04fake-diagnostics-zip"

    async def get_panel_state(self, **kwargs):
        return {
            "tasks": [{"task_id": "t1", "status": "active"}],
            "plan": {},
            "settings": {"download_dir": "/tmp/downloads"},
            "login": {"logged_in": False},
            "catalog": {"total": 1},
        }

    async def get_diagnostics(self):
        return dict(self.diagnostics_payload)

    async def run_diagnostics(self, include_network: bool = True):
        if self.fail_run:
            raise _FakeDiagnosticsError(
                "backend exploded",
                {
                    "access_token": "super-secret-token",
                    "nested": {"cookie": "UID=secret", "ok": 1},
                    "trace": ["step1"],
                },
            )
        return dict(self.run_payload)

    async def export_diagnostics(self):
        return bytes(self.export_bytes)


class _FakePlugin:
    def __init__(self, service=None):
        self.tianyi_service = service or _FakeService()


async def _with_client(fn):
    app = web.Application(middlewares=[server_manager.cors_middleware])
    server_manager.setup_main_server_routes(app, _FakePlugin())
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    try:
        await fn(client)
    finally:
        await client.close()


async def _with_secured_client(fn, service=None):
    """把测试服务器的真实端口临时加入允许 Origin 集合。

    使用 ``setup_main_server_routes`` 是为了把 ``/_healthz``、``/`` 也纳入真实路由。
    """
    app = web.Application(middlewares=[server_manager.cors_middleware])
    service = service or _FakeService()
    plugin = _FakePlugin(service)
    server_manager.setup_main_server_routes(app, plugin)
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    port = int(client.port)
    previous = set(server_manager._ALLOWED_ORIGIN_PORTS)
    server_manager._ALLOWED_ORIGIN_PORTS.add(port)
    try:
        await fn(client, port, service)
    finally:
        server_manager._ALLOWED_ORIGIN_PORTS.clear()
        server_manager._ALLOWED_ORIGIN_PORTS.update(previous)
        await client.close()


def test_state_api_simulated():
    async def scenario(client):
        response = await client.get("/api/tianyi/state")
        assert response.status == 200
        payload = await response.json()
        assert payload["status"] == "success"
        assert payload["data"]["tasks"][0]["task_id"] == "t1"
        assert response.headers.get("Access-Control-Allow-Origin") is None

    asyncio.run(_with_client(scenario))


def test_mutating_api_rejects_other_localhost_origin():
    async def scenario(client):
        response = await client.post(
            "/api/tianyi/diagnostics/run",
            headers={"Origin": "http://127.0.0.1:6000"},
        )
        assert response.status == 403
        payload = await response.json()
        assert payload["status"] == "error"

    asyncio.run(_with_client(scenario))


def test_healthz_and_index_are_loopback_only_without_cors():
    async def scenario(client):
        health = await client.get("/_healthz")
        assert health.status == 200
        assert await health.json() == {"status": "ok"}
        assert health.headers.get("Cross-Origin-Resource-Policy") == "same-origin"
        assert health.headers.get("Access-Control-Allow-Origin") is None

        index = await client.get("/")
        assert index.status == 200
        payload = await index.json()
        assert payload["name"] == "freedeckCY"

    asyncio.run(_with_client(scenario))


def test_allowed_origin_gets_cors_headers_on_get():
    async def scenario(client, port, _service):
        origin = f"http://127.0.0.1:{port}"
        response = await client.get("/api/tianyi/state", headers={"Origin": origin})
        assert response.status == 200
        assert response.headers.get("Access-Control-Allow-Origin") == origin
        assert "Origin" in str(response.headers.get("Vary", ""))
        assert response.headers.get("Access-Control-Allow-Methods") == "GET, POST, OPTIONS"

        # localhost 与 127.0.0.1 都算允许来源
        response = await client.get(
            "/api/tianyi/state", headers={"Origin": f"http://localhost:{port}"}
        )
        assert response.status == 200
        assert response.headers.get("Access-Control-Allow-Origin") == f"http://localhost:{port}"

    asyncio.run(_with_secured_client(scenario))


def test_mutating_api_with_allowed_origin_executes():
    async def scenario(client, port, _service):
        origin = f"http://127.0.0.1:{port}"
        response = await client.post(
            "/api/tianyi/diagnostics/run",
            headers={"Origin": origin, "Content-Type": "application/json"},
            data="{}",
        )
        assert response.status == 200
        payload = await response.json()
        assert payload["status"] == "success"
        assert payload["data"]["summary"]["ok"] == 1
        assert response.headers.get("Access-Control-Allow-Origin") == origin

    asyncio.run(_with_secured_client(scenario))


def test_mutating_api_rejects_cross_site_fetch_metadata():
    async def scenario(client, port, _service):
        # 即使 Origin 合法，Sec-Fetch-Site: cross-site 也视为跨站写入。
        response = await client.post(
            "/api/tianyi/diagnostics/run",
            headers={
                "Origin": f"http://127.0.0.1:{port}",
                "Sec-Fetch-Site": "cross-site",
            },
        )
        assert response.status == 403
        payload = await response.json()
        assert "跨站" in payload["message"]

        # 远程 Origin 即使没有 Sec-Fetch-Site 头也必须拒绝。
        response = await client.post(
            "/api/tianyi/diagnostics/run",
            headers={"Origin": "https://evil.example.com"},
        )
        assert response.status == 403

    asyncio.run(_with_secured_client(scenario))


def test_options_preflight_only_for_allowed_origin():
    async def scenario(client, port, _service):
        allowed = f"http://127.0.0.1:{port}"
        response = await client.options(
            "/api/tianyi/settings",
            headers={"Origin": allowed, "Access-Control-Request-Method": "POST"},
        )
        assert response.status == 204
        assert response.headers.get("Access-Control-Allow-Origin") == allowed
        assert response.headers.get("Access-Control-Max-Age") == "600"

        response = await client.options(
            "/api/tianyi/settings",
            headers={"Origin": "http://127.0.0.1:1", "Access-Control-Request-Method": "POST"},
        )
        assert response.status == 403

    asyncio.run(_with_secured_client(scenario))


def test_host_header_must_be_loopback():
    async def scenario(client):
        response = await client.get("/api/tianyi/state", headers={"Host": "evil.example.com"})
        assert response.status == 403
        payload = await response.json()
        assert payload["status"] == "error"
        assert "本机" in payload["message"]

        # 默认 Host（127.0.0.1:<port>）不受影响。
        response = await client.get("/api/tianyi/state")
        assert response.status == 200

    asyncio.run(_with_client(scenario))


def test_diagnostics_endpoints():
    async def scenario(client, _port, _service):
        response = await client.get("/api/tianyi/diagnostics")
        assert response.status == 200
        payload = await response.json()
        assert payload["data"]["version"] == "0.3.1"

        response = await client.post("/api/tianyi/diagnostics/run")
        assert response.status == 200
        payload = await response.json()
        assert payload["data"]["checks"][0]["id"] == "plugin"

        response = await client.get("/api/tianyi/diagnostics/export")
        assert response.status == 200
        assert response.headers["Content-Type"].startswith("application/zip")
        assert "freedeckcy-diagnostics.zip" in response.headers["Content-Disposition"]
        assert await response.read() == b"PK\x03\x04fake-diagnostics-zip"

    asyncio.run(_with_secured_client(scenario))


def test_diagnostics_error_redacts_tokens_and_cookies():
    async def scenario(client, _port, service):
        service.fail_run = True
        response = await client.post("/api/tianyi/diagnostics/run")
        assert response.status == 400
        raw = await response.text()
        # 响应体里不能出现任何 token/cookie 原始值。
        assert "super-secret-token" not in raw
        assert "UID=secret" not in raw
        payload = json.loads(raw)
        assert payload["status"] == "error"
        diagnostics = payload["diagnostics"]
        assert diagnostics["access_token"] == "<redacted>"
        assert diagnostics["nested"]["cookie"] == "<redacted>"
        assert diagnostics["nested"]["ok"] == 1
        assert diagnostics["trace"] == ["step1"]

    asyncio.run(_with_secured_client(scenario))
