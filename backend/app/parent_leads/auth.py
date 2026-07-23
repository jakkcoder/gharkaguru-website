"""Signed cookie sessions for admin and agent logins."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Annotated, Any

from fastapi import Cookie, HTTPException, Response

from app.parent_leads.config import (
    PARENT_LEADS_ADMIN_PASSWORD as ADMIN_PASSWORD,
    PARENT_LEADS_SESSION_SECRET as SESSION_SECRET,
)

ADMIN_COOKIE = "pli_admin"
AGENT_COOKIE = "pli_agent"
SESSION_TTL_SECONDS = 60 * 60 * 12


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=bytes.fromhex(salt),
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )
    return f"scrypt:{salt}:{key.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt_hex, key_hex = stored.split(":", 2)
        if algo != "scrypt":
            return False
        key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=2**14,
            r=8,
            p=1,
            dklen=32,
        )
        return hmac.compare_digest(key.hex(), key_hex)
    except (ValueError, TypeError):
        return False


def _sign(payload: str) -> str:
    sig = hmac.new(
        SESSION_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{sig}"


def _verify(token: str | None) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None
    payload, sig = token.rsplit(".", 1)
    expected = hmac.new(
        SESSION_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8"))
    except (json.JSONDecodeError, ValueError):
        return None
    exp = data.get("exp")
    if not isinstance(exp, (int, float)) or time.time() >= float(exp):
        return None
    return data


def _make_token(data: dict[str, Any]) -> str:
    payload = base64.urlsafe_b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")
    return _sign(payload)


def verify_admin_password(password: str) -> bool:
    return hmac.compare_digest(password, ADMIN_PASSWORD)


def set_admin_cookie(response: Response) -> None:
    exp = int(time.time()) + SESSION_TTL_SECONDS
    token = _make_token({"exp": exp, "role": "admin"})
    response.set_cookie(
        key=ADMIN_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_TTL_SECONDS,
        path="/",
    )


def clear_admin_cookie(response: Response) -> None:
    response.delete_cookie(key=ADMIN_COOKIE, path="/")


def set_agent_cookie(response: Response, agent_id: str) -> None:
    exp = int(time.time()) + SESSION_TTL_SECONDS
    token = _make_token({"exp": exp, "role": "agent", "agent_id": agent_id})
    response.set_cookie(
        key=AGENT_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_TTL_SECONDS,
        path="/",
    )


def clear_agent_cookie(response: Response) -> None:
    response.delete_cookie(key=AGENT_COOKIE, path="/")


def admin_session(pli_admin: Annotated[str | None, Cookie()] = None) -> None:
    data = _verify(pli_admin)
    if not data or data.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Admin login required")


def agent_session(pli_agent: Annotated[str | None, Cookie()] = None) -> str:
    data = _verify(pli_agent)
    if not data or data.get("role") != "agent":
        raise HTTPException(status_code=401, detail="Agent login required")
    agent_id = data.get("agent_id")
    if not isinstance(agent_id, str) or not agent_id:
        raise HTTPException(status_code=401, detail="Invalid agent session")
    return agent_id


def optional_admin(pli_admin: Annotated[str | None, Cookie()] = None) -> bool:
    data = _verify(pli_admin)
    return bool(data and data.get("role") == "admin")


def optional_agent_id(pli_agent: Annotated[str | None, Cookie()] = None) -> str | None:
    data = _verify(pli_agent)
    if data and data.get("role") == "agent":
        aid = data.get("agent_id")
        return aid if isinstance(aid, str) else None
    return None
