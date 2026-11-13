from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from app.auth.password import hash_password
from app.models.category import Category
from app.models.group import Group, GroupMember
from app.models.item import Item
from app.models.item_batch import ItemBatch
from app.models.item_history import QuantityLog
from app.models.location import Location
from app.models.loan import ItemLoan
from app.models.user import User
from app.services import reports_service
from app.services.reports_service import period_for

SEP_START_UTC = datetime(2026, 8, 31, 16, 0, tzinfo=UTC)
SEP_END_UTC = datetime(2026, 9, 30, 16, 0, tzinfo=UTC)
GENERATED_AT = datetime(2026, 10, 1, 0, 5, tzinfo=UTC)


async def _user(session, username: str) -> User:
    user = User(
        email=f"{username}@test.io",
        username=username,
        password_hash=hash_password("secret1234"),
    )
    session.add(user)
    await session.flush()
    return user


async def _item(session, owner: User, **fields) -> Item:
    item = Item(owner_id=owner.id, name=fields.pop("name", "物品"), **fields)
    session.add(item)
    await session.flush()
    return item


def test_period_bounds_are_taipei_month():
    period = period_for(date(2026, 9, 1))

    assert (period.key, period.start, period.end) == (
        "2026-09",
        date(2026, 9, 1),
        date(2026, 9, 30),
    )
    # Asia/Taipei = UTC+8：9/1 00:00 TPE = 8/31 16:00 UTC
    assert period.start_utc == SEP_START_UTC
    assert period.end_utc == SEP_END_UTC


def test_previous_period_handles_year_boundary():
    period = reports_service.previous_period(date(2026, 1, 1))

    assert period.key == "2025-12"
    assert period.start == date(2025, 12, 1)
    assert period.end == date(2025, 12, 31)


def test_previous_period_uses_immediately_previous_month():
    period = reports_service.previous_period(date(2026, 10, 18))

    assert period.key == "2026-09"


def test_previous_week_on_monday():
    """週一執行：上一個完整 ISO 週（週一至週日）。"""
    period = reports_service.previous_week(date(2026, 10, 19))

    assert (period.key, period.start, period.end) == (
        "2026-W42",
        date(2026, 10, 12),
        date(2026, 10, 18),
    )
    # Asia/Taipei = UTC+8：週一 00:00 TPE = 前一日 16:00 UTC
    assert period.start_utc == datetime(2026, 10, 11, 16, 0, tzinfo=UTC)
    assert period.end_utc == datetime(2026, 10, 18, 16, 0, tzinfo=UTC)


def test_previous_week_on_sunday_does_not_include_current_week():
    """週日執行：當週尚未結束，仍取再上一個完整週。"""
    period = reports_service.previous_week(date(2026, 10, 18))

    assert (period.key, period.start, period.end) == (
        "2026-W41",
        date(2026, 10, 5),
        date(2026, 10, 11),
    )


def test_previous_week_iso_year_boundary():
    period = reports_service.previous_week(date(2026, 1, 1))

    assert (period.key, period.start, period.end) == (
        "2025-W52",
        date(2025, 12, 22),
        date(2025, 12, 28),
    )


def test_previous_week_key_uses_monday_iso_year():
    """2025-12-29（一）的 ISO 年為 2026 → key 必須是 2026-W01，不是 2025-W53。"""
    period = reports_service.previous_week(date(2026, 1, 5))

    assert (period.key, period.start, period.end) == (
        "2026-W01",
        date(2025, 12, 29),
        date(2026, 1, 4),
    )


