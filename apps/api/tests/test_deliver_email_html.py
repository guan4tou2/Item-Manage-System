"""`deliver_email` 的 HTML alternative 契約（Phase 31 T1.6）。

以假 FastMail 攔截 `MessageSchema`，驗證：
- 預設（無 html）：維持純文字
- 有 html：subtype=plain ＋ alternative_body=html ＋ multipart=alternative
"""
from __future__ import annotations

from app.services import external_notifications as ext


class _SettingsStub:
    smtp_host = "smtp.test"
    smtp_from = "no-reply@test.io"
    smtp_user = ""
    smtp_password = ""
    smtp_port = 587


def _capture(monkeypatch) -> dict:
    captured: dict = {}

    class FakeFastMail:
        def __init__(self, conf):  # noqa: ARG002
            pass

        async def send_message(self, message):
            captured["message"] = message

    class FakeConnectionConfig:
        def __init__(self, **kwargs):
            captured["config"] = kwargs

    monkeypatch.setattr(ext, "get_settings", lambda: _SettingsStub())
    monkeypatch.setattr("fastapi_mail.FastMail", FakeFastMail)
    monkeypatch.setattr("fastapi_mail.ConnectionConfig", FakeConnectionConfig)
    return captured


async def test_deliver_email_plain_by_default(monkeypatch):
    captured = _capture(monkeypatch)

    ok = await ext.deliver_email("u@t.io", "主旨", "純文字內容")

    assert ok is True
    message = captured["message"]
    assert message.body == "純文字內容"
    assert message.alternative_body is None
    assert str(message.subtype.value) == "plain"


async def test_deliver_email_with_html_alternative(monkeypatch):
    captured = _capture(monkeypatch)

    ok = await ext.deliver_email(
        "u@t.io", "主旨", "純文字內容", html="<h1>HTML</h1>"
    )

    assert ok is True
    message = captured["message"]
    assert message.body == "純文字內容"
    assert message.alternative_body == "<h1>HTML</h1>"
    assert str(message.subtype.value) == "plain"
    assert str(message.multipart_subtype.value) == "alternative"
