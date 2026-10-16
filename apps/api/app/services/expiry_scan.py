"""到期掃描 job（Phase 24）。

流程：候選批次（owner 自有、未刪除、未耗盡、有到期日）→ 依 Asia/Taipei
「今天」判級（`d30`/`d7`/`d0` 首次跨入各一次、補發語義；`expired` 每日至
過期 14 天止）→ 冪等寫入 `expiry_alerts`（UNIQUE 為最後防線）→ 每用戶每
類型最多一則摘要 `emit()`（Phase 23 偏好自動過濾）→ per-user commit
（單一用戶失敗不阻斷其他用戶；重跑依 dedupe 只補差額）。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import days_left, today_taipei
from app.models.item import Item
from app.models.item_batch import ItemBatch
from app.repositories import expiry_alerts_repository as alerts_repo
from app.services import jobs_service, notifications_service

logger = logging.getLogger(__name__)

#: 進階級別 → 門檻天數（每批每級只發一次；補發語義）
ADVANCE_LEVEL_DAYS: dict[str, int] = {"d30": 30, "d7": 7, "d0": 0}
EXPIRED_LEVEL = "expired"
#: 過期推播截止：過期 14 天內（含）每日一則；15 天起停止（站內資料保留）
EXPIRED_STOP_DAYS = 14
#: 級別 → 通知偏好類型（d30/d7/d0 共用 expiring_soon）
LEVEL_TYPE: dict[str, str] = {
    "d30": "expiring_soon",
    "d7": "expiring_soon",
    "d0": "expiring_soon",
    EXPIRED_LEVEL: "expired",
}
#: 摘要 deep link（落點：清單到期檢視）
DIGEST_LINK: dict[str, str] = {
    "expiring_soon": "/items?sort=expiry_asc",
    "expired": "/items?expiry=expired&sort=expiry_asc",
}


@dataclass(frozen=True)
class _Candidate:
    batch_id: UUID
    owner_id: UUID
    item_name: str
    expiry_date: date


def _levels_for(expiry_date: date, today: date) -> list[str]:
    """今天應發的級別（未去重既有記錄前）。"""
    remaining = days_left(expiry_date, today=today)
    if remaining < 0:
        return [EXPIRED_LEVEL] if remaining >= -EXPIRED_STOP_DAYS else []
    return [
        level
        for level, threshold in ADVANCE_LEVEL_DAYS.items()
        if remaining <= threshold
    ]


async def _candidates(session: AsyncSession) -> list[_Candidate]:
    stmt = (
        select(ItemBatch.id, Item.owner_id, Item.name, ItemBatch.expiry_date)
        .join(Item, Item.id == ItemBatch.item_id)
        .where(
            ItemBatch.is_depleted.is_(False),
            ItemBatch.expiry_date.is_not(None),
            Item.is_deleted.is_(False),
        )
    )
    return [_Candidate(*row) for row in (await session.execute(stmt)).all()]


async def scan(
    session: AsyncSession, today: date | None = None
) -> jobs_service.JobResult:
    """掃描到期批次並發送摘要；`today` 供測試注入（預設 Asia/Taipei 今天）。"""
    day = today if today is not None else today_taipei()
    result = jobs_service.JobResult()

    candidates = await _candidates(session)
    if not candidates:
        return result

    batch_ids = [c.batch_id for c in candidates]
    fired_advance = await alerts_repo.advance_levels_for(session, batch_ids)
    fired_expired = await alerts_repo.expired_on(session, batch_ids, day)

    by_owner: dict[UUID, list[tuple[_Candidate, list[str]]]] = {}
    for c in candidates:
        new_levels = [
            level
            for level in _levels_for(c.expiry_date, day)
            if (c.batch_id, level) not in fired_advance
            and not (level == EXPIRED_LEVEL and c.batch_id in fired_expired)
        ]
        if new_levels:
            by_owner.setdefault(c.owner_id, []).append((c, new_levels))

    for owner_id, entries in by_owner.items():
        try:
            created, emitted = await _process_owner(session, owner_id, entries, day)
            await session.commit()
        except Exception as exc:  # noqa: BLE001 — 單一用戶失敗不阻斷其他用戶
            await session.rollback()
            logger.exception("expiry-scan 使用者 %s 失敗", owner_id)
            result.errors.append(f"user {owner_id}: {type(exc).__name__}: {exc}")
            continue
        result.processed += created
        result.emitted += emitted

    return result


async def _process_owner(
    session: AsyncSession,
    owner_id: UUID,
    entries: list[tuple[_Candidate, list[str]]],
    day: date,
) -> tuple[int, int]:
    """單一用戶：寫入 alert 列＋每類型一則摘要；回 (新增列數, 摘要數)。"""
    created = 0
    new_by_type: dict[str, list[_Candidate]] = {}
    for c, levels in entries:
        types: set[str] = set()
        for level in levels:
            row = await alerts_repo.create(
                session, batch_id=c.batch_id, level=level, sent_on=day
            )
            if row is not None:
                created += 1
                types.add(LEVEL_TYPE[level])
        for type_key in types:
            new_by_type.setdefault(type_key, []).append(c)

    emitted = 0
    for type_key, group in new_by_type.items():
        await notifications_service.emit(
            session,
            user_id=owner_id,
            type=type_key,
            title=_digest_title(type_key, len(group)),
            body=_digest_body(type_key, min(group, key=lambda c: c.expiry_date), day),
            link=DIGEST_LINK[type_key],
        )
        emitted += 1
    return created, emitted


def _digest_title(type_key: str, count: int) -> str:
    if type_key == "expired":
        return f"{count} 件物品已過期"
    return f"{count} 件物品即將到期"


def _digest_body(type_key: str, soonest: _Candidate, day: date) -> str:
    remaining = days_left(soonest.expiry_date, today=day)
    if type_key == "expired":
        return f"最急：{soonest.item_name}（已過期 {abs(remaining)} 天）"
    if remaining == 0:
        return f"最急：{soonest.item_name}（今天到期）"
    return f"最急：{soonest.item_name}（剩 {remaining} 天）"


jobs_service.register(jobs_service.JobSpec(name="expiry-scan", run=scan))
