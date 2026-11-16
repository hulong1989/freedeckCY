# -*- coding: utf-8 -*-
"""tianyi_store 数据模型与状态存储单元测试。

全部读写 tmp_path 下的临时 state.json：不触碰用户真实 Decky 目录。
覆盖点：
  - TianyiTaskRecord.from_dict / TianyiInstalledGame.from_dict 的缺省值与类型容错；
  - TianyiStateStore 的 load/save、upsert_tasks、upsert_installed_game（新增/按
    game_id 或 install_path 合并）、remove_installed_game、settings/login 归一化。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tianyi_store import (
    TianyiInstalledGame,
    TianyiStateStore,
    TianyiTaskRecord,
)


def _new_task(**overrides) -> TianyiTaskRecord:
    payload = {
        "task_id": "t1",
        "gid": "g1",
        "game_id": "1001",
        "game_title": "游戏 A",
        "share_code": "sc",
        "share_id": "si",
        "file_id": "fi",
        "file_name": "pkg.7z",
        "download_dir": "/downloads",
        "local_path": "/downloads/pkg.7z",
        "status": "waiting",
        "progress": 0.0,
        "speed": 0,
    }
    payload.update(overrides)
    return TianyiTaskRecord(**payload)


# ---------------------------------------------------------------------------
# TianyiTaskRecord.from_dict
# ---------------------------------------------------------------------------


def test_task_record_from_dict_defaults() -> None:
    record = TianyiTaskRecord.from_dict({})
    assert record.task_id == ""
    assert record.file_name == ""
    assert record.status == "waiting"
    assert record.progress == 0.0
    assert record.speed == 0
    assert record.install_status == "pending"
    assert record.install_message == ""
    assert record.installed_path == ""
    assert record.post_processed is False
    assert record.error_reason == ""
    assert isinstance(record.created_at, int) and record.created_at > 0
    assert isinstance(record.updated_at, int) and record.updated_at > 0


def test_task_record_from_dict_coerces_types() -> None:
    record = TianyiTaskRecord.from_dict(
        {
            "task_id": "t1",
            "game_id": 1001,  # int -> str
            "progress": "12.5",  # str -> float
            "speed": "1024",  # str -> int
            "install_status": None,
            "post_processed": "yes",  # str -> bool
            "openpath": None,
            "created_at": "1700000000",
            "updated_at": "not-a-number",  # 解析失败退化为 now
        }
    )
    assert record.task_id == "t1"
    assert record.game_id == "1001"
    assert record.status == "waiting"  # 缺省值
    assert record.progress == 12.5
    assert record.speed == 1024
    assert record.install_status == "pending"
    assert record.post_processed is True
    assert record.openpath == ""
    assert record.created_at == 1700000000
    assert isinstance(record.updated_at, int) and record.updated_at > 0


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(True, True), (1, True), ("1", True), ("true", True), ("YES", True), ("on", True),
     (False, False), (0, False), ("0", False), ("no", False), ("off", False),
     ("garbage", False), (None, False)],
)
def test_task_record_post_processed_flag(raw, expected: bool) -> None:
    record = TianyiTaskRecord.from_dict({"post_processed": raw})
    assert record.post_processed is expected


# ---------------------------------------------------------------------------
# TianyiInstalledGame.from_dict
# ---------------------------------------------------------------------------


def test_installed_game_from_dict_defaults() -> None:
    record = TianyiInstalledGame.from_dict({})
    assert record.game_id == ""
    assert record.game_title == ""
    assert record.install_path == ""
    assert record.source_path == ""
    assert record.status == "installed"
    assert record.size_bytes == 0
    assert record.steam_app_id == 0
    assert record.playtime_seconds == 0
    assert record.playtime_sessions == 0
    assert isinstance(record.created_at, int) and record.created_at > 0


def test_installed_game_from_dict_clamps_negative_and_coerces() -> None:
    record = TianyiInstalledGame.from_dict(
        {
            "game_id": "g1",
            "game_title": "游戏 B",
            "install_path": "/games/b",
            "status": None,  # 缺省 installed
            "size_bytes": "-5",  # 负数 -> 0
            "steam_app_id": -999,  # 负数 -> 0
            "playtime_seconds": "3600",  # str -> int
            "playtime_sessions": "bad",  # 解析失败 -> 0
            "playtime_last_played_at": None,  # int(None) 失败 -> 0
        }
    )
    assert record.game_id == "g1"
    assert record.status == "installed"
    assert record.size_bytes == 0
    assert record.steam_app_id == 0
    assert record.playtime_seconds == 3600
    assert record.playtime_sessions == 0
    assert record.playtime_last_played_at == 0


# ---------------------------------------------------------------------------
# TianyiStateStore：load / save / 往返
# ---------------------------------------------------------------------------


def _store(tmp_path: Path) -> TianyiStateStore:
    return TianyiStateStore(str(tmp_path / "tianyi" / "state.json"))


def test_state_store_load_without_file_keeps_defaults(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.load()
    assert store.tasks == []
    assert store.installed_games == []
    assert store.login.cookie == ""
    assert store.settings.split_count == 16
    assert store.state_file == str(tmp_path / "tianyi" / "state.json")


def test_state_store_upsert_tasks_roundtrip(tmp_path: Path) -> None:
    store = _store(tmp_path)
    task = _new_task()
    store.upsert_tasks([task])

    state_file = Path(store.state_file)
    assert state_file.is_file()  # save() 自动创建父目录

    reloaded = _store(tmp_path)
    reloaded.load()
    assert len(reloaded.tasks) == 1
    restored = reloaded.tasks[0]
    assert restored.task_id == "t1"
    assert restored.game_title == "游戏 A"
    assert restored.file_name == "pkg.7z"
    assert restored.created_at == task.created_at


def test_state_store_save_creates_parent_directories(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b" / "c" / "state.json"
    store = TianyiStateStore(str(nested))
    store.save()
    assert nested.is_file()


def test_state_store_upsert_installed_game_roundtrip(tmp_path: Path) -> None:
    store = _store(tmp_path)
    game = TianyiInstalledGame(
        game_id="1001",
        game_title="游戏 A",
        install_path="/games/a",
        source_path="/downloads/a.7z",
        size_bytes=1024,
        steam_app_id=123456,
    )
    store.upsert_installed_game(game)
    assert len(store.installed_games) == 1

    reloaded = _store(tmp_path)
    reloaded.load()
    assert len(reloaded.installed_games) == 1
    restored = reloaded.installed_games[0]
    assert restored.game_id == "1001"
    assert restored.game_title == "游戏 A"
    assert restored.install_path == "/games/a"
    assert restored.steam_app_id == 123456
    assert restored.size_bytes == 1024


def test_state_store_upsert_installed_game_merges_by_game_id(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert_installed_game(
        TianyiInstalledGame(
            game_id="1001",
            game_title="游戏 A",
            install_path="/games/a",
            source_path="/downloads/a.7z",
            steam_app_id=123456,
            size_bytes=1024,
        )
    )
    created_at = store.installed_games[0].created_at

    # 同 game_id 再次上报：只更新可变字段，不应新增记录
    store.upsert_installed_game(
        TianyiInstalledGame(
            game_id="1001",
            game_title="",  # 空值保留原值
            install_path="",  # 空值保留原路径
            source_path="",
            status="running",
            steam_app_id=0,  # 0 保留原值
            size_bytes=0,
        )
    )
    assert len(store.installed_games) == 1
    merged = store.installed_games[0]
    assert merged.game_title == "游戏 A"
    assert merged.install_path == "/games/a"
    assert merged.status == "running"
    assert merged.steam_app_id == 123456
    assert merged.created_at == created_at
    assert merged.updated_at >= created_at

    reloaded = _store(tmp_path)
    reloaded.load()
    assert len(reloaded.installed_games) == 1
    assert reloaded.installed_games[0].status == "running"


def test_state_store_upsert_installed_game_merges_by_install_path(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert_installed_game(
        TianyiInstalledGame(
            game_id="1001",
            game_title="游戏 A",
            install_path="/games/a",
            source_path="",
        )
    )
    # game_id 为空但 install_path 相同，也应命中同一条记录
    store.upsert_installed_game(
        TianyiInstalledGame(
            game_id="",
            game_title="游戏 A 改名",
            install_path="/games/a",
            source_path="",
            status="updated",
        )
    )
    assert len(store.installed_games) == 1
    assert store.installed_games[0].game_id == "1001"
    assert store.installed_games[0].game_title == "游戏 A 改名"
    assert store.installed_games[0].status == "updated"


def test_state_store_remove_installed_game(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert_installed_game(
        TianyiInstalledGame(game_id="1001", game_title="A", install_path="/games/a", source_path="")
    )
    store.upsert_installed_game(
        TianyiInstalledGame(game_id="1002", game_title="B", install_path="/games/b", source_path="")
    )
    assert len(store.installed_games) == 2

    removed = store.remove_installed_game(game_id="1001")
    assert removed is not None
    assert removed.game_id == "1001"
    assert len(store.installed_games) == 1

    reloaded = _store(tmp_path)
    reloaded.load()
    assert [game.game_id for game in reloaded.installed_games] == ["1002"]

    # 按安装路径移除
    by_path = store.remove_installed_game(install_path="/games/b")
    assert by_path is not None
    assert by_path.game_id == "1002"
    assert store.installed_games == []

    # 不存在的记录 / 未提供条件 -> None
    assert store.remove_installed_game(game_id="nope") is None
    assert store.remove_installed_game() is None


def test_state_store_cloud_save_results_roundtrip(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.set_cloud_save_last_result({"version": "20260115_123456.7z", "ok": True})
    store.set_cloud_save_restore_last_result({"restored": 2})

    reloaded = _store(tmp_path)
    reloaded.load()
    assert reloaded.cloud_save_last_result == {"version": "20260115_123456.7z", "ok": True}
    assert reloaded.cloud_save_restore_last_result == {"restored": 2}


def test_state_store_load_normalizes_raw_payload(tmp_path: Path) -> None:
    """直接写一份"脏"状态文件，验证加载时的过滤与归一化。"""
    state_file = tmp_path / "tianyi" / "state.json"
    state_file.parent.mkdir(parents=True)
    raw = {
        "login": {"cookie": " c ", "user_account": "u1", "updated_at": "1700000000"},
        "settings": {
            "download_dir": "/dl",
            "split_count": 999,  # clamp 到 64
            "page_size": 5,  # clamp 到 10
            "auto_install": "false",  # str -> False
        },
        "tasks": [
            # 合法
            {"task_id": "t1", "file_name": "pkg.7z", "status": "complete", "progress": 100},
            # 缺 task_id -> 丢弃
            {"file_name": "no-id.7z"},
            # 缺 file_name -> 丢弃
            {"task_id": "t2"},
            "not-a-dict",
        ],
        "installed_games": [
            {"game_id": "g1", "game_title": "A", "install_path": "/games/a"},
            # 缺 install_path -> 丢弃
            {"game_id": "g2", "game_title": "B"},
            # 缺 game_title -> 丢弃
            {"game_id": "g3", "install_path": "/games/c"},
        ],
        "cloud_save_last_result": {"k": "v"},
        "cloud_save_restore_last_result": "not-a-dict",
    }
    state_file.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

    store = TianyiStateStore(str(state_file))
    store.load()
    assert [task.task_id for task in store.tasks] == ["t1"]
    assert store.tasks[0].progress == 100.0
    assert [game.game_id for game in store.installed_games] == ["g1"]
    assert store.settings.split_count == 64
    assert store.settings.page_size == 10
    assert store.settings.auto_install is False
    assert store.login.cookie == " c "
    assert store.login.updated_at == 1700000000
    assert store.cloud_save_last_result == {"k": "v"}
    assert store.cloud_save_restore_last_result == {}


def test_state_store_load_tolerates_non_dict_payload(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    store = TianyiStateStore(str(state_file))
    store.load()
    assert store.tasks == []
    assert store.installed_games == []
    assert store.login.cookie == ""


def test_task_record_roundtrip_keeps_group_and_size(tmp_path: Path) -> None:
    """新增的 file_size / group_id / group_total 必须能持久化并读回。"""
    task = _new_task(
        task_id="grouped",
        file_size=1024,
        group_id="group-1",
        group_total=3,
    )
    store = TianyiStateStore(str(tmp_path / "state" / "state.json"))
    store.upsert_tasks([task])
    store.save()

    reloaded = TianyiStateStore(str(tmp_path / "state" / "state.json"))
    reloaded.load()

    assert len(reloaded.tasks) == 1
    loaded = reloaded.tasks[0]
    assert loaded.file_size == 1024
    assert loaded.group_id == "group-1"
    assert loaded.group_total == 3
