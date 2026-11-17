"""百度 Passport 网页扫码登录（BDUSS/Cookie）。"""

from __future__ import annotations

import asyncio
import html
import http.cookiejar
import json
import re
import ssl
import time
import urllib.request
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import aiohttp

QRCODE_URL = "https://passport.baidu.com/v2/api/getqrcode"
UNICAST_URL = "https://passport.baidu.com/channel/unicast"
QR_LOGIN_URL = "https://passport.baidu.com/v3/login/main/qrbdusslogin"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://passport.baidu.com/",
}

# 上游错误正文可能回显 sign/cookie/token 等登录凭证，进入面板/日志前统一脱敏。
_SENSITIVE_TEXT_RE = re.compile(
    r"(?i)\b(bduss|stoken|ptoken|bdstoken|access_token|refresh_token|client_secret|secret_key|"
    r"session_key|session_secret|cookie|sign|pwd|randsk|sekey)\b(\s*[=:]\s*)([^\s&;，,]+)"
)
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class BaiduQrError(RuntimeError):
    pass


def _safe_detail(value: Any, limit: int = 200) -> str:
    """把上游响应/异常压成单行并遮蔽凭证类键值，避免错误信息泄露。"""
    text = _CONTROL_CHARS_RE.sub(" ", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    text = _SENSITIVE_TEXT_RE.sub(lambda match: f"{match.group(1)}{match.group(2)}<redacted>", text)
    return text[: max(1, int(limit))]


def _timeout(total: float = 12.0) -> aiohttp.ClientTimeout:
    return aiohttp.ClientTimeout(total=total, connect=8, sock_connect=8, sock_read=total)


def _ssl_context():
    try:
        return ssl.create_default_context()
    except Exception:
        # None 表示使用 aiohttp/urllib 默认上下文，而不是静默关闭校验。
        return None


def _parse_jsonish(text: str) -> Dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        pass
    match = re.search(r"\{.*\}", raw, re.S)
    if match:
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else {}
        except Exception:
            pass
    return {}


def _build_urllib_opener(context: Optional[ssl.SSLContext], jar: http.cookiejar.CookieJar):
    handlers = [urllib.request.HTTPCookieProcessor(jar)]
    if context is not None:
        handlers.append(urllib.request.HTTPSHandler(context=context))
    return urllib.request.build_opener(*handlers)


def _urllib_fetch(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    *,
    timeout: float = 15.0,
    insecure: bool = False,
) -> Tuple[str, Dict[str, str]]:
    """urllib 回退：返回 (响应文本, Set-Cookie 收集到的 cookie)。

    显式使用 CookieJar 是为了在 aiohttp TLS 不可用、只能走 urllib 的环境里
    仍能复用 getqrcode 下发的 BAIDUID，保证后续 unicast/qrbdusslogin 同会话。
    """
    request_url = str(url or "").strip()
    if params:
        query = urlencode({str(key): str(value) for key, value in params.items()})
        joiner = "&" if "?" in request_url else "?"
        request_url = f"{request_url}{joiner}{query}"
    jar = http.cookiejar.CookieJar()
    context = ssl._create_unverified_context() if insecure else _ssl_context()
    opener = _build_urllib_opener(context, jar)
    request = urllib.request.Request(request_url, headers=HEADERS)
    with opener.open(request, timeout=timeout) as response:
        text = response.read().decode("utf-8", "replace")
    cookies = {cookie.name: cookie.value for cookie in jar}
    return text, cookies


def _urllib_get_text(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    *,
    timeout: float = 15.0,
) -> Tuple[str, Dict[str, str]]:
    """先按系统 CA 校验；仅证书链失败时降级为不校验证书再试一次。"""
    try:
        return _urllib_fetch(url, params, timeout=timeout)
    except Exception as exc:
        if not _is_cert_failure(exc):
            raise
        return _urllib_fetch(url, params, timeout=timeout, insecure=True)


def _is_cert_failure(exc: BaseException) -> bool:
    text = str(exc).lower()
    return (
        isinstance(exc, ssl.SSLCertVerificationError)
        or "certificate verify failed" in text
        or "certificate_verify_failed" in text
        or "unable to get local issuer" in text
    )


async def request_qr() -> Dict[str, Any]:
    params = {"lp": "pc", "qrloginfrom": "pc"}
    text = ""
    last_error = ""
    cookies: Dict[str, str] = {}
    attempts = [True]
    for verify in attempts:
        try:
            jar = aiohttp.CookieJar(unsafe=True)
            connector = aiohttp.TCPConnector(ssl=_ssl_context() if verify else False)
            async with aiohttp.ClientSession(timeout=_timeout(10), cookie_jar=jar, connector=connector) as session:
                async with session.get(QRCODE_URL, params=params, headers=HEADERS) as response:
                    text = await response.text()
                    if response.status == 200 and text.strip():
                        cookies = {cookie.key: cookie.value for cookie in jar}
                        break
                    last_error = f"HTTP {response.status}: {_safe_detail(text, 200)}"
                    # 清空正文以触发 urllib 回退（不同 TLS 栈/代理下可能可用）。
                    text = ""
                    break
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {_safe_detail(exc, 200)}"
            # 只在证书链失败时降级；HTTP/连接错误绝不跳过校验。
            if verify and _is_cert_failure(exc):
                attempts.append(False)
                continue
            break
    if not text.strip():
        try:
            text, cookies = await asyncio.to_thread(_urllib_get_text, QRCODE_URL, params)
        except Exception as exc:
            detail = last_error or f"{type(exc).__name__}: {_safe_detail(exc, 200)}"
            raise BaiduQrError(f"获取百度二维码失败（{_safe_detail(detail, 260)}）") from exc
    data = _parse_jsonish(text)
    if not data:
        raise BaiduQrError(f"百度二维码响应异常: {_safe_detail(text, 300)}")
    if int(data.get("errno", 0) or 0) != 0:
        raise BaiduQrError(_safe_detail(data.get("prompt") or f"百度二维码 errno={data.get('errno')}", 300))
    sign = str(data.get("sign", "") or "").strip()
    imgurl = str(data.get("imgurl", "") or "").strip()
    if not sign:
        raise BaiduQrError("百度二维码缺少 sign")
    if imgurl and not imgurl.startswith(("http://", "https://")):
        imgurl = "https://" + imgurl.lstrip("/")
    return {
        "sign": sign,
        "imgurl": imgurl,
        "prompt": str(data.get("prompt", "") or ""),
        "cookies": cookies,
    }


async def fetch_qr_image(imgurl: str) -> bytes:
    url = str(imgurl or "").strip()
    if not url:
        return b""
    try:
        connector = aiohttp.TCPConnector(ssl=_ssl_context())
        async with aiohttp.ClientSession(timeout=_timeout(12), connector=connector) as session:
            async with session.get(url, headers=HEADERS) as response:
                if response.status != 200:
                    return b""
                return await response.read()
    except Exception as exc:
        if not _is_cert_failure(exc):
            return b""
        try:
            request = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=12, context=ssl._create_unverified_context()) as response:
                return response.read()
        except Exception:
            return b""


