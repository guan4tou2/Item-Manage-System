"""使用者模型"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Boolean, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from flask_login import UserMixin

from app import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    User: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    Password: Mapped[str] = mapped_column(String(255), nullable=False)
    admin: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # 通知設定
    email: Mapped[Optional[str]] = mapped_column(String(255), default="")
    notify_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_days: Mapped[int] = mapped_column(Integer, default=30)
    notify_time: Mapped[str] = mapped_column(String(10), default="09:00")
    notify_channels: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    reminder_ladder: Mapped[Optional[str]] = mapped_column(String(50), default="30,14,7,3,1")
    last_notification_date: Mapped[Optional[str]] = mapped_column(String(20), default="")
    replacement_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    replacement_intervals: Mapped[Optional[List[dict]]] = mapped_column(JSON, default=list)
    
    # 密碼修改相關
    password_changed: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[str]] = mapped_column(String(50), default="")
    last_login: Mapped[Optional[str]] = mapped_column(String(50), default="")
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(100), default="")
    login_history: Mapped[Optional[List[dict]]] = mapped_column(JSON, default=list)

    def get_id(self) -> str:
        return str(self.id)

    def to_dict(self) -> dict:
        """轉換為字典格式"""
        return {
            "_id": self.id,
            "User": self.User,
            "Password": self.Password,
            "admin": self.admin,
            "email": self.email,
            "notify_enabled": self.notify_enabled,
            "notify_days": self.notify_days,
            "notify_time": self.notify_time,
            "notify_channels": list(self.notify_channels or []),
            "reminder_ladder": self.reminder_ladder or "",
            "last_notification_date": self.last_notification_date,
            "password_changed": self.password_changed,
            "failed_attempts": self.failed_attempts,
            "locked_until": self.locked_until,
            "last_login": self.last_login,
            "last_login_ip": self.last_login_ip,
            "login_history": self.login_history,
        }

    def __repr__(self) -> str:
        return f"<User {self.User}>"
