from __future__ import annotations

import re
from typing import Any

from fastapi import Header, HTTPException

from app.db import connect, new_token, now_iso, row_to_dict


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", (raw or "").strip())
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if len(digits) != 10:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_PHONE", "message": "Enter a valid 10-digit Indian phone number."}},
        )
    return digits


def create_session(phone: str, role: str) -> dict[str, Any]:
    phone = normalize_phone(phone)
    role = (role or "student").strip().lower()
    if role not in {"student", "teacher"}:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_ROLE", "message": "Role must be student or teacher."}},
        )

    token = new_token()
    ts = now_iso()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO users (phone, role, created_at, last_login_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(phone) DO UPDATE SET
              role = excluded.role,
              last_login_at = excluded.last_login_at
            """,
            (phone, role, ts, ts),
        )
        conn.execute(
            "INSERT INTO sessions (token, phone, role, created_at) VALUES (?, ?, ?, ?)",
            (token, phone, role, ts),
        )
        conn.commit()
    return {"token": token, "role": role, "phone": phone}


def get_session(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Login required."}},
        )
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Login required."}},
        )
    with connect(read_only=True) as conn:
        row = conn.execute(
            "SELECT token, phone, role, created_at FROM sessions WHERE token = ?",
            (token,),
        ).fetchone()
    session = row_to_dict(row)
    if not session:
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Session expired. Please login again."}},
        )
    return session
