from __future__ import annotations
import hashlib
import hmac
import json
import logging
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import _utcnow
from app.models.webhook import Webhook, WebhookDelivery
from app.schemas.webhook import WebhookCreate, WebhookRead, WebhookUpdate

logger = logging.getLogger(__name__)


async def list_webhooks(session: AsyncSession, owner_id: UUID) -> list[WebhookRead]:
    stmt = select(Webhook).where(Webhook.owner_id == owner_id).order_by(Webhook.created_at.desc())
    rows = (await session.execute(stmt)).scalars().all()
    return [WebhookRead.model_validate(r) for r in rows]


async def create_webhook(
    session: AsyncSession, owner_id: UUID, body: WebhookCreate
) -> WebhookRead:
    w = Webhook(
        owner_id=owner_id, name=body.name, url=body.url,
        secret=body.secret, events=body.events,
    )
    session.add(w)
    await session.commit()
    await session.refresh(w)
    return WebhookRead.model_validate(w)


async def _ensure_owned(session, owner_id, webhook_id) -> Webhook:
    w = await session.get(Webhook, webhook_id)
    if w is None or w.owner_id != owner_id:
        raise HTTPException(status_code=404, detail="webhook not found")
    return w


async def update_webhook(
    session: AsyncSession, owner_id: UUID, webhook_id: UUID, body: WebhookUpdate
) -> WebhookRead:
    w = await _ensure_owned(session, owner_id, webhook_id)
    fields = body.model_dump(exclude_unset=True)
    for k, v in fields.items():
        setattr(w, k, v)
    await session.commit()
    await session.refresh(w)
    return WebhookRead.model_validate(w)


async def delete_webhook(
    session: AsyncSession, owner_id: UUID, webhook_id: UUID
) -> None:
    stmt = sa_delete(Webhook).where(Webhook.id == webhook_id, Webhook.owner_id == owner_id)
    result = await session.execute(stmt)
    await session.commit()
    if (result.rowcount or 0) == 0:
        raise HTTPException(status_code=404, detail="webhook not found")


async def list_deliveries(
    session: AsyncSession, owner_id: UUID, webhook_id: UUID, limit: int = 50
) -> list[WebhookDelivery]:
    await _ensure_owned(session, owner_id, webhook_id)
    stmt = (
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_id == webhook_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


async def dispatch(
    session: AsyncSession,
    owner_id: UUID,
    event: str,
    payload: dict[str, Any],
) -> None:
    """Fan out an event to all active webhooks for the owner that subscribe to it.
    Fail-soft: never raises; logs + records delivery rows."""
    try:
        rows = (await session.execute(
            select(Webhook).where(
                Webhook.owner_id == owner_id,
                Webhook.is_active.is_(True),
            )
        )).scalars().all()
    except Exception:
        logger.warning("webhook dispatch query failed", exc_info=True)
        return

    eligible = [w for w in rows if (not w.events) or event in w.events]
    if not eligible:
        return

    body_bytes = json.dumps({"event": event, "payload": payload}).encode("utf-8")
    for w in eligible:
        headers = {"Content-Type": "application/json", "X-IMS-Event": event}
        if w.secret:
            headers["X-IMS-Signature"] = _sign(w.secret, body_bytes)
        status_code: int | None = None
        excerpt: str | None = None
        try:
            async with httpx.AsyncClient(timeout=10) as http:
                resp = await http.post(w.url, content=body_bytes, headers=headers)
                status_code = resp.status_code
                excerpt = resp.text[:500]
        except Exception as exc:
            logger.warning("webhook deliver failed: %s", exc)
            excerpt = f"error: {exc}"[:500]
        try:
            session.add(WebhookDelivery(
                webhook_id=w.id, event=event, payload=payload,
                status_code=status_code, response_excerpt=excerpt,
            ))
            w.last_fired_at = _utcnow()
            w.last_status = status_code
            await session.commit()
        except Exception:
            logger.warning("webhook delivery log failed", exc_info=True)
