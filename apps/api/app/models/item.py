from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, _utcnow
from app.models.user import GUID


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_items_quantity_nonneg"),
        CheckConstraint(
            "min_quantity IS NULL OR min_quantity >= 0",
            name="ck_items_min_quantity_nonneg",
        ),
    )

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"), default=1)
    min_quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"), index=True)
    image_id: Mapped[Optional[UUID]] = mapped_column(GUID(), ForeignKey("images.id", ondelete="SET NULL"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="items")  # noqa: F821
    location: Mapped[Optional["Location"]] = relationship("Location", back_populates="items")  # noqa: F821
    tags: Mapped[list["Tag"]] = relationship("Tag", secondary="item_tags", back_populates="items")  # noqa: F821
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id])  # noqa: F821
