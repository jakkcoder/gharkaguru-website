"""Configuration for parent leads inbox module."""

from __future__ import annotations

import os
from pathlib import Path

# Import shared config
from app.config import DATA_DIR, GOOGLE_CLOUD_PROJECT

# GCS paths for parent leads
GCS_LEADS_BUCKET = os.getenv("GCS_LEADS_BUCKET", "vertex-ai-learning-487906-gharka-leads")
GCS_PARENTS_OBJECT = os.getenv("GCS_PARENTS_OBJECT", "meta-ads/leads/parents.json")
GCS_ANNOTATIONS_OBJECT = os.getenv("GCS_ANNOTATIONS_OBJECT", "meta-ads/leads/annotations.json")
GCS_PARENT_LEADS_DB_OBJECT = os.getenv("GCS_PARENT_LEADS_DB_OBJECT", "parent-leads-inbox/parent_leads.db")
GCS_META_SYNC_STATE_OBJECT = os.getenv(
    "GCS_META_SYNC_STATE_OBJECT", "parent-leads-inbox/meta_sync_state.json"
)
GCS_AGENT_SECRETS_OBJECT = os.getenv(
    "GCS_AGENT_SECRETS_OBJECT", "parent-leads-inbox/agent_passwords.json"
)

# Local paths
PARENT_LEADS_DB_PATH = DATA_DIR / "parent_leads.db"
PARENT_LEADS_GCS_STATE_PATH = DATA_DIR / ".gcs_parent_leads_state.json"

# Meta-ads gold marker — exclude from inbox queue
GOLD_STATUS = "Demo scheduled"

# Lead date filter — only include leads created on or after this date
LEADS_START_DATE = os.getenv("LEADS_START_DATE", "2026-07-19")

# Direct Meta Graph API (admin Pull) — no manual GCS export step
PAGE_ID = os.getenv("PAGE_ID", "347244005670587")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN", "")
META_API_VERSION = os.getenv("META_API_VERSION", "v25.0")
LEADS_OVERLAP_SECONDS = int(os.getenv("LEADS_OVERLAP_SECONDS", "3600"))
PARENT_LEADS_META_SYNC = os.getenv("PARENT_LEADS_META_SYNC", "true").lower() in {
    "1",
    "true",
    "yes",
}
_DEFAULT_PARENT_FORMS = (
    "4495668977342555",  # getparent_new (legacy)
    "1337209721880919",  # getparent_new_with_details_v2 (name + phone + demo)
)
_extra_forms = [
    x.strip()
    for x in os.getenv("PARENT_FORM_IDS_EXTRA", "").split(",")
    if x.strip()
]
PARENT_FORM_IDS = tuple(dict.fromkeys(list(_DEFAULT_PARENT_FORMS) + _extra_forms))

# Web / auth
PARENT_LEADS_ADMIN_PASSWORD = os.getenv("PARENT_LEADS_ADMIN_PASSWORD", "khus@123")
PARENT_LEADS_SESSION_SECRET = os.getenv("PARENT_LEADS_SESSION_SECRET", "parent-leads-inbox-session-secret")

# Pipeline stages
STAGE_UNASSIGNED = "unassigned"
STAGE_ASSIGNED = "assigned"
STAGE_DEMO = "demo_scheduled"
STAGE_CLASS = "class_started"
STAGE_PAYMENT = "payment_received"

STAGE_ORDER = [STAGE_ASSIGNED, STAGE_DEMO, STAGE_CLASS, STAGE_PAYMENT]
TAB_JUNK = "junk"
PORTAL_TABS = STAGE_ORDER + [TAB_JUNK]
STAGE_LABELS = {
    STAGE_ASSIGNED: "Assigned",
    STAGE_DEMO: "Demo scheduled",
    STAGE_CLASS: "Class started",
    STAGE_PAYMENT: "Payment received",
    TAB_JUNK: "Junk",
}
NEXT_STAGE = {
    STAGE_ASSIGNED: STAGE_DEMO,
    STAGE_DEMO: STAGE_CLASS,
    STAGE_CLASS: STAGE_PAYMENT,
}
PREV_STAGE = {
    STAGE_DEMO: STAGE_ASSIGNED,
    STAGE_CLASS: STAGE_DEMO,
    STAGE_PAYMENT: STAGE_CLASS,
}
