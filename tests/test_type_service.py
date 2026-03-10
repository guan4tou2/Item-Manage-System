"""類型服務測試"""
import unittest

from app.services import type_service


class FakeTypeRepo:
    def __init__(self):
        self.types = []

    def list_types(self):
        for t in self.types:
            yield t

    def insert_type(self, type_data):
        if isinstance(type_data, dict):
            self.types.append(type_data)
        else:
            self.types.append({"name": type_data})


class TypeServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.fake_repo = FakeTypeRepo()
        self._orig_repo = type_service.type_repo
        type_service.type_repo = self.fake_repo

    def tearDown(self):
        type_service.type_repo = self._orig_repo

    def test_list_types(self):
        """測試列出所有類型"""
        self.fake_repo.insert_type({"name": "文具"})
        self.fake_repo.insert_type({"name": "工具"})
        self.fake_repo.insert_type({"name": "電子產品"})
        
        types = type_service.list_types()
        type_list = list(types)
        
        self.assertGreaterEqual(len(type_list), 20)
        names = [t["name"] for t in type_list]
        self.assertIn("文具", names)
        self.assertIn("工具", names)
        self.assertIn("電子產品", names)
        self.assertIn("清潔用品", names)
        self.assertIn("廚房用品", names)
        self.assertIn("藥品", names)
        self.assertIn("保健食品", names)

    def test_list_types_empty(self):
        """測試空類型列表會自動補入預設類型"""
        types = type_service.list_types()
        names = [t["name"] for t in list(types)]
        self.assertIn("家電", names)
        self.assertIn("衣物", names)
        self.assertIn("藥品", names)
        self.assertIn("保健食品", names)

    def test_create_type(self):
        """測試建立類型"""
        type_data = {"name": "新類型"}
        
        type_service.create_type(type_data)
        
        types = list(type_service.list_types())
        self.assertIn("新類型", [t["name"] for t in types])

    def test_list_types_backfills_missing_health_related_types(self):
        self.fake_repo.insert_type({"name": "文具"})
        self.fake_repo.insert_type({"name": "工具"})

        names = [t["name"] for t in type_service.list_types()]

        self.assertIn("急救防災", names)
        self.assertIn("藥品", names)
        self.assertIn("保健食品", names)


if __name__ == "__main__":
    unittest.main()
