from __future__ import annotations

import uuid
from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select, update

from app.auth.password import hash_password
from app.clock import today_taipei
from app.models.item import Item
from app.models.item_batch import ItemBatch
from app.models.item_history import QuantityLog
from app.models.user import User
from app.repositories import batches_repository
from app.services import batches_service


async def _user(session) -> User:
    user = User(
        email="svc@test.io",
        username="svc_user",
        password_hash=hash_password("secret1234"),
    )
    session.add(user)
    await session.flush()
    return user


async def _item(session, user, *, quantity: int = 5, track_batches: bool = False) -> Item:
    item = Item(
        owner_id=user.id, name="牛奶", quantity=quantity, track_batches=track_batches
    )
    session.add(item)
    await session.flush()
    return item


async def _active_total(session, item_id) -> int:
    return (
        await session.execute(
            select(func.coalesce(func.sum(ItemBatch.quantity), 0)).where(
                ItemBatch.item_id == item_id, ItemBatch.is_depleted.is_(False)
            )
        )
    ).scalar_one()


async def _assert_invariant(session, item: Item) -> None:
    fresh = (
        await session.execute(select(Item.quantity).where(Item.id == item.id))
    ).scalar_one()
    assert fresh == await _active_total(session, item.id)


async def _logs(session) -> list[QuantityLog]:
    return list(
        (await session.execute(select(QuantityLog).order_by(QuantityLog.created_at)))
        .scalars()
        .all()
    )


async def test_first_batch_absorbs_current_quantity(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=5)

    batch = await batches_service.create_batch(db_session, user.id, item.id)

    assert batch.quantity == 5
    assert batch.expiry_date is None
    assert batch.received_at == today_taipei()
    assert item.track_batches is True
    # 數量未變（5 → 5）→ 不寫 quantity_log
    assert await _logs(db_session) == []
    await _assert_invariant(db_session, item)


async def test_create_batch_explicit_quantity_recalcs_and_logs(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=5)

    batch = await batches_service.create_batch(
        db_session, user.id, item.id, quantity=8, expiry_date=date(2026, 11, 1)
    )

    assert batch.quantity == 8
    assert item.quantity == 8
    logs = await _logs(db_session)
    assert len(logs) == 1
    assert (logs[0].old_quantity, logs[0].new_quantity) == (5, 8)
    assert logs[0].reason == f"batch:add:{batch.id}"
    await _assert_invariant(db_session, item)


async def test_second_batch_requires_quantity(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=5)
    await batches_service.create_batch(db_session, user.id, item.id)

    with pytest.raises(HTTPException) as exc:
        await batches_service.create_batch(db_session, user.id, item.id)
    assert exc.value.status_code == 422


async def test_create_batch_rejects_zero_quantity(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=5)

    with pytest.raises(HTTPException) as exc:
        await batches_service.create_batch(db_session, user.id, item.id, quantity=0)
    assert exc.value.status_code == 422
    assert item.track_batches is False


async def test_consume_from_batch_decrements_and_logs(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=5)
    batch = await batches_service.create_batch(
        db_session, user.id, item.id, quantity=3, expiry_date=date(2026, 10, 20)
    )
    before = len(await _logs(db_session))

    consumed = await batches_service.consume_from_batch(
        db_session, user.id, item.id, batch.id, 2
    )

    assert consumed.quantity == 1
    assert consumed.is_depleted is False
    assert item.quantity == 1
    logs = await _logs(db_session)
    assert len(logs) == before + 1
    assert logs[-1].reason == f"batch:consume:{batch.id}"
    assert (logs[-1].old_quantity, logs[-1].new_quantity) == (3, 1)
    await _assert_invariant(db_session, item)


async def test_consume_exact_amount_marks_depleted(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=3)
    batch = await batches_service.create_batch(db_session, user.id, item.id)

    consumed = await batches_service.consume_from_batch(
        db_session, user.id, item.id, batch.id, 3
    )

    assert consumed.quantity == 0
    assert consumed.is_depleted is True
    assert item.quantity == 0
    await _assert_invariant(db_session, item)


async def test_consume_over_amount_is_409_zero_change(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=2)
    batch = await batches_service.create_batch(db_session, user.id, item.id)
    before = len(await _logs(db_session))

    with pytest.raises(HTTPException) as exc:
        await batches_service.consume_from_batch(db_session, user.id, item.id, batch.id, 5)
    assert exc.value.status_code == 409

    assert item.quantity == 2
    assert (
        await db_session.execute(
            select(ItemBatch.quantity).where(ItemBatch.id == batch.id)
        )
    ).scalar_one() == 2
    assert len(await _logs(db_session)) == before
    await _assert_invariant(db_session, item)


