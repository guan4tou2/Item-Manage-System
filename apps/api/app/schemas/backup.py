from __future__ import annotations

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class BackupImportEntitySummary(BaseModel):
    """單一實體的匯入摘要；`imported = created + reused + renamed + skipped + errors`。"""

    entity: str
    #: 匯入前帳號內既有列數（preferences 為 1）
    existing: int = 0
    #: 備份檔內列數
    imported: int = 0
    #: 新建列數
    created: int = 0
    #: 名稱匹配沿用既有列數（taxonomy）
    reused: int = 0
    #: 名稱衝突加後綴新建數
    renamed: int = 0
    #: 刻意略過（如 create_only 下已存在的通知偏好格）
    skipped: int = 0
    #: 列級錯誤數
    errors: int = 0


class BackupImportError(BaseModel):
    entity: str
    index: int
    name: Optional[str] = None
    message: str


class BackupReconciliationItem(BaseModel):
    """批次對帳不一致：`quantity` 應等於未耗盡批次總和。"""

    item_id: UUID
    name: str
    quantity: int
    batch_total: int


class BackupImportResult(BaseModel):
    format_version: int
    mode: Literal["create_only", "replace"]
    dry_run: bool
    status: Literal["ok", "partial", "error"]
    #: replace 模式實際（dry-run 為預計）刪除列數；create_only 恆為 0
    deleted_total: int = 0
    entities: list[BackupImportEntitySummary] = []
    errors: list[BackupImportError] = []
    errors_total: int = 0
    warnings: list[str] = []
    reconciliation: list[BackupReconciliationItem] = []
