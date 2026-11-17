"""插件入口 import 冒烟：防止 runtime_user 等模块漏打包/漏提交。"""

from __future__ import annotations


def test_main_module_imports_with_fake_decky():
    import main

    assert hasattr(main, "Plugin")
    assert callable(getattr(main.Plugin, "restart_steam", None))
    assert callable(getattr(main.Plugin, "clear_steam_restart_pending", None))


def test_runtime_user_resolves_non_root_candidate():
    from runtime_user import resolve_runtime_user

    user = resolve_runtime_user()
    assert user.get("name")
    assert int(user.get("uid", 0)) >= 0
    assert user.get("home")
