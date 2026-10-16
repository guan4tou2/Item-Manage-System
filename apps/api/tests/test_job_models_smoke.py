from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.auth.password import hash_password
from app.models.expiry_alert import ExpiryAlert
from app.models.item import Item
from app.models.item_batch import ItemBatch
from app.models.job_run import JobRun
from app.models.user import User


async def _batch(session) -> ItemBatch:
    u = User(
        email="jobs@test.io",
        username="jobs_user",
        password_hash=hash_password("secret1234"),
    )
    session.add(u)
    await session.flush()
    item = Item(owner_id=u.id, name="牛奶")
    session.add(item)
    await session.flush()
    batch = ItemBatch(item_id=item.id, quantity=1, expiry_date=date(2026, 11, 1))
    session.add(batch)
    await session.flush()
    return batch


async def test_job_run_roundtrip_defaults(db_session):
    run = JobRun(job_name="expiry-scan", status="running")
    db_session.add(run)
    await db_session.commit()

    assert run.id is not None
    assert run.started_at is not None
    assert run.finished_at is None
    assert run.result is None


async def test_expiry_alert_roundtrip(db_session):
    batch = await _batch(db_session)
    alert = ExpiryAlert(batch_id=batch.id, level="d7", sent_on=date(2026, 10, 16))
    db_session.add(alert)
    await db_session.commit()

    assert alert.id is not None
    assert alert.created_at is not None


async def test_expiry_alert_unique_per_batch_level_day(db_session):
    batch = await _batch(db_session)
    day = date(2026, 10, 16)
    db_session.add(ExpiryAlert(batch_id=batch.id, level="d7", sent_on=day))
    await db_session.commit()

    db_session.add(ExpiryAlert(batch_id=batch.id, level="d7", sent_on=day))
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_expiry_alert_cascade_delete_with_batch(db_session):
    batch = await _batch(db_session)
    db_session.add(
        ExpiryAlert(batch_id=batch.id, level="expired", sent_on=date(2026, 10, 16))
    )
    await db_session.commit()
    batch_id = batch.id

    # SQLite 預設不啟用 FK；開啟後驗證 DB 層 CASCADE 定義
    await db_session.execute(text("PRAGMA foreign_keys=ON"))
    await db_session.delete(batch)
    await db_session.commit()

    remaining = (
        await db_session.execute(
            select(ExpiryAlert).where(ExpiryAlert.batch_id == batch_id)
        )
    ).scalar_one_or_none()
    assert remaining is None