async def test_payload_totals_activity_and_visible_scope(db_session):
    alice = await _user(db_session, "alice")
    bob = await _user(db_session, "bob")
    carol = await _user(db_session, "carol")

    group = Group(owner_id=alice.id, name="家人")
    group.members = [
        GroupMember(user_id=alice.id),
        GroupMember(user_id=bob.id),
    ]
    db_session.add(group)

    food = Category(owner_id=alice.id, name="食品")
    tools = Category(owner_id=alice.id, name="工具")
    bob_category = Category(owner_id=bob.id, name="鮑伯分類")
    root = Location(owner_id=alice.id, name="儲藏室")
    bob_location = Location(owner_id=bob.id, name="鮑伯櫃")
    db_session.add_all([food, tools, bob_category, root, bob_location])
    await db_session.flush()
    shelf = Location(owner_id=alice.id, name="上層", parent_id=root.id)
    db_session.add(shelf)
    await db_session.flush()

    old_alive = await _item(
        db_session,
        alice,
        name="既有庫存",
        quantity=13,
        cost=Decimal("2.00"),
        category_id=food.id,
        location_id=shelf.id,
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
    )
    new_alive = await _item(
        db_session,
        alice,
        name="本月新增",
        quantity=2,
        cost=Decimal("1.00"),
        category_id=food.id,
        location_id=root.id,
        created_at=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
    )
    await _item(
        db_session,
        alice,
        name="工具",
        quantity=1,
        category_id=tools.id,
        location_id=root.id,
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
    )
    await _item(
        db_session,
        alice,
        name="本月刪除",
        quantity=2,
        cost=Decimal("5.00"),
        category_id=tools.id,
        is_deleted=True,
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
        updated_at=datetime(2026, 9, 12, tzinfo=UTC),
    )
    await _item(
        db_session,
        alice,
        name="上上月刪除",
        is_deleted=True,
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
        updated_at=datetime(2026, 8, 15, tzinfo=UTC),
    )
    await _item(
        db_session,
        bob,
        name="鮑伯物品",
        quantity=4,
        category_id=bob_category.id,
        location_id=bob_location.id,
        created_at=datetime(2026, 8, 20, tzinfo=UTC),
    )
    carol_item = await _item(
        db_session,
        carol,
        name="卡蘿物品",
        quantity=99,
        created_at=datetime(2026, 8, 20, tzinfo=UTC),
    )

    db_session.add_all(
        [
            QuantityLog(
                item_id=old_alive.id,
                old_quantity=10,
                new_quantity=15,
                created_at=datetime(2026, 9, 5, tzinfo=UTC),
            ),
            QuantityLog(
                item_id=old_alive.id,
                old_quantity=15,
                new_quantity=13,
                created_at=datetime(2026, 9, 6, tzinfo=UTC),
            ),
            QuantityLog(
                item_id=new_alive.id,
                old_quantity=3,
                new_quantity=2,
                created_at=datetime(2026, 9, 20, tzinfo=UTC),
            ),
            QuantityLog(
                item_id=old_alive.id,
                old_quantity=10,
                new_quantity=9,
                created_at=datetime(2026, 8, 20, tzinfo=UTC),
            ),
            QuantityLog(
                item_id=carol_item.id,
                old_quantity=99,
                new_quantity=1,
                created_at=datetime(2026, 9, 20, tzinfo=UTC),
            ),
        ]
    )
    await db_session.commit()

    payload = await reports_service.build_payload(
        db_session,
        user_id=alice.id,
        period=period_for(date(2026, 9, 1)),
        generated_at=GENERATED_AT,
        currency="TWD",
    )

    assert payload.period == "2026-09"
    assert payload.kind == "monthly"
    assert payload.timezone == "Asia/Taipei"
    assert payload.period_start == date(2026, 9, 1)
    assert payload.period_end == date(2026, 9, 30)
    assert payload.currency == "TWD"

    # alice + bob（同群組）；carol 不在群組 → 排除
    assert payload.totals.item_count == 4
    assert payload.totals.quantity == 20

    assert payload.activity.items_created == 1
    assert payload.activity.items_deleted == 1
    assert payload.activity.quantity_in == 5
    assert payload.activity.quantity_out == 3
    assert payload.has_activity is True

    assert [(b.label, b.count) for b in payload.top_categories] == [
        ("食品", 2),
        ("工具", 1),
        ("鮑伯分類", 1),
    ]
    location_buckets = [(b.label, b.count) for b in payload.top_locations]
    assert location_buckets[0] == ("儲藏室", 2)
    # 兩筆同為 1 件：順序依 location_id（插入序），不鎖定跨資料庫的 tie-break
    assert set(location_buckets[1:]) == {
        ("儲藏室 / 上層", 1),
        ("鮑伯櫃", 1),
    }


async def test_payload_period_boundary_uses_taipei_midnight(db_session):
    user = await _user(db_session, "boundary")

    inside = await _item(
        db_session,
        user,
        name="九月最後一分鐘",
        created_at=datetime(2026, 9, 30, 15, 59, tzinfo=UTC),
    )
    await _item(
        db_session,
        user,
        name="十月第一秒",
        created_at=datetime(2026, 9, 30, 16, 0, tzinfo=UTC),
    )
    await db_session.commit()

    payload = await reports_service.build_payload(
        db_session,
        user_id=user.id,
        period=period_for(date(2026, 9, 1)),
        generated_at=GENERATED_AT,
        currency="TWD",
    )

    assert payload.activity.items_created == 1
    assert payload.totals.item_count == 2
    # 現況包含兩件；期間新增只算 9/30 23:59 TPE 那件
    assert payload.has_activity is True
    assert inside.created_at is not None


