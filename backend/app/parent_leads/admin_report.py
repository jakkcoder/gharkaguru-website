"""Admin dashboard: pipeline snapshot + daily activity (Asia/Kolkata)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.parent_leads import db as inbox_db
from app.parent_leads.config import STAGE_LABELS, TAB_JUNK

IST = ZoneInfo("Asia/Kolkata")


def ist_today() -> date:
    return datetime.now(IST).date()


def ist_day_bounds(day: date) -> tuple[str, str]:
    """UTC ISO bounds [start, end) for a calendar day in IST."""
    start_local = datetime.combine(day, datetime.min.time(), tzinfo=IST)
    end_local = start_local + timedelta(days=1)
    start_utc = start_local.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    end_utc = end_local.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    return start_utc, end_utc


def _count_between(
    conn,
    *,
    start: str,
    end: str,
    extra_where: str = "",
    params: tuple[Any, ...] = (),
) -> int:
    row = conn.execute(
        f"""
        SELECT COUNT(*) AS n FROM parent_leads
        WHERE updated_at >= ? AND updated_at < ?
        {extra_where}
        """,
        (start, end, *params),
    ).fetchone()
    return int(row["n"])


def daily_metrics_for_day(day: date, path=None) -> dict[str, Any]:
    start, end = ist_day_bounds(day)
    with inbox_db.connect(path) as conn:
        new_pulled = conn.execute(
            """
            SELECT COUNT(*) AS n FROM parent_leads
            WHERE pulled_at >= ? AND pulled_at < ?
            """,
            (start, end),
        ).fetchone()["n"]
        moved_demo = _count_between(
            conn,
            start=start,
            end=end,
            extra_where="AND is_junk = 0 AND pipeline_stage = 'demo_scheduled'",
        )
        moved_class = _count_between(
            conn,
            start=start,
            end=end,
            extra_where="AND is_junk = 0 AND pipeline_stage = 'class_started'",
        )
        moved_payment = _count_between(
            conn,
            start=start,
            end=end,
            extra_where="AND is_junk = 0 AND pipeline_stage = 'payment_received'",
        )
        moved_junk = _count_between(
            conn,
            start=start,
            end=end,
            extra_where="AND is_junk = 1",
        )
        touched = _count_between(conn, start=start, end=end)
    return {
        "date": day.isoformat(),
        "date_label": day.strftime("%a, %d %b %Y"),
        "new_pulled": int(new_pulled),
        "moved_demo": int(moved_demo),
        "moved_class": int(moved_class),
        "moved_payment": int(moved_payment),
        "moved_junk": int(moved_junk),
        "agent_updates": int(touched),
    }


def pipeline_snapshot(path=None) -> dict[str, Any]:
    with inbox_db.connect(path) as conn:
        rows = conn.execute(
            """
            SELECT pipeline_stage, COUNT(*) AS n
            FROM parent_leads
            WHERE is_junk = 0
            GROUP BY pipeline_stage
            """
        ).fetchall()
        junk = conn.execute(
            "SELECT COUNT(*) AS n FROM parent_leads WHERE is_junk = 1"
        ).fetchone()["n"]
        filled = conn.execute(
            "SELECT COUNT(*) AS n FROM parent_leads WHERE fill_status = 'filled' AND is_junk = 0"
        ).fetchone()["n"]
        with_name = conn.execute(
            """
            SELECT COUNT(*) AS n FROM parent_leads
            WHERE trim(parent_name) != '' AND is_junk = 0
            """
        ).fetchone()["n"]
        by_agent = conn.execute(
            """
            SELECT a.name, a.email,
                   SUM(CASE WHEN pl.is_junk = 0 THEN 1 ELSE 0 END) AS active_leads,
                   SUM(CASE WHEN pl.is_junk = 1 THEN 1 ELSE 0 END) AS junk_leads
            FROM agents a
            LEFT JOIN parent_leads pl ON pl.assigned_agent_id = a.id
            WHERE a.is_active = 1
            GROUP BY a.id
            ORDER BY a.name
            """
        ).fetchall()

    stage_counts: dict[str, int] = {str(r["pipeline_stage"]): int(r["n"]) for r in rows}
    labeled = [
        {
            "key": key,
            "label": STAGE_LABELS.get(key, key.replace("_", " ").title()),
            "count": stage_counts.get(key, 0),
        }
        for key in ("assigned", "demo_scheduled", "class_started", "payment_received", "unassigned")
    ]
    return {
        "stages": labeled,
        "stage_counts": stage_counts,
        "junk": int(junk),
        "filled": int(filled),
        "with_parent_name": int(with_name),
        "total": sum(stage_counts.values()) + int(junk),
        "by_agent": [dict(r) for r in by_agent],
    }


def admin_dashboard(*, report_day: date | None = None, history_days: int = 7, path=None) -> dict[str, Any]:
    day = report_day or ist_today()
    history: list[dict[str, Any]] = []
    for offset in range(history_days - 1, -1, -1):
        d = day - timedelta(days=offset)
        history.append(daily_metrics_for_day(d, path=path))
    start, end = ist_day_bounds(day)
    raw_events = inbox_db.list_today_events(day_start_utc=start, day_end_utc=end, limit=40, path=path)
    activity: list[dict[str, Any]] = []
    for ev in raw_events:
        created = ev.get("created_at") or ""
        time_label = created
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            time_label = dt.astimezone(IST).strftime("%H:%M")
        except ValueError:
            pass
        phone = (ev.get("parent_phone") or "").strip() or "—"
        activity.append(
            {
                "time": time_label,
                "agent": ev.get("agent_name") or ev.get("agent_email") or "—",
                "phone": phone,
                "lead_id": ev.get("lead_id") or "",
                "action": ev.get("action") or "",
                "detail": ev.get("detail") or "",
            }
        )
    return {
        "report_day": day.isoformat(),
        "report_day_label": day.strftime("%A, %d %B %Y"),
        "timezone": "Asia/Kolkata",
        "today": daily_metrics_for_day(day, path=path),
        "activity": activity,
        "history": history,
        "snapshot": pipeline_snapshot(path=path),
        "inbox": inbox_db.counts(path=path),
        "junk_label": STAGE_LABELS.get(TAB_JUNK, "Junk"),
    }
