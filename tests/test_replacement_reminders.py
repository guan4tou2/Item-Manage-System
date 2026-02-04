import unittest
from datetime import date, timedelta

from app.services import item_service


class FakeItemRepo:
    def __init__(self, items):
        self.items = items

    def list_items(self, filter_query, projection, sort=None, skip=0, limit=None):
        for item in self.items:
            yield {k: v for k, v in item.items() if k in projection or projection.get("_id") == 0}


class ReplacementReminderTestCase(unittest.TestCase):
    def setUp(self):
        self._orig_repo = item_service.item_repo

    def tearDown(self):
        item_service.item_repo = self._orig_repo

    def _set_repo(self, items):
        item_service.item_repo = FakeItemRepo(items)

    def test_disabled_replacement(self):
        self._set_repo([])
        settings = {"replacement_enabled": False}
        result = item_service.get_replacement_items(settings)
        self.assertFalse(result["enabled"])
        self.assertEqual(result["total_alerts"], 0)

    def test_due_and_upcoming(self):
        today = date.today()
        due_date = (today - timedelta(days=90)).strftime("%Y-%m-%d")  # underwear rule 90
        upcoming_date = (today - timedelta(days=170)).strftime("%Y-%m-%d")  # socks rule 180 -> 10 days left
        items = [
            {"ItemName": "內衣", "ItemID": "U1", "ItemType": "服飾", "ItemGetDate": due_date},
            {"ItemName": "襪子", "ItemID": "S1", "ItemType": "服飾", "ItemGetDate": upcoming_date},
        ]
        self._set_repo(items)

        result = item_service.get_replacement_items({"replacement_enabled": True})

        self.assertTrue(result["enabled"])
        self.assertEqual(len(result["due"]), 1)
        self.assertEqual(len(result["upcoming"]), 1)
        self.assertEqual(result["due"][0]["ItemID"], "U1")
        self.assertEqual(result["upcoming"][0]["ItemID"], "S1")
        self.assertGreaterEqual(result["total_alerts"], 2)

    def test_custom_rule_parsing(self):
        today = date.today()
        custom_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        items = [
            {"ItemName": "運動毛巾", "ItemID": "T1", "ItemType": "運動", "ItemGetDate": custom_date},
        ]
        self._set_repo(items)

        settings = {
            "replacement_enabled": True,
            "replacement_intervals": ["運動毛巾=20"],
        }
        result = item_service.get_replacement_items(settings)
        self.assertEqual(len(result["due"]), 1)
        self.assertEqual(result["due"][0]["ItemID"], "T1")


if __name__ == "__main__":
    unittest.main()
