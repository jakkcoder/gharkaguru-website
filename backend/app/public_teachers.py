"""Public teacher profiles. Phone numbers are never loaded or returned."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA = Path(__file__).with_name("data") / "public_teachers.json"
_FORBIDDEN = {"phone", "phone_number", "phone_normalized", "mobile", "whatsapp"}


@lru_cache(maxsize=1)
def load_teachers() -> list[dict[str, Any]]:
    rows = json.loads(_DATA.read_text(encoding="utf-8"))
    public: list[dict[str, Any]] = []
    for row in rows:
        if any(key in row for key in _FORBIDDEN):
            raise RuntimeError("Public teacher data must not include phone numbers")
        public.append(_view(row))
    return public


def _view(row: dict[str, Any]) -> dict[str, Any]:
    education = (row.get("education") or "").strip()
    medium = (row.get("medium") or "").strip()
    bio_parts = [part for part in (education, f"Medium: {medium}" if medium else "") if part]
    address = (row.get("address") or row.get("locality") or "").strip()
    subjects = list(row.get("subjects") or [])
    return {
        "id": row["id"],
        "name": row["name"],
        "slug": row["slug"],
        "photoUrl": "",
        "isVerified": False,
        "rating": 0,
        "reviewCount": 0,
        "subjects": subjects,
        "topSubjects": list(row.get("topSubjects") or subjects[:3]),
        "experienceYears": 0,
        "feeMin": 0,
        "feeMax": 0,
        "city": row.get("city") or address,
        "locality": address,
        "address": address,
        "distanceKm": 0,
        "responseTimeMins": 0,
        "boards": [],
        "classes": list(row.get("classes") or []),
        "gender": "Other",
        "mode": row.get("mode") or "both",
        "availability": [],
        "qualifications": {"degrees": [], "certifications": []},
        "bio": "\n".join(bio_parts),
        "education": education,
        "medium": medium,
        "teachingStyle": [],
        "achievements": [],
        "gallery": [],
        "reviews": [],
    }


def _subject_match(teacher: dict[str, Any], wanted: str) -> bool:
    needle = wanted.strip().lower()
    if not needle:
        return True
    owned = [item.lower() for item in teacher["subjects"]]
    if any(needle in item or item in needle for item in owned if item):
        return True
    return any(item == "all" or item.startswith("all ") for item in owned)


def search_teachers(
    *,
    location: str = "",
    subject: str = "",
    subjects: list[str] | None = None,
    mode: str = "",
    ids: list[str] | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    page = max(1, page)
    page_size = min(50, max(1, page_size))
    wanted_subjects = [subject, *(subjects or [])]
    wanted_subjects = [item.strip() for item in wanted_subjects if item and item.strip()]
    location_needle = location.strip().lower()
    mode_needle = mode.strip().lower()
    id_set = {item for item in (ids or []) if item}

    matched = []
    for teacher in load_teachers():
        if id_set and teacher["id"] not in id_set:
            continue
        if location_needle and location_needle not in f"{teacher['address']} {teacher['city']}".lower():
            continue
        if wanted_subjects and not any(_subject_match(teacher, item) for item in wanted_subjects):
            continue
        if mode_needle in {"online", "offline"} and teacher["mode"] not in {mode_needle, "both"}:
            continue
        if mode_needle == "both" and teacher["mode"] != "both":
            continue
        matched.append(teacher)

    start = (page - 1) * page_size
    items = [
        {
            "id": teacher["id"],
            "name": teacher["name"],
            "slug": teacher["slug"],
            "photoUrl": "",
            "isVerified": False,
            "rating": 0,
            "reviewCount": 0,
            "topSubjects": teacher["topSubjects"],
            "subjects": teacher["subjects"],
            "experienceYears": 0,
            "feeMin": 0,
            "feeMax": 0,
            "city": teacher["city"],
            "locality": teacher["locality"],
            "address": teacher["address"],
            "classes": teacher["classes"],
            "education": teacher["education"],
            "medium": teacher["medium"],
            "distanceKm": 0,
            "responseTimeMins": 0,
            "mode": teacher["mode"],
            "boards": [],
        }
        for teacher in matched[start : start + page_size]
    ]
    return {"items": items, "total": len(matched), "page": page, "pageSize": page_size}


def get_teacher(teacher_id: str) -> dict[str, Any] | None:
    for teacher in load_teachers():
        if teacher["id"] == teacher_id:
            return teacher
    return None
