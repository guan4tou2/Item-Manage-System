"""排程備份設定模型"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app import db


class BackupConfig(db.Model):
    __tablename__ = "backup_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    schedule: Mapped[str] = mapped_column(String(20), default="daily")  # daily, weekly, monthly, disabled
    time: Mapped[str] = mapped_column(String(10), default="03:00")
    destination: Mapped[str] = mapped_column(String(20), default="local")  # local, s3
    s3_bucket: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    s3_region: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    local_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    retention_days: Mapped[int] = mapped_column(Integer, default=30)
    last_backup_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_backup_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "schedule": self.schedule,
            "time": self.time,
            "destination": self.destination,
            "s3_bucket": self.s3_bucket or "",
            "s3_region": self.s3_region or "",
            "local_path": self.local_path or "",
            "retention_days": self.retention_days,
            "last_backup_at": self.last_backup_at.strftime("%Y-%m-%d %H:%M:%S") if self.last_backup_at else None,
            "last_backup_status": self.last_backup_status or "",
            "enabled": self.enabled,
        }

    def __repr__(self) -> str:
        return f"<BackupConfig {self.id}: {self.schedule}>"
