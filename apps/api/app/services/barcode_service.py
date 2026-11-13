"""條碼服務：canonicalize／分類／外部 provider／快取／分類建議。

- `canonicalize`：寫入正規化的唯一入口（表單／CSV／API 皆套用）。
- `classify`：分派 provider——ISBN（978/979／ISBN-10）→ Open Library；
  EAN-8/13、UPC-A → Open Food Facts；其餘（含 checksum 無效）→ other。
- 快取：`barcode_lookups` 正（payload）負（payload=None）結果皆存，
  TTL 30 天；`unavailable`（逾時/網路/非 JSON/5xx）不寫快取。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Optional, Protocol
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.barcode_lookup import BarcodeLookup
from app.models.category import Category

CACHE_TTL_DAYS = 30
EXTERNAL_TIMEOUT_SECONDS = 3.0

OFF_URL = "https://world.openfoodfacts.org/api/v2/product/{code}.json"
OFF_FIELDS = "product_name,brands,categories,quantity,image_front_small_url"
OL_URL = "https://openlibrary.org/api/books"

_DIGITS_RE = re.compile(r"^\d{8,14}$")
_ISBN10_RE = re.compile(r"^\d{9}[\dXx]$")

STATUS_OK = "ok"
STATUS_NOT_FOUND = "not_found"
STATUS_UNAVAILABLE = "unavailable"
STATUS_UNSUPPORTED = "unsupported"


def canonicalize(raw: Optional[str]) -> str:
    """去空白／連字號／底線；數字（8–14 位）或 ISBN-10 收斂為 canonical。

    其餘（Code128 等英數 SKU）保留 trim 原樣，避免破壞使用者輸入。
    """
    if not raw:
        return ""
    trimmed = raw.strip()
    cleaned = re.sub(r"[\s\-_]+", "", trimmed)
    if _DIGITS_RE.match(cleaned) or _ISBN10_RE.match(cleaned):
        return cleaned.upper()
    return trimmed


def _ean_checksum_ok(digits: str) -> bool:
    """EAN-8／EAN-13／UPC-A 共同檢查碼演算法。"""
    if not digits.isdigit():
        return False
    body, check = digits[:-1], int(digits[-1])
    total = sum(
        int(ch) * (3 if i % 2 == 0 else 1) for i, ch in enumerate(reversed(body))
    )
    return (10 - total % 10) % 10 == check


def _isbn10_checksum_ok(code: str) -> bool:
    if len(code) != 10:
        return False
    total = 0
    for i, ch in enumerate(code):
        weight = 10 - i
        if ch == "X":
            if i != 9:
                return False
            value = 10
        elif ch.isdigit():
            value = int(ch)
        else:
            return False
        total += value * weight
    return total % 11 == 0


def classify(code: str) -> str:
    """回傳 `isbn`／`ean`／`other`（provider 分派種類）。"""
    if _isbn10_checksum_ok(code):
        return "isbn"
    if (
        len(code) == 13
        and code.isdigit()
        and code[:3] in ("978", "979")
        and _ean_checksum_ok(code)
    ):
        return "isbn"
    if len(code) in (8, 12, 13) and code.isdigit() and _ean_checksum_ok(code):
        return "ean"
    return "other"


@dataclass
class ExternalResult:
    source: str
    name: str
    description: str
    image_url: Optional[str] = None
    categories_text: str = ""


class BarcodeProvider(Protocol):
    name: str

    async def fetch(
        self, http: httpx.AsyncClient, code: str
    ) -> Optional[ExternalResult]: ...


class OpenFoodFactsProvider:
    name = "openfoodfacts"

    async def fetch(
        self, http: httpx.AsyncClient, code: str
    ) -> Optional[ExternalResult]:
        resp = await http.get(OFF_URL.format(code=code), params={"fields": OFF_FIELDS})
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != 1:
            return None
        product = data.get("product") or {}
        name = str(product.get("product_name") or "").strip()
        if not name:
            return None
        parts = [
            str(product.get("brands") or "").strip(),
            str(product.get("categories") or "").strip(),
            str(product.get("quantity") or "").strip(),
        ]
        description = "，".join(part for part in parts if part)
        image = str(product.get("image_front_small_url") or "").strip() or None
        return ExternalResult(
            source=self.name,
            name=name,
            description=description,
            image_url=image,
            categories_text=str(product.get("categories") or "").strip(),
        )


class OpenLibraryProvider:
    name = "openlibrary"

    async def fetch(
        self, http: httpx.AsyncClient, code: str
    ) -> Optional[ExternalResult]:
        resp = await http.get(
            OL_URL,
            params={"bibkeys": f"ISBN:{code}", "format": "json", "jscmd": "data"},
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        book = data.get(f"ISBN:{code}")
        if not book:
            return None
        title = str(book.get("title") or "").strip()
        if not title:
            return None

        authors = "、".join(
            str(a.get("name") or "").strip()
            for a in book.get("authors") or []
            if a.get("name")
        )
        publishers = "、".join(
            str(p.get("name") or "").strip()
            for p in book.get("publishers") or []
            if isinstance(p, dict) and p.get("name")
        )
        parts: list[str] = []
        if authors:
            parts.append(f"作者：{authors}")
        if book.get("publish_date"):
            parts.append(f"出版：{book['publish_date']}")
        if publishers:
            parts.append(f"出版社：{publishers}")

        cover = book.get("cover") or {}
        image = str(cover.get("medium") or cover.get("small") or "").strip() or None

        subjects = "，".join(
            str(s.get("name") or "").strip()
            for s in book.get("subjects") or []
            if isinstance(s, dict) and s.get("name")
        )
        return ExternalResult(
            source=self.name,
            name=title,
            description="；".join(parts),
            image_url=image,
            categories_text=subjects,
        )


PROVIDERS: dict[str, BarcodeProvider] = {
    "openfoodfacts": OpenFoodFactsProvider(),
    "openlibrary": OpenLibraryProvider(),
}

KIND_PROVIDER = {"isbn": "openlibrary", "ean": "openfoodfacts"}


def provider_for(code: str) -> Optional[BarcodeProvider]:
    name = KIND_PROVIDER.get(classify(code))
    return PROVIDERS.get(name) if name else None


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=EXTERNAL_TIMEOUT_SECONDS)


@dataclass
class ExternalLookup:
    external: Optional[dict[str, Any]]
    status: str
    cached: bool
    categories_text: str = ""
    source: str = ""


async def _get_row(session: AsyncSession, code: str) -> Optional[BarcodeLookup]:
    return (
        await session.execute(
            select(BarcodeLookup).where(BarcodeLookup.code == code)
        )
    ).scalar_one_or_none()


def _fetched_at(row: BarcodeLookup) -> datetime:
    value = row.fetched_at
    if value.tzinfo is None:  # SQLite 回 naive
        value = value.replace(tzinfo=UTC)
    return value


def _from_row(row: BarcodeLookup) -> ExternalLookup:
    payload = row.payload
    return ExternalLookup(
        external=payload,
        status=STATUS_OK if payload else STATUS_NOT_FOUND,
        cached=True,
        categories_text=(payload or {}).get("categories_text", ""),
        source=row.source,
    )


async def _store_cache(
    session: AsyncSession,
    *,
    code: str,
    source: str,
    payload: Optional[dict[str, Any]],
    fetched_at: datetime,
) -> None:
    row = await _get_row(session, code)
    if row is None:
        try:
            async with session.begin_nested():
                session.add(
                    BarcodeLookup(
                        code=code, source=source, payload=payload, fetched_at=fetched_at
                    )
                )
        except IntegrityError:
            # 並發：另一請求已寫入 → 改 UPDATE
            row = await _get_row(session, code)
    if row is not None:
        row.source = source
        row.payload = payload
        row.fetched_at = fetched_at
    await session.commit()


async def lookup_external(session: AsyncSession, code: str) -> ExternalLookup:
    """外查（含快取）：unsupported｜ok｜not_found｜unavailable；fail-soft 不拋錯。"""
    provider = provider_for(code)
    if provider is None:
        return ExternalLookup(external=None, status=STATUS_UNSUPPORTED, cached=False)

    row = await _get_row(session, code)
    now = datetime.now(UTC)
    if row is not None and now - _fetched_at(row) < timedelta(days=CACHE_TTL_DAYS):
        return _from_row(row)

    try:
        async with _client() as http:
            result = await provider.fetch(http, code)
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return ExternalLookup(
            external=None, status=STATUS_UNAVAILABLE, cached=False, source=provider.name
        )

    payload: Optional[dict[str, Any]] = None
    if result is not None:
        payload = {
            "name": result.name,
            "description": result.description,
            "image_url": result.image_url,
            "categories_text": result.categories_text,
        }
    await _store_cache(
        session, code=code, source=provider.name, payload=payload, fetched_at=now
    )
    return ExternalLookup(
        external=payload,
        status=STATUS_OK if payload else STATUS_NOT_FOUND,
        cached=False,
        categories_text=result.categories_text if result else "",
        source=provider.name,
    )


async def suggest_category_id(
    session: AsyncSession, owner_id: UUID, categories_text: str
) -> Optional[int]:
    """外部分類字串與使用者葉分類名稱字面比對；唯一命中才建議。"""
    if not categories_text:
        return None
    rows = (
        await session.execute(
            select(Category.id, Category.name, Category.parent_id).where(
                Category.owner_id == owner_id
            )
        )
    ).all()
    parent_ids = {row.parent_id for row in rows if row.parent_id is not None}
    haystack = categories_text.casefold()
    matches = [
        row.id
        for row in rows
        if row.id not in parent_ids
        and len(row.name) >= 2
        and row.name.casefold() in haystack
    ]
    if len(matches) == 1:
        return matches[0]
    return None
