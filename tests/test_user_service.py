"""使用者服務測試"""

import unittest

from werkzeug.security import check_password_hash

from app.services import user_service


class FakeUserRepo:
    def __init__(self):
        self.users = {}

    def find_by_username(self, username: str):
        return self.users.get(username)

    def insert_user(self, user: dict):
        self.users[user["User"]] = user

    def update_password(self, username: str, hashed_password: str):
        if username in self.users:
            self.users[username]["Password"] = hashed_password


class UserServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.fake_repo = FakeUserRepo()
        self._orig_repo = user_service.user_repo
        user_service.user_repo = self.fake_repo

    def tearDown(self):
        user_service.user_repo = self._orig_repo

    def test_authenticate_with_hashed_password(self):
        """測試使用雜湊密碼認證"""
        username = "testuser"
        password = "testpass123"
        hashed = user_service.hash_password(password)

        self.fake_repo.insert_user(
            {
                "User": username,
                "Password": hashed,
                "admin": False,
            }
        )

        self.assertTrue(user_service.authenticate(username, password))
        self.assertFalse(user_service.authenticate(username, "wrongpass"))

    def test_authenticate_with_plain_password_upgrade(self):
        """測試明文密碼認證並自動升級為雜湊"""
        username = "plainuser"
        password = "plainpass"

        self.fake_repo.insert_user(
            {
                "User": username,
                "Password": password,  # 明文密碼
                "admin": False,
            }
        )

        # 認證應該成功
        self.assertTrue(user_service.authenticate(username, password))

        # 密碼應該已被升級為雜湊
        user = self.fake_repo.find_by_username(username)
        self.assertTrue(user["Password"].startswith(("pbkdf2:", "scrypt:")))
        self.assertTrue(check_password_hash(user["Password"], password))

    def test_authenticate_user_not_found(self):
        """測試使用者不存在的情況"""
        self.assertFalse(user_service.authenticate("nonexistent", "password"))

    def test_authenticate_wrong_password(self):
        """測試錯誤密碼"""
        username = "testuser"
        hashed = user_service.hash_password("correctpass")

        self.fake_repo.insert_user(
            {
                "User": username,
                "Password": hashed,
                "admin": False,
            }
        )

        self.assertFalse(user_service.authenticate(username, "wrongpass"))

    def test_create_user_success(self):
        """測試成功建立使用者"""
        username = "newuser"
        password = "newpass123"

        result = user_service.create_user(username, password, admin=False)
        self.assertTrue(result)

        user = self.fake_repo.find_by_username(username)
        self.assertIsNotNone(user)
        self.assertEqual(user["User"], username)
        self.assertTrue(check_password_hash(user["Password"], password))
        self.assertFalse(user.get("admin", False))

    def test_create_user_duplicate(self):
        """測試建立重複使用者"""
        username = "duplicate"
        password = "pass123"

        # 第一次建立應該成功
        self.assertTrue(user_service.create_user(username, password))

        # 第二次建立應該失敗
        self.assertFalse(user_service.create_user(username, password))

    def test_create_user_with_admin_flag(self):
        """測試建立管理員使用者"""
        username = "adminuser"
        password = "adminpass"

        user_service.create_user(username, password, admin=True)
        user = self.fake_repo.find_by_username(username)
        self.assertTrue(user.get("admin", False))

    def test_get_user(self):
        """測試取得使用者資訊"""
        username = "testuser"
        self.fake_repo.insert_user(
            {
                "User": username,
                "Password": "hashed",
                "admin": False,
            }
        )

        user = user_service.get_user(username)
        self.assertIsNotNone(user)
        self.assertEqual(user["User"], username)

        # 不存在的使用者
        self.assertIsNone(user_service.get_user("nonexistent"))

    def test_hash_password(self):
        """測試密碼雜湊功能"""
        password = "testpass123"
        hashed = user_service.hash_password(password)

        # 應該是雜湊格式
        self.assertTrue(hashed.startswith(("pbkdf2:", "scrypt:")))
        # 應該能驗證原始密碼
        self.assertTrue(check_password_hash(hashed, password))
        # 錯誤密碼應該驗證失敗
        self.assertFalse(check_password_hash(hashed, "wrongpass"))


if __name__ == "__main__":
    unittest.main()
