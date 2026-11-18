"""目录 CSV Ed25519 签名校验。"""

from __future__ import annotations

import base64

import catalog_signature

SEED = base64.b64decode("8z76iFzq39hqP6ziMyW91OWohFDuwJ/NWEY+vg+1zYc=")


def test_signature_roundtrip_and_tamper():
    data = b"game_id,title\n1,Game\n"
    signature = base64.b64encode(catalog_signature.sign(SEED, data)).decode("ascii")
    assert catalog_signature.verify_signature(data, signature)
    assert not catalog_signature.verify_signature(data + b"x", signature)
    assert not catalog_signature.verify_signature(data, "not-base64")
