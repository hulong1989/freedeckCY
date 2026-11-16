"""aria2 运行时元数据/存活判断测试（不启动真实 aria2 进程）。"""

from __future__ import annotations

import os

from aria2_manager import Aria2Manager, Aria2Runtime, _is_pid_alive


def test_runtime_meta_roundtrip(tmp_path):
    manager = Aria2Manager(plugin_dir=str(tmp_path), work_dir=str(tmp_path))
    runtime = Aria2Runtime(
        process=None,
        rpc_url="http://127.0.0.1:6800/jsonrpc",
        rpc_secret="secret",
        binary_path="/usr/bin/aria2c",
        started_at=123,
        pid=os.getpid(),
        owned=True,
    )
    manager._write_runtime_meta(runtime)

    loaded = manager._read_runtime_meta()
    assert loaded is not None
    assert loaded.rpc_url == runtime.rpc_url
    assert loaded.rpc_secret == "secret"
    assert loaded.binary_path == "/usr/bin/aria2c"
    assert loaded.pid == os.getpid()
    # 从元数据读出来的实例不是当前进程拥有的
    assert loaded.owned is False
    assert manager._runtime_looks_alive(loaded) is True


def test_corrupted_meta_is_ignored(tmp_path):
    manager = Aria2Manager(plugin_dir=str(tmp_path), work_dir=str(tmp_path))
    meta_path = tmp_path / "aria2-runtime.json"
    meta_path.write_text("{not json", encoding="utf-8")
    assert manager._read_runtime_meta() is None

    meta_path.write_text('{"rpc_url": ""}', encoding="utf-8")
    assert manager._read_runtime_meta() is None


def test_pid_alive_detection():
    assert _is_pid_alive(os.getpid()) is True
    assert _is_pid_alive(0) is False
    assert _is_pid_alive(-1) is False


def test_stop_without_runtime_is_safe(tmp_path):
    manager = Aria2Manager(plugin_dir=str(tmp_path), work_dir=str(tmp_path))
    manager.stop()  # 不应抛异常


def test_clear_runtime_meta(tmp_path):
    manager = Aria2Manager(plugin_dir=str(tmp_path), work_dir=str(tmp_path))
    runtime = Aria2Runtime(
        process=None,
        rpc_url="http://127.0.0.1:1/jsonrpc",
        rpc_secret="s",
        binary_path="b",
        started_at=1,
        pid=0,
        owned=True,
    )
    manager._write_runtime_meta(runtime)
    assert (tmp_path / "aria2-runtime.json").exists()

    manager._clear_runtime_meta()
    assert not (tmp_path / "aria2-runtime.json").exists()
    manager._clear_runtime_meta()  # 幂等
