from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, _utcnow
from app.models.user import GUID


class ItemLoan(Base):
    __tablename__ = "item_loans"
    __table_args__ = (
        CheckConstraint(
            "borrower_user_id IS NOT NULL OR borrower_label IS NOT NULL",
            name="ck_loans_borrower_presence",
        ),
        Index(
            "uq_item_loans_one_active",
            "item_id",
            unique=True,
            sqlite_where=text("returned_at IS NULL"),
            postgresql_where=text("returned_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    item_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    borrower_user_id: Mapped[Optional[UUID]] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    borrower_label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    lent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    expected_return: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    returned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
