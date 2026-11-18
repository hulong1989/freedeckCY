"""GitHub Issue 表单 -> submission JSON 的解析测试。"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "issue_to_submission", str(ROOT / "scripts" / "issue_to_submission.py")
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_parse_issue_form_fields():
    module = _load_script()
    body = """### 游戏名称（中文）

测试游戏

### 英文名 / 原名

Test Game

### 平台

pc

### 分享链接

https://cloud.189.cn/t/abc123

### 提取码

x1y2

### 网盘内路径

Game/Game.7z

### 分类（可选）

动作冒险,休闲益智

### 备注

_No response_
"""
    data = module.parse_issue_body(body)
    assert data["name"] == "测试游戏"
    assert data["english_name"] == "Test Game"
    assert data["share_url"].endswith("/t/abc123")
    assert data["access_code"] == "x1y2"
    assert data["openpath"] == "Game/Game.7z"
    assert data["notes"] == ""
