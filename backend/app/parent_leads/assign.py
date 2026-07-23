"""Assign unassigned parent leads to agents by normalized traffic weights."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.parent_leads.config import STAGE_ASSIGNED, STAGE_UNASSIGNED
from app.parent_leads.db import connect, now_iso, unassigned_lead_ids


def _active_agents(conn) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, name, email, traffic_percent
        FROM agents
        WHERE is_active = 1 AND traffic_percent > 0
        ORDER BY id ASC
        """
    ).fetchall()
    return [dict(r) for r in rows]


def _distribution(agent_ids: list[str], weights: list[int], n: int) -> list[str]:
    """Largest-remainder allocation of n leads across agents."""
    if not agent_ids or n <= 0:
        return []
    total = sum(weights)
    if total <= 0:
        return []

    exact = [n * w / total for w in weights]
    base = [int(x) for x in exact]
    remainders = [x - b for x, b in zip(exact, base)]
    assigned = list(base)
    leftover = n - sum(assigned)

    order = sorted(range(len(agent_ids)), key=lambda i: remainders[i], reverse=True)
    for i in range(leftover):
        assigned[order[i % len(order)]] += 1

    out: list[str] = []
    for agent_id, count in zip(agent_ids, assigned):
        out.extend([agent_id] * count)
    return out


def assign_unassigned_leads(path: Path | None = None) -> dict[str, Any]:
    """Assign all unassigned leads using normalized traffic_percent among active agents."""
    with connect(path) as conn:
        agents = _active_agents(conn)
        lead_ids = unassigned_lead_ids(path)
        if not lead_ids:
            return {"assigned": 0, "agents": len(agents), "by_agent": {}}

        if not agents:
            return {"assigned": 0, "agents": 0, "by_agent": {}, "skipped_no_agents": len(lead_ids)}

        agent_ids = [a["id"] for a in agents]
        weights = [int(a["traffic_percent"]) for a in agents]
        slots = _distribution(agent_ids, weights, len(lead_ids))
        ts = now_iso()
        by_agent: dict[str, int] = {aid: 0 for aid in agent_ids}

        for lead_id, agent_id in zip(lead_ids, slots):
            conn.execute(
                """
                UPDATE parent_leads
                SET assigned_agent_id = ?, pipeline_stage = ?, updated_at = ?
                WHERE lead_id = ?
                  AND (assigned_agent_id IS NULL OR pipeline_stage = ?)
                """,
                (agent_id, STAGE_ASSIGNED, ts, lead_id, STAGE_UNASSIGNED),
            )
            by_agent[agent_id] = by_agent.get(agent_id, 0) + 1

        conn.commit()

    return {
        "assigned": len(slots),
        "agents": len(agents),
        "by_agent": by_agent,
        "weights": dict(zip(agent_ids, weights)),
    }


def redistribute_all_leads(path: Path | None = None) -> dict[str, Any]:
    """Redistribute ALL leads (including already assigned) among active agents.
    
    WARNING: This will reassign leads that agents may already be working on.
    Use only for testing or when explicitly requested.
    """
    with connect(path) as conn:
        agents = _active_agents(conn)
        
        # Get ALL lead IDs (not just unassigned)
        rows = conn.execute(
            "SELECT lead_id FROM parent_leads ORDER BY created_time DESC"
        ).fetchall()
        lead_ids = [r["lead_id"] for r in rows]
        
        if not lead_ids:
            return {"redistributed": 0, "agents": len(agents), "by_agent": {}}

        if not agents:
            return {"redistributed": 0, "agents": 0, "by_agent": {}, "error": "no_active_agents"}

        agent_ids = [a["id"] for a in agents]
        weights = [int(a["traffic_percent"]) for a in agents]
        slots = _distribution(agent_ids, weights, len(lead_ids))
        ts = now_iso()
        by_agent: dict[str, int] = {aid: 0 for aid in agent_ids}

        for lead_id, agent_id in zip(lead_ids, slots):
            conn.execute(
                """
                UPDATE parent_leads
                SET assigned_agent_id = ?, pipeline_stage = ?, updated_at = ?
                WHERE lead_id = ?
                """,
                (agent_id, STAGE_ASSIGNED, ts, lead_id),
            )
            by_agent[agent_id] = by_agent.get(agent_id, 0) + 1

        conn.commit()

    return {
        "redistributed": len(slots),
        "agents": len(agents),
        "by_agent": by_agent,
        "weights": dict(zip(agent_ids, weights)),
    }
