"""Append website tutor registrations to the teacher-pipeline GCS lead file."""

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
