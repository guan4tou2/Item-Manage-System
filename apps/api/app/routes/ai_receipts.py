"""AI 收據辨識端點（Phase 33）。

`POST /api/ai/receipts`：多頁收據 → 一次 Gemini 抽取 → 每品項一列 `ready` 草稿。

- 同步完成（不引入背景 worker）；一次呼叫＝1 次配額（與頁數／品項數無關）
- 抽取失敗時不落地任何列（重試＝重新送出同一組圖片）
- 錯誤一律以代碼字串回 `detail`：`ai_disabled`／`quota_exhausted`／
  `upstream_error`／`no_items`；寫入端點掛 `WriterGuardRoute`（viewer 403）
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.readonly import WriterGuardRoute
from app.db.session import get_db
from app.models.user import User
from app.routes.ai_drafts import to_read
from app.schemas.ai import ReceiptCreateRequest
from app.schemas.ai_draft import ReceiptCreateResponse
from app.services import ai_drafts_service

router = APIRouter(route_class=WriterGuardRoute, prefix="/api/ai", tags=["ai"])


@router.post(
    "/receipts",
    response_model=ReceiptCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_receipt(
    body: ReceiptCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ReceiptCreateResponse:
    receipt_id, created, truncated = await ai_drafts_service.create_receipt_drafts(
        session, user.id, body.image_ids
    )
    return ReceiptCreateResponse(
        receipt_id=receipt_id,
        truncated=truncated,
        created=[to_read(row) for row in created],
    )
