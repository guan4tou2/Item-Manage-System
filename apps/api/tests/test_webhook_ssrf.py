"""Phase 44 D10–D13：webhook 出站 SSRF 防護。"""
from __future__ import annotations

import ipaddress
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.config import get_settings
from app.services import url_guard
from app.services.url_guard import (
    DESTINATION_NOT_ALLOWED_EXCERPT,
    UnsafeUrlError,
    is_public_address,
    resolve_safe_addresses,
    validate_webhook_url,
)


@pytest.fixture(autouse=True)
def _reset_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


# ---- 寫入時檢查（純函式） ------------------------------------------------

GOOD_URLS = [
    "http://example.com/hook",
    "https://hooks.example.com:8443/a?b=1",
    "HTTPS://Example.COM/x",
    "http://93.184.216.34/hook",
    "http://[2606:2800:220:1:248:1893:25c8:1946]/hook",
    "http://localhostfoo.com/",  # 只是名稱含 localhost，不是 localhost
]


@pytest.mark.parametrize("url", GOOD_URLS)
def test_validate_accepts_public(url):
    assert validate_webhook_url(url) == url


BAD_URLS = [
    # 私有／保留 IP 字面值
    "http://127.0.0.1/",
    "http://127.0.0.1:8000/hook",
    "http://10.0.0.5/",
    "http://172.16.0.1/",
    "http://192.168.1.1/",
    "http://169.254.169.254/latest/meta-data/",
    "http://100.64.0.1/",
    "http://0.0.0.0/",
    "http://255.255.255.255/",
    "http://224.0.0.1/",
    "http://[::1]/",
    "http://[::]/",
    "http://[fe80::1]/",
    "http://[fc00::1]/",
    "http://[fd12:3456::1]/",
    "http://[::ffff:127.0.0.1]/",
    "http://[::ffff:10.0.0.1]/",
    "http://[64:ff9b::7f00:1]/",
    "http://[::7f00:1]/",  # IPv4-compatible（已棄用），is_global 會誤判為全域
    "http://[2002:7f00:1::1]/",
    # 非標準 IPv4 寫法
    "http://2130706433/",
    "http://0x7f.1/",
    "http://0x7f000001/",
    "http://0177.0.0.1/",
    "http://127.1/",
    "http://017700000001/",
    # 保留名稱
    "http://localhost/",
    "http://localhost:3000/",
    "http://LOCALHOST/",
    "http://LocalHost/",
    "http://localhost./",
    "http://foo.localhost/",
    "http://foo.localhost./",
    "http://printer.local/",
    "http://svc.internal/",
    "http://a.b.INTERNAL/",
    # userinfo
    "http://user@example.com/",
    "http://user:pw@example.com/",
    "http://example.com@evil.com/",
    "http://@example.com/",
    # scheme／結構
    "ftp://example.com/",
    "file:///etc/passwd",
    "gopher://example.com/",
    "javascript:alert(1)",
    "example.com/hook",
    "//example.com/hook",
    "http://",
    "http:///path",
    "http://example.com:99999/",
    "http://example.com:abc/",
    " http://example.com/",
    "",
]


@pytest.mark.parametrize("url", BAD_URLS)
def test_validate_rejects(url):
    with pytest.raises(UnsafeUrlError) as ei:
        validate_webhook_url(url)
    assert str(ei.value) == url_guard.URL_NOT_ALLOWED_MESSAGE


@pytest.mark.parametrize(
    "ip,expected",
    [
        ("8.8.8.8", True),
        ("93.184.216.34", True),
        ("2606:4700:4700::1111", True),
        ("127.0.0.1", False),
        ("10.1.2.3", False),
        ("172.31.255.255", False),
        ("192.168.0.1", False),
        ("169.254.1.1", False),
        ("100.64.0.1", False),
        ("100.127.255.255", False),
        ("0.0.0.0", False),
        ("192.0.0.1", False),
        ("198.18.0.1", False),
        ("240.0.0.1", False),
        ("224.0.0.1", False),
        ("::1", False),
        ("::", False),
        ("fe80::1", False),
        ("fc00::1", False),
        ("fd00::1", False),
        ("ff02::1", False),
        ("::ffff:127.0.0.1", False),
        ("::ffff:169.254.169.254", False),
        ("::ffff:8.8.8.8", True),
        ("64:ff9b::a00:1", False),
        ("::7f00:1", False),
        ("::a00:1", False),
        ("2002:a00:1::", False),
    ],
)
def test_is_public_address(ip, expected):
    assert is_public_address(ipaddress.ip_address(ip)) is expected


def test_validate_opt_in_allows_private_but_not_scheme(monkeypatch):
    monkeypatch.setenv("WEBHOOK_ALLOW_PRIVATE_HOSTS", "true")
    get_settings.cache_clear()
    for url in ("http://192.168.1.10:8123/api", "http://localhost/x", "http://ha.local/x", "http://[::1]/"):
        assert validate_webhook_url(url) == url
    for url in ("ftp://192.168.1.10/", "http://user@192.168.1.10/", "http://", "file:///x"):
        with pytest.raises(UnsafeUrlError):
            validate_webhook_url(url)


