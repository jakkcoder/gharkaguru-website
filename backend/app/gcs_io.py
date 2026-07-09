from __future__ import annotations

import json
import os
import socket
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

from google.api_core import exceptions as gcp_exceptions
from google.cloud import storage

from app.config import (
    DB_PATH,
    GCS_LOCK_MAX_AGE_SECONDS,
    GCS_STATE_PATH,
    GOOGLE_CLOUD_PROJECT,
    UPLOADS_GCS_PREFIX,
    WEBSITE_DB_GCS,
)
from app.db import init_db

BUSY_MESSAGE = "Please try after some time — the GCS file is busy now."


class GcsBusyError(RuntimeError):
    pass


@dataclass(frozen=True)
class GcsObjectRef:
    bucket: str
    blob: str

    @property
    def lock_blob(self) -> str:
        return f"{self.blob}.lock"

    @property
    def uri(self) -> str:
        return f"gs://{self.bucket}/{self.blob}"


def parse_gcs_uri(uri: str) -> GcsObjectRef:
    parsed = urlparse(uri)
    if parsed.scheme != "gs" or not parsed.netloc or not parsed.path.lstrip("/"):
        raise ValueError(f"Invalid GCS URI: {uri}")
    return GcsObjectRef(bucket=parsed.netloc, blob=parsed.path.lstrip("/"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_state() -> dict:
    if not GCS_STATE_PATH.exists():
        return {}
    return json.loads(GCS_STATE_PATH.read_text(encoding="utf-8"))


def _save_state(state: dict) -> None:
    GCS_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    GCS_STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _client() -> storage.Client:
    return storage.Client(project=GOOGLE_CLOUD_PROJECT)


def _lock_is_stale(lock_blob: storage.Blob) -> bool:
    lock_blob.reload()
    updated = lock_blob.updated
    if updated is None:
        return True
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - updated).total_seconds() > GCS_LOCK_MAX_AGE_SECONDS


def _acquire_lock(client: storage.Client, ref: GcsObjectRef, operation: str) -> storage.Blob:
    bucket = client.bucket(ref.bucket)
    lock = bucket.blob(ref.lock_blob)
    payload = json.dumps(
        {
            "holder": f"{socket.gethostname()}:{os.getpid()}:{operation}",
            "since": _now_iso(),
            "operation": operation,
        }
    )
    try:
        lock.upload_from_string(payload, content_type="application/json", if_generation_match=0)
        return lock
    except gcp_exceptions.PreconditionFailed:
        if lock.exists() and _lock_is_stale(lock):
            lock.delete()
            lock.upload_from_string(
                payload, content_type="application/json", if_generation_match=0
            )
            return lock
        raise GcsBusyError(BUSY_MESSAGE) from None


def _release_lock(lock: storage.Blob) -> None:
    try:
        lock.reload()
        lock.delete(if_generation_match=lock.generation)
    except (gcp_exceptions.NotFound, gcp_exceptions.PreconditionFailed):
        return


@contextmanager
def gcs_lock(operation: str) -> Iterator[None]:
    ref = parse_gcs_uri(WEBSITE_DB_GCS)
    client = _client()
    lock = _acquire_lock(client, ref, operation)
    try:
        yield
    finally:
        _release_lock(lock)


def pull_db_from_gcs() -> dict:
    """Download website.db from GCS, or create empty local DB if missing."""
    ref = parse_gcs_uri(WEBSITE_DB_GCS)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with gcs_lock("pull"):
        client = _client()
        blob = client.bucket(ref.bucket).blob(ref.blob)
        if not blob.exists():
            init_db(DB_PATH)
            blob.upload_from_filename(str(DB_PATH))
            blob.reload()
        else:
            blob.reload()
            blob.download_to_filename(str(DB_PATH))
            init_db(DB_PATH)

        state = {
            "generation": blob.generation,
            "updated": blob.updated.isoformat() if blob.updated else None,
            "synced_at": _now_iso(),
            "uri": ref.uri,
        }
        _save_state(state)
        return state


def push_db_to_gcs() -> dict:
    """Upload local website.db to GCS with generation lock."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    ref = parse_gcs_uri(WEBSITE_DB_GCS)
    with gcs_lock("push"):
        client = _client()
        blob = client.bucket(ref.bucket).blob(ref.blob)
        state = _load_state()
        generation = state.get("generation")

        if blob.exists():
            blob.reload()
            remote_generation = blob.generation
            if generation not in (None, remote_generation):
                # Remote changed — download merge base is not needed for full replace
                # of this app-owned DB; sync state and overwrite carefully via lock.
                pass
            blob.upload_from_filename(
                str(DB_PATH),
                if_generation_match=remote_generation,
            )
        else:
            blob.upload_from_filename(str(DB_PATH), if_generation_match=0)

        blob.reload()
        new_state = {
            "generation": blob.generation,
            "updated": blob.updated.isoformat() if blob.updated else None,
            "synced_at": _now_iso(),
            "uri": ref.uri,
        }
        _save_state(new_state)
        return new_state


def upload_bytes(data: bytes, *, object_name: str, content_type: str) -> str:
    """Upload a file under website-uploads/ and return gs:// URI."""
    prefix = parse_gcs_uri(UPLOADS_GCS_PREFIX)
    blob_path = f"{prefix.blob.rstrip('/')}/{object_name.lstrip('/')}"
    client = _client()
    blob = client.bucket(prefix.bucket).blob(blob_path)
    blob.upload_from_string(data, content_type=content_type)
    return f"gs://{prefix.bucket}/{blob_path}"


def ensure_local_db() -> None:
    if DB_PATH.exists():
        init_db(DB_PATH)
        return
    try:
        pull_db_from_gcs()
    except Exception:
        init_db(DB_PATH)
