"""自动云存档：Ludusavi 清单匹配 + gamewatch 进程检测。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import gamewatch
import save_manifest
import tianyi_service as svc_module
from tianyi_store import TianyiSettings, TianyiStateStore


def test_gamewatcher_start_end_events():
    running = {"value": False}
    watcher = gamewatch.GameWatcher(lambda path: running["value"])
    record = SimpleNamespace(game_id="g1", install_path="/tmp/g1")

    assert watcher.poll([record]) == []  # 首次只记录状态
    running["value"] = True
    events = watcher.poll([record])
    assert [event["type"] for event in events] == ["start"]
    assert events[0]["game_id"] == "g1"

    running["value"] = False
    events = watcher.poll([record])
    assert [event["type"] for event in events] == ["end"]


def test_gamewatcher_forgets_removed_games():
    watcher = gamewatch.GameWatcher(lambda path: True)
    record = SimpleNamespace(game_id="g1", install_path="/tmp/g1")
    watcher.poll([record])
    assert watcher._states == {"g1": True}
    watcher.poll([])
    assert watcher._states == {}


def test_manifest_match_and_resolve(tmp_path, monkeypatch):
    prefix = tmp_path / "pfx"
    appdata = prefix / "drive_c" / "users" / "steamuser" / "AppData" / "Roaming" / "TestGame"
    appdata.mkdir(parents=True)
    (appdata / "slot1.sav").write_bytes(b"save")
    install = tmp_path / "installed" / "TestGame"
    (install / "saves").mkdir(parents=True)
    (install / "saves" / "local.dat").write_bytes(b"x")

    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "Test Game": {
                    "steam": {"id": 123456},
                    "files": {
                        "<winAppData>/TestGame/*.sav": {"tags": ["save"], "when": [{"os": "windows"}]},
                        "<base>/saves": {"tags": ["save"]},
                        "<winAppData>/TestGame/linux-only": {"when": [{"os": "linux"}]},
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("FREEDECKCY_LUDUSAVI_MANIFEST", str(manifest))

    data = save_manifest.load_manifest(str(tmp_path / "plugin"))
    key, info = save_manifest.match_manifest(data, titles=["测试/Test Game"])
    assert key == "Test Game"
    assert info

    paths = save_manifest.resolve_manifest_paths(
        info,
        prefix_dir=str(prefix),
        install_dir=str(install),
    )
    assert any(path.endswith("slot1.sav") for path in paths)
    assert any(path.endswith("saves") for path in paths)
    assert all("linux-only" not in path for path in paths)

    by_id, _ = save_manifest.match_manifest(data, titles=["完全不同"], app_id=123456)
    assert by_id == "Test Game"

    missing, info_missing = save_manifest.match_manifest(data, titles=["No Such Game"])
    assert missing == "" and info_missing == {}


def test_auto_upload_triggers_task(monkeypatch):
    service = svc_module.TianyiService.__new__(svc_module.TianyiService)
    service.store = SimpleNamespace(
        settings=TianyiSettings(cloud_save_auto_upload=True),
        login=SimpleNamespace(cookie="UID=test"),
    )
    service._cloud_save_task = None
    service._auto_cloud_upload_task = None
    service._last_auto_cloud_upload_at = 0.0

    calls = []

    async def _start(**kwargs):
        calls.append(kwargs)
        return {"accepted": True, "message": "ok"}

    service.start_cloud_save_upload = _start  # type: ignore[assignment]

    async def _run():
        service._maybe_auto_cloud_upload(SimpleNamespace(game_id="g1", game_title="Game"))
        if service._auto_cloud_upload_task:
            await service._auto_cloud_upload_task
        await asyncio.sleep(0)

    asyncio.run(_run())
    assert calls and calls[0].get("game_ids") == ["g1"]


def test_auto_upload_respects_setting(monkeypatch):
    service = svc_module.TianyiService.__new__(svc_module.TianyiService)
    service.store = SimpleNamespace(
        settings=TianyiSettings(cloud_save_auto_upload=False),
        login=SimpleNamespace(cookie="UID=test"),
    )
    service._cloud_save_task = None
    service._auto_cloud_upload_task = None
    service._last_auto_cloud_upload_at = 0.0

    calls = []

    async def _start():
        calls.append("start")
        return {"accepted": True}

    service.start_cloud_save_upload = _start  # type: ignore[assignment]
    service._maybe_auto_cloud_upload(SimpleNamespace(game_id="g1"))
    assert calls == []
    assert service._auto_cloud_upload_task is None


def test_auto_upload_skips_when_upload_running():
    service = svc_module.TianyiService.__new__(svc_module.TianyiService)
    service.store = SimpleNamespace(
        settings=TianyiSettings(cloud_save_auto_upload=True),
        login=SimpleNamespace(cookie="UID=test"),
    )
    service._cloud_save_task = SimpleNamespace(done=lambda: False)
    service._auto_cloud_upload_task = None
    service._last_auto_cloud_upload_at = 0.0

    calls = []

    async def _start():
        calls.append("start")
        return {"accepted": True}

    service.start_cloud_save_upload = _start  # type: ignore[assignment]
    service._maybe_auto_cloud_upload(SimpleNamespace(game_id="g1"))
    assert calls == []


def test_settings_cloud_save_auto_upload_roundtrip(tmp_path):
    state_file = tmp_path / "state.json"
    store = TianyiStateStore(str(state_file))
    assert store.settings.cloud_save_auto_upload is True
    store.set_settings(cloud_save_auto_upload=False)
    reloaded = TianyiStateStore(str(state_file))
    reloaded.load()
    assert reloaded.settings.cloud_save_auto_upload is False


def test_cloud_save_fingerprint_detects_changes(tmp_path):
    service = svc_module.TianyiService.__new__(svc_module.TianyiService)
    save_dir = tmp_path / "saves"
    save_dir.mkdir()
    save_file = save_dir / "slot1.sav"
    save_file.write_bytes(b"one")
    first = service._cloud_save_fingerprint([str(save_dir)])
    assert first

    save_file.write_bytes(b"two")
    second = service._cloud_save_fingerprint([str(save_dir)])
    assert second and second != first

    assert service._cloud_save_fingerprint([str(tmp_path / "missing")]) == ""


def test_store_persists_cloud_save_fingerprints(tmp_path):
    state_file = tmp_path / "state.json"
    store = TianyiStateStore(str(state_file))
    store.cloud_save_fingerprints["game-1"] = "abc123"
    store.save()

    reloaded = TianyiStateStore(str(state_file))
    reloaded.load()
    assert reloaded.cloud_save_fingerprints == {"game-1": "abc123"}
