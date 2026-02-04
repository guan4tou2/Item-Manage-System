"""使用者服務測試"""

import unittest

from werkzeug.security import check_password_hash

from app.services import user_service


class FakeUserRepo:
    def __init__(self):
        self.users = {}

    def find_by_username(self, username: str):
        return self.users.get(username)

    def find_by_username_case_insensitive(self, username: str):
        for k, v in self.users.items():
            if k.lower() == username.lower():
                return v
        return None

    def get_lock_status(self, username: str):
        return None

    def get_failed_attempts(self, username: str):
        return 0

    def reset_failed_attempts(self, username: str):
        return None

    def update_lock_status(self, username: str, locked_until: str):
        return None

    def record_login(self, username: str, ip: str, success: bool):
        return None

    def insert_user(self, user: dict):
        self.users[user["User"]] = user

    def update_password(self, username: str, hashed_password: str):
        if username in self.users:
            self.users[username]["Password"] = hashed_password

    def mark_password_changed(self, username: str):
        if username in self.users:
            self.users[username]["password_changed"] = True


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

        ok, _ = user_service.authenticate(username, password)
        self.assertTrue(ok)
        ok_wrong, _ = user_service.authenticate(username, "wrongpass")
        self.assertFalse(ok_wrong)

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

        ok, _ = user_service.authenticate(username, password)
        self.assertTrue(ok)

        user = self.fake_repo.find_by_username(username)
        self.assertIsNotNone(user)
        assert user is not None
        self.assertTrue(user["Password"].startswith(("pbkdf2:", "scrypt:")))
        self.assertTrue(check_password_hash(user["Password"], password))

    def test_authenticate_user_not_found(self):
        """測試使用者不存在的情況"""
        ok, _ = user_service.authenticate("nonexistent", "password")
        self.assertFalse(ok)

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

        ok, _ = user_service.authenticate(username, "wrongpass")
        self.assertFalse(ok)

    def test_create_user_success(self):
        """測試成功建立使用者"""
        username = "newuser"
        password = "newpass123"

        result = user_service.create_user(username, password, admin=False)
        self.assertTrue(result)

        user = self.fake_repo.find_by_username(username)
        self.assertIsNotNone(user)
        assert user is not None
        self.assertEqual(user["User"], username)
        self.assertTrue(check_password_hash(user["Password"], password))
        self.assertFalse(user.get("admin", False))

    def test_create_user_duplicate(self):
        """測試建立重複使用者"""
        username = "duplicate"
        password = "pass123"

        password = "pass1234"

        self.assertTrue(user_service.create_user(username, password))

        self.assertFalse(user_service.create_user(username, password))

    def test_create_user_with_admin_flag(self):
        """測試建立管理員使用者"""
        username = "adminuser"
        password = "adminpass1"

        ok = user_service.create_user(username, password, admin=True)
        self.assertTrue(ok)
        user = self.fake_repo.find_by_username(username)
        self.assertIsNotNone(user)
        assert user is not None
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
