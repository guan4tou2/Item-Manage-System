"""庫存盤點模型"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db


class StocktakeSession(db.Model):
    __tablename__ = "stocktake_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, in_progress, review, committed
    created_by: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    committed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    items = relationship("StocktakeItem", backref="session", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "",
            "committed_at": self.committed_at.strftime("%Y-%m-%d %H:%M") if self.committed_at else "",
            "notes": self.notes or "",
            "item_count": len(self.items) if self.items else 0,
        }


class StocktakeItem(db.Model):
    __tablename__ = "stocktake_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("stocktake_sessions.id"), index=True)
    item_id: Mapped[str] = mapped_column(String(50), index=True)
    item_name: Mapped[str] = mapped_column(String(200), default="")
    expected_qty: Mapped[int] = mapped_column(Integer, default=0)
    actual_qty: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, counted, discrepancy
    counted_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    counted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "item_id": self.item_id,
            "item_name": self.item_name,
            "expected_qty": self.expected_qty,
            "actual_qty": self.actual_qty,
            "status": self.status,
            "counted_by": self.counted_by or "",
            "counted_at": self.counted_at.strftime("%Y-%m-%d %H:%M") if self.counted_at else "",
            "notes": self.notes or "",
        }
