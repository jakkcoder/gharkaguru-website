"""Public tutor registration takes the phone in the form, with no login."""

from __future__ import annotations

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
            conn.execute("DELETE FROM teacher_applications WHERE phone = ?", (PHONE,))
            conn.execute("DELETE FROM teacher_registry WHERE phone = ?", (PHONE,))
            conn.commit()
        # No `with`: skip the lifespan, which would pull from GCS.
        self.client = TestClient(main.app)
        append = mock.patch.object(main, "append_website_tutor", return_value={"id": f"web-{PHONE}"})
        sync = mock.patch.object(main, "sync_to_gcs")
        self.append = append.start()
        self.sync = sync.start()
        self.addCleanup(append.stop)
        self.addCleanup(sync.stop)

    def test_saves_to_gcs_without_login(self) -> None:
        response = self.client.post("/v1/api/teacher/register", data=FORM)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"referenceId": f"web-{PHONE}"})
        self.append.assert_called_once()
        phone, answers = self.append.call_args.args
        self.assertEqual(phone, PHONE)
        self.assertEqual(answers["full_name"], "Asha Rao")
        self.assertEqual(answers["pin"], "110059")
        self.sync.assert_called_once()
        with connect(read_only=True) as conn:
            application = conn.execute(
                "SELECT 1 FROM teacher_applications WHERE phone = ?", (PHONE,)
            ).fetchone()
            registry = conn.execute(
                "SELECT full_name, source FROM teacher_registry WHERE phone = ?", (PHONE,)
            ).fetchone()
        self.assertIsNone(application)
        self.assertEqual(registry["full_name"], "Asha Rao")
        self.assertEqual(registry["source"], "website")

    def test_rejects_bad_phone(self) -> None:
        response = self.client.post("/v1/api/teacher/register", data={**FORM, "phone": "12345"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"]["error"]["code"], "INVALID_PHONE")
        self.append.assert_not_called()
        self.sync.assert_not_called()

    def test_rejects_bad_pin(self) -> None:
        response = self.client.post("/v1/api/teacher/register", data={**FORM, "pin": "1100"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"]["error"]["code"], "INVALID")
        self.append.assert_not_called()
        self.sync.assert_not_called()


if __name__ == "__main__":
    unittest.main()
