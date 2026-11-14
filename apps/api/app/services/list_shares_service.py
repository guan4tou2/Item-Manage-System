"""分享憑證生命週期與最小揭露的公開讀取。"""

import hashlib
import secrets
from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import _utcnow
from app.models.list import List, ListEntry
from app.models.list_share import ListShare
from app.models.user import User
from app.schemas.list_share import (
    ListShareCreate,
    ListShareCreated,
    ListShareRead,
    PublicList,
    PublicListEntry,
)
from app.schemas.preferences import currency_from_raw
from app.services import audit_service


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _active(now):
    return or_(ListShare.expires_at.is_(None), ListShare.expires_at > now)


async def _owned(session, owner_id, list_id):
    # 以清單列鎖序列化建立請求，避免並行突破有效連結上限。
    row = (
        await session.execute(
            select(List)
            .where(
                List.id == list_id,
                List.owner_id == owner_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "list not found")
    return row


async def _cleanup(session, list_id, now):
    await session.execute(
        delete(ListShare).where(
            ListShare.list_id == list_id,
            ListShare.expires_at <= now,
        )
    )


async def _audit(session, owner_id, row, action):
    await audit_service.log(
        session,
        user_id=owner_id,
        action=action,
        resource_type="list_share",
        resource_id=str(row.id),
        meta={
            "list_id": str(row.list_id),
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            "show_prices": row.show_prices,
            "token_prefix": row.token_prefix,
        },
    )


async def create_share(
    session: AsyncSession, owner_id: UUID, list_id: UUID, body: ListShareCreate
) -> ListShareCreated:
    await _owned(session, owner_id, list_id)
    now = _utcnow()
    await _cleanup(session, list_id, now)
    count = (
        await session.execute(
            select(func.count())
            .select_from(ListShare)
            .where(
                ListShare.list_id == list_id,
                _active(now),
            )
        )
    ).scalar_one()
    if count >= 5:
        raise HTTPException(409, "share limit reached")
    raw = secrets.token_urlsafe(32)
    row = ListShare(
        list_id=list_id,
        owner_id=owner_id,
        token_hash=_hash(raw),
        token_prefix=raw[:6],
        show_prices=body.show_prices,
        expires_at=now + timedelta(days=body.expires_in_days)
        if body.expires_in_days
        else None,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    result = ListShareCreated(
        **ListShareRead.model_validate(row).model_dump(), token=raw
    )
    await _audit(session, owner_id, row, "list.share_created")
    return result


async def list_shares(
    session: AsyncSession, owner_id: UUID, list_id: UUID
) -> list[ListShareRead]:
    await _owned(session, owner_id, list_id)
    now = _utcnow()
    await _cleanup(session, list_id, now)
    rows = (
        (
            await session.execute(
                select(ListShare)
                .where(
                    ListShare.list_id == list_id,
                    _active(now),
                )
                .order_by(ListShare.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    result = [ListShareRead.model_validate(row) for row in rows]
    await session.commit()
    return result


async def revoke_share(
    session: AsyncSession, owner_id: UUID, list_id: UUID, share_id: UUID
):
    await _owned(session, owner_id, list_id)
    row = (
        await session.execute(
            select(ListShare).where(
                ListShare.id == share_id,
                ListShare.list_id == list_id,
                ListShare.owner_id == owner_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "share not found")
    await session.delete(row)
    await session.commit()
    await _audit(session, owner_id, row, "list.share_revoked")


async def record_access(session: AsyncSession, share_id: UUID):
    """以原子加法計數；失敗只回滾計數交易，不阻擋已建立的公開回應。"""
    try:
        await session.execute(
            update(ListShare)
            .where(ListShare.id == share_id)
            .values(
                last_accessed_at=_utcnow(),
                access_count=ListShare.access_count + 1,
            )
        )
        await session.commit()
    except Exception:
        # 不記錄例外與 SQL 參數，避免憑證雜湊出現在記錄中。
        await session.rollback()


async def read_public(session: AsyncSession, token: str | None) -> PublicList:
    if not token or len(token) != 43:
        raise HTTPException(404, "share not found")
    result = (
        await session.execute(
            select(ListShare, List, User.preferences)
            .join(List, List.id == ListShare.list_id)
            .join(User, User.id == ListShare.owner_id)
            .where(ListShare.token_hash == _hash(token), _active(_utcnow()))
        )
    ).first()
    if result is None:
        raise HTTPException(404, "share not found")
    share, lst, preferences = result
    entries = (
        (
            await session.execute(
                select(ListEntry)
                .where(
                    ListEntry.list_id == lst.id,
                )
                .order_by(ListEntry.position)
            )
        )
        .scalars()
        .all()
    )
    public_entries = []
    for entry in entries:
        fields = dict(
            name=entry.name,
            quantity=entry.quantity,
            note=entry.note,
            is_done=entry.is_done,
            link=entry.link
            if entry.link and entry.link.lower().startswith(("http://", "https://"))
            else None,
        )
        if share.show_prices:
            fields["price"] = entry.price
        public_entries.append(PublicListEntry(**fields))
    fields = dict(
        kind=lst.kind,
        title=lst.title,
        description=lst.description,
        start_date=lst.start_date,
        end_date=lst.end_date,
        entries=public_entries,
    )
    if share.show_prices:
        fields.update(budget=lst.budget, currency=currency_from_raw(preferences or {}))
    response = PublicList(**fields)
    await record_access(session, share.id)
    return response
