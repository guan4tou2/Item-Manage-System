from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category


async def list_for_owner(session: AsyncSession, owner_id: UUID) -> list[Category]:
    stmt = select(Category).where(Category.owner_id == owner_id).order_by(Category.id)
    return list((await session.execute(stmt)).scalars().all())


async def get_owned(session: AsyncSession, owner_id: UUID, category_id: int) -> Category | None:
    stmt = select(Category).where(Category.id == category_id, Category.owner_id == owner_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def create(session: AsyncSession, owner_id: UUID, name: str, parent_id: int | None) -> Category:
    cat = Category(owner_id=owner_id, name=name, parent_id=parent_id)
    session.add(cat)
    await session.commit()
    await session.refresh(cat)
    return cat


async def update(session: AsyncSession, cat: Category, **fields) -> Category:
    for k, v in fields.items():
        setattr(cat, k, v)
    await session.commit()
    await session.refresh(cat)
    return cat


async def delete(session: AsyncSession, cat: Category) -> None:
    await session.delete(cat)
    await session.commit()
