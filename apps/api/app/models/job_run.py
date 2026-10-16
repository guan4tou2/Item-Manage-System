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


class JobRun(Base):
    """排程 job 執行記錄：每次 `POST /api/jobs/{job_name}/run` 一列。

    `running` 開列後立即 commit（部分成功可觀測），收尾更新為
    `succeeded`／`failed` 並寫入 result（含 processed／emitted／errors）。
    """

    __tablename__ = "job_runs"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    job_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
