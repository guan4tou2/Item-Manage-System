"""類型服務測試"""
import unittest

from app.services import type_service


class FakeTypeRepo:
    def __init__(self):
        self.types = []

    def list_types(self):
        for t in self.types:
            yield t

    def insert_type(self, type_data: dict):
        self.types.append(type_data)


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
        
        self.assertEqual(len(type_list), 3)
        names = [t["name"] for t in type_list]
        self.assertIn("文具", names)
        self.assertIn("工具", names)
        self.assertIn("電子產品", names)

    def test_list_types_empty(self):
        """測試空類型列表"""
        types = type_service.list_types()
        self.assertEqual(list(types), [])

    def test_create_type(self):
        """測試建立類型"""
        type_data = {"name": "新類型"}
        
        type_service.create_type(type_data)
        
        types = list(type_service.list_types())
        self.assertEqual(len(types), 1)
        self.assertEqual(types[0]["name"], "新類型")


if __name__ == "__main__":
    unittest.main()

