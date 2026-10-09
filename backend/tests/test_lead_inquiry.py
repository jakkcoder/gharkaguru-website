"""Homepage Find Tutors enquiries are saved locally and listed for the parent pipeline."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="website-lead-tests-"))
os.environ.setdefault("PULL_ON_STARTUP", "false")

from fastapi.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402
from app.db import connect, init_db  # noqa: E402

SYNC_KEY = "test-sync-key"
URL = "/v1/api/lead-inquiry"
FEED = "/v1/api/internal/parent-leads"


class LeadInquiryTest(unittest.TestCase):
    def setUp(self) -> None:
        init_db()
        with connect() as conn:
            conn.execute("DELETE FROM inquiries")
            conn.commit()
        self.client = TestClient(main.app)
        for patch in (
            mock.patch.object(main, "sync_to_gcs"),
            mock.patch.dict(os.environ, {"WEBSITE_SYNC_SECRET": SYNC_KEY}),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def feed(self) -> list[dict]:
        response = self.client.get(FEED, headers={"X-Website-Sync-Key": SYNC_KEY})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["leads"]

    def test_phone_only_enquiry_reaches_the_feed(self) -> None:
        response = self.client.post(URL, json={"contactPhone": "+91 98765 43210"})

        self.assertEqual(response.status_code, 200, response.text)
        inquiry_id = response.json()["inquiryId"]
        [lead] = self.feed()
        self.assertEqual(lead["id"], f"web-{inquiry_id}")
        self.assertEqual(lead["form_id"], "website-find-tutors")
        self.assertEqual(lead["field_data"], [{"name": "phone_number", "values": ["9876543210"]}])

    def test_class_and_subject_are_kept_when_sent(self) -> None:
        self.client.post(URL, json={"contactPhone": "9876543210", "classLevel": " Class 5 ", "subject": "Maths"})

        fields = {f["name"]: f["values"][0] for f in self.feed()[0]["field_data"]}
        self.assertEqual(fields, {"phone_number": "9876543210", "class": "Class 5", "subject": "Maths"})

    def test_every_submission_is_listed(self) -> None:
        for phone in ("9876543210", "9876543210", "8000000001"):
            self.assertEqual(self.client.post(URL, json={"contactPhone": phone}).status_code, 200)
        self.assertEqual(len(self.feed()), 3)

    def test_rejects_bad_phones(self) -> None:
        for phone in ("12345", "", "5123456780", "0123456789", "98765432101", "abcdefghij", "९८७६५४३२१०"):
            with self.subTest(phone=phone):
                response = self.client.post(URL, json={"contactPhone": phone})
                self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(self.feed(), [])

    def test_rejects_missing_phone_and_overlong_fields(self) -> None:
        self.assertEqual(self.client.post(URL, json={}).status_code, 422)
        self.assertEqual(self.client.post(URL, json={"contactPhone": "9876543210", "subject": "x" * 101}).status_code, 422)
        self.assertEqual(self.feed(), [])

    def test_feed_needs_the_sync_key(self) -> None:
        self.assertEqual(self.client.get(FEED).status_code, 401)
        self.assertEqual(self.client.get(FEED, headers={"X-Website-Sync-Key": "wrong"}).status_code, 401)


if __name__ == "__main__":
    unittest.main()
