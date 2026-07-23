from __future__ import annotations

import sqlite3
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from app.config import DATA_DIR

FINALIZED_DEALS_DB_PATH = DATA_DIR / "finalized_deals.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS finalized_deals (
  id TEXT PRIMARY KEY,
  parent_name TEXT NOT NULL DEFAULT '',
  parent_phone TEXT NOT NULL DEFAULT '',
  parent_class TEXT NOT NULL DEFAULT '',
  parent_location TEXT NOT NULL DEFAULT '',
  parent_mode TEXT NOT NULL DEFAULT '',
  teacher_name TEXT NOT NULL DEFAULT '',
  teacher_phone TEXT NOT NULL DEFAULT '',
  teacher_subject TEXT NOT NULL DEFAULT '',
  teacher_notes TEXT NOT NULL DEFAULT '',
  finalized_amount REAL,
  class_start_date TEXT NOT NULL,
  submitted_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  deleted_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_finalized_deals_start
  ON finalized_deals(class_start_date);
CREATE INDEX IF NOT EXISTS idx_finalized_deals_deleted
  ON finalized_deals(deleted_at);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def init_finalized_deals_db(path: Path | None = None) -> None:
    target = path or FINALIZED_DEALS_DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


def connect(*, read_only: bool = False) -> sqlite3.Connection:
    init_finalized_deals_db()
    if read_only and FINALIZED_DEALS_DB_PATH.exists():
        conn = sqlite3.connect(f"file:{FINALIZED_DEALS_DB_PATH}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(FINALIZED_DEALS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def new_deal_id() -> str:
    return f"fd-{uuid.uuid4().hex[:12]}"


def compute_aging_days(class_start_date: str) -> int | None:
    if not class_start_date:
        return None
    try:
        start = date.fromisoformat(class_start_date[:10])
    except ValueError:
        return None
    return (date.today() - start).days


def aging_label(days: int | None) -> str:
    if days is None:
        return "—"
    if days < 0:
        return f"Starts in {-days} day(s)"
    if days == 0:
        return "Starts today"
    return f"{days} day(s)"


def list_deals(*, include_deleted: bool = False) -> list[dict[str, Any]]:
    with connect(read_only=True) as conn:
        if include_deleted:
            rows = conn.execute(
                """
                SELECT * FROM finalized_deals
                ORDER BY class_start_date DESC, submitted_at DESC
                """
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM finalized_deals
                WHERE deleted_at IS NULL
                ORDER BY class_start_date DESC, submitted_at DESC
                """
            ).fetchall()
    out = []
    for row in rows:
        d = row_to_dict(row) or {}
        days = compute_aging_days(d.get("class_start_date") or "")
        d["aging_days"] = days
        d["aging_label"] = aging_label(days)
        out.append(d)
    return out


def get_deal(deal_id: str) -> dict[str, Any] | None:
    with connect(read_only=True) as conn:
        row = conn.execute(
            "SELECT * FROM finalized_deals WHERE id = ? AND deleted_at IS NULL",
            (deal_id,),
        ).fetchone()
    if not row:
        return None
    d = row_to_dict(row) or {}
    days = compute_aging_days(d.get("class_start_date") or "")
    d["aging_days"] = days
    d["aging_label"] = aging_label(days)
    return d


def insert_deal(fields: dict[str, Any]) -> dict[str, Any]:
    deal_id = new_deal_id()
    ts = now_iso()
    amount = fields.get("finalized_amount")
    if amount == "" or amount is None:
        amount_val = None
    else:
        try:
            amount_val = float(amount)
        except (TypeError, ValueError):
            amount_val = None

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO finalized_deals (
              id, parent_name, parent_phone, parent_class, parent_location, parent_mode,
              teacher_name, teacher_phone, teacher_subject, teacher_notes,
              finalized_amount, class_start_date, submitted_at, updated_at, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                deal_id,
                fields.get("parent_name", "").strip(),
                fields.get("parent_phone", "").strip(),
                fields.get("parent_class", "").strip(),
                fields.get("parent_location", "").strip(),
                fields.get("parent_mode", "").strip(),
                fields.get("teacher_name", "").strip(),
                fields.get("teacher_phone", "").strip(),
                fields.get("teacher_subject", "").strip(),
                fields.get("teacher_notes", "").strip(),
                amount_val,
                fields.get("class_start_date", "").strip(),
                ts,
                ts,
            ),
        )
        conn.commit()
    return get_deal(deal_id) or {"id": deal_id}


def update_deal(deal_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
    existing = get_deal(deal_id)
    if not existing:
        return None
    amount = fields.get("finalized_amount")
    if amount == "" or amount is None:
        amount_val = None
    else:
        try:
            amount_val = float(amount)
        except (TypeError, ValueError):
            amount_val = existing.get("finalized_amount")

    ts = now_iso()
    with connect() as conn:
        conn.execute(
            """
            UPDATE finalized_deals SET
              parent_name = ?, parent_phone = ?, parent_class = ?,
              parent_location = ?, parent_mode = ?,
              teacher_name = ?, teacher_phone = ?, teacher_subject = ?,
              teacher_notes = ?, finalized_amount = ?,
              class_start_date = ?, updated_at = ?
            WHERE id = ? AND deleted_at IS NULL
            """,
            (
                fields.get("parent_name", "").strip(),
                fields.get("parent_phone", "").strip(),
                fields.get("parent_class", "").strip(),
                fields.get("parent_location", "").strip(),
                fields.get("parent_mode", "").strip(),
                fields.get("teacher_name", "").strip(),
                fields.get("teacher_phone", "").strip(),
                fields.get("teacher_subject", "").strip(),
                fields.get("teacher_notes", "").strip(),
                amount_val,
                fields.get("class_start_date", "").strip(),
                ts,
                deal_id,
            ),
        )
        conn.commit()
    return get_deal(deal_id)


def soft_delete_deal(deal_id: str) -> bool:
    ts = now_iso()
    with connect() as conn:
        cur = conn.execute(
            """
            UPDATE finalized_deals SET deleted_at = ?, updated_at = ?
            WHERE id = ? AND deleted_at IS NULL
            """,
            (ts, ts, deal_id),
        )
        conn.commit()
        return cur.rowcount > 0
