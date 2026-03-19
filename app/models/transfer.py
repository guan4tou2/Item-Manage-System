"""倉庫調撥記錄模型"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app import db


class WarehouseTransfer(db.Model):
    __tablename__ = "warehouse_transfers"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[str] = mapped_column(String(50), index=True)
    item_name: Mapped[str] = mapped_column(String(100))
    from_warehouse_id: Mapped[int] = mapped_column(Integer)
    to_warehouse_id: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, completed, cancelled
    requested_by: Mapped[str] = mapped_column(String(50))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "item_id": self.item_id,
            "item_name": self.item_name,
            "from_warehouse_id": self.from_warehouse_id,
            "to_warehouse_id": self.to_warehouse_id,
            "quantity": self.quantity,
            "status": self.status,
            "requested_by": self.requested_by,
            "completed_at": self.completed_at.strftime("%Y-%m-%d %H:%M") if self.completed_at else None,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "",
            "notes": self.notes or "",
        }

    def __repr__(self) -> str:
        return f"<WarehouseTransfer {self.id}: {self.item_id} {self.from_warehouse_id}->{self.to_warehouse_id}>"
