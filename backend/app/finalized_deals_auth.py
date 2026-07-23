"""Simple password gate + signed cookie for /finilized_deals."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Annotated

from fastapi import Cookie, HTTPException, Request, Response

from app.config import FINALIZED_DEALS_PASSWORD, FINALIZED_DEALS_SESSION_SECRET

COOKIE_NAME = "fd_session"
SESSION_TTL_SECONDS = 60 * 60 * 12  # 12 hours


def _sign(payload: str) -> str:
    sig = hmac.new(
        FINALIZED_DEALS_SESSION_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{sig}"


def _verify(token: str) -> bool:
    if not token or "." not in token:
        return False
    payload, sig = token.rsplit(".", 1)
    expected = hmac.new(
        FINALIZED_DEALS_SESSION_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return False
    try:
        data = json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8"))
    except (json.JSONDecodeError, ValueError):
        return False
    exp = data.get("exp")
    return isinstance(exp, (int, float)) and time.time() < float(exp)


def verify_password(password: str) -> bool:
    return hmac.compare_digest(password, FINALIZED_DEALS_PASSWORD)


def set_session_cookie(response: Response) -> None:
    exp = int(time.time()) + SESSION_TTL_SECONDS
    raw = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode("utf-8")).decode("utf-8")
    token = _sign(raw)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_TTL_SECONDS,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")


def require_finalized_deals_session(
    fd_session: Annotated[str | None, Cookie()] = None,
) -> None:
    if not fd_session or not _verify(fd_session):
        raise HTTPException(status_code=401, detail="Login required")


def is_authenticated(request: Request) -> bool:
    token = request.cookies.get(COOKIE_NAME)
    return bool(token and _verify(token))
