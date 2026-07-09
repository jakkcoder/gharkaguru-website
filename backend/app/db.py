from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import DB_PATH, DATA_DIR

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
  phone TEXT PRIMARY KEY,
  role TEXT NOT NULL,
  created_at TEXT NOT NULL,
  last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  phone TEXT NOT NULL,
  role TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS teacher_applications (
  reference_id TEXT PRIMARY KEY,
  phone TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  profile_completion_percent INTEGER NOT NULL DEFAULT 0,
  data_json TEXT NOT NULL DEFAULT '{}',
  idempotency_key TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_idem
  ON teacher_applications(idempotency_key)
  WHERE idempotency_key IS NOT NULL AND TRIM(idempotency_key) != '';

CREATE TABLE IF NOT EXISTS inquiries (
  inquiry_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  contact_phone TEXT NOT NULL,
  tutor_id TEXT,
  class_level TEXT,
  subject TEXT,
  message TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS enquiries (
  id TEXT PRIMARY KEY,
  phone TEXT,
  tutor_id TEXT,
  tutor_name TEXT,
  subject TEXT,
  message TEXT,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def connect(*, read_only: bool = False) -> sqlite3.Connection:
    ensure_data_dir()
    if read_only and DB_PATH.exists():
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: Path | None = None) -> None:
    target = path or DB_PATH
    ensure_data_dir()
    conn = sqlite3.connect(target)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def new_token() -> str:
    return f"tn_{uuid.uuid4().hex}"


def new_reference_id() -> str:
    year = datetime.now(timezone.utc).year
    return f"TUT-APP-{year}-{uuid.uuid4().hex[:8].upper()}"


def new_inquiry_id() -> str:
    year = datetime.now(timezone.utc).year
    return f"INQ-{year}-{uuid.uuid4().hex[:8].upper()}"


def new_enquiry_id() -> str:
    year = datetime.now(timezone.utc).year
    return f"ENQ-{year}-{uuid.uuid4().hex[:8].upper()}"


def estimate_completion(data: dict[str, Any]) -> int:
    keys = [
        "fullName",
        "email",
        "location",
        "subjectsTaught",
        "yearsTeaching",
        "bio",
        "teachingMode",
        "availability",
    ]
    filled = 0
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        filled += 1
    return int(round(100 * filled / len(keys)))


def dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def loads(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}
