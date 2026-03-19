"""倉庫模型"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app import db


class Warehouse(db.Model):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    owner: Mapped[str] = mapped_column(String(50), index=True)
    group_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address or "",
            "owner": self.owner,
            "group_id": self.group_id,
            "is_default": self.is_default,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "",
        }

    def __repr__(self) -> str:
        return f"<Warehouse {self.id}: {self.name}>"
