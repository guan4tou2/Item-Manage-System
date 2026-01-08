"""操作日誌模型"""
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import String, Integer, Text, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app import db


class Log(db.Model):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    user: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    item_id: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    item_name: Mapped[Optional[str]] = mapped_column(String(100))
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    timestamp: Mapped[str] = mapped_column(String(50), default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"), index=True)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "id": self.id,
            "action": self.action,
            "user": self.user,
            "item_id": self.item_id,
            "item_name": self.item_name,
            "details": self.details,
            "timestamp": self.timestamp,
        }

    def __repr__(self) -> str:
        return f"<Log {self.id}: {self.action} by {self.user}>"
