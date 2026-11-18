"""内置 CA bundle 的可用性。"""

from pathlib import Path


def test_bundled_ca_file_exists():
    path = Path(__file__).resolve().parents[1] / "py_modules" / "cacert.pem"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert text.count("BEGIN CERTIFICATE") >= 50
