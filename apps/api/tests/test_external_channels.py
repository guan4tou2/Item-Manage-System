from __future__ import annotations
import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={"email": "ch@t.io", "username": "ch_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "ch_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_status_default_unconfigured(client, auth):
    r = await client.get("/api/channels/status", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["email_configured"] is False
    assert body["user_line_linked"] is False
    assert body["user_web_push_count"] == 0


async def test_line_link_roundtrip(client, auth):
    r = await client.put("/api/channels/line", headers=auth, json={"line_user_id": "U1234567"})
    assert r.status_code == 204
    status = (await client.get("/api/channels/status", headers=auth)).json()
    assert status["user_line_linked"] is True
    r = await client.delete("/api/channels/line", headers=auth)
    assert r.status_code == 204
    status = (await client.get("/api/channels/status", headers=auth)).json()
    assert status["user_line_linked"] is False


async def test_telegram_link_roundtrip(client, auth):
    r = await client.put("/api/channels/telegram", headers=auth, json={"chat_id": "12345"})
    assert r.status_code == 204


async def test_web_push_sub_roundtrip(client, auth):
    sub = (await client.post(
        "/api/channels/web-push/subscriptions", headers=auth,
        json={"endpoint": "https://fcm.googleapis.com/x", "p256dh": "AAA", "auth": "BBB"},
    )).json()
    listed = await client.get("/api/channels/web-push/subscriptions", headers=auth)
    assert len(listed.json()) == 1
    r = await client.delete(f"/api/channels/web-push/subscriptions/{sub['id']}", headers=auth)
    assert r.status_code == 204


async def test_test_send_email_without_config_fails(client, auth):
    r = await client.post("/api/channels/test/email", headers=auth)
    # email not configured → deliver_email returns False → {"delivered": False}
    assert r.status_code == 200
    assert r.json() == {"delivered": False}


# ---- Phase 44：Web Push endpoint 的 SSRF 防護 ----------------------------


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://fcm.googleapis.com/x",  # 非 https
        "https://127.0.0.1/x",
        "https://localhost/x",
        "https://169.254.169.254/latest/meta-data",
        "https://[::1]/x",
        "https://10.0.0.5/x",
        "https://user:pw@fcm.googleapis.com/x",
    ],
)
async def test_web_push_sub_rejects_unsafe_endpoint(client, auth, endpoint):
    r = await client.post(
        "/api/channels/web-push/subscriptions", headers=auth,
        json={"endpoint": endpoint, "p256dh": "AAA", "auth": "BBB"},
    )
    assert r.status_code == 422
    listed = await client.get("/api/channels/web-push/subscriptions", headers=auth)
    assert listed.json() == []


@pytest.fixture
def vapid_configured(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("VAPID_PRIVATE_KEY", "test-private")
    monkeypatch.setenv("VAPID_PUBLIC_KEY", "test-public")
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


def _fake_getaddrinfo(*ips):
    import socket

    def _g(host, port, *args, **kwargs):
        return [
            (
                socket.AF_INET6 if ":" in ip else socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                (ip, port),
            )
            for ip in ips
        ]

    return _g


def _sub(endpoint: str):
    from app.models.external_channels import WebPushSubscription

    return WebPushSubscription(endpoint=endpoint, p256dh="p", auth="a")


@pytest.mark.parametrize("ips", [("10.0.0.5",), ("93.184.216.34", "127.0.0.1"), ("::1",)])
def test_web_push_blocked_when_endpoint_resolves_private(monkeypatch, vapid_configured, ips):
    import pywebpush

    from app.services import external_notifications as ext
    from app.services import url_guard

    calls = []
    monkeypatch.setattr(pywebpush, "webpush", lambda **kw: calls.append(kw))
    monkeypatch.setattr(url_guard.socket, "getaddrinfo", _fake_getaddrinfo(*ips))

    assert ext.deliver_web_push(_sub("https://push.example.com/x"), "t", "b", None) is False
    assert calls == []


def test_web_push_blocks_legacy_private_endpoint_without_dns(monkeypatch, vapid_configured):
    """既有資料（未經寫入時驗證）在送出時仍被擋；IP 字面值不走 DNS。"""
    import pywebpush

    from app.services import external_notifications as ext
    from app.services import url_guard

    def _no_dns(*a, **k):
        raise AssertionError("literal IP must not hit DNS")

    calls = []
    monkeypatch.setattr(pywebpush, "webpush", lambda **kw: calls.append(kw))
    monkeypatch.setattr(url_guard.socket, "getaddrinfo", _no_dns)

    assert ext.deliver_web_push(_sub("https://169.254.169.254/x"), "t", "b", None) is False
    assert ext.deliver_web_push(_sub("http://[::ffff:10.0.0.1]:6379/"), "t", "b", None) is False
    assert calls == []


def test_web_push_public_endpoint_sends_without_following_redirects(monkeypatch, vapid_configured):
    import pywebpush

    from app.services import external_notifications as ext
    from app.services import url_guard

    calls = []
    monkeypatch.setattr(pywebpush, "webpush", lambda **kw: calls.append(kw))
    monkeypatch.setattr(url_guard.socket, "getaddrinfo", _fake_getaddrinfo("93.184.216.34"))

    assert ext.deliver_web_push(_sub("https://push.example.com/x"), "t", "b", "/n") is True
    assert len(calls) == 1
    assert calls[0]["subscription_info"]["endpoint"] == "https://push.example.com/x"
    assert calls[0]["requests_session"].max_redirects == 0


def test_web_push_dns_failure_does_not_send(monkeypatch, vapid_configured):
    import pywebpush

    from app.services import external_notifications as ext
    from app.services import url_guard

    def _fail(*a, **k):
        raise OSError("nodename nor servname provided")

    calls = []
    monkeypatch.setattr(pywebpush, "webpush", lambda **kw: calls.append(kw))
    monkeypatch.setattr(url_guard.socket, "getaddrinfo", _fail)

    assert ext.deliver_web_push(_sub("https://push.example.com/x"), "t", "b", None) is False
    assert calls == []
