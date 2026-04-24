from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag
from app.repositories import tags_repository as repo


async def list_tags(session: AsyncSession, owner_id: UUID, q: str | None) -> list[Tag]:
    return await repo.list_for_owner(session, owner_id, q)


async def list_with_counts(
    session: AsyncSession, owner_id: UUID
) -> list[dict]:
    rows = await repo.list_with_counts(session, owner_id)
    return [
        {"id": tag.id, "name": tag.name, "item_count": count} for tag, count in rows
    ]


async def rename_tag(
    session: AsyncSession, owner_id: UUID, tag_id: int, new_name: str
) -> Tag:
    tag = await repo.get_by_id(session, owner_id, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="tag not found")
    normalized = repo.normalize(new_name)
    if not normalized:
        raise HTTPException(status_code=422, detail="name cannot be empty")
    if normalized == tag.name:
        return tag  # no-op
    # Check uniqueness under this owner
    existing = await repo.get_by_name(session, owner_id, normalized)
    if existing is not None and existing.id != tag.id:
        raise HTTPException(
            status_code=409, detail=f"tag '{normalized}' already exists"
        )
    return await repo.rename(session, tag, normalized)


async def merge_tags(
    session: AsyncSession, owner_id: UUID, source_id: int, target_id: int
) -> dict:
    if source_id == target_id:
        raise HTTPException(status_code=400, detail="cannot merge a tag into itself")
    source = await repo.get_by_id(session, owner_id, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="source tag not found")
    target = await repo.get_by_id(session, owner_id, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="target tag not found")
    reassigned = await repo.merge(session, source, target)
    return {"target_id": target.id, "reassigned_item_count": reassigned}


async def delete_tag(
    session: AsyncSession, owner_id: UUID, tag_id: int, *, force: bool
) -> None:
    tag = await repo.get_by_id(session, owner_id, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="tag not found")
    if not force:
        item_count = await repo.count_items(session, tag.id)
        if item_count > 0:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"tag is attached to {item_count} item(s); "
                    "pass ?force=true to delete anyway"
                ),
            )
    await repo.delete_tag(session, tag)


async def prune_orphans(session: AsyncSession, owner_id: UUID) -> int:
    return await repo.prune_orphans(session, owner_id)
