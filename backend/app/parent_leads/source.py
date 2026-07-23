"""Load parents.json + annotations.json from GCS (meta-ads-manager exports)."""

from __future__ import annotations

import json
from typing import Any

from google.cloud import storage

from app.parent_leads.config import (
    GCS_ANNOTATIONS_OBJECT,
    GCS_LEADS_BUCKET,
    GCS_PARENTS_OBJECT,
    GOOGLE_CLOUD_PROJECT,
    GOLD_STATUS,
    LEADS_START_DATE,
)
from app.parent_leads.extract import flatten_parent_lead


def _client() -> storage.Client:
    return storage.Client(project=GOOGLE_CLOUD_PROJECT)


def read_json_object(object_name: str) -> dict[str, Any]:
    blob = _client().bucket(GCS_LEADS_BUCKET).blob(object_name)
    if not blob.exists():
        raise FileNotFoundError(f"gs://{GCS_LEADS_BUCKET}/{object_name} not found")
    return json.loads(blob.download_as_text(encoding="utf-8"))


def apply_annotations(
    leads: list[dict[str, Any]], annotations: dict[str, Any]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for lead in leads:
        lead_id = str(lead.get("id") or "")
        ann = annotations.get(lead_id) or {}
        merged = dict(lead)
        for key in (
            "is_junk",
            "note",
            "budget",
            "student_class",
            "status",
            "mode",
            "location",
            "follow_up_count",
            "demo_at",
            "demo_review_status",
            "gold_transition_at",
            "annotation_updated_at",
        ):
            if key in ann and ann[key] is not None:
                merged[key] = ann[key]
        if "updated_at" in ann and ann["updated_at"] is not None:
            merged["annotation_updated_at"] = ann["updated_at"]
        out.append(merged)
    return out


def load_meta_parent_leads() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return flattened parent candidates + meta about the source pull."""
    parents_raw = read_json_object(GCS_PARENTS_OBJECT)
    try:
        annotations_raw = read_json_object(GCS_ANNOTATIONS_OBJECT)
    except FileNotFoundError:
        annotations_raw = {"annotations": {}}

    leads = parents_raw.get("leads") or []
    annotations = annotations_raw.get("annotations") or {}
    if not isinstance(leads, list):
        leads = []
    if not isinstance(annotations, dict):
        annotations = {}

    merged = apply_annotations(leads, annotations)
    flattened = [flatten_parent_lead(row) for row in merged]

    meta = {
        "bucket": GCS_LEADS_BUCKET,
        "parents_object": GCS_PARENTS_OBJECT,
        "annotations_object": GCS_ANNOTATIONS_OBJECT,
        "exported_at": parents_raw.get("exported_at"),
        "source_lead_count": len(flattened),
        "annotation_count": len(annotations),
    }
    return flattened, meta


def filter_new_unfilled(
    flattened: list[dict[str, Any]],
    *,
    existing_ids: set[str],
    require_contact: bool = True,
) -> list[dict[str, Any]]:
    """Keep only parents that are new to our DB and not filled upstream/in-app.

    Rules (parent-only queue):
    - drop leads created before LEADS_START_DATE (default: 2026-07-17)
    - drop junk
    - drop gold (status == Demo scheduled)
    - drop ops-filled in meta-ads (class/location/mode/budget/note already set)
    - drop lead_ids already present in inbox DB
    - optionally require at least a phone or a name
    """
    selected: list[dict[str, Any]] = []
    for row in flattened:
        lead_id = row.get("lead_id") or ""
        if not lead_id:
            continue
        if lead_id in existing_ids:
            continue
        # Date filter: only include leads from LEADS_START_DATE onwards
        created_time = row.get("created_time") or ""
        if created_time and LEADS_START_DATE:
            # created_time format: "2026-07-17T10:30:00+0000" or similar
            lead_date = created_time[:10]  # Extract YYYY-MM-DD
            if lead_date < LEADS_START_DATE:
                continue
        if row.get("is_junk"):
            continue
        if (row.get("status") or "").strip() == GOLD_STATUS:
            continue
        if row.get("ops_filled"):
            continue
        if require_contact and not (row.get("parent_phone") or row.get("parent_name")):
            continue
        selected.append(row)
    selected.sort(key=lambda r: r.get("created_time") or "", reverse=True)
    return selected
