import uuid
import pytest

from app.models import Category, Item, Location, Tag, User


@pytest.fixture
async def make_user(db_session):
    async def _make(username: str = "smoke") -> User:
        user = User(
            email=f"{username}@t.io", username=username,
            password_hash="x", is_active=True, is_admin=False,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user
    return _make


async def test_item_roundtrip(db_session, make_user):
    user = await make_user()
    item = Item(owner_id=user.id, name="hammer")
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    assert isinstance(item.id, uuid.UUID)
    assert item.quantity == 1
    assert item.is_deleted is False


async def test_category_tag_location_roundtrip(db_session, make_user):
    user = await make_user("smoke2")
    cat = Category(owner_id=user.id, name="tools")
    loc = Location(owner_id=user.id, floor="1F", room="garage")
    tag = Tag(owner_id=user.id, name="sharp")
    db_session.add_all([cat, loc, tag])
    await db_session.commit()
    item = Item(owner_id=user.id, name="saw", category=cat, location=loc, tags=[tag])
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item, ["category", "location", "tags"])
    assert item.category.name == "tools"
    assert item.location.floor == "1F"
    assert [t.name for t in item.tags] == ["sharp"]
