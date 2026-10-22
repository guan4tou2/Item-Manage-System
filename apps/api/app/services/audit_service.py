"""稽核記錄服務（Phase 39 擴充查詢能力）。

- 寫入：`log()`（fail-soft，既有行為）
- 查詢：`query_logs()`（篩選／排序／總數／使用者 email）、`facets()`（列舉值）、
  `export_rows()`（CSV 用，上限截斷）
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import Text, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.favorite_audit_token import AuditLog
from app.models.user import User

logger = logging.getLogger(__name__)

#: facets 每個維度最多回傳的列舉值數（避免下拉選單爆量）
MAX_FACET_VALUES = 50

#: CSV 匯出上限（超過即截斷，維持 `created_at DESC`）
DEFAULT_EXPORT_MAX_ROWS = 10_000

#: LIKE 轉義字元（`%`／`_`／`\` 由使用者輸入轉義，避免變成萬用字元）
_LIKE_ESCAPE = "\\"


async def log(
    session: AsyncSession,
    *,
    user_id: Optional[UUID],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    meta: Optional[dict[str, Any]] = None,
) -> None:
    """Insert an audit log row. Fail-soft like notifications_service.emit."""
    try:
        row = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            meta=meta,
        )
        session.add(row)
        await session.commit()
    except Exception:
        logger.warning("audit log insert failed", exc_info=True)


@dataclass(frozen=True)
class AuditQuery:
    """稽核查詢條件（全部為選填；空白字串視同未提供）。"""

    action: Optional[str] = None
    resource_type: Optional[str] = None
    user_id: Optional[UUID] = None
    q: Optional[str] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None


@dataclass(frozen=True)
class AuditRow:
    """查詢結果的一列（含 JOIN 取得的使用者 email）。"""

    log: AuditLog
    user_email: Optional[str]


@dataclass(frozen=True)
class AuditFacets:
    """列舉值（全域，不受查詢篩選影響）。"""

    actions: list[tuple[str, int]]
    resource_types: list[tuple[str, int]]


def _like_pattern(value: str) -> str:
    """把使用者輸入轉為 LIKE 樣式（轉義 `\\`／`%`／`_`）。"""
    escaped = (
        value.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2)
        .replace("%", f"{_LIKE_ESCAPE}%")
        .replace("_", f"{_LIKE_ESCAPE}_")
    )
    return f"%{escaped}%"


def _conditions(query: AuditQuery) -> list[Any]:
    """把 `AuditQuery` 轉為 SQLAlchemy 條件（空白值略過）。"""
    conditions: list[Any] = []

    action = (query.action or "").strip()
    if action:
        conditions.append(AuditLog.action == action)

    resource_type = (query.resource_type or "").strip()
    if resource_type:
        conditions.append(AuditLog.resource_type == resource_type)

    if query.user_id is not None:
        conditions.append(AuditLog.user_id == query.user_id)

    keyword = (query.q or "").strip()
    if keyword:
        pattern = _like_pattern(keyword)
        conditions.append(
            or_(
                AuditLog.action.ilike(pattern, escape=_LIKE_ESCAPE),
                AuditLog.resource_type.ilike(pattern, escape=_LIKE_ESCAPE),
                AuditLog.resource_id.ilike(pattern, escape=_LIKE_ESCAPE),
                # meta 以 JSON 文字比對：SQLite（TEXT）與 PostgreSQL（jsonb::text）皆可
                cast(AuditLog.meta, Text).ilike(pattern, escape=_LIKE_ESCAPE),
            )
        )

    if query.created_from is not None:
        conditions.append(AuditLog.created_at >= query.created_from)
    if query.created_to is not None:
        conditions.append(AuditLog.created_at < query.created_to)

    return conditions


def _row_query(conditions: list[Any], *, limit: int, offset: int):
    return (
        select(AuditLog, User.email)
        .outerjoin(User, User.id == AuditLog.user_id)
        .where(*conditions)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
        .offset(offset)
    )


async def _rows(
    session: AsyncSession, conditions: list[Any], *, limit: int, offset: int = 0
) -> list[AuditRow]:
    result = await session.execute(_row_query(conditions, limit=limit, offset=offset))
    return [AuditRow(log=log, user_email=email) for log, email in result.all()]


async def query_logs(
    session: AsyncSession,
    query: AuditQuery,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AuditRow], int]:
    """回傳（符合條件的分頁列, 符合條件的總數）。"""
    conditions = _conditions(query)
    rows = await _rows(session, conditions, limit=limit, offset=offset)
    total = (
        await session.execute(
            select(func.count()).select_from(AuditLog).where(*conditions)
        )
    ).scalar_one()
    return rows, int(total)


async def _facet_counts(session: AsyncSession, column) -> list[tuple[str, int]]:
    count = func.count()
    stmt = (
        select(column, count)
        .group_by(column)
        .order_by(count.desc(), column.asc())
        .limit(MAX_FACET_VALUES)
    )
    rows = (await session.execute(stmt)).all()
    return [(str(value), int(hits)) for value, hits in rows if value is not None]


async def facets(session: AsyncSession) -> AuditFacets:
    """列舉值（全域）：動作與資源類型，依出現次數遞減、值遞增。"""
    return AuditFacets(
        actions=await _facet_counts(session, AuditLog.action),
        resource_types=await _facet_counts(session, AuditLog.resource_type),
    )


async def export_rows(
    session: AsyncSession,
    query: AuditQuery,
    *,
    max_rows: int = DEFAULT_EXPORT_MAX_ROWS,
) -> list[AuditRow]:
    """CSV 匯出用：套用相同篩選，最多 `max_rows` 列（`created_at DESC`）。"""
    return await _rows(session, _conditions(query), limit=max_rows)
