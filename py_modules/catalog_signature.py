"""Minimal Ed25519 sign/verify (RFC 8032), stdlib only."""
import hashlib

q = 2**255 - 19
l = 2**252 + 27742317777372353535851937790883648493
d = (-121665 * pow(121666, q - 2, q)) % q
I = pow(2, (q - 1) // 4, q)

def H(m: bytes) -> bytes:
    return hashlib.sha512(m).digest()

def _bit(h: bytes, i: int) -> int:
    return (h[i // 8] >> (i % 8)) & 1

def _xrecover(y: int) -> int:
    xx = ((y * y - 1) * pow(d * y * y + 1, q - 2, q)) % q
    x = pow(xx, (q + 3) // 8, q)
    if (x * x - xx) % q != 0:
        x = (x * I) % q
    if x % 2 != 0:
        x = q - x
    return x

By = (4 * pow(5, q - 2, q)) % q
Bx = _xrecover(By)
B = [Bx % q, By % q, 1, (Bx * By) % q]

def _edwards(P, Q):
    x1, y1, z1, t1 = P
    x2, y2, z2, t2 = Q
    a = ((y1 - x1) * (y2 - x2)) % q
    b = ((y1 + x1) * (y2 + x2)) % q
    c = (t1 * 2 * d * t2) % q
    dd = (z1 * 2 * z2) % q
    e = b - a
    f = dd - c
    g = dd + c
    h = b + a
    return [e * f % q, g * h % q, f * g % q, e * h % q]

def _scalarmult(P, e):
    if e == 0:
        return [0, 1, 1, 0]
    Q = _scalarmult(P, e // 2)
    Q = _edwards(Q, Q)
    if e & 1:
        Q = _edwards(Q, P)
    return Q

def _encodepoint(P):
    x, y, z, t = P
    zi = pow(z, q - 2, q)
    x = (x * zi) % q
    y = (y * zi) % q
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")

def _decodepoint(s: bytes):
    if len(s) != 32:
        raise ValueError("bad point")
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    if y >= q:
        raise ValueError("bad y")
    x = _xrecover(y)
    if (x & 1) != sign:
        x = q - x
    P = [x, y, 1, (x * y) % q]
    if not _isequal(_edwards(P, [0, 1, 1, 0]), P):
        raise ValueError("bad point")
    return P

def _isequal(P, Q):
    x1, y1, z1, _ = P
    x2, y2, z2, _ = Q
    return (x1 * z2 - x2 * z1) % q == 0 and (y1 * z2 - y2 * z1) % q == 0

def public_key(seed: bytes) -> bytes:
    h = H(seed)
    a = 2**254 + sum(2**i * _bit(h, i) for i in range(3, 254))
    return _encodepoint(_scalarmult(B, a))

def sign(seed: bytes, message: bytes) -> bytes:
    h = H(seed)
    a = 2**254 + sum(2**i * _bit(h, i) for i in range(3, 254))
    A = _encodepoint(_scalarmult(B, a))
    r = int.from_bytes(H(h[32:] + message), "little") % l
    R = _encodepoint(_scalarmult(B, r))
    S = (r + int.from_bytes(H(R + A + message), "little") * a) % l
    return R + int.to_bytes(S, 32, "little")

def verify(public: bytes, message: bytes, signature: bytes) -> bool:
    if len(public) != 32 or len(signature) != 64:
        return False
    try:
        A = _decodepoint(public)
        R = _decodepoint(signature[:32])
    except Exception:
        return False
    S = int.from_bytes(signature[32:], "little")
    if S >= l:
        return False
    h = int.from_bytes(H(signature[:32] + public + message), "little") % l
    return _isequal(_scalarmult(B, S), _edwards(R, _scalarmult(A, h)))

# ── freedeckCY 内置公钥 ─────────────────────────────────────────────────────
import base64

PUBLIC_KEY_B64 = "6jWTcEYZG75wQeTIpIj5EAbWwZdaPRPAqSM/l+N/yMM="


def verify_signature(data: bytes, signature_b64: str) -> bool:
    try:
        signature = base64.b64decode(str(signature_b64 or "").strip(), validate=True)
        public = base64.b64decode(PUBLIC_KEY_B64)
        return verify(public, data, signature)
    except Exception:
        return False