async def test_weekly_payload_period_boundary_uses_taipei_midnight(db_session):
    """Phase 42：週報期間為 [週一 00:00 TPE, 下週一 00:00 TPE)。"""
    user = await _user(db_session, "weekly_boundary")

    inside = await _item(
        db_session,
        user,
        name="週日最後一分鐘",
        created_at=datetime(2026, 10, 18, 15, 59, tzinfo=UTC),
    )
    await _item(
        db_session,
        user,
        name="週一第一秒",
        created_at=datetime(2026, 10, 18, 16, 0, tzinfo=UTC),
    )
    await db_session.commit()

    payload = await reports_service.build_payload(
        db_session,
        user_id=user.id,
        period=reports_service.previous_week(date(2026, 10, 19)),
        generated_at=GENERATED_AT,
        currency="TWD",
        kind="weekly",
    )

    assert payload.kind == "weekly"
    assert payload.period == "2026-W42"
    assert payload.period_start == date(2026, 10, 12)
    assert payload.period_end == date(2026, 10, 18)
    assert payload.activity.items_created == 1
    assert payload.totals.item_count == 2
    assert inside.created_at is not None


async def test_payload_without_items_is_empty(db_session):
    user = await _user(db_session, "empty")
    await db_session.commit()

    payload = await reports_service.build_payload(
        db_session,
        user_id=user.id,
        period=period_for(date(2026, 9, 1)),
        generated_at=GENERATED_AT,
        currency="TWD",
    )

    assert payload.totals.item_count == 0
    assert payload.totals.quantity == 0
    assert payload.activity.items_created == 0
    assert payload.has_activity is False
    assert payload.top_categories == []
    assert payload.top_locations == []


async def test_payload_valuation_reconstruction(db_session):
    user = await _user(db_session, "valuation")

    old = await _item(
        db_session,
        user,
        name="既有庫存",
        quantity=7,
        cost=Decimal("2.00"),
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
    )
    await _item(
        db_session,
        user,
        name="本月新增",
        quantity=4,
        cost=Decimal("1.50"),
        created_at=datetime(2026, 9, 10, tzinfo=UTC),
    )
    await _item(
        db_session,
        user,
        name="本月刪除",
        quantity=2,
        cost=Decimal("5.00"),
        is_deleted=True,
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
        updated_at=datetime(2026, 9, 12, tzinfo=UTC),
    )
    await _item(
        db_session,
        user,
        name="未設定成本",
        quantity=7,
        cost=None,
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
    )
    created_then_deleted = await _item(
        db_session,
        user,
        name="本月建立又刪除",
        quantity=3,
        cost=Decimal("4.00"),
        is_deleted=True,
        created_at=datetime(2026, 9, 10, tzinfo=UTC),
        updated_at=datetime(2026, 9, 15, tzinfo=UTC),
    )
    db_session.add(
        QuantityLog(
            item_id=old.id,
            old_quantity=10,
            new_quantity=7,
            created_at=datetime(2026, 9, 6, tzinfo=UTC),
        )
    )
    db_session.add(
        QuantityLog(
            item_id=created_then_deleted.id,
            old_quantity=3,
            new_quantity=1,
            created_at=datetime(2026, 9, 11, tzinfo=UTC),
        )
    )
    await db_session.commit()

    payload = await reports_service.build_payload(
        db_session,
        user_id=user.id,
        period=period_for(date(2026, 9, 1)),
        generated_at=GENERATED_AT,
        currency="TWD",
    )

    # end = 7×2 + 4×1.5 = 20；start = 20 − 6 + 10 − (−6) = 30
    # （月初：既有 10×2 + 本月刪除 2×5 = 30；期末消耗 3 件 −6）
    assert payload.valuation.end == "20.00"
    assert payload.valuation.start == "30.00"
    assert payload.valuation.delta == "-10.00"
    assert payload.valuation.unpriced_items == 1


