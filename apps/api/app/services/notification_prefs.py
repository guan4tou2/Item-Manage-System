"""通知偏好：預設展開、鎖定類型、覆寫套用。

常數是本模組的對外唯一出口——emit 字串映射、鎖定集合、預設值一律從此取得，
其他模組不得各自複製一份，避免矩陣語意漂移。
"""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.external_channels import (
    LineUserLink,
    TelegramUserLink,
    WebPushSubscription,
)
from app.repositories import notification_preferences_repository as repo

logger = logging.getLogger(__name__)

DEFAULT_ENABLED = True

CHANNELS: tuple[str, ...] = ("in_app", "email", "line", "telegram", "web_push")

# 有序 11 類（key, group）；群組：items／collab／system
TYPES: tuple[tuple[str, str], ...] = (
    ("low_stock", "items"),
    ("expiring_soon", "items"),
    ("expired", "items"),
    ("loan_open", "collab"),
    ("loan_overdue", "collab"),
    ("loan_returned", "collab"),
    ("transfer.request", "collab"),
    ("transfer.accepted", "collab"),
    ("group_invite", "collab"),
    ("report_ready", "system"),
    ("system", "system"),
)

TYPE_KEYS: tuple[str, ...] = tuple(key for key, _group in TYPES)

# 整列鎖定：後端強制開啟，PUT 關閉 → 422
LOCKED_TYPES: frozenset[str] = frozenset({"group_invite", "system"})

# emit 字串 → 矩陣類型；未映射字串視為開啟（新類型在偏好上線前不受限）
EMIT_TYPE_MAP: dict[str, str] = {
    "system.welcome": "system",
    "admin.test": "system",
}

# 預設例外：到期提醒只留站內與 web_push，不外送 email／line／telegram
TYPE_DEFAULT_OVERRIDES: dict[str, dict[str, bool]] = {
    "expired": {"email": False, "line": False, "telegram": False},
    "expiring_soon": {"email": False, "line": False, "telegram": False},
}


class PreferenceUpdateError(ValueError):
    """PUT 驗證失敗：未知 type／channel、鎖定類型不可關閉。"""


def default_enabled(type: str, channel: str) -> bool:
    """(type, channel) 的預設值；未列於覆寫表＝DEFAULT_ENABLED。"""
    return TYPE_DEFAULT_OVERRIDES.get(type, {}).get(channel, DEFAULT_ENABLED)


def resolve_emit_type(type: str) -> str | None:
    """emit 字串 → 矩陣類型；未映射回 None。"""
    if type in TYPE_KEYS:
        return type
    return EMIT_TYPE_MAP.get(type)


async def is_enabled(
    session: AsyncSession, user_id: UUID, *, type: str, channel: str
) -> bool:
    """單格有效值。鎖定類型恆開；未映射字串視為開啟；查詢失敗 fail-soft 視為開啟。"""
    resolved = resolve_emit_type(type)
    if resolved is None:
        logger.debug("unmapped notification type; treated as enabled", extra={"type": type})
        return True
    if resolved in LOCKED_TYPES:
        return True
    try:
        row = await repo.get_cell(session, user_id, type=resolved, channel=channel)
    except Exception:
        logger.warning(
            "notification preference lookup failed; treated as enabled",
            exc_info=True,
            extra={"type": type, "channel": channel},
        )
        return True
    if row is None:
        return default_enabled(resolved, channel)
    return row.enabled


async def channel_availability(session: AsyncSession, user_id: UUID) -> dict[str, bool]:
    """使用者側可用性：in_app／email 恆可用；其餘依綁定狀態。"""
    line = (
        await session.execute(
            select(LineUserLink.id).where(LineUserLink.user_id == user_id).limit(1)
        )
    ).scalar_one_or_none()
    tg = (
        await session.execute(
            select(TelegramUserLink.id)
            .where(TelegramUserLink.user_id == user_id)
            .limit(1)
        )
    ).scalar_one_or_none()
    push_count = (
        await session.execute(
            select(func.count(WebPushSubscription.id)).where(
                WebPushSubscription.user_id == user_id
            )
        )
    ).scalar_one()
    return {
        "in_app": True,
        "email": True,
        "line": line is not None,
        "telegram": tg is not None,
        "web_push": int(push_count) > 0,
    }


async def get_snapshot(session: AsyncSession, user_id: UUID) -> dict:
    """展開完整矩陣（預設＋覆寫）＋鎖定／可用性。"""
    rows = await repo.list_for_user(session, user_id)
    overrides = {(r.type, r.channel): r.enabled for r in rows}

    matrix: dict[str, dict[str, bool]] = {}
    for key in TYPE_KEYS:
        if key in LOCKED_TYPES:
            matrix[key] = {ch: True for ch in CHANNELS}
            continue
        matrix[key] = {
            ch: overrides.get((key, ch), default_enabled(key, ch)) for ch in CHANNELS
        }

    return {
        "types": [
            {"key": key, "group": group, "locked": key in LOCKED_TYPES}
            for key, group in TYPES
        ],
        "channels": list(CHANNELS),
        "matrix": matrix,
        "has_custom": bool(rows),
        "channel_availability": await channel_availability(session, user_id),
    }


async def apply_updates(
    session: AsyncSession, user_id: UUID, updates: list[dict]
) -> dict:
    """批次套用覆寫：先全數驗證、再單交易寫入；`enabled == 預設` 一律刪列。"""
    pending: dict[tuple[str, str], bool] = {}
    for update in updates:
        type_ = update["type"]
        channel = update["channel"]
        enabled = update["enabled"]
        if type_ not in TYPE_KEYS:
            raise PreferenceUpdateError(f"unknown notification type: {type_}")
        if channel not in CHANNELS:
            raise PreferenceUpdateError(f"unknown channel: {channel}")
        if type_ in LOCKED_TYPES and not enabled:
            raise PreferenceUpdateError(
                f"notification type {type_} cannot be disabled"
            )
        pending[(type_, channel)] = enabled

    for (type_, channel), enabled in pending.items():
        if enabled == default_enabled(type_, channel):
            await repo.delete_cell(session, user_id, type=type_, channel=channel)
        else:
            await repo.upsert(
                session, user_id, type=type_, channel=channel, enabled=enabled
            )
    await session.commit()
    return await get_snapshot(session, user_id)


async def reset(session: AsyncSession, user_id: UUID) -> dict:
    """清除全部覆寫＝重置為預設。"""
    await repo.delete_all(session, user_id)
    await session.commit()
    return await get_snapshot(session, user_id)
