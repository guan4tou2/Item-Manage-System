from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.auth.password import hash_password
from app.models.ai_draft import AiDraftItem
from app.models.ai_usage import AiUsage
from app.models.image import Image
from app.models.user import User


async def _user(session, username: str = "draft_user") -> User:
    user = User(
        email=f"{username}@test.io",
        username=username,
        password_hash=hash_password("secret1234"),
    )
    session.add(user)
    await session.flush()
    return user


async def _image(session, owner_id) -> Image:
    image = Image(
        owner_id=owner_id,
        filename="photo.png",
        mime_type="image/png",
        size_bytes=68,
        storage_path="/tmp/photo.png",
    )
    session.add(image)
    await session.flush()
    return image


async def test_draft_roundtrip_defaults(db_session):
    user = await _user(db_session)
    image = await _image(db_session, user.id)
    draft = AiDraftItem(
        owner_id=user.id,
        source="batch_photo",
        image_id=image.id,
        payload={"version": 1},
    )
    db_session.add(draft)
    await db_session.commit()

    assert draft.id is not None
    assert draft.status == "pending"
    assert draft.error_code is None
    assert draft.item_id is None
    assert draft.processed_at is None
    assert draft.created_at is not None
    assert draft.payload["version"] == 1


async def test_draft_image_set_null_on_image_delete(db_session):
    user = await _user(db_session)
    image = await _image(db_session, user.id)
    draft = AiDraftItem(
        owner_id=user.id,
        source="batch_photo",
        image_id=image.id,
        payload={"version": 1},
    )
    db_session.add(draft)
    await db_session.commit()
    draft_id = draft.id

    await db_session.execute(text("PRAGMA foreign_keys=ON"))
    await db_session.delete(image)
    await db_session.commit()
    db_session.expire_all()

    row = (
        await db_session.execute(select(AiDraftItem).where(AiDraftItem.id == draft_id))
    ).scalar_one()
    assert row.image_id is None


async def test_draft_cascade_delete_with_user(db_session):
    user = await _user(db_session)
    draft = AiDraftItem(
        owner_id=user.id,
        source="batch_photo",
        payload={"version": 1},
    )
    db_session.add(draft)
    await db_session.commit()
    draft_id = draft.id

    await db_session.execute(text("PRAGMA foreign_keys=ON"))
    await db_session.delete(user)
    await db_session.commit()

    remaining = (
        await db_session.execute(select(AiDraftItem).where(AiDraftItem.id == draft_id))
    ).scalar_one_or_none()
    assert remaining is None


async def test_ai_usage_unique_per_user_and_day(db_session):
    user = await _user(db_session)
    db_session.add(AiUsage(user_id=user.id, day=date(2026, 10, 19), calls=1))
    await db_session.commit()

    db_session.add(AiUsage(user_id=user.id, day=date(2026, 10, 19), calls=1))
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_ai_usage_same_day_allowed_for_different_users(db_session):
    first = await _user(db_session, "usage_a")
    second = await _user(db_session, "usage_b")
    db_session.add_all(
        [
            AiUsage(user_id=first.id, day=date(2026, 10, 19), calls=2),
            AiUsage(user_id=second.id, day=date(2026, 10, 19), calls=3),
        ]
    )
    await db_session.commit()

    rows = (await db_session.execute(select(AiUsage))).scalars().all()
    assert sorted(row.calls for row in rows) == [2, 3]
