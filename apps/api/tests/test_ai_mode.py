"""Phase 35 T1.1：AI stub 模式的設定與啟用判定。

- `AI_MODE` ∈ {live, stub}；非法值 → 啟動即失敗（不靜默降級）
- 非 dev 環境不得啟用 stub（避免正式環境誤開而回假資料）
- `ai_enabled()`：stub → 一律啟用；live → 有 key 才啟用
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings, _DEFAULT_JWT_SECRET
from app.services.ai_mode import ai_enabled


def test_default_mode_is_live():
    settings = Settings(environment="dev", jwt_secret=_DEFAULT_JWT_SECRET)
    assert settings.ai_mode == "live"


def test_stub_mode_parsed():
    settings = Settings(
        environment="dev", jwt_secret=_DEFAULT_JWT_SECRET, ai_mode="stub"
    )
    assert settings.ai_mode == "stub"


def test_invalid_mode_rejected():
    with pytest.raises(ValidationError):
        Settings(environment="dev", jwt_secret=_DEFAULT_JWT_SECRET, ai_mode="off")


def test_stub_rejected_outside_dev():
    """非 dev 環境啟用 stub → 啟動失敗（與 JWT_SECRET 守則一致）。"""
    with pytest.raises(ValidationError):
        Settings(environment="prod", jwt_secret="a-real-secret", ai_mode="stub")


def test_ai_enabled_live_without_key():
    settings = Settings(
        environment="dev", jwt_secret=_DEFAULT_JWT_SECRET, gemini_api_key=""
    )
    assert ai_enabled(settings) is False


def test_ai_enabled_live_with_key():
    settings = Settings(
        environment="dev", jwt_secret=_DEFAULT_JWT_SECRET, gemini_api_key="fake-key"
    )
    assert ai_enabled(settings) is True


def test_ai_enabled_stub_without_key():
    settings = Settings(
        environment="dev", jwt_secret=_DEFAULT_JWT_SECRET, ai_mode="stub"
    )
    assert ai_enabled(settings) is True
