"""群組模型"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db


class Group(db.Model):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    owner: Mapped[str] = mapped_column(String(50), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    members = relationship("GroupMember", backref="group", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "owner": self.owner,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else "",
        }

    def __repr__(self) -> str:
        return f"<Group {self.id}: {self.name}>"


class GroupMember(db.Model):
    __tablename__ = "group_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id"), index=True)
    username: Mapped[str] = mapped_column(String(50), index=True)
    role: Mapped[str] = mapped_column(String(20), default="member")  # admin, member, viewer
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "group_id": self.group_id,
            "username": self.username,
            "role": self.role,
            "joined_at": self.joined_at.strftime("%Y-%m-%d %H:%M") if self.joined_at else "",
        }

    def __repr__(self) -> str:
        return f"<GroupMember {self.username} in group {self.group_id}>"
