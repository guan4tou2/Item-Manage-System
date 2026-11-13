from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import select

from app.auth.password import hash_password
from app.models.barcode_lookup import BarcodeLookup
from app.models.category import Category
from app.models.user import User
from app.services import barcode_service


def with_check(body: str) -> str:
    """依 EAN 規則補檢查碼（EAN-8／EAN-13／UPC-A 同演算法）。"""
    total = sum(
        int(ch) * (3 if i % 2 == 0 else 1) for i, ch in enumerate(reversed(body))
    )
    return f"{body}{(10 - total % 10) % 10}"


def ean13(body12: str) -> str:
    return with_check(body12)


def ean8(body7: str) -> str:
    return with_check(body7)


def upca(body11: str) -> str:
    return with_check(body11)


def mock_http(monkeypatch, handler):
    """以 MockTransport 攔截 httpx；回傳呼叫計數器。"""
    calls = {"n": 0}

    def wrapped(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return handler(request)

    def factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(wrapped), timeout=3.0)

    monkeypatch.setattr(barcode_service, "_client", factory)
    return calls


def off_hit(code: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "status": 1,
            "product": {
                "product_name": "鮮奶",
                "brands": "瑞穗",
                "categories": "乳製品, 飲料",
                "quantity": "936ml",
                "image_front_small_url": "https://img.example/milk.jpg",
            },
        },
    )


def ol_hit(code: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            f"ISBN:{code}": {
                "title": "Clean Code",
                "authors": [{"name": "Robert C. Martin"}],
                "publish_date": "2008",
                "publishers": [{"name": "Prentice Hall"}],
                "cover": {"medium": "https://covers.example/clean.jpg"},
                "subjects": [{"name": "Computer programming"}],
            }
        },
    )


# ---------- canonicalize ----------


def test_canonicalize_strips_formatting():
    assert barcode_service.canonicalize(" 4710085200016 ") == "4710085200016"
    assert barcode_service.canonicalize("978-0-306-40615-7") == "9780306406157"
    assert barcode_service.canonicalize("0-8044-2957-x") == "080442957X"
    assert barcode_service.canonicalize("  ") == ""


def test_canonicalize_keeps_alphanumeric_sku():
    assert barcode_service.canonicalize("ABC-123") == "ABC-123"
    assert barcode_service.canonicalize("SKU_99") == "SKU_99"


# ---------- classify ----------


def test_classify_isbn_codes():
    assert barcode_service.classify("0306406152") == "isbn"  # ISBN-10 有效
    assert barcode_service.classify("0306406153") == "other"  # 檢查碼壞
    assert barcode_service.classify("080442957X") == "isbn"  # X 檢查碼
    assert barcode_service.classify(ean13("978030640615")) == "isbn"
    assert barcode_service.classify(ean13("979109063607")) == "isbn"


def test_classify_ean_codes():
    assert barcode_service.classify(ean13("471008520001")) == "ean"
    assert barcode_service.classify(ean8("9638507")) == "ean"
    assert barcode_service.classify(upca("03600029145")) == "ean"


def test_classify_rejects_bad_checksum_and_other():
    assert barcode_service.classify("4710085200014") == "other"  # 檢查碼壞
    assert barcode_service.classify("12345678") == "other"
    assert barcode_service.classify("ABC123") == "other"
    assert barcode_service.classify("") == "other"


# ---------- provider（經 lookup_external 端到端） ----------


async def test_off_hit_maps_and_caches(db_session, monkeypatch):
    code = ean13("471008520001")
    calls = mock_http(monkeypatch, lambda req: off_hit(code))

    first = await barcode_service.lookup_external(db_session, code)
    assert first.status == "ok"
    assert first.cached is False
    assert first.external["name"] == "鮮奶"
    assert first.external["description"] == "瑞穗，乳製品, 飲料，936ml"
    assert first.external["image_url"] == "https://img.example/milk.jpg"
    assert first.categories_text == "乳製品, 飲料"
    assert calls["n"] == 1

    second = await barcode_service.lookup_external(db_session, code)
    assert second.status == "ok"
    assert second.cached is True
    assert second.external == first.external
    assert calls["n"] == 1  # 快取命中不打 API


async def test_off_status_zero_is_not_found_and_negative_cached(
    db_session, monkeypatch
):
    code = ean13("471008520002")
    calls = mock_http(monkeypatch, lambda req: httpx.Response(200, json={"status": 0}))

    first = await barcode_service.lookup_external(db_session, code)
    assert first.status == "not_found"
    assert first.external is None

    row = (
        await db_session.execute(
            select(BarcodeLookup).where(BarcodeLookup.code == code)
        )
    ).scalar_one()
    assert row.payload is None

    second = await barcode_service.lookup_external(db_session, code)
    assert second.status == "not_found"
    assert second.cached is True
    assert calls["n"] == 1


async def test_off_404_is_not_found(db_session, monkeypatch):
    code = ean13("471008520003")
    mock_http(monkeypatch, lambda req: httpx.Response(404))

    result = await barcode_service.lookup_external(db_session, code)
    assert result.status == "not_found"


async def test_off_non_json_is_unavailable_and_not_cached(db_session, monkeypatch):
    code = ean13("471008520004")
    calls = mock_http(
        monkeypatch,
        lambda req: httpx.Response(200, text="<html>oops</html>"),
    )

    first = await barcode_service.lookup_external(db_session, code)
    assert first.status == "unavailable"

    rows = (await db_session.execute(select(BarcodeLookup))).scalars().all()
    assert rows == []

    second = await barcode_service.lookup_external(db_session, code)
    assert second.status == "unavailable"
    assert calls["n"] == 2


