from __future__ import annotations

import uuid
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, _utcnow
from app.models.user import GUID


class ExpiryAlert(Base):
    """到期提醒 dedupe 記錄：UNIQUE(`batch_id`, `level`, `sent_on`) 為最後防線。

    `d30`／`d7`／`d0` 每批每級一次（不限日期）；`expired` 每日一次
    （同日重跑不重發；隔日為新列）。
    """

    __tablename__ = "expiry_alerts"
    __table_args__ = (
        UniqueConstraint(
            "batch_id", "level", "sent_on", name="uq_expiry_alerts_batch_level_day"
        ),
        Index("ix_expiry_alerts_sent_on", "sent_on"),
    )

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[UUID] = mapped_column(
        GUID(),
        ForeignKey("item_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level: Mapped[str] = mapped_column(String(10), nullable=False)
    sent_on: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
