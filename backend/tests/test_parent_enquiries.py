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
    my_applications,
    public_enquiry,
    registration_source,
    scrub_text,
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
        address="H-12, Gali 4, Raja Puri, Delhi",
        locality="Rajapuri",
        pin="110059",
        budget="5000",
        notes="Need home tutor",
    )


class ParentEnquiryTests(unittest.TestCase):
    def test_public_payload_omits_phone_names_and_street_address(self) -> None:
        conn = memory_db()
        upsert_enquiry(conn, lead())
        conn.commit()
        shown = list_open(conn)[0]
        for key in ("parentPhone", "parent_phone", "parentName", "studentName", "address"):
            self.assertNotIn(key, shown)
        self.assertEqual(shown["locality"], "Rajapuri")
        self.assertEqual(shown["pin"], "110059")
        self.assertEqual(shown["subject"], "Maths, Science")
        raw = str(public_enquiry(conn.execute("SELECT * FROM parent_enquiries").fetchone()))
        for secret in ("9876543210", "Kartavya", "H-12", "Gali 4"):
            self.assertNotIn(secret, raw)

    def test_public_notes_hide_phone_numbers_and_names(self) -> None:
        conn = memory_db()
        noisy = lead()
        noisy.notes = "Call Kartavya's mother on 98765 43210 or +91-9123456789. Budget 5000 - 10000."
        noisy.schedule = "Evenings, ask for kartavya"
        upsert_enquiry(conn, noisy)
        conn.commit()
        shown = list_open(conn)[0]
        self.assertNotIn("9876543210", shown["notes"].replace(" ", ""))
        self.assertNotIn("9123456789", shown["notes"].replace("-", ""))
        self.assertNotIn("Kartavya", shown["notes"])
        self.assertIn("5000 - 10000", shown["notes"])
        self.assertNotIn("kartavya", shown["schedule"].lower())

    def test_scrub_keeps_short_numbers(self) -> None:
        self.assertEqual(scrub_text("Class 10, 4-6 pm, PIN 110059", []), "Class 10, 4-6 pm, PIN 110059")

    def test_teacher_sees_student_name_only_after_payment(self) -> None:
        conn = memory_db()
        upsert_enquiry(conn, lead())
        note_website_teacher(conn, "9111111111", "Site Tutor")
        body = ApplyBody(isTutor=True, acceptNoRefund=True, acceptCommission=True, policyVersion=POLICY_VERSION)
        applied = apply_for_enquiry(conn, "lead-1", "9111111111", body)
        self.assertEqual(my_applications(conn, "9111111111")[0]["studentName"], "")
        mark_payment_paid(conn, "lead-1", applied["payment"]["id"])
        self.assertEqual(my_applications(conn, "9111111111")[0]["studentName"], "Kartavya")

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

    def test_init_db_adds_locality_to_an_old_table(self) -> None:
        import tempfile
        from pathlib import Path

        from app.db import init_db

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "old.db"
            old = sqlite3.connect(path)
            old.execute("CREATE TABLE parent_enquiries (meta_lead_id TEXT PRIMARY KEY, status TEXT NOT NULL)")
            old.commit()
            old.close()
            init_db(path)
            check = sqlite3.connect(path)
            columns = {row[1] for row in check.execute("PRAGMA table_info(parent_enquiries)")}
            check.close()
        self.assertIn("locality", columns)


if __name__ == "__main__":
    unittest.main()
