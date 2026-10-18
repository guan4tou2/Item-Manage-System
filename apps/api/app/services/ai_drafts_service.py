"""AI 入庫草稿（Phase 32）：建立／清單／狀態機／接受／丟棄。

狀態機（伺服器端唯一來源）：
    pending → processing → ready | failed（終態 accepted | discarded）
- `process`：非終態皆可進入（`processing` 可重入＝卡住復原）；終態 409
- `accept`：`ready` 或 `failed`（手動完成）可接受；`pending`／`processing` 409
- payload（version=1）：`ai`（Gemini 建議）＋ `history`（本人歷史規則建議）
"""
from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_draft import AiDraftItem
from app.services.images_service import get_visible as get_visible_image

logger = logging.getLogger(__name__)

PAYLOAD_VERSION = 1
#: 活動狀態（清單預設範圍）
ACTIVE_STATUSES: tuple[str, ...] = ("pending", "processing", "ready", "failed")
#: 同圖去重範圍（`failed` 不算活動：允許重新上傳同一張照片）
DEDUPE_STATUSES: tuple[str, ...] = ("pending", "processing", "ready")
TERMINAL_STATUSES: tuple[str, ...] = ("accepted", "discarded")
ALL_STATUSES: tuple[str, ...] = ACTIVE_STATUSES + TERMINAL_STATUSES


def empty_payload() -> dict[str, Any]:
    return {
        "version": PAYLOAD_VERSION,
        "ai": None,
        "history": {"category": None, "location": None, "tags": []},
    }


async def get_owned(
    session: AsyncSession, owner_id: UUID, draft_id: UUID
) -> AiDraftItem:
    """本人草稿；不存在或非本人一律 404（不洩漏存在性）。"""
    row = (
        await session.execute(
            select(AiDraftItem).where(
                AiDraftItem.id == draft_id, AiDraftItem.owner_id == owner_id
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="draft not found")
    return row


async def create_drafts(
    session: AsyncSession, owner_id: UUID, image_ids: list[UUID]
) -> tuple[list[AiDraftItem], list[UUID]]:
    """每張圖片建立一筆 `pending` 草稿；同圖已有活動草稿 → 跳過。"""
    created: list[AiDraftItem] = []
    skipped: list[UUID] = []
    for image_id in image_ids:
        image = await get_visible_image(session, owner_id, image_id)
        if image is None:
            raise HTTPException(status_code=404, detail="image not found")
        existing = (
            await session.execute(
                select(AiDraftItem.id).where(
                    AiDraftItem.owner_id == owner_id,
                    AiDraftItem.image_id == image_id,
                    AiDraftItem.status.in_(DEDUPE_STATUSES),
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            skipped.append(image_id)
            continue
        draft = AiDraftItem(
            owner_id=owner_id,
            source="batch_photo",
            image_id=image_id,
            payload=empty_payload(),
        )
        session.add(draft)
        created.append(draft)
    await session.commit()
    for draft in created:
        await session.refresh(draft)
    return created, skipped


async def list_drafts(
    session: AsyncSession,
    owner_id: UUID,
    *,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AiDraftItem], int]:
    """清單（`created_at` DESC）；未指定 `status` 時只回活動四態。"""
    filters = [AiDraftItem.owner_id == owner_id]
    if status is None:
        filters.append(AiDraftItem.status.in_(ACTIVE_STATUSES))
    else:
        filters.append(AiDraftItem.status == status)
    rows = (
        (
            await session.execute(
                select(AiDraftItem)
                .where(*filters)
                .order_by(AiDraftItem.created_at.desc(), AiDraftItem.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )
    total = (
        await session.execute(
            select(func.count()).select_from(AiDraftItem).where(*filters)
        )
    ).scalar_one()
    return list(rows), int(total)


async def counts(session: AsyncSession, owner_id: UUID) -> dict[str, int]:
    """六態計數（缺者補 0），供批量條與入口卡徽章。"""
    rows = (
        await session.execute(
            select(AiDraftItem.status, func.count())
            .where(AiDraftItem.owner_id == owner_id)
            .group_by(AiDraftItem.status)
        )
    ).all()
    result = {status: 0 for status in ALL_STATUSES}
    for status, count in rows:
        result[status] = int(count)
    return result
