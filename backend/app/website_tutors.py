"""Website tutor registrations for the teacher lead pipeline.

Every registration is kept in website.db (``website_tutor_leads``), which the
teacher pipeline reads through ``GET /api/internal/website-tutors``. The GCS
copy is written only where GCS is in use (not when ``SKIP_GCS_SYNC`` is set).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from app.config import GOOGLE_CLOUD_PROJECT

DEFAULT_WEBSITE_TUTORS_GCS = (
    "gs://vertex-ai-learning-487906-gharka-leads/meta-ads/leads/website-tutors.json"
)
FORM_NAME = "Become a Home Tutor"

MEDIUMS = {"English", "Hindi", "Both"}
TEACHING_MODES = {"Home", "Online", "Both"}
# Longest answer kept per field. Longer input is a mistake or abuse, not a tutor.
MAX_LENGTHS = {
    "full_name": 100,
    "location": 300,
    "pin": 6,
    "subject": 200,
    "class_can_teach": 100,
    "education": 200,
    "medium": 10,
    "teaching_mode": 10,
}


def registration_problem(phone: str, answers: dict[str, str]) -> str | None:
    """The first thing wrong with a submission, worded for the tutor. None when it is fine."""
    if not (len(phone) == 10 and phone.isascii() and phone[0] in "6789"):
        return "Enter a valid 10-digit mobile number."
    if any(not value for value in answers.values()):
        return "Fill every tutor field."
    for field, limit in MAX_LENGTHS.items():
        if len(answers[field]) > limit:
            return f"{field.replace('_', ' ').capitalize()} must be {limit} characters or fewer."
    if len(answers["full_name"]) < 2:
        return "Enter your full name."
    pin = answers["pin"]
    if not (len(pin) == 6 and set(pin) <= set("0123456789") and pin[0] != "0"):
        return "PIN must be 6 digits."
    if answers["medium"] not in MEDIUMS:
        return "Choose English, Hindi, or Both for medium."
    if answers["teaching_mode"] not in TEACHING_MODES:
        return "Choose Home, Online, or Both for teaching mode."
    return None


def website_tutors_gcs() -> str:
    return os.getenv("WEBSITE_TUTORS_GCS", DEFAULT_WEBSITE_TUTORS_GCS).strip()


def tutor_lead_document(phone: str, answers: dict[str, str], *, created_time: str | None = None) -> dict[str, Any]:
    """Lead object the teacher bronze reader already understands."""
    digits = "".join(ch for ch in phone if ch.isdigit())
    local = digits[-10:]
    created = created_time or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "id": f"web-{local}",
        "created_time": created,
        "form_name": FORM_NAME,
        "fields": {
            "full_name": answers["full_name"].strip(),
            "phone_number": local,
            "location": answers["location"].strip(),
            "pin": answers["pin"].strip(),
            "subject": answers["subject"].strip(),
            "class_can_teach": answers["class_can_teach"].strip(),
            "educational_background": answers["education"].strip(),
            "english_hindi_medium": answers["medium"].strip(),
            "online_offline": answers["teaching_mode"].strip(),
        },
    }


def merge_tutor_lead(payload: dict[str, Any] | None, lead: dict[str, Any]) -> dict[str, Any]:
    body = payload if isinstance(payload, dict) else {}
    leads = [item for item in body.get("leads") or [] if isinstance(item, dict) and item.get("id") != lead["id"]]
    leads.append(lead)
    return {"leads": leads}


def gcs_copy_enabled() -> bool:
    return os.getenv("SKIP_GCS_SYNC", "").strip().lower() not in {"1", "true", "yes"}


def save_website_tutor(conn: Any, lead: dict[str, Any]) -> None:
    """Keep this phone's latest registration. The first submit time is kept."""
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    phone = lead["fields"]["phone_number"]
    row = conn.execute(
        "SELECT lead_json FROM website_tutor_leads WHERE phone = ?", (phone,)
    ).fetchone()
    if row:
        lead = {**lead, "created_time": json.loads(row[0]).get("created_time") or lead["created_time"]}
    conn.execute(
        """
        INSERT INTO website_tutor_leads (id, phone, lead_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(phone) DO UPDATE SET
          id = excluded.id,
          lead_json = excluded.lead_json,
          updated_at = excluded.updated_at
        """,
        (lead["id"], phone, json.dumps(lead, ensure_ascii=False), lead["created_time"], now),
    )


def list_website_tutors(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT lead_json FROM website_tutor_leads ORDER BY created_at").fetchall()
    return [json.loads(row[0]) for row in rows]


def _parse_gcs(uri: str) -> tuple[str, str]:
    if not uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {uri}")
    bucket, _, blob = uri[5:].partition("/")
    if not bucket or not blob:
        raise ValueError(f"Invalid GCS URI: {uri}")
    return bucket, blob


def append_website_tutor(phone: str, answers: dict[str, str]) -> dict[str, Any]:
    """Replace this phone's lead and write the file if the generation still matches."""
    from google.api_core.exceptions import PreconditionFailed
    from google.cloud import storage

    lead = tutor_lead_document(phone, answers)
    bucket_name, blob_name = _parse_gcs(website_tutors_gcs())
    client = storage.Client(project=GOOGLE_CLOUD_PROJECT)
    bucket = client.bucket(bucket_name)
    last_error: Exception | None = None
    for _ in range(5):
        blob = bucket.blob(blob_name)
        if blob.exists():
            blob.reload()
            generation = blob.generation
            payload = json.loads(blob.download_as_text(encoding="utf-8"))
        else:
            generation = 0
            payload = {"leads": []}
        merged = merge_tutor_lead(payload, lead)
        try:
            blob.upload_from_string(
                json.dumps(merged, ensure_ascii=False),
                content_type="application/json",
                if_generation_match=generation,
            )
            return lead
        except PreconditionFailed as exc:
            last_error = exc
            continue
    raise RuntimeError("Could not save the tutor lead. Try again.") from last_error
