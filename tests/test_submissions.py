"""仓库游戏提交：校验与合并。"""

from __future__ import annotations

import csv
import json

import submission


def _write_catalog(tmp_path, rows=()):
    path = tmp_path / "catalog.csv"
    fields = list(submission.CATALOG_FIELDS)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    return path


def _submission(**overrides):
    data = {
        "name": "测试游戏",
        "english_name": "Test Game",
        "platform": "pc",
        "share_url": "https://cloud.189.cn/t/AbCdEf123456",
        "access_code": "x9k2",
        "openpath": "Test Game/TestGame.exe",
        "categories": "动作冒险",
        "executable_name": "TestGame.exe",
    }
    data.update(overrides)
    return data


def test_validate_submission_accepts_valid(tmp_path):
    catalog = _write_catalog(tmp_path)
    data = _submission()
    normalized, errors, warnings = submission.validate_submission(
        data,
        catalog_share_codes=submission.catalog_share_codes(submission.load_catalog(catalog)),
    )
    assert errors == []
    assert warnings == []
    assert normalized["platform"] == "pc"
    assert normalized["categories"] == "动作冒险"


def test_validate_submission_rejects_bad_platform_and_url(tmp_path):
    catalog = _write_catalog(tmp_path)
    _normalized, errors, _warnings = submission.validate_submission(
        _submission(platform="wiiu", share_url="https://example.com/share"),
        catalog_share_codes=set(),
    )
    assert any("platform" in error for error in errors)
    assert any("share_url" in error for error in errors)


def test_validate_submission_rejects_duplicate_share_code(tmp_path):
    catalog = _write_catalog(
        tmp_path,
        [
            {
                "game_id": "1",
                "down_url": "https://cloud.189.cn/t/AbCdEf123456?pwd=x9k2",
                "shorturl": "AbCdEf123456",
            }
        ],
    )
    rows = submission.load_catalog(catalog)
    _normalized, errors, _warnings = submission.validate_submission(
        _submission(),
        catalog_share_codes=submission.catalog_share_codes(rows),
    )
    assert any("已存在" in error for error in errors)


def test_validate_submission_platform_aliases():
    assert submission.normalize_platform("windows") == "pc"
    assert submission.normalize_platform("ns") == "switch"
    assert submission.normalize_platform("3d") == "3ds"
    assert submission.normalize_platform("psx") == "ps1"
    assert submission.normalize_platform("switch") == "switch"
    assert submission.normalize_platform("arcade") == ""


def test_merge_submissions_dry_run_and_apply(tmp_path):
    catalog = _write_catalog(
        tmp_path,
        [{"game_id": "7", "title": "Old", "down_url": "https://cloud.189.cn/t/OldCode"}],
    )
    submissions = tmp_path / "submissions"
    submissions.mkdir()
    (submissions / "test-game.json").write_text(json.dumps(_submission(), ensure_ascii=False), encoding="utf-8")

    dry = submission.merge_submissions(submissions, catalog, apply=False)
    assert dry["ok"] is True and dry["applied"] is False
    assert dry["rows"][0]["row"]["game_id"] == "8"
    assert (submissions / "test-game.json").is_file()

    applied = submission.merge_submissions(submissions, catalog, apply=True)
    assert applied["ok"] is True and applied["applied"] is True
    assert not (submissions / "test-game.json").exists()
    assert (submissions / "merged" / "test-game.json").is_file()

    rows = submission.load_catalog(catalog)
    assert rows[-1]["game_id"] == "8"
    assert rows[-1]["title"] == "测试游戏/Test Game"
    assert rows[-1]["platform"] == "pc"
    assert rows[-1]["pwd"] == "x9k2"
    assert rows[-1]["shorturl"] == "AbCdEf123456"
    assert rows[-1]["down_url"].endswith("pwd=x9k2")


def test_merge_submissions_stops_on_errors(tmp_path):
    catalog = _write_catalog(tmp_path)
    submissions = tmp_path / "submissions"
    submissions.mkdir()
    (submissions / "bad.json").write_text(json.dumps(_submission(platform="nope")), encoding="utf-8")
    result = submission.merge_submissions(submissions, catalog, apply=True)
    assert result["ok"] is False
    assert (submissions / "bad.json").is_file()
    assert len(submission.load_catalog(catalog)) == 0


def test_validate_baidu_submission_and_server(tmp_path):
    catalog = _write_catalog(tmp_path)
    data = _submission(
        name="百度测试",
        english_name="Baidu Test",
        share_url="https://pan.baidu.com/s/1AbCdEf123456",
        access_code="x9k2",
    )
    normalized, errors, _warnings = submission.validate_submission(data, catalog_share_codes=set())
    assert errors == []
    assert submission._share_provider(normalized["share_url"]) == "baidu"
    row = submission.build_catalog_row(normalized, "9")
    assert row["server"] == "b"
    assert row["shorturl"] == "1AbCdEf123456"
    assert row["pwd"] == "x9k2"


