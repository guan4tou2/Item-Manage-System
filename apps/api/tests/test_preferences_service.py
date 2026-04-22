from uuid import uuid4

import pytest

from app.auth.password import hash_password
from app.models.user import User
from app.schemas.preferences import PreferencesUpdate
from app.services.preferences_service import (
    get_preferences,
    update_preferences,
)


@pytest.fixture
async def user(db_session):
    user = User(
        email=f"prefs_{uuid4().hex[:8]}@example.com",
        username=f"prefs_{uuid4().hex[:8]}",
        password_hash=hash_password("secret1234"),
        preferences={},
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


class TestGetPreferences:
    async def test_empty_returns_default_theme(self, db_session, user):
        prefs = await get_preferences(db_session, user_id=user.id)
        assert prefs.theme == "system"

    async def test_existing_theme_returned(self, db_session, user):
        user.preferences = {"theme": "dark"}
        await db_session.flush()
        prefs = await get_preferences(db_session, user_id=user.id)
        assert prefs.theme == "dark"


class TestUpdatePreferences:
    async def test_sets_theme(self, db_session, user):
        result = await update_preferences(
            db_session,
            user_id=user.id,
            update=PreferencesUpdate(theme="light"),
        )
        assert result.theme == "light"

    async def test_merges_not_overwrites(self, db_session, user):
        user.preferences = {"theme": "dark", "language": "zh-TW"}
        await db_session.flush()
        result = await update_preferences(
            db_session,
            user_id=user.id,
            update=PreferencesUpdate(theme="light"),
        )
        assert result.theme == "light"
        assert result.model_dump()["language"] == "zh-TW"

    async def test_ignores_none_fields(self, db_session, user):
        user.preferences = {"theme": "dark"}
        await db_session.flush()
        result = await update_preferences(
            db_session,
            user_id=user.id,
            update=PreferencesUpdate(),
        )
        assert result.theme == "dark"
