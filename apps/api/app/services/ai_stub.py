"""Phase 35 T1.2：AI stub 供應器（確定性輸出）。

設計要點（計畫 D2／D3／D4／D5）：

- **回傳原始 JSON 文字**（不是已解析物件）→ live 的解析／白名單／名稱解析／
  引用映射路徑在 stub 模式**完全相同**被執行。
- **完全決定性**：同輸入必得同輸出（無隨機、無時鐘依賴）。
- 搜尋轉譯為**規則式**：目錄名稱比對 → 關鍵詞規則 → 殘留關鍵字。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Optional

from app.services.ai_search_filters import Catalog, CatalogEntry

#: 搜尋關鍵字上限（與 `ai_search_filters.MAX_QUERY_LEN` 一致）
MAX_QUERY_LEN = 100
#: 標籤條件上限（與 `ai_search_filters.MAX_TAGS` 一致）
MAX_TAGS = 5
#: 問答答案字數上限（與 live `parse_ask_response` 一致）
MAX_ANSWER_LEN = 1000


# --- 建議（圖片 → 物品欄位） ---------------------------------------------

#: stub 建議（固定值；e2e 與文件以之作為斷言依據）
STUB_SUGGEST: dict[str, Any] = {
    "name": "測試物品",
    "description": "AI stub 模式產生的測試描述",
    "category_suggestion": "測試分類",
    "tag_suggestions": ["測試標籤"],
}


def suggest_text() -> str:
    """圖片建議的 stub 回應（原始 JSON 文字）。"""
    return json.dumps(STUB_SUGGEST, ensure_ascii=False)


# --- 收據（頁面 → 品項） -----------------------------------------------

#: stub 收據（固定值；`total` == 品項小計合計 → 對帳相符）
STUB_RECEIPT: dict[str, Any] = {
    "merchant": "測試商店",
    "purchased_at": "2026-01-01",
    "currency": "TWD",
    "total": "150.00",
    "items": [
        {
            "name": "測試品項甲",
            "quantity": 2,
            "unit_price": "50.00",
            "subtotal": "100.00",
        },
        {
            "name": "測試品項乙",
            "quantity": 1,
            "unit_price": "50.00",
            "subtotal": "50.00",
        },
    ],
}


def receipt_text() -> str:
    """收據抽取的 stub 回應（原始 JSON 文字）。"""
    return json.dumps(STUB_RECEIPT, ensure_ascii=False)


# --- 問答（問題＋物品摘要 → 回答） ---------------------------------------

def ask_text(question: str, context: list[dict[str, Any]]) -> str:
    """問答的 stub 回應（原始 JSON 文字）。

    只以上下文為依據，產生可被既有 `_citations_from_answer` 映射的 `[#n]` 引用。
    """
    items = list(context)[:10]
    if not items:
        payload = {"answer": "INSUFFICIENT_DATA", "grounded": False}
        return json.dumps(payload, ensure_ascii=False)

    described = "、".join(
        f"{entry.get('name') or '未命名物品'} [#{index}]"
        for index, entry in enumerate(items, start=1)
    )
    answer = f"依系統資料，共找到 {len(items)} 筆相關物品：{described}。"
    payload = {"answer": answer[:MAX_ANSWER_LEN], "grounded": True}
    return json.dumps(payload, ensure_ascii=False)


# --- 搜尋（自然語言 → filters） ------------------------------------------


@dataclass(frozen=True)
class _Candidate:
    """目錄命中候選（以字串出現位置判定）。"""

    kind: str  # category | location | tag
    name: str
    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start


@dataclass(frozen=True)
class _Match:
    """已選定的目錄命中。"""

    kind: str
    name: str
    start: int
    end: int


#: 關鍵詞規則（有序；同一欄位先命中者勝出）
_EXPIRY_SOON_PATTERNS = ("快過期", "即將過期", "快到期", "即將到期", "最近到期", "7天內", "七天內")
_EXPIRED_PATTERNS = ("已過期", "已經過期", "過期了")
_LOAN_OVERDUE_PATTERNS = ("逾期", "超期未還", "過期未還")
_LOAN_BORROWED_PATTERNS = ("借出", "借著", "借給", "外借", "借還沒還")
_FAVORITE_PATTERNS = ("最愛", "收藏")
_MIN_QUANTITY_RE = re.compile(r"(?:數量)?至少\s*(\d+)")
_MAX_QUANTITY_RE = re.compile(r"(?:數量)?(?:最多|不超過)\s*(\d+)")
_SORT_EXPIRY_PATTERNS = ("最快到期", "依到期", "先到期")
_SORT_CREATED_PATTERNS = ("最新建立", "最近建立", "最近新增", "最新的")
_SORT_NAME_PATTERNS = ("按名稱", "依名稱", "名稱排序", "名字排序")

#: 殘留關鍵字的頭尾虛詞（只修剪兩端，不刪中間，避免破壞詞彙）
_LEADING_PARTICLES = ("幫我", "想要", "我要", "我想", "看看", "查一下", "找一下", "我的", "我", "請", "找", "查", "幫")
_TRAILING_PARTICLES = ("的", "裡", "裏", "中", "有", "呢", "嗎", "啊", "了", "看", "在", "內", "上", "下", "去", "回")
#: 中間屬格助詞：取「的」之後的尾部當關鍵字
_POSSESSIVE = "的"
#: 需移除的標點
_PUNCTUATION = "、，。！？?!.,；;：:（）()「」《》【】…～~ "


def _catalog_candidates(query: str, catalog: Catalog) -> list[_Candidate]:
    """在查詢字串中找出目錄名稱／位置路徑的命中（全部候選）。"""
    candidates: list[_Candidate] = []
    groups: list[tuple[str, list[CatalogEntry]]] = [
        ("category", list(catalog.categories)),
        ("location", list(catalog.locations)),
        ("tag", list(catalog.tags)),
    ]
    for kind, entries in groups:
        for entry in entries:
            # 位置可用完整路徑比對（較長、較具體）
            names = [entry.name]
            if kind == "location" and entry.path:
                names.append(entry.path)
            for name in names:
                if not name:
                    continue
                index = query.find(name)
                while index != -1:
                    candidates.append(
                        _Candidate(kind, name, index, index + len(name))
                    )
                    index = query.find(name, index + 1)
    return candidates


def _select_matches(query: str, catalog: Catalog) -> list[_Match]:
    """選出互不重疊的目錄命中（分類／位置各一；標籤多個）。

    重疊者只保留**最長**者（例如分類「廚房用品」與位置「廚房」同時命中時，
    只留「廚房用品」，避免互相矛盾的條件）。
    """
    candidates = sorted(
        _catalog_candidates(query, catalog), key=lambda c: (-c.length, c.start)
    )
    selected: list[_Match] = []
    for candidate in candidates:
        overlaps = any(
            candidate.start < match.end and match.start < candidate.end
            for match in selected
        )
        if overlaps:
            continue
        if candidate.kind in ("category", "location"):
            if any(match.kind == candidate.kind for match in selected):
                continue
        elif candidate.kind == "tag":
            if len([m for m in selected if m.kind == "tag"]) >= MAX_TAGS:
                continue
        selected.append(
            _Match(candidate.kind, candidate.name, candidate.start, candidate.end)
        )
    return selected


def _find_pattern(query: str, patterns: tuple[str, ...]) -> Optional[str]:
    """回傳第一個命中的關鍵詞（找不到 → None）。"""
    for pattern in patterns:
        if pattern in query:
            return pattern
    return None


def _strip_matched(
    query: str, matches: list[_Match], patterns: list[str]
) -> str:
    """移除已命中的目錄名稱與關鍵詞，留下殘留文字。"""
    spans = sorted(
        [(m.start, m.end) for m in matches], key=lambda span: (-span[1] + span[0])
    )
    # 由長到短移除（避免先移除短片段破壞長片段的邊界）
    for start, end in sorted(spans, key=lambda span: -(span[1] - span[0])):
        query = query[:start] + query[end:]
    for pattern in sorted(patterns, key=len, reverse=True):
        if pattern:
            query = query.replace(pattern, "")
    return query


def _trim_particles(text: str) -> str:
    """修剪殘留文字兩端的虛詞。"""
    changed = True
    while changed and text:
        changed = False
        for particle in _LEADING_PARTICLES:
            if text.startswith(particle):
                text = text[len(particle) :]
                changed = True
                break
        for particle in _TRAILING_PARTICLES:
            if text.endswith(particle):
                text = text[: -len(particle)]
                changed = True
                break
    return text


def translate_search(query: str, catalog: Catalog) -> dict[str, Any]:
    """自然語言 → stub filters（**僅白名單欄位**；與 live 輸出同構）。"""
    text = (query or "").strip()
    payload: dict[str, Any] = {}
    if not text:
        return payload

    matches = _select_matches(text, catalog)
    used_patterns: list[str] = []

    category = next((m for m in matches if m.kind == "category"), None)
    if category is not None:
        payload["category"] = category.name

    location = next((m for m in matches if m.kind == "location"), None)
    if location is not None:
        payload["location"] = location.name

    tags = [m.name for m in matches if m.kind == "tag"]
    if tags:
        payload["tags"] = tags[:MAX_TAGS]

    expiry_soon = _find_pattern(text, _EXPIRY_SOON_PATTERNS)
    expired = _find_pattern(text, _EXPIRED_PATTERNS)
    if expiry_soon is not None:
        payload["expiry"] = "expiring_soon"
        used_patterns.append(expiry_soon)
    elif expired is not None:
        payload["expiry"] = "expired"
        used_patterns.append(expired)

    overdue = _find_pattern(text, _LOAN_OVERDUE_PATTERNS)
    borrowed = _find_pattern(text, _LOAN_BORROWED_PATTERNS)
    if overdue is not None:
        payload["loan"] = "overdue"
        used_patterns.append(overdue)
    elif borrowed is not None:
        payload["loan"] = "borrowed"
        used_patterns.append(borrowed)

    favorite = _find_pattern(text, _FAVORITE_PATTERNS)
    if favorite is not None:
        payload["favorite"] = True
        used_patterns.append(favorite)

    min_match = _MIN_QUANTITY_RE.search(text)
    if min_match is not None:
        payload["min_quantity"] = int(min_match.group(1))
        used_patterns.append(min_match.group(0))
    max_match = _MAX_QUANTITY_RE.search(text)
    if max_match is not None:
        payload["max_quantity"] = int(max_match.group(1))
        used_patterns.append(max_match.group(0))

    sort_expiry = _find_pattern(text, _SORT_EXPIRY_PATTERNS)
    sort_created = _find_pattern(text, _SORT_CREATED_PATTERNS)
    sort_name = _find_pattern(text, _SORT_NAME_PATTERNS)
    if sort_expiry is not None:
        payload["sort"] = "expiry_asc"
        used_patterns.append(sort_expiry)
    elif sort_created is not None:
        payload["sort"] = "created_desc"
        used_patterns.append(sort_created)
    elif sort_name is not None:
        payload["sort"] = "name_asc"
        used_patterns.append(sort_name)

    residual = _strip_matched(text, matches, used_patterns)
    residual = residual.translate(str.maketrans("", "", _PUNCTUATION))
    if _POSSESSIVE in residual:
        residual = residual.split(_POSSESSIVE, 1)[1]
    residual = _trim_particles(residual.strip())
    if residual:
        payload["q"] = residual[:MAX_QUERY_LEN]

    return payload


def search_filters_text(query: str, catalog: Catalog) -> str:
    """搜尋轉譯的 stub 回應（原始 JSON 文字）。"""
    payload = translate_search(query, catalog)
    return json.dumps(payload, ensure_ascii=False)
