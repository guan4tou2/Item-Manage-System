"""不依賴登入的清單讀取；所有結果皆禁止快取與索引。"""

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.list_share import PublicList
from app.services import list_shares_service

router = APIRouter(prefix="/api/public", tags=["public lists"])
PUBLIC_HEADERS = {
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex, nofollow",
    "Referrer-Policy": "no-referrer",
}


@router.get("/list", response_model=PublicList, response_model_exclude_unset=True)
async def read_public_list(
    response: Response,
    token: str | None = Header(default=None, alias="X-Share-Token"),
    session: AsyncSession = Depends(get_db),
) -> PublicList:
    response.headers.update(PUBLIC_HEADERS)
    try:
        return await list_shares_service.read_public(session, token)
    except HTTPException as exc:
        raise HTTPException(
            exc.status_code, exc.detail, headers=PUBLIC_HEADERS
        ) from None
