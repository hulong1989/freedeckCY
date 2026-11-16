"""DroidDeck（Android 上的 SteamOS 运行时）适配测试。"""

from __future__ import annotations

import os

import steam_shortcuts as sc
from tianyi_store import TianyiSettings, TianyiStateStore


def test_detect_proton_tool_defaults_to_valve_proton(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("FREEDECKCY_PROTON_TOOL", raising=False)
    assert sc.is_droiddeck() is False
    assert sc.detect_proton_tool() == "proton_experimental"


def test_detect_proton_tool_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("FREEDECKCY_PROTON_TOOL", "none")
    assert sc.detect_proton_tool() == "none"


def test_droiddeck_detection_and_arm_tool(monkeypatch, tmp_path):
    home = tmp_path / "home"
    (home / ".droiddeck-x64").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("FREEDECKCY_PROTON_TOOL", raising=False)
    monkeypatch.delenv("DROIDDECK_ROOT", raising=False)

    assert sc.is_droiddeck() is True
    assert sc.detect_proton_tool() == "droiddeck-proton-arm64"


def test_droiddeck_prefers_proton_11_when_config_mentions_it(monkeypatch, tmp_path):
    home = tmp_path / "home"
    steam_root = home / ".local" / "share" / "Steam"
    (steam_root / "config").mkdir(parents=True)
    (steam_root / "package").mkdir(parents=True)
    (steam_root / "package" / "droiddeck-installed").write_text("x", encoding="utf-8")
    (steam_root / "config" / "config.vdf").write_text(
        '"CompatToolMapping"\n{\n\t"0"\n\t{\n\t\t"name"\t\t"droiddeck-proton-11-arm64"\n\t}\n}\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("FREEDECKCY_PROTON_TOOL", raising=False)

    assert sc.is_droiddeck(str(steam_root)) is True
    assert sc.detect_proton_tool(str(steam_root)) == "droiddeck-proton-11-arm64"


def test_droiddeck_x64_steam_root_is_preferred_when_running(monkeypatch, tmp_path):
    home = tmp_path / "home"
    x64_root = home / ".droiddeck-x64" / ".local" / "share" / "Steam"
    (x64_root / "steamapps").mkdir(parents=True)
    (x64_root / "steam.pid").write_text("123\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("FREEDECKCY_STEAM_ROOT", raising=False)

    candidates = sc._steam_root_candidates()
    assert candidates[0] == str(x64_root)
    assert sc._find_steam_root() == os.path.realpath(str(x64_root))


def test_droiddeck_x64_candidate_is_last_when_not_running(monkeypatch, tmp_path):
    home = tmp_path / "home"
    x64_root = home / ".droiddeck-x64" / ".local" / "share" / "Steam"
    (x64_root / "steamapps").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("FREEDECKCY_STEAM_ROOT", raising=False)

    candidates = sc._steam_root_candidates()
    assert candidates[-1] == str(x64_root)


def test_settings_proton_tool_roundtrip(tmp_path):
    state_file = tmp_path / "state.json"
    store = TianyiStateStore(str(state_file))
    assert store.settings.proton_tool == "auto"

    store.set_settings(proton_tool="droiddeck-proton-arm64")
    reloaded = TianyiStateStore(str(state_file))
    reloaded.load()
    assert reloaded.settings.proton_tool == "droiddeck-proton-arm64"


def test_settings_unknown_proton_tool_falls_back_to_auto(tmp_path):
    state_file = tmp_path / "state.json"
    state_file.write_text(
        '{"settings": {"download_dir": "", "proton_tool": ""}}',
        encoding="utf-8",
    )
    store = TianyiStateStore(str(state_file))
    store.load()
    assert store.settings.proton_tool == "auto"


def test_settings_dataclass_default_is_auto():
    assert TianyiSettings().proton_tool == "auto"
