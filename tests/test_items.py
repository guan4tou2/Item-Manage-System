import unittest
from unittest import mock

from app.services import item_service


class FakeItemRepo:
    def __init__(self, items):
        self.items = items
        self.inserted_items = []
        self.updated_items = {}
        self.deleted_items = []

    def list_items(self, filter_query, projection, sort=None, skip=0, limit=None):
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

        # 應用分頁
        paginated = matched[skip:]
        if limit:
            paginated = paginated[:limit]

        for item in paginated:
            yield {k: v for k, v in item.items() if k in projection or projection.get("_id") == 0}

    def count_items(self, filter_query):
        def match(item):
            for key, condition in filter_query.items():
                if isinstance(condition, dict) and "$regex" in condition:
                    if condition["$regex"].lower() not in item.get(key, "").lower():
                        return False
                else:
                    if item.get(key) != condition:
                        return False
            return True
        return len([i for i in self.items if match(i)])

    def find_item_by_id(self, item_id, projection=None):
        for item in self.items:
            if item.get("ItemID") == item_id:
                if projection:
                    return {k: v for k, v in item.items() if k in projection or projection.get("_id") == 0}
                return item
        return None

    def insert_item(self, item_data):
        self.inserted_items.append(item_data)

    def update_item_by_id(self, item_id, updates):
        self.updated_items[item_id] = updates

    def delete_item_by_id(self, item_id):
        for item in self.items:
            if item.get("ItemID") == item_id:
                self.deleted_items.append(item_id)
                return True
        return False


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
        """測試依名稱搜尋"""
        result = item_service.list_items({"q": "筆記", "place": "", "type": ""})
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["ItemID"], "A1")
        self.assertEqual(result["total"], 1)

    def test_search_by_place(self):
        """測試依位置搜尋"""
        result = item_service.list_items({"q": "", "place": "工具", "type": ""})
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["ItemID"], "B2")

    def test_search_by_type(self):
        """測試依類型搜尋"""
        result = item_service.list_items({"q": "", "place": "", "type": "文具"})
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["ItemID"], "A1")

    def test_search_by_floor_room_zone(self):
        """測試依樓層、房間、區域搜尋"""
        result = item_service.list_items(
            {"q": "", "place": "", "type": "", "floor": "1F", "room": "書房", "zone": "書桌"}
        )
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["ItemID"], "A1")

    def test_expiry_annotation(self):
        """測試過期狀態註解"""
        result = item_service.list_items({"q": "", "place": "", "type": ""})
        items = result["items"]
        a1 = next(i for i in items if i["ItemID"] == "A1")
        b2 = next(i for i in items if i["ItemID"] == "B2")
        self.assertEqual(a1["WarrantyStatus"], "ok")
        self.assertIn(b2["WarrantyStatus"], ["expired", "near", "ok", "invalid"])

    def test_sort_by_warranty(self):
        """測試依保固期限排序"""
        result = item_service.list_items({"q": "", "place": "", "type": "", "sort": "warranty"})
        # B2 有較舊的日期，應該排在前面
        self.assertEqual(result["items"][0]["ItemID"], "B2")

    def test_sort_by_name(self):
        """測試依名稱排序"""
        result = item_service.list_items({"q": "", "place": "", "type": "", "sort": "name"})
        items = result["items"]
        # 依名稱排序，"筆記本" 應該在 "螺絲起子" 之前
        self.assertEqual(items[0]["ItemName"], "筆記本")
        self.assertEqual(items[1]["ItemName"], "螺絲起子")

    def test_sort_by_usage(self):
        """測試依使用期限排序"""
        result = item_service.list_items({"q": "", "place": "", "type": "", "sort": "usage"})
        # B2 有較舊的使用期限，應該排在前面
        self.assertEqual(result["items"][0]["ItemID"], "B2")

    def test_pagination(self):
        """測試分頁功能"""
        # 添加更多測試資料
        for i in range(15):
            self.sample_items.append({
                "ItemName": f"物品{i}",
                "ItemID": f"C{i}",
                "ItemStorePlace": "倉庫",
                "ItemType": "其他",
                "ItemOwner": "Admin",
            })
        
        # 重新設定 repo
        item_service.item_repo = FakeItemRepo(self.sample_items)
        
        # 測試第一頁
        result = item_service.list_items({"q": "", "place": "", "type": ""}, page=1, page_size=12)
        self.assertEqual(len(result["items"]), 12)
        self.assertEqual(result["page"], 1)
        self.assertEqual(result["page_size"], 12)
        self.assertTrue(result["has_next"])
        self.assertFalse(result["has_prev"])
        
        # 測試第二頁
        result = item_service.list_items({"q": "", "place": "", "type": ""}, page=2, page_size=12)
        self.assertEqual(len(result["items"]), 5)  # 17 - 12 = 5
        self.assertEqual(result["page"], 2)
        self.assertTrue(result["has_prev"])
        self.assertFalse(result["has_next"])

    def test_get_item(self):
        """測試取得單個物品"""
        item = item_service.get_item("A1")
        self.assertIsNotNone(item)
        self.assertEqual(item["ItemID"], "A1")
        self.assertEqual(item["ItemName"], "筆記本")
        # 應該有過期狀態註解
        self.assertIn("WarrantyStatus", item)
        self.assertIn("UsageStatus", item)

    def test_get_item_not_found(self):
        """測試取得不存在的物品"""
        item = item_service.get_item("NONEXISTENT")
        self.assertIsNone(item)

    def test_create_item_success(self):
        """測試成功建立物品"""
        with mock.patch("app.services.item_service._filter_valid_types", return_value=["文具", "工具"]), \
             mock.patch("app.services.location_service.list_choices", return_value=(["1F"], ["書房"], ["書桌"])), \
             mock.patch("app.validators.items.validate_item_fields", return_value=(True, "")), \
             mock.patch("app.utils.storage.save_upload", return_value=None):
            
            form_data = {
                "ItemName": "新物品",
                "ItemID": "NEW1",
                "ItemStorePlace": "書房",
                "ItemType": "文具",
                "ItemOwner": "Admin",
                "ItemGetDate": "2024-01-01",
            }
            
            ok, msg = item_service.create_item(form_data, None)
            self.assertTrue(ok)
            self.assertIn("成功", msg)
            self.assertEqual(len(item_service.item_repo.inserted_items), 1)

    def test_create_item_validation_failure(self):
        """測試建立物品時驗證失敗"""
        with mock.patch("app.services.item_service._filter_valid_types", return_value=["文具", "工具"]), \
             mock.patch("app.services.location_service.list_choices", return_value=(["1F"], ["書房"], ["書桌"])), \
             mock.patch("app.validators.items.validate_item_fields", return_value=(False, "驗證失敗")):
            
            form_data = {"ItemName": ""}  # 缺少必填欄位
            ok, msg = item_service.create_item(form_data, None)
            self.assertFalse(ok)
            self.assertEqual(msg, "驗證失敗")

    def test_update_item_success(self):
        """測試成功更新物品"""
        with mock.patch("app.services.item_service._filter_valid_types", return_value=["文具", "工具"]), \
             mock.patch("app.services.location_service.list_choices", return_value=(["1F"], ["書房"], ["書桌"])), \
             mock.patch("app.validators.items.validate_item_fields", return_value=(True, "")):
            
            form_data = {
                "ItemName": "更新後的物品",
                "ItemID": "A1",  # 這個欄位會被移除
                "ItemStorePlace": "書房",
                "ItemType": "文具",
                "ItemOwner": "Admin",
                "ItemGetDate": "2024-01-01",
            }
            
            ok, msg = item_service.update_item("A1", form_data, None)
            self.assertTrue(ok)
            self.assertIn("成功", msg)
            self.assertIn("A1", item_service.item_repo.updated_items)

    def test_update_item_not_found(self):
        """測試更新不存在的物品"""
        form_data = {"ItemName": "測試"}
        ok, msg = item_service.update_item("NONEXISTENT", form_data, None)
        self.assertFalse(ok)
        self.assertIn("找不到", msg)

    def test_delete_item_success(self):
        """測試成功刪除物品"""
        ok, msg = item_service.delete_item("A1")
        self.assertTrue(ok)
        self.assertIn("刪除", msg)
        self.assertIn("A1", item_service.item_repo.deleted_items)

    def test_delete_item_not_found(self):
        """測試刪除不存在的物品"""
        ok, msg = item_service.delete_item("NONEXISTENT")
        self.assertFalse(ok)
        self.assertIn("找不到", msg)

    def test_update_item_place(self):
        """測試更新物品位置"""
        updates = {
            "ItemStorePlace": "新位置",
            "ItemFloor": "2F",
            "ItemRoom": "臥室",
            "ItemZone": "衣櫃",
        }
        item_service.update_item_place("A1", updates)
        self.assertIn("A1", item_service.item_repo.updated_items)
        self.assertEqual(item_service.item_repo.updated_items["A1"]["ItemStorePlace"], "新位置")


if __name__ == "__main__":
    unittest.main()

