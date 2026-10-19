"""智慧分類建議（Phase 32）：以**本人歷史資料**生成「名稱關鍵詞 → 分類／位置／標籤」規則。

純規則式（不呼叫 LLM），因此 LLM 不可用／配額耗盡時仍可運作。
- 分詞：NFKC ＋ lower；拉丁／數字連續片段（長度 ≥ 2）、CJK bigram（單字元 CJK 保留）
- 評分：與歷史物品名稱的 token 交集大小；分類／位置／標籤以 `(score, item_count)` 聚合
- 排序：`score` desc → `item_count` desc → `id`／`name` asc（完全決定性）
- 隱私：僅查詢 `owner_id` 本人的未刪除物品
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.item import Item
from app.models.location import Location
from app.models.tag import Tag, item_tags

#: 掃描護欄：家用量級遠低於此；超過仍為決定性（依建立時間取前 N 筆）
MAX_SCAN = 2000
#: 標籤建議上限
TOP_TAGS = 3

_CJK_RANGES = "\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
_LATIN_RE = re.compile(r"[a-z0-9]+")
_CJK_RE = re.compile(f"[{_CJK_RANGES}]+")


@dataclass(frozen=True)
class BucketSuggestion:
    id: int
    name: str
    item_count: int
    score: int


@dataclass(frozen=True)
class TagSuggestion:
    name: str
    item_count: int
    score: int


@dataclass(frozen=True)
class ClassificationSuggestions:
    category: Optional[BucketSuggestion]
    location: Optional[BucketSuggestion]
    tags: list[TagSuggestion]


def tokenize(name: str) -> set[str]:
    """名稱 → token 集合（決定性；純函式）。"""
    normalized = unicodedata.normalize("NFKC", name or "").lower()
    tokens: set[str] = set()
    for run in _LATIN_RE.findall(normalized):
        if len(run) >= 2:
            tokens.add(run)
    for run in _CJK_RE.findall(normalized):
        if len(run) == 1:
            tokens.add(run)
        else:
            tokens.update(run[i : i + 2] for i in range(len(run) - 1))
    return tokens


def _accumulate(scores: dict, key, overlap: int) -> None:
    entry = scores.setdefault(key, [0, 0])
    entry[0] += overlap
    entry[1] += 1


def to_payload(suggestions: ClassificationSuggestions) -> dict[str, Any]:
    """`ClassificationSuggestions` → payload／回應的 dict 形狀（`HistorySuggestions`）。"""

    def bucket(item: Optional[Any]) -> Optional[dict[str, Any]]:
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


async def _bucket(
    session: AsyncSession,
    model,
    scores: dict[int, list[int]],
    names: Optional[dict[int, str]] = None,
) -> Optional[BucketSuggestion]:
    """分數聚合 → top1 建議；`names` 可帶入已載入的名稱表（批次化避免重查）。"""
    if not scores:
        return None
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1][0], -kv[1][1], kv[0]))
    if names is None:
        rows = (
            await session.execute(
                select(model.id, model.name).where(
                    model.id.in_([key for key, _ in ranked])
                )
            )
        ).all()
        names = dict(rows)
    for bucket_id, (score, count) in ranked:
        name = names.get(bucket_id)
        if name is not None:
            return BucketSuggestion(
                id=bucket_id, name=name, item_count=count, score=score
            )
    return None


async def suggest_for_names(
    session: AsyncSession, owner_id: UUID, names: list[str]
) -> list[ClassificationSuggestions]:
    """批次建議（Phase 33 收據品項）：**單次**掃描歷史，逐一比對名稱。

    與逐次呼叫 `suggest_for_name` 結果完全相同（含排序與分數）；僅節省查詢次數
    （收據一次最多 50 品項）。空名稱／無 token 者回空建議，順序與輸入一致。
    """
    if not names:
        return []

    token_sets = [tokenize(name) for name in names]
    empty = ClassificationSuggestions(category=None, location=None, tags=[])
    if not any(token_sets):
        return [empty for _ in names]

    rows = (
        await session.execute(
            select(Item.id, Item.name, Item.category_id, Item.location_id)
            .where(Item.owner_id == owner_id, Item.is_deleted.is_(False))
            .order_by(Item.created_at, Item.id)
            .limit(MAX_SCAN)
        )
    ).all()
    # 歷史名稱 token 只算一次（多個品項共用）
    item_tokens = [
        (item_id, tokenize(item_name), category_id, location_id)
        for item_id, item_name, category_id, location_id in rows
    ]

    results: list[ClassificationSuggestions] = []
    for tokens in token_sets:
        if not tokens:
            results.append(empty)
            continue

        category_scores: dict[int, list[int]] = {}
        location_scores: dict[int, list[int]] = {}
        tag_scores: dict[str, list[int]] = {}
        overlaps: dict[UUID, int] = {}
        for item_id, hist_tokens, category_id, location_id in item_tokens:
            overlap = len(tokens & hist_tokens)
            if overlap == 0:
                continue
            overlaps[item_id] = overlap
            if category_id is not None:
                _accumulate(category_scores, category_id, overlap)
            if location_id is not None:
                _accumulate(location_scores, location_id, overlap)

        if overlaps:
            tag_rows = (
                await session.execute(
                    select(item_tags.c.item_id, Tag.name)
                    .join(Tag, Tag.id == item_tags.c.tag_id)
                    .where(
                        item_tags.c.item_id.in_(list(overlaps)),
                        Tag.owner_id == owner_id,
                    )
                )
            ).all()
            for item_id, tag_name in tag_rows:
                _accumulate(tag_scores, tag_name, overlaps[item_id])

        ranked_tags = sorted(
            tag_scores.items(), key=lambda kv: (-kv[1][0], -kv[1][1], kv[0])
        )[:TOP_TAGS]
        results.append(
            ClassificationSuggestions(
                category=await _bucket(session, Category, category_scores),
                location=await _bucket(session, Location, location_scores),
                tags=[
                    TagSuggestion(name=tag_name, item_count=count, score=score)
                    for tag_name, (score, count) in ranked_tags
                ],
            )
        )
    return results


async def suggest_for_name(
    session: AsyncSession, owner_id: UUID, name: str
) -> ClassificationSuggestions:
    """以 `name` 為關鍵詞，回傳本人歷史中的分類／位置／標籤建議。"""
    return (await suggest_for_names(session, owner_id, [name]))[0]
