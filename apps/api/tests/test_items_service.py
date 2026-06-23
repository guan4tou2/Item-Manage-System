import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models import Tag, User
from app.repositories import tags_repository
from app.schemas import item as item_schemas
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


async def test_create_with_tag_created_after_lookup_reuses_existing_tag(
    db_session, test_engine, two_users, monkeypatch
):
    u = two_users[0]
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    original_get_by_name = tags_repository.get_by_name
    inserted = False

    async def racing_get_by_name(session, owner_id, name):
        nonlocal inserted
        existing = await original_get_by_name(session, owner_id, name)
        if existing is None and not inserted:
            inserted = True
            async with maker() as other_session:
                other_session.add(Tag(owner_id=owner_id, name=name))
                await other_session.commit()
        return existing

    monkeypatch.setattr(tags_repository, "get_by_name", racing_get_by_name)

    result = await items_service.create_item(
        db_session,
        u.id,
        ItemCreate(name="race-safe", tag_names=["Office"]),
    )

    assert [tag.name for tag in result.tags] == ["office"]


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


async def test_bulk_update_appends_tags(db_session, two_users):
    u = two_users[0]
    first = await items_service.create_item(
        db_session, u.id, ItemCreate(name="first", tag_names=["old"])
    )
    second = await items_service.create_item(
        db_session, u.id, ItemCreate(name="second", tag_names=["keep"])
    )

    result = await items_service.bulk_update_items(
        db_session,
        u.id,
        item_schemas.ItemBulkUpdate(
            item_ids=[first.id, second.id],
            tag_names=["new"],
            tag_mode="append",
        ),
    )

    assert result.updated == 2
    updated_first = await items_service.get_item(db_session, u.id, first.id)
    updated_second = await items_service.get_item(db_session, u.id, second.id)
    assert sorted(tag.name for tag in updated_first.tags) == ["new", "old"]
    assert sorted(tag.name for tag in updated_second.tags) == ["keep", "new"]


async def test_bulk_update_cross_owner_fails_before_mutating(db_session, two_users):
    owner, other = two_users
    owned = await items_service.create_item(
        db_session, owner.id, ItemCreate(name="owned", tag_names=["keep"])
    )
    other_item = await items_service.create_item(
        db_session, other.id, ItemCreate(name="other")
    )

    with pytest.raises(HTTPException) as e:
        await items_service.bulk_update_items(
            db_session,
            owner.id,
            item_schemas.ItemBulkUpdate(
                item_ids=[owned.id, other_item.id],
                tag_names=["changed"],
            ),
        )

    assert e.value.status_code == 404
    unchanged = await items_service.get_item(db_session, owner.id, owned.id)
    assert [tag.name for tag in unchanged.tags] == ["keep"]


async def test_bulk_delete_cross_owner_fails_before_mutating(db_session, two_users):
    owner, other = two_users
    owned = await items_service.create_item(db_session, owner.id, ItemCreate(name="owned"))
    other_item = await items_service.create_item(db_session, other.id, ItemCreate(name="other"))

    with pytest.raises(HTTPException) as e:
        await items_service.bulk_delete_items(
            db_session,
            owner.id,
            item_schemas.ItemBulkDelete(item_ids=[owned.id, other_item.id]),
        )

    assert e.value.status_code == 404
    still_there = await items_service.get_item(db_session, owner.id, owned.id)
    assert still_there.id == owned.id
