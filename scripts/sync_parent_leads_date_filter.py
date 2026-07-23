#!/usr/bin/env python3
"""Apply LEADS_START_DATE: purge old rows, pull new from Meta, reassign, push GCS."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

os.environ.setdefault("DATA_DIR", "/tmp/website-data-reset")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "vertex-ai-learning-487906")
os.environ.setdefault("LEADS_START_DATE", "2026-07-19")

from app.parent_leads import agents_db, db, gcs_db
from app.parent_leads.assign import assign_unassigned_leads, redistribute_all_leads
from app.parent_leads.config import LEADS_START_DATE
from app.parent_leads.pull import run_pull


def main() -> int:
    print(f"LEADS_START_DATE (on or after): {LEADS_START_DATE}")
    gcs_db.ensure_local_db()
    gcs_db.pull_db()
    db.init_db()

    removed = db.purge_leads_before_start_date()
    print(f"Purged {removed} leads before {LEADS_START_DATE}")

    pull = run_pull(push=False, pull_db_first=False, assign_new=True, assign_existing=False)
    print(f"Pull inserted: {pull.get('inserted', 0)} new from Meta")

    assignment = redistribute_all_leads()
    print(f"Redistributed {assignment.get('redistributed', 0)} leads among agents")

    counts = db.counts()
    print(f"Inbox counts: {counts}")

    conn = db.connect()
    row = conn.execute(
        """
        SELECT MIN(substr(created_time,1,10)) AS min_d,
               MAX(substr(created_time,1,10)) AS max_d,
               COUNT(*) AS n
        FROM parent_leads
        """
    ).fetchone()
    conn.close()
    print(f"Date range in DB: {row['min_d']} .. {row['max_d']} ({row['n']} leads)")

    for a in agents_db.list_agents():
        lc = agents_db.agent_lead_counts().get(a["id"], 0)
        print(f"  {a['name']}: {lc} leads")

    gcs_db.push_db()
    print("Pushed to GCS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
