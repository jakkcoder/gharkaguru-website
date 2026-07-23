"""Agent CRUD for parent leads portal."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from app.parent_leads.auth import hash_password, verify_password
from app.parent_leads.db import connect, now_iso, row_to_dict


def new_agent_id() -> str:
    return f"agent-{uuid.uuid4().hex[:12]}"


def list_agents(*, include_inactive: bool = True, path: Path | None = None) -> list[dict[str, Any]]:
    with connect(path) as conn:
        if include_inactive:
            rows = conn.execute(
                "SELECT * FROM agents ORDER BY is_active DESC, name ASC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM agents WHERE is_active = 1 ORDER BY name ASC"
            ).fetchall()
    return [row_to_dict(r) or {} for r in rows]


def get_agent(agent_id: str, path: Path | None = None) -> dict[str, Any] | None:
    with connect(path) as conn:
        row = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
    return row_to_dict(row)


def get_agent_by_email(email: str, path: Path | None = None) -> dict[str, Any] | None:
    with connect(path) as conn:
        row = conn.execute(
            "SELECT * FROM agents WHERE email = ? COLLATE NOCASE",
            (email.strip().lower(),),
        ).fetchone()
    return row_to_dict(row)


def authenticate_agent(email: str, password: str, path: Path | None = None) -> dict[str, Any] | None:
    agent = get_agent_by_email(email, path)
    if not agent or not agent.get("is_active"):
        return None
    if not verify_password(password, agent.get("password_hash") or ""):
        return None
    return agent


def normalized_traffic_summary(path: Path | None = None) -> list[dict[str, Any]]:
    agents = [a for a in list_agents(include_inactive=False, path=path) if int(a.get("traffic_percent") or 0) > 0]
    total = sum(int(a.get("traffic_percent") or 0) for a in agents)
    out = []
    for a in agents:
        pct = int(a.get("traffic_percent") or 0)
        norm = round(100.0 * pct / total, 1) if total else 0.0
        out.append({**a, "normalized_percent": norm})
    return out


def create_agent(
    *,
    name: str,
    email: str,
    password: str,
    traffic_percent: int,
    path: Path | None = None,
) -> dict[str, Any]:
    agent_id = new_agent_id()
    ts = now_iso()
    pct = max(0, min(100, int(traffic_percent)))
    with connect(path) as conn:
        conn.execute(
            """
            INSERT INTO agents (id, name, email, password_hash, password_plain, traffic_percent, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                agent_id,
                name.strip(),
                email.strip().lower(),
                hash_password(password),
                password,
                pct,
                ts,
                ts,
            ),
        )
        conn.commit()
    return get_agent(agent_id, path) or {"id": agent_id}


def update_agent(
    agent_id: str,
    *,
    name: str | None = None,
    email: str | None = None,
    password: str | None = None,
    traffic_percent: int | None = None,
    is_active: bool | None = None,
    path: Path | None = None,
) -> dict[str, Any] | None:
    existing = get_agent(agent_id, path)
    if not existing:
        return None
    ts = now_iso()
    fields: list[str] = []
    values: list[Any] = []
    if name is not None:
        fields.append("name = ?")
        values.append(name.strip())
    if email is not None:
        fields.append("email = ?")
        values.append(email.strip().lower())
    if password:
        fields.append("password_hash = ?")
        values.append(hash_password(password))
        fields.append("password_plain = ?")
        values.append(password)
    if traffic_percent is not None:
        fields.append("traffic_percent = ?")
        values.append(max(0, min(100, int(traffic_percent))))
    if is_active is not None:
        fields.append("is_active = ?")
        values.append(1 if is_active else 0)
    if not fields:
        return existing
    fields.append("updated_at = ?")
    values.append(ts)
    values.append(agent_id)
    with connect(path) as conn:
        conn.execute(f"UPDATE agents SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
    return get_agent(agent_id, path)


def delete_all_agents(path: Path | None = None) -> int:
    with connect(path) as conn:
        cur = conn.execute("DELETE FROM agents")
        conn.execute(
            """
            UPDATE parent_leads
            SET assigned_agent_id = NULL, pipeline_stage = 'unassigned', updated_at = ?
            WHERE assigned_agent_id IS NOT NULL
            """,
            (now_iso(),),
        )
        conn.commit()
        return cur.rowcount


def agent_lead_counts(path: Path | None = None) -> dict[str, int]:
    with connect(path) as conn:
        rows = conn.execute(
            """
            SELECT assigned_agent_id AS agent_id, COUNT(*) AS n
            FROM parent_leads
            WHERE assigned_agent_id IS NOT NULL
            GROUP BY assigned_agent_id
            """
        ).fetchall()
    return {str(r["agent_id"]): int(r["n"]) for r in rows}
