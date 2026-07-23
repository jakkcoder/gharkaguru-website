"""CLI: pull new unfilled parent leads from meta-ads GCS into local/GCS SQLite."""

from __future__ import annotations

import argparse
import json

from app.parent_leads import db as inbox_db
from app.parent_leads import gcs_db
from app.parent_leads.assign import assign_unassigned_leads
from app.parent_leads.config import PARENT_LEADS_DB_PATH as LOCAL_DB_PATH
from app.parent_leads.meta_sync import load_parent_leads_for_inbox
from app.parent_leads.source import filter_new_unfilled


def run_pull(
    *,
    push: bool = False,
    pull_db_first: bool = False,
    assign_new: bool = True,
    assign_existing: bool = False,
    limit_preview: int = 10,
    meta_full_sync: bool = False,
) -> dict:
    if pull_db_first:
        db_state = gcs_db.pull_db()
    else:
        inbox_db.init_db()
        db_state = {"action": "local_only", "path": str(LOCAL_DB_PATH)}

    flattened, meta = load_parent_leads_for_inbox(full_sync=meta_full_sync)
    existing = inbox_db.existing_lead_ids()
    refreshed = inbox_db.refresh_contact_fields_from_meta(flattened)
    selected = filter_new_unfilled(flattened, existing_ids=existing)
    inserted = inbox_db.insert_leads(selected)

    assignment: dict = {"assigned": 0}
    if assign_new or assign_existing:
        assignment = assign_unassigned_leads()

    stats = inbox_db.counts()
    preview = inbox_db.list_unfilled(limit=limit_preview)

    result = {
        "source": meta,
        "db": db_state,
        "candidates_from_meta": meta.get("source_lead_count") or meta.get("lead_count") or 0,
        "already_in_inbox": len(existing),
        "contact_fields_refreshed": refreshed,
        "new_unfilled_selected": len(selected),
        "inserted": inserted,
        "assignment": assignment,
        "inbox_counts": stats,
        "preview_unfilled": preview,
    }

    if push:
        result["gcs_push"] = gcs_db.push_db()

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Pull new unfilled Meta parent leads into parent_leads.db"
    )
    parser.add_argument(
        "--pull-db",
        action="store_true",
        help="Download existing inbox DB from GCS before merge",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Upload local inbox DB to GCS after pull",
    )
    parser.add_argument(
        "--assign-existing",
        action="store_true",
        help="Assign all unassigned inbox leads to active agents",
    )
    parser.add_argument(
        "--no-assign",
        action="store_true",
        help="Skip traffic assignment after insert",
    )
    parser.add_argument("--preview", type=int, default=10, help="Preview row count")
    args = parser.parse_args(argv)

    result = run_pull(
        push=args.push,
        pull_db_first=args.pull_db,
        assign_new=not args.no_assign,
        assign_existing=args.assign_existing,
        limit_preview=args.preview,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
