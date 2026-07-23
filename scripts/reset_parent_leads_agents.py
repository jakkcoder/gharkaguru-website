#!/usr/bin/env python3
"""Reset parent-leads agents in GCS and reassign leads by traffic."""

from __future__ import annotations

import os
import sys

# Run from repo: PYTHONPATH=backend python3 scripts/reset_parent_leads_agents.py
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

os.environ.setdefault("DATA_DIR", "/tmp/website-data-reset")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "vertex-ai-learning-487906")

from app.parent_leads import agents_db, db, gcs_db
from app.parent_leads.assign import assign_unassigned_leads

AGENTS = [
    {"name": "Neha", "email": "neha@gharkaguru.com", "password": "neha", "traffic_percent": 17},
    {"name": "Rohini", "email": "rohini@gharkaguru.com", "password": "rohini", "traffic_percent": 50},
    {"name": "Anshika", "email": "anshika@gharkaguru.com", "password": "anshika", "traffic_percent": 17},
    {"name": "Anjali", "email": "anjali@gharkaguru.com", "password": "anjali", "traffic_percent": 16},
]


def main() -> int:
    gcs_db.ensure_local_db()
    gcs_db.pull_db()
    db.init_db()

    deleted = agents_db.delete_all_agents()
    print(f"Removed {deleted} old agent row(s); leads marked unassigned.")

    for spec in AGENTS:
        agents_db.create_agent(**spec)
        print(f"Created {spec['name']} ({spec['email']}) traffic={spec['traffic_percent']}% pwd={spec['password']}")

    assignment = assign_unassigned_leads()
    print(f"Assigned {assignment.get('assigned', 0)} leads: {assignment.get('by_agent', {})}")

    counts = db.counts()
    print(f"Inbox: {counts}")

    by_agent = agents_db.agent_lead_counts()
    for a in agents_db.list_agents():
        print(f"  {a['name']}: {by_agent.get(a['id'], 0)} leads")

    gcs_db.push_db()
    print("Pushed parent_leads.db to GCS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
