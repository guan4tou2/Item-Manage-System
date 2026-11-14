"""批次庫存單一入口（roadmap Phase 22 決策 1–5）。

`track_batches=true` 的物品，一切數量變動都必須經由本模組；invariant：

    items.quantity == Σ 未耗盡批次（is_depleted=false）.quantity

    進貨 create_batch ──────┐
    消耗 consume_from_batch ─┤   批次列變更 → recalc（單一 UPDATE…RETURNING）
    消耗 consume_fefo ───────┼─► → commit → quantity_logs（reason 含批次資訊）
    盤點 adjust_for_stocktake ┤
    編輯 update_batch ───────┤
    刪除 delete_batch ───────┘
    disable_tracking：批次合併回單一數量（items.quantity 維持，invariant 退場）

併發：SQLite 測試環境的 `FOR UPDATE` 會被 SQLAlchemy 方言省略，正確性由
`decrement_guarded` 的條件式 UPDATE＋rowcount 檢查承擔；PG 生產環境另以
`get_owned(..., for_update=True)` 鎖 item 列序列化寫入。

首次建立批次（決策 3）：未開啟追蹤的物品建立第一批時自動開啟；`quantity`
省略＝沿用當前 `items.quantity`（當前數量併入一筆無到期日批次）。若帶明確
`quantity`，未耗盡總和以該聲明值為準（差異記入 quantity_logs 留痕）。
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import today_taipei
from app.models.item import Item
from app.models.item_batch import ItemBatch
from app.repositories import batches_repository, items_repository
from app.services import item_history_service

#: 區分「未提供」與「明確設為 None」（PATCH 語義）
UNSET: Any = object()


async def _get_owned_for_update(session: AsyncSession, owner_id: UUID, item_id: UUID) -> Item:
    item = await items_repository.get_owned(session, owner_id, item_id, for_update=True)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return item


async def _ensure_owner(session: AsyncSession, owner_id: UUID, item_id: UUID) -> Item:
    item = await items_repository.get_owned(session, owner_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return item


async def _commit_and_log(
    session: AsyncSession,
    *,
    item: Item,
    owner_id: UUID,
    old_quantity: int,
    reason: str,
) -> int:
    """recalc → commit → 數量有變才寫 quantity_log（沿用 log 自帶 commit 慣例）。"""
    new_quantity = await batches_repository.recalc_item_quantity(session, item.id)
    item.quantity = new_quantity
    await session.commit()
    if new_quantity != old_quantity:
        await item_history_service.log_quantity_change(
            session,
            item_id=item.id,
            user_id=owner_id,
            old_quantity=old_quantity,
            new_quantity=new_quantity,
            reason=reason,
        )
    return new_quantity


async def list_batches(session: AsyncSession, owner_id: UUID, item_id: UUID) -> list[ItemBatch]:
    await _ensure_owner(session, owner_id, item_id)
    return await batches_repository.list_by_item(session, item_id)


async def create_batch(
    session: AsyncSession,
    owner_id: UUID,
    item_id: UUID,
    *,
    quantity: int | None = None,
    expiry_date: date | None = None,
    received_at: date | None = None,
    note: str | None = None,
    unit_cost: Decimal | None = None,
) -> ItemBatch:
    item = await _get_owned_for_update(session, owner_id, item_id)
    first_batch = not item.track_batches
    if quantity is None:
        if not first_batch:
            raise HTTPException(status_code=422, detail="quantity is required")
        quantity = item.quantity
    if quantity < 1:
        raise HTTPException(status_code=422, detail="quantity must be >= 1")

    old_quantity = item.quantity
    item.track_batches = True
    batch = ItemBatch(
        item_id=item.id,
        quantity=quantity,
        expiry_date=expiry_date,
        received_at=received_at if received_at is not None else today_taipei(),
        note=note,
        unit_cost=unit_cost,
    )
    session.add(batch)
    await session.flush()

    await _commit_and_log(
        session,
        item=item,
        owner_id=owner_id,
        old_quantity=old_quantity,
        reason=f"batch:add:{batch.id}",
    )
    await session.refresh(batch)
    return batch


async def update_batch(
    session: AsyncSession,
    owner_id: UUID,
    item_id: UUID,
    batch_id: UUID,
    *,
    quantity: Any = UNSET,
    expiry_date: Any = UNSET,
    note: Any = UNSET,
    unit_cost: Any = UNSET,
) -> ItemBatch:
    item = await _get_owned_for_update(session, owner_id, item_id)
    batch = await batches_repository.get(session, item_id, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")
    if batch.is_depleted:
        raise HTTPException(status_code=409, detail="batch is depleted")

    old_quantity = item.quantity
    if quantity is not UNSET:
        if not isinstance(quantity, int) or quantity < 1:
            raise HTTPException(status_code=422, detail="quantity must be >= 1")
        batch.quantity = quantity
    if expiry_date is not UNSET:
        batch.expiry_date = expiry_date
    if unit_cost is not UNSET:
        batch.unit_cost = unit_cost
    if note is not UNSET:
        batch.note = note

    await session.flush()
    await _commit_and_log(
        session,
        item=item,
        owner_id=owner_id,
        old_quantity=old_quantity,
        reason=f"batch:update:{batch.id}",
    )
    await session.refresh(batch)
    return batch


async def delete_batch(
    session: AsyncSession, owner_id: UUID, item_id: UUID, batch_id: UUID
) -> None:
    item = await _get_owned_for_update(session, owner_id, item_id)
    batch = await batches_repository.get(session, item_id, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")

    old_quantity = item.quantity
    await session.delete(batch)
    await session.flush()
    await _commit_and_log(
        session,
        item=item,
        owner_id=owner_id,
        old_quantity=old_quantity,
        reason=f"batch:delete:{batch.id}",
    )


async def consume_from_batch(
    session: AsyncSession, owner_id: UUID, item_id: UUID, batch_id: UUID, quantity: int
) -> ItemBatch:
    if quantity < 1:
        raise HTTPException(status_code=422, detail="quantity must be >= 1")
    item = await _get_owned_for_update(session, owner_id, item_id)
    if not item.track_batches:
        raise HTTPException(status_code=409, detail="item does not track batches")
    batch = await batches_repository.get(session, item_id, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="batch not found")

    old_quantity = item.quantity
    ok = await batches_repository.decrement_guarded(
        session, item_id=item_id, batch_id=batch_id, quantity=quantity
    )
    if not ok:
        raise HTTPException(status_code=409, detail="insufficient batch quantity")

    await _commit_and_log(
        session,
        item=item,
        owner_id=owner_id,
        old_quantity=old_quantity,
        reason=f"batch:consume:{batch_id}",
    )
    await session.refresh(batch)
    return batch


async def _consume_fefo_locked(
    session: AsyncSession, *, item_id: UUID, quantity: int
) -> list[tuple[UUID, int]] | None:
    """FEFO 消耗核心（呼叫端已持有 item 鎖）。庫存不足時回 None 且零變更。"""
    batches = await batches_repository.list_active(session, item_id)
    if sum(b.quantity for b in batches) < quantity:
        return None

    remaining = quantity
    split: list[tuple[UUID, int]] = []
    for batch in batches:
        if remaining <= 0:
            break
        take = min(batch.quantity, remaining)
        ok = await batches_repository.decrement_guarded(
            session, item_id=item_id, batch_id=batch.id, quantity=take
        )
        if not ok:
            raise HTTPException(
                status_code=409, detail="batch changed concurrently, please retry"
            )
        split.append((batch.id, take))
        remaining -= take
    return split


async def consume_fefo(
    session: AsyncSession, owner_id: UUID, item_id: UUID, quantity: int
) -> list[tuple[UUID, int]]:
    if quantity < 1:
        raise HTTPException(status_code=422, detail="quantity must be >= 1")
    item = await _get_owned_for_update(session, owner_id, item_id)
    if not item.track_batches:
        raise HTTPException(status_code=409, detail="item does not track batches")

    old_quantity = item.quantity
    split = await _consume_fefo_locked(session, item_id=item.id, quantity=quantity)
    if split is None:
        raise HTTPException(status_code=409, detail="insufficient quantity")

    await _commit_and_log(
        session, item=item, owner_id=owner_id, old_quantity=old_quantity, reason="batch:fefo"
    )
    return split


async def disable_tracking(session: AsyncSession, owner_id: UUID, item_id: UUID) -> Item:
    """關閉追蹤（決策 4）：批次合併回單一數量——items.quantity 維持不變。"""
    item = await _get_owned_for_update(session, owner_id, item_id)
    await batches_repository.delete_all_for_item(session, item_id)
    item.track_batches = False
    await session.commit()
    # commit 後重新載入（含 relationships），確保回傳物件可直接轉 ItemRead
    fresh = await items_repository.get_owned(session, owner_id, item_id)
    return fresh if fresh is not None else item


async def adjust_for_stocktake(
    session: AsyncSession,
    owner_id: UUID,
    item_id: UUID,
    *,
    stocktake_id: UUID,
    actual_quantity: int,
) -> None:
    """盤點完成時對 tracked 物品套用差異（決策 2）。

    delta > 0 → 建批次（無到期日，note 記盤點來源）；
    delta < 0 → FEFO 消耗（invariant 保證庫存必足夠）。
    """
    item = await _get_owned_for_update(session, owner_id, item_id)
    delta = actual_quantity - item.quantity
    if delta == 0:
        return

    reason = f"stocktake:{stocktake_id}"
    old_quantity = item.quantity
    if delta > 0:
        session.add(
            ItemBatch(
                item_id=item.id,
                quantity=delta,
                expiry_date=None,
                received_at=today_taipei(),
                note=reason,
            )
        )
        await session.flush()
    else:
        split = await _consume_fefo_locked(session, item_id=item.id, quantity=-delta)
        if split is None:
            raise HTTPException(status_code=409, detail="insufficient quantity")

    await _commit_and_log(
        session, item=item, owner_id=owner_id, old_quantity=old_quantity, reason=reason
    )
