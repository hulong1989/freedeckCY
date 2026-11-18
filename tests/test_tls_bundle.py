"""内置 CA bundle 的可用性。"""

from pathlib import Path


def test_bundled_ca_file_exists():
    path = Path(__file__).resolve().parents[1] / "py_modules" / "cacert.pem"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert text.count("BEGIN CERTIFICATE") >= 50


def test_bundled_ca_takes_precedence(monkeypatch, tmp_path):
    from tianyi_client import _build_tls_context

    bad = tmp_path / "bad-ca.pem"
    bad.write_text("", encoding="utf-8")
    monkeypatch.setenv("SSL_CERT_FILE", str(bad))
    context = _build_tls_context()
    assert len(context.get_ca_certs()) >= 50
