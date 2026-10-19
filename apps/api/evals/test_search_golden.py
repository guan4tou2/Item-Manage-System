"""Phase 34 T1.8：NL 搜尋 golden eval（≥20 句）。

預設 **mock 模式**（進 CI、不需 key、不連外網）：
    以 `search_golden.jsonl` 內記錄的 LLM 輸出跑「白名單轉譯 → 期望比對」，
    驗證轉譯層與注入防護；LLM 品質本身不在 CI 驗證範圍。

手動模式（`EVAL_LIVE=1` 且設 `GEMINI_API_KEY`）：
    實際呼叫 Gemini 計分（完全符合率），未設 key 時自動 skip。

執行：
    cd apps/api && uv run pytest evals/ -q          # mock
    EVAL_LIVE=1 uv run pytest evals/ -q -s          # 實際呼叫並印出分數
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.services.ai_search_filters import Catalog, CatalogEntry, filters_from_llm

GOLDEN_PATH = Path(__file__).with_name("search_golden.jsonl")


def _catalog() -> Catalog:
    """與 `search_golden.jsonl` 期望值對應的固定目錄。"""
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


def _load_cases() -> list[dict]:
    return [
        json.loads(line)
        for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


CASES = _load_cases()


def test_golden_dataset_has_at_least_20_cases():
    assert len(CASES) >= 20
    assert len({case["id"] for case in CASES}) == len(CASES)


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_mock_translation_matches_expected(case: dict):
    """mock 模式：轉譯層對已知 LLM 輸出的處理必須與期望一致。"""
    parsed = filters_from_llm(case["llm"], _catalog())

    expected = case.get("expected", {})
    assert parsed.filters == expected, f"{case['id']}: {case['query']}"
    assert parsed.unresolved == case.get("expected_unresolved", [])


@pytest.mark.parametrize(
    "case", [case for case in CASES if case["id"].startswith("inj-")],
    ids=[case["id"] for case in CASES if case["id"].startswith("inj-")],
)
def test_injection_cases_drop_unknown_fields(case: dict):
    """注入樣本：LLM 輸出中的非白名單欄位一律不得進入 filters。"""
    parsed = filters_from_llm(case["llm"], _catalog())

    allowed = {
        "q",
        "category_id",
        "location_id",
        "tag_ids",
        "expiry",
        "loan",
        "favorite",
        "min_quantity",
        "max_quantity",
        "sort",
    }
    assert set(parsed.filters) <= allowed
    for leaked in ("owner_id", "sql", "ids", "page"):
        assert leaked not in parsed.filters


@pytest.mark.skipif(
    os.environ.get("EVAL_LIVE") != "1" or not os.environ.get("GEMINI_API_KEY"),
    reason="EVAL_LIVE=1 且設定 GEMINI_API_KEY 時才實際呼叫 Gemini",
)
def test_live_translation_accuracy(capsys):
    """手動模式：實際呼叫 Gemini，印出完全符合率（僅供人工檢視）。"""
    import asyncio

    from app.services import ai_service

    async def _run() -> tuple[int, int]:
        catalog = _catalog()
        matched = 0
        for case in CASES:
            payload = await ai_service.call_gemini_search_filters(case["query"], catalog)
            parsed = filters_from_llm(payload, catalog)
            expected = case.get("expected", {})
            if parsed.filters == expected:
                matched += 1
            else:
                print(f"MISS {case['id']}: {case['query']}")
                print(f"  expected={expected}")
                print(f"  got     ={parsed.filters}")
        return matched, len(CASES)

    matched, total = asyncio.run(_run())
    with capsys.disabled():
        print(f"\nLIVE golden eval: {matched}/{total} ({matched / total:.0%})")
    assert matched / total >= 0.7, "live 完全符合率低於 70%"
