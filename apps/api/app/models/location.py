from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import GUID
from app.models.favorite_audit_token import JSONType

if TYPE_CHECKING:
    from app.models.item import Item


class Location(Base):
    """任意深度位置樹（樓層 ＞ 房間 ＞ 櫃子 ＞ 抽屜…）。

    adjacency list（`parent_id`）＋ recursive CTE 查詢；同一 parent 下名稱唯一
    （root 與非 root 各一個 partial unique index，比照 `categories`）。
    `kind` 可為預設鍵（floor／room／shelf／box／other）或自由文字。
    """

    __tablename__ = "locations"
    __table_args__ = (
        Index("ix_locations_owner_parent_sort", "owner_id", "parent_id", "sort_order"),
        Index(
            "uq_locations_owner_root_name",
            "owner_id",
            "name",
            unique=True,
            postgresql_where=text("parent_id IS NULL"),
            sqlite_where=text("parent_id IS NULL"),
        ),
        Index(
            "uq_locations_owner_parent_name",
            "owner_id",
            "parent_id",
            "name",
            unique=True,
            postgresql_where=text("parent_id IS NOT NULL"),
            sqlite_where=text("parent_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("locations.id", ondelete="RESTRICT"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    kind: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    floor_plan_image_id: Mapped[Optional[UUID]] = mapped_column(
        GUID(), ForeignKey("images.id", ondelete="SET NULL"), nullable=True
    )

    plan_region: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)

    parent: Mapped[Optional["Location"]] = relationship(
        "Location", remote_side=[id], back_populates="children"
    )
    children: Mapped[list["Location"]] = relationship(
        "Location", back_populates="parent", passive_deletes=True
    )
    items: Mapped[list["Item"]] = relationship(
        "Item", back_populates="location", passive_deletes=True
    )
