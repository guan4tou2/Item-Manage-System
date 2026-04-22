from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.repositories import categories_repository as repo
from app.schemas.category import CategoryCreate, CategoryTreeNode, CategoryUpdate


def _build_tree(categories: list[Category]) -> list[CategoryTreeNode]:
    by_id: dict[int, CategoryTreeNode] = {
        c.id: CategoryTreeNode(id=c.id, name=c.name, parent_id=c.parent_id, children=[])
        for c in categories
    }
    roots: list[CategoryTreeNode] = []
    for c in categories:
        node = by_id[c.id]
        if c.parent_id is None or c.parent_id not in by_id:
            roots.append(node)
        else:
            by_id[c.parent_id].children.append(node)
    return roots


async def list_tree(session: AsyncSession, owner_id: UUID) -> list[CategoryTreeNode]:
    cats = await repo.list_for_owner(session, owner_id)
    return _build_tree(cats)


async def _validate_parent(
    session: AsyncSession,
    owner_id: UUID,
    parent_id: int | None,
    self_id: int | None = None,
) -> None:
    if parent_id is None:
        return
    if self_id is not None and parent_id == self_id:
        raise HTTPException(status_code=422, detail="category parent would create cycle")
    parent = await repo.get_owned(session, owner_id, parent_id)
    if parent is None:
        raise HTTPException(status_code=422, detail="parent_id not found")
    if self_id is not None:
        cursor = parent
        while cursor is not None and cursor.parent_id is not None:
            if cursor.parent_id == self_id:
                raise HTTPException(status_code=422, detail="category parent would create cycle")
            cursor = await repo.get_owned(session, owner_id, cursor.parent_id)


async def create(session: AsyncSession, owner_id: UUID, body: CategoryCreate) -> Category:
    await _validate_parent(session, owner_id, body.parent_id)
    return await repo.create(session, owner_id, body.name, body.parent_id)


async def update(session: AsyncSession, owner_id: UUID, category_id: int, body: CategoryUpdate) -> Category:
    cat = await repo.get_owned(session, owner_id, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="category not found")
    fields = body.model_dump(exclude_unset=True)
    if "parent_id" in fields:
        await _validate_parent(session, owner_id, fields["parent_id"], self_id=cat.id)
    return await repo.update(session, cat, **fields)


async def delete(session: AsyncSession, owner_id: UUID, category_id: int) -> None:
    cat = await repo.get_owned(session, owner_id, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="category not found")
    await repo.delete(session, cat)