def parse_qr_poll_payload(text: str) -> Dict[str, Any]:
    """解析 unicast 轮询响应（独立出来便于单测）。

    百度约定：errno=1 未扫码；errno=0 + channel_v(status/v) 表示已扫/已确认；
    其余 errno 只有明确提示"失效/过期"才判 expired，其余按 error 处理，
    避免把风控/临时错误误判成二维码过期而丢掉会话。
    """
    raw = str(text or "").strip()
    if not raw:
        return {"status": "error", "error": "轮询响应为空"}
    data = _parse_jsonish(raw)
    if not data:
        return {"status": "error", "error": f"响应不是 JSON: {_safe_detail(raw, 120)}"}
    try:
        errno = int(data.get("errno", 0) or 0)
    except Exception:
        errno = -1
    prompt = _safe_detail(data.get("prompt", ""), 200)
    if errno == 1:
        return {"status": "waiting"}
    if errno != 0:
        expired_markers = ("失效", "过期", "超时", "expired", "timeout")
        prompt_lower = prompt.lower()
        if errno == 2 or any(marker in prompt_lower for marker in expired_markers):
            return {"status": "expired", "error": prompt or f"errno={errno}"}
        return {"status": "error", "error": prompt or f"百度轮询 errno={errno}"}
    channel_v = data.get("channel_v")
    try:
        payload = json.loads(channel_v) if isinstance(channel_v, str) else (channel_v or {})
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    value = str(payload.get("v", "") or "").strip()
    if value:
        return {"status": "confirmed", "v": value}
    if int(payload.get("status", -1) or 0) == 1:
        return {"status": "scanned"}
    return {"status": "waiting"}


