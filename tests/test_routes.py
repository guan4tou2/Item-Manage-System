"""路由層測試"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

from app import create_app
from app.utils.auth import get_current_user


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

    @patch("app.services.user_service.get_user", return_value={"User": "admin", "admin": True})
    def test_get_current_user_normalizes_name_field(self, _mock_get_user):
        with self.app.test_request_context("/home"):
            from flask import session
            session["UserID"] = "admin"
            user = get_current_user()

        self.assertEqual(user["User"], "admin")
        self.assertEqual(user["name"], "admin")
        self.assertTrue(user["admin"])

    @patch("app.services.user_service.list_users", return_value=[])
    @patch("app.services.user_service.get_user", return_value={"User": "admin", "name": "admin", "admin": True})
    def test_admin_users_page_contains_create_form(self, _mock_get_user, _mock_list_users):
        with self.client.session_transaction() as sess:
            sess["UserID"] = "admin"

        response = self.client.get("/admin/users")
        content = response.data.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIn('action="/admin/users/create"', content)
        self.assertIn('name="ConfirmPassword"', content)

    @patch("app.services.user_service.create_user", return_value=True)
    @patch("app.services.user_service.validate_new_password", return_value=(True, ""))
    @patch("app.services.user_service.get_user", return_value={"User": "admin", "name": "admin", "admin": True})
    def test_admin_can_create_user(
        self,
        _mock_get_user,
        _mock_validate_password,
        mock_create_user,
    ):
        with self.client.session_transaction() as sess:
            sess["UserID"] = "admin"

        response = self.client.post(
            "/admin/users/create",
            data={
                "UserID": "newuser",
                "Password": "Passw0rd1",
                "ConfirmPassword": "Passw0rd1",
                "admin": "on",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/users", response.location)
        mock_create_user.assert_called_once_with("newuser", "Passw0rd1", admin=True)

    @patch("app.services.user_service.get_user", return_value={"User": "admin", "name": "admin", "admin": True})
    def test_admin_create_user_rejects_password_mismatch(self, _mock_get_user):
        with self.client.session_transaction() as sess:
            sess["UserID"] = "admin"

        response = self.client.post(
            "/admin/users/create",
            data={
                "UserID": "newuser",
                "Password": "Passw0rd1",
                "ConfirmPassword": "Passw0rd2",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/users", response.location)

    @patch("app.services.user_service.list_users", return_value=[
        {"User": "admin", "admin": True},
        {"User": "user1", "admin": False},
    ])
    @patch("app.services.user_service.get_user", return_value={"User": "admin", "name": "admin", "admin": True})
    def test_admin_users_page_contains_delete_action(self, _mock_get_user, _mock_list_users):
        with self.client.session_transaction() as sess:
            sess["UserID"] = "admin"

        response = self.client.get("/admin/users")
        content = response.data.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/admin/delete-user/user1", content)
        self.assertNotIn("/admin/delete-user/admin", content)

    @patch("app.services.user_service.delete_user", return_value=(True, "已刪除 user1"))
    @patch("app.services.user_service.get_user", return_value={"User": "admin", "name": "admin", "admin": True})
    def test_admin_can_delete_user(self, _mock_get_user, mock_delete_user):
        with self.client.session_transaction() as sess:
            sess["UserID"] = "admin"

        response = self.client.post("/admin/delete-user/user1", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/users", response.location)
        mock_delete_user.assert_called_once_with("admin", "user1")

    @patch("app.utils.auth.get_current_user", return_value={"User": "admin", "name": "admin", "admin": True})
    @patch("app.services.item_service.get_stats", return_value={"total": 2, "by_type": {"工具": 1}, "low_stock": 0})
    @patch("app.services.item_service.get_all_items_for_export")
    @patch("app.services.type_service.list_types", return_value=[{"name": "工具"}, {"name": "文具"}])
    @patch("app.services.location_service.list_choices", return_value=(["1F", "2F"], [], []))
    @patch("app.services.item_service.get_notification_count", return_value={"expired": 0, "near": 0, "total": 0})
    def test_statistics_page_renders_from_aggregated_items(
        self,
        _mock_notification_count,
        _mock_location_choices,
        _mock_list_types,
        mock_get_all_items,
        _mock_stats,
        _mock_current_user,
    ):
        """測試統計頁以一次撈取的物品資料聚合，不依賴逐項 count 查詢"""
        with self.client.session_transaction() as sess:
            sess["UserID"] = "admin"

        mock_get_all_items.return_value = [
            {"ItemID": "A1", "ItemType": "工具", "ItemFloor": "1F"},
            {"ItemID": "A2", "ItemType": "文具", "ItemFloor": "1F"},
        ]

        response = self.client.get("/statistics")
        content = response.data.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIn("工具", content)
        self.assertIn("1F", content)

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

    @patch("app.services.type_service.list_types", return_value=[])
    @patch("app.services.location_service.list_choices", return_value=([], [], []))
    @patch("app.utils.auth.get_current_user", return_value={"User": "admin", "name": "admin", "admin": True})
    def test_additem_page_contains_camera_capture_entry(
        self,
        _mock_current_user,
        _mock_location_choices,
        _mock_types,
    ):
        with self.client.session_transaction() as sess:
            sess["UserID"] = "admin"

        response = self.client.get("/additem")
        content = response.data.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIn('capture="environment"', content)
        self.assertIn("直接拍照", content)
        self.assertIn("cameraModal", content)
        self.assertIn("建議保養週期", content)
        self.assertIn("MaintenanceIntervalDays", content)
        self.assertIn("LastMaintenanceDate", content)

    @patch("app.services.type_service.list_types", return_value=[])
    @patch("app.services.location_service.list_choices", return_value=([], [], []))
    @patch("app.services.item_service.get_item")
    @patch("app.utils.auth.get_current_user", return_value={"User": "admin", "name": "admin", "admin": True})
    def test_edititem_page_contains_camera_capture_entry(
        self,
        _mock_current_user,
        mock_get_item,
        _mock_location_choices,
        _mock_types,
    ):
        with self.client.session_transaction() as sess:
            sess["UserID"] = "admin"

        mock_get_item.return_value = {
            "ItemID": "DEMO-001",
            "ItemName": "測試物品",
            "ItemStorePlace": "書房/書桌",
            "ItemFloor": "",
            "ItemRoom": "",
            "ItemZone": "",
            "ItemType": "",
            "ItemOwner": "admin",
            "visibility": "private",
            "ItemGetDate": "2026-03-10",
            "WarrantyExpiry": "",
            "UsageExpiry": "",
            "ItemDesc": "",
            "ItemPic": "",
        }

        response = self.client.get("/edititem/DEMO-001")
        content = response.data.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIn('capture="environment"', content)
        self.assertIn("直接拍照", content)
        self.assertIn("cameraModal", content)
        self.assertIn("建議保養週期", content)
        self.assertIn("MaintenanceIntervalDays", content)
        self.assertIn("LastMaintenanceDate", content)

    @patch("app.services.item_service.get_item")
    @patch("app.utils.auth.get_current_user", return_value={"User": "admin", "name": "admin", "admin": True})
    def test_item_detail_shows_maintenance_information(
        self,
        _mock_current_user,
        mock_get_item,
    ):
        with self.client.session_transaction() as sess:
            sess["UserID"] = "admin"

        mock_get_item.return_value = {
            "ItemID": "DEMO-001",
            "ItemName": "行動電源",
            "ItemStorePlace": "書房/抽屜",
            "ItemFloor": "1F",
            "ItemRoom": "書房",
            "ItemZone": "抽屜",
            "ItemType": "3C配件",
            "ItemOwner": "admin",
            "visibility": "private",
            "ItemGetDate": "2026-03-10",
            "WarrantyExpiry": "",
            "UsageExpiry": "",
            "ItemDesc": "",
            "ItemPic": "",
            "MaintenanceCategory": "充電保養",
            "MaintenanceIntervalDays": "45",
            "LastMaintenanceDate": "2026-03-01",
        }

        response = self.client.get("/item/DEMO-001")
        content = response.data.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIn("保養資訊", content)
        self.assertIn("充電保養", content)
        self.assertIn("45 天", content)

    def test_search_requires_login(self):
        """測試搜尋頁面需要登入"""
        response = self.client.get("/search", follow_redirects=False)
        self.assertEqual(response.status_code, 302)

    @patch("app.services.item_service.list_items")
    @patch("app.services.type_service.list_types", return_value=[])
    @patch("app.services.location_service.list_choices", return_value=(["1F"], ["書房"], ["書桌"]))
    @patch("app.utils.auth.get_current_user", return_value={"User": "admin", "name": "admin", "admin": True})
    def test_search_filter_remove_links_preserve_other_filters(
        self,
        _mock_current_user,
        _mock_location_choices,
        _mock_types,
        mock_list_items,
    ):
        with self.client.session_transaction() as sess:
            sess["UserID"] = "admin"

        mock_list_items.return_value = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 12,
            "total_pages": 1,
            "has_prev": False,
            "has_next": False,
        }

        response = self.client.get("/search?q=筆電&place=書房&type=電子產品&floor=1F&room=書房&zone=書桌&sort=name")
        content = response.data.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIn("place=%E6%9B%B8%E6%88%BF", content)
        self.assertIn("floor=1F", content)
        self.assertIn("room=%E6%9B%B8%E6%88%BF", content)
        self.assertIn("zone=%E6%9B%B8%E6%A1%8C", content)
        self.assertIn("sort=name", content)

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

    @patch("app.utils.auth.get_current_user", return_value={"User": "admin", "admin": True})
    def test_import_page_renders_for_admin(self, _mock_current_user):
        """測試批量導入頁面可正常載入"""
        with self.client.session_transaction() as sess:
            sess["UserID"] = "admin"

        response = self.client.get("/import/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("批量導入物品", response.data.decode("utf-8"))

    @patch("app.utils.auth.get_current_user", return_value={"User": "admin", "admin": True})
    def test_import_template_includes_optional_inventory_fields(self, _mock_current_user):
        with self.client.session_transaction() as sess:
            sess["UserID"] = "admin"

        response = self.client.get("/import/template")
        content = response.data.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIn("ItemID", content)
        self.assertIn("Quantity", content)
        self.assertIn("SafetyStock", content)
        self.assertIn("ReorderLevel", content)

    @patch("app.routes.import_routes.location_service.create_location")
    @patch("app.routes.import_routes.item_repo.insert_item")
    @patch("app.routes.import_routes.item_repo.find_item_by_id", return_value=None)
    @patch("app.utils.auth.get_current_user", return_value={"User": "admin", "admin": True})
    def test_import_upload_normalizes_location_and_generates_item_id(
        self,
        _mock_current_user,
        mock_find_item,
        mock_insert_item,
        mock_create_location,
    ):
        """測試批量導入會生成 ItemID、拆解位置並同步位置選項"""
        with self.client.session_transaction() as sess:
            sess["UserID"] = "admin"

        csv_content = (
            "ItemName,ItemType,Location,WarrantyExpiry,UsageExpiry,Notes\n"
            "筆電,電子產品,1F/書房/書桌,2026-12-31,,工作用\n"
        )

        response = self.client.post(
            "/import/upload",
            data={
                "file": (BytesIO(csv_content.encode("utf-8")), "items.csv"),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["result"]["success_count"], 1)
        self.assertEqual(data["result"]["failed_count"], 0)

        inserted_item = mock_insert_item.call_args[0][0]
        self.assertTrue(inserted_item["ItemID"].startswith("ITEM-"))
        self.assertEqual(inserted_item["ItemStorePlace"], "1F/書房/書桌")
        self.assertEqual(inserted_item["ItemFloor"], "1F")
        self.assertEqual(inserted_item["ItemRoom"], "書房")
        self.assertEqual(inserted_item["ItemZone"], "書桌")
        self.assertEqual(inserted_item["ItemOwner"], "admin")
        mock_create_location.assert_called_once_with({"floor": "1F", "room": "書房", "zone": "書桌"})

    @patch("app.services.item_service.get_expiring_items")
    @patch("app.services.item_service.get_low_stock_items")
    @patch("app.services.item_service.get_replacement_items")
    @patch("app.repositories.user_repo.get_notification_settings")
    @patch("app.utils.auth.get_current_user", return_value={"User": "admin", "name": "admin", "admin": True})
    def test_notifications_summary_includes_low_stock_and_replacement_sections(
        self,
        _mock_current_user,
        mock_get_settings,
        mock_get_replacement_items,
        mock_get_low_stock_items,
        mock_get_expiring_items,
    ):
        """測試通知摘要頁面包含低庫存與更換提醒資料"""
        with self.client.session_transaction() as sess:
            sess["UserID"] = "admin"

        mock_get_settings.return_value = {"replacement_enabled": True, "replacement_intervals": []}
        mock_get_expiring_items.return_value = {
            "expired": [],
            "near_expiry": [],
            "expired_count": 0,
            "near_count": 0,
            "total_alerts": 0,
        }
        mock_get_low_stock_items.return_value = {
            "low_stock": [{"ItemID": "A1", "ItemName": "電池", "Quantity": 0, "SafetyStock": 1, "ReorderLevel": 1, "stock_status": "critical"}],
            "low_stock_count": 1,
            "need_reorder": [],
            "reorder_count": 1,
            "total_alerts": 1,
        }
        mock_get_replacement_items.return_value = {
            "due": [{"ItemID": "B1", "ItemName": "襪子", "ItemType": "衣物", "rule_name": "襪子", "days_since": 200}],
            "upcoming": [],
            "total_alerts": 1,
            "enabled": True,
        }

        response = self.client.get("/notifications/summary")
        content = response.data.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIn("庫存不足", content)
        self.assertIn("保養 / 更換提醒", content)

    @patch("app.locations.routes.location_service.list_choices", return_value=([], [], []))
    @patch("app.locations.routes.location_service.list_locations", return_value=[])
    @patch("app.utils.auth.get_current_user", return_value={"User": "admin", "admin": True})
    def test_update_location_rejects_blank_location(
        self,
        _mock_current_user,
        _mock_list_locations,
        _mock_list_choices,
    ):
        with self.client.session_transaction() as sess:
            sess["UserID"] = "admin"

        response = self.client.post(
            "/locations",
            data={"action": "update", "loc_id": "507f1f77bcf86cd799439011", "floor": "", "room": "", "zone": ""},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)

    @patch("app.utils.auth.get_current_user", return_value={"User": "admin", "admin": True})
    def test_restore_backup_rejects_empty_filename(self, _mock_current_user):
        with self.client.session_transaction() as sess:
            sess["UserID"] = "admin"

        response = self.client.post(
            "/api/backup/restore",
            data={"backup_file": (BytesIO(b""), ""), "mode": "merge"},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["message"], "請選擇備份檔案")

    @patch("app.utils.auth.get_current_user", return_value={"User": "admin", "name": "admin", "admin": True})
    @patch("app.services.item_service.get_stats", return_value={"total": 3, "with_photo": 1, "with_location": 2, "with_type": 3})
    @patch("app.services.item_service.get_all_items_for_export")
    @patch("app.services.type_service.list_types", return_value=[{"name": "工具"}, {"name": "文具"}])
    @patch("app.services.location_service.list_choices", return_value=(["2F", "1F"], [], []))
    @patch("app.services.item_service.get_notification_count", return_value={"expired": 0, "near": 0, "total": 0})
    def test_statistics_page_sorts_top_type_and_floor_by_count(
        self,
        _mock_notification_count,
        _mock_location_choices,
        _mock_list_types,
        mock_get_all_items,
        _mock_stats,
        _mock_current_user,
    ):
        with self.client.session_transaction() as sess:
            sess["UserID"] = "admin"

        mock_get_all_items.return_value = [
            {"ItemID": "A1", "ItemType": "文具", "ItemFloor": "1F"},
            {"ItemID": "A2", "ItemType": "文具", "ItemFloor": "1F"},
            {"ItemID": "A3", "ItemType": "工具", "ItemFloor": "2F"},
        ]

        response = self.client.get("/statistics")
        content = response.data.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIn("主要樓層", content)
        self.assertIn("主要類型", content)
        self.assertIn(">1F<", content)
        self.assertIn(">文具<", content)


if __name__ == "__main__":
    unittest.main()
