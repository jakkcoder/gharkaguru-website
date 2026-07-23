"""Local SQLite inbox for unfilled parent leads + agent assignments."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.parent_leads.config import PARENT_LEADS_DB_PATH as LOCAL_DB_PATH, STAGE_ASSIGNED, STAGE_UNASSIGNED

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS agents (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  traffic_percent INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS parent_leads (
  lead_id TEXT PRIMARY KEY,
  form_id TEXT NOT NULL DEFAULT '',
  form_name TEXT NOT NULL DEFAULT '',
  created_time TEXT NOT NULL DEFAULT '',
  parent_name TEXT NOT NULL DEFAULT '',
  parent_phone TEXT NOT NULL DEFAULT '',
  student_class TEXT NOT NULL DEFAULT '',
  location TEXT NOT NULL DEFAULT '',
  mode TEXT NOT NULL DEFAULT '',
  budget TEXT NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '',
  meta_status TEXT NOT NULL DEFAULT '',
  platform TEXT NOT NULL DEFAULT '',
  fields_json TEXT NOT NULL DEFAULT '{}',
  fill_status TEXT NOT NULL DEFAULT 'unfilled',
  assigned_agent_id TEXT,
  pipeline_stage TEXT NOT NULL DEFAULT 'unassigned',
  pulled_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  filled_at TEXT,
  FOREIGN KEY (assigned_agent_id) REFERENCES agents(id)
);

CREATE INDEX IF NOT EXISTS idx_parent_leads_fill
  ON parent_leads(fill_status);
CREATE INDEX IF NOT EXISTS idx_parent_leads_created
  ON parent_leads(created_time);
CREATE INDEX IF NOT EXISTS idx_parent_leads_phone
  ON parent_leads(parent_phone);
CREATE INDEX IF NOT EXISTS idx_agents_active
  ON agents(is_active);
"""

INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_parent_leads_agent_stage
  ON parent_leads(assigned_agent_id, pipeline_stage);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _migrate_agents(conn: sqlite3.Connection) -> None:
    cols = _table_columns(conn, "agents")
    if "password_plain" not in cols:
        conn.execute("ALTER TABLE agents ADD COLUMN password_plain TEXT NOT NULL DEFAULT ''")


def _migrate_parent_leads(conn: sqlite3.Connection) -> None:
    cols = _table_columns(conn, "parent_leads")
    if "assigned_agent_id" not in cols:
        conn.execute("ALTER TABLE parent_leads ADD COLUMN assigned_agent_id TEXT")
    if "pipeline_stage" not in cols:
        conn.execute(
            "ALTER TABLE parent_leads ADD COLUMN pipeline_stage TEXT NOT NULL DEFAULT 'unassigned'"
        )
    if "is_junk" not in cols:
        conn.execute("ALTER TABLE parent_leads ADD COLUMN is_junk INTEGER NOT NULL DEFAULT 0")
    if "teacher_phone" not in cols:
        conn.execute("ALTER TABLE parent_leads ADD COLUMN teacher_phone TEXT NOT NULL DEFAULT ''")
    if "subject" not in cols:
        conn.execute("ALTER TABLE parent_leads ADD COLUMN subject TEXT NOT NULL DEFAULT ''")
    if "student_name" not in cols:
        conn.execute("ALTER TABLE parent_leads ADD COLUMN student_name TEXT NOT NULL DEFAULT ''")
    conn.execute(
        """
        UPDATE parent_leads
        SET pipeline_stage = 'unassigned'
        WHERE pipeline_stage IS NULL OR pipeline_stage = ''
        """
    )


LEAD_EVENTS_SQL = """
CREATE TABLE IF NOT EXISTS lead_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lead_id TEXT NOT NULL,
  agent_id TEXT,
  action TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lead_events_created
  ON lead_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_lead_events_lead
  ON lead_events(lead_id);
"""


def _ensure_lead_events(conn: sqlite3.Connection) -> None:
    conn.executescript(LEAD_EVENTS_SQL)


