"""物品模板模型 (M19)"""
import json
from typing import Optional, Dict, Any

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app import db


class ItemTemplate(db.Model):
    __tablename__ = "item_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(50))
    default_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    default_fields: Mapped[str] = mapped_column(Text, default='{}')  # JSON with default values
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_by: Mapped[str] = mapped_column(String(50), default="system")

    def get_defaults(self) -> Dict[str, Any]:
        try:
            return json.loads(self.default_fields or '{}')
        except (ValueError, TypeError):
            return {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "default_type": self.default_type or "",
            "default_fields": self.get_defaults(),
            "icon": self.icon or "",
            "created_by": self.created_by,
        }

    def __repr__(self) -> str:
        return f"<ItemTemplate {self.id}: {self.name}>"
