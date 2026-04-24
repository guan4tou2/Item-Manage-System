from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.items_bulk import BulkImportRowError, BulkImportSummary
from app.services import csv_service

router = APIRouter(prefix="/api/items", tags=["items-bulk"])

MAX_CSV_BYTES = 5 * 1024 * 1024  # 5 MB


@router.get("/export.csv")
async def export_items_csv(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    body = await csv_service.export_csv(session, user.id)
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="items.csv"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/bulk-import", response_model=BulkImportSummary)
async def bulk_import_items(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BulkImportSummary:
    if file.content_type not in {"text/csv", "application/vnd.ms-excel", "text/plain"}:
        # Many browsers send text/csv; some send octet-stream — tolerate common variants
        if file.content_type not in {"application/octet-stream"}:
            raise HTTPException(
                status_code=415, detail=f"unsupported content-type: {file.content_type}"
            )
    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="empty file")
    if len(raw) > MAX_CSV_BYTES:
        raise HTTPException(
            status_code=413, detail=f"file exceeds {MAX_CSV_BYTES} bytes"
        )
    summary = await csv_service.import_csv(session, user.id, raw)
    return BulkImportSummary(
        created_count=summary.created_count,
        total_rows=summary.total_rows,
        errors=[
            BulkImportRowError(row=e.row, reason=e.reason) for e in summary.errors
        ],
    )
