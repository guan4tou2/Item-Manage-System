from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, _utcnow
from app.models.user import GUID


class ItemBatch(Base):
    """批次庫存：`track_batches=true` 物品的數量明細。

    invariant（由 batches_service 單一入口維護）：
        items.quantity == Σ 未耗盡批次（is_depleted=false）.quantity
    """

    __tablename__ = "item_batches"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_item_batches_quantity_nonneg"),
        CheckConstraint("unit_cost IS NULL OR unit_cost >= 0", name="ck_item_batches_unit_cost_nonneg"),
        Index("ix_item_batches_item_depleted", "item_id", "is_depleted"),
    )

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    item_id: Mapped[UUID] = mapped_column(
        GUID(),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    received_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_depleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
