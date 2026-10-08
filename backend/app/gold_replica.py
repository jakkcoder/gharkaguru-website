"""Keep parent_enquiries a replica of the leads tool's gold leads.

The leads tool (parent-lead-pipeline) serves its current gold leads over the cluster
network, without phones, names or street addresses. Every refresh makes the open rows
here exactly that set: new gold leads open, changed ones update, and a lead that left
gold is closed, so it drops off the public page. Rows are closed, not deleted, so teacher
interests and payments keep their enquiry.

The parent's number is never stored. parent_contact asks the leads tool for it when a
teacher's access fee has been confirmed.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Callable

from app.db import connect, now_iso

logger = logging.getLogger("website-api")

LEADS_API_URL = os.getenv(
    "LEADS_API_URL", "http://parent-lead-pipeline.apps.svc.cluster.local:8092"
).strip().rstrip("/")
REFRESH_SECONDS = max(5, int(os.getenv("GOLD_REPLICA_SECONDS", "15")))
# A page read refreshes first when the copy is older than this, so an edit in the
# leads tool shows on the next page load.
READ_MAX_AGE_SECONDS = float(os.getenv("GOLD_REPLICA_READ_MAX_AGE", "3"))

Fetch = Callable[[str], dict[str, Any]]

_FIELDS = (
    ("class_level", "classLevel"),
    ("subject", "subject"),
    ("board", "board"),
    ("medium", "medium"),
    ("tutor_mode", "tutorMode"),
    ("teacher_preference", "teacherPreference"),
    ("locality", "locality"),
    ("pin", "pin"),
    ("budget", "budget"),
    ("notes", "notes"),
    ("schedule", "schedule"),
)


def fetch_from_leads_tool(path: str) -> dict[str, Any]:
    secret = os.environ.get("WEBSITE_SYNC_SECRET", "").strip()
    if not secret:
        raise RuntimeError("WEBSITE_SYNC_SECRET is not set.")
    request = urllib.request.Request(
        LEADS_API_URL + path,
        headers={"X-Website-Sync-Key": secret, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        body = json.loads(response.read().decode("utf-8") or "{}")
    if not isinstance(body, dict):
        raise RuntimeError("Leads tool returned an unexpected body.")
    return body


def replace_open_set(conn: Any, leads: list[dict[str, Any]]) -> dict[str, int]:
    """Make the open enquiries exactly `leads`. Does not commit."""
    ts = now_iso()
    seen: set[str] = set()
    for lead in leads:
        lead_id = str(lead.get("metaLeadId") or "").strip()
        if not lead_id or lead_id in seen:
            continue
        seen.add(lead_id)
        values = [str(lead.get(key) or "").strip() for _column, key in _FIELDS]
        revision = str(lead.get("updatedAt") or "").strip()
        existing = conn.execute(
            "SELECT 1 FROM parent_enquiries WHERE meta_lead_id = ?",
            (lead_id,),
        ).fetchone()
        assignments = ", ".join(f"{column} = ?" for column, _key in _FIELDS)
        if existing:
            # parent_phone, names and address are blanked: the replica never holds them.
            conn.execute(
                f"""
                UPDATE parent_enquiries
                SET status = 'open', parent_phone = '', parent_name = '', student_name = '', address = '',
                    {assignments}, source_revision = ?, updated_at = ?
                WHERE meta_lead_id = ?
                """,
                (*values, revision, ts, lead_id),
            )
        else:
            columns = ", ".join(column for column, _key in _FIELDS)
            marks = ", ".join("?" for _ in _FIELDS)
            conn.execute(
                f"""
                INSERT INTO parent_enquiries (
                    meta_lead_id, status, parent_phone, {columns}, source_revision, created_at, updated_at
                ) VALUES (?, 'open', '', {marks}, ?, ?, ?)
                """,
                (lead_id, *values, revision, ts, ts),
            )
    stale = [
        row["meta_lead_id"]
        for row in conn.execute("SELECT meta_lead_id FROM parent_enquiries WHERE status = 'open'").fetchall()
        if row["meta_lead_id"] not in seen
    ]
    for lead_id in stale:
        conn.execute(
            "UPDATE parent_enquiries SET status = 'closed', updated_at = ? WHERE meta_lead_id = ?",
            (ts, lead_id),
        )
    return {"open": len(seen), "closed": len(stale)}


_lock = threading.Lock()
_last_refresh = 0.0


def refresh(fetch: Fetch | None = None) -> dict[str, int]:
    """Pull the gold set once. On any fetch error the replica is left as it was."""
    global _last_refresh
    with _lock:
        body = (fetch or fetch_from_leads_tool)("/api/website/gold-leads")
        leads = body.get("leads")
        if not isinstance(leads, list):
            raise RuntimeError("Leads tool response has no leads list.")
        with connect() as conn:
            counts = replace_open_set(conn, leads)
            conn.commit()
        _last_refresh = time.monotonic()
    return counts


def refresh_if_stale(max_age: float = READ_MAX_AGE_SECONDS, fetch: Fetch | None = None) -> None:
    """Refresh before a page read unless the copy is fresh. Failures keep the last copy."""
    if not _enabled() or time.monotonic() - _last_refresh < max_age:
        return
    try:
        refresh(fetch)
    except Exception as exc:
        logger.warning("Gold replica refresh before read failed, serving the last copy: %s", exc)


def _enabled() -> bool:
    return os.getenv("GOLD_REPLICA", "true").lower() in {"1", "true", "yes"}


def live_contact(meta_lead_id: str, fetch: Fetch | None = None) -> dict[str, str]:
    """The parent's number and name, read from the leads tool at the moment they are needed."""
    from urllib.parse import quote

    body = (fetch or fetch_from_leads_tool)(f"/api/website/gold-leads/{quote(meta_lead_id, safe='')}/contact")
    return {
        "parentPhone": str(body.get("parentPhone") or ""),
        "parentName": str(body.get("parentName") or ""),
    }


def _loop(stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            refresh()
        except (urllib.error.URLError, OSError, RuntimeError, ValueError) as exc:
            logger.warning("Gold replica refresh failed, keeping the last copy: %s", exc)
        except Exception:
            logger.exception("Gold replica refresh failed")
        stop.wait(REFRESH_SECONDS)


def start_background_refresh() -> threading.Event | None:
    if not _enabled():
        return None
    stop = threading.Event()
    threading.Thread(target=_loop, args=(stop,), name="gold-replica", daemon=True).start()
    return stop
