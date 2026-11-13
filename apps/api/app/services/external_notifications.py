"""External notification delivery — email, LINE, Telegram, Web Push.

Each `deliver_*` is fail-soft: logs and returns bool without raising.
`deliver_all` fans out based on which channels are configured + user has linked.
"""
from __future__ import annotations

import json
import logging
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.external_channels import (
    LineUserLink,
    TelegramUserLink,
    WebPushSubscription,
)
from app.models.user import User
from app.services import url_guard

logger = logging.getLogger(__name__)


async def deliver_email(
    to_email: str,
    subject: str,
    body: str,
    *,
    html: Optional[str] = None,
) -> bool:
    """寄送 Email；`html` 提供時附上 HTML alternative（plain-text fallback）。"""
    s = get_settings()
    if not (s.smtp_host and s.smtp_from):
        return False
    try:
        from fastapi_mail import (
            ConnectionConfig,
            FastMail,
            MessageSchema,
            MessageType,
            MultipartSubtypeEnum,
        )

        conf = ConnectionConfig(
            MAIL_USERNAME=s.smtp_user,
            MAIL_PASSWORD=s.smtp_password,
            MAIL_FROM=s.smtp_from,
            MAIL_PORT=s.smtp_port,
            MAIL_SERVER=s.smtp_host,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=False,
            USE_CREDENTIALS=bool(s.smtp_user),
            VALIDATE_CERTS=True,
        )
        message_kwargs: dict = {
            "subject": subject,
            "recipients": [to_email],
            "body": body,
            "subtype": MessageType.plain,
        }
        if html is not None:
            message_kwargs["alternative_body"] = html
            message_kwargs["multipart_subtype"] = MultipartSubtypeEnum.alternative
        message = MessageSchema(**message_kwargs)
        await FastMail(conf).send_message(message)
        return True
    except Exception:
        logger.warning("email deliver failed", exc_info=True)
        return False


async def deliver_line(line_user_id: str, text: str) -> bool:
    s = get_settings()
    if not s.line_channel_access_token:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            resp = await http.post(
                "https://api.line.me/v2/bot/message/push",
                headers={
                    "Authorization": f"Bearer {s.line_channel_access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "to": line_user_id,
                    "messages": [{"type": "text", "text": text[:1000]}],
                },
            )
            return resp.status_code // 100 == 2
    except Exception:
        logger.warning("line deliver failed", exc_info=True)
        return False


async def deliver_telegram(chat_id: str, text: str) -> bool:
    s = get_settings()
    if not s.telegram_bot_token:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            resp = await http.post(
                f"https://api.telegram.org/bot{s.telegram_bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text[:4000]},
            )
            return resp.status_code // 100 == 2
    except Exception:
        logger.warning("telegram deliver failed", exc_info=True)
        return False


def deliver_web_push(sub: WebPushSubscription, title: str, body: str, link: Optional[str]) -> bool:
    s = get_settings()
    if not (s.vapid_private_key and s.vapid_public_key):
        return False
    try:
        from pywebpush import webpush
    except ImportError:
        return False
    # Phase 44：endpoint 是使用者提供的 URL，送出前檢查目的地（防 SSRF）。
    # 既有資料不做 migration；不合格的訂閱在這裡被擋下。
    if not url_guard.is_destination_allowed_sync(sub.endpoint):
        logger.warning("web push destination blocked: subscription_id=%s", sub.id)
        return False
    try:
        import requests

        # 不跟隨 redirect：公網 endpoint 仍可能 3xx 轉向內網。
        http = requests.Session()
        http.max_redirects = 0
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=json.dumps({"title": title, "body": body, "url": link or "/"}),
                vapid_private_key=s.vapid_private_key,
                vapid_claims={"sub": f"mailto:{s.vapid_email}"},
                timeout=10,
                requests_session=http,
            )
        finally:
            http.close()
        return True
    except Exception:
        logger.warning("web push deliver failed", exc_info=True)
        return False


async def deliver_all(
    session: AsyncSession,
    *,
    user_id: UUID,
    title: str,
    body: str,
    link: Optional[str],
    type: str,
    exclude: frozenset[str] = frozenset(),
) -> dict[str, bool]:
    """Attempt delivery across all channels the user has linked.

    Each external channel is filtered through the user's notification
    preferences for `(type, channel)`; locked types always deliver and
    preference lookup failures are fail-soft (deliver).

    `exclude` 讓呼叫端略過特定管道（月報以 HTML 版單獨寄 email，避免重複）。"""
    from app.services.notification_prefs import is_enabled

    user = await session.get(User, user_id)
    if user is None:
        return {}

    results: dict[str, bool] = {}

    # Email
    if (
        "email" not in exclude
        and user.email
        and await is_enabled(session, user_id, type=type, channel="email")
    ):
        results["email"] = await deliver_email(user.email, title, body)

    # LINE
    line_link = (await session.execute(
        select(LineUserLink).where(LineUserLink.user_id == user_id)
    )).scalar_one_or_none()
    if (
        "line" not in exclude
        and line_link
        and await is_enabled(session, user_id, type=type, channel="line")
    ):
        results["line"] = await deliver_line(line_link.line_user_id, f"{title}\n{body}")

    # Telegram
    tg_link = (await session.execute(
        select(TelegramUserLink).where(TelegramUserLink.user_id == user_id)
    )).scalar_one_or_none()
    if (
        "telegram" not in exclude
        and tg_link
        and await is_enabled(session, user_id, type=type, channel="telegram")
    ):
        results["telegram"] = await deliver_telegram(tg_link.chat_id, f"{title}\n{body}")

    # Web Push
    subs = (await session.execute(
        select(WebPushSubscription).where(WebPushSubscription.user_id == user_id)
    )).scalars().all()
    if (
        "web_push" not in exclude
        and subs
        and await is_enabled(session, user_id, type=type, channel="web_push")
    ):
        results["web_push"] = any(deliver_web_push(s, title, body, link) for s in subs)

    return results
