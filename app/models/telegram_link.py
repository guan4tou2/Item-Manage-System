from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app import db


class TelegramUserLink(db.Model):
    __tablename__ = "telegram_user_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    telegram_user_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    chat_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<TelegramUserLink {self.user_id}:{self.telegram_user_id}>"
