"""Phase 35 T1.2：stub 供應器與規則轉譯器。

驗證重點：
- 輸出**原始 JSON 文字**（可被 live 的解析函式直接消費）
- 搜尋轉譯：目錄比對（最長匹配）、關鍵詞規則、殘留關鍵字、虛詞修剪
- 問答：含可映射的 `[#n]` 引用、長度上限
- 收據：`total` == 品項小計合計（對帳相符）
- **完全決定性**：同輸入必得同輸出
"""
from __future__ import annotations

import json

from app.services.ai_search_filters import Catalog, CatalogEntry
from app.services.ai_stub import (
    MAX_ANSWER_LEN,
    ask_text,
    receipt_text,
    search_filters_text,
    suggest_text,
    translate_search,
)


def _catalog() -> Catalog:
    return Catalog(
        categories=[
            CatalogEntry(id=3, name="食品"),
            CatalogEntry(id=4, name="日用品"),
            CatalogEntry(id=5, name="廚房用品"),
        ],
        locations=[
            CatalogEntry(id=7, name="廚房", path="1F / 廚房"),
            CatalogEntry(id=8, name="藥箱", path="1F / 廚房 / 藥箱"),
            CatalogEntry(id=9, name="冰箱", path="1F / 廚房 / 冰箱"),
        ],
        tags=[
            CatalogEntry(id=11, name="重要"),
            CatalogEntry(id=12, name="咖啡"),
        ],
    )


# --- 建議 ---------------------------------------------------------------


def test_suggest_text_is_valid_json_with_expected_fields():
    payload = json.loads(suggest_text())
    assert payload["name"] == "測試物品"
    assert isinstance(payload["tag_suggestions"], list)
    assert payload["category_suggestion"] == "測試分類"


# --- 收據 ---------------------------------------------------------------


def test_receipt_text_parses_and_totals_match():
    from app.services.ai_service import parse_receipt_response

    extraction = parse_receipt_response(receipt_text())
    assert extraction.merchant == "測試商店"
    assert extraction.currency == "TWD"
    assert len(extraction.items) == 2
    item_total = sum(item.subtotal for item in extraction.items)
    assert item_total == extraction.total


# --- 問答 ---------------------------------------------------------------


def test_ask_text_contains_mappable_citations():
    from app.services.ai_service import parse_ask_response

    context = [
        {"name": "感冒藥", "category": "藥品", "location": "1F / 藥箱", "quantity": 2},
        {"name": "鮮乳", "category": "食品", "location": "1F / 冰箱", "quantity": 1},
    ]
    answer, grounded = parse_ask_response(ask_text("有哪些東西？", context))
    assert grounded is True
    assert "[#1]" in answer
    assert "[#2]" in answer
    assert "感冒藥" in answer


def test_ask_text_without_context_is_insufficient():
    from app.services.ai_service import parse_ask_response

    answer, grounded = parse_ask_response(ask_text("有哪些東西？", []))
    assert grounded is False
    assert answer == ""


def test_ask_text_respects_answer_length_limit():
    context = [
        {"name": f"物品{i}", "category": None, "location": None, "quantity": 1}
        for i in range(10)
    ]
    payload = json.loads(ask_text("?", context))
    assert len(payload["answer"]) <= MAX_ANSWER_LEN


# --- 搜尋轉譯 -----------------------------------------------------------


def test_translate_matches_location_and_expiry_and_keyword():
    payload = translate_search("廚房裡快過期的感冒藥", _catalog())
    assert payload["location"] == "廚房"
    assert payload["expiry"] == "expiring_soon"
    assert payload["q"] == "感冒藥"


def test_translate_matches_category():
    payload = translate_search("廚房用品", _catalog())
    assert payload["category"] == "廚房用品"


def test_translate_prefers_longest_overlapping_match():
    """分類「廚房用品」與位置「廚房」重疊 → 只留較長者（避免矛盾條件）。"""
    payload = translate_search("廚房用品的藥", _catalog())
    assert payload.get("category") == "廚房用品"
    assert "location" not in payload


def test_translate_matches_tags():
    payload = translate_search("重要的咖啡", _catalog())
    assert set(payload["tags"]) == {"重要", "咖啡"}


def test_translate_loan_overdue_beats_borrowed():
    payload = translate_search("借出但已逾期的工具", _catalog())
    assert payload["loan"] == "overdue"


def test_translate_loan_borrowed():
    payload = translate_search("借出去的東西", _catalog())
    assert payload["loan"] == "borrowed"


def test_translate_favorite():
    payload = translate_search("我最愛的東西", _catalog())
    assert payload["favorite"] is True


def test_translate_quantity_bounds():
    payload = translate_search("數量至少 3 的瓶裝水", _catalog())
    assert payload["min_quantity"] == 3
    payload = translate_search("數量最多 2 的瓶裝水", _catalog())
    assert payload["max_quantity"] == 2


def test_translate_sort_rules():
    assert translate_search("最快到期的", _catalog())["sort"] == "expiry_asc"
    assert translate_search("最新建立的", _catalog())["sort"] == "created_desc"
    assert translate_search("依名稱排序", _catalog())["sort"] == "name_asc"


def test_translate_keeps_only_whitelisted_fields():
    allowed = {
        "q",
        "category",
        "location",
        "tags",
        "expiry",
        "loan",
        "favorite",
        "min_quantity",
        "max_quantity",
        "sort",
    }
    payload = translate_search("廚房裡快過期的感冒藥", _catalog())
    assert set(payload) <= allowed


def test_translate_empty_query_returns_empty():
    assert translate_search("   ", _catalog()) == {}


def test_translate_long_keyword_is_truncated():
    payload = translate_search("x" * 300, _catalog())
    assert len(payload["q"]) <= 100


def test_search_filters_text_is_valid_json():
    payload = json.loads(search_filters_text("廚房裡快過期的感冒藥", _catalog()))
    assert payload["location"] == "廚房"


def test_translate_is_deterministic():
    first = translate_search("廚房裡快過期的感冒藥", _catalog())
    second = translate_search("廚房裡快過期的感冒藥", _catalog())
    assert first == second
    assert search_filters_text("廚房裡快過期的感冒藥", _catalog()) == (
        search_filters_text("廚房裡快過期的感冒藥", _catalog())
    )
