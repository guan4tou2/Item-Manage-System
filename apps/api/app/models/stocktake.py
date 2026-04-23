from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, _utcnow
from app.models.user import GUID


class Stocktake(Base):
    __tablename__ = "stocktakes"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open','completed','cancelled')",
            name="ck_stocktakes_status_valid",
        ),
    )

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class StocktakeItem(Base):
    __tablename__ = "stocktake_items"
    __table_args__ = (
        UniqueConstraint("stocktake_id", "item_id", name="uq_stocktake_items_st_item"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stocktake_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("stocktakes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expected_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
