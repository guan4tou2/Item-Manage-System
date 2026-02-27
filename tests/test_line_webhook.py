import base64
import hashlib
import hmac
import json
import os
import unittest
from unittest import mock

import tests.fixtures_env  # noqa: F401
from itsdangerous import URLSafeSerializer

from app import create_app, db


class LineWebhookTestCase(unittest.TestCase):
    def setUp(self):
        os.environ["DB_TYPE"] = "postgres"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        os.environ["REDIS_URL"] = "redis://localhost:6379/0"
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.app.config["LINE_CHANNEL_SECRET"] = "test-secret"
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def _signature(self, body: str) -> str:
        digest = hmac.new(
            self.app.config["LINE_CHANNEL_SECRET"].encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(digest).decode("utf-8")

    def test_webhook_invalid_signature(self):
        body = json.dumps({"events": []})
        response = self.client.post(
            "/line/webhook",
            data=body,
            content_type="application/json",
            headers={"X-Line-Signature": "bad-signature"},
        )
        self.assertEqual(response.status_code, 401)

    def test_postback_event_dispatches_handler(self):
        payload = {
            "events": [
                {
                    "type": "postback",
                    "replyToken": "reply-token",
                    "source": {"type": "user", "userId": "U_LINE_123"},
                    "postback": {"data": "cmd=my_trips"},
                }
            ]
        }
        body = json.dumps(payload)
        with mock.patch("app.line.routes._handle_postback", return_value=("ok", [], None)) as mocked_handler, mock.patch(
            "app.line.routes._reply_message"
        ) as mocked_reply:
            response = self.client.post(
                "/line/webhook",
                data=body,
                content_type="application/json",
                headers={"X-Line-Signature": self._signature(body)},
            )

        self.assertEqual(response.status_code, 200)
        mocked_handler.assert_called_once_with("U_LINE_123", "cmd=my_trips")
        mocked_reply.assert_called_once_with("reply-token", "ok", [], None)

    def test_text_event_dispatches_flex_reply(self):
        payload = {
            "events": [
                {
                    "type": "message",
                    "replyToken": "reply-token",
                    "source": {"type": "user", "userId": "U_LINE_123"},
                    "message": {"type": "text", "text": "我的旅行"},
                }
            ]
        }
        body = json.dumps(payload)
        flex = {"type": "flex", "altText": "demo", "contents": {"type": "bubble", "body": {"type": "box", "layout": "vertical", "contents": []}}}
        with mock.patch("app.line.routes._handle_text_message", return_value=("ok", [], flex)) as mocked_handler, mock.patch(
            "app.line.routes._reply_message"
        ) as mocked_reply:
            response = self.client.post(
                "/line/webhook",
                data=body,
                content_type="application/json",
                headers={"X-Line-Signature": self._signature(body)},
            )

        self.assertEqual(response.status_code, 200)
        mocked_handler.assert_called_once_with("U_LINE_123", "我的旅行")
        mocked_reply.assert_called_once_with("reply-token", "ok", [], flex)

    def test_account_link_event_creates_mapping(self):
        serializer = URLSafeSerializer(self.app.config["SECRET_KEY"], salt="line-account-link")
        nonce = serializer.dumps({"u": "testuser", "n": "random"})
        payload = {
            "events": [
                {
                    "type": "accountLink",
                    "replyToken": "dummy",
                    "source": {"type": "user", "userId": "U_LINE_123"},
                    "link": {"result": "ok", "nonce": nonce},
                }
            ]
        }
        body = json.dumps(payload)
        with mock.patch("app.line.routes._upsert_link") as mocked_upsert:
            response = self.client.post(
                "/line/webhook",
                data=body,
                content_type="application/json",
                headers={"X-Line-Signature": self._signature(body)},
            )
            self.assertEqual(response.status_code, 200)
            mocked_upsert.assert_called_once_with("testuser", "U_LINE_123")
