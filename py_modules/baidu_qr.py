"""百度 Passport 网页扫码登录（BDUSS/Cookie）。"""

from __future__ import annotations

import asyncio
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


class BaiduQrError(RuntimeError):
    pass


def _timeout(total: float = 12.0) -> aiohttp.ClientTimeout:
    return aiohttp.ClientTimeout(total=total, connect=8, sock_connect=8, sock_read=total)


def _ssl_context():
    try:
        return ssl.create_default_context()
    except Exception:
        return False


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


def _urllib_qr(url: str, params: Dict[str, Any]) -> str:
    query = urlencode({str(k): str(v) for k, v in params.items()})
    request_url = f"{url}?{query}"
    request = urllib.request.Request(request_url, headers=HEADERS)
    context = _ssl_context()
    try:
        with urllib.request.urlopen(request, timeout=15, context=context) as response:
            return response.read().decode("utf-8", "replace")
    except Exception as exc:
        if context is not False:
            try:
                with urllib.request.urlopen(request, timeout=15, context=ssl._create_unverified_context()) as response:
                    return response.read().decode("utf-8", "replace")
            except Exception:
                pass
        raise exc


async def request_qr() -> Dict[str, Any]:
    params = {"lp": "pc", "qrloginfrom": "pc"}
    text = ""
    last_error = ""
    # 1) aiohttp 主路径；证书/连接错误时重试不校验证书。
    for verify in (True, False):
        try:
            connector = aiohttp.TCPConnector(ssl=_ssl_context() if verify else False)
            jar = aiohttp.CookieJar(unsafe=True)
            async with aiohttp.ClientSession(timeout=_timeout(15), cookie_jar=jar, connector=connector) as session:
                async with session.get(QRCODE_URL, params=params, headers=HEADERS) as response:
                    text = await response.text()
                    if response.status == 200 and text.strip():
                        break
                    last_error = f"HTTP {response.status}: {text[:200]}"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
    # 2) urllib 回退（部分 Decky/SteamOS 环境的 aiohttp TLS 不可用）。
    if not text.strip():
        try:
            text = await asyncio.to_thread(_urllib_qr, QRCODE_URL, params)
        except Exception as exc:
            detail = last_error or f"{type(exc).__name__}: {exc}"
            raise BaiduQrError(f"获取百度二维码失败（{detail}）") from exc
    data = _parse_jsonish(text)
    if not data:
        raise BaiduQrError(f"百度二维码响应异常: {text[:300]}")
    if int(data.get("errno", 0) or 0) != 0:
        raise BaiduQrError(str(data.get("prompt") or f"百度二维码 errno={data.get('errno')}"))
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
        "cookies": {},
    }


async def fetch_qr_image(imgurl: str) -> bytes:
    url = str(imgurl or "").strip()
    if not url:
        return b""
    try:
        connector = aiohttp.TCPConnector(ssl=_ssl_context())
        async with aiohttp.ClientSession(timeout=_timeout(15), connector=connector) as session:
            async with session.get(url, headers=HEADERS) as response:
                if response.status != 200:
                    return b""
                return await response.read()
    except Exception:
        try:
            request = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=15, context=ssl._create_unverified_context()) as response:
                return response.read()
        except Exception:
            return b""


async def poll_qr(
    sign: str,
    *,
    timeout: float = 8.0,
    cookies: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """单次轮询；百度是长轮询，超时视为仍在等待。"""
    params = {"channel_id": str(sign or "").strip(), "tpl": "pp", "tt": str(int(time.time() * 1000))}
    headers = {"User-Agent": UA, "Referer": "https://passport.baidu.com/"}
    text = ""
    last_error = ""
    for verify in (True, False):
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
                        last_error = f"HTTP {response.status}"
                        text = ""
                        continue
                    if text.strip():
                        break
        except asyncio.TimeoutError:
            return {"status": "waiting"}
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if "timeout" in str(exc).lower():
                return {"status": "waiting"}
    if not text.strip():
        return {"status": "error", "error": (last_error or "empty response")[:300]}
    if not text.strip():
        return {"status": "waiting"}
    try:
        data = json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.S)
        try:
            data = json.loads(match.group(0)) if match else {}
        except Exception:
            data = {}
    if int(data.get("errno", -1) or 0) == 1:
        return {"status": "waiting"}
    if int(data.get("errno", -1) or 0) != 0:
        return {"status": "waiting"}
    channel_v = data.get("channel_v")
    try:
        payload = json.loads(channel_v) if isinstance(channel_v, str) else (channel_v or {})
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    v = str(payload.get("v", "") or "").strip()
    if v:
        return {"status": "confirmed", "v": v}
    if int(payload.get("status", -1) or 0) == 1:
        return {"status": "scanned"}
    return {"status": "waiting"}


def _parse_login_payload(text: str) -> Dict[str, Any]:
    cleaned = text.replace("&quot;", '"').replace("'", '"')
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"\{.*\}", cleaned, re.S)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except Exception:
            return {}


async def complete_login(v: str, *, cookies: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """用 unicast 返回的 v 换取 BDUSS/STOKEN/PTOKEN。"""
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
    for verify in (True, False):
        try:
            jar = aiohttp.CookieJar(unsafe=True)
            if cookies:
                jar.update_cookies(cookies)
            connector = aiohttp.TCPConnector(ssl=_ssl_context() if verify else False)
            async with aiohttp.ClientSession(
                timeout=_timeout(20), cookie_jar=jar, connector=connector
            ) as session:
                async with session.get(QR_LOGIN_URL, params=params, headers=headers) as response:
                    text = await response.text()
                    if response.status != 200:
                        last_error = f"HTTP {response.status}: {text[:200]}"
                        text = ""
                        continue
                    break
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
    if not text.strip():
        raise BaiduQrError(f"百度登录网络错误: {last_error or 'empty response'}")
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
            message = str(data["errInfo"].get("msg", "") or "")
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
