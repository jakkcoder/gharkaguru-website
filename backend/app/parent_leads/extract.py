"""Normalize parent name/phone from Meta lead `fields` + annotations."""

from __future__ import annotations

import re
from typing import Any

PHONE_KEYS = (
    "phone_number",
    "phone",
    "mobile",
    "mobile_number",
    "whatsapp",
    "whatsapp_number",
    "phone_number_verified",
)
NAME_KEYS = (
    "full_name",
    "full name",
    "name",
    "parent_name",
    "your_name",
    "first_name",
)


def _norm_key(key: str) -> str:
    return re.sub(r"[\s\-]+", "_", key.strip().lower())


def fields_map(fields: dict[str, Any] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in (fields or {}).items():
        if value is None:
            continue
        text = str(value).strip()
        if text:
            out[_norm_key(str(key))] = text
    return out


def pick_phone(fields: dict[str, str]) -> str:
    for key in PHONE_KEYS:
        if fields.get(key):
            return normalize_phone(fields[key])
    for key, value in fields.items():
        if "phone" in key or "mobile" in key or "whatsapp" in key:
            return normalize_phone(value)
    return ""


def pick_name(fields: dict[str, str]) -> str:
    for key in NAME_KEYS:
        if fields.get(key):
            return fields[key]
    first = fields.get("first_name") or ""
    last = fields.get("last_name") or ""
    combined = f"{first} {last}".strip()
    if combined:
        return combined
    for key, value in fields.items():
        if "name" in key and "file" not in key:
            return value
    return ""


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) >= 10:
        return digits[-10:]
    return digits


def is_ops_filled(record: dict[str, Any]) -> bool:
    """True when meta-ads ops already enriched the lead (treat as filled upstream)."""
    for key in ("student_class", "location", "mode", "budget"):
        value = record.get(key)
        if value is not None and str(value).strip():
            return True
    note = record.get("note")
    return bool(note is not None and str(note).strip())


def flatten_parent_lead(record: dict[str, Any]) -> dict[str, Any]:
    fmap = fields_map(record.get("fields") if isinstance(record.get("fields"), dict) else {})
    phone = pick_phone(fmap)
    name = pick_name(fmap)
    return {
        "lead_id": str(record.get("id") or "").strip(),
        "form_id": str(record.get("form_id") or "").strip(),
        "form_name": str(record.get("form_name") or "").strip(),
        "created_time": str(record.get("created_time") or "").strip(),
        "parent_name": name,
        "parent_phone": phone,
        "student_class": str(record.get("student_class") or fmap.get("class_grade") or "").strip(),
        "location": str(record.get("location") or "").strip(),
        "mode": str(record.get("mode") or "").strip(),
        "budget": str(record.get("budget") or "").strip(),
        "note": str(record.get("note") or "").strip(),
        "status": str(record.get("status") or "").strip(),
        "is_junk": bool(record.get("is_junk")),
        "platform": str(record.get("platform") or "").strip(),
        "fields_json": fmap,
        "ops_filled": is_ops_filled(record),
    }
