"""通知模組測試"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime

import tests.fixtures_env  # noqa: F401

from app import create_app


class NotificationsTestCase(unittest.TestCase):
    """通知路由測試"""

    def setUp(self):
        """測試前設置"""
        os.environ["DB_TYPE"] = "postgres"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        os.environ["REDIS_URL"] = "redis://localhost:6379/0"
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
                'notify_time': '09:00',
                'notify_channels': ['email'],
                'reminder_ladder': '30,14,7',
                'replacement_enabled': True,
                'replacement_intervals': [],
            },
            'expiry_info': {'expired_count': 1, 'near_count': 2, 'total_alerts': 3},
            'replacement_info': {
                'due': [{'ItemID': 'A1', 'ItemName': '行動電源', 'replacement_rule_name': '充電保養', 'replacement_due_date': '2026-03-10', 'days_overdue': 4}],
                'upcoming': [{'ItemID': 'B1', 'ItemName': '飲水機濾芯', 'replacement_rule_name': '濾芯更換', 'replacement_due_date': '2026-03-20', 'days_left': 6}],
                'total_alerts': 2,
            },
            'can_send': True,
        }
        mock_find_user.return_value = {'User': 'testuser', 'admin': False}

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.get('/notifications/')
        self.assertEqual(response.status_code, 200)
        content = response.data.decode('utf-8')
        self.assertIn('testuser', content)
        self.assertIn('需保養', content)
        self.assertIn('即將保養', content)
        self.assertIn('保養 / 更換提醒', content)
        self.assertIn('通知摘要與保養提醒', content)

    @patch('app.services.notification_service.get_notification_summary')
    @patch('app.repositories.user_repo.find_by_username')
    def test_notifications_index_hides_telegram_bind_button_when_bot_unconfigured(self, mock_find_user, mock_get_summary):
        mock_get_summary.return_value = {
            'settings': {
                'email': 'test@example.com',
                'notify_enabled': True,
                'notify_days': 30,
                'notify_time': '09:00',
                'notify_channels': ['email'],
                'replacement_enabled': True,
                'replacement_intervals': [],
                'reminder_ladder': '30,14,7',
            },
            'expiry_info': {'expired_count': 0, 'near_count': 2, 'total_alerts': 2},
            'replacement_info': {'due': [], 'upcoming': [], 'total_alerts': 0},
            'can_send': True,
        }
        mock_find_user.return_value = {'User': 'testuser', 'admin': False}
        self.app.config['TELEGRAM_BOT_USERNAME'] = ''

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.get('/notifications/')
        self.assertEqual(response.status_code, 200)
        content = response.data.decode('utf-8')
        self.assertNotIn('前往 Telegram 綁定', content)
        self.assertIn('暫時無法綁定', content)

    @patch('app.services.notification_service.get_notification_summary')
    @patch('app.repositories.user_repo.find_by_username')
    def test_notifications_index_shows_telegram_bind_button_when_bot_configured(self, mock_find_user, mock_get_summary):
        mock_get_summary.return_value = {
            'settings': {
                'email': 'test@example.com',
                'notify_enabled': True,
                'notify_days': 30,
                'notify_time': '09:00',
                'notify_channels': ['email'],
                'replacement_enabled': True,
                'replacement_intervals': [],
                'reminder_ladder': '30,14,7',
            },
            'expiry_info': {'expired_count': 0, 'near_count': 2, 'total_alerts': 2},
            'replacement_info': {'due': [], 'upcoming': [], 'total_alerts': 0},
            'can_send': True,
        }
        mock_find_user.return_value = {'User': 'testuser', 'admin': False}
        self.app.config['TELEGRAM_BOT_USERNAME'] = 'item_manage_bot'

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.get('/notifications/')
        self.assertEqual(response.status_code, 200)
        content = response.data.decode('utf-8')
        self.assertIn('前往 Telegram 綁定', content)

    @patch('app.services.notification_service.get_notification_summary')
    @patch('app.repositories.user_repo.find_by_username')
    def test_notifications_index_uses_new_send_feedback_wording(self, mock_find_user, mock_get_summary):
        mock_get_summary.return_value = {
            'settings': {
                'email': 'test@example.com',
                'notify_enabled': True,
                'notify_days': 30,
                'notify_time': '09:00',
                'notify_channels': ['email'],
                'replacement_enabled': True,
                'replacement_intervals': [],
                'reminder_ladder': '30,14,7',
            },
            'expiry_info': {'expired_count': 1, 'near_count': 2, 'total_alerts': 3},
            'replacement_info': {
                'due': [{'ItemID': 'A1', 'ItemName': '行動電源', 'replacement_rule_name': '充電保養', 'replacement_due_date': '2026-03-10', 'days_overdue': 4}],
                'upcoming': [{'ItemID': 'B1', 'ItemName': '飲水機濾芯', 'replacement_rule_name': '濾芯更換', 'replacement_due_date': '2026-03-20', 'days_left': 6}],
                'total_alerts': 2,
            },
            'can_send': True,
        }
        mock_find_user.return_value = {'User': 'testuser', 'admin': False}

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.get('/notifications/')
        content = response.data.decode('utf-8')
        self.assertEqual(response.status_code, 200)
        self.assertIn('需保養', content)
        self.assertIn('即將保養', content)
        self.assertNotIn('需更換', content)

    @patch('app.services.notification_service.get_notification_summary')
    @patch('app.repositories.user_repo.find_by_username')
    @patch('app.models.TelegramUserLink')
    @patch('app.models.LineUserLink')
    @patch('app.get_db_type', return_value='postgres')
    def test_notifications_index_enables_test_send_for_linked_chat_channels(
        self,
        mock_db_type,
        mock_line_link,
        mock_tg_link,
        mock_find_user,
        mock_get_summary,
    ):
        mock_get_summary.return_value = {
            'settings': {
                'email': '',
                'notify_enabled': True,
                'notify_days': 30,
                'notify_time': '09:00',
                'notify_channels': ['telegram'],
                'replacement_enabled': True,
                'replacement_intervals': [],
                'reminder_ladder': '30,14,7',
            },
            'expiry_info': {'expired_count': 1, 'near_count': 0, 'total_alerts': 1},
            'replacement_info': {'due': [], 'upcoming': [], 'total_alerts': 0},
            'can_send': True,
        }
        mock_find_user.return_value = {'User': 'testuser', 'admin': False}
        mock_line_link.query.filter_by.return_value.first.return_value = None
        mock_tg_link.query.filter_by.return_value.first.return_value = object()
        self.app.config['TELEGRAM_BOT_USERNAME'] = 'item_manage_bot'

        with self.client.session_transaction() as sess:
            sess['UserID'] = 'testuser'

        response = self.client.get('/notifications/')
        self.assertEqual(response.status_code, 200)
        content = response.data.decode('utf-8')
        self.assertIn('id="sendTestBtn"', content)
        self.assertNotIn('id="sendTestBtn" class="btn btn-outline-success"\n                    disabled', content)

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

    def test_plain_notification_text_uses_new_maintenance_terms(self):
        from app.services import notification_service

        text = notification_service._build_plain_notification_text(
            expiry_info={
                'expired': [{'ItemID': 'E1'}],
                'near_expiry': [{'ItemID': 'E2'}],
            },
            replacement_info={
                'due': [{'ItemID': 'M1', 'replacement_rule_name': '充電保養'}],
                'upcoming': [{'ItemID': 'M2', 'replacement_rule_name': '濾芯更換'}],
            },
        )

        self.assertIn('已過期 1 項', text)
        self.assertIn('即將到期 1 項', text)
        self.assertIn('需保養 / 更換 1 項', text)
        self.assertIn('即將保養 / 更換 1 項', text)
        self.assertNotIn('需要更換', text)
        self.assertNotIn('即將更換', text)

    def test_email_text_content_uses_new_maintenance_contract(self):
        from app.services import email_service

        content = email_service.generate_text_content(
            expired_items=[],
            near_expiry_items=[],
            replacement_due=[{
                'ItemName': '行動電源',
                'replacement_rule_name': '充電保養',
                'replacement_due_date': '2026-03-10',
                'days_overdue': 4,
            }],
            replacement_upcoming=[{
                'ItemName': '飲水機濾芯',
                'replacement_rule_name': '濾芯更換',
                'replacement_due_date': '2026-03-20',
                'days_left': 6,
            }],
        )

        self.assertIn('需保養 / 更換 (1 項)', content)
        self.assertIn('即將保養 / 更換 (1 項)', content)
        self.assertIn('下次保養日: 2026-03-10', content)
        self.assertIn('已逾期 4 天', content)
        self.assertIn('剩餘 6 天', content)
        self.assertIn('規則: 充電保養', content)
        self.assertNotIn('days_since', content)
        self.assertNotIn('需要更換', content)

    def test_email_html_content_uses_new_maintenance_contract(self):
        from app.services import email_service

        content = email_service.generate_html_content(
            expired_items=[],
            near_expiry_items=[],
            replacement_due=[{
                'ItemName': '行動電源',
                'replacement_rule_name': '充電保養',
                'replacement_due_date': '2026-03-10',
                'days_overdue': 4,
            }],
            replacement_upcoming=[{
                'ItemName': '飲水機濾芯',
                'replacement_rule_name': '濾芯更換',
                'replacement_due_date': '2026-03-20',
                'days_left': 6,
            }],
        )

        self.assertIn('需保養 / 更換 (1 項)', content)
        self.assertIn('即將保養 / 更換 (1 項)', content)
        self.assertIn('下次保養日', content)
        self.assertIn('已逾期 4 天', content)
        self.assertIn('剩餘 6 天', content)
        self.assertIn('充電保養', content)
        self.assertNotIn('days_since', content)
        self.assertNotIn('需要更換', content)

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

    @patch('app.services.notification_service.get_db_type', return_value='mongo')
    @patch('app.services.notification_service.TelegramUserLink')
    @patch('app.services.notification_service.LineUserLink')
    def test_send_chat_notifications_returns_false_without_sql_in_mongo_mode(self, mock_line_link, mock_tg_link, _mock_db_type):
        from app.services import notification_service

        status = notification_service._send_chat_notifications(
            username='testuser',
            channels={'line', 'telegram'},
            text='hello',
        )

        self.assertEqual(status, {'line': False, 'telegram': False})
        mock_line_link.query.filter_by.assert_not_called()
        mock_tg_link.query.filter_by.assert_not_called()


if __name__ == '__main__':
    unittest.main()
