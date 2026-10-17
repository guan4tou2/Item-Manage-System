from __future__ import annotations

import json
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.backup import BackupImportResult
from app.services import backup_import_service, backup_service

router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.get("/export")
async def export_data(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    data = await backup_service.export_full(session, user.id)
    filename = f"ims-backup-{user.username}-{data['exported_at'][:10]}.json"
    return JSONResponse(
        data,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", response_model=BackupImportResult)
async def import_data(
    file: UploadFile = File(...),
    mode: Literal["create_only", "replace"] = Form("create_only"),
    dry_run: bool = Form(False),
    confirm: Optional[str] = Form(None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> BackupImportResult:
    """從 JSON 備份還原（multipart）。`dry_run=true` 只回摘要、零寫入。"""
    raw = await file.read()
    if len(raw) > backup_import_service.MAX_BACKUP_BYTES:
        limit_mb = backup_import_service.MAX_BACKUP_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=413, detail=f"備份檔超過大小上限（{limit_mb} MiB）"
        )
    if mode == "replace" and not dry_run and confirm != backup_import_service.CONFIRM_PHRASE:
        raise HTTPException(
            status_code=400,
            detail=f"「取代」模式需輸入確認字串 {backup_import_service.CONFIRM_PHRASE}",
        )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="備份檔不是有效的 JSON") from exc
    try:
        plan = await backup_import_service.build_plan(session, user.id, payload, mode=mode)
    except backup_import_service.BackupFormatError as exc:
        raise HTTPException(status_code=400, detail=exc.detail) from exc
    if dry_run:
        return backup_import_service.to_result(plan, dry_run=True)
    raise HTTPException(status_code=501, detail="非 dry-run 匯入尚未實作")
