"""百度 Passport 网页扫码登录（BDUSS/Cookie）。"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, Optional

import aiohttp

QRCODE_URL = "https://passport.baidu.com/v2/api/getqrcode"
UNICAST_URL = "https://passport.baidu.com/channel/unicast"
QR_LOGIN_URL = "https://passport.baidu.com/v3/login/main/qrbdusslogin"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class BaiduQrError(RuntimeError):
    pass


def _timeout(total: float = 12.0) -> aiohttp.ClientTimeout:
    return aiohttp.ClientTimeout(total=total, connect=8, sock_connect=8, sock_read=total)


async def request_qr() -> Dict[str, Any]:
    params = {"lp": "pc", "qrloginfrom": "pc"}
    headers = {"User-Agent": UA, "Referer": "https://passport.baidu.com/"}
    async with aiohttp.ClientSession(timeout=_timeout(15)) as session:
        async with session.get(QRCODE_URL, params=params, headers=headers) as response:
            text = await response.text()
    try:
        data = json.loads(text)
    except Exception as exc:
        raise BaiduQrError(f"百度二维码响应异常: {text[:200]}") from exc
    if int(data.get("errno", 0) or 0) != 0:
        raise BaiduQrError(str(data.get("prompt") or "获取百度二维码失败"))
    sign = str(data.get("sign", "") or "").strip()
    imgurl = str(data.get("imgurl", "") or "").strip()
    if not sign:
        raise BaiduQrError("百度二维码缺少 sign")
    if imgurl and not imgurl.startswith(("http://", "https://")):
        imgurl = "https://" + imgurl.lstrip("/")
    return {"sign": sign, "imgurl": imgurl, "prompt": str(data.get("prompt", "") or "")}


async def fetch_qr_image(imgurl: str) -> bytes:
    url = str(imgurl or "").strip()
    if not url:
        return b""
    headers = {"User-Agent": UA, "Referer": "https://passport.baidu.com/"}
    async with aiohttp.ClientSession(timeout=_timeout(15)) as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                return b""
            return await response.read()


async def poll_qr(sign: str, *, timeout: float = 8.0) -> Dict[str, Any]:
    """单次轮询；百度是长轮询，超时视为仍在等待。"""
    params = {"channel_id": str(sign or "").strip(), "tpl": "pp", "tt": str(int(time.time() * 1000))}
    headers = {"User-Agent": UA, "Referer": "https://passport.baidu.com/"}
    try:
        async with aiohttp.ClientSession(timeout=_timeout(timeout)) as session:
            async with session.get(UNICAST_URL, params=params, headers=headers) as response:
                text = await response.text()
    except Exception:
        return {"status": "waiting"}
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


async def complete_login(v: str) -> Dict[str, Any]:
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
    async with aiohttp.ClientSession(timeout=_timeout(20)) as session:
        async with session.get(QR_LOGIN_URL, params=params, headers=headers) as response:
            text = await response.text()
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
