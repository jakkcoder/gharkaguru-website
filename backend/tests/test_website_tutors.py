"""Website tutor registrations become phone-keyed GCS leads."""

from __future__ import annotations

import json
import unittest

from app.website_tutors import merge_tutor_lead, tutor_lead_document


ANSWERS = {
    "full_name": "Asha Rao",
    "location": "Rajapuri, Delhi",
    "pin": "110059",
    "subject": "Maths, Science",
    "class_can_teach": "6 to 10",
    "education": "B.Sc",
    "medium": "Both",
    "teaching_mode": "Home",
}


class WebsiteTutorLeadTest(unittest.TestCase):
    def test_document_keeps_only_teacher_pipeline_fields(self) -> None:
        lead = tutor_lead_document("+91 9876543210", ANSWERS, created_time="2026-10-01T00:00:00+00:00")
        self.assertEqual(lead["id"], "web-9876543210")
        self.assertEqual(lead["form_name"], "Become a Home Tutor")
        self.assertEqual(
            set(lead["fields"]),
            {
                "full_name",
                "phone_number",
                "location",
                "pin",
                "subject",
                "class_can_teach",
                "educational_background",
                "english_hindi_medium",
                "online_offline",
            },
        )
        self.assertEqual(lead["fields"]["phone_number"], "9876543210")
        self.assertNotIn("photo", json.dumps(lead))
        self.assertNotIn("email", lead["fields"])

    def test_merge_replaces_the_same_phone(self) -> None:
        first = tutor_lead_document("9876543210", ANSWERS)
        updated = tutor_lead_document("9876543210", {**ANSWERS, "subject": "English"})
        other = tutor_lead_document("9000000001", {**ANSWERS, "full_name": "Other"})
        merged = merge_tutor_lead({"leads": [first, other]}, updated)
        by_id = {item["id"]: item for item in merged["leads"]}
        self.assertEqual(len(by_id), 2)
        self.assertEqual(by_id["web-9876543210"]["fields"]["subject"], "English")
        self.assertEqual(by_id["web-9000000001"]["fields"]["full_name"], "Other")


if __name__ == "__main__":
    unittest.main()
