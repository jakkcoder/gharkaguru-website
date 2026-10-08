"""The website's parent enquiries mirror the leads tool's gold leads."""

from __future__ import annotations

import os
import sqlite3
import unittest

os.environ.setdefault("DATA_DIR", "/tmp/website-enquiry-tests")
os.environ.setdefault("PULL_ON_STARTUP", "false")

from app.db import SCHEMA_SQL  # noqa: E402
from app.gold_replica import live_contact, replace_open_set  # noqa: E402
from app.parent_enquiries import (  # noqa: E402
    POLICY_VERSION,
    ApplyBody,
    apply_for_enquiry,
    contact_details,
    get_open,
    list_open,
    mark_payment_paid,
    note_website_teacher,
)
from fastapi import HTTPException  # noqa: E402


def memory_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    return conn


def gold(lead_id: str = "lead-1", **extra: str) -> dict[str, str]:
    lead = {
        "metaLeadId": lead_id,
        "classLevel": "10",
        "subject": "Maths, Science",
        "board": "CBSE",
        "medium": "english",
        "tutorMode": "home",
        "teacherPreference": "male",
        "locality": "Rajapuri",
        "pin": "110059",
        "budget": "5000",
        "notes": "Need home tutor",
        "schedule": "",
        "updatedAt": "2026-10-08T00:00:00+00:00",
    }
    lead.update(extra)
    return lead


class GoldReplicaTests(unittest.TestCase):
    def test_open_enquiries_are_exactly_the_gold_set(self) -> None:
        conn = memory_db()
        replace_open_set(conn, [gold("lead-1"), gold("lead-2", subject="English")])
        self.assertEqual({item["id"] for item in list_open(conn)}, {"lead-1", "lead-2"})
        counts = replace_open_set(conn, [gold("lead-2", subject="Hindi")])
        self.assertEqual(counts, {"open": 1, "closed": 1})
        shown = list_open(conn)
        self.assertEqual([item["id"] for item in shown], ["lead-2"])
        self.assertEqual(shown[0]["subject"], "Hindi")
        self.assertIsNone(get_open(conn, "lead-1"))
        replace_open_set(conn, [gold("lead-1"), gold("lead-2")])
        self.assertIsNotNone(get_open(conn, "lead-1"))

    def test_replica_never_stores_phone_names_or_address(self) -> None:
        conn = memory_db()
        conn.execute(
            """
            INSERT INTO parent_enquiries (meta_lead_id, status, parent_phone, parent_name, student_name, address,
                                          created_at, updated_at)
            VALUES ('lead-1', 'open', '9876543210', 'Sunita', 'Kartavya', 'H-12 Gali 4', 'x', 'x')
            """
        )
        replace_open_set(conn, [gold("lead-1", parentPhone="9876543210", parentName="Sunita")])
        row = conn.execute("SELECT * FROM parent_enquiries WHERE meta_lead_id = 'lead-1'").fetchone()
        self.assertEqual((row["parent_phone"], row["parent_name"], row["student_name"], row["address"]), ("", "", "", ""))
        self.assertNotIn("9876543210", str(list_open(conn)))

    def test_closed_lead_keeps_teacher_interest_but_takes_no_new_ones(self) -> None:
        conn = memory_db()
        replace_open_set(conn, [gold()])
        note_website_teacher(conn, "9111111111", "Site Tutor")
        note_website_teacher(conn, "9222222222", "Other Tutor")
        body = ApplyBody(isTutor=True, acceptNoRefund=True, acceptCommission=True, policyVersion=POLICY_VERSION)
        apply_for_enquiry(conn, "lead-1", "9111111111", body)
        replace_open_set(conn, [])
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM teacher_enquiry_interests").fetchone()[0], 1)
        with self.assertRaises(HTTPException) as closed:
            apply_for_enquiry(conn, "lead-1", "9222222222", body)
        self.assertEqual(closed.exception.status_code, 409)

    def test_paid_teacher_gets_the_number_live_from_the_leads_tool(self) -> None:
        conn = memory_db()
        replace_open_set(conn, [gold()])
        note_website_teacher(conn, "9111111111", "Site Tutor")
        body = ApplyBody(isTutor=True, acceptNoRefund=True, acceptCommission=True, policyVersion=POLICY_VERSION)
        applied = apply_for_enquiry(conn, "lead-1", "9111111111", body)
        mark_payment_paid(conn, "lead-1", applied["payment"]["id"])
        row = conn.execute("SELECT * FROM parent_enquiries WHERE meta_lead_id = 'lead-1'").fetchone()
        asked: list[str] = []

        def fetch(path: str) -> dict[str, str]:
            asked.append(path)
            return {"parentPhone": "9876543210", "parentName": "Sunita"}

        found = contact_details(row, live=lambda lead_id: live_contact(lead_id, fetch=fetch))
        self.assertEqual(found["parentPhone"], "9876543210")
        self.assertEqual(asked, ["/api/website/gold-leads/lead-1/contact"])
        self.assertEqual(conn.execute("SELECT parent_phone FROM parent_enquiries").fetchone()[0], "")

    def test_contact_lookup_failure_is_a_503(self) -> None:
        conn = memory_db()
        replace_open_set(conn, [gold()])
        row = conn.execute("SELECT * FROM parent_enquiries").fetchone()

        def down(_lead_id: str) -> dict[str, str]:
            raise OSError("leads tool down")

        with self.assertRaises(HTTPException) as failed:
            contact_details(row, live=down)
        self.assertEqual(failed.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
