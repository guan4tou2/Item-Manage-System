from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app import db

class QuantityLog(db.Model):
    __tablename__ = "quantity_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[str] = mapped_column(String(50), index=True)
    item_name: Mapped[str] = mapped_column(String(200), default="")
    user: Mapped[str] = mapped_column(String(50))
    delta: Mapped[int] = mapped_column(Integer)
    old_quantity: Mapped[int] = mapped_column(Integer)
    new_quantity: Mapped[int] = mapped_column(Integer)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id, "item_id": self.item_id, "item_name": self.item_name,
            "user": self.user, "delta": self.delta, "old_quantity": self.old_quantity,
            "new_quantity": self.new_quantity, "reason": self.reason,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M") if self.timestamp else ""
        }
