from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, _utcnow
from app.models.favorite_audit_token import JSONType
from app.models.user import GUID


class ItemType(Base):
    __tablename__ = "item_types"
    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_item_types_owner_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class CustomField(Base):
    __tablename__ = "custom_fields"
    __table_args__ = (
        UniqueConstraint("owner_id", "name", name="uq_custom_fields_owner_name"),
        CheckConstraint(
            "field_type IN ('text','number','date','bool')",
            name="ck_custom_fields_type_valid",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    field_type: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class ItemCustomValue(Base):
    __tablename__ = "item_custom_values"
    __table_args__ = (UniqueConstraint("item_id", "custom_field_id", name="uq_icv_item_field"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    custom_field_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("custom_fields.id", ondelete="CASCADE"), nullable=False, index=True
    )
    value: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)


class ItemTemplate(Base):
    __tablename__ = "item_templates"
    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_item_templates_owner_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