# ---- 送出時檢查（解析注入） ---------------------------------------------


def _resolver(*ips):
    async def _r(host, port):
        return [ipaddress.ip_address(i) for i in ips]

    return _r


async def test_resolve_all_public_ok(monkeypatch):
    monkeypatch.setattr(url_guard, "resolve_host", _resolver("93.184.216.34", "2606:2800::1"))
    parts, host, addrs = await resolve_safe_addresses("https://Example.com/x")
    assert host == "example.com" and len(addrs) == 2


@pytest.mark.parametrize("bad", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::ffff:127.0.0.1", "100.64.0.1", "fd00::1", "0.0.0.0"])
async def test_resolve_any_private_blocks(monkeypatch, bad):
    # 多筆 A／AAAA：只要有一筆不合格就擋
    monkeypatch.setattr(url_guard, "resolve_host", _resolver("93.184.216.34", bad))
    with pytest.raises(UnsafeUrlError):
        await resolve_safe_addresses("http://rebind.example.com/")


async def test_resolve_literal_ip_skips_dns(monkeypatch):
    async def boom(host, port):
        raise AssertionError("不該解析 IP 字面值")

    monkeypatch.setattr(url_guard, "resolve_host", boom)
    with pytest.raises(UnsafeUrlError):
        await resolve_safe_addresses("http://10.0.0.1/")
    _, _, addrs = await resolve_safe_addresses("http://93.184.216.34/")
    assert [str(a) for a in addrs] == ["93.184.216.34"]


async def test_resolve_opt_in_allows_private(monkeypatch):
    monkeypatch.setenv("WEBHOOK_ALLOW_PRIVATE_HOSTS", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(url_guard, "resolve_host", _resolver("192.168.1.10"))
    _, _, addrs = await resolve_safe_addresses("http://ha.local/x")
    assert [str(a) for a in addrs] == ["192.168.1.10"]


# ---- 路由層 --------------------------------------------------------------


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={"email": "ssrf@t.io", "username": "ssrf_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "ssrf_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.parametrize(
    "url",
    ["http://127.0.0.1/hook", "http://localhost/hook", "http://169.254.169.254/", "ftp://example.com/", "http://u:p@example.com/", "http://2130706433/"],
)
async def test_create_rejects_unsafe_url(client, auth, url):
    r = await client.post("/api/webhooks", headers=auth, json={"name": "x", "url": url})
    assert r.status_code == 422
    assert url_guard.URL_NOT_ALLOWED_MESSAGE in r.text


async def test_update_rejects_unsafe_url_but_allows_omitted(client, auth):
    r = await client.post("/api/webhooks", headers=auth, json={"name": "x", "url": "http://example.com/hook"})
    wid = r.json()["id"]
    bad = await client.patch(f"/api/webhooks/{wid}", headers=auth, json={"url": "http://10.0.0.1/"})
    assert bad.status_code == 422
    assert url_guard.URL_NOT_ALLOWED_MESSAGE in bad.text
    null = await client.patch(f"/api/webhooks/{wid}", headers=auth, json={"url": None})
    assert null.status_code == 422
    ok = await client.patch(f"/api/webhooks/{wid}", headers=auth, json={"name": "renamed"})
    assert ok.status_code == 200
    ok = await client.patch(f"/api/webhooks/{wid}", headers=auth, json={"url": "https://example.org/h"})
    assert ok.status_code == 200 and ok.json()["url"] == "https://example.org/h"


# ---- 送出行為 ------------------------------------------------------------


def _mock_http(monkeypatch, status=200):
    class Resp:
        status_code = status
        text = "ok"

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=Resp())
    ctor_kwargs: dict = {}

    def factory(**kw):
        ctor_kwargs.update(kw)
        return mock_client

    monkeypatch.setattr(httpx, "AsyncClient", factory)
    return mock_client.post, ctor_kwargs


async def _create_and_fire(client, auth, url):
    r = await client.post("/api/webhooks", headers=auth, json={"name": "t", "url": url, "events": ["item.created"]})
    assert r.status_code == 201, r.text
    wid = r.json()["id"]
    await client.post("/api/items", headers=auth, json={"name": "trigger"})
    deliveries = (await client.get(f"/api/webhooks/{wid}/deliveries", headers=auth)).json()
    return wid, deliveries


async def test_dispatch_blocked_when_dns_resolves_private(client, auth, monkeypatch):
    post, _ = _mock_http(monkeypatch)
    monkeypatch.setattr(url_guard, "resolve_host", _resolver("10.0.0.7"))
    _, deliveries = await _create_and_fire(client, auth, "http://rebind.example.com/hook")
    post.assert_not_called()
    assert len(deliveries) == 1
    d = deliveries[0]
    assert d["status_code"] is None
    assert d["response_excerpt"] == DESTINATION_NOT_ALLOWED_EXCERPT
    assert "10.0.0.7" not in d["response_excerpt"]
    # 與一般網路失敗一致：照常排重試
    assert d["attempt"] == 1 and d["next_retry_at"] is not None


async def test_dispatch_blocked_when_any_record_private(client, auth, monkeypatch):
    post, _ = _mock_http(monkeypatch)
    monkeypatch.setattr(url_guard, "resolve_host", _resolver("93.184.216.34", "169.254.169.254"))
    _, deliveries = await _create_and_fire(client, auth, "https://multi.example.com/hook")
    post.assert_not_called()
    assert deliveries[0]["response_excerpt"] == DESTINATION_NOT_ALLOWED_EXCERPT


async def test_dispatch_pins_ip_and_keeps_host_header(client, auth, monkeypatch):
    post, ctor = _mock_http(monkeypatch)
    monkeypatch.setattr(url_guard, "resolve_host", _resolver("93.184.216.34"))
    _, deliveries = await _create_and_fire(client, auth, "http://hooks.example.com:8080/a/b?x=1")
    assert deliveries[0]["status_code"] == 200
    post.assert_awaited_once()
    args, kwargs = post.call_args
    assert args[0] == "http://93.184.216.34:8080/a/b?x=1"
    assert kwargs["headers"]["Host"] == "hooks.example.com:8080"
    assert kwargs["extensions"] == {}  # http 不需要 SNI
    assert ctor["follow_redirects"] is False
    assert ctor["trust_env"] is False


async def test_dispatch_https_sets_sni_and_brackets_ipv6(client, auth, monkeypatch):
    post, _ = _mock_http(monkeypatch)
    monkeypatch.setattr(url_guard, "resolve_host", _resolver("2606:2800:220:1:248:1893:25c8:1946"))
    await _create_and_fire(client, auth, "https://hooks.example.com/h")
    args, kwargs = post.call_args
    assert args[0] == "https://[2606:2800:220:1:248:1893:25c8:1946]/h"
    assert kwargs["headers"]["Host"] == "hooks.example.com"
    assert kwargs["extensions"] == {"sni_hostname": "hooks.example.com"}


async def test_dispatch_falls_back_to_next_address_on_connect_error(client, auth, monkeypatch):
    post, _ = _mock_http(monkeypatch)
    resp = MagicMock(status_code=200, text="ok")
    post.side_effect = [httpx.ConnectError("down"), resp]
    monkeypatch.setattr(url_guard, "resolve_host", _resolver("2606:2800::1", "93.184.216.34"))
    _, deliveries = await _create_and_fire(client, auth, "http://dual.example.com/h")
    assert deliveries[0]["status_code"] == 200
    assert [c.args[0] for c in post.call_args_list] == ["http://[2606:2800::1]/h", "http://93.184.216.34/h"]


async def test_dispatch_dns_failure_is_plain_network_error(client, auth, monkeypatch):
    post, _ = _mock_http(monkeypatch)

    async def nx(host, port):
        raise OSError("Name or service not known")

    monkeypatch.setattr(url_guard, "resolve_host", nx)
    _, deliveries = await _create_and_fire(client, auth, "http://nx.invalid/h")
    post.assert_not_called()
    assert deliveries[0]["status_code"] is None
    assert deliveries[0]["response_excerpt"].startswith("error:")
    assert deliveries[0]["response_excerpt"] != DESTINATION_NOT_ALLOWED_EXCERPT


async def test_legacy_private_url_blocked_on_dispatch(client, auth, db_session, monkeypatch):
    """D13：既有（寫入時未檢查的）內網 URL 在投遞時被擋並留下失敗紀錄。"""
    from sqlalchemy import update

    from app.models.webhook import Webhook

    post, _ = _mock_http(monkeypatch)
    r = await client.post("/api/webhooks", headers=auth, json={"name": "old", "url": "http://example.com/h", "events": ["item.created"]})
    wid = r.json()["id"]
    await db_session.execute(update(Webhook).values(url="http://127.0.0.1:5432/"))
    await db_session.commit()
    await client.post("/api/items", headers=auth, json={"name": "trigger"})
    post.assert_not_called()
    deliveries = (await client.get(f"/api/webhooks/{wid}/deliveries", headers=auth)).json()
    assert deliveries[0]["response_excerpt"] == DESTINATION_NOT_ALLOWED_EXCERPT


async def test_dispatch_opt_in_allows_private_target(client, auth, monkeypatch):
    monkeypatch.setenv("WEBHOOK_ALLOW_PRIVATE_HOSTS", "true")
    get_settings.cache_clear()
    post, ctor = _mock_http(monkeypatch)
    r = await client.post("/api/webhooks", headers=auth, json={"name": "lan", "url": "http://192.168.1.10:8123/api/webhook/x", "events": ["item.created"]})
    assert r.status_code == 201
    await client.post("/api/items", headers=auth, json={"name": "trigger"})
    post.assert_awaited_once()
    assert post.call_args.args[0] == "http://192.168.1.10:8123/api/webhook/x"
    assert ctor["follow_redirects"] is False
