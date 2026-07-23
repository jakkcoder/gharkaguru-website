"""GCS backup of agent login passwords (admin display + recovery if SQLite plain is wiped)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from google.cloud import storage

from app.parent_leads.auth import hash_password, verify_password
from app.parent_leads.config import (
    GCS_AGENT_SECRETS_OBJECT,
    GCS_LEADS_BUCKET,
    GOOGLE_CLOUD_PROJECT,
    PARENT_LEADS_DB_PATH,
)


def _client() -> storage.Client:
    return storage.Client(project=GOOGLE_CLOUD_PROJECT)


def _blob():
    return _client().bucket(GCS_LEADS_BUCKET).blob(GCS_AGENT_SECRETS_OBJECT)


def read_secrets() -> dict[str, str]:
    blob = _blob()
    if not blob.exists():
        return {}
    try:
        data = json.loads(blob.download_as_text(encoding="utf-8"))
    except Exception:
        return {}
    agents = data.get("agents") or data
    if not isinstance(agents, dict):
        return {}
    return {str(k).strip().lower(): str(v) for k, v in agents.items() if k and v}


def write_secrets(secrets: dict[str, str]) -> None:
    payload = {
        "agents": {k: v for k, v in sorted(secrets.items()) if v},
    }
    _blob().upload_from_string(
        json.dumps(payload, indent=2, ensure_ascii=False),
        content_type="application/json",
    )


def sync_secrets_from_db(path: Path | None = None) -> dict[str, str]:
    db_path = path or PARENT_LEADS_DB_PATH
    if not db_path.exists():
        return {}
    conn = sqlite3.connect(db_path)
    try:
        try:
            rows = conn.execute(
                "SELECT email, password_plain FROM agents WHERE trim(password_plain) != ''"
            ).fetchall()
        except sqlite3.OperationalError:
            return {}
    finally:
        conn.close()
    secrets = {str(email).strip().lower(): str(plain) for email, plain in rows}
    if secrets:
        write_secrets(secrets)
    return secrets


def apply_secrets_to_db(path: Path | None = None) -> int:
    secrets = read_secrets()
    if not secrets:
        return 0
    db_path = path or PARENT_LEADS_DB_PATH
    if not db_path.exists():
        return 0
    conn = sqlite3.connect(db_path)
    try:
        updated = 0
        for email, plain in secrets.items():
            row = conn.execute(
                "SELECT id, password_hash, password_plain FROM agents WHERE lower(email) = ?",
                (email,),
            ).fetchone()
            if not row:
                continue
            agent_id, stored_hash, existing_plain = row
            if existing_plain is None or not str(existing_plain).strip():
                conn.execute(
                    "UPDATE agents SET password_plain = ? WHERE id = ?",
                    (plain, agent_id),
                )
                updated += 1
            if not verify_password(plain, stored_hash or ""):
                conn.execute(
                    "UPDATE agents SET password_hash = ?, password_plain = ? WHERE id = ?",
                    (hash_password(plain), plain, agent_id),
                )
                updated += 1
        conn.commit()
        return updated
    finally:
        conn.close()
