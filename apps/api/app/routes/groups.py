from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.group import (
    GroupAddMember,
    GroupCreate,
    GroupDetail,
    GroupMemberRead,
    GroupSummary,
    GroupUpdate,
)
from app.services import groups_service as svc

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("", response_model=list[GroupSummary])
async def list_groups(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.list_groups(session, user.id)


@router.post("", response_model=GroupSummary, status_code=status.HTTP_201_CREATED)
async def create_group(
    body: GroupCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.create_group(session, user.id, body)


@router.get("/{group_id}", response_model=GroupDetail)
async def get_group(
    group_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.get_group_detail(session, user.id, group_id)


@router.patch("/{group_id}", response_model=GroupSummary)
async def update_group(
    group_id: UUID,
    body: GroupUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.update_group(session, user.id, group_id, body)


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_group(
    group_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await svc.delete_group(session, user.id, group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{group_id}/members", response_model=GroupMemberRead, status_code=status.HTTP_201_CREATED
)
async def add_member(
    group_id: UUID,
    body: GroupAddMember,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.add_member_by_username(session, user.id, group_id, body)


@router.delete(
    "/{group_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def remove_member(
    group_id: UUID,
    user_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await svc.remove_member(session, user.id, group_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
