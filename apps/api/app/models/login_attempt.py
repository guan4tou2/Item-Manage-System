from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, _utcnow
from app.models.user import GUID


class LoginAttempt(Base):
    """登入失敗紀錄（Phase 43）。

    每次失敗寫入兩列：`kind="account"`（使用者名稱）與 `kind="ip"`（來源）。
    `key_hash` 是 HMAC-SHA256，不保存原始名稱或 IP；索引支援時間窗查詢。
    """

    __tablename__ = "login_attempts"
    __table_args__ = (
        Index(
            "ix_login_attempts_lookup",
            "kind",
            "key_hash",
            "created_at",
        ),
        Index("ix_login_attempts_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(8), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
