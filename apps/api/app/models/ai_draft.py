from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, _utcnow
from app.models.favorite_audit_token import JSONType
from app.models.user import GUID


class AiDraftItem(Base):
    """AI 入庫草稿（Phase 32；Phase 33 擴充收據群組）。

    狀態機：`pending → processing → ready | failed`，終態 `accepted | discarded`。
    `payload` 為 `DraftPayload`（version=1：`ai` ＋ `history` 建議；收據另有
    `receipt`／`receipt_item` 快照）。
    `source='receipt'` 的每列＝一個收據品項，同次收據以 `receipt_id` 群組（無 FK）。
    """

    __tablename__ = "ai_draft_items"
    __table_args__ = (
        CheckConstraint(
            "source IN ('batch_photo', 'receipt')",
            name="ck_ai_draft_items_source",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'ready', 'failed', 'accepted', 'discarded')",
            name="ck_ai_draft_items_status",
        ),
        Index("ix_ai_draft_items_owner_status", "owner_id", "status"),
        Index("ix_ai_draft_items_owner_receipt", "owner_id", "receipt_id"),
    )

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    receipt_id: Mapped[Optional[UUID]] = mapped_column(GUID(), nullable=True)
    image_id: Mapped[Optional[UUID]] = mapped_column(
        GUID(), ForeignKey("images.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    error_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    item_id: Mapped[Optional[UUID]] = mapped_column(
        GUID(), ForeignKey("items.id", ondelete="SET NULL"), nullable=True
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
