from functools import lru_cache
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_DEFAULT_JWT_SECRET = "change-me-in-production-please"


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
    gemini_api_key: str = Field(default="")
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
