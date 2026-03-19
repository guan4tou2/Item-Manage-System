"""API Token 模型"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app import db


class APIToken(db.Model):
    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(100))
    token_hash: Mapped[str] = mapped_column(String(255), unique=True)
    token_prefix: Mapped[str] = mapped_column(String(10))  # first 8 chars for display
    scopes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        import json
        scopes_list = []
        if self.scopes:
            try:
                scopes_list = json.loads(self.scopes)
            except (ValueError, TypeError):
                scopes_list = []
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "token_prefix": self.token_prefix,
            "scopes": scopes_list,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<APIToken {self.id}: {self.name} ({self.user_id})>"
