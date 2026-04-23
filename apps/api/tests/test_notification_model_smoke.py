from __future__ import annotations

import pytest

from app.models.notification import Notification


async def test_notification_row_roundtrip(db_session):
    from app.models.user import User
    from app.auth.password import hash_password

    user = User(email="n@t.io", username="n_user", password_hash=hash_password("secret1234"))
    db_session.add(user)
    await db_session.flush()

    n = Notification(
        user_id=user.id,
        type="system.welcome",
        title="歡迎",
        body="從儀表板開始。",
        link="/dashboard",
    )
    db_session.add(n)
    await db_session.commit()
    await db_session.refresh(n)

    assert n.id is not None
    assert n.user_id == user.id
    assert n.type == "system.welcome"
    assert n.read_at is None
    assert n.created_at is not None
