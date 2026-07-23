"""Direct Meta Graph API load for parent leads (incremental) + GCS parents.json export."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from google.cloud import storage

from app.parent_leads.config import (
    GCS_ANNOTATIONS_OBJECT,
    GCS_LEADS_BUCKET,
    GCS_META_SYNC_STATE_OBJECT,
    GCS_PARENTS_OBJECT,
    GOOGLE_CLOUD_PROJECT,
    LEADS_OVERLAP_SECONDS,
    LEADS_START_DATE,
    META_API_VERSION,
    PAGE_ACCESS_TOKEN,
    PAGE_ID,
    PARENT_FORM_IDS,
    PARENT_LEADS_GCS_STATE_PATH,
    PARENT_LEADS_META_SYNC,
)
from app.parent_leads.extract import flatten_parent_lead
from app.parent_leads.source import apply_annotations, read_json_object

logger = logging.getLogger("parent-leads-meta-sync")

LEAD_FIELDS = (
    "id,created_time,field_data,ad_id,adset_id,campaign_id,form_id,platform,is_organic"
)


def _meta_enabled() -> bool:
    return PARENT_LEADS_META_SYNC and bool(PAGE_ACCESS_TOKEN.strip()) and bool(PAGE_ID.strip())


def _storage_client() -> storage.Client:
    return storage.Client(project=GOOGLE_CLOUD_PROJECT)


def _read_state() -> dict[str, Any]:
    client = _storage_client()
    bucket = client.bucket(GCS_LEADS_BUCKET)
    blob = bucket.blob(GCS_META_SYNC_STATE_OBJECT)
    if blob.exists():
        try:
            return json.loads(blob.download_as_text(encoding="utf-8"))
        except Exception:
            pass
    # Legacy: local file from older revisions
    path = PARENT_LEADS_GCS_STATE_PATH
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def _write_state(state: dict[str, Any]) -> None:
    client = _storage_client()
    bucket = client.bucket(GCS_LEADS_BUCKET)
    blob = bucket.blob(GCS_META_SYNC_STATE_OBJECT)
    blob.upload_from_string(json.dumps(state), content_type="application/json")
    path = PARENT_LEADS_GCS_STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state))


def _since_ts_for_form(cursors: dict[str, str], *, full_sync: bool) -> int | None:
    if full_sync:
        return None
    if LEADS_START_DATE:
        try:
            start = datetime.fromisoformat(LEADS_START_DATE).replace(tzinfo=timezone.utc)
            return int(start.timestamp())
        except ValueError:
            pass
    return _default_since_ts()


def _parse_created_ts(created_time: str | None) -> int | None:
    if not created_time:
        return None
    try:
        dt = datetime.fromisoformat(created_time.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return None


def _default_since_ts() -> int:
    since = datetime.now(timezone.utc) - timedelta(days=45)
    return int(since.timestamp())


def _api_lead_record(data: dict[str, Any], form_names: dict[str, str]) -> dict[str, Any]:
    fields: dict[str, str] = {}
    for item in data.get("field_data") or []:
        name = str(item.get("name") or "")
        values = item.get("values") or []
        if name and values:
            fields[name] = str(values[0]).strip()
    form_id = str(data.get("form_id") or "")
    return {
        "id": str(data.get("id") or ""),
        "form_id": form_id,
        "form_name": form_names.get(form_id) or form_id,
        "created_time": str(data.get("created_time") or ""),
        "ad_id": data.get("ad_id"),
        "adset_id": data.get("adset_id"),
        "campaign_id": data.get("campaign_id"),
        "platform": data.get("platform"),
        "is_organic": data.get("is_organic"),
        "is_junk": False,
        "note": None,
        "budget": None,
        "student_class": None,
        "status": None,
        "mode": None,
        "location": None,
        "fields": fields,
    }


class MetaLeadClient:
    def __init__(self, access_token: str) -> None:
        self.access_token = access_token
        self.base_url = f"https://graph.facebook.com/{META_API_VERSION}"

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        p = dict(params or {})
        p.setdefault("access_token", self.access_token)
        url = path if path.startswith("http") else f"{self.base_url}/{path.lstrip('/')}"
        with httpx.Client(timeout=90.0) as client:
            response = client.get(url, params=p)
            payload = response.json()
        if response.status_code >= 400 or "error" in payload:
            err = payload.get("error") or {}
            raise RuntimeError(err.get("message") or payload)
        return payload

    def paginate_leads(
        self,
        form_id: str,
        *,
        since_ts: int | None,
        overlap_seconds: int = LEADS_OVERLAP_SECONDS,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"fields": LEAD_FIELDS, "limit": 100}
        if since_ts:
            params["filtering"] = json.dumps(
                [
                    {
                        "field": "time_created",
                        "operator": "GREATER_THAN",
                        "value": max(0, since_ts - overlap_seconds),
                    }
                ]
            )
        out: list[dict[str, Any]] = []
        path = f"{form_id}/leads"
        while path:
            if path.startswith("http"):
                payload = self._get(path, {})
            else:
                payload = self._get(path, params)
                params = None
            out.extend(payload.get("data") or [])
            next_url = (payload.get("paging") or {}).get("next")
            path = next_url or ""
        return out

    def form_names(self, page_id: str) -> dict[str, str]:
        names: dict[str, str] = {}
        payload = self._get(
            f"{page_id}/leadgen_forms",
            {"fields": "id,name", "limit": 100},
        )
        for row in payload.get("data") or []:
            names[str(row["id"])] = str(row.get("name") or row["id"])
        return names


def _write_parents_json_to_gcs(leads: list[dict[str, Any]]) -> str:
    blob_path = GCS_PARENTS_OBJECT
    body = {
        "exported_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": "parent_leads.meta_sync",
        "leads": leads,
    }
    bucket = _storage_client().bucket(GCS_LEADS_BUCKET)
    bucket.blob(blob_path).upload_from_string(
        json.dumps(body, ensure_ascii=False, indent=2),
        content_type="application/json",
    )
    return f"gs://{GCS_LEADS_BUCKET}/{blob_path}"


def load_parent_leads_from_meta(*, full_sync: bool = False) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Incremental Meta → flatten. Updates GCS parents.json. Raises if Meta sync disabled."""
    if not _meta_enabled():
        raise RuntimeError("Meta sync disabled (set PARENT_LEADS_META_SYNC and PAGE_ACCESS_TOKEN)")

    client = MetaLeadClient(PAGE_ACCESS_TOKEN)
    form_names = client.form_names(PAGE_ID)
    state = _read_state()
    cursors: dict[str, str] = dict(state.get("meta_lead_cursors") or {})

    try:
        annotations_raw = read_json_object(GCS_ANNOTATIONS_OBJECT)
    except FileNotFoundError:
        annotations_raw = {"annotations": {}}
    annotations = annotations_raw.get("annotations") or {}
    if not isinstance(annotations, dict):
        annotations = {}

    all_records: list[dict[str, Any]] = []
    per_form: dict[str, Any] = {}

    for form_id in PARENT_FORM_IDS:
        cursor_ts = _parse_created_ts(cursors.get(form_id))
        since_ts = None if full_sync else (cursor_ts or _since_ts_for_form(cursors, full_sync=False))
        raw_leads = client.paginate_leads(form_id, since_ts=since_ts)
        records = [_api_lead_record(row, form_names) for row in raw_leads]
        merged = apply_annotations(records, annotations)
        all_records.extend(merged)
        max_ts = since_ts or 0
        for row in raw_leads:
            ts = _parse_created_ts(row.get("created_time"))
            if ts and ts > max_ts:
                max_ts = ts
        if max_ts:
            cursors[form_id] = datetime.fromtimestamp(max_ts, tz=timezone.utc).isoformat()
        per_form[form_id] = {"fetched": len(raw_leads), "since_ts": since_ts}

    # Merge with existing parents.json so incremental fetch does not drop older leads.
    try:
        existing_raw = read_json_object(GCS_PARENTS_OBJECT)
        existing_leads = existing_raw.get("leads") or []
    except FileNotFoundError:
        existing_leads = []

    by_id: dict[str, dict[str, Any]] = {}
    for row in existing_leads:
        lid = str(row.get("id") or "")
        if lid:
            by_id[lid] = row
    for row in all_records:
        lid = str(row.get("id") or "")
        if lid:
            by_id[lid] = row

    merged_leads = sorted(
        by_id.values(),
        key=lambda r: r.get("created_time") or "",
        reverse=True,
    )
    gcs_uri = _write_parents_json_to_gcs(merged_leads)

    state["meta_lead_cursors"] = cursors
    state["meta_last_sync_at"] = time.time()
    _write_state(state)

    flattened = [flatten_parent_lead(row) for row in merged_leads]
    meta = {
        "mode": "meta_api_direct",
        "bucket": GCS_LEADS_BUCKET,
        "parents_object": GCS_PARENTS_OBJECT,
        "gcs_uri": gcs_uri,
        "forms": per_form,
        "lead_count": len(flattened),
        "full_sync": full_sync,
    }
    return flattened, meta


def load_parent_leads_for_inbox(*, full_sync: bool = False) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Prefer direct Meta load when configured; otherwise GCS parents.json."""
    if _meta_enabled():
        try:
            return load_parent_leads_from_meta(full_sync=full_sync)
        except Exception as exc:
            logger.exception("Meta direct sync failed, falling back to GCS: %s", exc)
    from app.parent_leads.source import load_meta_parent_leads

    return load_meta_parent_leads()
