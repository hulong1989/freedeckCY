# tests/conftest.py - freedeckCY 测试公共环境
#
# 被测代码（py_modules/*.py）在 Decky 运行时里直接 `import decky`、`import config`，
# 因此 pytest 收集用例前必须：
#   1. 把仓库根目录与 py_modules/ 加入 sys.path（插件运行时由 Decky 完成这一步）；
#   2. 往 sys.modules 注入一个假的 decky 模块，避免依赖真实 Decky 运行时。
#
# 这样任何测试文件都可以独立运行：`.venv/bin/python -m pytest tests/test_xxx.py -q`

from __future__ import annotations

import logging
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PY_MODULES_DIR = REPO_ROOT / "py_modules"


def _ensure_sys_path() -> None:
    """保证插件源码可被 `import config` / `import py_modules...` 找到。"""
    for candidate in (str(REPO_ROOT), str(PY_MODULES_DIR)):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)


def _build_fake_decky() -> types.ModuleType:
    """构造离线的假 decky 模块。

    py_modules 里实际用到的属性（见 grep）：
      - decky.logger（tianyi_http / server_manager / main 等打日志）
      - decky.DECKY_PLUGIN_DIR（game_catalog.resolve_default_catalog_path、tianyi_service）
      - decky.DECKY_PLUGIN_SETTINGS_DIR（server_manager）
      - decky.settings（server_manager，getattr 取可选配置）
    其余常量按真实 Decky 运行时的命名补齐，供后续测试或模块使用。
    """
    fake = types.ModuleType("decky")
    fake.logger = logging.getLogger("freedeckcy.test.decky")

    # 路径类常量：指向仓库本身 / 不存在的测试目录，避免触碰用户真实 Steam/Decky 目录。
    fake.DECKY_PLUGIN_DIR = str(REPO_ROOT)
    fake.DECKY_PLUGIN_SETTINGS_DIR = str(REPO_ROOT / ".pytest-decky" / "settings")
    fake.DECKY_PLUGIN_RUNTIME_DIR = str(REPO_ROOT / ".pytest-decky" / "runtime")
    fake.DECKY_PLUGIN_LOG_DIR = str(REPO_ROOT / ".pytest-decky" / "logs")
    fake.DECKY_USER = "deck"
    fake.DECKY_USER_HOME = str(REPO_ROOT / ".pytest-decky" / "home")
    fake.DECKY_HOME = str(REPO_ROOT / ".pytest-decky" / "home")
    fake.DECKY_VERSION = "3.0.0"
    fake.DECKY_API_VERSION = "1.1.3"
    fake.HEAD = "0"

    # server_manager 使用 getattr(decky, "settings", None) 读取可选设置；
    # 这里给一个最小的内存桩，避免测试意外写入真实 Decky 设置。
    class _FakeSettings:
        def __init__(self) -> None:
            self._values: dict = {}

        def get_setting(self, key, default=None):
            return self._values.get(key, default)

        def set_setting(self, key, value):
            self._values[key] = value

    fake.settings = _FakeSettings()
    fake.emit = lambda *args, **kwargs: None
    fake.emit_error = lambda *args, **kwargs: None
    return fake


_ensure_sys_path()
# setdefault：若真实环境已注入 decky（理论上不会），优先复用。
sys.modules.setdefault("decky", _build_fake_decky())


def pytest_configure(config) -> None:
    """兜底：确保 decky 在所有用例导入插件模块前已就位。"""
    _ensure_sys_path()
    sys.modules.setdefault("decky", _build_fake_decky())


@pytest.fixture(scope="session")
def fake_decky() -> types.ModuleType:
    """返回 conftest 注入的假 decky 模块。"""
    return sys.modules["decky"]


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """仓库根目录。"""
    return REPO_ROOT


@pytest.fixture(scope="session")
def py_modules_dir() -> Path:
    """插件源码目录（py_modules/）。"""
    return PY_MODULES_DIR
