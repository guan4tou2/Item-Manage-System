from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, _utcnow
from app.models.favorite_audit_token import JSONType
from app.models.user import GUID


class Report(Base):
    """月報（Phase 31）：每位使用者、每個期間（`YYYY-MM`，Asia/Taipei）一列。

    `payload` 為 `ReportPayload`（version=1）；唯一約束 `(user_id, period)` 是
    job 冪等的最後防線。
    """

    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("user_id", "period", name="uq_reports_user_period"),
    )

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
