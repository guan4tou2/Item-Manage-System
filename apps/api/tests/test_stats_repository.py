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
