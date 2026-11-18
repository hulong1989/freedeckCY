"""内置目录地址：后端可用，但不在设置字段回显。"""

from config import DEFAULT_CATALOG_CSV_URL


def test_builtin_catalog_url_is_available():
    assert DEFAULT_CATALOG_CSV_URL.startswith("http")