def log_lead_event(
    lead_id: str,
    action: str,
    *,
    agent_id: str | None = None,
    detail: str = "",
    path: Path | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Record a brief agent/admin action for Today's activity."""
    ts = now_iso()
    detail_s = (detail or "").strip()[:240]
    if conn is not None:
        conn.execute(
            """
            INSERT INTO lead_events (lead_id, agent_id, action, detail, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (lead_id, agent_id, action, detail_s, ts),
        )
        return
    with connect(path) as c:
        c.execute(
            """
            INSERT INTO lead_events (lead_id, agent_id, action, detail, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (lead_id, agent_id, action, detail_s, ts),
        )
        c.commit()


def init_db(path: Path | None = None) -> Path:
    target = path or LOCAL_DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    try:
        conn.executescript(SCHEMA_SQL)
        _migrate_agents(conn)
        _migrate_parent_leads(conn)
        _ensure_lead_events(conn)
        conn.executescript(INDEX_SQL)
        conn.commit()
    finally:
        conn.close()
    return target


def connect(path: Path | None = None) -> sqlite3.Connection:
    target = init_db(path)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def existing_lead_ids(path: Path | None = None) -> set[str]:
    with connect(path) as conn:
        rows = conn.execute("SELECT lead_id FROM parent_leads").fetchall()
    return {str(r["lead_id"]) for r in rows}


def insert_leads(rows: list[dict[str, Any]], path: Path | None = None) -> int:
    if not rows:
        return 0
    ts = now_iso()
    inserted = 0
    with connect(path) as conn:
        for row in rows:
            fields = row.get("fields_json") or {}
            if not isinstance(fields, str):
                fields = json.dumps(fields, ensure_ascii=False)
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO parent_leads (
                  lead_id, form_id, form_name, created_time,
                  parent_name, parent_phone, student_class, location, mode, budget,
                  note, meta_status, platform, fields_json,
                  fill_status, assigned_agent_id, pipeline_stage,
                  pulled_at, updated_at, filled_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'unfilled', NULL, ?, ?, ?, NULL)
                """,
                (
                    row.get("lead_id") or "",
                    row.get("form_id") or "",
                    row.get("form_name") or "",
                    row.get("created_time") or "",
                    row.get("parent_name") or "",
                    row.get("parent_phone") or "",
                    row.get("student_class") or "",
                    row.get("location") or "",
                    row.get("mode") or "",
                    row.get("budget") or "",
                    row.get("note") or "",
                    row.get("status") or "",
                    row.get("platform") or "",
                    fields,
                    STAGE_UNASSIGNED,
                    ts,
                    ts,
                ),
            )
            inserted += cur.rowcount
        conn.commit()
    return inserted


def refresh_contact_fields_from_meta(
    rows: list[dict[str, Any]], path: Path | None = None
) -> int:
    """Update parent_name/phone/meta fields on leads already in the inbox."""
    if not rows:
        return 0
    ts = now_iso()
    updated = 0
    with connect(path) as conn:
        for row in rows:
            lead_id = row.get("lead_id") or ""
            if not lead_id:
                continue
            fields = row.get("fields_json") or {}
            if not isinstance(fields, str):
                fields = json.dumps(fields, ensure_ascii=False)
            cur = conn.execute(
                """
                UPDATE parent_leads SET
                  parent_name = CASE WHEN ? != '' THEN ? ELSE parent_name END,
                  parent_phone = CASE WHEN ? != '' THEN ? ELSE parent_phone END,
                  student_class = CASE WHEN ? != '' THEN ? ELSE student_class END,
                  location = CASE WHEN ? != '' THEN ? ELSE location END,
                  mode = CASE WHEN ? != '' THEN ? ELSE mode END,
                  budget = CASE WHEN ? != '' THEN ? ELSE budget END,
                  note = CASE WHEN ? != '' THEN ? ELSE note END,
                  form_name = CASE WHEN ? != '' THEN ? ELSE form_name END,
                  fields_json = ?,
                  updated_at = ?
                WHERE lead_id = ?
                """,
                (
                    row.get("parent_name") or "",
                    row.get("parent_name") or "",
                    row.get("parent_phone") or "",
                    row.get("parent_phone") or "",
                    row.get("student_class") or "",
                    row.get("student_class") or "",
                    row.get("location") or "",
                    row.get("location") or "",
                    row.get("mode") or "",
                    row.get("mode") or "",
                    row.get("budget") or "",
                    row.get("budget") or "",
                    row.get("note") or "",
                    row.get("note") or "",
                    row.get("form_name") or "",
                    row.get("form_name") or "",
                    fields,
                    ts,
                    lead_id,
                ),
            )
            updated += cur.rowcount
        conn.commit()
    return updated


def counts(path: Path | None = None) -> dict[str, int]:
    with connect(path) as conn:
        total = conn.execute("SELECT COUNT(*) AS n FROM parent_leads").fetchone()["n"]
        unfilled = conn.execute(
            "SELECT COUNT(*) AS n FROM parent_leads WHERE fill_status = 'unfilled'"
        ).fetchone()["n"]
        filled = conn.execute(
            "SELECT COUNT(*) AS n FROM parent_leads WHERE fill_status = 'filled'"
        ).fetchone()["n"]
        unassigned = conn.execute(
            """
            SELECT COUNT(*) AS n FROM parent_leads
            WHERE assigned_agent_id IS NULL OR pipeline_stage = 'unassigned'
            """
        ).fetchone()["n"]
    return {
        "total": int(total),
        "unfilled": int(unfilled),
        "filled": int(filled),
        "unassigned": int(unassigned),
    }


def list_unfilled(limit: int = 20, path: Path | None = None) -> list[dict[str, Any]]:
    with connect(path) as conn:
        rows = conn.execute(
            """
            SELECT lead_id, parent_name, parent_phone, created_time, form_name, fill_status,
                   pipeline_stage, assigned_agent_id
            FROM parent_leads
            WHERE fill_status = 'unfilled'
            ORDER BY created_time DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_leads_for_agent(
    agent_id: str,
    stage: str,
    *,
    limit: int = 500,
    path: Path | None = None,
) -> list[dict[str, Any]]:
    from app.parent_leads.config import TAB_JUNK

    with connect(path) as conn:
        if stage == TAB_JUNK:
            rows = conn.execute(
                """
                SELECT lead_id, parent_name, parent_phone, created_time, form_name,
                       student_name, student_class, subject, location, mode, budget, note,
                       teacher_phone, fill_status, pipeline_stage, updated_at, is_junk
                FROM parent_leads
                WHERE assigned_agent_id = ? AND is_junk = 1
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (agent_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT lead_id, parent_name, parent_phone, created_time, form_name,
                       student_name, student_class, subject, location, mode, budget, note,
                       teacher_phone, fill_status, pipeline_stage, updated_at, is_junk
                FROM parent_leads
                WHERE assigned_agent_id = ? AND pipeline_stage = ? AND is_junk = 0
                ORDER BY created_time DESC
                LIMIT ?
                """,
                (agent_id, stage, limit),
            ).fetchall()
    return [dict(r) for r in rows]


def stage_counts_for_agent(agent_id: str, path: Path | None = None) -> dict[str, int]:
    from app.parent_leads.config import STAGE_ORDER, TAB_JUNK

    with connect(path) as conn:
        out: dict[str, int] = {}
        for stage in STAGE_ORDER:
            n = conn.execute(
                """
                SELECT COUNT(*) AS n FROM parent_leads
                WHERE assigned_agent_id = ? AND pipeline_stage = ? AND is_junk = 0
                """,
                (agent_id, stage),
            ).fetchone()["n"]
            out[stage] = int(n)
        junk_n = conn.execute(
            """
            SELECT COUNT(*) AS n FROM parent_leads
            WHERE assigned_agent_id = ? AND is_junk = 1
            """,
            (agent_id,),
        ).fetchone()["n"]
        out[TAB_JUNK] = int(junk_n)
    return out


def get_lead(lead_id: str, path: Path | None = None) -> dict[str, Any] | None:
    with connect(path) as conn:
        row = conn.execute(
            "SELECT * FROM parent_leads WHERE lead_id = ?",
            (lead_id,),
        ).fetchone()
    return row_to_dict(row)


def advance_lead_stage(
    lead_id: str,
    agent_id: str,
    *,
    path: Path | None = None,
) -> dict[str, Any] | None:
    from app.parent_leads.config import NEXT_STAGE, STAGE_LABELS

    lead = get_lead(lead_id, path)
    if not lead:
        return None
    if lead.get("is_junk"):
        return None
    if lead.get("assigned_agent_id") != agent_id:
        return None
    current = lead.get("pipeline_stage") or ""
    nxt = NEXT_STAGE.get(current)
    if not nxt:
        return None
    ts = now_iso()
    with connect(path) as conn:
        conn.execute(
            """
            UPDATE parent_leads SET pipeline_stage = ?, updated_at = ?
            WHERE lead_id = ? AND assigned_agent_id = ?
            """,
            (nxt, ts, lead_id, agent_id),
        )
        log_lead_event(
            lead_id,
            "advance",
            agent_id=agent_id,
            detail=f"{STAGE_LABELS.get(current, current)} → {STAGE_LABELS.get(nxt, nxt)}",
            conn=conn,
        )
        conn.commit()
    return get_lead(lead_id, path)


def move_back_lead_stage(
    lead_id: str,
    agent_id: str,
    *,
    path: Path | None = None,
) -> dict[str, Any] | None:
    from app.parent_leads.config import PREV_STAGE, STAGE_LABELS

    lead = get_lead(lead_id, path)
    if not lead:
        return None
    if lead.get("is_junk"):
        return None
    if lead.get("assigned_agent_id") != agent_id:
        return None
    current = lead.get("pipeline_stage") or ""
    prev = PREV_STAGE.get(current)
    if not prev:
        return None
    ts = now_iso()
    with connect(path) as conn:
        conn.execute(
            """
            UPDATE parent_leads SET pipeline_stage = ?, updated_at = ?
            WHERE lead_id = ? AND assigned_agent_id = ?
            """,
            (prev, ts, lead_id, agent_id),
        )
        log_lead_event(
            lead_id,
            "move_back",
            agent_id=agent_id,
            detail=f"{STAGE_LABELS.get(current, current)} → {STAGE_LABELS.get(prev, prev)}",
            conn=conn,
        )
        conn.commit()
    return get_lead(lead_id, path)


def unassigned_lead_ids(path: Path | None = None) -> list[str]:
    with connect(path) as conn:
        rows = conn.execute(
            """
            SELECT lead_id FROM parent_leads
            WHERE assigned_agent_id IS NULL
               OR pipeline_stage = 'unassigned'
            ORDER BY created_time ASC, lead_id ASC
            """
        ).fetchall()
    return [str(r["lead_id"]) for r in rows]


def purge_leads_before_start_date(path: Path | None = None) -> int:
    """Remove inbox rows with created_time strictly before LEADS_START_DATE."""
    from app.parent_leads.config import LEADS_START_DATE

    if not LEADS_START_DATE:
        return 0
    with connect(path) as conn:
        cur = conn.execute(
            """
            DELETE FROM parent_leads
            WHERE created_time = ''
               OR substr(created_time, 1, 10) < ?
            """,
            (LEADS_START_DATE,),
        )
        conn.commit()
        return int(cur.rowcount)


def _agent_owns_lead(lead_id: str, agent_id: str, path: Path | None = None) -> dict[str, Any] | None:
    lead = get_lead(lead_id, path)
    if not lead or lead.get("assigned_agent_id") != agent_id:
        return None
    return lead


def update_lead_fill(
    lead_id: str,
    agent_id: str,
    *,
    parent_name: str = "",
    student_name: str = "",
    student_class: str = "",
    subject: str = "",
    location: str = "",
    mode: str = "",
    budget: str = "",
    note: str = "",
    path: Path | None = None,
) -> dict[str, Any] | None:
    if not _agent_owns_lead(lead_id, agent_id, path):
        return None
    ts = now_iso()
    parent_name_s = parent_name.strip()
    student_name_s = student_name.strip()
    student_class_s = student_class.strip()
    subject_s = subject.strip()
    location_s = location.strip()
    mode_s = mode.strip()
    budget_s = budget.strip()
    note_s = note.strip()
    filled = any(
        (
            parent_name_s,
            student_name_s,
            student_class_s,
            subject_s,
            location_s,
            mode_s,
            budget_s,
            note_s,
        )
    )
    bits = [
        x
        for x in (
            parent_name_s and f"name={parent_name_s}",
            student_class_s and f"class={student_class_s}",
            subject_s and f"subj={subject_s}",
            location_s and f"addr={location_s}",
        )
        if x
    ]
    detail = ", ".join(bits) or "details updated"
    with connect(path) as conn:
        conn.execute(
            """
            UPDATE parent_leads
            SET parent_name = ?, student_name = ?, student_class = ?, subject = ?,
                location = ?, mode = ?, budget = ?, note = ?,
                fill_status = ?, filled_at = COALESCE(filled_at, ?), updated_at = ?
            WHERE lead_id = ? AND assigned_agent_id = ?
            """,
            (
                parent_name_s,
                student_name_s,
                student_class_s,
                subject_s,
                location_s,
                mode_s,
                budget_s,
                note_s,
                "filled" if filled else "unfilled",
                ts if filled else None,
                ts,
                lead_id,
                agent_id,
            ),
        )
        log_lead_event(
            lead_id,
            "fill",
            agent_id=agent_id,
            detail=detail,
            conn=conn,
        )
        conn.commit()
    return get_lead(lead_id, path)


def mark_lead_junk(lead_id: str, agent_id: str, *, path: Path | None = None) -> dict[str, Any] | None:
    if not _agent_owns_lead(lead_id, agent_id, path):
        return None
    ts = now_iso()
    with connect(path) as conn:
        conn.execute(
            """
            UPDATE parent_leads SET is_junk = 1, updated_at = ?
            WHERE lead_id = ? AND assigned_agent_id = ?
            """,
            (ts, lead_id, agent_id),
        )
        log_lead_event(lead_id, "junk", agent_id=agent_id, detail="marked junk", conn=conn)
        conn.commit()
    return get_lead(lead_id, path)


def promote_lead_with_teacher(
    lead_id: str,
    agent_id: str,
    teacher_phone: str,
    *,
    path: Path | None = None,
) -> dict[str, Any] | None:
    from app.parent_leads.config import STAGE_CLASS

    if not _agent_owns_lead(lead_id, agent_id, path):
        return None
    phone = teacher_phone.strip()
    if not phone:
        return None
    ts = now_iso()
    with connect(path) as conn:
        conn.execute(
            """
            UPDATE parent_leads
            SET teacher_phone = ?, fill_status = 'filled', filled_at = COALESCE(filled_at, ?),
                pipeline_stage = ?, is_junk = 0, updated_at = ?
            WHERE lead_id = ? AND assigned_agent_id = ?
            """,
            (phone, ts, STAGE_CLASS, ts, lead_id, agent_id),
        )
        log_lead_event(
            lead_id,
            "promote",
            agent_id=agent_id,
            detail=f"teacher={phone}",
            conn=conn,
        )
        conn.commit()
    return get_lead(lead_id, path)


def list_today_events(
    *,
    day_start_utc: str,
    day_end_utc: str,
    limit: int = 40,
    path: Path | None = None,
) -> list[dict[str, Any]]:
    """Brief activity feed for Admin Today (IST day bounds as UTC ISO)."""
    with connect(path) as conn:
        rows = conn.execute(
            """
            SELECT e.id, e.lead_id, e.agent_id, e.action, e.detail, e.created_at,
                   a.name AS agent_name, a.email AS agent_email,
                   pl.parent_phone, pl.parent_name
            FROM lead_events e
            LEFT JOIN agents a ON a.id = e.agent_id
            LEFT JOIN parent_leads pl ON pl.lead_id = e.lead_id
            WHERE e.created_at >= ? AND e.created_at < ?
            ORDER BY e.created_at DESC
            LIMIT ?
            """,
            (day_start_utc, day_end_utc, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def admin_list_leads(
    *,
    from_agent_id: str | None = None,
    include_junk: bool = False,
    limit: int = 500,
    path: Path | None = None,
) -> list[dict[str, Any]]:
    clauses = ["1=1"]
    params: list[Any] = []
    if not include_junk:
        clauses.append("pl.is_junk = 0")
    if from_agent_id:
        clauses.append("pl.assigned_agent_id = ?")
        params.append(from_agent_id)
    where = " AND ".join(clauses)
    params.append(limit)
    with connect(path) as conn:
        rows = conn.execute(
            f"""
            SELECT pl.lead_id, pl.parent_name, pl.parent_phone, pl.pipeline_stage,
                   pl.assigned_agent_id, pl.is_junk, pl.created_time,
                   a.name AS agent_name
            FROM parent_leads pl
            LEFT JOIN agents a ON a.id = pl.assigned_agent_id
            WHERE {where}
            ORDER BY pl.created_time DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [dict(r) for r in rows]


def admin_reassign_lead(
    lead_id: str,
    to_agent_id: str,
    *,
    path: Path | None = None,
) -> dict[str, Any] | None:
    with connect(path) as conn:
        agent = conn.execute(
            "SELECT id FROM agents WHERE id = ? AND is_active = 1",
            (to_agent_id,),
        ).fetchone()
        if not agent:
            return None
        row = conn.execute(
            "SELECT lead_id, pipeline_stage, assigned_agent_id FROM parent_leads WHERE lead_id = ?",
            (lead_id,),
        ).fetchone()
        if not row:
            return None
        stage = row["pipeline_stage"] or STAGE_UNASSIGNED
        if stage == STAGE_UNASSIGNED or not row["assigned_agent_id"]:
            stage = STAGE_ASSIGNED
        ts = now_iso()
        conn.execute(
            """
            UPDATE parent_leads
            SET assigned_agent_id = ?, pipeline_stage = ?, updated_at = ?
            WHERE lead_id = ?
            """,
            (to_agent_id, stage, ts, lead_id),
        )
        conn.commit()
    return get_lead(lead_id, path)


def admin_bulk_reassign(
    from_agent_id: str,
    to_agent_id: str,
    *,
    path: Path | None = None,
) -> int:
    if from_agent_id == to_agent_id:
        return 0
    with connect(path) as conn:
        dest = conn.execute(
            "SELECT id FROM agents WHERE id = ? AND is_active = 1",
            (to_agent_id,),
        ).fetchone()
        if not dest:
            return 0
        ts = now_iso()
        cur = conn.execute(
            """
            UPDATE parent_leads
            SET assigned_agent_id = ?,
                pipeline_stage = CASE
                  WHEN pipeline_stage = ? OR assigned_agent_id IS NULL THEN ?
                  ELSE pipeline_stage
                END,
                updated_at = ?
            WHERE assigned_agent_id = ? AND is_junk = 0
            """,
            (
                to_agent_id,
                STAGE_UNASSIGNED,
                STAGE_ASSIGNED,
                ts,
                from_agent_id,
            ),
        )
        conn.commit()
        return int(cur.rowcount)
