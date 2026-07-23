"""GCS pull/push for finalized_deals.db (separate from website.db)."""

from __future__ import annotations

import json
import os
import socket
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

from google.api_core import exceptions as gcp_exceptions
from google.cloud import storage

from app.config import (
    FINALIZED_DEALS_DB_GCS,
    FINALIZED_DEALS_GCS_STATE_PATH,
    GCS_LOCK_MAX_AGE_SECONDS,
    GOOGLE_CLOUD_PROJECT,
)
from app.finalized_deals_db import FINALIZED_DEALS_DB_PATH, init_finalized_deals_db

BUSY_MESSAGE = "Finalized deals database is busy — try again in a moment."


class GcsBusyError(RuntimeError):
    pass


def parse_gcs_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "gs" or not parsed.netloc or not parsed.path.lstrip("/"):
        raise ValueError(f"Invalid GCS URI: {uri}")
    return parsed.netloc, parsed.path.lstrip("/")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_state() -> dict:
    if not FINALIZED_DEALS_GCS_STATE_PATH.exists():
        return {}
    return json.loads(FINALIZED_DEALS_GCS_STATE_PATH.read_text(encoding="utf-8"))


def _save_state(state: dict) -> None:
    FINALIZED_DEALS_GCS_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FINALIZED_DEALS_GCS_STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


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


def _acquire_lock(client: storage.Client, bucket: str, blob_name: str, operation: str) -> storage.Blob:
    lock_path = f"{blob_name}.lock"
    lock = client.bucket(bucket).blob(lock_path)
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
            lock.upload_from_string(payload, content_type="application/json", if_generation_match=0)
            return lock
        raise GcsBusyError(BUSY_MESSAGE) from None


def _release_lock(lock: storage.Blob) -> None:
    try:
        lock.reload()
        lock.delete(if_generation_match=lock.generation)
    except (gcp_exceptions.NotFound, gcp_exceptions.PreconditionFailed):
        return


@contextmanager
def finalized_deals_gcs_lock(operation: str) -> Iterator[None]:
    bucket, blob = parse_gcs_uri(FINALIZED_DEALS_DB_GCS)
    client = _client()
    lock = _acquire_lock(client, bucket, blob, operation)
    try:
        yield
    finally:
        _release_lock(lock)


def pull_finalized_deals_db() -> dict:
    bucket, blob_name = parse_gcs_uri(FINALIZED_DEALS_DB_GCS)
    FINALIZED_DEALS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with finalized_deals_gcs_lock("pull"):
        client = _client()
        blob = client.bucket(bucket).blob(blob_name)
        if not blob.exists():
            init_finalized_deals_db(FINALIZED_DEALS_DB_PATH)
            blob.upload_from_filename(str(FINALIZED_DEALS_DB_PATH))
            blob.reload()
        else:
            blob.reload()
            blob.download_to_filename(str(FINALIZED_DEALS_DB_PATH))
            init_finalized_deals_db(FINALIZED_DEALS_DB_PATH)

        state = {
            "generation": blob.generation,
            "updated": blob.updated.isoformat() if blob.updated else None,
            "synced_at": _now_iso(),
            "uri": FINALIZED_DEALS_DB_GCS,
        }
        _save_state(state)
        return state


def push_finalized_deals_db() -> dict:
    if not FINALIZED_DEALS_DB_PATH.exists():
        init_finalized_deals_db(FINALIZED_DEALS_DB_PATH)

    bucket, blob_name = parse_gcs_uri(FINALIZED_DEALS_DB_GCS)
    with finalized_deals_gcs_lock("push"):
        client = _client()
        blob = client.bucket(bucket).blob(blob_name)
        state = _load_state()
        generation = state.get("generation")

        if blob.exists():
            blob.reload()
            remote_generation = blob.generation
            blob.upload_from_filename(
                str(FINALIZED_DEALS_DB_PATH),
                if_generation_match=remote_generation,
            )
        else:
            blob.upload_from_filename(str(FINALIZED_DEALS_DB_PATH), if_generation_match=0)

        blob.reload()
        new_state = {
            "generation": blob.generation,
            "updated": blob.updated.isoformat() if blob.updated else None,
            "synced_at": _now_iso(),
            "uri": FINALIZED_DEALS_DB_GCS,
        }
        _save_state(new_state)
        return new_state


def ensure_local_finalized_deals_db() -> None:
    if FINALIZED_DEALS_DB_PATH.exists():
        init_finalized_deals_db(FINALIZED_DEALS_DB_PATH)
        return
    try:
        pull_finalized_deals_db()
    except Exception:
        init_finalized_deals_db(FINALIZED_DEALS_DB_PATH)
