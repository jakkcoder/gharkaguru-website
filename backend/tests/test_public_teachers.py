"""Public teacher profiles must come from teacher records and omit phone numbers."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.public_teachers import get_teacher, load_teachers, search_teachers


class PublicTeachersTest(unittest.TestCase):
    def test_catalog_has_real_names_and_no_phones(self) -> None:
        raw = json.loads(
            Path(__file__).resolve().parents[1].joinpath("app/data/public_teachers.json").read_text()
        )
        self.assertGreater(len(raw), 1000)
        blob = json.dumps(raw)
        for forbidden in ("phone", "phone_number", "phone_normalized", "photoUrl"):
            self.assertNotIn(f'"{forbidden}"', blob)
        teachers = load_teachers()
        self.assertEqual(teachers[0]["photoUrl"], "")
        self.assertTrue(teachers[0]["name"])
        self.assertTrue(teachers[0]["address"])
        self.assertNotIn("phone", teachers[0])

    def test_search_filters_location_without_exposing_contact(self) -> None:
        page = search_teachers(location="Rohini", page=1, page_size=5)
        self.assertGreater(page["total"], 0)
        self.assertLessEqual(len(page["items"]), 5)
        for item in page["items"]:
            self.assertIn("rohini", (item["address"] + item["city"]).lower())
            self.assertEqual(item["photoUrl"], "")
            self.assertNotIn("phone", item)

    def test_profile_lookup(self) -> None:
        teacher = load_teachers()[0]
        found = get_teacher(teacher["id"])
        self.assertIsNotNone(found)
        assert found is not None
        self.assertEqual(found["name"], teacher["name"])
        self.assertEqual(found["gallery"], [])
        self.assertIsNone(get_teacher("missing"))


if __name__ == "__main__":
    unittest.main()
