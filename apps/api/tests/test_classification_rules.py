from __future__ import annotations

from typing import Optional, Sequence

import pytest

from app.auth.password import hash_password
from app.models.category import Category
from app.models.item import Item
from app.models.location import Location
from app.models.tag import Tag
from app.models.user import User
from app.services import classification_service


async def _user(session, username: str = "cls_user") -> User:
    user = User(
        email=f"{username}@test.io",
        username=username,
        password_hash=hash_password("secret1234"),
    )
    session.add(user)
    await session.flush()
    return user


async def _category(session, owner_id, name: str) -> Category:
    category = Category(owner_id=owner_id, name=name)
    session.add(category)
    await session.flush()
    return category


async def _location(session, owner_id, name: str) -> Location:
    location = Location(owner_id=owner_id, name=name)
    session.add(location)
    await session.flush()
    return location


async def _tag(session, owner_id, name: str) -> Tag:
    tag = Tag(owner_id=owner_id, name=name)
    session.add(tag)
    await session.flush()
    return tag


async def _item(
    session,
    owner_id,
    name: str,
    *,
    category: Optional[Category] = None,
    location: Optional[Location] = None,
    tags: Sequence[Tag] = (),
    is_deleted: bool = False,
) -> Item:
    item = Item(
        owner_id=owner_id,
        name=name,
        quantity=1,
        is_deleted=is_deleted,
        category_id=category.id if category else None,
        location_id=location.id if location else None,
        tags=list(tags),
    )
    session.add(item)
    await session.flush()
    return item


# --- tokenize ---------------------------------------------------------------


def test_tokenize_mixed_cjk_latin():
    assert classification_service.tokenize("Hario V60 陶瓷咖啡濾杯") == {
        "hario",
        "v60",
        "陶瓷",
        "瓷咖",
        "咖啡",
        "啡濾",
        "濾杯",
    }


def test_tokenize_short_cjk_and_latin():
    # CJK 單字元保留；拉丁／數字單字元丟棄
    assert classification_service.tokenize("杯") == {"杯"}
    assert classification_service.tokenize("a b 杯") == {"杯"}


def test_tokenize_nfkc_and_case_fold():
    assert classification_service.tokenize("ＡＢ１２") == {"ab12"}
    assert classification_service.tokenize("USB充電線") == {"usb", "充電", "電線"}


def test_tokenize_blank_and_symbols():
    assert classification_service.tokenize("") == set()
    assert classification_service.tokenize("   ") == set()
    assert classification_service.tokenize("!!!--@#") == set()


# --- suggest ----------------------------------------------------------------


async def test_suggest_ranks_by_score(db_session):
    user = await _user(db_session)
    kitchen = await _category(db_session, user.id, "廚房用品")
    tableware = await _category(db_session, user.id, "餐具")
    cabinet = await _location(db_session, user.id, "廚房")
    coffee_tag = await _tag(db_session, user.id, "咖啡")
    await _item(
        db_session,
        user.id,
        "陶瓷咖啡杯",
        category=kitchen,
        location=cabinet,
        tags=[coffee_tag],
    )
    await _item(db_session, user.id, "陶瓷盤", category=tableware)

    result = await classification_service.suggest_for_name(
        db_session, user.id, "陶瓷咖啡杯"
    )

    assert result.category is not None
    assert (result.category.id, result.category.name) == (kitchen.id, "廚房用品")
    assert result.category.score == 4
    assert result.category.item_count == 1
    assert result.location is not None
    assert result.location.name == "廚房"
    assert [tag.name for tag in result.tags] == ["咖啡"]


async def test_suggest_tie_break_by_item_count(db_session):
    user = await _user(db_session)
    single = await _category(db_session, user.id, "單品")
    double = await _category(db_session, user.id, "雙品")
    await _item(db_session, user.id, "咖啡壺", category=single)
    await _item(db_session, user.id, "即溶咖啡", category=double)
    await _item(db_session, user.id, "咖啡豆", category=double)

    result = await classification_service.suggest_for_name(db_session, user.id, "咖啡壺")

    # 兩分類 score 皆為 2；item_count 較多者優先
    assert result.category is not None
    assert (result.category.name, result.category.item_count) == ("雙品", 2)


async def test_suggest_tie_break_by_id(db_session):
    user = await _user(db_session)
    first = await _category(db_session, user.id, "甲類")
    second = await _category(db_session, user.id, "乙類")
    await _item(db_session, user.id, "電線", category=first)
    await _item(db_session, user.id, "電線", category=second)

    result = await classification_service.suggest_for_name(db_session, user.id, "電線")

    assert result.category is not None
    assert result.category.id == first.id


async def test_suggest_tags_top3_sorted(db_session):
    user = await _user(db_session)
    tags = {
        name: await _tag(db_session, user.id, name)
        for name in ("blue", "green", "red", "yellow")
    }
    await _item(db_session, user.id, "電線", tags=[tags["blue"]])
    await _item(db_session, user.id, "電線", tags=[tags["blue"]])
    await _item(db_session, user.id, "電線", tags=[tags["red"]])
    await _item(db_session, user.id, "電線", tags=[tags["green"]])
    await _item(db_session, user.id, "電線", tags=[tags["yellow"]])

    result = await classification_service.suggest_for_name(db_session, user.id, "電線")

    # blue（count 2）優先，其餘 count 1 依名稱排序；僅取前 3
    assert [(tag.name, tag.item_count) for tag in result.tags] == [
        ("blue", 2),
        ("green", 1),
        ("red", 1),
    ]


