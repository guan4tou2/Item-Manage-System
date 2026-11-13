"""部署探針、請求脈絡與文件開關的行為驗證。"""

import json
import logging
import os
import re
import subprocess
import sys
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.db.session import get_db
from app.logging_config import JsonFormatter, configure_logging, request_id
from app.main import create_app


@pytest.fixture
def settings_env(monkeypatch):
    monkeypatch.delenv("API_DOCS_ENABLED", raising=False)
    monkeypatch.delenv("LOG_FORMAT", raising=False)
    get_settings.cache_clear()
    yield monkeypatch
    monkeypatch.undo()
    get_settings.cache_clear()
    settings = get_settings()
    configure_logging(settings.log_format, settings.log_level)


async def test_readiness_success(client):
    response = await client.get("/api/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


async def test_readiness_failure():
    app = create_app()
    db = AsyncMock()
    db.execute.side_effect = RuntimeError("private-database-password")

    async def broken_db():
        yield db

    app.dependency_overrides[get_db] = broken_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert "private-database-password" not in response.text


@pytest.mark.parametrize("incoming", [None, "trace_123.A-b", "", "bad value", "a" * 65, "bad\nvalue"])
async def test_request_id(client, incoming):
    headers = {} if incoming is None else {"X-Request-ID": incoming}
    response = await client.get("/api/health", headers=headers)
    value = response.headers["x-request-id"]
    assert re.fullmatch(r"[A-Za-z0-9._-]{1,64}", value)
    if incoming == "trace_123.A-b":
        assert value == incoming
    else:
        assert value != incoming
    assert request_id.get() is None


async def test_access_log_privacy(client, caplog):
    with caplog.at_level(logging.INFO, logger="ims.access"):
        await client.get("/missing?token=secret-query", headers={"X-Request-ID": "privacy-test"})
        await client.get("/api/health")
        await client.get("/api/health/ready")
    records = [r for r in caplog.records if r.name == "ims.access"]
    assert len(records) == 1
    record = records[0]
    assert (record.method, record.path, record.status) == ("GET", "/missing", 404)
    assert record.duration_ms >= 0
    assert record.request_id == "privacy-test"
    assert "secret-query" not in JsonFormatter().format(record)


def test_json_format_and_idempotent_configuration():
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    configure_logging("json", "INFO")
    configure_logging("json", "INFO")
    assert root.handlers == original_handlers
    token = request_id.set("json-test")
    try:
        try:
            raise ValueError("測試例外")
        except ValueError:
            record = logging.LogRecord("ims.test", logging.ERROR, __file__, 1, "訊息 %s", ("內容",), sys.exc_info())
        body = json.loads(JsonFormatter().format(record))
        assert set(body) == {"ts", "level", "logger", "msg", "request_id", "exc"}
        assert body["level"] == "ERROR"
        assert body["logger"] == "ims.test"
        assert body["msg"] == "訊息 內容"
        assert body["request_id"] == "json-test"
        assert "ValueError: 測試例外" in body["exc"]
    finally:
        request_id.reset(token)
        settings = get_settings()
        configure_logging(settings.log_format, settings.log_level)


@pytest.mark.parametrize("environment,override,enabled", [
    ("dev", None, True), ("production", None, False),
    ("production", "true", True), ("dev", "false", False),
])
async def test_docs_switch(settings_env, environment, override, enabled):
    settings_env.setenv("ENVIRONMENT", environment)
    if override is not None:
        settings_env.setenv("API_DOCS_ENABLED", override)
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.log_format == ("text" if environment == "dev" else "json")
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for path in ("/api/docs", "/api/redoc", "/api/openapi.json"):
            assert (await client.get(path)).status_code == (200 if enabled else 404)


def test_export_openapi_in_production():
    env = {**os.environ, "ENVIRONMENT": "production", "JWT_SECRET": "0123456789abcdef0123456789abcdef", "API_DOCS_ENABLED": "false"}
    result = subprocess.run([sys.executable, "scripts/export_openapi.py"], env=env, capture_output=True, text=True, check=True)
    schema = json.loads(result.stdout)
    assert "/api/health/ready" in schema["paths"]
    assert schema["openapi"]
