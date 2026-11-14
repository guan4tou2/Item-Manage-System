"""Gemini 模型代號取自設定（GEMINI_MODEL），不寫死在程式裡。

`gemini-2.0-flash` 已於 2026-06-01 被 Google 關閉；寫死的模型代號在 mock／stub 的測試下
不會被發現，所以這裡直接斷言送給 SDK 的 `model` 參數。
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.config import get_settings
from app.services import ai_service
from app.services.ai_search_filters import Catalog


@pytest.fixture(autouse=True)
def _reset_settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _fake_client(monkeypatch) -> MagicMock:
    client = MagicMock()
    client.models.generate_content.return_value = MagicMock(text='{"filters": {}}')
    monkeypatch.setattr("google.genai.Client", lambda api_key: client)
    return client


async def test_default_model_is_not_the_retired_one(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setenv("AI_MODE", "live")
    get_settings.cache_clear()
    client = _fake_client(monkeypatch)

    await ai_service.call_gemini_search_filters("廚房裡快過期的東西", Catalog())

    model = client.models.generate_content.call_args.kwargs["model"]
    assert model == get_settings().gemini_model == "gemini-3.6-flash"
    assert model != "gemini-2.0-flash"


async def test_model_can_be_overridden_by_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-9-test")
    monkeypatch.setenv("AI_MODE", "live")
    get_settings.cache_clear()
    client = _fake_client(monkeypatch)

    await ai_service.call_gemini_search_filters("電池", Catalog())

    assert client.models.generate_content.call_args.kwargs["model"] == "gemini-9-test"


def test_no_hardcoded_model_id_in_service():
    import inspect

    source = inspect.getsource(ai_service)
    assert 'model="gemini-' not in source
    assert source.count("model=settings.gemini_model") == 4
