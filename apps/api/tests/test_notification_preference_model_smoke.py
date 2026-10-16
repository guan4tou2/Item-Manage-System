from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.notification_preference import NotificationPreference


async def _make_user(db_session, name: str):
    from app.models.user import User
    from app.auth.password import hash_password

    user = User(
        email=f"{name}@t.io", username=name, password_hash=hash_password("secret1234")
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_notification_preference_roundtrip(db_session):
    user = await _make_user(db_session, "pref_user")

    row = NotificationPreference(
        user_id=user.id, type="low_stock", channel="email", enabled=False
    )
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)

    assert row.id is not None
    assert row.user_id == user.id
    assert row.type == "low_stock"
    assert row.channel == "email"
    assert row.enabled is False
    assert row.created_at is not None
    assert row.updated_at is not None


async def test_notification_preference_unique_cell(db_session):
    user = await _make_user(db_session, "pref_user2")

    db_session.add(
        NotificationPreference(
            user_id=user.id, type="low_stock", channel="email", enabled=True
        )
    )
    await db_session.commit()

    db_session.add(
        NotificationPreference(
            user_id=user.id, type="low_stock", channel="email", enabled=False
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
