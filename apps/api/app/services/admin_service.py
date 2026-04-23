from __future__ import annotations
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services import notifications_service


async def list_users(session: AsyncSession) -> list[User]:
    stmt = select(User).order_by(User.created_at)
    return list((await session.execute(stmt)).scalars().all())


async def count_active_admins(session: AsyncSession) -> int:
    return int((await session.execute(
        select(func.count(User.id)).where(
            User.is_admin.is_(True), User.is_active.is_(True)
        )
    )).scalar_one())


async def set_active(
    session: AsyncSession, admin_user: User, target_user_id: UUID, is_active: bool
) -> User:
    if target_user_id == admin_user.id:
        raise HTTPException(status_code=422, detail="cannot deactivate self")
    target = await session.get(User, target_user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="user not found")
    # If deactivating, ensure we're not removing the last active admin
    if not is_active and target.is_admin and target.is_active:
        remaining = (await session.execute(
            select(func.count(User.id)).where(
                User.is_admin.is_(True),
                User.is_active.is_(True),
                User.id != target_user_id,
            )
        )).scalar_one()
        if remaining == 0:
            raise HTTPException(status_code=422, detail="cannot deactivate last admin")
    target.is_active = is_active
    await session.commit()
    await session.refresh(target)
    return target


async def send_test_notification(
    session: AsyncSession, admin_user: User, target_user_id: UUID
) -> None:
    target = await session.get(User, target_user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="user not found")
    await notifications_service.emit(
        session,
        user_id=target_user_id,
        type="admin.test",
        title=f"「{admin_user.username}」寄送的測試通知",
        body="此為管理員測試通知，若您看到此訊息代表通知通道運作正常。",
        link="/notifications",
    )
