# -*- coding: utf-8 -*-
"""steam_shortcuts / vdf 纯函数单元测试。

只测不依赖真实 Steam 目录的逻辑：
  - _generate_non_steam_app_id：确定性、结果落在 signed int32、最高位为 1；
  - _derive_tianyi_launch_token：清洗规则；
  - py_modules/vdf 的文本 loads/dumps roundtrip（转义、嵌套、空目录、重复键）。
"""

from __future__ import annotations

import binascii
import struct

import pytest

import steam_shortcuts
import vdf


# ---------------------------------------------------------------------------
# _generate_non_steam_app_id
# ---------------------------------------------------------------------------


def _unsigned(value: int) -> int:
    """把 signed int32 还原成无符号视图。"""
    return value & 0xFFFFFFFF


def test_generate_non_steam_app_id_is_stable() -> None:
    cases = [
        ("Test Game", "/tmp/test game.exe"),
        ("游戏", "/games/x/game.exe"),
        ("", ""),
    ]
    for app_name, exe_path in cases:
        first = steam_shortcuts._generate_non_steam_app_id(app_name, exe_path)
        second = steam_shortcuts._generate_non_steam_app_id(app_name, exe_path)
        assert first == second


def test_generate_non_steam_app_id_known_vectors() -> None:
    """固定输入 -> 固定结果，防止算法被无意改动（平台无关，crc32 + struct）。"""
    assert steam_shortcuts._generate_non_steam_app_id("Test Game", "/tmp/test game.exe") == -1006784590
    assert steam_shortcuts._generate_non_steam_app_id("游戏", "/games/x/game.exe") == -48988833
    # crc32("") == 0，因此空输入得到 0x80000000（signed 下为 -2147483648）
    assert steam_shortcuts._generate_non_steam_app_id("", "") == -2147483648


@pytest.mark.parametrize(
    ("app_name", "exe_path"),
    [
        ("Test Game", "/tmp/test game.exe"),
        ("游戏", "/games/x/game.exe"),
        ("", ""),
        ("a" * 512, "/very/long/path/" + "b" * 512),
    ],
)
def test_generate_non_steam_app_id_high_bit_set(app_name: str, exe_path: str) -> None:
    value = steam_shortcuts._generate_non_steam_app_id(app_name, exe_path)
    unsigned = _unsigned(value)
    # 非 Steam 快捷方式约定：appid 最高位必须为 1
    assert unsigned >= 0x80000000
    # 结果必须是合法的 signed 32bit（Steam VDF 里以 i32 存）
    assert -(2**31) <= value < 2**31
    assert struct.unpack("i", struct.pack("I", unsigned))[0] == value
    # 与直接 crc32 的实现一致：crc32(exe_path + app_name) 后置最高位
    expected = (binascii.crc32(f"{exe_path}{app_name}".encode("utf-8")) & 0xFFFFFFFF) | 0x80000000
    assert unsigned == expected


def test_generate_non_steam_app_id_differs_for_different_inputs() -> None:
    base = steam_shortcuts._generate_non_steam_app_id("Game", "/tmp/game.exe")
    assert steam_shortcuts._generate_non_steam_app_id("Game 2", "/tmp/game.exe") != base
    assert steam_shortcuts._generate_non_steam_app_id("Game", "/tmp/game2.exe") != base


# ---------------------------------------------------------------------------
# _derive_tianyi_launch_token
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("game_id", "expected"),
    [
        ("game-123", "game-123"),
        ("game/abc 123#x", "game_abc_123_x"),
        ("  __abc__  ", "abc"),
        ("a.b_c-d", "a.b_c-d"),
        ("游戏 1", "1"),
        ("!!!", "game"),
        ("", "game"),
        (None, "game"),
    ],
)
def test_derive_tianyi_launch_token(game_id, expected: str) -> None:
    assert steam_shortcuts._derive_tianyi_launch_token(game_id) == expected


def test_derive_tianyi_launch_token_is_idempotent() -> None:
    token = steam_shortcuts._derive_tianyi_launch_token("game/abc 123")
    assert steam_shortcuts._derive_tianyi_launch_token(token) == token


# ---------------------------------------------------------------------------
# vdf 文本格式 roundtrip
# ---------------------------------------------------------------------------


def test_vdf_text_roundtrip_with_escapes() -> None:
    data = {
        "AppState": {
            "appid": "123",
            "name": 'He said "hi"\nnext\tline\\path',
            "empty": "",
        },
        "shortcuts": {
            "0": {"appname": "游戏 A", "LaunchOptions": "freedeckcy:tianyi:abc"},
        },
        "empty_section": {},
    }
    dumped = vdf.dumps(data)
    assert vdf.loads(dumped) == data
    # 转义后的文本里不应出现未转义换行（换行只属于结构分隔）
    assert 'He said \\"hi\\"\\nnext\\tline\\\\path' in dumped


def test_vdf_dumps_pretty_uses_tabs() -> None:
    dumped = vdf.dumps({"root": {"k": "v"}}, pretty=True)
    assert '\t"k" "v"\n' in dumped
    assert vdf.loads(dumped) == {"root": {"k": "v"}}


def test_vdf_empty_mapping_roundtrip() -> None:
    assert vdf.loads(vdf.dumps({"root": {}})) == {"root": {}}


def test_vdf_duplicate_keys_merge_last_wins() -> None:
    text = '"root"\n{\n "k" "1"\n "k" "2"\n}\n'
    assert vdf.loads(text) == {"root": {"k": "2"}}


def test_vdf_duplicate_sections_merge() -> None:
    text = (
        '"root"\n'
        "{\n"
        ' "a"\n {\n "x" "1"\n }\n'
        ' "a"\n {\n "y" "2"\n }\n'
        "}\n"
    )
    # merge_duplicate_keys=True（默认）时同名子节合并
    assert vdf.loads(text) == {"root": {"a": {"x": "1", "y": "2"}}}


def test_vdf_duplicate_sections_overwrite_when_merge_disabled() -> None:
    text = (
        '"root"\n'
        "{\n"
        ' "a"\n {\n "x" "1"\n }\n'
        ' "a"\n {\n "y" "2"\n }\n'
        "}\n"
    )
    assert vdf.loads(text, merge_duplicate_keys=False) == {"root": {"a": {"y": "2"}}}


def test_vdf_loads_accepts_bom_and_comments() -> None:
    text = "\ufeff// a comment line\n\n" '"root"\n{\n "k" "v"\n}\n'
    assert vdf.loads(text) == {"root": {"k": "v"}}


def test_vdf_dumps_rejects_non_mapping() -> None:
    with pytest.raises(TypeError):
        vdf.dumps([1, 2, 3])  # type: ignore[arg-type]


def test_vdf_loads_rejects_non_str() -> None:
    with pytest.raises(TypeError):
        vdf.loads(b'"root"\n{\n}\n')  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# steam_shortcuts._safe_int
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "default", "expected"),
    [
        ("42", 0, 42),
        ("not-a-number", 0, 0),
        (None, 7, 7),
        ("", 5, 5),
    ],
)
def test_steam_shortcuts_safe_int(raw, default: int, expected: int) -> None:
    assert steam_shortcuts._safe_int(raw, default) == expected
