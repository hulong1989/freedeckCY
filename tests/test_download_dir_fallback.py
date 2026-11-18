"""不可写下载目录的回退。"""

from types import SimpleNamespace

import config
import server_manager


def test_ensure_download_dir_falls_back(tmp_path, monkeypatch):
    bad = tmp_path / "not-a-dir"
    bad.write_text("x", encoding="utf-8")
    good = tmp_path / "Downloads"
    monkeypatch.setattr(config, "DOWNLOADS_DIR", str(good))
    plugin = SimpleNamespace(downloads_dir=str(bad))
    result = server_manager.ensure_download_dir(plugin)
    assert result == str(good.resolve())
    assert plugin.downloads_dir == str(good.resolve())
    assert good.is_dir()
