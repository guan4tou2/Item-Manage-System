"""位置模型"""
from typing import Optional

from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app import db


class Location(db.Model):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    floor: Mapped[Optional[str]] = mapped_column(String(50))
    room: Mapped[Optional[str]] = mapped_column(String(50))
    zone: Mapped[Optional[str]] = mapped_column(String(50))
    order: Mapped[Optional[int]] = mapped_column(Integer, default=0)

    def to_dict(self) -> dict:
        """轉換為字典格式"""
        return {
            "_id": str(self.id),
            "floor": self.floor,
            "room": self.room,
            "zone": self.zone,
            "order": self.order,
        }

    def __repr__(self) -> str:
        return f"<Location {self.id}: {self.floor}/{self.room}/{self.zone}>"
