"""诊断自检：不依赖网络也要能返回结构化检查。"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from tianyi_service import TianyiService
from tianyi_store import TianyiSettings, TianyiStateStore


def test_run_diagnostics_returns_checks_without_network(tmp_path, monkeypatch):
    service = TianyiService.__new__(TianyiService)
    service.store = TianyiStateStore(str(tmp_path / "state.json"))
    service.store.settings = TianyiSettings(
        download_dir=str(tmp_path / "downloads"),
        install_dir=str(tmp_path / "installed"),
    )
    service.plugin = SimpleNamespace(downloads_dir=str(tmp_path), server_running=False, server_port=0)
    service.catalog = SimpleNamespace(
        entries=[object()],
        platform_counts=lambda: [{"value": "pc", "label": "PC", "count": 1}],
        cover_index_total=0,
    )
    service._invalidate_panel_cache = lambda **kwargs: None
    monkeypatch.setattr("tianyi_service._find_steam_root", lambda: "")
    monkeypatch.setattr("tianyi_service._tail_text", lambda path, limit=200: "")
    result = asyncio.run(service.run_diagnostics(include_network=False))
    ids = {item["id"] for item in result["checks"]}
    assert {"plugin", "state_dir", "download_dir", "install_dir", "catalog", "steam", "baidu_qr", "tasks", "log"} <= ids
    assert result["summary"]["fail"] >= 0
    assert "sign" not in str(result).lower()
