# -*- coding: utf-8 -*-
"""utils 单元测试：端口探测 / 异步等待端口释放 / IP 获取失败回退。

端口测试全程只监听 127.0.0.1 的临时端口（bind port 0），不依赖外网；
IP 相关测试通过 monkeypatch 打桩，避免探测真实网卡或联网。
"""

from __future__ import annotations

import asyncio
import socket
import threading
import time
import types

import pytest

import utils


def _listening_socket(drain: bool = True) -> socket.socket:
    """在 127.0.0.1 上开一个临时监听端口。

    注意：必须用足够大的 backlog 并在后台 accept/close。
    `is_port_in_use` 会反复 connect 探测，若监听端不 accept，
    完成握手的连接会占满队列，导致后续 connect 超时、探测结果抖动。

    `drain` 线程用 accept 超时轮询，close 后能在 ~50ms 内退出并释放 fd
    （Linux 上阻塞 accept 不会因为另一个线程 close 立刻返回）。
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 0))
        sock.listen(128)
    except Exception:
        sock.close()
        raise

    if not drain:
        return sock

    sock.settimeout(0.05)

    def _drain(listener: socket.socket) -> None:
        while True:
            try:
                conn, _ = listener.accept()
            except socket.timeout:
                if listener.fileno() < 0:
                    return
                continue
            except OSError:
                return
            try:
                conn.close()
            except OSError:
                pass

    threading.Thread(target=_drain, args=(sock,), daemon=True).start()
    return sock


def _free_port() -> int:
    """拿一个当前没有进程监听的端口号（只 bind 不 listen，避免后台线程持有 fd）。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
    finally:
        sock.close()


# ---------------------------------------------------------------------------
# is_port_in_use
# ---------------------------------------------------------------------------


def test_is_port_in_use_detects_listener() -> None:
    sock = _listening_socket()
    try:
        port = sock.getsockname()[1]
        assert utils.is_port_in_use(port, timeout=0.5, retries=1) is True
    finally:
        sock.close()


def test_is_port_in_use_returns_false_after_release() -> None:
    port = _free_port()
    assert utils.is_port_in_use(port, timeout=0.3, retries=1) is False


def test_is_port_in_use_handles_multiple_retries() -> None:
    """端口释放后多次重试也应该是 False。"""
    port = _free_port()
    assert utils.is_port_in_use(port, timeout=0.1, retries=3) is False


# ---------------------------------------------------------------------------
# wait_for_port_release（pytest-asyncio）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wait_for_port_release_returns_true_when_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # wait_for_port_release 内部用 is_port_in_use 的默认重试次数；测试里压成 1 次以加快速度
    monkeypatch.setattr(utils.config, "PORT_CHECK_RETRIES", 1)
    port = _free_port()
    started = time.monotonic()
    assert await utils.wait_for_port_release(port, timeout=2.0) is True
    assert time.monotonic() - started < 1.5


@pytest.mark.asyncio
async def test_wait_for_port_release_returns_false_on_timeout() -> None:
    sock = _listening_socket()
    try:
        port = sock.getsockname()[1]
        started = time.monotonic()
        assert await utils.wait_for_port_release(port, timeout=0.5) is False
        assert time.monotonic() - started >= 0.4
    finally:
        sock.close()


@pytest.mark.asyncio
async def test_wait_for_port_release_succeeds_after_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(utils.config, "PORT_CHECK_RETRIES", 1)
    sock = _listening_socket()
    port = sock.getsockname()[1]
    sock.close()
    assert await asyncio.wait_for(utils.wait_for_port_release(port, timeout=2.0), timeout=3.0) is True


# ---------------------------------------------------------------------------
# _is_vpn_interface
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["tun0", "tap1", "wg0", "ppp0", "utun3", "tailscale0", "docker0", "br-abc", "virbr0", "lo"],
)
def test_is_vpn_interface_positive(name: str) -> None:
    assert utils._is_vpn_interface(name) is True


@pytest.mark.parametrize("name", ["wlan0", "eth0", "enp3s0", "wlp2s0", "en0"])
def test_is_vpn_interface_negative(name: str) -> None:
    assert utils._is_vpn_interface(name) is False


# ---------------------------------------------------------------------------
# get_ip_address（打桩，不联网）
# ---------------------------------------------------------------------------


def test_get_ip_address_uses_ip_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(utils, "_get_ip_from_ip_cmd", lambda: "192.168.1.50")
    monkeypatch.setattr(utils, "_cached_ip_address", None)
    monkeypatch.setattr(utils, "_cached_ip_timestamp", 0.0)

    assert utils.get_ip_address(force_refresh=True) == "192.168.1.50"
    assert utils._cached_ip_address == "192.168.1.50"


def test_get_ip_address_caches_result(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def fake_ip_cmd() -> str:
        calls.append(1)
        return "10.0.0.8"

    monkeypatch.setattr(utils, "_get_ip_from_ip_cmd", fake_ip_cmd)
    monkeypatch.setattr(utils, "_cached_ip_address", None)
    monkeypatch.setattr(utils, "_cached_ip_timestamp", 0.0)

    assert utils.get_ip_address(force_refresh=True) == "10.0.0.8"
    assert utils.get_ip_address() == "10.0.0.8"
    assert len(calls) == 1  # 第二次走缓存，不再探测


def test_get_ip_address_falls_back_to_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(utils, "_get_ip_from_ip_cmd", lambda: None)
    monkeypatch.setattr(utils, "_cached_ip_address", None)
    monkeypatch.setattr(utils, "_cached_ip_timestamp", 0.0)

    class _RaisingSocket:
        def __call__(self, *args, **kwargs):
            raise OSError("network unavailable")

    fake_socket_module = types.SimpleNamespace(
        socket=_RaisingSocket(),
        AF_INET=socket.AF_INET,
        SOCK_DGRAM=socket.SOCK_DGRAM,
    )
    monkeypatch.setattr(utils, "socket", fake_socket_module)

    assert utils.get_ip_address(force_refresh=True) == "127.0.0.1"


def test_get_ip_address_returns_cached_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(utils, "_get_ip_from_ip_cmd", lambda: None)
    monkeypatch.setattr(utils, "_cached_ip_address", "10.1.2.3")
    monkeypatch.setattr(utils, "_cached_ip_timestamp", 0.0)

    class _RaisingSocket:
        def __call__(self, *args, **kwargs):
            raise OSError("network unavailable")

    monkeypatch.setattr(
        utils,
        "socket",
        types.SimpleNamespace(
            socket=_RaisingSocket(),
            AF_INET=socket.AF_INET,
            SOCK_DGRAM=socket.SOCK_DGRAM,
        ),
    )

    # 全部探测失败时回退到上一次缓存值
    assert utils.get_ip_address(force_refresh=True) == "10.1.2.3"
