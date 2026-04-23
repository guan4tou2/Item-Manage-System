from __future__ import annotations
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item
from app.models.warehouse import Warehouse
from app.schemas.warehouse import WarehouseCreate, WarehouseRead, WarehouseUpdate


async def _to_read(session: AsyncSession, w: Warehouse) -> WarehouseRead:
    count = int((await session.execute(
        select(func.count(Item.id)).where(
            Item.warehouse_id == w.id, Item.is_deleted.is_(False)
        )
    )).scalar_one())
    return WarehouseRead(
        id=w.id, name=w.name, description=w.description,
        created_at=w.created_at, item_count=count,
    )


async def list_warehouses(session: AsyncSession, owner_id: UUID) -> list[WarehouseRead]:
    stmt = select(Warehouse).where(Warehouse.owner_id == owner_id).order_by(Warehouse.name)
    rows = (await session.execute(stmt)).scalars().all()
    return [await _to_read(session, r) for r in rows]


async def create_warehouse(
    session: AsyncSession, owner_id: UUID, body: WarehouseCreate
) -> WarehouseRead:
    try:
        w = Warehouse(owner_id=owner_id, name=body.name, description=body.description)
        session.add(w)
        await session.commit()
        await session.refresh(w)
        return await _to_read(session, w)
    except Exception:
        await session.rollback()
        raise HTTPException(status_code=409, detail="name already exists")


async def _ensure_owned(session, owner_id, warehouse_id) -> Warehouse:
    w = await session.get(Warehouse, warehouse_id)
    if w is None or w.owner_id != owner_id:
        raise HTTPException(status_code=404, detail="warehouse not found")
    return w


async def get_warehouse(
    session: AsyncSession, owner_id: UUID, warehouse_id: int
) -> WarehouseRead:
    w = await _ensure_owned(session, owner_id, warehouse_id)
    return await _to_read(session, w)


async def update_warehouse(
    session: AsyncSession, owner_id: UUID, warehouse_id: int, body: WarehouseUpdate
) -> WarehouseRead:
    w = await _ensure_owned(session, owner_id, warehouse_id)
    fields = body.model_dump(exclude_unset=True)
    for k, v in fields.items():
        setattr(w, k, v)
    await session.commit()
    await session.refresh(w)
    return await _to_read(session, w)


async def delete_warehouse(
    session: AsyncSession, owner_id: UUID, warehouse_id: int
) -> None:
    # Items with this warehouse_id will have it SET NULL by FK
    stmt = sa_delete(Warehouse).where(
        Warehouse.id == warehouse_id, Warehouse.owner_id == owner_id
    )
    result = await session.execute(stmt)
    await session.commit()
    if (result.rowcount or 0) == 0:
        raise HTTPException(status_code=404, detail="warehouse not found")
