"""AI 入庫草稿（Phase 32）：建立／清單／狀態機／接受／丟棄。

狀態機（伺服器端唯一來源）：
    pending → processing → ready | failed（終態 accepted | discarded）
- `process`：非終態皆可進入（`processing` 可重入＝卡住復原）；終態 409
- `accept`：`ready` 或 `failed`（手動完成）可接受；`pending`／`processing` 409
- payload（version=1）：`ai`（Gemini 建議）＋ `history`（本人歷史規則建議）
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.base import _utcnow
from app.models.ai_draft import AiDraftItem
from app.services import ai_quota, ai_service, classification_service
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


def _history_dict(
    suggestions: classification_service.ClassificationSuggestions,
) -> dict[str, Any]:
    def bucket(item: Any) -> Optional[dict[str, Any]]:
        if item is None:
            return None
        return {
            "id": item.id,
            "name": item.name,
            "item_count": item.item_count,
            "score": item.score,
        }

    return {
        "category": bucket(suggestions.category),
        "location": bucket(suggestions.location),
        "tags": [
            {"name": tag.name, "item_count": tag.item_count, "score": tag.score}
            for tag in suggestions.tags
        ],
    }


async def process_draft(
    session: AsyncSession, owner_id: UUID, draft_id: UUID
) -> AiDraftItem:
    """辨識單張草稿：配額 → Gemini → 歷史建議 → `ready`／`failed`（一律 200 回狀態）。"""
    draft = await get_owned(session, owner_id, draft_id)
    if draft.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=409, detail=f"draft already {draft.status}"
        )

    # 先落地 `processing`：並行讀取可看到辨識中；卡住時可再次呼叫復原
    draft.status = "processing"
    draft.error_code = None
    await session.commit()

    payload: dict[str, Any] = empty_payload()
    ai: Optional[ai_service.AiSuggestResponse] = None
    error_code: Optional[str] = None

    settings = get_settings()
    image: Any = None
    if draft.image_id is not None:
        image = await get_visible_image(session, owner_id, draft.image_id)
    image_path = Path(image.storage_path) if image is not None else None
    image_ok = image_path is not None and image_path.exists()

    if not image_ok:
        error_code = "image_missing"
    elif not settings.gemini_api_key:
        error_code = "ai_disabled"
    elif not await ai_quota.consume(session, owner_id):
        error_code = "quota_exhausted"
    else:
        try:
            ai = await ai_service.call_gemini_suggest(image_path, image.mime_type)
        except ai_service.AiUpstreamError as exc:
            logger.warning("draft %s AI call failed: %s", draft_id, exc)
            error_code = "upstream_error"

    if ai is not None:
        payload["ai"] = ai.model_dump()
        history = await classification_service.suggest_for_name(
            session, owner_id, ai.name
        )
        payload["history"] = _history_dict(history)

    draft.payload = payload
    draft.error_code = error_code
    draft.status = "ready" if ai is not None else "failed"
    draft.processed_at = _utcnow()
    await session.commit()
    await session.refresh(draft)
    return draft