async def test_consume_untracked_item_is_409(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=5)
    orphan = ItemBatch(item_id=item.id, quantity=2)
    db_session.add(orphan)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc:
        await batches_service.consume_from_batch(db_session, user.id, item.id, orphan.id, 1)
    assert exc.value.status_code == 409

    with pytest.raises(HTTPException) as exc:
        await batches_service.consume_fefo(db_session, user.id, item.id, 1)
    assert exc.value.status_code == 409


async def test_consume_fefo_earliest_expiry_first_nulls_last(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=6)
    late = await batches_service.create_batch(
        db_session, user.id, item.id, quantity=2, expiry_date=date(2026, 11, 1)
    )
    early = await batches_service.create_batch(
        db_session, user.id, item.id, quantity=2, expiry_date=date(2026, 10, 20)
    )
    no_expiry = await batches_service.create_batch(db_session, user.id, item.id, quantity=2)

    split = await batches_service.consume_fefo(db_session, user.id, item.id, 3)

    assert split == [(early.id, 2), (late.id, 1)]
    await db_session.refresh(early)
    await db_session.refresh(late)
    await db_session.refresh(no_expiry)
    assert (early.quantity, early.is_depleted) == (0, True)
    assert (late.quantity, late.is_depleted) == (1, False)
    assert no_expiry.quantity == 2
    assert item.quantity == 3
    logs = await _logs(db_session)
    assert logs[-1].reason == "batch:fefo"
    await _assert_invariant(db_session, item)


async def test_consume_fefo_tiebreak_by_received_at(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=2)
    older = await batches_service.create_batch(
        db_session,
        user.id,
        item.id,
        quantity=1,
        expiry_date=date(2026, 10, 20),
        received_at=date(2026, 10, 1),
    )
    newer = await batches_service.create_batch(
        db_session,
        user.id,
        item.id,
        quantity=1,
        expiry_date=date(2026, 10, 20),
        received_at=date(2026, 10, 5),
    )

    split = await batches_service.consume_fefo(db_session, user.id, item.id, 1)

    assert split == [(older.id, 1)]
    assert (
        await db_session.execute(
            select(ItemBatch.quantity).where(ItemBatch.id == newer.id)
        )
    ).scalar_one() == 1


async def test_consume_fefo_insufficient_is_409_zero_change(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=2)
    batch = await batches_service.create_batch(db_session, user.id, item.id)
    before = len(await _logs(db_session))

    with pytest.raises(HTTPException) as exc:
        await batches_service.consume_fefo(db_session, user.id, item.id, 3)
    assert exc.value.status_code == 409

    assert (
        await db_session.execute(
            select(ItemBatch.quantity).where(ItemBatch.id == batch.id)
        )
    ).scalar_one() == 2
    assert item.quantity == 2
    assert len(await _logs(db_session)) == before
    await _assert_invariant(db_session, item)


async def test_update_batch_quantity_recalcs_and_logs(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=5)
    batch = await batches_service.create_batch(db_session, user.id, item.id)

    updated = await batches_service.update_batch(
        db_session, user.id, item.id, batch.id, quantity=8
    )

    assert updated.quantity == 8
    assert item.quantity == 8
    logs = await _logs(db_session)
    assert logs[-1].reason == f"batch:update:{batch.id}"
    assert (logs[-1].old_quantity, logs[-1].new_quantity) == (5, 8)
    await _assert_invariant(db_session, item)


async def test_update_batch_expiry_and_note_no_log(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=5)
    batch = await batches_service.create_batch(db_session, user.id, item.id)
    before = len(await _logs(db_session))

    updated = await batches_service.update_batch(
        db_session,
        user.id,
        item.id,
        batch.id,
        expiry_date=date(2026, 12, 31),
        note="冰箱上層",
    )

    assert updated.expiry_date == date(2026, 12, 31)
    assert updated.note == "冰箱上層"
    assert len(await _logs(db_session)) == before
    await _assert_invariant(db_session, item)


async def test_update_depleted_batch_is_409(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=1)
    batch = await batches_service.create_batch(db_session, user.id, item.id)
    await batches_service.consume_from_batch(db_session, user.id, item.id, batch.id, 1)

    with pytest.raises(HTTPException) as exc:
        await batches_service.update_batch(db_session, user.id, item.id, batch.id, quantity=5)
    assert exc.value.status_code == 409


