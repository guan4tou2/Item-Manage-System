from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import preferences_repository
from app.schemas.preferences import PreferencesRead, PreferencesUpdate


async def get_preferences(
    session: AsyncSession, *, user_id: UUID
) -> PreferencesRead:
    raw = await preferences_repository.get_raw_preferences(session, user_id)
    return PreferencesRead.model_validate(raw)


async def update_preferences(
    session: AsyncSession,
    *,
    user_id: UUID,
    update: PreferencesUpdate,
) -> PreferencesRead:
    current = await preferences_repository.get_raw_preferences(session, user_id)
    incoming = update.model_dump(exclude_none=True)
    merged = {**current, **incoming}
    saved = await preferences_repository.set_raw_preferences(
        session, user_id, merged
    )
    return PreferencesRead.model_validate(saved)
