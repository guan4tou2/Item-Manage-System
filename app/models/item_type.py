"""物品類型模型"""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app import db


class ItemType(db.Model):
    __tablename__ = "item_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<ItemType {self.name}>"
