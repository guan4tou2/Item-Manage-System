from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_DEFAULT_JWT_SECRET = "change-me-in-production-please"

#: AI 執行模式（Phase 35）：`live` 走真實 Gemini；`stub` 走確定性 stub 供應器。
AiMode = Literal["live", "stub"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    app_name: str = "IMS v2 API"
    environment: str = Field(default="dev")
    database_url: str = Field(default="postgresql+asyncpg://ims:ims@localhost:5432/ims")
    redis_url: str = Field(default="redis://localhost:6379/0")
    jwt_secret: str = Field(default=_DEFAULT_JWT_SECRET)
    jwt_algorithm: str = "HS256"
    access_token_ttl_seconds: int = 60 * 15
    refresh_token_ttl_seconds: int = 60 * 60 * 24 * 7
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    media_dir: str = Field(default="/app/media")
    max_image_bytes: int = Field(default=10 * 1024 * 1024)  # 10 MB
    # Public web base URL (used for encoding QR codes and deep links)
    public_web_url: str = Field(default="http://localhost:3000")
    gemini_api_key: str = Field(default="")
    # Phase 35：AI 模式開關（live/stub）；非 dev 環境不得啟用 stub
    ai_mode: AiMode = Field(default="live")
    # AI 每日配額（per-user，Asia/Taipei 換日；<= 0 表示不設限）
    ai_daily_quota: int = Field(default=50)
    # Email (SMTP)
    smtp_host: str = Field(default="")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_from: str = Field(default="")
    # LINE Messaging API
    line_channel_access_token: str = Field(default="")
    # Telegram Bot
    telegram_bot_token: str = Field(default="")
    # Web Push (VAPID)
    vapid_public_key: str = Field(default="")
    vapid_private_key: str = Field(default="")
    vapid_email: str = Field(default="admin@example.com")

    @model_validator(mode="after")
    def _ensure_production_secret(self) -> "Settings":
        if self.environment != "dev" and self.jwt_secret == _DEFAULT_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET must be set explicitly outside dev "
                "(generate with `openssl rand -hex 32`)"
            )
        return self

    @model_validator(mode="after")
    def _ensure_stub_only_in_dev(self) -> "Settings":
        """Phase 35 D1：非 dev 環境不得啟用 stub（避免正式環境誤回假資料）。"""
        if self.environment != "dev" and self.ai_mode == "stub":
            raise ValueError(
                "AI_MODE=stub is only allowed in dev "
                "(stub responses are not real AI results)"
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