async def test_delete_batch_recalcs_and_logs(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=5)
    keep = await batches_service.create_batch(db_session, user.id, item.id, quantity=3)
    drop = await batches_service.create_batch(db_session, user.id, item.id, quantity=2)

    await batches_service.delete_batch(db_session, user.id, item.id, drop.id)

    assert item.quantity == 3
    logs = await _logs(db_session)
    assert logs[-1].reason == f"batch:delete:{drop.id}"
    assert (logs[-1].old_quantity, logs[-1].new_quantity) == (5, 3)
    await _assert_invariant(db_session, item)
    remaining = await batches_repository.list_by_item(db_session, item.id)
    assert [b.id for b in remaining] == [keep.id]


async def test_disable_tracking_keeps_quantity_and_clears_batches(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=5)
    await batches_service.create_batch(db_session, user.id, item.id, quantity=3)
    await batches_service.create_batch(db_session, user.id, item.id, quantity=2)
    before = len(await _logs(db_session))

    disabled = await batches_service.disable_tracking(db_session, user.id, item.id)

    assert disabled.track_batches is False
    assert disabled.quantity == 5
    assert await batches_repository.list_by_item(db_session, item.id) == []
    # 合併：數量不變 → 不寫 log
    assert len(await _logs(db_session)) == before


async def test_disable_tracking_is_idempotent(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=5)

    result = await batches_service.disable_tracking(db_session, user.id, item.id)

    assert result.track_batches is False
    assert result.quantity == 5


async def test_adjust_for_stocktake_positive_creates_batch(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=5)
    await batches_service.create_batch(db_session, user.id, item.id)
    stocktake_id = uuid.uuid4()

    await batches_service.adjust_for_stocktake(
        db_session, user.id, item.id, stocktake_id=stocktake_id, actual_quantity=8
    )

    assert item.quantity == 8
    batches = await batches_repository.list_by_item(db_session, item.id)
    assert len(batches) == 2
    added = next(b for b in batches if b.note == f"stocktake:{stocktake_id}")
    assert added.quantity == 3
    assert added.expiry_date is None
    logs = await _logs(db_session)
    assert logs[-1].reason == f"stocktake:{stocktake_id}"
    assert (logs[-1].old_quantity, logs[-1].new_quantity) == (5, 8)
    await _assert_invariant(db_session, item)


async def test_adjust_for_stocktake_negative_consumes_fefo(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=0)
    early = await batches_service.create_batch(
        db_session, user.id, item.id, quantity=2, expiry_date=date(2026, 10, 20)
    )
    late = await batches_service.create_batch(
        db_session, user.id, item.id, quantity=3, expiry_date=date(2026, 11, 1)
    )
    stocktake_id = uuid.uuid4()

    await batches_service.adjust_for_stocktake(
        db_session, user.id, item.id, stocktake_id=stocktake_id, actual_quantity=2
    )

    await db_session.refresh(early)
    await db_session.refresh(late)
    assert (early.quantity, early.is_depleted) == (0, True)
    assert (late.quantity, late.is_depleted) == (2, False)
    assert item.quantity == 2
    logs = await _logs(db_session)
    assert logs[-1].reason == f"stocktake:{stocktake_id}"
    assert (logs[-1].old_quantity, logs[-1].new_quantity) == (5, 2)
    await _assert_invariant(db_session, item)


async def test_adjust_for_stocktake_zero_is_noop(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=5)
    await batches_service.create_batch(db_session, user.id, item.id)
    before = len(await _logs(db_session))

    await batches_service.adjust_for_stocktake(
        db_session, user.id, item.id, stocktake_id=uuid.uuid4(), actual_quantity=5
    )

    assert len(await _logs(db_session)) == before
    await _assert_invariant(db_session, item)


async def test_guarded_decrement_blocks_stale_consumption(db_session):
    user = await _user(db_session)
    item = await _item(db_session, user, quantity=1)
    batch = await batches_service.create_batch(db_session, user.id, item.id)

    # 模擬並行寫入者已在別處把批次耗盡（條件式 UPDATE 前的 stale read 情境）
    await db_session.execute(
        update(ItemBatch.__table__)
        .where(ItemBatch.id == batch.id)
        .values(quantity=0, is_depleted=True)
    )

    assert (
        await batches_repository.decrement_guarded(
            db_session, item_id=item.id, batch_id=batch.id, quantity=1
        )
        is False
    )

    with pytest.raises(HTTPException) as exc:
        await batches_service.consume_from_batch(db_session, user.id, item.id, batch.id, 1)
    assert exc.value.status_code == 409

    stored = (
        await db_session.execute(
            select(ItemBatch.quantity).where(ItemBatch.id == batch.id)
        )
    ).scalar_one()
    assert stored == 0  # 不得為負
