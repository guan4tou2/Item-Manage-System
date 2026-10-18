from __future__ import annotations

import uuid
from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import GUID


class AiUsage(Base):
    """AI 每日配額計數（Phase 32）：`(user_id, day)` 一列，`day` 為 Asia/Taipei 當地日期。

    計次於**嘗試**（呼叫 LLM 前先扣；上游失敗亦計）。
    """

    __tablename__ = "ai_usage"
    __table_args__ = (
        UniqueConstraint("user_id", "day", name="uq_ai_usage_user_day"),
    )

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    day: Mapped[date] = mapped_column(Date(), nullable=False)
    calls: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
