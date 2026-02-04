"""路由層測試"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

from app import create_app


class RoutesTestCase(unittest.TestCase):
    def setUp(self):
        """設定測試環境"""
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False  # 測試時禁用 CSRF
        self.app.config["MONGO_URI"] = "mongodb://localhost:27017/test_db"
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        """清理測試環境"""
        self.app_context.pop()

    def test_signin_get(self):
        """測試登入頁面 GET 請求"""
        response = self.client.get("/signin")
        self.assertEqual(response.status_code, 200)
        # 檢查回應內容（使用 decode 處理中文）
        self.assertIn("登入", response.data.decode('utf-8'))

    def test_signin_post_success(self):
        """測試成功登入"""
        with patch("app.services.user_service.authenticate", return_value=(True, "")):
            response = self.client.post(
                "/signin",
                data={"UserID": "admin", "Password": "admin"},
                follow_redirects=False,
            )
            # 應該重定向到首頁
            self.assertEqual(response.status_code, 302)
            self.assertIn("/home", response.location)

    def test_signin_post_failure(self):
        """測試登入失敗"""
        with patch("app.services.user_service.authenticate", return_value=(False, "帳號或密碼錯誤")):
            response = self.client.post(
                "/signin",
                data={"UserID": "admin", "Password": "wrong"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("帳號或密碼錯誤", response.data.decode('utf-8'))

    def test_signin_post_empty_fields(self):
        """測試登入時欄位為空"""
        response = self.client.post(
            "/signin",
            data={"UserID": "", "Password": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("請輸入帳號與密碼", response.data.decode('utf-8'))

    def test_signout(self):
        """測試登出"""
        # 先登入
        with patch("app.services.user_service.authenticate", return_value=True):
            self.client.post(
                "/signin",
                data={"UserID": "admin", "Password": "admin"},
            )
        
        # 登出
        response = self.client.get("/signout", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/signin", response.location)

    def test_home_requires_login(self):
        """測試首頁需要登入"""
        response = self.client.get("/home", follow_redirects=False)
        # 應該重定向到登入頁面
        self.assertEqual(response.status_code, 302)

    def test_home_with_login(self):
        """測試登入後訪問首頁"""
        with patch("app.services.user_service.authenticate", return_value=(True, "")):
            self.client.post(
                "/signin",
                data={"UserID": "admin", "Password": "admin"},
            )
        
        with patch("app.services.item_service.list_items") as mock_list, \
             patch("app.services.type_service.list_types", return_value=[]), \
             patch("app.services.location_service.list_choices", return_value=([], [], [])), \
             patch("app.utils.auth.get_current_user", return_value={"User": "admin"}):
            
            mock_list.return_value = {
                "items": [],
                "total": 0,
                "page": 1,
                "page_size": 12,
                "total_pages": 1,
                "has_prev": False,
                "has_next": False,
            }
            
            response = self.client.get("/home")
            self.assertEqual(response.status_code, 200)

    def test_additem_requires_admin(self):
        """測試新增物品需要管理員權限"""
        with patch("app.services.user_service.authenticate", return_value=True):
            # 登入為一般使用者
            self.client.post(
                "/signin",
                data={"UserID": "user", "Password": "pass"},
            )
        
        with patch("app.utils.auth.get_current_user", return_value={"User": "user", "admin": False}):
            response = self.client.get("/additem", follow_redirects=False)
            # 應該被拒絕或重定向
            self.assertIn(response.status_code, [302, 403])

    def test_search_requires_login(self):
        """測試搜尋頁面需要登入"""
        response = self.client.get("/search", follow_redirects=False)
        self.assertEqual(response.status_code, 302)

    def test_scan_requires_login(self):
        """測試掃描頁面需要登入"""
        response = self.client.get("/scan", follow_redirects=False)
        self.assertEqual(response.status_code, 302)

    def test_qrcode_requires_login(self):
        """測試 QR Code 生成需要登入"""
        response = self.client.get("/items/A1/qrcode", follow_redirects=False)
        self.assertEqual(response.status_code, 302)

    def test_barcode_requires_login(self):
        """測試條碼生成需要登入"""
        response = self.client.get("/items/A1/barcode", follow_redirects=False)
        self.assertEqual(response.status_code, 302)

    def test_deleteitem_requires_admin(self):
        """測試刪除物品需要管理員權限"""
        with patch("app.services.user_service.authenticate", return_value=True):
            self.client.post(
                "/signin",
                data={"UserID": "admin", "Password": "admin"},
            )
        
        with patch("app.services.item_service.delete_item", return_value=(True, "已刪除")), \
             patch("app.utils.auth.get_current_user", return_value={"User": "admin", "admin": True}):
            
            response = self.client.post("/deleteitem/A1", follow_redirects=False)
            self.assertEqual(response.status_code, 302)


if __name__ == "__main__":
    unittest.main()

