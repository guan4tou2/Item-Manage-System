from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai import AiSuggestRequest, AiSuggestResponse
from app.services import ai_service

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/suggest-from-image", response_model=AiSuggestResponse)
async def suggest_from_image(
    body: AiSuggestRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AiSuggestResponse:
    return await ai_service.suggest_from_image(session, user.id, body.image_id, body.hint)
