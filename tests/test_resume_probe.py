"""Range 续传探测与恢复下载路径的回归测试。"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import tianyi_client as client
import tianyi_service as svc_module
from tianyi_service import TianyiService
from tianyi_store import TianyiLoginState, TianyiSettings, TianyiStateStore, TianyiTaskRecord


class _FakeResponse:
    def __init__(self, status: int, headers=None):
        self.status = status
        self.headers = dict(headers or {})

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self, response, captured, exc=None):
        self.response = response
        self.captured = captured
        self.exc = exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url, headers=None, allow_redirects=True):
        self.captured["url"] = url
        self.captured["headers"] = dict(headers or {})
        self.captured["allow_redirects"] = allow_redirects
        if self.exc is not None:
            raise self.exc
        return self.response


def _patch_session(monkeypatch, *, status=200, headers=None, exc=None):
    captured = {}
    response = _FakeResponse(status, headers)
    monkeypatch.setattr(
        client,
        "_create_session",
        lambda **kwargs: _FakeSession(response, captured, exc),
    )
    return captured


def test_probe_resume_http_206(monkeypatch):
    captured = _patch_session(monkeypatch, status=206, headers={"Content-Range": "bytes 0-0/100"})
    supported, detail = asyncio.run(client.probe_resume_support("https://example.com/file.bin"))
    assert supported is True
    assert "206" in detail
    assert captured["headers"]["Range"] == "bytes=0-0"


def test_probe_resume_accept_ranges_header(monkeypatch):
    _patch_session(monkeypatch, status=200, headers={"Accept-Ranges": "bytes"})
    supported, detail = asyncio.run(client.probe_resume_support("https://example.com/file.bin"))
    assert supported is True
    assert "accept-ranges" in detail.lower()


def test_probe_resume_content_range_without_206(monkeypatch):
    _patch_session(monkeypatch, status=200, headers={"Content-Range": "bytes 0-0/100"})
    supported, detail = asyncio.run(client.probe_resume_support("https://example.com/file.bin"))
    assert supported is True
    assert "content-range" in detail.lower()


def test_probe_resume_200_without_range_headers(monkeypatch):
    _patch_session(monkeypatch, status=200)
    supported, detail = asyncio.run(client.probe_resume_support("https://example.com/file.bin"))
    assert supported is False
    assert "without range" in detail


def test_probe_resume_error_is_conservative(monkeypatch):
    _patch_session(monkeypatch, exc=OSError("network down"))
    supported, detail = asyncio.run(client.probe_resume_support("https://example.com/file.bin"))
    assert supported is True
    assert "probe error" in detail


def test_probe_resume_merges_custom_headers(monkeypatch):
    captured = _patch_session(monkeypatch, status=206)
    asyncio.run(
        client.probe_resume_support(
            "https://example.com/file.bin",
            {"Cookie": "BDUSS=abc", "Referer": "https://pan.baidu.com/disk/home"},
        )
    )
    assert captured["headers"]["Cookie"] == "BDUSS=abc"
    assert captured["headers"]["Referer"] == "https://pan.baidu.com/disk/home"
    assert captured["allow_redirects"] is True


def test_probe_resume_invalid_url_is_conservative():
    supported, detail = asyncio.run(client.probe_resume_support(""))
    assert supported is True
    assert "invalid url" in detail


class _FakeAria2:
    def __init__(self):
        self.added = []
        self.replaced = []

    async def add_uri(self, **kwargs):
        self.added.append(kwargs)
        return "new-gid"

    async def replace_uri(self, gid, direct_url):
        self.replaced.append((gid, direct_url))


def _service(tmp_path):
    service = TianyiService.__new__(TianyiService)
    service.store = TianyiStateStore(str(tmp_path / "state.json"))
    service.store.settings = TianyiSettings(download_dir=str(tmp_path), install_dir=str(tmp_path / "games"))
    service.store.login = TianyiLoginState(cookie="cookie=1")
    service.aria2 = _FakeAria2()
    service._readd_attempts = {}
    service._task_sync_misses = {}
    return service


def _task(tmp_path, *, gid="", progress=50.0) -> TianyiTaskRecord:
    return TianyiTaskRecord(
        task_id="t1",
        gid=gid,
        game_id="g1",
        game_title="Demo",
        share_code="code",
        share_id="share",
        file_id="file",
        file_name="demo.bin",
        download_dir=str(tmp_path),
        local_path=str(tmp_path / "demo.bin"),
        status="error",
        progress=progress,
        speed=0,
        provider="tianyi",
    )


def _patch_direct_url(monkeypatch):
    async def fake_token(cookie):
        return "token"

    async def fake_url(cookie, token, share_id, file_id):
        return "https://example.com/direct.bin"

    monkeypatch.setattr(svc_module, "fetch_access_token", fake_token)
    monkeypatch.setattr(svc_module, "fetch_download_url", fake_url)


def test_readd_restarts_when_resume_unsupported(tmp_path, monkeypatch):
    service = _service(tmp_path)
    task = _task(tmp_path)
    partial = tmp_path / "demo.bin"
    partial.write_bytes(b"partial")
    _patch_direct_url(monkeypatch)

    async def probe(url, headers=None):
        return False, "http 200 without range headers"

    monkeypatch.setattr(svc_module, "probe_resume_support", probe)
    monkeypatch.setattr(service, "_quarantine_download_file", lambda item, reason="bad": str(partial) + ".moved")

    assert asyncio.run(service._readd_task_download(task, consume_attempt=False)) is True
    assert service.aria2.added, "should add a fresh download"
    assert task.progress == 0.0
    assert task.gid == "new-gid"


def test_readd_keeps_gid_when_resume_supported(tmp_path, monkeypatch):
    service = _service(tmp_path)
    task = _task(tmp_path, gid="old-gid")
    (tmp_path / "demo.bin").write_bytes(b"partial")
    _patch_direct_url(monkeypatch)

    async def probe(url, headers=None):
        return True, "http 206"

    monkeypatch.setattr(svc_module, "probe_resume_support", probe)

    assert asyncio.run(service._readd_task_download(task, consume_attempt=False)) is True
    assert service.aria2.replaced == [("old-gid", "https://example.com/direct.bin")]
    assert service.aria2.added == []


def test_readd_skips_probe_without_partial_data(tmp_path, monkeypatch):
    service = _service(tmp_path)
    task = _task(tmp_path, progress=0.0)
    _patch_direct_url(monkeypatch)
    called = []

    async def probe(url, headers=None):
        called.append(url)
        return False, "should not be called"

    monkeypatch.setattr(svc_module, "probe_resume_support", probe)

    assert asyncio.run(service._readd_task_download(task, consume_attempt=False)) is True
    assert called == []
    assert service.aria2.added
