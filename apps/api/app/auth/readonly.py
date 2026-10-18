"""唯讀 viewer 防線（Phase 30）。

- `require_writer`：寫入方法專用依賴；唯讀 viewer → 403。
- `WriterGuardRoute`：`APIRoute` 子類——非 GET/HEAD/OPTIONS 的方法自動掛上
  `require_writer`。以 `APIRouter(route_class=WriterGuardRoute)` 套用於庫存／
  taxonomy 域 routers，避免逐一列舉端點時遺漏。

語意：403 發生於路由依賴階段，早於 body 解析與資源查詢——不存在的資源對
viewer 亦回 403（不洩漏資源存在與否）。讀取路徑完全不受影響。
"""
from __future__ import annotations

from typing import Any, Callable

from fastapi import Depends, HTTPException, status
from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services import visibility_service

_READ_METHODS = {"GET", "HEAD", "OPTIONS"}


async def require_writer(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """唯讀 viewer 不得執行任何寫入操作 → 403。"""
    if await visibility_service.is_read_only(session, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="read-only viewer cannot modify data",
        )


class WriterGuardRoute(APIRoute):
    """對非讀取方法自動附加 `require_writer` 的路由類。"""

    def __init__(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        methods = {str(m).upper() for m in (kwargs.get("methods") or {"GET"})}
        if not methods <= _READ_METHODS:
            dependencies = list(kwargs.get("dependencies") or [])
            dependencies.append(Depends(require_writer))
            kwargs["dependencies"] = dependencies
        super().__init__(path, endpoint, **kwargs)
