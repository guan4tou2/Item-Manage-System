"""AI 搜尋：LLM filters → 受控查詢參數（Phase 34）。

**純函式、無 DB、無 LLM**——只接受白名單欄位，任何超範圍／型別錯／未知欄位
一律丟棄（計畫 D2）。名稱（分類／位置／標籤）以呼叫端提供的目錄解析：

- 分類：先比對完整路徑（`家庭 / 藥品`），再比對唯一同名；同名多筆 → 歧義，不猜
- 位置：同上（完整路徑或唯一葉名）
- 標籤：不分大小寫的唯一名稱

解析失敗 → 記入 `unresolved`（`category:名稱` 等），供前端顯示灰字 chip。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

#: 關鍵字上限（與前端輸入上限一致）
MAX_QUERY_LEN = 100
#: 標籤條件上限
MAX_TAGS = 5

_EXPIRY_VALUES = {"expired", "expiring_soon"}
_LOAN_VALUES = {"borrowed", "overdue"}
_SORT_VALUES = {"expiry_asc", "name_asc", "created_desc"}


@dataclass(frozen=True)
class CatalogEntry:
    """目錄項目：`path` 為完整路徑（分類／位置巢狀時提供，用於消歧義）。"""

    id: int
    name: str
    path: Optional[str] = None


@dataclass(frozen=True)
class Catalog:
    """呼叫端提供的本人目錄（僅本人可見項目）。"""

    categories: list[CatalogEntry] = field(default_factory=list)
    locations: list[CatalogEntry] = field(default_factory=list)
    tags: list[CatalogEntry] = field(default_factory=list)


@dataclass(frozen=True)
class ParsedFilters:
    """轉譯結果：`filters` 可直接餵給 `items_service.list_items`。"""

    filters: dict[str, Any]
    unresolved: list[str]

    @property
    def is_empty(self) -> bool:
        return not self.filters


def _clean_name(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _resolve(entries: list[CatalogEntry], raw: str) -> tuple[Optional[int], bool]:
    """名稱 → id。回傳 `(id, resolved)`；`resolved=False` 表示未找到或歧義。"""
    target = raw.strip()
    if not target:
        return None, False
    lowered = target.lower()

    # 1) 完整路徑精確匹配（可消歧義）
    for entry in entries:
        if entry.path and entry.path == target:
            return entry.id, True
    # 2) 名稱精確匹配；唯一才採用
    by_name = [
        entry
        for entry in entries
        if entry.name == target or entry.name.lower() == lowered
    ]
    if len(by_name) == 1:
        return by_name[0].id, True
    # 3) 葉名唯一（位置常以葉名被提及）
    if len(by_name) > 1:
        paths = {entry.path for entry in by_name}
        if len(paths) == 1 and None not in paths:
            return by_name[0].id, True
    return None, False


def _int_or_none(value: Any, *, minimum: int = 0) -> Optional[int]:
    """嚴格整數（bool 不算）；低於 `minimum` → None。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= minimum else None
    if isinstance(value, float) and value.is_integer():
        integer = int(value)
        return integer if integer >= minimum else None
    if isinstance(value, str) and value.strip().isdigit():
        integer = int(value.strip())
        return integer if integer >= minimum else None
    return None


def filters_from_llm(payload: Any, catalog: Catalog) -> ParsedFilters:
    """LLM 輸出 → `ParsedFilters`（白名單；永不拋錯）。"""
    if not isinstance(payload, dict):
        return ParsedFilters(filters={}, unresolved=[])

    filters: dict[str, Any] = {}
    unresolved: list[str] = []

    query = _clean_name(payload.get("q"))
    if query is not None:
        filters["q"] = query[:MAX_QUERY_LEN]

    category = _clean_name(payload.get("category"))
    if category is not None:
        category_id, ok = _resolve(catalog.categories, category)
        if ok and category_id is not None:
            filters["category_id"] = category_id
        else:
            unresolved.append(f"category:{category}")

    location = _clean_name(payload.get("location"))
    if location is not None:
        location_id, ok = _resolve(catalog.locations, location)
        if ok and location_id is not None:
            filters["location_id"] = location_id
        else:
            unresolved.append(f"location:{location}")

    raw_tags = payload.get("tags")
    if isinstance(raw_tags, list):
        tag_ids: list[int] = []
        for raw_tag in raw_tags[:MAX_TAGS]:
            tag = _clean_name(raw_tag)
            if tag is None:
                continue
            tag_id, ok = _resolve(catalog.tags, tag)
            if ok and tag_id is not None:
                if tag_id not in tag_ids:
                    tag_ids.append(tag_id)
            else:
                unresolved.append(f"tag:{tag}")
        if tag_ids:
            filters["tag_ids"] = tag_ids

    expiry = payload.get("expiry")
    if isinstance(expiry, str) and expiry in _EXPIRY_VALUES:
        filters["expiry"] = expiry

    loan = payload.get("loan")
    if isinstance(loan, str) and loan in _LOAN_VALUES:
        filters["loan"] = loan

    favorite = payload.get("favorite")
    if isinstance(favorite, bool):
        filters["favorite"] = favorite

    minimum = _int_or_none(payload.get("min_quantity"))
    maximum = _int_or_none(payload.get("max_quantity"))
    if minimum is not None and maximum is not None and minimum > maximum:
        minimum = None
        maximum = None
    if minimum is not None:
        filters["min_quantity"] = minimum
    if maximum is not None:
        filters["max_quantity"] = maximum

    sort = payload.get("sort")
    if isinstance(sort, str) and sort in _SORT_VALUES:
        filters["sort"] = sort

    return ParsedFilters(filters=filters, unresolved=unresolved)
