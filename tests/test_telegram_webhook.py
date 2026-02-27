import json
import os
import unittest
from unittest import mock

import tests.fixtures_env  # noqa: F401

from app import create_app


class TelegramWebhookTestCase(unittest.TestCase):
    def setUp(self):
        os.environ["DB_TYPE"] = "postgres"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        os.environ["REDIS_URL"] = "redis://localhost:6379/0"
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.app.config["TELEGRAM_WEBHOOK_SECRET"] = "tg-secret"
        self.client = self.app.test_client()

    def test_webhook_rejects_invalid_secret(self):
        response = self.client.post(
            "/telegram/webhook",
            json={"update_id": 1},
            headers={"X-Telegram-Bot-Api-Secret-Token": "bad"},
        )
        self.assertEqual(response.status_code, 401)

    def test_message_event_dispatches_handler(self):
        payload = {
            "update_id": 1,
            "message": {
                "message_id": 12,
                "from": {"id": 111},
                "chat": {"id": 222},
                "text": "我的旅行",
            },
        }
        with mock.patch("app.telegram.routes._handle_text", return_value=("ok", None)) as mocked_handle, mock.patch(
            "app.telegram.routes._send_message"
        ) as mocked_send:
            response = self.client.post(
                "/telegram/webhook",
                data=json.dumps(payload),
                content_type="application/json",
                headers={"X-Telegram-Bot-Api-Secret-Token": "tg-secret"},
            )

        self.assertEqual(response.status_code, 200)
        mocked_handle.assert_called_once_with("111", "222", "我的旅行")
        mocked_send.assert_called_once_with("222", "ok", None)

    def test_callback_event_dispatches_handler(self):
        payload = {
            "update_id": 2,
            "callback_query": {
                "id": "cbq-1",
                "from": {"id": 111},
                "message": {"chat": {"id": 222}},
                "data": "cmd:common",
            },
        }
        with mock.patch("app.telegram.routes._handle_callback", return_value=("ok", [[{"text": "X", "callback_data": "cmd:my_trips"}]])) as mocked_handle, mock.patch(
            "app.telegram.routes._send_message"
        ) as mocked_send:
            response = self.client.post(
                "/telegram/webhook",
                data=json.dumps(payload),
                content_type="application/json",
                headers={"X-Telegram-Bot-Api-Secret-Token": "tg-secret"},
            )

        self.assertEqual(response.status_code, 200)
        mocked_handle.assert_called_once_with("111", "cmd:common")
        mocked_send.assert_called_once()
