"""Tests for admin dashboard metrics."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from app.parent_leads import db as inbox_db
from app.parent_leads.admin_report import (
    admin_dashboard,
    daily_metrics_for_day,
    ist_day_bounds,
    pipeline_snapshot,
)

IST = ZoneInfo("Asia/Kolkata")


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    p = tmp_path / "test.db"
    inbox_db.init_db(p)
    return p


def _insert(
    path: Path,
    lead_id: str,
    *,
    stage: str = "assigned",
    is_junk: int = 0,
    updated_at: str,
    pulled_at: str | None = None,
) -> None:
    ts = pulled_at or updated_at
    with inbox_db.connect(path) as conn:
        conn.execute(
            """
            INSERT INTO parent_leads (
              lead_id, form_id, form_name, created_time, parent_name, parent_phone,
              student_class, location, mode, budget, note, meta_status, platform,
              fields_json, fill_status, assigned_agent_id, pipeline_stage,
              pulled_at, updated_at, filled_at, is_junk
            ) VALUES (?, '', '', '2026-07-20T10:00:00+00:00', 'Test Parent', '9999999999',
              '', '', '', '', '', '', '', '{}', 'unfilled', NULL, ?,
              ?, ?, NULL, ?)
            """,
            (lead_id, stage, ts, updated_at, is_junk),
        )
        conn.commit()


def test_ist_day_bounds():
    start, end = ist_day_bounds(date(2026, 7, 23))
    assert start < end
    # Jul 23 00:00 IST = Jul 22 18:30 UTC
    assert "2026-07-22T18:30:00" in start


def test_daily_metrics_demo_and_junk(db_path: Path):
    day = date(2026, 7, 23)
    start, _ = ist_day_bounds(day)
    mid = datetime.fromisoformat(start)
    if mid.tzinfo is None:
        mid = mid.replace(tzinfo=timezone.utc)
    updated = (mid + timedelta(hours=2)).isoformat()

    _insert(db_path, "1", stage="demo_scheduled", updated_at=updated)
    _insert(db_path, "2", stage="assigned", is_junk=1, updated_at=updated)
    _insert(db_path, "3", stage="assigned", updated_at=updated, pulled_at=updated)

    m = daily_metrics_for_day(day, path=db_path)
    assert m["moved_demo"] == 1
    assert m["moved_junk"] == 1
    assert m["new_pulled"] == 3


def test_pipeline_snapshot(db_path: Path):
    _insert(
        db_path,
        "a",
        stage="demo_scheduled",
        updated_at="2026-07-23T06:00:00+00:00",
    )
    _insert(
        db_path,
        "b",
        stage="assigned",
        is_junk=1,
        updated_at="2026-07-23T06:00:00+00:00",
    )
    snap = pipeline_snapshot(path=db_path)
    assert snap["junk"] == 1
    assert snap["stage_counts"].get("demo_scheduled") == 1


def test_admin_dashboard_includes_history(db_path: Path):
    data = admin_dashboard(report_day=date(2026, 7, 23), path=db_path)
    assert len(data["history"]) == 7
    assert "today" in data
    assert "snapshot" in data
