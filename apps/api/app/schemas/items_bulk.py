from __future__ import annotations

from pydantic import BaseModel


class BulkImportRowError(BaseModel):
    row: int
    reason: str


class BulkImportSummary(BaseModel):
    created_count: int
    total_rows: int
    errors: list[BulkImportRowError]
