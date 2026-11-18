"""更新流程 mixin 的拆分契约。"""

from __future__ import annotations

from tianyi_service import TianyiService
from update_flow import UpdateFlowMixin, _default_update_download_dir, _parse_version


def test_update_flow_mixin_wired_into_service():
    assert issubclass(TianyiService, UpdateFlowMixin)
    for name in ("_check_server_update", "check_update", "download_update"):
        assert hasattr(TianyiService, name)


def test_update_version_parser_handles_suffixes():
    assert _parse_version("v0.26.42") > _parse_version("0.26.41")
    assert _parse_version("1.2.3-beta") == (1, 2, 3)


def test_update_package_uses_internal_downloads_dir():
    path = _default_update_download_dir()
    assert path.endswith("/Downloads") or path.endswith("\\Downloads")
