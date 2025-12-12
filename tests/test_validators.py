"""驗證器測試"""
import unittest

from app.validators import items as item_validator


class ItemValidatorTestCase(unittest.TestCase):
    def test_validate_required_fields(self):
        """測試必填欄位驗證"""
        # 缺少 ItemName
        data = {
            "ItemID": "A1",
            "ItemStorePlace": "書房",
            "ItemType": "文具",
            "ItemOwner": "Admin",
            "ItemGetDate": "2024-01-01",
        }
        ok, msg = item_validator.validate_item_fields(data)
        self.assertFalse(ok)
        self.assertIn("ItemName", msg)

    def test_validate_all_required_fields_present(self):
        """測試所有必填欄位都存在"""
        data = {
            "ItemName": "筆記本",
            "ItemID": "A1",
            "ItemStorePlace": "書房",
            "ItemType": "文具",
            "ItemOwner": "Admin",
            "ItemGetDate": "2024-01-01",
        }
        ok, msg = item_validator.validate_item_fields(data)
        self.assertTrue(ok)
        self.assertEqual(msg, "")

    def test_validate_item_type(self):
        """測試物品類型驗證"""
        data = {
            "ItemName": "筆記本",
            "ItemID": "A1",
            "ItemStorePlace": "書房",
            "ItemType": "不存在的類型",
            "ItemOwner": "Admin",
            "ItemGetDate": "2024-01-01",
        }
        valid_types = ["文具", "工具", "電子產品"]
        
        ok, msg = item_validator.validate_item_fields(data, valid_types=valid_types)
        self.assertFalse(ok)
        self.assertIn("類型不存在", msg)

    def test_validate_item_type_valid(self):
        """測試有效的物品類型"""
        data = {
            "ItemName": "筆記本",
            "ItemID": "A1",
            "ItemStorePlace": "書房",
            "ItemType": "文具",
            "ItemOwner": "Admin",
            "ItemGetDate": "2024-01-01",
        }
        valid_types = ["文具", "工具", "電子產品"]
        
        ok, msg = item_validator.validate_item_fields(data, valid_types=valid_types)
        self.assertTrue(ok)

    def test_validate_location_fields(self):
        """測試位置欄位驗證"""
        data = {
            "ItemName": "筆記本",
            "ItemID": "A1",
            "ItemStorePlace": "書房",
            "ItemType": "文具",
            "ItemOwner": "Admin",
            "ItemGetDate": "2024-01-01",
            "ItemFloor": "不存在的樓層",
        }
        valid_floors = ["1F", "2F", "B1"]
        valid_rooms = ["書房", "臥室"]
        valid_zones = ["書桌", "衣櫃"]
        
        ok, msg = item_validator.validate_item_fields(
            data,
            valid_floors=valid_floors,
            valid_rooms=valid_rooms,
            valid_zones=valid_zones,
        )
        self.assertFalse(ok)
        self.assertIn("樓層", msg)

    def test_validate_location_fields_valid(self):
        """測試有效的位置欄位"""
        data = {
            "ItemName": "筆記本",
            "ItemID": "A1",
            "ItemStorePlace": "書房",
            "ItemType": "文具",
            "ItemOwner": "Admin",
            "ItemGetDate": "2024-01-01",
            "ItemFloor": "1F",
            "ItemRoom": "書房",
            "ItemZone": "書桌",
        }
        valid_floors = ["1F", "2F"]
        valid_rooms = ["書房", "臥室"]
        valid_zones = ["書桌", "衣櫃"]
        
        ok, msg = item_validator.validate_item_fields(
            data,
            valid_floors=valid_floors,
            valid_rooms=valid_rooms,
            valid_zones=valid_zones,
        )
        self.assertTrue(ok)

    def test_validate_date_format(self):
        """測試日期格式驗證"""
        data = {
            "ItemName": "筆記本",
            "ItemID": "A1",
            "ItemStorePlace": "書房",
            "ItemType": "文具",
            "ItemOwner": "Admin",
            "ItemGetDate": "2024-01-01",
            "WarrantyExpiry": "2024-13-01",  # 無效月份
        }
        
        ok, msg = item_validator.validate_item_fields(data)
        self.assertFalse(ok)
        self.assertIn("保固期限", msg)
        self.assertIn("YYYY-MM-DD", msg)

    def test_validate_date_format_valid(self):
        """測試有效的日期格式"""
        data = {
            "ItemName": "筆記本",
            "ItemID": "A1",
            "ItemStorePlace": "書房",
            "ItemType": "文具",
            "ItemOwner": "Admin",
            "ItemGetDate": "2024-01-01",
            "WarrantyExpiry": "2024-12-31",
            "UsageExpiry": "2025-06-30",
        }
        
        ok, msg = item_validator.validate_item_fields(data)
        self.assertTrue(ok)

    def test_validate_date_get_date_invalid(self):
        """測試取得日期格式無效"""
        data = {
            "ItemName": "筆記本",
            "ItemID": "A1",
            "ItemStorePlace": "書房",
            "ItemType": "文具",
            "ItemOwner": "Admin",
            "ItemGetDate": "2024/01/01",  # 錯誤格式
        }
        
        ok, msg = item_validator.validate_item_fields(data)
        self.assertFalse(ok)
        self.assertIn("取得日期", msg)

    def test_validate_optional_date_fields(self):
        """測試可選日期欄位為空時不驗證"""
        data = {
            "ItemName": "筆記本",
            "ItemID": "A1",
            "ItemStorePlace": "書房",
            "ItemType": "文具",
            "ItemOwner": "Admin",
            "ItemGetDate": "2024-01-01",
            # WarrantyExpiry 和 UsageExpiry 為空
        }
        
        ok, msg = item_validator.validate_item_fields(data)
        self.assertTrue(ok)

    def test_validate_location_optional(self):
        """測試位置欄位為可選"""
        data = {
            "ItemName": "筆記本",
            "ItemID": "A1",
            "ItemStorePlace": "書房",
            "ItemType": "文具",
            "ItemOwner": "Admin",
            "ItemGetDate": "2024-01-01",
            # ItemFloor, ItemRoom, ItemZone 為空
        }
        
        ok, msg = item_validator.validate_item_fields(
            data,
            valid_floors=["1F"],
            valid_rooms=["書房"],
            valid_zones=["書桌"],
        )
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()

