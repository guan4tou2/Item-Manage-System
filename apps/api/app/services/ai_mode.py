"""AI 啟用判定（Phase 35）。

集中「AI 是否可用」的判斷，避免各處散落 `if not settings.gemini_api_key`：

- `AI_MODE=stub`：一律可用（stub 供應器不需要 API 金鑰）
- `AI_MODE=live`：需要 `GEMINI_API_KEY`
"""
from __future__ import annotations

from app.config import Settings, get_settings


def ai_enabled(settings: Settings | None = None) -> bool:
    """AI 功能（建議／收據／搜尋／問答）目前是否可用。"""
    current = settings if settings is not None else get_settings()
    if current.ai_mode == "stub":
        return True
    return bool(current.gemini_api_key)


def is_stub(settings: Settings | None = None) -> bool:
    """目前是否為 stub 模式。"""
    current = settings if settings is not None else get_settings()
    return current.ai_mode == "stub"