async def test_payload_expiry_counts_at_period_end(db_session):
    user = await _user(db_session, "expiry")
    other = await _user(db_session, "expiry_other")

    def batch(item: Item, quantity: int, expiry, *, depleted: bool = False):
        return ItemBatch(
            item_id=item.id,
            quantity=quantity,
            expiry_date=expiry,
            is_depleted=depleted,
        )

    expired_item = await _item(
        db_session, user, name="已過期", created_at=datetime(2026, 8, 1, tzinfo=UTC)
    )
    soon_item = await _item(
        db_session, user, name="快到期", created_at=datetime(2026, 8, 1, tzinfo=UTC)
    )
    far_item = await _item(
        db_session, user, name="還很久", created_at=datetime(2026, 8, 1, tzinfo=UTC)
    )
    deleted_item = await _item(
        db_session,
        user,
        name="已刪除",
        is_deleted=True,
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
        updated_at=datetime(2026, 9, 1, tzinfo=UTC),
    )
    other_item = await _item(
        db_session, other, name="他人", created_at=datetime(2026, 8, 1, tzinfo=UTC)
    )
    db_session.add_all(
        [
            batch(expired_item, 1, date(2026, 9, 25)),
            batch(soon_item, 2, date(2026, 9, 30)),  # 期末當天到期：expired
            batch(soon_item, 3, date(2026, 10, 10)),  # 10 天內：expiring
            batch(far_item, 4, date(2026, 11, 15)),  # 超過 30 天
            batch(far_item, 5, date(2026, 9, 20), depleted=True),  # 已耗盡
            batch(deleted_item, 1, date(2026, 9, 20)),  # 物品已刪除
            batch(other_item, 1, date(2026, 9, 20)),  # 非可見範圍
        ]
    )
    await db_session.commit()

    payload = await reports_service.build_payload(
        db_session,
        user_id=user.id,
        period=period_for(date(2026, 9, 1)),
        generated_at=GENERATED_AT,
        currency="TWD",
    )

    assert payload.expiry.expired == 2
    assert payload.expiry.expiring_soon == 1


async def test_payload_loan_counts(db_session):
    user = await _user(db_session, "loans")
    other = await _user(db_session, "loans_other")

    item1 = await _item(
        db_session, user, name="借出物品1", created_at=datetime(2026, 8, 1, tzinfo=UTC)
    )
    item2 = await _item(
        db_session, user, name="借出物品2", created_at=datetime(2026, 8, 1, tzinfo=UTC)
    )
    item3 = await _item(
        db_session, user, name="借出物品3", created_at=datetime(2026, 8, 1, tzinfo=UTC)
    )
    item4 = await _item(
        db_session, user, name="借出物品4", created_at=datetime(2026, 8, 1, tzinfo=UTC)
    )
    other_item = await _item(
        db_session,
        other,
        name="他人物品",
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
    )

    def loan(
        target: Item,
        lent: datetime,
        expected: date | None,
        returned: datetime | None = None,
    ) -> ItemLoan:
        return ItemLoan(
            item_id=target.id,
            borrower_label="朋友",
            lent_at=lent,
            expected_return=expected,
            returned_at=returned,
        )

    db_session.add_all(
        [
            # 本期借出、本期歸還：out + returned，不算逾期
            loan(
                item1,
                datetime(2026, 9, 5, tzinfo=UTC),
                date(2026, 9, 20),
                datetime(2026, 9, 25, tzinfo=UTC),
            ),
            # 上期借出、期末已逾期、10 月才歸還：overdue
            loan(
                item2,
                datetime(2026, 8, 20, tzinfo=UTC),
                date(2026, 9, 10),
                datetime(2026, 10, 2, tzinfo=UTC),
            ),
            # 上期借出、期末未到期：不計
            loan(
                item3,
                datetime(2026, 8, 20, tzinfo=UTC),
                date(2026, 10, 10),
            ),
            # 本期借出、期末仍未還且逾期：out + overdue
            loan(
                item4,
                datetime(2026, 9, 10, tzinfo=UTC),
                date(2026, 9, 12),
            ),
            # 非可見範圍
            loan(
                other_item,
                datetime(2026, 9, 10, tzinfo=UTC),
                date(2026, 9, 12),
                datetime(2026, 9, 13, tzinfo=UTC),
            ),
        ]
    )
    await db_session.commit()

    payload = await reports_service.build_payload(
        db_session,
        user_id=user.id,
        period=period_for(date(2026, 9, 1)),
        generated_at=GENERATED_AT,
        currency="TWD",
    )

    assert payload.activity.loans_out == 2
    assert payload.activity.loans_returned == 1
    assert payload.activity.loans_overdue == 2


async def test_payload_activity_false_when_only_expiry_state(db_session):
    user = await _user(db_session, "quiet")
    item = await _item(
        db_session, user, name="安靜", created_at=datetime(2026, 8, 1, tzinfo=UTC)
    )
    db_session.add(
        ItemBatch(item_id=item.id, quantity=1, expiry_date=date(2026, 10, 5))
    )
    await db_session.commit()

    payload = await reports_service.build_payload(
        db_session,
        user_id=user.id,
        period=period_for(date(2026, 9, 1)),
        generated_at=GENERATED_AT,
        currency="TWD",
    )

    assert payload.expiry.expiring_soon == 1
    assert payload.has_activity is False
