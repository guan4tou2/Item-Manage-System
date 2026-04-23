from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.db.session import get_db
from app.models.external_channels import LineUserLink, TelegramUserLink, WebPushSubscription
from app.models.user import User
from app.schemas.external_channels import (
    ChannelStatus,
    LineLinkSet,
    TelegramLinkSet,
    VapidPublicKey,
    WebPushSubscriptionCreate,
    WebPushSubscriptionRead,
)
from app.services.external_notifications import deliver_email, deliver_line, deliver_telegram

router = APIRouter(prefix="/api/channels", tags=["channels"])


@router.get("/status", response_model=ChannelStatus)
async def status_(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    s = get_settings()
    line_link = (await session.execute(
        select(LineUserLink).where(LineUserLink.user_id == user.id)
    )).scalar_one_or_none()
    tg_link = (await session.execute(
        select(TelegramUserLink).where(TelegramUserLink.user_id == user.id)
    )).scalar_one_or_none()
    subs = (await session.execute(
        select(WebPushSubscription).where(WebPushSubscription.user_id == user.id)
    )).scalars().all()
    return ChannelStatus(
        email_configured=bool(s.smtp_host and s.smtp_from),
        line_configured=bool(s.line_channel_access_token),
        telegram_configured=bool(s.telegram_bot_token),
        web_push_configured=bool(s.vapid_public_key and s.vapid_private_key),
        user_line_linked=line_link is not None,
        user_telegram_linked=tg_link is not None,
        user_web_push_count=len(subs),
    )


# --- LINE link ---
@router.put("/line", status_code=204, response_class=Response)
async def set_line_link(
    body: LineLinkSet,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    existing = (await session.execute(
        select(LineUserLink).where(LineUserLink.user_id == user.id)
    )).scalar_one_or_none()
    if existing:
        existing.line_user_id = body.line_user_id
    else:
        session.add(LineUserLink(user_id=user.id, line_user_id=body.line_user_id))
    await session.commit()
    return Response(status_code=204)


@router.delete("/line", status_code=204, response_class=Response)
async def unlink_line(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await session.execute(sa_delete(LineUserLink).where(LineUserLink.user_id == user.id))
    await session.commit()
    return Response(status_code=204)


# --- Telegram link ---
@router.put("/telegram", status_code=204, response_class=Response)
async def set_tg_link(
    body: TelegramLinkSet,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    existing = (await session.execute(
        select(TelegramUserLink).where(TelegramUserLink.user_id == user.id)
    )).scalar_one_or_none()
    if existing:
        existing.chat_id = body.chat_id
    else:
        session.add(TelegramUserLink(user_id=user.id, chat_id=body.chat_id))
    await session.commit()
    return Response(status_code=204)


@router.delete("/telegram", status_code=204, response_class=Response)
async def unlink_tg(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await session.execute(sa_delete(TelegramUserLink).where(TelegramUserLink.user_id == user.id))
    await session.commit()
    return Response(status_code=204)


# --- Web Push subscriptions ---
@router.get("/vapid-public-key", response_model=VapidPublicKey)
async def vapid_public_key():
    s = get_settings()
    return VapidPublicKey(public_key=s.vapid_public_key)


@router.get("/web-push/subscriptions", response_model=list[WebPushSubscriptionRead])
async def list_web_push(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    subs = (await session.execute(
        select(WebPushSubscription).where(WebPushSubscription.user_id == user.id)
    )).scalars().all()
    return [WebPushSubscriptionRead.model_validate(s) for s in subs]


@router.post("/web-push/subscriptions", response_model=WebPushSubscriptionRead, status_code=201)
async def add_web_push(
    body: WebPushSubscriptionCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    # upsert by endpoint for this user
    existing = (await session.execute(
        select(WebPushSubscription).where(WebPushSubscription.endpoint == body.endpoint)
    )).scalar_one_or_none()
    if existing:
        existing.user_id = user.id
        existing.p256dh = body.p256dh
        existing.auth = body.auth
        sub = existing
    else:
        sub = WebPushSubscription(
            user_id=user.id, endpoint=body.endpoint, p256dh=body.p256dh, auth=body.auth,
        )
        session.add(sub)
    await session.commit()
    await session.refresh(sub)
    return WebPushSubscriptionRead.model_validate(sub)


@router.delete("/web-push/subscriptions/{sub_id}", status_code=204, response_class=Response)
async def remove_web_push(
    sub_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        sa_delete(WebPushSubscription).where(
            WebPushSubscription.id == sub_id,
            WebPushSubscription.user_id == user.id,
        )
    )
    await session.commit()
    if (result.rowcount or 0) == 0:
        raise HTTPException(status_code=404, detail="subscription not found")
    return Response(status_code=204)


# --- Test send ---
@router.post("/test/{channel}")
async def test_send(
    channel: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    title = "IMS 測試通知"
    body = "此為測試訊息，若您看到這則代表該通道運作正常。"
    if channel == "email":
        if not user.email:
            raise HTTPException(status_code=400, detail="user has no email")
        ok = await deliver_email(user.email, title, body)
    elif channel == "line":
        link = (await session.execute(
            select(LineUserLink).where(LineUserLink.user_id == user.id)
        )).scalar_one_or_none()
        if link is None:
            raise HTTPException(status_code=400, detail="no line link")
        ok = await deliver_line(link.line_user_id, f"{title}\n{body}")
    elif channel == "telegram":
        link = (await session.execute(
            select(TelegramUserLink).where(TelegramUserLink.user_id == user.id)
        )).scalar_one_or_none()
        if link is None:
            raise HTTPException(status_code=400, detail="no telegram link")
        ok = await deliver_telegram(link.chat_id, f"{title}\n{body}")
    elif channel == "web_push":
        from app.services.external_notifications import deliver_web_push
        subs = (await session.execute(
            select(WebPushSubscription).where(WebPushSubscription.user_id == user.id)
        )).scalars().all()
        if not subs:
            raise HTTPException(status_code=400, detail="no web push subscription")
        ok = any(deliver_web_push(s, title, body, "/notifications") for s in subs)
    else:
        raise HTTPException(status_code=400, detail="unknown channel")
    return {"delivered": ok}
