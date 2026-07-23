"""GCS pull/push for parent_leads.db."""

from __future__ import annotations

import json
import logging
import sqlite3
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from google.cloud import storage

from app.parent_leads.config import (
    GCS_LEADS_BUCKET,
    GCS_PARENT_LEADS_DB_OBJECT,
    GOOGLE_CLOUD_PROJECT,
    PARENT_LEADS_DB_PATH,
    PARENT_LEADS_GCS_STATE_PATH,
)

logger = logging.getLogger("parent-leads-gcs")

_LOCK_OBJECT = GCS_PARENT_LEADS_DB_OBJECT + ".lock"
_LOCK_MAX_AGE = 300


def _client() -> storage.Client:
    return storage.Client(project=GOOGLE_CLOUD_PROJECT)


def _state_path() -> Path:
    return PARENT_LEADS_GCS_STATE_PATH


def _read_state() -> dict[str, Any]:
    p = _state_path()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {}


def _write_state(state: dict[str, Any]) -> None:
    p = _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    merged = _read_state()
    merged.update(state)
    p.write_text(json.dumps(merged))


@contextmanager
def _gcs_lock(operation: str) -> Iterator[None]:
    client = _client()
    bucket = client.bucket(GCS_LEADS_BUCKET)
    lock_blob = bucket.blob(_LOCK_OBJECT)

    now = time.time()
    if lock_blob.exists():
        lock_blob.reload()
        age = now - lock_blob.updated.timestamp()
        if age < _LOCK_MAX_AGE:
            raise RuntimeError(f"GCS lock held for {age:.0f}s, max {_LOCK_MAX_AGE}s")
        logger.warning("Stale lock detected (%.0fs), overwriting", age)

    lock_blob.upload_from_string(f"{operation}:{now}")
    try:
        yield
    finally:
        try:
            lock_blob.delete()
        except Exception:
            pass


def pull_db() -> dict[str, Any]:
    """Download parent_leads.db from GCS."""
    client = _client()
    bucket = client.bucket(GCS_LEADS_BUCKET)
    blob = bucket.blob(GCS_PARENT_LEADS_DB_OBJECT)

    if not blob.exists():
        logger.info("No parent_leads.db in GCS, starting fresh")
        return {"status": "not_found"}

    PARENT_LEADS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(str(PARENT_LEADS_DB_PATH))

    from app.parent_leads.agent_secrets import apply_secrets_to_db

    apply_secrets_to_db(PARENT_LEADS_DB_PATH)

    blob.reload()
    gen = blob.generation
    _write_state({"generation": gen, "pulled_at": time.time()})
    logger.info("Pulled parent_leads.db from GCS (generation=%s)", gen)
    return {"status": "ok", "generation": gen}


def _merge_remote_password_plain_into_local(local_path: Path) -> None:
    """If local agents lack password_plain, keep values from GCS copy (avoid wipe on push)."""
    client = _client()
    bucket = client.bucket(GCS_LEADS_BUCKET)
    blob = bucket.blob(GCS_PARENT_LEADS_DB_OBJECT)
    if not blob.exists() or not local_path.exists():
        return
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        blob.download_to_filename(tmp.name)
        remote = sqlite3.connect(tmp.name)
        try:
            try:
                rows = remote.execute(
                    """
                    SELECT id, password_plain FROM agents
                    WHERE password_plain IS NOT NULL AND trim(password_plain) != ''
                    """
                ).fetchall()
            except sqlite3.OperationalError:
                return
        finally:
            remote.close()
    if not rows:
        return
    local = sqlite3.connect(local_path)
    try:
        for agent_id, plain in rows:
            local.execute(
                """
                UPDATE agents SET password_plain = ?
                WHERE id = ? AND (password_plain IS NULL OR trim(password_plain) = '')
                """,
                (plain, agent_id),
            )
        local.commit()
    finally:
        local.close()


def push_db() -> dict[str, Any]:
    """Upload parent_leads.db to GCS with lock."""
    if not PARENT_LEADS_DB_PATH.exists():
        return {"status": "no_local_db"}

    _merge_remote_password_plain_into_local(PARENT_LEADS_DB_PATH)

    from app.parent_leads.agent_secrets import sync_secrets_from_db

    sync_secrets_from_db(PARENT_LEADS_DB_PATH)

    with _gcs_lock("push"):
        client = _client()
        bucket = client.bucket(GCS_LEADS_BUCKET)
        blob = bucket.blob(GCS_PARENT_LEADS_DB_OBJECT)

        blob.upload_from_filename(str(PARENT_LEADS_DB_PATH))
        blob.reload()
        gen = blob.generation
        _write_state({"generation": gen, "pushed_at": time.time()})
        logger.info("Pushed parent_leads.db to GCS (generation=%s)", gen)
        return {"status": "ok", "generation": gen}


def ensure_local_db() -> None:
    """Ensure local parent_leads.db directory exists."""
    PARENT_LEADS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
