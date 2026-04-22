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


async def test_by_location_composes_label_and_includes_null(db_session, two_users):
    alice, _ = two_users
    loc_full = Location(owner_id=alice.id, floor="1F", room="客廳", zone="電視櫃")
    loc_partial = Location(owner_id=alice.id, floor="2F", room=None, zone="陽台")
    db_session.add_all([loc_full, loc_partial])
    await db_session.commit()
    db_session.add_all([
        Item(owner_id=alice.id, name="i1", location_id=loc_full.id, quantity=1),
        Item(owner_id=alice.id, name="i2", location_id=loc_full.id, quantity=1),
        Item(owner_id=alice.id, name="i3", location_id=loc_partial.id, quantity=1),
        Item(owner_id=alice.id, name="i4", quantity=1),
    ])
    await db_session.commit()

    rows = await stats_repository.by_location(db_session, alice.id)
    by_id = {r["location_id"]: r for r in rows}
    assert by_id[loc_full.id] == {
        "location_id": loc_full.id, "label": "1F / 客廳 / 電視櫃", "count": 2,
    }
    assert by_id[loc_partial.id] == {
        "location_id": loc_partial.id, "label": "2F / 陽台", "count": 1,
    }
    assert by_id[None] == {"location_id": None, "label": None, "count": 1}


async def test_by_tag_counts_usage_desc_and_respects_limit(db_session, two_users):
    alice, _ = two_users
    t_red = Tag(owner_id=alice.id, name="red")
    t_blue = Tag(owner_id=alice.id, name="blue")
    t_unused = Tag(owner_id=alice.id, name="unused")
    db_session.add_all([t_red, t_blue, t_unused])
    await db_session.commit()
    i1 = Item(owner_id=alice.id, name="i1", quantity=1)
    i2 = Item(owner_id=alice.id, name="i2", quantity=1)
    i3 = Item(owner_id=alice.id, name="i3", quantity=1)
    i1.tags = [t_red, t_blue]
    i2.tags = [t_red]
    i3.tags = [t_red]
    db_session.add_all([i1, i2, i3])
    await db_session.commit()

    rows = await stats_repository.by_tag(db_session, alice.id, limit=10)
    names = [(r["name"], r["count"]) for r in rows]
    assert names == [("red", 3), ("blue", 1)]

    limited = await stats_repository.by_tag(db_session, alice.id, limit=1)
    assert len(limited) == 1
    assert limited[0]["name"] == "red"


async def test_by_tag_excludes_soft_deleted_items(db_session, two_users):
    alice, _ = two_users
    t = Tag(owner_id=alice.id, name="x")
    db_session.add(t)
    await db_session.commit()
    i = Item(owner_id=alice.id, name="gone", quantity=1, is_deleted=True)
    i.tags = [t]
    db_session.add(i)
    await db_session.commit()
    rows = await stats_repository.by_tag(db_session, alice.id, limit=10)
    assert rows == []


async def test_recent_items_desc_by_created_at(db_session, two_users):
    from datetime import datetime, timedelta, timezone
    alice, _ = two_users
    now = datetime.now(timezone.utc)
    older = Item(owner_id=alice.id, name="old", quantity=1, created_at=now - timedelta(hours=2))
    newer = Item(owner_id=alice.id, name="new", quantity=1, created_at=now - timedelta(hours=1))
    db_session.add_all([older, newer])
    await db_session.commit()

    rows = await stats_repository.recent_items(db_session, alice.id, limit=5)
    assert [r.name for r in rows] == ["new", "old"]


async def test_recent_items_limit(db_session, two_users):
    alice, _ = two_users
    for i in range(3):
        db_session.add(Item(owner_id=alice.id, name=f"i{i}", quantity=1))
    await db_session.commit()
    rows = await stats_repository.recent_items(db_session, alice.id, limit=2)
    assert len(rows) == 2
