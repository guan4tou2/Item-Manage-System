"""AI 自然語言搜尋（Phase 34）：LLM filters → 既有搜尋 API；失敗一律關鍵字 fallback。

流程（`POST /api/ai/search`）：
1. opt-in 檢查（未開啟 → 403 `ai_opt_in_required`）
2. 未設 key → 關鍵字 fallback（不扣配額）
3. 扣配額；耗盡 → 關鍵字 fallback
4. LLM 轉譯 → 白名單驗證（`ai_search_filters`）→ 名稱解析
5. 轉譯失敗／無任何條件 → 關鍵字 fallback（已扣次，計次於嘗試）
6. 以 `items_service.list_items` 執行（與 `/api/items` 同一條路徑）
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.repositories import (
    categories_repository,
    locations_repository,
    tags_repository,
)
from app.schemas.ai_search import (
    AppliedBucket,
    AppliedFilters,
    AskResponse,
    Citation,
    SearchResponse,
)
from app.services import (
    ai_quota,
    ai_service,
    ai_search_filters,
    classification_service,
    items_service,
    preferences_service,
)

logger = logging.getLogger(__name__)

#: 搜尋結果上限（家用量級；AI 搜尋不分頁）
SEARCH_LIMIT = 50


async def _catalog(session: AsyncSession, owner_id: UUID) -> ai_search_filters.Catalog:
    """本人可見的分類／位置／標籤目錄（供名稱解析與 prompt）。"""
    categories = await categories_repository.list_for_owner(session, owner_id)
    locations = await locations_repository.fetch_all(session, owner_id)
    tags = await tags_repository.list_for_owner(session, owner_id)

    location_paths = locations_repository.paths_for(locations, [loc.id for loc in locations])
    return ai_search_filters.Catalog(
        categories=[
            ai_search_filters.CatalogEntry(id=c.id, name=c.name)
            for c in categories
        ],
        locations=[
            ai_search_filters.CatalogEntry(
                id=loc.id, name=loc.name, path=location_paths.get(loc.id)
            )
            for loc in locations
        ],
        tags=[ai_search_filters.CatalogEntry(id=t.id, name=t.name) for t in tags],
    )


def _applied(
    filters: dict[str, Any], catalog: ai_search_filters.Catalog
) -> AppliedFilters:
    """把實際套用的 filters 轉成顯示用結構（含名稱與路徑）。"""
    categories = {entry.id: entry for entry in catalog.categories}
    locations = {entry.id: entry for entry in catalog.locations}
    tags = {entry.id: entry for entry in catalog.tags}

    def _bucket(entry) -> Optional[AppliedBucket]:
        if entry is None:
            return None
        return AppliedBucket(id=entry.id, name=entry.name, path=entry.path)

    return AppliedFilters(
        q=filters.get("q"),
        category=_bucket(categories.get(filters.get("category_id"))),
        location=_bucket(locations.get(filters.get("location_id"))),
        tags=[_bucket(tags[tag_id]) for tag_id in filters.get("tag_ids", []) if tag_id in tags],
        expiry=filters.get("expiry"),
        loan=filters.get("loan"),
        favorite=filters.get("favorite"),
        min_quantity=filters.get("min_quantity"),
        max_quantity=filters.get("max_quantity"),
        sort=filters.get("sort"),
    )


async def _run_search(
    session: AsyncSession, owner_id: UUID, filters: dict[str, Any]
):
    return await items_service.list_items(
        session,
        owner_id,
        q=filters.get("q"),
        category_id=filters.get("category_id"),
        location_id=filters.get("location_id"),
        location_scope="subtree",
        tag_ids=filters.get("tag_ids"),
        favorite=filters.get("favorite"),
        expiry=filters.get("expiry"),
        loan=filters.get("loan"),
        min_quantity=filters.get("min_quantity"),
        max_quantity=filters.get("max_quantity"),
        sort=filters.get("sort"),
        page=1,
        per_page=SEARCH_LIMIT,
    )


async def _fallback(
    session: AsyncSession,
    owner_id: UUID,
    query: str,
    catalog: ai_search_filters.Catalog,
    reason: str,
    unresolved: list[str] | None = None,
) -> SearchResponse:
    """關鍵字 fallback：以整句為 `q`（與現行搜尋一致），不報錯。"""
    filters = {"q": query}
    result = await _run_search(session, owner_id, filters)
    return SearchResponse(
        filters=filters,
        applied=_applied(filters, catalog),
        unresolved=unresolved or [],
        items=result.items,
        total=result.total,
        fallback_reason=reason,
    )


#: 問答上下文上限
ASK_CONTEXT_LIMIT = 20
#: 資料不足時的固定回答（伺服器提供，避免空字串）
INSUFFICIENT_ANSWER = "目前資料中找不到足夠資訊回答這個問題。"


async def _ask_context(
    session: AsyncSession,
    owner_id: UUID,
    question: str,
    item_ids: list[UUID],
) -> list[dict[str, Any]]:
    """組裝問答上下文（僅本人可見物品）；無 `item_ids` 時以問題做關鍵字搜尋。"""
    if item_ids:
        items = []
        for item_id in item_ids[:ASK_CONTEXT_LIMIT]:
            try:
                items.append(await items_service.get_item(session, owner_id, item_id))
            except HTTPException:
                # 不存在或非本人可見 → 丟棄（不洩漏存在性）
                continue
    else:
        # 無指定物品：以問題的關鍵詞（分詞取最長者，最多 3 個）逐一搜尋並去重；
        # 整句 ILIKE 幾乎不會命中，故不以整句查詢。
        tokens = sorted(
            classification_service.tokenize(question), key=len, reverse=True
        )[:3]
        if not tokens:
            tokens = [question]
        seen: set[str] = set()
        items = []
        for token in tokens:
            result = await _run_search(session, owner_id, {"q": token})
            for item in result.items:
                if str(item.id) in seen:
                    continue
                seen.add(str(item.id))
                items.append(item)
            if len(items) >= ASK_CONTEXT_LIMIT:
                break
        items = items[:ASK_CONTEXT_LIMIT]

    context: list[dict[str, Any]] = []
    for item in items:
        context.append(
            {
                "item_id": str(item.id),
                "name": item.name,
                "category": item.category.name if item.category else None,
                "location": item.location.path if item.location else None,
                "quantity": item.quantity,
                "soonest_expiry": (
                    item.soonest_expiry.isoformat() if item.soonest_expiry else None
                ),
                "tags": [tag.name for tag in item.tags],
            }
        )
    return context


def _citations_from_answer(
    answer: str, context: list[dict[str, Any]]
) -> list[Citation]:
    """`[#n]` → citations（1 起算；越界丟棄、去重保序）。"""
    citations: list[Citation] = []
    seen: set[str] = set()
    for match in re.finditer(r"\[#(\d+)\]", answer):
        index = int(match.group(1)) - 1
        if index < 0 or index >= len(context):
            continue
        entry = context[index]
        if entry["item_id"] in seen:
            continue
        seen.add(entry["item_id"])
        citations.append(
            Citation(
                item_id=UUID(entry["item_id"]),
                name=entry["name"],
                path=entry["location"],
            )
        )
    return citations


async def search(session: AsyncSession, owner_id: UUID, query: str) -> SearchResponse:
    prefs = await preferences_service.get_preferences(session, user_id=owner_id)
    if not prefs.ai_data_sharing_enabled:
        raise HTTPException(status_code=403, detail="ai_opt_in_required")

    catalog = await _catalog(session, owner_id)
    settings = get_settings()

    if not settings.gemini_api_key:
        return await _fallback(session, owner_id, query, catalog, "ai_disabled")

    if not await ai_quota.consume(session, owner_id):
        return await _fallback(session, owner_id, query, catalog, "quota_exhausted")

    try:
        payload = await ai_service.call_gemini_search_filters(query, catalog)
    except ai_service.AiUpstreamError as exc:
        logger.info("ai search translation failed: %s", exc)
        reason = "unparsed" if "JSON" in str(exc) or "empty" in str(exc) else "upstream_error"
        return await _fallback(session, owner_id, query, catalog, reason)

    parsed = ai_search_filters.filters_from_llm(payload, catalog)
    if parsed.is_empty:
        # 無任何可用條件 → 以整句關鍵字搜尋（避免全表掃描）
        return await _fallback(
            session, owner_id, query, catalog, "unparsed", parsed.unresolved
        )

    result = await _run_search(session, owner_id, parsed.filters)
    return SearchResponse(
        filters=parsed.filters,
        applied=_applied(parsed.filters, catalog),
        unresolved=parsed.unresolved,
        items=result.items,
        total=result.total,
        fallback_reason=None,
    )


async def ask(
    session: AsyncSession, owner_id: UUID, question: str, item_ids: list[UUID]
) -> AskResponse:
    """以本人可見物品摘要做 grounding 問答（Phase 34）。

    - 上下文：`item_ids`（≤20，僅可見者）或 `q=question` 前 20 筆
    - 上下文為空 → `grounded=false`（不呼叫 LLM、不扣配額）
    - 未 opt-in → 403；無 key → 503；配額 → 429；上游 → 502
    - 回答中的 `[#n]` 只映射到上下文內物品（越界丟棄、去重保序）
    """
    prefs = await preferences_service.get_preferences(session, user_id=owner_id)
    if not prefs.ai_data_sharing_enabled:
        raise HTTPException(status_code=403, detail="ai_opt_in_required")

    settings = get_settings()
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="ai_disabled")

    context = await _ask_context(session, owner_id, question, item_ids)
    if not context:
        return AskResponse(
            answer=INSUFFICIENT_ANSWER, citations=[], grounded=False
        )

    if not await ai_quota.consume(session, owner_id):
        raise HTTPException(status_code=429, detail="quota_exhausted")

    try:
        answer, grounded = await ai_service.call_gemini_ask(question, context)
    except ai_service.AiUpstreamError as exc:
        logger.warning("ai ask failed: %s", exc)
        raise HTTPException(status_code=502, detail="upstream_error") from exc

    if not grounded or not answer:
        return AskResponse(answer=INSUFFICIENT_ANSWER, citations=[], grounded=False)

    citations = _citations_from_answer(answer, context)
    return AskResponse(answer=answer, citations=citations, grounded=True)