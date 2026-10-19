from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai import (
    AiSuggestRequest,
    AiSuggestResponse,
    ClassificationSuggestRequest,
    HistorySuggestions,
)
from app.services import ai_service, classification_service

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/suggest-from-image", response_model=AiSuggestResponse)
async def suggest_from_image(
    body: AiSuggestRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AiSuggestResponse:
    return await ai_service.suggest_from_image(session, user.id, body.image_id, body.hint)


@router.post("/suggest-classification", response_model=HistorySuggestions)
async def suggest_classification(
    body: ClassificationSuggestRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> HistorySuggestions:
    """以本人歷史資料建議分類／位置／標籤（純規則式；不呼叫 LLM、不消耗配額）。

    LLM 不可用時的替代動線：使用者在草稿卡輸入名稱後即可套用歷史建議。
    """
    suggestions = await classification_service.suggest_for_name(
        session, user.id, body.name
    )
    return HistorySuggestions.model_validate(classification_service.to_payload(suggestions))
