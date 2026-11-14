"""收據人工核對紀錄；列存在即表示已核對。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, _utcnow
from app.models.user import GUID


class AiReceiptReview(Base):
    __tablename__ = "ai_receipt_reviews"

    receipt_id: Mapped[UUID] = mapped_column(GUID(), primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
