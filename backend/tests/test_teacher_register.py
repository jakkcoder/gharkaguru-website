"""Public tutor registration takes the phone in the form, with no login."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="website-register-tests-"))
os.environ.setdefault("PULL_ON_STARTUP", "false")

from fastapi.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402
from app.db import connect, init_db  # noqa: E402

PHONE = "9123456780"
SYNC_KEY = "test-sync-key"

FORM = {
    "phone": f"+91 {PHONE}",
    "fullName": "Asha Rao",
    "location": "Rajapuri, Delhi",
    "pin": "110059",
    "subject": "Maths, Science",
    "classCanTeach": "6 to 10",
    "education": "B.Sc",
    "medium": "Both",
    "teachingMode": "Home",
}


class TeacherRegisterTest(unittest.TestCase):
    def setUp(self) -> None:
        init_db()
        with connect() as conn:
            conn.execute("DELETE FROM teacher_applications")
            conn.execute("DELETE FROM teacher_registry")
            conn.execute("DELETE FROM website_tutor_leads")
            conn.commit()
        # No `with`: skip the lifespan, which would pull from GCS.
        self.client = TestClient(main.app)
        patches = {
            "append": mock.patch.object(main, "append_website_tutor", return_value={"id": f"web-{PHONE}"}),
            "sync": mock.patch.object(main, "sync_to_gcs"),
            "env": mock.patch.dict(os.environ, {"WEBSITE_SYNC_SECRET": SYNC_KEY, "SKIP_GCS_SYNC": "true"}),
        }
        for name, patch in patches.items():
            setattr(self, name, patch.start())
            self.addCleanup(patch.stop)

    def register(self, **changes: str):
        return self.client.post("/v1/api/teacher/register", data={**FORM, **changes})

    def saved_leads(self) -> list[dict]:
        with connect(read_only=True) as conn:
            return [json.loads(row[0]) for row in conn.execute("SELECT lead_json FROM website_tutor_leads")]

    def assert_rejected(self, response, code: str = "INVALID") -> None:
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json()["detail"]["error"]["code"], code)
        self.assertEqual(self.saved_leads(), [])

    def test_saves_to_sqlite_without_login_or_gcs(self) -> None:
        response = self.register()

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"referenceId": f"web-{PHONE}"})
        self.append.assert_not_called()
        self.sync.assert_not_called()
        [lead] = self.saved_leads()
        self.assertEqual(lead["id"], f"web-{PHONE}")
        self.assertEqual(lead["fields"]["phone_number"], PHONE)
        self.assertEqual(lead["fields"]["full_name"], "Asha Rao")
        self.assertEqual(lead["fields"]["pin"], "110059")
        with connect(read_only=True) as conn:
            registry = conn.execute(
                "SELECT full_name, source FROM teacher_registry WHERE phone = ?", (PHONE,)
            ).fetchone()
        self.assertEqual(registry["full_name"], "Asha Rao")
        self.assertEqual(registry["source"], "website")

    def test_gcs_failure_does_not_fail_the_form(self) -> None:
        self.append.side_effect = RuntimeError("Your default credentials were not found.")
        with mock.patch.dict(os.environ, {"SKIP_GCS_SYNC": ""}):
            response = self.register()

        self.assertEqual(response.status_code, 200, response.text)
        self.append.assert_called_once()
        self.assertEqual(len(self.saved_leads()), 1)

    def test_resubmitting_updates_one_row_and_keeps_first_time(self) -> None:
        self.register()
        first = self.saved_leads()[0]["created_time"]
        response = self.register(phone=PHONE, subject="English")

        self.assertEqual(response.status_code, 200, response.text)
        [lead] = self.saved_leads()
        self.assertEqual(lead["fields"]["subject"], "English")
        self.assertEqual(lead["created_time"], first)

    def test_accepts_phone_formats(self) -> None:
        for raw in ("9123456780", "+91 91234 56780", "919123456780", "91234-56780 "):
            with self.subTest(raw=raw):
                self.assertEqual(self.register(phone=raw).status_code, 200)
        self.assertEqual(len(self.saved_leads()), 1)

    def test_trims_whitespace(self) -> None:
        response = self.register(fullName="  Asha Rao  ", pin=" 110059 ", subject="\tMaths\n")

        self.assertEqual(response.status_code, 200, response.text)
        fields = self.saved_leads()[0]["fields"]
        self.assertEqual(fields["full_name"], "Asha Rao")
        self.assertEqual(fields["pin"], "110059")
        self.assertEqual(fields["subject"], "Maths")

    def test_keeps_hindi_and_markup_as_plain_text(self) -> None:
        response = self.register(fullName="आशा राव", location="<script>alert(1)</script> Delhi", education="बी.एससी")

        self.assertEqual(response.status_code, 200, response.text)
        fields = self.saved_leads()[0]["fields"]
        self.assertEqual(fields["full_name"], "आशा राव")
        self.assertEqual(fields["location"], "<script>alert(1)</script> Delhi")

    def test_rejects_bad_phones(self) -> None:
        for raw in ("12345", "", "abcdefghij", "91234567801", "0123456789"):
            with self.subTest(raw=raw):
                response = self.register(phone=raw)
                # An empty form value counts as missing, which FastAPI answers with 422.
                self.assertIn(response.status_code, (400, 422), response.text)
        self.assertEqual(self.saved_leads(), [])

    def test_rejects_phone_starting_below_6(self) -> None:
        self.assert_rejected(self.register(phone="5123456780"))

    def test_rejects_bad_pins(self) -> None:
        for pin in ("1100", "1100590", "11005a", "011005", "११००५९", "      "):
            with self.subTest(pin=pin):
                self.assert_rejected(self.register(pin=pin))

    def test_rejects_blank_fields(self) -> None:
        for field in ("fullName", "location", "subject", "classCanTeach", "education"):
            with self.subTest(field=field):
                self.assert_rejected(self.register(**{field: "   "}))

    def test_rejects_missing_fields(self) -> None:
        data = {k: v for k, v in FORM.items() if k != "education"}
        response = self.client.post("/v1/api/teacher/register", data=data)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.saved_leads(), [])

    def test_rejects_unknown_choices(self) -> None:
        self.assert_rejected(self.register(medium="French"))
        self.assert_rejected(self.register(teachingMode="Anywhere"))

    def test_rejects_overlong_answers(self) -> None:
        self.assert_rejected(self.register(fullName="A" * 101))
        self.assert_rejected(self.register(location="x" * 301))
        self.assert_rejected(self.register(fullName="A"))

    def test_pipeline_endpoint_needs_the_sync_key(self) -> None:
        self.register()
        url = "/v1/api/internal/website-tutors"
        self.assertEqual(self.client.get(url).status_code, 401)
        self.assertEqual(self.client.get(url, headers={"X-Website-Sync-Key": "wrong"}).status_code, 401)

        response = self.client.get(url, headers={"X-Website-Sync-Key": SYNC_KEY})
        self.assertEqual(response.status_code, 200, response.text)
        [lead] = response.json()["leads"]
        self.assertEqual(lead["id"], f"web-{PHONE}")
        self.assertEqual(lead["form_name"], "Become a Home Tutor")


if __name__ == "__main__":
    unittest.main()
