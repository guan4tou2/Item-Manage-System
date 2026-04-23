from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_password, verify_password
from app.models.user import User
from app.schemas.user import PasswordChange, UserProfileUpdate


async def update_profile(
    session: AsyncSession, user: User, body: UserProfileUpdate
) -> User:
    fields = body.model_dump(exclude_unset=True, exclude_none=True)
    if "email" in fields and fields["email"] != user.email:
        existing = (await session.execute(
            select(User).where(User.email == fields["email"], User.id != user.id)
        )).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=409, detail="email already taken")
    if "username" in fields and fields["username"] != user.username:
        existing = (await session.execute(
            select(User).where(User.username == fields["username"], User.id != user.id)
        )).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=409, detail="username already taken")
    for k, v in fields.items():
        setattr(user, k, v)
    await session.commit()
    await session.refresh(user)
    return user


async def change_password(
    session: AsyncSession, user: User, body: PasswordChange
) -> None:
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=422, detail="current_password incorrect")
    user.password_hash = hash_password(body.new_password)
    await session.commit()


async def count_admins(session: AsyncSession) -> int:
    return int((await session.execute(
        select(func.count(User.id)).where(User.is_admin.is_(True))
    )).scalar_one())


async def bootstrap_admin_if_none(
    session: AsyncSession, user: User
) -> User:
    if await count_admins(session) > 0:
        raise HTTPException(status_code=409, detail="admin already exists")
    user.is_admin = True
    await session.commit()
    await session.refresh(user)
    return user
