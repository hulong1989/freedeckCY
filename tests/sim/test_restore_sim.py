"""云存档全模拟：假 7z 压缩/解压，覆盖上传清单、目录层恢复。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import config
from tianyi_service import TianyiService
from tests.sim.fakes import FakeSevenZip


def test_psp_archive_restore_preserves_title_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path / "state"))
    service = TianyiService.__new__(TianyiService)
    service.seven_zip = FakeSevenZip()

    savedata = tmp_path / "PSP" / "SAVEDATA"
    title_dir = savedata / "ULUS12345"
    title_dir.mkdir(parents=True)
    (title_dir / "DATA.BIN").write_bytes(b"save")

    archive_path, _meta = asyncio.run(
        service._archive_single_game_saves(
            candidate={
                "game_key": "psp-demo",
                "game_id": "psp-1",
                "game_title": "PSP Demo",
                "source_paths": [str(title_dir)],
                "playtime": {},
            },
            timestamp="20260101_000000",
        )
    )
    extract = tmp_path / "extract"
    service.seven_zip.extract_archive(archive_path, str(extract))
    manifest = json.loads((extract / "manifest.json").read_text(encoding="utf-8"))
    entries = service._normalize_cloud_restore_entries(manifest=manifest, extract_dir=str(extract))
    assert entries[0]["archive_rel_path"] == "ULUS12345"

    target = tmp_path / "restore" / "SAVEDATA"
    target.mkdir(parents=True)
    plan = service._build_restore_copy_plan(
        extract_dir=str(extract),
        entries=entries,
        selected_entry_ids=[entries[0]["entry_id"]],
        target_dir=str(target),
    )
    assert plan["copy_pairs"][0][1] == str(target / "ULUS12345" / "DATA.BIN")


def test_restore_flat_legacy_manifest_into_title_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DECKY_SEND_DIR", str(tmp_path / "state"))
    service = TianyiService.__new__(TianyiService)
    extract = tmp_path / "extract"
    extract.mkdir()
    (extract / "DATA.BIN").write_bytes(b"save")
    entries = service._normalize_cloud_restore_entries(
        manifest={"entries": [{"entry_id": "e1", "name": "ULUS12345", "archive_rel_path": "ULUS12345"}]},
        extract_dir=str(extract),
    )
    target = tmp_path / "SAVEDATA"
    target.mkdir()
    plan = service._build_restore_copy_plan(
        extract_dir=str(extract),
        entries=entries,
        selected_entry_ids=["e1"],
        target_dir=str(target),
    )
    assert plan["copy_pairs"][0][1] == str(target / "ULUS12345" / "DATA.BIN")
