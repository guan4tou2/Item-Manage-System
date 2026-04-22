import pytest

from app.models.category import Category
from app.models.item import Item
from app.models.location import Location
from app.models.tag import Tag
from app.models.user import User
from app.repositories import stats_repository


@pytest.fixture
async def two_users(db_session):
    a = User(email="a@t.io", username="alice", password_hash="x")
    b = User(email="b@t.io", username="bob", password_hash="x")
    db_session.add_all([a, b])
    await db_session.commit()
    return a, b


async def test_overview_empty_owner_returns_zeros(db_session, two_users):
    alice, _ = two_users
    result = await stats_repository.overview(db_session, alice.id)
    assert result == {
        "total_items": 0,
        "total_quantity": 0,
        "total_categories": 0,
        "total_locations": 0,
        "total_tags": 0,
    }


async def test_overview_counts_owned_items_only(db_session, two_users):
    alice, bob = two_users
    db_session.add_all([
        Item(owner_id=alice.id, name="x", quantity=3),
        Item(owner_id=alice.id, name="y", quantity=5),
        Item(owner_id=bob.id, name="z", quantity=100),
    ])
    await db_session.commit()
    result = await stats_repository.overview(db_session, alice.id)
    assert result["total_items"] == 2
    assert result["total_quantity"] == 8


async def test_overview_excludes_soft_deleted(db_session, two_users):
    alice, _ = two_users
    live = Item(owner_id=alice.id, name="live", quantity=1)
    dead = Item(owner_id=alice.id, name="dead", quantity=10, is_deleted=True)
    db_session.add_all([live, dead])
    await db_session.commit()
    result = await stats_repository.overview(db_session, alice.id)
    assert result["total_items"] == 1
    assert result["total_quantity"] == 1


async def test_overview_counts_taxonomy(db_session, two_users):
    alice, _ = two_users
    cat = Category(owner_id=alice.id, name="cat1")
    loc = Location(owner_id=alice.id, floor="1F")
    tag = Tag(owner_id=alice.id, name="tag1")
    db_session.add_all([cat, loc, tag])
    await db_session.commit()
    result = await stats_repository.overview(db_session, alice.id)
    assert result["total_categories"] == 1
    assert result["total_locations"] == 1
    assert result["total_tags"] == 1


async def test_by_category_groups_and_includes_null_bucket(db_session, two_users):
    alice, _ = two_users
    cat_a = Category(owner_id=alice.id, name="A")
    cat_b = Category(owner_id=alice.id, name="B")
    db_session.add_all([cat_a, cat_b])
    await db_session.commit()
    db_session.add_all([
        Item(owner_id=alice.id, name="i1", category_id=cat_a.id, quantity=1),
        Item(owner_id=alice.id, name="i2", category_id=cat_a.id, quantity=1),
        Item(owner_id=alice.id, name="i3", category_id=cat_b.id, quantity=1),
        Item(owner_id=alice.id, name="i4", quantity=1),
        Item(owner_id=alice.id, name="i5", quantity=1, is_deleted=True),
    ])
    await db_session.commit()

    rows = await stats_repository.by_category(db_session, alice.id)
    assert rows[0] == {"category_id": cat_a.id, "name": "A", "count": 2}
    rest = sorted(rows[1:], key=lambda r: (r["name"] is None, r["name"] or ""))
    assert rest == [
        {"category_id": cat_b.id, "name": "B", "count": 1},
        {"category_id": None, "name": None, "count": 1},
    ]


async def test_by_category_owner_isolation(db_session, two_users):
    alice, bob = two_users
    cat = Category(owner_id=bob.id, name="bob-cat")
    db_session.add(cat)
    await db_session.commit()
    db_session.add(Item(owner_id=bob.id, name="x", category_id=cat.id, quantity=1))
    await db_session.commit()
    rows = await stats_repository.by_category(db_session, alice.id)
    assert rows == []
