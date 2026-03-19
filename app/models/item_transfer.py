"""物品轉讓請求模型 (M29)"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app import db


class ItemTransferRequest(db.Model):
    __tablename__ = "item_transfer_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[str] = mapped_column(String(50), index=True)
    item_name: Mapped[str] = mapped_column(String(100))
    from_user: Mapped[str] = mapped_column(String(50))
    to_user: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, accepted, rejected
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "item_id": self.item_id,
            "item_name": self.item_name,
            "from_user": self.from_user,
            "to_user": self.to_user,
            "status": self.status,
            "message": self.message or "",
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "",
        }

    def __repr__(self) -> str:
        return f"<ItemTransferRequest {self.id}: {self.item_id} {self.from_user}->{self.to_user}>"
