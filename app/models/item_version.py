"""物品版本歷史模型"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app import db


class ItemVersion(db.Model):
    __tablename__ = "item_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON snapshot
    changed_by: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    change_summary: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "item_id": self.item_id,
            "version": self.version,
            "data": self.data,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.strftime("%Y-%m-%d %H:%M:%S") if self.changed_at else None,
            "change_summary": self.change_summary or "",
        }

    def __repr__(self) -> str:
        return f"<ItemVersion {self.item_id} v{self.version}>"