async def test_suggest_skips_null_category_and_location(db_session):
    user = await _user(db_session)
    await _item(db_session, user.id, "陶瓷咖啡杯")

    result = await classification_service.suggest_for_name(
        db_session, user.id, "陶瓷咖啡杯"
    )

    assert result.category is None
    assert result.location is None
    assert result.tags == []


async def test_suggest_excludes_soft_deleted(db_session):
    user = await _user(db_session)
    kitchen = await _category(db_session, user.id, "廚房用品")
    await _item(db_session, user.id, "陶瓷咖啡杯", category=kitchen, is_deleted=True)

    result = await classification_service.suggest_for_name(
        db_session, user.id, "陶瓷咖啡杯"
    )

    assert result.category is None


async def test_suggest_only_uses_own_items(db_session):
    owner = await _user(db_session, "cls_owner")
    other = await _user(db_session, "cls_other")
    other_category = await _category(db_session, other.id, "別的廚房")
    await _item(db_session, other.id, "陶瓷咖啡杯", category=other_category)

    result = await classification_service.suggest_for_name(
        db_session, owner.id, "陶瓷咖啡杯"
    )

    assert result.category is None
    assert result.tags == []


async def test_suggest_blank_or_unmatched_name(db_session):
    user = await _user(db_session)
    kitchen = await _category(db_session, user.id, "廚房用品")
    await _item(db_session, user.id, "陶瓷咖啡杯", category=kitchen)

    blank = await classification_service.suggest_for_name(db_session, user.id, "   ")
    assert (blank.category, blank.location, blank.tags) == (None, None, [])

    unmatched = await classification_service.suggest_for_name(
        db_session, user.id, "量子力學"
    )
    assert (unmatched.category, unmatched.location, unmatched.tags) == (None, None, [])


async def test_suggest_is_deterministic(db_session):
    user = await _user(db_session)
    kitchen = await _category(db_session, user.id, "廚房用品")
    await _item(db_session, user.id, "陶瓷咖啡杯", category=kitchen)

    first = await classification_service.suggest_for_name(
        db_session, user.id, "陶瓷咖啡杯"
    )
    second = await classification_service.suggest_for_name(
        db_session, user.id, "陶瓷咖啡杯"
    )

    assert first == second


async def test_suggest_respects_scan_limit(db_session, monkeypatch):
    monkeypatch.setattr(classification_service, "MAX_SCAN", 2)
    user = await _user(db_session)
    kitchen = await _category(db_session, user.id, "廚房用品")
    for _ in range(3):
        await _item(db_session, user.id, "咖啡", category=kitchen)

    result = await classification_service.suggest_for_name(db_session, user.id, "咖啡")

    # 只掃描前 2 筆（未套用護欄會是 score 3／item_count 3）
    assert result.category is not None
    assert (result.category.score, result.category.item_count) == (2, 2)


# --- suggest_for_names（Phase 33 批次化） ------------------------------------


async def test_suggest_for_names_matches_single_calls(db_session):
    """批次結果與逐次呼叫完全相同（含排序與分數）。"""
    user = await _user(db_session)
    kitchen = await _category(db_session, user.id, "廚房用品")
    food = await _category(db_session, user.id, "食品")
    kitchen_loc = await _location(db_session, user.id, "廚房")
    coffee_tag = await _tag(db_session, user.id, "咖啡")
    await _item(
        db_session, user.id, "陶瓷咖啡杯",
        category=kitchen, location=kitchen_loc, tags=[coffee_tag],
    )
    await _item(db_session, user.id, "鮮乳", category=food)
    await _item(db_session, user.id, "咖啡豆", category=food, tags=[coffee_tag])

    names = ["陶瓷咖啡杯", "鮮乳", "咖啡豆", "無關字串"]
    batched = await classification_service.suggest_for_names(
        db_session, user.id, names
    )
    singles = [
        await classification_service.suggest_for_name(db_session, user.id, name)
        for name in names
    ]

    assert batched == singles


async def test_suggest_for_names_preserves_order_and_handles_empty(db_session):
    user = await _user(db_session)
    food = await _category(db_session, user.id, "食品")
    await _item(db_session, user.id, "鮮乳", category=food)

    results = await classification_service.suggest_for_names(
        db_session, user.id, ["", "鮮乳", "不存在"]
    )

    assert len(results) == 3
    # 空名稱 → 無建議；命中 → 食品；未命中 → 無建議
    assert results[0].category is None
    assert results[1].category is not None
    assert results[1].category.id == food.id
    assert results[2].category is None


async def test_suggest_for_names_empty_list(db_session):
    user = await _user(db_session)

    assert await classification_service.suggest_for_names(db_session, user.id, []) == []


async def test_suggest_for_names_isolates_users(db_session):
    alice = await _user(db_session, "cls_alice")
    bob = await _user(db_session, "cls_bob")
    alice_cat = await _category(db_session, alice.id, "廚房用品")
    await _item(db_session, alice.id, "咖啡濾杯", category=alice_cat)

    result = await classification_service.suggest_for_names(
        db_session, bob.id, ["咖啡濾杯"]
    )

    assert result[0].category is None
