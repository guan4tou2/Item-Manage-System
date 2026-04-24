from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.tag import (
    PruneOrphansResult,
    TagMerge,
    TagMergeResult,
    TagRead,
    TagReadWithCount,
    TagRename,
)
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


@router.get("/with-counts", response_model=list[TagReadWithCount])
async def list_tags_with_counts_route(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[TagReadWithCount]:
    rows = await tags_service.list_with_counts(session, user.id)
    return [TagReadWithCount(**r) for r in rows]


@router.patch("/{tag_id}", response_model=TagRead)
async def rename_tag_route(
    tag_id: int,
    body: TagRename,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TagRead:
    tag = await tags_service.rename_tag(session, user.id, tag_id, body.name)
    return TagRead.model_validate(tag)


@router.post("/{tag_id}/merge", response_model=TagMergeResult)
async def merge_tag_route(
    tag_id: int,
    body: TagMerge,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> TagMergeResult:
    result = await tags_service.merge_tags(session, user.id, tag_id, body.target_id)
    return TagMergeResult(**result)


@router.delete(
    "/{tag_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response
)
async def delete_tag_route(
    tag_id: int,
    force: bool = Query(default=False),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    await tags_service.delete_tag(session, user.id, tag_id, force=force)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/prune-orphans", response_model=PruneOrphansResult)
async def prune_orphans_route(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PruneOrphansResult:
    count = await tags_service.prune_orphans(session, user.id)
    return PruneOrphansResult(deleted_count=count)
