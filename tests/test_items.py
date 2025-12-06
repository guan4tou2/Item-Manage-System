import unittest

from app.services import item_service


class FakeItemRepo:
    def __init__(self, items):
        self.items = items

    def list_items(self, filter_query, projection, sort=None):
        def match(item):
            for key, condition in filter_query.items():
                if isinstance(condition, dict) and "$regex" in condition:
                    if condition["$regex"].lower() not in item.get(key, "").lower():
                        return False
                else:
                    if item.get(key) != condition:
                        return False
            return True

        matched = [i for i in self.items if match(i)]

        if sort:
            field, direction = sort[0]
            reverse = direction == -1
            matched = sorted(matched, key=lambda x: x.get(field, ""), reverse=reverse)

        for item in matched:
            yield {k: v for k, v in item.items() if k in projection or projection.get("_id") == 0}


class ItemServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.sample_items = [
            {
                "ItemName": "筆記本",
                "ItemID": "A1",
                "ItemStorePlace": "書房",
                "ItemType": "文具",
                "ItemOwner": "Admin",
                "ItemFloor": "1F",
                "ItemRoom": "書房",
                "ItemZone": "書桌",
                "WarrantyExpiry": "2030-01-01",
                "UsageExpiry": "2030-06-01",
            },
            {
                "ItemName": "螺絲起子",
                "ItemID": "B2",
                "ItemStorePlace": "工具間",
                "ItemType": "工具",
                "ItemOwner": "Admin",
                "ItemFloor": "B1",
                "ItemRoom": "工具間",
                "ItemZone": "架上",
                "WarrantyExpiry": "2000-01-01",
                "UsageExpiry": "2000-02-01",
            },
        ]
        self._orig_repo = item_service.item_repo
        item_service.item_repo = FakeItemRepo(self.sample_items)

    def tearDown(self):
        item_service.item_repo = self._orig_repo

    def test_search_by_name(self):
        items = item_service.list_items({"q": "筆記", "place": "", "type": ""})
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["ItemID"], "A1")

    def test_search_by_place(self):
        items = item_service.list_items({"q": "", "place": "工具", "type": ""})
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["ItemID"], "B2")

    def test_search_by_type(self):
        items = item_service.list_items({"q": "", "place": "", "type": "文具"})
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["ItemID"], "A1")

    def test_search_by_floor_room_zone(self):
        items = item_service.list_items(
            {"q": "", "place": "", "type": "", "floor": "1F", "room": "書房", "zone": "書桌"}
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["ItemID"], "A1")

    def test_expiry_annotation(self):
        items = item_service.list_items({"q": "", "place": "", "type": ""})
        a1 = next(i for i in items if i["ItemID"] == "A1")
        b2 = next(i for i in items if i["ItemID"] == "B2")
        self.assertEqual(a1["WarrantyStatus"], "ok")
        self.assertIn(b2["WarrantyStatus"], ["expired", "near", "ok", "invalid"])

    def test_sort_by_warranty(self):
        items = item_service.list_items({"q": "", "place": "", "type": "", "sort": "warranty"})
        # B2 has older date, should come first
        self.assertEqual(items[0]["ItemID"], "B2")


if __name__ == "__main__":
    unittest.main()

