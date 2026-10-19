"""AI 入庫草稿端點（Phase 32）：只回傳登入者自己的草稿。

- `POST /api/ai/drafts`：多圖建立 `pending` 草稿（1–10 張；同圖活動草稿去重）
- `GET  /api/ai/drafts`：清單（`created_at` DESC、limit／offset／total、六態 counts）
- 寫入端點皆掛 `WriterGuardRoute`（viewer → 403，於路由依賴階段）
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.readonly import WriterGuardRoute
from app.db.session import get_db
from app.models.ai_draft import AiDraftItem
from app.models.user import User
from app.schemas.ai_draft import (
    DraftAccept,
    DraftAcceptResponse,
    DraftCounts,
    DraftCreate,
    DraftCreateResponse,
    DraftDiscardRequest,
    DraftDiscardResponse,
    DraftDiscardSkipped,
    DraftListResponse,
    DraftPayload,
    DraftRead,
    DraftStatus,
)
from app.services import ai_drafts_service

router = APIRouter(
    route_class=WriterGuardRoute, prefix="/api/ai/drafts", tags=["ai"]
)


def to_read(row: AiDraftItem) -> DraftRead:
    return DraftRead(
        id=row.id,
        source=row.source,
        status=row.status,
        image_id=row.image_id,
        item_id=row.item_id,
        error_code=row.error_code,
        payload=DraftPayload.model_validate(row.payload),
        processed_at=row.processed_at,
        created_at=row.created_at,
        receipt_id=row.receipt_id,
    )


@router.post("", response_model=DraftCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_drafts(
    body: DraftCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DraftCreateResponse:
    created, skipped = await ai_drafts_service.create_drafts(
        session, user.id, body.image_ids
    )
    return DraftCreateResponse(
        created=[to_read(row) for row in created],
        skipped_image_ids=skipped,
    )


@router.get("", response_model=DraftListResponse)
async def list_drafts(
    status_filter: Optional[DraftStatus] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DraftListResponse:
    rows, total = await ai_drafts_service.list_drafts(
        session, user.id, status=status_filter, limit=limit, offset=offset
    )
    counts = await ai_drafts_service.counts(session, user.id)
    return DraftListResponse(
        items=[to_read(row) for row in rows],
        total=total,
        counts=DraftCounts(**counts),
    )


@router.post("/{draft_id}/process", response_model=DraftRead)
async def process_draft(
    draft_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DraftRead:
    draft = await ai_drafts_service.process_draft(session, user.id, draft_id)
    return to_read(draft)


@router.post("/{draft_id}/accept", response_model=DraftAcceptResponse)
async def accept_draft(
    draft_id: UUID,
    body: DraftAccept,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DraftAcceptResponse:
    draft, item = await ai_drafts_service.accept_draft(session, user.id, draft_id, body)
    return DraftAcceptResponse(draft=to_read(draft), item=item)


@router.post("/{draft_id}/discard", response_model=DraftRead)
async def discard_draft(
    draft_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DraftRead:
    draft = await ai_drafts_service.discard_draft(session, user.id, draft_id)
    return to_read(draft)


@router.post("/discard", response_model=DraftDiscardResponse)
async def discard_many(
    body: DraftDiscardRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DraftDiscardResponse:
    discarded, skipped = await ai_drafts_service.discard_many(
        session, user.id, body.ids
    )
    return DraftDiscardResponse(
        discarded=discarded,
        skipped=[
            DraftDiscardSkipped(id=draft_id, reason=reason)
            for draft_id, reason in skipped
        ],
    )
