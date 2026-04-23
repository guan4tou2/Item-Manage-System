from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.list import (
    ListCreate,
    ListDetail,
    ListEntryCreate,
    ListEntryRead,
    ListEntryUpdate,
    ListListResponse,
    ListSummary,
    ListUpdate,
    ReorderRequest,
)
from app.services import lists_service as svc

router = APIRouter(prefix="/api/lists", tags=["lists"])


@router.get("", response_model=ListListResponse)
async def list_lists(
    kind: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ListListResponse:
    return await svc.list_lists(session, user.id, kind=kind, limit=limit, offset=offset)


@router.post("", response_model=ListSummary, status_code=status.HTTP_201_CREATED)
async def create_list(
    body: ListCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ListSummary:
    return await svc.create_list(session, user.id, body)


@router.get("/{list_id}", response_model=ListDetail)
async def get_list(
    list_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ListDetail:
    return await svc.get_list_detail(session, user.id, list_id)


@router.patch("/{list_id}", response_model=ListSummary)
async def update_list(
    list_id: UUID,
    body: ListUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ListSummary:
    return await svc.update_list(session, user.id, list_id, body)


@router.delete(
    "/{list_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_list(
    list_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    await svc.delete_list(session, user.id, list_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{list_id}/entries",
    response_model=ListEntryRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_entry(
    list_id: UUID,
    body: ListEntryCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ListEntryRead:
    return await svc.create_entry(session, user.id, list_id, body)


@router.patch("/{list_id}/entries/{entry_id}", response_model=ListEntryRead)
async def update_entry(
    list_id: UUID,
    entry_id: UUID,
    body: ListEntryUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ListEntryRead:
    return await svc.update_entry(session, user.id, list_id, entry_id, body)


@router.post("/{list_id}/entries/{entry_id}/toggle", response_model=ListEntryRead)
async def toggle_entry(
    list_id: UUID,
    entry_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ListEntryRead:
    return await svc.toggle_entry(session, user.id, list_id, entry_id)


@router.post(
    "/{list_id}/entries/reorder",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def reorder_entries(
    list_id: UUID,
    body: ReorderRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    await svc.reorder_entries(session, user.id, list_id, body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{list_id}/entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_entry(
    list_id: UUID,
    entry_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    await svc.delete_entry(session, user.id, list_id, entry_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