async def poll_qr(
    sign: str,
    *,
    timeout: float = 8.0,
    cookies: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """单次轮询；百度长轮询超时/空 body 视为仍在等待。

    - 读超时（长轮询没消息）→ waiting；
    - TCP 连接超时 → error（网络不可达，不能一直显示"等待扫码"）；
    - aiohttp 整体不可用时回退 urllib，并复用 getqrcode 的 cookie。
    """
    params = {"channel_id": str(sign or "").strip(), "tpl": "pp", "tt": str(int(time.time() * 1000))}
    headers = {"User-Agent": UA, "Referer": "https://passport.baidu.com/"}
    text = ""
    last_error = ""
    attempts = [True]
    for verify in attempts:
        try:
            jar = aiohttp.CookieJar(unsafe=True)
            if cookies:
                jar.update_cookies(cookies)
            connector = aiohttp.TCPConnector(ssl=_ssl_context() if verify else False)
            async with aiohttp.ClientSession(
                timeout=_timeout(timeout), cookie_jar=jar, connector=connector
            ) as session:
                async with session.get(UNICAST_URL, params=params, headers=headers) as response:
                    text = await response.text()
                    if response.status >= 400:
                        last_error = f"百度轮询 HTTP {response.status}: {_safe_detail(text, 200)}"
                        text = ""
                        break
                    if not text.strip():
                        return {"status": "waiting"}
                    break
        except aiohttp.ConnectionTimeoutError:
            # TCP 连接超时是网络不可达，不是"还没扫码"：不要反复显示等待。
            return {"status": "error", "error": "连接 passport.baidu.com 超时（网络不可达）"}
        except asyncio.TimeoutError:
            # 长轮询读超时属于正常等待。
            return {"status": "waiting"}
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {_safe_detail(exc, 200)}"
            if "timeout" in str(exc).lower():
                return {"status": "waiting"}
            if verify and _is_cert_failure(exc):
                attempts.append(False)
                continue
            break
    if not text.strip():
        try:
            text, _cookies = await asyncio.to_thread(
                _urllib_get_text, UNICAST_URL, params, timeout=min(10.0, max(3.0, float(timeout)))
            )
        except Exception as exc:
            detail = last_error or f"{type(exc).__name__}: {_safe_detail(exc, 200)}"
            return {"status": "error", "error": _safe_detail(detail, 300)}
        if not text.strip():
            return {"status": "waiting"}
    return parse_qr_poll_payload(text)


def _parse_login_payload(text: str) -> Dict[str, Any]:
    """解析 qrbdusslogin 响应：兼容纯 JSON、JSONP 包装与 HTML 转义。

    注意不能像旧实现那样把单引号整体替换成双引号：errInfo.msg 里出现
    apostrophe（如 "it's"）时会把合法 JSON 破坏成解析失败。
    """
    raw = str(text or "").strip()
    if not raw:
        return {}
    candidates = [raw]
    unescaped = html.unescape(raw)
    if unescaped != raw:
        candidates.append(unescaped)
    for candidate in candidates:
        data = _parse_jsonish(candidate)
        if data:
            return data
    return {}


async def complete_login(v: str, *, cookies: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """用 unicast 返回的 v 换取 BDUSS/STOKEN/PTOKEN。

    aiohttp 不可用（SteamOS/proot 老 TLS 栈）时回退到 urllib，并带上
    getqrcode 下发的 cookie，保证换登录态与二维码是同一会话。
    """
    value = str(v or "").strip()
    if not value:
        raise BaiduQrError("百度登录凭证 v 为空")
    ts = str(int(time.time() * 1000))
    params = {
        "bduss": value,
        "qrcode": "1",
        "tpl": "pp",
        "apiver": "v3",
        "tt": ts,
        "traceid": "",
        "time": ts,
        "alg": "v3",
        "elapsed": "1",
    }
    headers = {"User-Agent": UA, "Referer": "https://passport.baidu.com/"}
    text = ""
    last_error = ""
    attempts = [True]
    for verify in attempts:
        try:
            jar = aiohttp.CookieJar(unsafe=True)
            if cookies:
                jar.update_cookies(cookies)
            connector = aiohttp.TCPConnector(ssl=_ssl_context() if verify else False)
            async with aiohttp.ClientSession(
                timeout=_timeout(16), cookie_jar=jar, connector=connector
            ) as session:
                async with session.get(QR_LOGIN_URL, params=params, headers=headers) as response:
                    text = await response.text()
                    if response.status != 200:
                        last_error = f"HTTP {response.status}: {_safe_detail(text, 200)}"
                        text = ""
                        break
                    break
        except aiohttp.ConnectionTimeoutError as exc:
            raise BaiduQrError("百度登录连接超时（网络不可达），请检查网络后重新扫码") from exc
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {_safe_detail(exc, 200)}"
            if verify and _is_cert_failure(exc):
                attempts.append(False)
                continue
            break
    if not text.strip():
        try:
            text, _cookies = await asyncio.to_thread(
                _urllib_get_text, QR_LOGIN_URL, params, timeout=15
            )
        except Exception as exc:
            detail = last_error or f"{type(exc).__name__}: {_safe_detail(exc, 200)}"
            raise BaiduQrError(f"百度登录网络错误: {_safe_detail(detail, 300)}") from exc
        if not text.strip():
            raise BaiduQrError("百度登录响应为空")
    data = _parse_login_payload(text)
    session_data = data.get("data", {}).get("session") if isinstance(data.get("data"), dict) else {}
    if not isinstance(session_data, dict):
        session_data = {}
    bduss = str(session_data.get("bduss", "") or "").strip()
    stoken = str(session_data.get("stoken", "") or "").strip()
    ptoken = str(session_data.get("ptoken", "") or "").strip()
    if not bduss:
        message = ""
        if isinstance(data.get("errInfo"), dict):
            message = _safe_detail(data["errInfo"].get("msg", ""), 200)
        raise BaiduQrError(message or "百度扫码登录未返回 BDUSS")
    cookie_parts = [f"BDUSS={bduss}"]
    if stoken:
        cookie_parts.append(f"STOKEN={stoken}")
    if ptoken:
        cookie_parts.append(f"PTOKEN={ptoken}")
    user = data.get("data", {}).get("user") if isinstance(data.get("data"), dict) else {}
    if not isinstance(user, dict):
        user = {}
    return {
        "cookie": "; ".join(cookie_parts),
        "BDUSS": bduss,
        "user_account": str(user.get("displayName") or user.get("username") or user.get("userId") or "").strip(),
    }
