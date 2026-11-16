# -*- coding: utf-8 -*-
"""TianyiService 云存档版本名解析/格式化单元测试。

TianyiService.__init__ 会创建目录、读取状态文件、初始化 aria2 等，测试里用
`TianyiService.__new__(TianyiService)` 绕过构造，只测两个纯函数，避免任何真实副作用。
"""

from __future__ import annotations

import time

import pytest

from tianyi_service import CLOUD_SAVE_DATE_FORMAT, TianyiService


@pytest.fixture()
def service() -> TianyiService:
    """绕过 __init__ 的空壳实例（不创建任何目录/文件）。"""
    instance = TianyiService.__new__(TianyiService)
    assert not hasattr(instance, "store")
    return instance


def _expected_ts(stem: str) -> int:
    return int(time.mktime(time.strptime(stem, CLOUD_SAVE_DATE_FORMAT)))


# ---------------------------------------------------------------------------
# _parse_cloud_save_version_timestamp
# ---------------------------------------------------------------------------


def test_parse_cloud_save_version_timestamp(service: TianyiService) -> None:
    expected = _expected_ts("20260115_123456")
    assert expected > 0
    assert service._parse_cloud_save_version_timestamp("20260115_123456") == expected
    assert service._parse_cloud_save_version_timestamp("20260115_123456.7z") == expected
    assert service._parse_cloud_save_version_timestamp("  20260115_123456.7Z  ") == expected


@pytest.mark.parametrize(
    "version_name",
    [
        "",
        "   ",
        None,
        "abc",
        "20260115_123456 extra",
        "2026-01-15_12-34-56",
        "20260115_12345",
        "20260115_1234567",
        "20260115_123456.7z.bak",
        "20261340_123456",  # 月/日非法，strptime 失败
        "20260115_250000",  # 时/分非法
    ],
)
def test_parse_cloud_save_version_timestamp_invalid(service: TianyiService, version_name) -> None:
    assert service._parse_cloud_save_version_timestamp(version_name) == 0


def test_parse_cloud_save_version_timestamp_returns_int(service: TianyiService) -> None:
    value = service._parse_cloud_save_version_timestamp("20260201_000000")
    assert isinstance(value, int)
    assert value > 0
    # 与预期一致，且和格式化函数可往返
    assert value == _expected_ts("20260201_000000")


# ---------------------------------------------------------------------------
# _format_cloud_save_version_time
# ---------------------------------------------------------------------------


def test_format_cloud_save_version_time(service: TianyiService) -> None:
    ts = 1768490096
    expected = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
    assert service._format_cloud_save_version_time(ts, "fallback") == expected


@pytest.mark.parametrize(
    ("ts", "fallback", "expected"),
    [
        (0, "fallback", "fallback"),
        (-100, "fallback", "fallback"),
        (0, "", ""),
        (None, "fallback", "fallback"),
        ("abc", "fallback", "fallback"),
        (None, None, ""),
    ],
)
def test_format_cloud_save_version_time_fallback(
    service: TianyiService, ts, fallback, expected: str
) -> None:
    assert service._format_cloud_save_version_time(ts, fallback) == expected


def test_format_cloud_save_version_time_accepts_numeric_string(service: TianyiService) -> None:
    ts = 1768490096
    expected = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
    assert service._format_cloud_save_version_time(str(ts), "fallback") == expected


def test_parse_and_format_roundtrip(service: TianyiService) -> None:
    version_name = "20260201_000000.7z"
    ts = service._parse_cloud_save_version_timestamp(version_name)
    assert ts > 0
    # mktime 按本地时区解析，localtime 还原后应与原版本名一致
    assert service._format_cloud_save_version_time(ts, version_name) == "2026-02-01 00:00:00"
