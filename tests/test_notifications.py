"""通知模組測試"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
from datetime import datetime

# Setup test environment
import tests.conftest  # noqa: F401

from app import create_app


class NotificationsTestCase(unittest.TestCase):
    """通知路由測試"""

    def setUp(self):
        """測試前設置"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        """測試後清理"""
        self.ctx.pop()

    def test_notifications_index_requires_auth(self):
        """測試通知設定頁面需要登入"""
        response = self.client.get('/notifications/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/signin', response.location)

    @patch('app.services.notification_service.get_notification_summary')
    @patch('app.repositories.user_repo.find_by_username')
    def test_notifications_index_authenticated(self, mock_find_user, mock_get_summary):
        """測試已登入用戶訪問通知設定頁面"""
        mock_get_summary.return_value = {
            'settings': {
                'email': 'test@example.com',
                'notify_enabled': True,
                'notify_days': 30,
            },
            'expiry_info': {'total': 5, 'expiring_soon': 2},
            'can_send': True,
        }
        mock_find_user.return_value = {'User': 'testuser', 'admin': False}

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.get('/notifications/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'testuser', response.data)

    def test_get_settings_requires_auth(self):
        """測試取得設定 API 需要登入"""
        response = self.client.get('/notifications/api/settings')
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn('error', data)

    @patch('app.repositories.user_repo.get_notification_settings')
    def test_get_settings_authenticated(self, mock_get_settings):
        """測試已登入用戶取得通知設定"""
        mock_get_settings.return_value = {
            'email': 'test@example.com',
            'notify_enabled': True,
            'notify_days': 30,
            'notify_time': '09:00',
            'notify_channels': ['email'],
        }

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.get('/notifications/api/settings')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['email'], 'test@example.com')
        self.assertTrue(data['notify_enabled'])

    def test_update_settings_requires_auth(self):
        """測試更新設定 API 需要登入"""
        response = self.client.post('/notifications/api/settings',
                                    json={'email': 'new@example.com'})
        self.assertEqual(response.status_code, 401)

    @patch('app.repositories.user_repo.update_notification_settings')
    def test_update_settings_success(self, mock_update):
        """測試成功更新通知設定"""
        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        test_data = {
            'email': 'new@example.com',
            'notify_enabled': True,
            'notify_days': 7,
            'notify_time': '10:00',
            'notify_channels': ['email'],
            'reminder_ladder': '30,14,7',
            'replacement_enabled': True,
            'replacement_intervals': []
        }

        response = self.client.post('/notifications/api/settings',
                                    json=test_data)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        mock_update.assert_called_once()

    @patch('app.repositories.user_repo.update_notification_settings')
    def test_update_settings_parse_replacement_intervals(self, mock_update):
        """測試解析替換間隔字串"""
        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        test_data = {
            'replacement_intervals': 'Filter=90,Battery=180'
        }

        response = self.client.post('/notifications/api/settings',
                                    json=test_data)
        self.assertEqual(response.status_code, 200)
        
        call_args = mock_update.call_args
        replacement_intervals = call_args.kwargs['replacement_intervals']
        self.assertEqual(len(replacement_intervals), 2)
        self.assertEqual(replacement_intervals[0]['name'], 'Filter')
        self.assertEqual(replacement_intervals[0]['days'], 90)

    def test_send_notification_requires_auth(self):
        """測試發送通知 API 需要登入"""
        response = self.client.post('/notifications/api/send')
        self.assertEqual(response.status_code, 401)

    @patch('app.services.notification_service.send_manual_notification')
    def test_send_notification_success(self, mock_send):
        """測試成功發送通知"""
        mock_send.return_value = {
            'success': True,
            'message': 'Notification sent'
        }

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.post('/notifications/api/send')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])

    @patch('app.services.notification_service.send_manual_notification')
    def test_send_notification_failure(self, mock_send):
        """測試發送通知失敗"""
        mock_send.return_value = {
            'success': False,
            'message': 'Email not configured'
        }

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.post('/notifications/api/send')
        data = response.get_json()
        self.assertFalse(data['success'])

    def test_get_summary_requires_auth(self):
        """測試取得摘要 API 需要登入"""
        response = self.client.get('/notifications/api/summary')
        self.assertEqual(response.status_code, 401)

    @patch('app.services.notification_service.get_notification_summary')
    def test_get_summary_authenticated(self, mock_get_summary):
        """測試已登入用戶取得通知摘要"""
        mock_get_summary.return_value = {
            'settings': {'email': 'test@example.com'},
            'expiry_info': {
                'total': 10,
                'expiring_soon': 3,
                'items': []
            },
            'can_send': True,
        }

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.get('/notifications/api/summary')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('settings', data)
        self.assertIn('expiry_info', data)
        self.assertEqual(data['expiry_info']['total'], 10)


if __name__ == '__main__':
    unittest.main()
