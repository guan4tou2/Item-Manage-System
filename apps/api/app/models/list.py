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
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, _utcnow
from app.models.user import GUID


class List(Base):
    __tablename__ = "lists"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('travel','shopping','collection','generic')",
            name="ck_lists_kind_valid",
        ),
        CheckConstraint(
            "budget IS NULL OR budget >= 0",
            name="ck_lists_budget_nonneg",
        ),
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="ck_lists_date_order",
        ),
    )

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    budget: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    entries: Mapped[list["ListEntry"]] = relationship(
        "ListEntry",
        back_populates="list",
        cascade="all, delete-orphan",
        order_by="ListEntry.position",
    )


class ListEntry(Base):
    __tablename__ = "list_entries"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_list_entries_position_nonneg"),
        CheckConstraint(
            "quantity IS NULL OR quantity >= 1",
            name="ck_list_entries_quantity_positive",
        ),
        CheckConstraint(
            "price IS NULL OR price >= 0", name="ck_list_entries_price_nonneg"
        ),
    )

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    list_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("lists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_done: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    list: Mapped[List] = relationship("List", back_populates="entries")
