"""Privacy and payment rules for public parent enquiries."""

from __future__ import annotations

import os
import sqlite3
import unittest

os.environ.setdefault("DATA_DIR", "/tmp/website-enquiry-tests")
os.environ.setdefault("PULL_ON_STARTUP", "false")

from app.db import SCHEMA_SQL  # noqa: E402
from app.parent_enquiries import (  # noqa: E402
    FIRST_FEE_RUPEES,
    NEXT_FEE_RUPEES,
    POLICY_VERSION,
    ApplyBody,
    EnquirySync,
    apply_for_enquiry,
    fee_rupees,
    get_open,
    list_open,
    mark_payment_paid,
    note_website_teacher,
    parent_contact,
    public_enquiry,
    registration_source,
    sync_teachers,
    upsert_enquiry,
)
from fastapi import HTTPException  # noqa: E402


def memory_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    return conn


def lead(status: str = "open", phone: str = "9876543210") -> EnquirySync:
    return EnquirySync(
        metaLeadId="lead-1",
        status=status,
        parentPhone=phone,
        parentName="S",
        studentName="Kartavya",
        classLevel="10",
        subject="Maths, Science",
        board="CBSE",
        medium="english",
        tutorMode="home",
        teacherPreference="male",
        address="Raja Puri, Delhi",
        pin="110059",
        budget="5000",
        notes="Need home tutor",
    )


class ParentEnquiryTests(unittest.TestCase):
    def test_public_payload_omits_the_parent_phone(self) -> None:
        conn = memory_db()
        upsert_enquiry(conn, lead())
        conn.commit()
        shown = list_open(conn)[0]
        self.assertNotIn("parentPhone", shown)
        self.assertNotIn("parent_phone", shown)
        self.assertEqual(shown["address"], "Raja Puri, Delhi")
        self.assertEqual(shown["studentName"], "Kartavya")
        raw = public_enquiry(conn.execute("SELECT * FROM parent_enquiries").fetchone())
        self.assertNotIn("9876543210", str(raw))

    def test_converted_lead_leaves_the_public_list(self) -> None:
        conn = memory_db()
        upsert_enquiry(conn, lead())
        upsert_enquiry(conn, lead(status="converted"))
        conn.commit()
        self.assertEqual(list_open(conn), [])
        self.assertIsNone(get_open(conn, "lead-1"))

    def test_website_or_gold_teacher_can_apply_once(self) -> None:
        conn = memory_db()
        upsert_enquiry(conn, lead())
        sync_teachers(conn, [{"phone": "919000000001", "fullName": "Gold Tutor"}])
        self.assertEqual(registration_source(conn, "9000000001"), "gold")
        body = ApplyBody(isTutor=True, acceptNoRefund=True, acceptCommission=True, policyVersion=POLICY_VERSION)
        first = apply_for_enquiry(conn, "lead-1", "9000000001", body)
        second = apply_for_enquiry(conn, "lead-1", "9000000001", body)
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["payment"]["amountRupees"], FIRST_FEE_RUPEES)
        self.assertEqual(first["interestId"], second["interestId"])

    def test_second_paid_unlock_costs_more_and_only_that_teacher_sees_the_number(self) -> None:
        conn = memory_db()
        upsert_enquiry(conn, lead())
        other = lead()
        other.metaLeadId = "lead-2"
        upsert_enquiry(conn, other)
        note_website_teacher(conn, "9111111111", "Site Tutor")
        body = ApplyBody(isTutor=True, acceptNoRefund=True, acceptCommission=True, policyVersion=POLICY_VERSION)
        first = apply_for_enquiry(conn, "lead-1", "9111111111", body)
        mark_payment_paid(conn, "lead-1", first["payment"]["id"])
        self.assertEqual(fee_rupees(conn, "9111111111"), NEXT_FEE_RUPEES)
        second = apply_for_enquiry(conn, "lead-2", "9111111111", body)
        self.assertEqual(second["payment"]["amountRupees"], NEXT_FEE_RUPEES)
        revealed = parent_contact(conn, "lead-1", "9111111111")
        self.assertEqual(revealed["parentPhone"], "9876543210")
        with self.assertRaises(HTTPException) as pending:
            parent_contact(conn, "lead-2", "9111111111")
        self.assertEqual(pending.exception.status_code, 402)
        note_website_teacher(conn, "9222222222", "Other Tutor")
        with self.assertRaises(HTTPException) as denied:
            parent_contact(conn, "lead-1", "9222222222")
        self.assertEqual(denied.exception.status_code, 403)

    def test_old_policy_version_is_rejected(self) -> None:
        conn = memory_db()
        upsert_enquiry(conn, lead())
        note_website_teacher(conn, "9111111111", "Site Tutor")
        body = ApplyBody(isTutor=True, acceptNoRefund=True, acceptCommission=True, policyVersion="2020-01-01")
        with self.assertRaises(HTTPException) as changed:
            apply_for_enquiry(conn, "lead-1", "9111111111", body)
        self.assertEqual(changed.exception.status_code, 409)

    def test_unregistered_teacher_must_finish_the_profile(self) -> None:
        conn = memory_db()
        upsert_enquiry(conn, lead())
        body = ApplyBody(isTutor=True, acceptNoRefund=True, acceptCommission=True, policyVersion=POLICY_VERSION)
        with self.assertRaises(HTTPException) as required:
            apply_for_enquiry(conn, "lead-1", "9333333333", body)
        self.assertEqual(required.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
