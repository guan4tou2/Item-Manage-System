import pytest
from fastapi import HTTPException

from app.models import User
from app.schemas.item import ItemCreate, ItemUpdate
from app.services import items_service


@pytest.fixture
async def two_users(db_session):
    users = []
    for i in range(2):
        u = User(email=f"u{i}@t.io", username=f"u{i}", password_hash="x",
                 is_active=True, is_admin=False)
        db_session.add(u)
        await db_session.commit()
        await db_session.refresh(u)
        users.append(u)
    return users


async def test_create_with_new_tags_autocreates(db_session, two_users):
    u = two_users[0]
    result = await items_service.create_item(
        db_session, u.id,
        ItemCreate(name="hammer", tag_names=["Tools", "heavy", "TOOLS"]),
    )
    assert result.name == "hammer"
    assert sorted(t.name for t in result.tags) == ["heavy", "tools"]


async def test_create_with_missing_category_returns_422(db_session, two_users):
    u = two_users[0]
    with pytest.raises(HTTPException) as e:
        await items_service.create_item(
            db_session, u.id,
            ItemCreate(name="x", category_id=999),
        )
    assert e.value.status_code == 422


async def test_get_item_other_user_returns_404(db_session, two_users):
    a, b = two_users
    created = await items_service.create_item(
        db_session, a.id, ItemCreate(name="only a")
    )
    with pytest.raises(HTTPException) as e:
        await items_service.get_item(db_session, b.id, created.id)
    assert e.value.status_code == 404


async def test_update_tag_names_replaces(db_session, two_users):
    u = two_users[0]
    created = await items_service.create_item(
        db_session, u.id, ItemCreate(name="x", tag_names=["old1", "old2"])
    )
    updated = await items_service.update_item(
        db_session, u.id, created.id,
        ItemUpdate(tag_names=["new1"]),
    )
    assert [t.name for t in updated.tags] == ["new1"]


async def test_update_tag_names_empty_clears(db_session, two_users):
    u = two_users[0]
    created = await items_service.create_item(
        db_session, u.id, ItemCreate(name="x", tag_names=["a", "b"])
    )
    updated = await items_service.update_item(
        db_session, u.id, created.id, ItemUpdate(tag_names=[])
    )
    assert updated.tags == []


async def test_update_without_tag_names_preserves(db_session, two_users):
    u = two_users[0]
    created = await items_service.create_item(
        db_session, u.id, ItemCreate(name="x", tag_names=["keep"])
    )
    updated = await items_service.update_item(
        db_session, u.id, created.id, ItemUpdate(name="y")
    )
    assert [t.name for t in updated.tags] == ["keep"]


async def test_delete_makes_item_unfindable(db_session, two_users):
    u = two_users[0]
    created = await items_service.create_item(db_session, u.id, ItemCreate(name="x"))
    await items_service.delete_item(db_session, u.id, created.id)
    with pytest.raises(HTTPException) as e:
        await items_service.get_item(db_session, u.id, created.id)
    assert e.value.status_code == 404
