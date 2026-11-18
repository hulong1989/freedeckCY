"""运行时 JSON 目录加载测试（FREEDECKCY_CATALOG_JSON）。"""

from __future__ import annotations

import json

from game_catalog import GameCatalog, resolve_default_catalog_json_path


def _item(game_id: str, title: str, **overrides):
    item = {
        "game_id": game_id,
        "title": title,
        "platform": "gba",
        "down_url": "https://cloud.189.cn/t/abc",
        "genre": "角色扮演",
        "openpath": "Test Game/game.gba",
        "file_name": "game.gba",
        "size_bytes": 2048,
        "size_text": "2 KB",
        "cover_url": "https://cdn/cover.jpg",
        "pwd": "x1",
    }
    item.update(overrides)
    return item


def test_load_json_catalog_and_variants(tmp_path):
    payload = [
        _item("1", "游戏 A/Game A"),
        {
            "game_id": "group-1",
            "title": "游戏 B",
            "variants": [
                _item("2", "游戏 B/Game B"),
                _item("3", "游戏 B 豪华版"),
            ],
        },
        # 与 variants 里的 game_id 重复，应被去重
        _item("2", "游戏 B 重复"),
        _item("4", "Bad", down_url="https://example.com/x"),
    ]
    path = tmp_path / "all.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    catalog = GameCatalog("", json_path=str(path))
    catalog.load()

    assert catalog.source == "json"
    assert [entry.game_id for entry in catalog.entries] == ["1", "2", "3"]
    assert catalog.invalid_rows == 1

    first = catalog.entries[0]
    assert first.title == "游戏 A/Game A"
    assert first.categories == "角色扮演"
    assert first.openpath == "Test Game/game.gba"
    assert first.size_bytes == 2048
    assert first.cover_url == "https://cdn/cover.jpg"


def test_json_failure_falls_back_to_csv(tmp_path):
    csv_path = tmp_path / "catalog.csv"
    csv_path.write_text(
        "game_id,title,platform,down_url,pwd,openpath,filesize_z,list_filesize,categories,cover_url,server\n"
        "1,CSV Game,pc,https://cloud.189.cn/t/x,,CSV Game/game.exe,100,1 KB,动作冒险,,\n",
        encoding="utf-8-sig",
    )
    missing_json = tmp_path / "missing.json"

    catalog = GameCatalog(str(csv_path), json_path=str(missing_json))
    catalog.load()

    assert catalog.source == "csv"
    assert [entry.game_id for entry in catalog.entries] == ["1"]


def test_resolve_default_catalog_json_path(tmp_path, monkeypatch):
    path = tmp_path / "catalog.json"
    path.write_text("[]", encoding="utf-8")
    monkeypatch.setenv("FREEDECKCY_CATALOG_JSON", str(path))
    monkeypatch.delenv("FRIENDECK_CATALOG_JSON", raising=False)
    assert resolve_default_catalog_json_path() == str(path.resolve())

    monkeypatch.setenv("FREEDECKCY_CATALOG_JSON", str(tmp_path / "nope.json"))
    assert resolve_default_catalog_json_path() == ""


def test_default_catalog_still_csv_without_env(tmp_path, monkeypatch):
    monkeypatch.delenv("FREEDECKCY_CATALOG_JSON", raising=False)
    monkeypatch.delenv("FRIENDECK_CATALOG_JSON", raising=False)
    csv_path = tmp_path / "catalog.csv"
    csv_path.write_text(
        "game_id,title,platform,down_url,openpath\n"
        "1,Only CSV,pc,https://cloud.189.cn/t/x,a.exe\n",
        encoding="utf-8-sig",
    )
    catalog = GameCatalog(str(csv_path))
    catalog.load()
    assert catalog.source == "csv"
    assert len(catalog.entries) == 1


