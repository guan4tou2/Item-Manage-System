"""AI 自然語言搜尋與物品問答端點（Phase 34）。

- `POST /api/ai/search`：自然語言 → filters → 既有搜尋 API；LLM 不可用時
  自動退回關鍵字搜尋（一律 200，`fallback_reason` 說明原因）
- `POST /api/ai/ask`：以本人可見物品摘要做 grounding 問答（引用連結）

唯讀端點，不掛 `WriterGuardRoute`（viewer 也可用）；需 opt-in
（`ai_data_sharing_enabled`）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai_search import AskRequest, AskResponse, SearchRequest, SearchResponse
from app.services import ai_search_service

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/search", response_model=SearchResponse)
async def ai_search(
    body: SearchRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SearchResponse:
    return await ai_search_service.search(session, user.id, body.query)


@router.post("/ask", response_model=AskResponse)
async def ai_ask(
    body: AskRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AskResponse:
    return await ai_search_service.ask(
        session, user.id, body.question, body.item_ids
    )
