from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services import backup_service

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
