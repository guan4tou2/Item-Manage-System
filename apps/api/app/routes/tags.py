from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.tag import TagRead
from app.services import tags_service

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=list[TagRead])
async def list_tags_route(
    q: str | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[TagRead]:
    tags = await tags_service.list_tags(session, user.id, q)
    return [TagRead.model_validate(t) for t in tags]