def test_baidu_share_code_canonicalizes_surl_and_short_path(tmp_path):
    catalog = _write_catalog(
        tmp_path,
        [
            {
                "game_id": "1",
                "down_url": "https://pan.baidu.com/s/1AbCdEf123456?pwd=x9k2",
                "shorturl": "1AbCdEf123456",
            }
        ],
    )
    rows = submission.load_catalog(catalog)
    data = _submission(
        name="百度重复",
        english_name="Baidu Dup",
        share_url="https://pan.baidu.com/share/init?surl=AbCdEf123456",
        access_code="x9k2",
    )
    _normalized, errors, _warnings = submission.validate_submission(
        data,
        catalog_share_codes=submission.catalog_share_codes(rows),
    )
    assert any("已存在" in error for error in errors)


def test_validate_submission_rejects_formula_injection_in_openpath():
    # openpath 会原样写进目录 CSV，必须与 name/categories 一样做公式注入校验。
    for bad_path in ("=HYPERLINK(\"http://evil\")", "+cmd", "-1+1", "@SUM(A1)"):
        _normalized, errors, _warnings = submission.validate_submission(
            _submission(openpath=bad_path),
            catalog_share_codes=set(),
        )
        assert any("公式注入" in error for error in errors), bad_path


def test_validate_submission_rejects_control_chars_and_absolute_openpath():
    _normalized, errors, _warnings = submission.validate_submission(
        _submission(openpath="Game/Game.7z\n=cmd"),
        catalog_share_codes=set(),
    )
    assert any("控制字符" in error for error in errors)

    for absolute in ("/Game/Game.7z", "C:/Games/Game.7z", "\\\\server\\share\\x.7z"):
        _normalized, errors, _warnings = submission.validate_submission(
            _submission(openpath=absolute),
            catalog_share_codes=set(),
        )
        assert any("绝对路径" in error for error in errors), absolute


def test_validate_submission_rejects_malformed_share_code():
    for share_url in (
        "https://cloud.189.cn/t/=cmd",
        "https://cloud.189.cn/t/abc%20def",
        "https://pan.baidu.com/s/1<script>",
    ):
        _normalized, errors, _warnings = submission.validate_submission(
            _submission(share_url=share_url, access_code=""),
            catalog_share_codes=set(),
        )
        assert any("share_url 无效" in error for error in errors), share_url


def test_validate_submission_accepts_explicit_port_and_subdomain():
    _normalized, errors, _warnings = submission.validate_submission(
        _submission(share_url="https://cloud.189.cn:443/t/AbCdEf123456"),
        catalog_share_codes=set(),
    )
    assert errors == []

    normalized, errors, _warnings = submission.validate_submission(
        _submission(share_url="https://h5.cloud.189.cn/t/AbCdEf123456"),
        catalog_share_codes=set(),
    )
    assert errors == []
    assert submission._share_provider(normalized["share_url"]) == "tianyi"


def test_access_code_overrides_stale_pwd_in_share_url():
    normalized, errors, _warnings = submission.validate_submission(
        _submission(share_url="https://cloud.189.cn/t/AbCdEf123456?pwd=old0", access_code="new1"),
        catalog_share_codes=set(),
    )
    assert errors == []
    row = submission.build_catalog_row(normalized, "11")
    assert "pwd=new1" in row["down_url"]
    assert "old0" not in row["down_url"]
    assert row["pwd"] == "new1"


def test_build_catalog_row_escapes_formula_cells_for_all_text_columns():
    data = {
        "name": "=游戏",
        "platform": "pc",
        "share_url": "https://cloud.189.cn/t/AbCdEf123456",
        "access_code": "x9k2",
        "openpath": "=cmd|' /C calc'!A0",
        "category_parent": "-5",
        "list_filesize": "+SUM(A1)",
    }
    row = submission.build_catalog_row(data, "12")
    for field in ("openpath", "category_parent", "list_filesize", "title"):
        assert row[field].startswith("'"), field
    assert row["categories"] == "未分类"
    assert row["game_id"] == "12"
    assert row["down_url"].startswith("https://")


def test_catalog_share_codes_ignores_malformed_shorturl():
    rows = [
        {"down_url": "", "shorturl": "=cmd"},
        {"down_url": "", "shorturl": "AbCdEf123456"},
    ]
    assert submission.catalog_share_codes(rows) == {"AbCdEf123456"}
