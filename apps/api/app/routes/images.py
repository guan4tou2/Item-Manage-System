from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.image import ImageRead
from app.services import images_service

router = APIRouter(prefix="/api/images", tags=["images"])


@router.post("", response_model=ImageRead, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ImageRead:
    image = await images_service.upload(session, user.id, file)
    return ImageRead.model_validate(image)


@router.get("/{image_id}")
async def fetch_image(
    image_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FileResponse:
    image = await images_service.get_visible(session, user.id, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="image not found")
    path = Path(image.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="file missing on disk")
    return FileResponse(str(path), media_type=image.mime_type, filename=image.filename)


@router.delete(
    "/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_image(
    image_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    ok = await images_service.delete(session, user.id, image_id)
    if not ok:
        raise HTTPException(status_code=404, detail="image not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
