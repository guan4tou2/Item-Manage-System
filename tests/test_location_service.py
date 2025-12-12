"""位置服務測試"""
import unittest
from bson import ObjectId

from app.services import location_service


class FakeLocationRepo:
    def __init__(self):
        self.locations = []

    def list_locations(self):
        for loc in self.locations:
            yield loc

    def insert_location(self, doc: dict):
        doc["_id"] = ObjectId()
        self.locations.append(doc)

    def delete_location(self, loc_id):
        self.locations = [l for l in self.locations if l["_id"] != loc_id]

    def update_location(self, loc_id, doc: dict):
        for loc in self.locations:
            if loc["_id"] == loc_id:
                loc.update(doc)
                break


class LocationServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.fake_repo = FakeLocationRepo()
        self._orig_repo = location_service.location_repo
        location_service.location_repo = self.fake_repo

    def tearDown(self):
        location_service.location_repo = self._orig_repo

    def test_list_locations(self):
        """測試列出所有位置"""
        self.fake_repo.insert_location({
            "floor": "1F",
            "room": "書房",
            "zone": "書桌",
        })
        self.fake_repo.insert_location({
            "floor": "2F",
            "room": "臥室",
            "zone": "衣櫃",
        })
        
        locations = location_service.list_locations()
        self.assertEqual(len(locations), 2)
        # 檢查 _id 是否轉換為字串
        self.assertIsInstance(locations[0]["_id"], str)

    def test_list_choices(self):
        """測試列出選擇選項"""
        self.fake_repo.insert_location({"floor": "1F", "room": "書房", "zone": "書桌"})
        self.fake_repo.insert_location({"floor": "2F", "room": "臥室", "zone": "衣櫃"})
        self.fake_repo.insert_location({"floor": "1F", "room": "客廳", "zone": "沙發"})
        
        floors, rooms, zones = location_service.list_choices()
        
        self.assertEqual(sorted(floors), ["1F", "2F"])
        self.assertEqual(sorted(rooms), ["客廳", "書房", "臥室"])
        self.assertEqual(sorted(zones), ["沙發", "書桌", "衣櫃"])

    def test_list_choices_empty(self):
        """測試空的位置列表"""
        floors, rooms, zones = location_service.list_choices()
        self.assertEqual(floors, [])
        self.assertEqual(rooms, [])
        self.assertEqual(zones, [])

    def test_create_location_success(self):
        """測試成功建立位置"""
        doc = {
            "floor": "1F",
            "room": "書房",
            "zone": "書桌",
        }
        
        ok, msg = location_service.create_location(doc)
        self.assertTrue(ok)
        self.assertIn("新增", msg)
        
        locations = location_service.list_locations()
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0]["floor"], "1F")

    def test_create_location_empty_fields(self):
        """測試建立位置時所有欄位為空"""
        doc = {}
        ok, msg = location_service.create_location(doc)
        self.assertFalse(ok)
        self.assertIn("至少填寫一個欄位", msg)

    def test_create_location_partial_fields(self):
        """測試建立位置時只有部分欄位"""
        doc = {"floor": "1F"}
        ok, msg = location_service.create_location(doc)
        self.assertTrue(ok)

    def test_create_location_duplicate(self):
        """測試建立重複位置"""
        doc = {
            "floor": "1F",
            "room": "書房",
            "zone": "書桌",
        }
        
        # 第一次建立應該成功
        ok1, _ = location_service.create_location(doc)
        self.assertTrue(ok1)
        
        # 第二次建立應該失敗
        ok2, msg2 = location_service.create_location(doc)
        self.assertFalse(ok2)
        self.assertIn("已存在", msg2)

    def test_delete_location_success(self):
        """測試成功刪除位置"""
        self.fake_repo.insert_location({"floor": "1F", "room": "書房", "zone": "書桌"})
        locations = location_service.list_locations()
        loc_id = locations[0]["_id"]
        
        location_service.delete_location(loc_id)
        
        locations_after = location_service.list_locations()
        self.assertEqual(len(locations_after), 0)

    def test_delete_location_invalid_id(self):
        """測試刪除無效 ID"""
        self.fake_repo.insert_location({"floor": "1F", "room": "書房", "zone": "書桌"})
        initial_count = len(location_service.list_locations())
        
        # 無效的 ID 應該不會拋出異常
        location_service.delete_location("invalid_id")
        
        # 數量應該不變
        self.assertEqual(len(location_service.list_locations()), initial_count)

    def test_update_location_success(self):
        """測試成功更新位置"""
        self.fake_repo.insert_location({"floor": "1F", "room": "書房", "zone": "書桌"})
        locations = location_service.list_locations()
        loc_id = locations[0]["_id"]
        
        updates = {"floor": "2F", "room": "臥室"}
        location_service.update_location(loc_id, updates)
        
        updated_locations = location_service.list_locations()
        self.assertEqual(updated_locations[0]["floor"], "2F")
        self.assertEqual(updated_locations[0]["room"], "臥室")
        self.assertEqual(updated_locations[0]["zone"], "書桌")  # 未更新的欄位保持不變

    def test_update_location_invalid_id(self):
        """測試更新無效 ID"""
        # 無效的 ID 應該不會拋出異常
        location_service.update_location("invalid_id", {"floor": "2F"})


if __name__ == "__main__":
    unittest.main()

