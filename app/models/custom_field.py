"""自訂欄位模型"""
from typing import Optional, Any, Dict

from sqlalchemy import String, Text, Integer, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app import db


class CustomField(db.Model):
    __tablename__ = "custom_fields"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    field_type: Mapped[str] = mapped_column(String(20), nullable=False)  # text, number, date, select, boolean
    options: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string for select options
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str] = mapped_column(String(50), default="")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "field_type": self.field_type,
            "options": self.options or "",
            "required": bool(self.required),
            "sort_order": int(self.sort_order or 0),
            "created_by": self.created_by or "",
        }

    def __repr__(self) -> str:
        return f"<CustomField {self.id}: {self.name}>"


class CustomFieldValue(db.Model):
    __tablename__ = "custom_field_values"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    field_id: Mapped[int] = mapped_column(Integer, ForeignKey("custom_fields.id", ondelete="CASCADE"), index=True)
    value: Mapped[str] = mapped_column(Text, default="")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "item_id": self.item_id,
            "field_id": self.field_id,
            "value": self.value or "",
        }

    def __repr__(self) -> str:
        return f"<CustomFieldValue item={self.item_id} field={self.field_id}>"
