"""仓库内 catalog-json/ 快照的一致性测试。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = REPO_ROOT / "catalog-json"


def _read_json(name: str):
    return json.loads((SNAPSHOT / name).read_text(encoding="utf-8"))


def test_manifest_hashes_and_counts():
    manifest = _read_json("manifest.json")
    assert manifest["schema_version"] == 1
    assert manifest["total"] == 7084
    assert sum(manifest["platforms"].values()) == manifest["total"]

    for rel, info in manifest["files"].items():
        path = SNAPSHOT / rel
        assert path.is_file(), rel
        raw = path.read_bytes()
        assert len(json.loads(raw)) == info["count"], rel
        assert hashlib.sha256(raw).hexdigest() == info["sha256"], rel


def test_all_and_platform_items_are_valid():
    all_items = _read_json("all.json")
    platforms = {item["platform"] for item in all_items}
    assert platforms == {"pc", "gba", "fc", "nds", "psp", "3ds", "ps2", "ps1", "ps3", "md", "switch"}

    for item in all_items:
        assert item["game_id"]
        assert item["title"]
        assert item["down_url"].startswith(("https://cloud.189.cn/", "http://cloud.189.cn/"))
        assert isinstance(item["size_bytes"], int)
        assert item["size_bytes"] >= 0

    for platform in platforms:
        rows = _read_json(f"platform/{platform}.json")
        assert rows, platform
        assert all(row["platform"] == platform for row in rows)

    curated = _read_json("curated/gba.json")
    assert 0 < len(curated) <= 60
    assert all(row["platform"] == "gba" for row in curated)


def test_schemas_and_emu_template_parse():
    schema = _read_json("schema.json")
    assert schema["$schema"].endswith("draft-07/schema#")
    assert "down_url" in schema["properties"]

    emu_schema = _read_json("emu.schema.json")
    assert emu_schema["type"] == "object"

    emu = _read_json("emu.example.json")
    for key, value in emu.items():
        if key.startswith("_"):
            continue
        assert value["share_url"] == ""
        assert value["pwd"] == ""
        assert value["file_name"] == ""
