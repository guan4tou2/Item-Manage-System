from __future__ import annotations

import hashlib
import secrets
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import _utcnow
from app.models.favorite_audit_token import ApiToken
from app.models.user import User
from app.schemas.api_token import ApiTokenCreate, ApiTokenCreated, ApiTokenRead


TOKEN_PREFIX = "ims_pat_"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def list_tokens(session: AsyncSession, user_id: UUID) -> list[ApiTokenRead]:
    stmt = select(ApiToken).where(ApiToken.user_id == user_id).order_by(ApiToken.created_at.desc())
    rows = (await session.execute(stmt)).scalars().all()
    return [ApiTokenRead.model_validate(r) for r in rows]


async def create_token(
    session: AsyncSession, user_id: UUID, body: ApiTokenCreate
) -> ApiTokenCreated:
    raw = TOKEN_PREFIX + secrets.token_urlsafe(32)
    t = ApiToken(user_id=user_id, name=body.name, token_hash=_hash(raw))
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return ApiTokenCreated(
        id=t.id, name=t.name, last_used_at=t.last_used_at,
        created_at=t.created_at, token=raw,
    )


async def delete_token(
    session: AsyncSession, user_id: UUID, token_id: UUID
) -> None:
    stmt = sa_delete(ApiToken).where(ApiToken.id == token_id, ApiToken.user_id == user_id)
    result = await session.execute(stmt)
    await session.commit()
    if (result.rowcount or 0) == 0:
        raise HTTPException(status_code=404, detail="token not found")


async def resolve_user_by_token(
    session: AsyncSession, raw_token: str
) -> User | None:
    """Look up a user by a raw PAT string. Updates last_used_at on success."""
    if not raw_token.startswith(TOKEN_PREFIX):
        return None
    stmt = select(ApiToken).where(ApiToken.token_hash == _hash(raw_token))
    token_row = (await session.execute(stmt)).scalar_one_or_none()
    if token_row is None:
        return None
    user = await session.get(User, token_row.user_id)
    if user is None or not user.is_active:
        return None
    token_row.last_used_at = _utcnow()
    await session.commit()
    return user
