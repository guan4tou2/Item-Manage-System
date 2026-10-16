from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, _utcnow
from app.models.favorite_audit_token import JSONType
from app.models.user import GUID


class BarcodeLookup(Base):
    """外部條碼查詢快取：正（payload 有值）負（payload=None）結果皆存，TTL 30 天。

    `code` 為 canonical 形式（`barcode_service.canonicalize`）；`source` 記錄
    處理的 provider（openfoodfacts／openlibrary）；`fetched_at` 供讀取時判定
    是否過期（過期重抓覆寫）。
    """

    __tablename__ = "barcode_lookups"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