async def test_off_timeout_is_unavailable(db_session, monkeypatch):
    code = ean13("471008520005")

    def handler(req):
        raise httpx.TimeoutException("timed out")

    mock_http(monkeypatch, handler)
    result = await barcode_service.lookup_external(db_session, code)
    assert result.status == "unavailable"


async def test_off_5xx_is_unavailable(db_session, monkeypatch):
    code = ean13("471008520006")
    mock_http(monkeypatch, lambda req: httpx.Response(503))

    result = await barcode_service.lookup_external(db_session, code)
    assert result.status == "unavailable"


async def test_off_missing_name_is_not_found(db_session, monkeypatch):
    code = ean13("471008520007")
    mock_http(
        monkeypatch,
        lambda req: httpx.Response(200, json={"status": 1, "product": {"brands": "X"}}),
    )

    result = await barcode_service.lookup_external(db_session, code)
    assert result.status == "not_found"


async def test_openlibrary_hit_maps(db_session, monkeypatch):
    code = ean13("978030640615")
    calls = mock_http(monkeypatch, lambda req: ol_hit(code))
    assert barcode_service.classify(code) == "isbn"

    result = await barcode_service.lookup_external(db_session, code)
    assert result.status == "ok"
    assert result.external["name"] == "Clean Code"
    assert result.external["description"] == "作者：Robert C. Martin；出版：2008；出版社：Prentice Hall"
    assert result.external["image_url"] == "https://covers.example/clean.jpg"
    assert result.categories_text == "Computer programming"
    assert calls["n"] == 1
    # 請求打到 openlibrary
    assert "openlibrary" in barcode_service.PROVIDERS["openlibrary"].name


async def test_openlibrary_empty_object_is_not_found(db_session, monkeypatch):
    code = ean13("978030640616")
    mock_http(monkeypatch, lambda req: httpx.Response(200, json={}))

    result = await barcode_service.lookup_external(db_session, code)
    assert result.status == "not_found"


async def test_openlibrary_isbn10_hit(db_session, monkeypatch):
    calls = mock_http(monkeypatch, lambda req: ol_hit("0306406152"))

    result = await barcode_service.lookup_external(db_session, "0306406152")
    assert result.status == "ok"
    assert result.external["name"] == "Clean Code"
    assert calls["n"] == 1


# ---------- 快取 TTL ----------


async def test_cache_ttl_expiry_refetches(db_session, monkeypatch):
    code = ean13("471008520008")
    calls = mock_http(monkeypatch, lambda req: off_hit(code))

    await barcode_service.lookup_external(db_session, code)
    assert calls["n"] == 1

    row = (
        await db_session.execute(
            select(BarcodeLookup).where(BarcodeLookup.code == code)
        )
    ).scalar_one()
    row.fetched_at = datetime.now(UTC) - timedelta(days=31)
    await db_session.commit()

    again = await barcode_service.lookup_external(db_session, code)
    assert calls["n"] == 2
    assert again.cached is False

    await db_session.refresh(row)
    fetched = row.fetched_at
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=UTC)
    assert datetime.now(UTC) - fetched < timedelta(minutes=1)


# ---------- unsupported ----------


async def test_unsupported_never_calls_http(db_session, monkeypatch):
    calls = mock_http(monkeypatch, lambda req: httpx.Response(500))

    result = await barcode_service.lookup_external(db_session, "12345")
    assert result.status == "unsupported"
    assert result.external is None
    assert calls["n"] == 0

    rows = (await db_session.execute(select(BarcodeLookup))).scalars().all()
    assert rows == []


# ---------- 分類建議 ----------


async def _category_tree(db_session) -> tuple[User, Category, Category]:
    u = User(
        email="cat@test.io",
        username="cat_user",
        password_hash=hash_password("secret1234"),
    )
    db_session.add(u)
    await db_session.flush()
    parent = Category(owner_id=u.id, name="生活")
    db_session.add(parent)
    await db_session.flush()
    food = Category(owner_id=u.id, name="食品", parent_id=parent.id)
    drink = Category(owner_id=u.id, name="飲料", parent_id=parent.id)
    db_session.add_all([food, drink])
    await db_session.commit()
    return u, food, drink


async def test_suggest_category_unique_leaf_match(db_session):
    u, food, _ = await _category_tree(db_session)

    suggested = await barcode_service.suggest_category_id(
        db_session, u.id, "Snacks, 食品, Dairy"
    )
    assert suggested == food.id


async def test_suggest_category_multiple_matches_is_none(db_session):
    u, _, _ = await _category_tree(db_session)

    assert await barcode_service.suggest_category_id(db_session, u.id, "食品, 飲料") is None


async def test_suggest_category_no_match_and_non_leaf(db_session):
    u, _, _ = await _category_tree(db_session)

    assert await barcode_service.suggest_category_id(db_session, u.id, "Books") is None
    # 上層分類（生活）非葉節點 → 不建議
    assert await barcode_service.suggest_category_id(db_session, u.id, "生活") is None


async def test_suggest_category_isolated_by_owner(db_session):
    await _category_tree(db_session)
    other = User(
        email="other@test.io",
        username="other_user",
        password_hash=hash_password("secret1234"),
    )
    db_session.add(other)
    await db_session.commit()

    assert (
        await barcode_service.suggest_category_id(db_session, other.id, "食品") is None
    )
