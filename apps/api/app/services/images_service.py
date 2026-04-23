from __future__ import annotations

import uuid as uuidlib
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.image import Image
from app.services.visibility_service import visible_item_owner_ids


_ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_EXT_BY_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


async def upload(session: AsyncSession, owner_id: UUID, upload_file: UploadFile) -> Image:
    settings = get_settings()
    mime = (upload_file.content_type or "").lower()
    if mime not in _ALLOWED_MIME:
        raise HTTPException(status_code=415, detail=f"unsupported mime: {mime!r}")

    data = await upload_file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="empty upload")
    if len(data) > settings.max_image_bytes:
        raise HTTPException(status_code=413, detail="file too large")

    owner_dir = Path(settings.media_dir) / str(owner_id)
    owner_dir.mkdir(parents=True, exist_ok=True)
    img_id = uuidlib.uuid4()
    ext = _EXT_BY_MIME.get(mime, "")
    storage_path = owner_dir / f"{img_id}{ext}"
    storage_path.write_bytes(data)

    image = Image(
        id=img_id,
        owner_id=owner_id,
        filename=upload_file.filename or f"upload{ext}",
        mime_type=mime,
        size_bytes=len(data),
        storage_path=str(storage_path),
    )
    session.add(image)
    await session.commit()
    await session.refresh(image)
    return image


async def get_visible(
    session: AsyncSession, viewer_id: UUID, image_id: UUID
) -> Image | None:
    image = await session.get(Image, image_id)
    if image is None:
        return None
    visible = await visible_item_owner_ids(session, viewer_id)
    if image.owner_id not in visible:
        return None
    return image


async def delete(session: AsyncSession, owner_id: UUID, image_id: UUID) -> bool:
    image = await session.get(Image, image_id)
    if image is None or image.owner_id != owner_id:
        return False
    try:
        Path(image.storage_path).unlink(missing_ok=True)
    except OSError:
        pass
    await session.execute(sa_delete(Image).where(Image.id == image_id))
    await session.commit()
    return True
