from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag
from app.repositories import tags_repository as repo


async def list_tags(session: AsyncSession, owner_id: UUID, q: str | None) -> list[Tag]:
    return await repo.list_for_owner(session, owner_id, q)
