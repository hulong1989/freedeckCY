from __future__ import annotations

import os
import pwd
from pathlib import Path
from typing import Any, Dict, List, Optional


_RUNTIME_USER_CACHE: Optional[Dict[str, Any]] = None


def _normalize_home_path(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        return os.path.realpath(os.path.expanduser(raw))
    except Exception:
        return ""


def _build_candidate_from_pwd(info: Any, *, source: str, score: int) -> Optional[Dict[str, Any]]:
    if info is None:
        return None
    try:
        uid = int(getattr(info, "pw_uid", -1))
        gid = int(getattr(info, "pw_gid", -1))
    except Exception:
        return None
    name = str(getattr(info, "pw_name", "") or "").strip()
    home = _normalize_home_path(getattr(info, "pw_dir", ""))
    if uid < 0 or gid < 0 or not name or not home:
        return None
    return {
        "name": name,
        "uid": uid,
        "gid": gid,
        "home": home,
        "source": source,
        "score": int(score),
    }


def _candidate_from_name(name: Any, *, source: str, score: int) -> Optional[Dict[str, Any]]:
    normalized = str(name or "").strip()
    if not normalized:
        return None
    try:
        return _build_candidate_from_pwd(pwd.getpwnam(normalized), source=source, score=score)
    except Exception:
        return None


def _candidate_from_uid(uid: Any, *, source: str, score: int) -> Optional[Dict[str, Any]]:
    try:
        normalized_uid = int(uid)
    except Exception:
        return None
    if normalized_uid < 0:
        return None
    try:
        return _build_candidate_from_pwd(pwd.getpwuid(normalized_uid), source=source, score=score)
    except Exception:
        return None


def _candidate_from_home(home: Any, *, source: str, score: int) -> Optional[Dict[str, Any]]:
    normalized = _normalize_home_path(home)
    if not normalized or not os.path.isdir(normalized):
        return None
    try:
        stat_result = os.stat(normalized)
    except Exception:
        return None
    candidate = _candidate_from_uid(getattr(stat_result, "st_uid", -1), source=source, score=score)
    if candidate is not None:
        return candidate
    uid = int(getattr(stat_result, "st_uid", -1))
    gid = int(getattr(stat_result, "st_gid", -1))
    if uid < 0 or gid < 0:
        return None
    return {
        "name": os.path.basename(normalized.rstrip("/")) or f"uid-{uid}",
        "uid": uid,
        "gid": gid,
        "home": normalized,
        "source": source,
        "score": int(score),
    }


def _candidate_from_path_owner(path: Any, *, source: str, score: int) -> Optional[Dict[str, Any]]:
    normalized = _normalize_home_path(path)
    if not normalized or not os.path.exists(normalized):
        return None
    try:
        stat_result = os.stat(normalized)
    except Exception:
        return None
    return _candidate_from_uid(getattr(stat_result, "st_uid", -1), source=source, score=score)


def _append_candidate(candidates: Dict[int, Dict[str, Any]], candidate: Optional[Dict[str, Any]]) -> None:
    if not isinstance(candidate, dict):
        return
    uid = int(candidate.get("uid", -1) or -1)
    gid = int(candidate.get("gid", -1) or -1)
    home = _normalize_home_path(candidate.get("home", ""))
    name = str(candidate.get("name", "") or "").strip()
    score = int(candidate.get("score", 0) or 0)
    if uid < 0 or gid < 0 or not name or not home:
        return
    existing = candidates.get(uid)
    if existing is None or score > int(existing.get("score", 0) or 0):
        candidates[uid] = {
            "name": name,
            "uid": uid,
            "gid": gid,
            "home": home,
            "source": str(candidate.get("source", "") or "").strip(),
            "score": score,
        }


def resolve_runtime_user(*, refresh: bool = False) -> Dict[str, Any]:
    global _RUNTIME_USER_CACHE
    if not refresh and isinstance(_RUNTIME_USER_CACHE, dict):
        return dict(_RUNTIME_USER_CACHE)

    candidates: Dict[int, Dict[str, Any]] = {}

    for env_name, score in (
        ("FREDECK_TARGET_USER", 1000),
        ("DECKY_TARGET_USER", 950),
        ("SUDO_USER", 900),
        ("PKEXEC_UID", 880),
    ):
        value = str(os.environ.get(env_name, "") or "").strip()
        if not value:
            continue
        candidate = _candidate_from_uid(value, source=f"env:{env_name}", score=score)
        if candidate is None:
            candidate = _candidate_from_name(value, source=f"env:{env_name}", score=score)
        _append_candidate(candidates, candidate)

    for env_name, score in (
        ("FREDECK_TARGET_HOME", 980),
        ("DECKY_USER_HOME", 940),
        ("HOME", 600),
    ):
        _append_candidate(
            candidates,
            _candidate_from_home(os.environ.get(env_name, ""), source=f"env:{env_name}", score=score),
        )

    runtime_dir = str(os.environ.get("XDG_RUNTIME_DIR", "") or "").strip()
    runtime_match = runtime_dir.split("/run/user/", 1)[1].split("/", 1)[0].strip() if "/run/user/" in runtime_dir else ""
    if runtime_match:
        _append_candidate(
            candidates,
            _candidate_from_uid(runtime_match, source="env:XDG_RUNTIME_DIR", score=920),
        )

    module_path = _normalize_home_path(__file__)
    cwd_path = _normalize_home_path(os.getcwd())
    for path, score, label in (
        (module_path, 860, "module_owner"),
        (cwd_path, 820, "cwd_owner"),
    ):
        _append_candidate(candidates, _candidate_from_path_owner(path, source=label, score=score))

    try:
        plugin_dir = str(os.environ.get("DECKY_PLUGIN_DIR", "") or "").strip()
    except Exception:
        plugin_dir = ""
    if plugin_dir:
        _append_candidate(
            candidates,
            _candidate_from_path_owner(plugin_dir, source="env:DECKY_PLUGIN_DIR", score=870),
        )

    try:
        current_uid = os.getuid()
    except Exception:
        current_uid = -1
    if current_uid > 0:
        _append_candidate(candidates, _candidate_from_uid(current_uid, source="process_uid", score=700))

    try:
        plugin_anchor = module_path or cwd_path
        for info in pwd.getpwall():
            candidate = _build_candidate_from_pwd(info, source="passwd_scan", score=100)
            if candidate is None:
                continue
            uid = int(candidate.get("uid", -1) or -1)
            name = str(candidate.get("name", "") or "").strip().lower()
            home = str(candidate.get("home", "") or "").strip()
            shell = str(getattr(info, "pw_shell", "") or "").strip().lower()
            score = int(candidate.get("score", 0) or 0)
            if uid < 1000:
                continue
            if shell.endswith("/nologin") or shell.endswith("/false"):
                score -= 30
            if plugin_anchor and home and plugin_anchor.startswith(home.rstrip("/") + os.sep):
                score += 120
            if name == "deck":
                score += 20
            candidate["score"] = score
            _append_candidate(candidates, candidate)
    except Exception:
        pass

    filtered = [item for item in candidates.values() if int(item.get("uid", -1) or -1) != 0]
    if filtered:
        selected = max(
            filtered,
            key=lambda item: (
                int(item.get("score", 0) or 0),
                1 if str(item.get("name", "") or "").strip().lower() == "deck" else 0,
                -int(item.get("uid", 0) or 0),
            ),
        )
    else:
        selected = _candidate_from_name("deck", source="fallback:deck", score=10)
        if selected is None:
            selected = {
                "name": str(os.environ.get("USER", "root") or "root").strip() or "root",
                "uid": max(0, int(os.getuid() if hasattr(os, "getuid") else 0)),
                "gid": max(0, int(os.getgid() if hasattr(os, "getgid") else 0)),
                "home": _normalize_home_path(Path.home()),
                "source": "fallback:process",
                "score": 0,
            }

    _RUNTIME_USER_CACHE = dict(selected)
    return dict(selected)


def resolve_runtime_home_dir(*, refresh: bool = False) -> str:
    return str(resolve_runtime_user(refresh=refresh).get("home", "") or "")

