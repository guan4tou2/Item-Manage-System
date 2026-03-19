"""Webhook 模型"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app import db


class Webhook(db.Model):
    __tablename__ = "webhooks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), index=True)
    url: Mapped[str] = mapped_column(String(500))
    events: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list of event names
    secret: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        import json as _json
        events_list = []
        if self.events:
            try:
                events_list = _json.loads(self.events)
            except Exception:
                events_list = []
        return {
            "id": self.id,
            "user_id": self.user_id,
            "url": self.url,
            "events": events_list,
            "secret": self.secret,
            "is_active": self.is_active,
            "last_triggered_at": self.last_triggered_at.strftime("%Y-%m-%d %H:%M:%S") if self.last_triggered_at else None,
            "failure_count": self.failure_count,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else "",
        }

    def __repr__(self) -> str:
        return f"<Webhook {self.id}: {self.url}>"