class _FakeResponse:
    def __init__(self, data: bytes):
        self._data = data

    def read(self, limit: int = -1) -> bytes:
        return self._data if limit < 0 else self._data[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_resolve_catalog_json_accepts_url(monkeypatch):
    from game_catalog import resolve_default_catalog_json_path

    url = "https://raw.githubusercontent.com/hulong1989/freedeckCY/main/catalog-json/all.json"
    monkeypatch.setenv("FREEDECKCY_CATALOG_JSON", url)
    monkeypatch.delenv("FRIENDECK_CATALOG_JSON", raising=False)
    assert resolve_default_catalog_json_path() == url


def test_load_remote_json_writes_cache(tmp_path, monkeypatch):
    import game_catalog

    payload = [_item("9", "Remote Game", platform="pc")]
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    calls = []

    def _fake_urlopen(request, timeout=0):
        calls.append(str(request.full_url))
        return _FakeResponse(raw)

    monkeypatch.setattr(game_catalog.urllib.request, "urlopen", _fake_urlopen)
    cache_path = tmp_path / "remote-cache.json"

    catalog = GameCatalog(
        "",
        json_path="https://example.com/all.json",
        json_cache_path=str(cache_path),
    )
    catalog.load()

    assert calls == ["https://example.com/all.json"]
    assert catalog.source == "json-url"
    assert [entry.game_id for entry in catalog.entries] == ["9"]
    assert cache_path.is_file()


def test_remote_cache_used_when_network_fails(tmp_path, monkeypatch):
    import game_catalog

    payload = [_item("10", "Cached Game", platform="pc")]
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    cache_path = tmp_path / "remote-cache.json"

    monkeypatch.setattr(
        game_catalog.urllib.request,
        "urlopen",
        lambda request, timeout=0: _FakeResponse(raw),
    )
    first = GameCatalog("", json_path="https://example.com/all.json", json_cache_path=str(cache_path))
    first.load()
    assert first.source == "json-url"

    def _fail(request, timeout=0):
        raise OSError("network down")

    monkeypatch.setattr(game_catalog.urllib.request, "urlopen", _fail)
    second = GameCatalog("", json_path="https://example.com/all.json", json_cache_path=str(cache_path))
    second.load()

    assert second.source == "json-url-cache"
    assert [entry.game_id for entry in second.entries] == ["10"]


def test_remote_failure_without_cache_falls_back_to_csv(tmp_path, monkeypatch):
    import game_catalog

    def _fail(request, timeout=0):
        raise OSError("network down")

    monkeypatch.setattr(game_catalog.urllib.request, "urlopen", _fail)
    csv_path = tmp_path / "catalog.csv"
    csv_path.write_text(
        "game_id,title,platform,down_url,openpath\n"
        "1,CSV Fallback,pc,https://cloud.189.cn/t/x,a.exe\n",
        encoding="utf-8-sig",
    )
    catalog = GameCatalog(
        str(csv_path),
        json_path="https://example.com/all.json",
        json_cache_path=str(tmp_path / "none.json"),
    )
    catalog.load()
    assert catalog.source == "csv"
    assert [entry.game_id for entry in catalog.entries] == ["1"]


def test_refresh_catalog_removes_remote_cache(tmp_path):
    import asyncio
    from types import SimpleNamespace

    from tianyi_service import TianyiService

    cache = tmp_path / "remote.json"
    cache.write_text("{}", encoding="utf-8")
    loaded = []

    class _Catalog:
        json_cache_path = str(cache)
        source = "csv"
        entries = [1, 2]
        invalid_rows = 0

        def load(self):
            loaded.append(True)
            self.source = "json-url"

    service = TianyiService.__new__(TianyiService)
    service.catalog = _Catalog()
    service._invalidate_panel_cache = lambda **kwargs: None
    result = asyncio.run(service.refresh_catalog())
    assert not cache.exists()
    assert loaded == [True]
    assert result["source"] == "json-url"
    assert result["total"] == 2
