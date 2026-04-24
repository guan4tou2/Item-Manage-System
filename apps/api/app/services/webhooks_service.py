from __future__ import annotations
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
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

# ---- retry policy (pure) ------------------------------------------------

# Max total attempts including the initial dispatch. Attempt 1 is the live
# dispatch; attempts 2..MAX_ATTEMPTS happen through process_due_retries().
MAX_ATTEMPTS = 5

# Seconds to wait before each retry. BACKOFF_SECONDS[n] is the delay *after
# attempt (n+1) failed*. len() must be >= MAX_ATTEMPTS - 1 so the last real
# attempt can still schedule a next one if we ever raise MAX_ATTEMPTS.
BACKOFF_SECONDS: list[int] = [30, 120, 480, 1800]  # 30s, 2min, 8min, 30min


def is_success(status_code: int | None) -> bool:
    """2xx → success. None (network failure) or 4xx/5xx → failure."""
    return status_code is not None and 200 <= status_code < 300


def backoff_after(attempt: int) -> timedelta | None:
    """Given we just finished this attempt (1-indexed), how long until the
    next one? Returns None when the retry budget is exhausted."""
    if attempt >= MAX_ATTEMPTS:
        return None
    idx = attempt - 1
    if idx < 0 or idx >= len(BACKOFF_SECONDS):
        return None
    return timedelta(seconds=BACKOFF_SECONDS[idx])


# ---- webhook CRUD -------------------------------------------------------


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


# ---- delivery primitive -------------------------------------------------


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


async def _send_once(
    webhook: Webhook, event: str, payload: dict[str, Any]
) -> tuple[int | None, str]:
    """One HTTP POST attempt. Returns (status_code_or_None, response_excerpt).
    Never raises — network failures return (None, error_message)."""
    body_bytes = json.dumps({"event": event, "payload": payload}).encode("utf-8")
    headers = {"Content-Type": "application/json", "X-IMS-Event": event}
    if webhook.secret:
        headers["X-IMS-Signature"] = _sign(webhook.secret, body_bytes)
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            resp = await http.post(webhook.url, content=body_bytes, headers=headers)
            return resp.status_code, resp.text[:500]
    except Exception as exc:
        logger.warning("webhook deliver failed: %s", exc)
        return None, f"error: {exc}"[:500]


async def _record_attempt(
    session: AsyncSession,
    webhook: Webhook,
    event: str,
    payload: dict[str, Any],
    attempt: int,
    status_code: int | None,
    excerpt: str | None,
    now: datetime | None = None,
) -> WebhookDelivery:
    """Insert a WebhookDelivery row for this attempt and schedule the next
    retry if the attempt failed and we still have budget. Updates the parent
    webhook's last_fired_at / last_status. Caller is responsible for commit."""
    now = now or _utcnow()
    row = WebhookDelivery(
        webhook_id=webhook.id,
        event=event,
        payload=payload,
        status_code=status_code,
        response_excerpt=excerpt,
        attempt=attempt,
        next_retry_at=None,
    )
    if not is_success(status_code):
        backoff = backoff_after(attempt)
        if backoff is not None:
            row.next_retry_at = now + backoff
    session.add(row)
    webhook.last_fired_at = now
    webhook.last_status = status_code
    return row


# ---- public dispatch ----------------------------------------------------


async def dispatch(
    session: AsyncSession,
    owner_id: UUID,
    event: str,
    payload: dict[str, Any],
) -> None:
    """Fan out an event to all active webhooks for the owner that subscribe to
    it. Fail-soft: never raises; logs + records delivery rows. Each failed
    initial dispatch schedules a retry; later attempts happen through
    process_due_retries()."""
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

    for w in eligible:
        status_code, excerpt = await _send_once(w, event, payload)
        try:
            await _record_attempt(
                session, w, event, payload, attempt=1,
                status_code=status_code, excerpt=excerpt,
            )
            await session.commit()
        except Exception:
            logger.warning("webhook delivery log failed", exc_info=True)


# ---- retry processing ---------------------------------------------------


async def process_due_retries(
    session: AsyncSession, *, now: datetime | None = None
) -> dict[str, int]:
    """Re-attempt every delivery whose next_retry_at has arrived. Creates a
    new WebhookDelivery row per retry (preserving history) and clears the
    previous row's next_retry_at so it isn't picked up again.

    Returns {processed, succeeded, remaining}.
    """
    current = now or _utcnow()
    due_stmt = (
        select(WebhookDelivery)
        .where(
            WebhookDelivery.next_retry_at.is_not(None),
            WebhookDelivery.next_retry_at <= current,
        )
        .order_by(WebhookDelivery.next_retry_at.asc())
    )
    due = list((await session.execute(due_stmt)).scalars().all())

    processed = 0
    succeeded = 0

    for row in due:
        webhook = await session.get(Webhook, row.webhook_id)
        # Take this row off the queue regardless of outcome.
        row.next_retry_at = None

        if webhook is None or not webhook.is_active:
            # Deleted or disabled — give up silently; no new attempt row.
            continue

        status_code, excerpt = await _send_once(webhook, row.event, row.payload)
        await _record_attempt(
            session, webhook, row.event, row.payload,
            attempt=row.attempt + 1,
            status_code=status_code, excerpt=excerpt,
            now=current,
        )
        processed += 1
        if is_success(status_code):
            succeeded += 1

    await session.commit()

    # Count how many deliveries still have a retry scheduled after this pass.
    remaining_stmt = select(WebhookDelivery).where(
        WebhookDelivery.next_retry_at.is_not(None)
    )
    remaining = len(list((await session.execute(remaining_stmt)).scalars().all()))

    return {"processed": processed, "succeeded": succeeded, "remaining": remaining}


async def retry_delivery_now(
    session: AsyncSession, owner_id: UUID, webhook_id: UUID, delivery_id: UUID
) -> WebhookDelivery:
    """Manually re-send a specific delivery right now. Creates a new attempt
    row. Used by the owner's UI button ("retry this failed delivery")."""
    webhook = await _ensure_owned(session, owner_id, webhook_id)
    row = await session.get(WebhookDelivery, delivery_id)
    if row is None or row.webhook_id != webhook_id:
        raise HTTPException(status_code=404, detail="delivery not found")

    # Take the scheduled retry off (if any) so the automated path doesn't
    # duplicate this attempt.
    row.next_retry_at = None

    status_code, excerpt = await _send_once(webhook, row.event, row.payload)
    new_row = await _record_attempt(
        session, webhook, row.event, row.payload,
        attempt=row.attempt + 1,
        status_code=status_code, excerpt=excerpt,
    )
    await session.commit()
    await session.refresh(new_row)
    return new_row
