from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    action: str
    resource_type: str
    resource_id: Optional[str]
    meta: Optional[dict[str, Any]]
    created_at: datetime
    #: 動作發起者的 email（Phase 39；使用者已刪除或系統事件 → `None`）
    user_email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AuditFacetValue(BaseModel):
    """列舉值與出現次數（供篩選下拉）。"""

    value: str
    count: int


class AuditFacets(BaseModel):
    """全域列舉值（不受列表篩選影響）。"""

    actions: list[AuditFacetValue]
    resource_types: list[AuditFacetValue]


class AuditLogPage(BaseModel):
    """稽核列表分頁信封（Phase 39）。"""

    items: list[AuditLogRead]
    total: int
    limit: int
    offset: int
    facets: AuditFacets
