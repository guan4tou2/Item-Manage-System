from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.password import hash_password
from app.models.barcode_lookup import BarcodeLookup
from app.models.item import Item
from app.models.user import User


async def _user(session) -> User:
    u = User(
        email="barcode@test.io",
        username="barcode_user",
        password_hash=hash_password("secret1234"),
    )
    session.add(u)
    await session.flush()
    return u


async def test_item_barcode_roundtrip_and_nonunique(db_session):
    u = await _user(db_session)

    # 同 owner 同 barcode 兩件並存（不設唯一）
    first = Item(owner_id=u.id, name="牛奶", barcode="4710085200014")
    second = Item(owner_id=u.id, name="牛奶（庫存）", barcode="4710085200014")
    plain = Item(owner_id=u.id, name="無條碼")
    db_session.add_all([first, second, plain])
    await db_session.commit()

    assert first.id is not None and second.id is not None
    assert plain.barcode is None

    rows = (
        (
            await db_session.execute(
                select(Item).where(Item.owner_id == u.id, Item.barcode == "4710085200014")
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 2


async def test_barcode_lookup_unique_code(db_session):
    db_session.add(
        BarcodeLookup(
            code="4710085200014",
            source="openfoodfacts",
            payload={"name": "牛奶"},
        )
    )
    await db_session.commit()

    db_session.add(
        BarcodeLookup(code="4710085200014", source="openfoodfacts", payload=None)
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_barcode_lookup_payload_roundtrip_and_negative_cache(db_session):
    hit = BarcodeLookup(
        code="9780306406157",
        source="openlibrary",
        payload={"name": "Book", "description": "作者：A"},
    )
    miss = BarcodeLookup(code="9999999999999", source="openfoodfacts", payload=None)
    db_session.add_all([hit, miss])
    await db_session.commit()

    assert hit.fetched_at is not None
    loaded = (
        await db_session.execute(
            select(BarcodeLookup).where(BarcodeLookup.code == "9780306406157")
        )
    ).scalar_one()
    assert loaded.payload == {"name": "Book", "description": "作者：A"}

    neg = (
        await db_session.execute(
            select(BarcodeLookup).where(BarcodeLookup.code == "9999999999999")
        )
    ).scalar_one()
    assert neg.payload is None
