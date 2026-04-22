from uuid import UUID

import pytest

from app.models import Category, Item, Location, Tag, User
from app.repositories import items_repository as repo


@pytest.fixture
async def seed(db_session):
    user = User(email="r@t.io", username="r_user", password_hash="x",
                is_active=True, is_admin=False)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    cat = Category(owner_id=user.id, name="cat1")
    loc = Location(owner_id=user.id, floor="1F")
    t1 = Tag(owner_id=user.id, name="red")
    t2 = Tag(owner_id=user.id, name="blue")
    db_session.add_all([cat, loc, t1, t2])
    await db_session.commit()

    a = Item(owner_id=user.id, name="apple", description="a fruit", category=cat, location=loc, tags=[t1])
    b = Item(owner_id=user.id, name="banana", description="yellow fruit", tags=[t2])
    c = Item(owner_id=user.id, name="cherry", tags=[t1, t2])
    d = Item(owner_id=user.id, name="deleted one", is_deleted=True)
    db_session.add_all([a, b, c, d])
    await db_session.commit()
    return {"user": user, "cat": cat, "loc": loc, "t1": t1, "t2": t2}


async def test_list_ignores_deleted(db_session, seed):
    rows, total = await repo.list_paginated(
        db_session, seed["user"].id,
        q=None, category_id=None, location_id=None, tag_ids=None,
        page=1, per_page=10,
    )
    names = {r.name for r in rows}
    assert "deleted one" not in names
    assert total == 3


async def test_search_q_ilike(db_session, seed):
    rows, total = await repo.list_paginated(
        db_session, seed["user"].id,
        q="fruit", category_id=None, location_id=None, tag_ids=None,
        page=1, per_page=10,
    )
    assert {r.name for r in rows} == {"apple", "banana"}
    assert total == 2


async def test_filter_category(db_session, seed):
    rows, total = await repo.list_paginated(
        db_session, seed["user"].id,
        q=None, category_id=seed["cat"].id, location_id=None, tag_ids=None,
        page=1, per_page=10,
    )
    assert {r.name for r in rows} == {"apple"}


async def test_filter_location(db_session, seed):
    rows, total = await repo.list_paginated(
        db_session, seed["user"].id,
        q=None, category_id=None, location_id=seed["loc"].id, tag_ids=None,
        page=1, per_page=10,
    )
    assert {r.name for r in rows} == {"apple"}


async def test_filter_tags_any_match(db_session, seed):
    rows, total = await repo.list_paginated(
        db_session, seed["user"].id,
        q=None, category_id=None, location_id=None, tag_ids=[seed["t1"].id],
        page=1, per_page=10,
    )
    assert {r.name for r in rows} == {"apple", "cherry"}


async def test_pagination(db_session, seed):
    rows1, total = await repo.list_paginated(
        db_session, seed["user"].id,
        q=None, category_id=None, location_id=None, tag_ids=None,
        page=1, per_page=2,
    )
    assert total == 3
    assert len(rows1) == 2
    rows2, _ = await repo.list_paginated(
        db_session, seed["user"].id,
        q=None, category_id=None, location_id=None, tag_ids=None,
        page=2, per_page=2,
    )
    assert len(rows2) == 1


async def test_soft_delete(db_session, seed):
    rows_before, total_before = await repo.list_paginated(
        db_session, seed["user"].id,
        q=None, category_id=None, location_id=None, tag_ids=None,
        page=1, per_page=10,
    )
    target = next(r for r in rows_before if r.name == "apple")
    await repo.soft_delete(db_session, target)
    rows_after, total_after = await repo.list_paginated(
        db_session, seed["user"].id,
        q=None, category_id=None, location_id=None, tag_ids=None,
        page=1, per_page=10,
    )
    assert total_after == total_before - 1
    assert "apple" not in {r.name for r in rows_after}
