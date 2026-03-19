"""物品類型模型"""
from typing import Optional

from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db


class ItemType(db.Model):
    __tablename__ = "item_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('item_types.id'), nullable=True)

    parent = relationship("ItemType", remote_side=[id], backref="children")

    def __repr__(self) -> str:
        return f"<ItemType {self.name}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
        }
