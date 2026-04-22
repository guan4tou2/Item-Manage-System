# Items CRUD + Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement v2 Items management — CRUD, search, filter, tags, categories, locations — as a single coherent subproject.

**Architecture:** FastAPI async + SQLAlchemy + Alembic on the backend (routes → services → repositories → models). Next.js App Router + React Query + React Hook Form + Zod on the frontend. URL-driven filter state, server components for initial data, client components for interactivity. Every user sees only their own data (owner_id scoping).

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.x async, Alembic, pytest + httpx; Next.js 15, TypeScript, React Query 5, React Hook Form 7, Zod 3, shadcn/ui, Playwright, Vitest.

**Design spec:** `docs/superpowers/specs/2026-04-22-items-crud-search-design.md`

**Worktree:** `.claude/worktrees/items-crud-search` on branch `claude/items-crud-search`.

---

## File Structure (new + modified)

### Backend (apps/api/)

**New:**
- `app/models/item.py` — `Item` ORM model
- `app/models/category.py` — `Category` ORM model
- `app/models/location.py` — `Location` ORM model
- `app/models/tag.py` — `Tag` + `item_tags` association table
- `app/schemas/item.py` — `ItemCreate`, `ItemUpdate`, `ItemRead`, `ItemListResponse`, `ItemFilters`
- `app/schemas/category.py` — `CategoryCreate`, `CategoryUpdate`, `CategoryRead`, `CategoryTreeNode`
- `app/schemas/location.py` — `LocationCreate`, `LocationUpdate`, `LocationRead`
- `app/schemas/tag.py` — `TagRead`
- `app/repositories/items_repository.py`
- `app/repositories/categories_repository.py`
- `app/repositories/locations_repository.py`
- `app/repositories/tags_repository.py`
- `app/services/items_service.py`
- `app/services/categories_service.py`
- `app/services/locations_service.py`
- `app/services/tags_service.py`
- `app/routes/items.py`
- `app/routes/categories.py`
- `app/routes/locations.py`
- `app/routes/tags.py`
- `alembic/versions/0003_items_taxonomy.py`
- `tests/test_items_repository.py`
- `tests/test_items_service.py`
- `tests/test_items_routes.py`
- `tests/test_categories_routes.py`
- `tests/test_locations_routes.py`
- `tests/test_tags_routes.py`

**Modified:**
- `app/models/__init__.py` — export new models
- `app/main.py` — include new routers
- `packages/api-types/openapi.json` — regenerated
- `packages/api-types/src/index.ts` — regenerated

### Frontend (apps/web/)

**New:**
- `lib/api/items.ts`
- `lib/api/categories.ts`
- `lib/api/locations.ts`
- `lib/api/tags.ts`
- `lib/hooks/use-items.ts`
- `lib/hooks/use-categories.ts`
- `lib/hooks/use-locations.ts`
- `lib/hooks/use-tags.ts`
- `lib/items/filters.ts` — URL ↔ ItemFilters conversion
- `lib/items/filters.test.ts`
- `components/items/item-form.tsx` — shared create + edit form
- `components/items/item-form.test.tsx`
- `components/items/items-table.tsx` — desktop table
- `components/items/items-cards.tsx` — mobile cards
- `components/items/items-filter-panel.tsx`
- `components/items/category-tree-select.tsx`
- `components/items/tag-multi-select.tsx`
- `components/items/delete-item-dialog.tsx`
- `components/taxonomy/categories-panel.tsx`
- `components/taxonomy/locations-panel.tsx`
- `app/(app)/items/page.tsx` — list (replaces placeholder)
- `app/(app)/items/new/page.tsx`
- `app/(app)/items/[id]/page.tsx`
- `app/(app)/items/[id]/edit/page.tsx`
- `app/(app)/settings/taxonomy/page.tsx`
- `tests/items-crud.spec.ts` — Playwright E2E

**Modified:**
- `messages/zh-TW.json` — add `items.*`, `taxonomy.*`
- `messages/en.json` — same keys
- `components/shell/nav-items.ts` — no change needed (items already present)
- `docs/v2-roadmap.md` — mark #3 complete

---

## Task 1: Alembic migration 0003 — items, categories, locations, tags, item_tags

**Files:**
- Create: `apps/api/alembic/versions/0003_items_taxonomy.py`

- [ ] **Step 1: Write the migration file**

```python
"""items, categories, locations, tags

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-22 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("owner_id", "parent_id", "name", name="uq_categories_owner_parent_name"),
    )
    op.create_index("ix_categories_owner_id", "categories", ["owner_id"])

    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("floor", sa.String(length=50), nullable=False),
        sa.Column("room", sa.String(length=50), nullable=True),
        sa.Column("zone", sa.String(length=50), nullable=True),
    )
    op.create_index("ix_locations_owner_id", "locations", ["owner_id"])

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.UniqueConstraint("owner_id", "name", name="uq_tags_owner_name"),
    )
    op.create_index("ix_tags_owner_id", "tags", ["owner_id"])

    op.create_table(
        "items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity >= 0", name="ck_items_quantity_nonneg"),
    )
    op.create_index("ix_items_owner_id_is_deleted", "items", ["owner_id", "is_deleted"])

    op.create_table(
        "item_tags",
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("item_tags")
    op.drop_index("ix_items_owner_id_is_deleted", table_name="items")
    op.drop_table("items")
    op.drop_index("ix_tags_owner_id", table_name="tags")
    op.drop_table("tags")
    op.drop_index("ix_locations_owner_id", table_name="locations")
    op.drop_table("locations")
    op.drop_index("ix_categories_owner_id", table_name="categories")
    op.drop_table("categories")
```

- [ ] **Step 2: Run alembic upgrade head against a scratch SQLite to verify**

Run:
```bash
cd apps/api
DATABASE_URL="sqlite+aiosqlite:///tmp-mig.db" uv run alembic -c alembic.ini upgrade head
```
Expected: no errors; run `DATABASE_URL="sqlite+aiosqlite:///tmp-mig.db" uv run alembic -c alembic.ini downgrade base` and verify it reverses cleanly. Then `rm tmp-mig.db`.

- [ ] **Step 3: Commit**

```bash
git add apps/api/alembic/versions/0003_items_taxonomy.py
git commit -m "feat(api): add migration 0003 for items + taxonomy tables"
```

---

## Task 2: ORM models for Item, Category, Location, Tag

**Files:**
- Create: `apps/api/app/models/item.py`
- Create: `apps/api/app/models/category.py`
- Create: `apps/api/app/models/location.py`
- Create: `apps/api/app/models/tag.py`
- Modify: `apps/api/app/models/__init__.py`

- [ ] **Step 1: Write `category.py`**

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import GUID

if TYPE_CHECKING:
    from app.models.item import Item


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("owner_id", "parent_id", "name", name="uq_categories_owner_parent_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)

    parent: Mapped[Optional["Category"]] = relationship("Category", remote_side=[id], backref="children")
    items: Mapped[list["Item"]] = relationship("Item", back_populates="category")
```

- [ ] **Step 2: Write `location.py`**

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import GUID

if TYPE_CHECKING:
    from app.models.item import Item


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    floor: Mapped[str] = mapped_column(String(50), nullable=False)
    room: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    zone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    items: Mapped[list["Item"]] = relationship("Item", back_populates="location")
```

- [ ] **Step 3: Write `tag.py`**

```python
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Column, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import GUID

if TYPE_CHECKING:
    from app.models.item import Item


item_tags = Table(
    "item_tags",
    Base.metadata,
    Column("item_id", GUID(), ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("owner_id", "name", name="uq_tags_owner_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    items: Mapped[list["Item"]] = relationship("Item", secondary=item_tags, back_populates="tags")
```

- [ ] **Step 4: Write `item.py`**

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import GUID


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_items_quantity_nonneg"),
    )

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"), default=1)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="items")  # noqa: F821
    location: Mapped[Optional["Location"]] = relationship("Location", back_populates="items")  # noqa: F821
    tags: Mapped[list["Tag"]] = relationship("Tag", secondary="item_tags", back_populates="items")  # noqa: F821
```

- [ ] **Step 5: Update `app/models/__init__.py`**

Replace file contents with:
```python
from app.models.category import Category
from app.models.item import Item
from app.models.location import Location
from app.models.tag import Tag, item_tags
from app.models.user import User

__all__ = ["User", "Item", "Category", "Location", "Tag", "item_tags"]
```

- [ ] **Step 6: Add a smoke test for model creation**

Create `apps/api/tests/test_models_smoke.py`:
```python
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
    await db_session.refresh(item)
    assert item.category.name == "tools"
    assert item.location.floor == "1F"
    assert [t.name for t in item.tags] == ["sharp"]
```

- [ ] **Step 7: Run the smoke tests**

Run:
```bash
cd apps/api
uv run pytest tests/test_models_smoke.py -v
```
Expected: 2 passed.

- [ ] **Step 8: Commit**

```bash
git add apps/api/app/models/ apps/api/tests/test_models_smoke.py
git commit -m "feat(api): add Item/Category/Location/Tag ORM models"
```

---

## Task 3: Categories — schemas + repository + service + routes

**Files:**
- Create: `apps/api/app/schemas/category.py`
- Create: `apps/api/app/repositories/categories_repository.py`
- Create: `apps/api/app/services/categories_service.py`
- Create: `apps/api/app/routes/categories.py`
- Create: `apps/api/tests/test_categories_routes.py`
- Modify: `apps/api/app/main.py` — include router

- [ ] **Step 1: Write schemas (`schemas/category.py`)**

```python
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    parent_id: Optional[int] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    parent_id: Optional[int] = None

    model_config = ConfigDict(extra="forbid")


class CategoryRead(BaseModel):
    id: int
    name: str
    parent_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class CategoryTreeNode(CategoryRead):
    children: list["CategoryTreeNode"] = []


CategoryTreeNode.model_rebuild()
```

- [ ] **Step 2: Write repository (`repositories/categories_repository.py`)**

```python
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category


async def list_for_owner(session: AsyncSession, owner_id: UUID) -> list[Category]:
    stmt = select(Category).where(Category.owner_id == owner_id).order_by(Category.id)
    return list((await session.execute(stmt)).scalars().all())


async def get_owned(session: AsyncSession, owner_id: UUID, category_id: int) -> Category | None:
    stmt = select(Category).where(Category.id == category_id, Category.owner_id == owner_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def create(session: AsyncSession, owner_id: UUID, name: str, parent_id: int | None) -> Category:
    cat = Category(owner_id=owner_id, name=name, parent_id=parent_id)
    session.add(cat)
    await session.commit()
    await session.refresh(cat)
    return cat


async def update(session: AsyncSession, cat: Category, **fields) -> Category:
    for k, v in fields.items():
        setattr(cat, k, v)
    await session.commit()
    await session.refresh(cat)
    return cat


async def delete(session: AsyncSession, cat: Category) -> None:
    await session.delete(cat)
    await session.commit()
```

- [ ] **Step 3: Write service (`services/categories_service.py`)**

```python
from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.repositories import categories_repository as repo
from app.schemas.category import CategoryCreate, CategoryTreeNode, CategoryUpdate


def _build_tree(categories: list[Category]) -> list[CategoryTreeNode]:
    by_id: dict[int, CategoryTreeNode] = {
        c.id: CategoryTreeNode(id=c.id, name=c.name, parent_id=c.parent_id, children=[])
        for c in categories
    }
    roots: list[CategoryTreeNode] = []
    for c in categories:
        node = by_id[c.id]
        if c.parent_id is None or c.parent_id not in by_id:
            roots.append(node)
        else:
            by_id[c.parent_id].children.append(node)
    return roots


async def list_tree(session: AsyncSession, owner_id: UUID) -> list[CategoryTreeNode]:
    cats = await repo.list_for_owner(session, owner_id)
    return _build_tree(cats)


async def _validate_parent(session: AsyncSession, owner_id: UUID, parent_id: int | None, self_id: int | None = None) -> None:
    if parent_id is None:
        return
    if self_id is not None and parent_id == self_id:
        raise HTTPException(status_code=422, detail="category parent would create cycle")
    parent = await repo.get_owned(session, owner_id, parent_id)
    if parent is None:
        raise HTTPException(status_code=422, detail="parent_id not found")
    if self_id is not None:
        cursor = parent
        while cursor is not None and cursor.parent_id is not None:
            if cursor.parent_id == self_id:
                raise HTTPException(status_code=422, detail="category parent would create cycle")
            cursor = await repo.get_owned(session, owner_id, cursor.parent_id)


async def create(session: AsyncSession, owner_id: UUID, body: CategoryCreate) -> Category:
    await _validate_parent(session, owner_id, body.parent_id)
    return await repo.create(session, owner_id, body.name, body.parent_id)


async def update(session: AsyncSession, owner_id: UUID, category_id: int, body: CategoryUpdate) -> Category:
    cat = await repo.get_owned(session, owner_id, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="category not found")
    fields = body.model_dump(exclude_unset=True)
    if "parent_id" in fields:
        await _validate_parent(session, owner_id, fields["parent_id"], self_id=cat.id)
    return await repo.update(session, cat, **fields)


async def delete(session: AsyncSession, owner_id: UUID, category_id: int) -> None:
    cat = await repo.get_owned(session, owner_id, category_id)
    if cat is None:
        raise HTTPException(status_code=404, detail="category not found")
    await repo.delete(session, cat)
```

- [ ] **Step 4: Write routes (`routes/categories.py`)**

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryRead, CategoryTreeNode, CategoryUpdate
from app.services import categories_service

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryTreeNode])
async def list_categories(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[CategoryTreeNode]:
    return await categories_service.list_tree(session, user.id)


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CategoryRead:
    cat = await categories_service.create(session, user.id, body)
    return CategoryRead.model_validate(cat)


@router.patch("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: int,
    body: CategoryUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CategoryRead:
    cat = await categories_service.update(session, user.id, category_id, body)
    return CategoryRead.model_validate(cat)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    await categories_service.delete(session, user.id, category_id)
```

- [ ] **Step 5: Wire router into `app/main.py`**

In `app/main.py`, add import and include:
```python
from app.routes import auth, categories, health, users  # modified
# …
    app.include_router(categories.router)  # add after users.router
```

- [ ] **Step 6: Write routes tests (`tests/test_categories_routes.py`)**

```python
import pytest


@pytest.fixture
async def auth_headers(client):
    await client.post("/api/auth/register", json={
        "email": "cat@t.io", "username": "cat_user", "password": "secret1234",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "cat_user", "password": "secret1234",
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestCategories:
    async def test_list_empty(self, client, auth_headers):
        resp = await client.get("/api/categories", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_and_list_tree(self, client, auth_headers):
        parent = await client.post("/api/categories", headers=auth_headers, json={"name": "tools"})
        assert parent.status_code == 201
        child = await client.post("/api/categories", headers=auth_headers,
                                  json={"name": "hammers", "parent_id": parent.json()["id"]})
        assert child.status_code == 201
        resp = await client.get("/api/categories", headers=auth_headers)
        tree = resp.json()
        assert len(tree) == 1
        assert tree[0]["name"] == "tools"
        assert len(tree[0]["children"]) == 1
        assert tree[0]["children"][0]["name"] == "hammers"

    async def test_invalid_parent_returns_422(self, client, auth_headers):
        resp = await client.post("/api/categories", headers=auth_headers,
                                 json={"name": "x", "parent_id": 9999})
        assert resp.status_code == 422

    async def test_update_name(self, client, auth_headers):
        created = await client.post("/api/categories", headers=auth_headers, json={"name": "a"})
        cid = created.json()["id"]
        resp = await client.patch(f"/api/categories/{cid}", headers=auth_headers, json={"name": "b"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "b"

    async def test_update_cycle_rejected(self, client, auth_headers):
        parent = (await client.post("/api/categories", headers=auth_headers, json={"name": "p"})).json()
        child = (await client.post("/api/categories", headers=auth_headers,
                                   json={"name": "c", "parent_id": parent["id"]})).json()
        resp = await client.patch(f"/api/categories/{parent['id']}", headers=auth_headers,
                                  json={"parent_id": child["id"]})
        assert resp.status_code == 422

    async def test_delete_clears_children_parent(self, client, auth_headers):
        parent = (await client.post("/api/categories", headers=auth_headers, json={"name": "p"})).json()
        child = (await client.post("/api/categories", headers=auth_headers,
                                   json={"name": "c", "parent_id": parent["id"]})).json()
        del_resp = await client.delete(f"/api/categories/{parent['id']}", headers=auth_headers)
        assert del_resp.status_code == 204
        tree = (await client.get("/api/categories", headers=auth_headers)).json()
        names = [n["name"] for n in tree]
        assert "c" in names
        assert "p" not in names

    async def test_unauthenticated_401(self, client):
        assert (await client.get("/api/categories")).status_code == 401

    async def test_other_user_cannot_access(self, client):
        await client.post("/api/auth/register", json={
            "email": "a@t.io", "username": "user_a", "password": "secret1234"})
        tok_a = (await client.post("/api/auth/login", json={
            "username": "user_a", "password": "secret1234"})).json()["access_token"]
        await client.post("/api/auth/register", json={
            "email": "b@t.io", "username": "user_b", "password": "secret1234"})
        tok_b = (await client.post("/api/auth/login", json={
            "username": "user_b", "password": "secret1234"})).json()["access_token"]
        created = await client.post(
            "/api/categories",
            headers={"Authorization": f"Bearer {tok_a}"},
            json={"name": "only-a"},
        )
        cid = created.json()["id"]
        resp = await client.patch(
            f"/api/categories/{cid}",
            headers={"Authorization": f"Bearer {tok_b}"},
            json={"name": "hijacked"},
        )
        assert resp.status_code == 404
```

- [ ] **Step 7: Run the tests**

```bash
cd apps/api
uv run pytest tests/test_categories_routes.py -v
```
Expected: all pass. If import errors, recheck `app/repositories/__init__.py` — not strictly needed since we use fully qualified imports, but ensure `categories_repository` can be resolved.

- [ ] **Step 8: Commit**

```bash
git add apps/api/app/schemas/category.py apps/api/app/repositories/categories_repository.py \
        apps/api/app/services/categories_service.py apps/api/app/routes/categories.py \
        apps/api/app/main.py apps/api/tests/test_categories_routes.py
git commit -m "feat(api): add categories CRUD with tree listing + cycle detection"
```

---

## Task 4: Locations — schemas + repository + service + routes

**Files:**
- Create: `apps/api/app/schemas/location.py`
- Create: `apps/api/app/repositories/locations_repository.py`
- Create: `apps/api/app/services/locations_service.py`
- Create: `apps/api/app/routes/locations.py`
- Create: `apps/api/tests/test_locations_routes.py`
- Modify: `apps/api/app/main.py`

- [ ] **Step 1: Schemas**

```python
# apps/api/app/schemas/location.py
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LocationCreate(BaseModel):
    floor: str = Field(min_length=1, max_length=50)
    room: Optional[str] = Field(default=None, max_length=50)
    zone: Optional[str] = Field(default=None, max_length=50)


class LocationUpdate(BaseModel):
    floor: Optional[str] = Field(default=None, min_length=1, max_length=50)
    room: Optional[str] = Field(default=None, max_length=50)
    zone: Optional[str] = Field(default=None, max_length=50)

    model_config = ConfigDict(extra="forbid")


class LocationRead(BaseModel):
    id: int
    floor: str
    room: Optional[str]
    zone: Optional[str]

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 2: Repository**

```python
# apps/api/app/repositories/locations_repository.py
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location


async def list_for_owner(session: AsyncSession, owner_id: UUID) -> list[Location]:
    stmt = (
        select(Location)
        .where(Location.owner_id == owner_id)
        .order_by(Location.floor, Location.room, Location.zone)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_owned(session: AsyncSession, owner_id: UUID, location_id: int) -> Location | None:
    stmt = select(Location).where(Location.id == location_id, Location.owner_id == owner_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def create(session: AsyncSession, owner_id: UUID, **fields) -> Location:
    loc = Location(owner_id=owner_id, **fields)
    session.add(loc)
    await session.commit()
    await session.refresh(loc)
    return loc


async def update(session: AsyncSession, loc: Location, **fields) -> Location:
    for k, v in fields.items():
        setattr(loc, k, v)
    await session.commit()
    await session.refresh(loc)
    return loc


async def delete(session: AsyncSession, loc: Location) -> None:
    await session.delete(loc)
    await session.commit()
```

- [ ] **Step 3: Service**

```python
# apps/api/app/services/locations_service.py
from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.location import Location
from app.repositories import locations_repository as repo
from app.schemas.location import LocationCreate, LocationUpdate


async def list_all(session: AsyncSession, owner_id: UUID) -> list[Location]:
    return await repo.list_for_owner(session, owner_id)


async def create(session: AsyncSession, owner_id: UUID, body: LocationCreate) -> Location:
    return await repo.create(session, owner_id, **body.model_dump())


async def update(session: AsyncSession, owner_id: UUID, location_id: int, body: LocationUpdate) -> Location:
    loc = await repo.get_owned(session, owner_id, location_id)
    if loc is None:
        raise HTTPException(status_code=404, detail="location not found")
    return await repo.update(session, loc, **body.model_dump(exclude_unset=True))


async def delete(session: AsyncSession, owner_id: UUID, location_id: int) -> None:
    loc = await repo.get_owned(session, owner_id, location_id)
    if loc is None:
        raise HTTPException(status_code=404, detail="location not found")
    await repo.delete(session, loc)
```

- [ ] **Step 4: Routes**

```python
# apps/api/app/routes/locations.py
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.location import LocationCreate, LocationRead, LocationUpdate
from app.services import locations_service

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.get("", response_model=list[LocationRead])
async def list_locations(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[LocationRead]:
    locs = await locations_service.list_all(session, user.id)
    return [LocationRead.model_validate(loc) for loc in locs]


@router.post("", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
async def create_location(
    body: LocationCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> LocationRead:
    loc = await locations_service.create(session, user.id, body)
    return LocationRead.model_validate(loc)


@router.patch("/{location_id}", response_model=LocationRead)
async def update_location(
    location_id: int,
    body: LocationUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> LocationRead:
    loc = await locations_service.update(session, user.id, location_id, body)
    return LocationRead.model_validate(loc)


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    await locations_service.delete(session, user.id, location_id)
```

- [ ] **Step 5: Wire in `app/main.py`**

Add `locations` to imports + `app.include_router(locations.router)`.

- [ ] **Step 6: Tests (`tests/test_locations_routes.py`)**

```python
import pytest


@pytest.fixture
async def auth_headers(client):
    await client.post("/api/auth/register", json={
        "email": "loc@t.io", "username": "loc_user", "password": "secret1234",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "loc_user", "password": "secret1234",
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestLocations:
    async def test_list_empty(self, client, auth_headers):
        resp = await client.get("/api/locations", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_minimal(self, client, auth_headers):
        resp = await client.post("/api/locations", headers=auth_headers,
                                 json={"floor": "1F"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["floor"] == "1F"
        assert body["room"] is None
        assert body["zone"] is None

    async def test_create_full(self, client, auth_headers):
        resp = await client.post("/api/locations", headers=auth_headers,
                                 json={"floor": "1F", "room": "kitchen", "zone": "pantry"})
        assert resp.status_code == 201

    async def test_update(self, client, auth_headers):
        created = await client.post("/api/locations", headers=auth_headers, json={"floor": "1F"})
        lid = created.json()["id"]
        resp = await client.patch(f"/api/locations/{lid}", headers=auth_headers, json={"room": "den"})
        assert resp.status_code == 200
        assert resp.json()["room"] == "den"

    async def test_delete(self, client, auth_headers):
        created = await client.post("/api/locations", headers=auth_headers, json={"floor": "1F"})
        lid = created.json()["id"]
        resp = await client.delete(f"/api/locations/{lid}", headers=auth_headers)
        assert resp.status_code == 204
        resp2 = await client.patch(f"/api/locations/{lid}", headers=auth_headers, json={"room": "x"})
        assert resp2.status_code == 404

    async def test_validation_empty_floor(self, client, auth_headers):
        resp = await client.post("/api/locations", headers=auth_headers, json={"floor": ""})
        assert resp.status_code == 422

    async def test_unauthenticated_401(self, client):
        assert (await client.get("/api/locations")).status_code == 401
```

- [ ] **Step 7: Run tests**

```bash
cd apps/api
uv run pytest tests/test_locations_routes.py -v
```
Expected: 7 passed.

- [ ] **Step 8: Commit**

```bash
git add apps/api/app/schemas/location.py apps/api/app/repositories/locations_repository.py \
        apps/api/app/services/locations_service.py apps/api/app/routes/locations.py \
        apps/api/app/main.py apps/api/tests/test_locations_routes.py
git commit -m "feat(api): add locations CRUD"
```

---

## Task 5: Tags — schemas + repository + service + routes

Tags are auto-created on item writes, so the public API is read-only (autocomplete + listing).

**Files:**
- Create: `apps/api/app/schemas/tag.py`
- Create: `apps/api/app/repositories/tags_repository.py`
- Create: `apps/api/app/services/tags_service.py`
- Create: `apps/api/app/routes/tags.py`
- Create: `apps/api/tests/test_tags_routes.py`
- Modify: `apps/api/app/main.py`

- [ ] **Step 1: Schemas**

```python
# apps/api/app/schemas/tag.py
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TagRead(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 2: Repository**

```python
# apps/api/app/repositories/tags_repository.py
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag


def normalize(name: str) -> str:
    return name.strip().lower()


async def list_for_owner(session: AsyncSession, owner_id: UUID, q: str | None = None) -> list[Tag]:
    stmt = select(Tag).where(Tag.owner_id == owner_id).order_by(Tag.name)
    if q:
        needle = normalize(q)
        stmt = stmt.where(Tag.name.ilike(f"{needle}%"))
    return list((await session.execute(stmt)).scalars().all())


async def get_by_name(session: AsyncSession, owner_id: UUID, name: str) -> Tag | None:
    stmt = select(Tag).where(Tag.owner_id == owner_id, Tag.name == normalize(name))
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_or_create_many(
    session: AsyncSession, owner_id: UUID, names: list[str]
) -> list[Tag]:
    result: list[Tag] = []
    seen: set[str] = set()
    for raw in names:
        n = normalize(raw)
        if not n or n in seen:
            continue
        seen.add(n)
        existing = await get_by_name(session, owner_id, n)
        if existing:
            result.append(existing)
        else:
            tag = Tag(owner_id=owner_id, name=n)
            session.add(tag)
            await session.flush()
            result.append(tag)
    return result
```

- [ ] **Step 3: Service**

```python
# apps/api/app/services/tags_service.py
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag
from app.repositories import tags_repository as repo


async def list_tags(session: AsyncSession, owner_id: UUID, q: str | None) -> list[Tag]:
    return await repo.list_for_owner(session, owner_id, q)
```

- [ ] **Step 4: Routes**

```python
# apps/api/app/routes/tags.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.tag import TagRead
from app.services import tags_service

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=list[TagRead])
async def list_tags(
    q: str | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[TagRead]:
    tags = await tags_service.list_tags(session, user.id, q)
    return [TagRead.model_validate(t) for t in tags]
```

- [ ] **Step 5: Wire in `app/main.py`**

Import `tags` and `app.include_router(tags.router)`.

- [ ] **Step 6: Tests (`tests/test_tags_routes.py`)**

Tags are auto-created via item creation, but we can test the list endpoint by seeding Tag rows directly in the DB session.

```python
import pytest

from app.models.tag import Tag


@pytest.fixture
async def auth_setup(client):
    await client.post("/api/auth/register", json={
        "email": "tag@t.io", "username": "tag_user", "password": "secret1234",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "tag_user", "password": "secret1234",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestTagsList:
    async def test_empty(self, client, auth_setup):
        resp = await client.get("/api/tags", headers=auth_setup)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_unauthenticated_401(self, client):
        assert (await client.get("/api/tags")).status_code == 401
```

Fuller behaviour (autocomplete, normalization) is exercised via items tests in Task 8.

- [ ] **Step 7: Run tests**

```bash
cd apps/api
uv run pytest tests/test_tags_routes.py -v
```
Expected: 2 passed.

- [ ] **Step 8: Commit**

```bash
git add apps/api/app/schemas/tag.py apps/api/app/repositories/tags_repository.py \
        apps/api/app/services/tags_service.py apps/api/app/routes/tags.py \
        apps/api/app/main.py apps/api/tests/test_tags_routes.py
git commit -m "feat(api): add read-only tags listing with owner scoping"
```

---

## Task 6: Items schemas + repository (list with filters, CRUD primitives)

**Files:**
- Create: `apps/api/app/schemas/item.py`
- Create: `apps/api/app/repositories/items_repository.py`
- Create: `apps/api/tests/test_items_repository.py`

- [ ] **Step 1: Schemas**

```python
# apps/api/app/schemas/item.py
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.category import CategoryRead
from app.schemas.location import LocationRead
from app.schemas.tag import TagRead


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    quantity: int = Field(default=1, ge=0)
    notes: Optional[str] = None
    tag_names: list[str] = Field(default_factory=list)


class ItemUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    quantity: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None
    tag_names: Optional[list[str]] = None

    model_config = ConfigDict(extra="forbid")


class ItemRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    quantity: int
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    category: Optional[CategoryRead]
    location: Optional[LocationRead]
    tags: list[TagRead]

    model_config = ConfigDict(from_attributes=True)


class ItemListResponse(BaseModel):
    items: list[ItemRead]
    total: int
    page: int
    per_page: int
```

- [ ] **Step 2: Repository**

```python
# apps/api/app/repositories/items_repository.py
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.item import Item
from app.models.tag import item_tags


def _base_query(owner_id: UUID):
    return select(Item).where(Item.owner_id == owner_id, Item.is_deleted.is_(False))


async def get_owned(session: AsyncSession, owner_id: UUID, item_id: UUID) -> Item | None:
    stmt = (
        _base_query(owner_id)
        .where(Item.id == item_id)
        .options(selectinload(Item.tags), selectinload(Item.category), selectinload(Item.location))
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_paginated(
    session: AsyncSession,
    owner_id: UUID,
    *,
    q: str | None,
    category_id: int | None,
    location_id: int | None,
    tag_ids: list[int] | None,
    page: int,
    per_page: int,
) -> tuple[list[Item], int]:
    base = _base_query(owner_id)

    if q:
        like = f"%{q}%"
        base = base.where(or_(Item.name.ilike(like), Item.description.ilike(like)))
    if category_id is not None:
        base = base.where(Item.category_id == category_id)
    if location_id is not None:
        base = base.where(Item.location_id == location_id)
    if tag_ids:
        base = base.where(
            Item.id.in_(
                select(item_tags.c.item_id).where(item_tags.c.tag_id.in_(tag_ids))
            )
        )

    total_stmt = select(func.count()).select_from(base.subquery())
    total = (await session.execute(total_stmt)).scalar_one()

    stmt = (
        base.order_by(Item.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .options(selectinload(Item.tags), selectinload(Item.category), selectinload(Item.location))
    )
    rows = list((await session.execute(stmt)).scalars().all())
    return rows, total


async def create(session: AsyncSession, item: Item) -> Item:
    session.add(item)
    await session.commit()
    stmt = (
        select(Item)
        .where(Item.id == item.id)
        .options(selectinload(Item.tags), selectinload(Item.category), selectinload(Item.location))
    )
    return (await session.execute(stmt)).scalar_one()


async def save(session: AsyncSession, item: Item) -> Item:
    await session.commit()
    stmt = (
        select(Item)
        .where(Item.id == item.id)
        .options(selectinload(Item.tags), selectinload(Item.category), selectinload(Item.location))
    )
    return (await session.execute(stmt)).scalar_one()


async def soft_delete(session: AsyncSession, item: Item) -> None:
    item.is_deleted = True
    await session.commit()
```

- [ ] **Step 3: Repository tests**

```python
# apps/api/tests/test_items_repository.py
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
```

- [ ] **Step 4: Run tests**

```bash
cd apps/api
uv run pytest tests/test_items_repository.py -v
```
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/schemas/item.py apps/api/app/repositories/items_repository.py apps/api/tests/test_items_repository.py
git commit -m "feat(api): add items schemas + repository with search/filter/pagination"
```

---

## Task 7: Items service (authorization + tag handling)

**Files:**
- Create: `apps/api/app/services/items_service.py`
- Create: `apps/api/tests/test_items_service.py`

- [ ] **Step 1: Service**

```python
# apps/api/app/services/items_service.py
from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item
from app.repositories import categories_repository, items_repository, locations_repository, tags_repository
from app.schemas.item import ItemCreate, ItemListResponse, ItemRead, ItemUpdate


async def _validate_refs(session: AsyncSession, owner_id: UUID, category_id: int | None, location_id: int | None) -> None:
    if category_id is not None:
        if await categories_repository.get_owned(session, owner_id, category_id) is None:
            raise HTTPException(status_code=422, detail="category_id not found")
    if location_id is not None:
        if await locations_repository.get_owned(session, owner_id, location_id) is None:
            raise HTTPException(status_code=422, detail="location_id not found")


async def list_items(
    session: AsyncSession,
    owner_id: UUID,
    *,
    q: str | None,
    category_id: int | None,
    location_id: int | None,
    tag_ids: list[int] | None,
    page: int,
    per_page: int,
) -> ItemListResponse:
    rows, total = await items_repository.list_paginated(
        session, owner_id,
        q=q, category_id=category_id, location_id=location_id, tag_ids=tag_ids,
        page=page, per_page=per_page,
    )
    return ItemListResponse(
        items=[ItemRead.model_validate(r) for r in rows],
        total=total, page=page, per_page=per_page,
    )


async def get_item(session: AsyncSession, owner_id: UUID, item_id: UUID) -> ItemRead:
    item = await items_repository.get_owned(session, owner_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return ItemRead.model_validate(item)


async def create_item(session: AsyncSession, owner_id: UUID, body: ItemCreate) -> ItemRead:
    await _validate_refs(session, owner_id, body.category_id, body.location_id)
    tags = await tags_repository.get_or_create_many(session, owner_id, body.tag_names)
    item = Item(
        owner_id=owner_id,
        name=body.name,
        description=body.description,
        category_id=body.category_id,
        location_id=body.location_id,
        quantity=body.quantity,
        notes=body.notes,
        tags=tags,
    )
    created = await items_repository.create(session, item)
    return ItemRead.model_validate(created)


async def update_item(session: AsyncSession, owner_id: UUID, item_id: UUID, body: ItemUpdate) -> ItemRead:
    item = await items_repository.get_owned(session, owner_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    fields = body.model_dump(exclude_unset=True)
    if "category_id" in fields or "location_id" in fields:
        await _validate_refs(
            session, owner_id,
            fields.get("category_id", item.category_id),
            fields.get("location_id", item.location_id),
        )
    if "tag_names" in fields:
        new_names = fields.pop("tag_names")
        item.tags = await tags_repository.get_or_create_many(session, owner_id, new_names or [])
    for k, v in fields.items():
        setattr(item, k, v)
    saved = await items_repository.save(session, item)
    return ItemRead.model_validate(saved)


async def delete_item(session: AsyncSession, owner_id: UUID, item_id: UUID) -> None:
    item = await items_repository.get_owned(session, owner_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    await items_repository.soft_delete(session, item)
```

- [ ] **Step 2: Service tests**

```python
# apps/api/tests/test_items_service.py
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.models import Category, Location, User
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
```

- [ ] **Step 3: Run tests**

```bash
cd apps/api
uv run pytest tests/test_items_service.py -v
```
Expected: 7 passed.

- [ ] **Step 4: Commit**

```bash
git add apps/api/app/services/items_service.py apps/api/tests/test_items_service.py
git commit -m "feat(api): add items service with auth + tag handling"
```

---

## Task 8: Items routes + integration tests

**Files:**
- Create: `apps/api/app/routes/items.py`
- Create: `apps/api/tests/test_items_routes.py`
- Modify: `apps/api/app/main.py`

- [ ] **Step 1: Routes**

```python
# apps/api/app/routes/items.py
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.item import ItemCreate, ItemListResponse, ItemRead, ItemUpdate
from app.services import items_service

router = APIRouter(prefix="/api/items", tags=["items"])


@router.get("", response_model=ItemListResponse)
async def list_items(
    q: str | None = None,
    category_id: int | None = None,
    location_id: int | None = None,
    tag_ids: list[int] | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ItemListResponse:
    return await items_service.list_items(
        session, user.id,
        q=q, category_id=category_id, location_id=location_id,
        tag_ids=tag_ids, page=page, per_page=per_page,
    )


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(
    body: ItemCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ItemRead:
    return await items_service.create_item(session, user.id, body)


@router.get("/{item_id}", response_model=ItemRead)
async def get_item(
    item_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ItemRead:
    return await items_service.get_item(session, user.id, item_id)


@router.patch("/{item_id}", response_model=ItemRead)
async def update_item(
    item_id: UUID,
    body: ItemUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ItemRead:
    return await items_service.update_item(session, user.id, item_id, body)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    await items_service.delete_item(session, user.id, item_id)
```

- [ ] **Step 2: Wire in `app/main.py`**

Import `items` and add `app.include_router(items.router)`.

Final state of `create_app`'s router list should be:
```python
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(locations.router)
app.include_router(tags.router)
app.include_router(items.router)
```

- [ ] **Step 3: Integration tests**

```python
# apps/api/tests/test_items_routes.py
import pytest


@pytest.fixture
async def auth_headers(client):
    await client.post("/api/auth/register", json={
        "email": "items@t.io", "username": "items_user", "password": "secret1234",
    })
    resp = await client.post("/api/auth/login", json={
        "username": "items_user", "password": "secret1234",
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestItemCreate:
    async def test_minimal(self, client, auth_headers):
        resp = await client.post("/api/items", headers=auth_headers, json={"name": "thing"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "thing"
        assert body["quantity"] == 1
        assert body["tags"] == []

    async def test_with_tags_autocreates(self, client, auth_headers):
        resp = await client.post(
            "/api/items", headers=auth_headers,
            json={"name": "x", "tag_names": ["a", "B", "a"]},
        )
        assert resp.status_code == 201
        assert sorted(t["name"] for t in resp.json()["tags"]) == ["a", "b"]
        tags = await client.get("/api/tags", headers=auth_headers)
        assert sorted(t["name"] for t in tags.json()) == ["a", "b"]

    async def test_missing_name_422(self, client, auth_headers):
        resp = await client.post("/api/items", headers=auth_headers, json={})
        assert resp.status_code == 422

    async def test_unauthenticated_401(self, client):
        resp = await client.post("/api/items", json={"name": "x"})
        assert resp.status_code == 401


class TestItemList:
    async def test_empty(self, client, auth_headers):
        resp = await client.get("/api/items", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body == {"items": [], "total": 0, "page": 1, "per_page": 20}

    async def test_search_q(self, client, auth_headers):
        await client.post("/api/items", headers=auth_headers, json={"name": "apple"})
        await client.post("/api/items", headers=auth_headers, json={"name": "banana"})
        resp = await client.get("/api/items?q=app", headers=auth_headers)
        assert [i["name"] for i in resp.json()["items"]] == ["apple"]

    async def test_filter_tags(self, client, auth_headers):
        await client.post("/api/items", headers=auth_headers, json={"name": "a", "tag_names": ["red"]})
        await client.post("/api/items", headers=auth_headers, json={"name": "b", "tag_names": ["blue"]})
        tags = (await client.get("/api/tags", headers=auth_headers)).json()
        red_id = next(t["id"] for t in tags if t["name"] == "red")
        resp = await client.get(f"/api/items?tag_ids={red_id}", headers=auth_headers)
        assert [i["name"] for i in resp.json()["items"]] == ["a"]

    async def test_pagination_metadata(self, client, auth_headers):
        for i in range(3):
            await client.post("/api/items", headers=auth_headers, json={"name": f"n{i}"})
        resp = await client.get("/api/items?per_page=2", headers=auth_headers)
        body = resp.json()
        assert body["total"] == 3
        assert body["page"] == 1
        assert body["per_page"] == 2
        assert len(body["items"]) == 2


class TestItemGet:
    async def test_not_found_404(self, client, auth_headers):
        resp = await client.get(
            "/api/items/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_other_user_404(self, client):
        await client.post("/api/auth/register", json={
            "email": "a@t.io", "username": "a", "password": "secret1234"})
        tok_a = (await client.post("/api/auth/login", json={
            "username": "a", "password": "secret1234"})).json()["access_token"]
        created = await client.post(
            "/api/items",
            headers={"Authorization": f"Bearer {tok_a}"},
            json={"name": "only a"},
        )
        item_id = created.json()["id"]
        await client.post("/api/auth/register", json={
            "email": "b@t.io", "username": "b", "password": "secret1234"})
        tok_b = (await client.post("/api/auth/login", json={
            "username": "b", "password": "secret1234"})).json()["access_token"]
        resp = await client.get(
            f"/api/items/{item_id}",
            headers={"Authorization": f"Bearer {tok_b}"},
        )
        assert resp.status_code == 404


class TestItemUpdate:
    async def test_patch_name(self, client, auth_headers):
        created = (await client.post(
            "/api/items", headers=auth_headers, json={"name": "old"}
        )).json()
        resp = await client.patch(
            f"/api/items/{created['id']}", headers=auth_headers,
            json={"name": "new"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "new"

    async def test_patch_replaces_tags(self, client, auth_headers):
        created = (await client.post(
            "/api/items", headers=auth_headers,
            json={"name": "x", "tag_names": ["a"]},
        )).json()
        resp = await client.patch(
            f"/api/items/{created['id']}", headers=auth_headers,
            json={"tag_names": ["b", "c"]},
        )
        assert sorted(t["name"] for t in resp.json()["tags"]) == ["b", "c"]


class TestItemDelete:
    async def test_soft_delete(self, client, auth_headers):
        created = (await client.post(
            "/api/items", headers=auth_headers, json={"name": "x"}
        )).json()
        resp = await client.delete(f"/api/items/{created['id']}", headers=auth_headers)
        assert resp.status_code == 204
        get_resp = await client.get(f"/api/items/{created['id']}", headers=auth_headers)
        assert get_resp.status_code == 404
        list_resp = await client.get("/api/items", headers=auth_headers)
        assert list_resp.json()["total"] == 0
```

- [ ] **Step 4: Run full API suite**

```bash
cd apps/api
uv run pytest -q
```
Expected: all tests green (previous suite + new ~50 items tests).

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/routes/items.py apps/api/app/main.py apps/api/tests/test_items_routes.py
git commit -m "feat(api): add items CRUD + search routes"
```

---

## Task 9: Regenerate OpenAPI + api-types

**Files:**
- Modify: `packages/api-types/openapi.json`
- Modify: `packages/api-types/src/index.ts`

- [ ] **Step 1: Dump fresh OpenAPI from the running API**

```bash
cd apps/api
uv run python -c "from app.main import create_app; import json; print(json.dumps(create_app().openapi(), indent=2))" > ../../packages/api-types/openapi.json
```
Verify the file size grew and contains `/api/items`, `/api/categories`, `/api/locations`, `/api/tags`.

- [ ] **Step 2: Regenerate TypeScript types**

```bash
cd packages/api-types
pnpm gen:types
```
Expected: `wrote <path>/src/index.ts`.

- [ ] **Step 3: Ensure web still typechecks**

```bash
cd apps/web
pnpm typecheck
```
Expected: no errors (existing pages don't use new types yet).

- [ ] **Step 4: Commit**

```bash
git add packages/api-types/openapi.json packages/api-types/src/index.ts
git commit -m "chore(api-types): regenerate for items/categories/locations/tags"
```

---

## Task 10: Web API client modules

**Files:**
- Create: `apps/web/lib/api/items.ts`
- Create: `apps/web/lib/api/categories.ts`
- Create: `apps/web/lib/api/locations.ts`
- Create: `apps/web/lib/api/tags.ts`

- [ ] **Step 1: Write `items.ts`**

```ts
// apps/web/lib/api/items.ts
import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

type ItemRead = paths["/api/items/{item_id}"]["get"]["responses"]["200"]["content"]["application/json"]
type ItemListResponse = paths["/api/items"]["get"]["responses"]["200"]["content"]["application/json"]
type ItemCreate = paths["/api/items"]["post"]["requestBody"]["content"]["application/json"]
type ItemUpdate = paths["/api/items/{item_id}"]["patch"]["requestBody"]["content"]["application/json"]

export type { ItemRead, ItemListResponse, ItemCreate, ItemUpdate }

export interface ItemFilters {
  q?: string
  categoryId?: number
  locationId?: number
  tagIds?: number[]
  page?: number
  perPage?: number
}

function buildQuery(filters: ItemFilters): string {
  const params = new URLSearchParams()
  if (filters.q) params.set("q", filters.q)
  if (filters.categoryId != null) params.set("category_id", String(filters.categoryId))
  if (filters.locationId != null) params.set("location_id", String(filters.locationId))
  if (filters.tagIds && filters.tagIds.length > 0) {
    for (const id of filters.tagIds) params.append("tag_ids", String(id))
  }
  if (filters.page != null) params.set("page", String(filters.page))
  if (filters.perPage != null) params.set("per_page", String(filters.perPage))
  const s = params.toString()
  return s ? `?${s}` : ""
}

export async function listItems(filters: ItemFilters, accessToken: string | null): Promise<ItemListResponse> {
  const res = await apiFetch(`/items${buildQuery(filters)}`, { accessToken })
  return (await res.json()) as ItemListResponse
}

export async function getItem(id: string, accessToken: string | null): Promise<ItemRead> {
  const res = await apiFetch(`/items/${id}`, { accessToken })
  return (await res.json()) as ItemRead
}

export async function createItem(body: ItemCreate, accessToken: string | null): Promise<ItemRead> {
  const res = await apiFetch("/items", {
    method: "POST", body: JSON.stringify(body), accessToken,
  })
  return (await res.json()) as ItemRead
}

export async function updateItem(id: string, body: ItemUpdate, accessToken: string | null): Promise<ItemRead> {
  const res = await apiFetch(`/items/${id}`, {
    method: "PATCH", body: JSON.stringify(body), accessToken,
  })
  return (await res.json()) as ItemRead
}

export async function deleteItem(id: string, accessToken: string | null): Promise<void> {
  await apiFetch(`/items/${id}`, { method: "DELETE", accessToken })
}
```

- [ ] **Step 2: Write `categories.ts`**

```ts
// apps/web/lib/api/categories.ts
import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

type CategoryTreeNode = paths["/api/categories"]["get"]["responses"]["200"]["content"]["application/json"][number]
type CategoryRead = paths["/api/categories"]["post"]["responses"]["201"]["content"]["application/json"]
type CategoryCreate = paths["/api/categories"]["post"]["requestBody"]["content"]["application/json"]
type CategoryUpdate = paths["/api/categories/{category_id}"]["patch"]["requestBody"]["content"]["application/json"]

export type { CategoryTreeNode, CategoryRead, CategoryCreate, CategoryUpdate }

export async function listCategories(accessToken: string | null): Promise<CategoryTreeNode[]> {
  const res = await apiFetch("/categories", { accessToken })
  return (await res.json()) as CategoryTreeNode[]
}

export async function createCategory(body: CategoryCreate, accessToken: string | null): Promise<CategoryRead> {
  const res = await apiFetch("/categories", {
    method: "POST", body: JSON.stringify(body), accessToken,
  })
  return (await res.json()) as CategoryRead
}

export async function updateCategory(id: number, body: CategoryUpdate, accessToken: string | null): Promise<CategoryRead> {
  const res = await apiFetch(`/categories/${id}`, {
    method: "PATCH", body: JSON.stringify(body), accessToken,
  })
  return (await res.json()) as CategoryRead
}

export async function deleteCategory(id: number, accessToken: string | null): Promise<void> {
  await apiFetch(`/categories/${id}`, { method: "DELETE", accessToken })
}
```

- [ ] **Step 3: Write `locations.ts`**

```ts
// apps/web/lib/api/locations.ts
import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

type LocationRead = paths["/api/locations"]["post"]["responses"]["201"]["content"]["application/json"]
type LocationCreate = paths["/api/locations"]["post"]["requestBody"]["content"]["application/json"]
type LocationUpdate = paths["/api/locations/{location_id}"]["patch"]["requestBody"]["content"]["application/json"]

export type { LocationRead, LocationCreate, LocationUpdate }

export async function listLocations(accessToken: string | null): Promise<LocationRead[]> {
  const res = await apiFetch("/locations", { accessToken })
  return (await res.json()) as LocationRead[]
}

export async function createLocation(body: LocationCreate, accessToken: string | null): Promise<LocationRead> {
  const res = await apiFetch("/locations", {
    method: "POST", body: JSON.stringify(body), accessToken,
  })
  return (await res.json()) as LocationRead
}

export async function updateLocation(id: number, body: LocationUpdate, accessToken: string | null): Promise<LocationRead> {
  const res = await apiFetch(`/locations/${id}`, {
    method: "PATCH", body: JSON.stringify(body), accessToken,
  })
  return (await res.json()) as LocationRead
}

export async function deleteLocation(id: number, accessToken: string | null): Promise<void> {
  await apiFetch(`/locations/${id}`, { method: "DELETE", accessToken })
}
```

- [ ] **Step 4: Write `tags.ts`**

```ts
// apps/web/lib/api/tags.ts
import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

type TagRead = paths["/api/tags"]["get"]["responses"]["200"]["content"]["application/json"][number]

export type { TagRead }

export async function listTags(q: string | undefined, accessToken: string | null): Promise<TagRead[]> {
  const qs = q ? `?q=${encodeURIComponent(q)}` : ""
  const res = await apiFetch(`/tags${qs}`, { accessToken })
  return (await res.json()) as TagRead[]
}
```

- [ ] **Step 5: Typecheck**

```bash
cd apps/web
pnpm typecheck
```
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add apps/web/lib/api/items.ts apps/web/lib/api/categories.ts \
        apps/web/lib/api/locations.ts apps/web/lib/api/tags.ts
git commit -m "feat(web): add typed API client modules for items/taxonomy/tags"
```

---

## Task 11: React Query hooks + URL filter helpers

**Files:**
- Create: `apps/web/lib/hooks/use-items.ts`
- Create: `apps/web/lib/hooks/use-categories.ts`
- Create: `apps/web/lib/hooks/use-locations.ts`
- Create: `apps/web/lib/hooks/use-tags.ts`
- Create: `apps/web/lib/items/filters.ts`
- Create: `apps/web/lib/items/filters.test.ts`

- [ ] **Step 1: Write `lib/items/filters.ts`**

```ts
// apps/web/lib/items/filters.ts
import type { ItemFilters } from "@/lib/api/items"

export function filtersFromSearchParams(params: URLSearchParams): ItemFilters {
  const f: ItemFilters = {}
  const q = params.get("q")
  if (q) f.q = q
  const cat = params.get("category")
  if (cat) f.categoryId = Number(cat)
  const loc = params.get("location")
  if (loc) f.locationId = Number(loc)
  const tags = params.get("tags")
  if (tags) {
    f.tagIds = tags.split(",").filter(Boolean).map(Number).filter((n) => !Number.isNaN(n))
    if (f.tagIds.length === 0) delete f.tagIds
  }
  const page = params.get("page")
  if (page) f.page = Math.max(1, Number(page))
  return f
}

export function filtersToSearchParams(f: ItemFilters): URLSearchParams {
  const p = new URLSearchParams()
  if (f.q) p.set("q", f.q)
  if (f.categoryId != null) p.set("category", String(f.categoryId))
  if (f.locationId != null) p.set("location", String(f.locationId))
  if (f.tagIds && f.tagIds.length > 0) p.set("tags", f.tagIds.join(","))
  if (f.page && f.page > 1) p.set("page", String(f.page))
  return p
}
```

- [ ] **Step 2: Write filters tests**

```ts
// apps/web/lib/items/filters.test.ts
import { describe, it, expect } from "vitest"
import { filtersFromSearchParams, filtersToSearchParams } from "./filters"

describe("filtersFromSearchParams", () => {
  it("parses all filters", () => {
    const p = new URLSearchParams("q=apple&category=1&location=2&tags=3,4&page=5")
    expect(filtersFromSearchParams(p)).toEqual({
      q: "apple", categoryId: 1, locationId: 2, tagIds: [3, 4], page: 5,
    })
  })

  it("returns empty object when nothing set", () => {
    expect(filtersFromSearchParams(new URLSearchParams())).toEqual({})
  })

  it("ignores invalid tag ids", () => {
    const p = new URLSearchParams("tags=1,abc,,2")
    expect(filtersFromSearchParams(p).tagIds).toEqual([1, 2])
  })

  it("coerces page below 1 to 1", () => {
    const p = new URLSearchParams("page=0")
    expect(filtersFromSearchParams(p).page).toBe(1)
  })
})

describe("filtersToSearchParams", () => {
  it("round-trips", () => {
    const f = { q: "a", categoryId: 1, locationId: 2, tagIds: [3, 4], page: 2 }
    const p = filtersToSearchParams(f)
    expect(Object.fromEntries(p.entries())).toEqual({
      q: "a", category: "1", location: "2", tags: "3,4", page: "2",
    })
  })

  it("omits page=1", () => {
    expect(filtersToSearchParams({ page: 1 }).toString()).toBe("")
  })

  it("omits empty tag list", () => {
    expect(filtersToSearchParams({ tagIds: [] }).toString()).toBe("")
  })
})
```

- [ ] **Step 3: Run the filter tests**

```bash
cd apps/web
pnpm test
```
Expected: all tests pass (existing + 6 new).

- [ ] **Step 4: Write `use-items.ts`**

```ts
// apps/web/lib/hooks/use-items.ts
"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import * as api from "@/lib/api/items"
import type { ItemCreate, ItemFilters, ItemUpdate } from "@/lib/api/items"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useItems(filters: ItemFilters) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["items", filters],
    queryFn: () => api.listItems(filters, token),
    enabled: token !== null,
  })
}

export function useItem(id: string | undefined) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["items", id],
    queryFn: () => api.getItem(id as string, token),
    enabled: token !== null && !!id,
  })
}

export function useCreateItem() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ItemCreate) => api.createItem(body, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["items"] })
      qc.invalidateQueries({ queryKey: ["tags"] })
    },
  })
}

export function useUpdateItem(id: string) {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ItemUpdate) => api.updateItem(id, body, token),
    onSuccess: (data) => {
      qc.setQueryData(["items", id], data)
      qc.invalidateQueries({ queryKey: ["items"] })
      qc.invalidateQueries({ queryKey: ["tags"] })
    },
  })
}

export function useDeleteItem() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deleteItem(id, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["items"] }),
  })
}
```

- [ ] **Step 5: Write `use-categories.ts`**

```ts
// apps/web/lib/hooks/use-categories.ts
"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import * as api from "@/lib/api/categories"
import type { CategoryCreate, CategoryUpdate } from "@/lib/api/categories"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useCategories() {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["categories"],
    queryFn: () => api.listCategories(token),
    enabled: token !== null,
  })
}

export function useCreateCategory() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CategoryCreate) => api.createCategory(body, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["categories"] }),
  })
}

export function useUpdateCategory() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: CategoryUpdate }) =>
      api.updateCategory(id, body, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["categories"] }),
  })
}

export function useDeleteCategory() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.deleteCategory(id, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["categories"] })
      qc.invalidateQueries({ queryKey: ["items"] })
    },
  })
}
```

- [ ] **Step 6: Write `use-locations.ts`**

```ts
// apps/web/lib/hooks/use-locations.ts
"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import * as api from "@/lib/api/locations"
import type { LocationCreate, LocationUpdate } from "@/lib/api/locations"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useLocations() {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["locations"],
    queryFn: () => api.listLocations(token),
    enabled: token !== null,
  })
}

export function useCreateLocation() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: LocationCreate) => api.createLocation(body, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["locations"] }),
  })
}

export function useUpdateLocation() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: LocationUpdate }) =>
      api.updateLocation(id, body, token),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["locations"] }),
  })
}

export function useDeleteLocation() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.deleteLocation(id, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["locations"] })
      qc.invalidateQueries({ queryKey: ["items"] })
    },
  })
}
```

- [ ] **Step 7: Write `use-tags.ts`**

```ts
// apps/web/lib/hooks/use-tags.ts
"use client"

import { useQuery } from "@tanstack/react-query"

import * as api from "@/lib/api/tags"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useTags(q: string | undefined = undefined) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["tags", q ?? ""],
    queryFn: () => api.listTags(q, token),
    enabled: token !== null,
  })
}
```

- [ ] **Step 8: Typecheck**

```bash
cd apps/web
pnpm typecheck && pnpm test
```
Expected: no type errors; all unit tests pass.

- [ ] **Step 9: Commit**

```bash
git add apps/web/lib/items/ apps/web/lib/hooks/
git commit -m "feat(web): add React Query hooks + URL filter helpers for items"
```

---

## Task 12: i18n strings for items + taxonomy

**Files:**
- Modify: `apps/web/messages/zh-TW.json`
- Modify: `apps/web/messages/en.json`

- [ ] **Step 1: Add keys to `messages/zh-TW.json`**

Insert these top-level keys before the closing `}` (keep existing keys):

```json
  "items": {
    "list": {
      "searchPlaceholder": "搜尋物品名稱或描述…",
      "new": "新增物品",
      "empty": "還沒有任何物品",
      "emptyCta": "建立第一件物品",
      "noResults": "沒有符合條件的物品",
      "showFilters": "篩選",
      "hideFilters": "收合篩選",
      "clearFilters": "清除篩選",
      "columnName": "名稱",
      "columnCategory": "分類",
      "columnLocation": "位置",
      "columnQuantity": "數量",
      "columnTags": "標籤",
      "page": "第 {page} 頁 / 共 {total} 頁"
    },
    "form": {
      "name": "名稱",
      "description": "描述",
      "category": "分類",
      "location": "位置",
      "quantity": "數量",
      "notes": "備註",
      "tags": "標籤",
      "tagsPlaceholder": "輸入後按 Enter 新增",
      "save": "儲存",
      "saving": "儲存中…",
      "cancel": "取消",
      "noneOption": "(未分類)",
      "validation": {
        "nameRequired": "請輸入名稱",
        "quantityMin": "數量不可小於 0"
      }
    },
    "detail": {
      "edit": "編輯",
      "delete": "刪除",
      "confirmDelete": "確定要刪除此物品?",
      "confirmDeleteBody": "物品將被標記為已刪除,之後無法從列表看到。",
      "deleted": "已刪除",
      "notFound": "找不到此物品"
    },
    "toast": {
      "created": "已建立",
      "updated": "已更新",
      "deleted": "已刪除"
    }
  },
  "taxonomy": {
    "title": "分類與位置",
    "tabs": {
      "categories": "分類",
      "locations": "位置"
    },
    "categories": {
      "add": "新增分類",
      "name": "名稱",
      "parent": "父分類",
      "noParent": "(頂層)",
      "empty": "尚未建立分類",
      "delete": "刪除",
      "confirmDelete": "確定刪除此分類?子分類會變為頂層。"
    },
    "locations": {
      "add": "新增位置",
      "floor": "樓層",
      "room": "房間",
      "zone": "區域",
      "empty": "尚未建立位置",
      "delete": "刪除",
      "confirmDelete": "確定刪除此位置?"
    }
  },
  "nav": {
    "dashboard": "儀表板",
    "items": "物品",
    "lists": "清單",
    "settings": "設定",
    "taxonomy": "分類與位置"
  }
```

Replace the existing `"nav"` block — the only addition is `taxonomy`. Keep other blocks untouched.

- [ ] **Step 2: Add same keys to `messages/en.json`**

```json
  "items": {
    "list": {
      "searchPlaceholder": "Search items by name or description…",
      "new": "New item",
      "empty": "No items yet",
      "emptyCta": "Create your first item",
      "noResults": "No items match your filters",
      "showFilters": "Filters",
      "hideFilters": "Hide filters",
      "clearFilters": "Clear filters",
      "columnName": "Name",
      "columnCategory": "Category",
      "columnLocation": "Location",
      "columnQuantity": "Qty",
      "columnTags": "Tags",
      "page": "Page {page} of {total}"
    },
    "form": {
      "name": "Name",
      "description": "Description",
      "category": "Category",
      "location": "Location",
      "quantity": "Quantity",
      "notes": "Notes",
      "tags": "Tags",
      "tagsPlaceholder": "Type and press Enter",
      "save": "Save",
      "saving": "Saving…",
      "cancel": "Cancel",
      "noneOption": "(None)",
      "validation": {
        "nameRequired": "Name is required",
        "quantityMin": "Quantity cannot be negative"
      }
    },
    "detail": {
      "edit": "Edit",
      "delete": "Delete",
      "confirmDelete": "Delete this item?",
      "confirmDeleteBody": "The item will be marked deleted and removed from lists.",
      "deleted": "Deleted",
      "notFound": "Item not found"
    },
    "toast": {
      "created": "Created",
      "updated": "Updated",
      "deleted": "Deleted"
    }
  },
  "taxonomy": {
    "title": "Categories & Locations",
    "tabs": {
      "categories": "Categories",
      "locations": "Locations"
    },
    "categories": {
      "add": "Add category",
      "name": "Name",
      "parent": "Parent",
      "noParent": "(Top level)",
      "empty": "No categories yet",
      "delete": "Delete",
      "confirmDelete": "Delete this category? Children become top-level."
    },
    "locations": {
      "add": "Add location",
      "floor": "Floor",
      "room": "Room",
      "zone": "Zone",
      "empty": "No locations yet",
      "delete": "Delete",
      "confirmDelete": "Delete this location?"
    }
  },
  "nav": {
    "dashboard": "Dashboard",
    "items": "Items",
    "lists": "Lists",
    "settings": "Settings",
    "taxonomy": "Taxonomy"
  }
```

- [ ] **Step 3: Verify JSON is valid**

```bash
cd apps/web
node -e "JSON.parse(require('fs').readFileSync('messages/zh-TW.json','utf8')); JSON.parse(require('fs').readFileSync('messages/en.json','utf8')); console.log('ok')"
```
Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add apps/web/messages/zh-TW.json apps/web/messages/en.json
git commit -m "feat(web): add i18n strings for items + taxonomy"
```

---

## Task 13: Shared ItemForm component + unit test

**Files:**
- Create: `apps/web/components/items/item-form.tsx`
- Create: `apps/web/components/items/item-form.test.tsx`
- Create: `apps/web/components/items/tag-multi-select.tsx`

- [ ] **Step 1: Write `tag-multi-select.tsx`** (minimal, chip-based input)

```tsx
// apps/web/components/items/tag-multi-select.tsx
"use client"

import { X } from "lucide-react"
import { useState, type KeyboardEvent } from "react"
import { useTranslations } from "next-intl"

import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"

interface Props {
  value: string[]
  onChange: (next: string[]) => void
  suggestions?: string[]
}

export function TagMultiSelect({ value, onChange, suggestions = [] }: Props) {
  const t = useTranslations()
  const [draft, setDraft] = useState("")

  const commit = () => {
    const cleaned = draft.trim().toLowerCase()
    if (!cleaned) return
    if (value.includes(cleaned)) {
      setDraft("")
      return
    }
    onChange([...value, cleaned])
    setDraft("")
  }

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault()
      commit()
    } else if (e.key === "Backspace" && draft === "" && value.length > 0) {
      onChange(value.slice(0, -1))
    }
  }

  const remove = (name: string) => onChange(value.filter((v) => v !== name))

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1 rounded-md border px-2 py-2">
        {value.map((name) => (
          <Badge key={name} variant="secondary" className="gap-1">
            {name}
            <button type="button" onClick={() => remove(name)} aria-label={`remove ${name}`}>
              <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}
        <Input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={commit}
          placeholder={t("items.form.tagsPlaceholder")}
          className="h-7 flex-1 border-0 p-0 focus-visible:ring-0"
          list="tag-suggestions"
        />
      </div>
      {suggestions.length > 0 && (
        <datalist id="tag-suggestions">
          {suggestions.filter((s) => !value.includes(s)).map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Write `item-form.tsx`**

```tsx
// apps/web/components/items/item-form.tsx
"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { useTranslations } from "next-intl"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { TagMultiSelect } from "./tag-multi-select"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import type { CategoryTreeNode } from "@/lib/api/categories"
import type { LocationRead } from "@/lib/api/locations"

export const itemFormSchema = z.object({
  name: z.string().min(1).max(200),
  description: z.string().optional(),
  category_id: z.number().nullable(),
  location_id: z.number().nullable(),
  quantity: z.number().int().min(0),
  notes: z.string().optional(),
  tag_names: z.array(z.string()),
})
export type ItemFormValues = z.infer<typeof itemFormSchema>

interface Props {
  defaultValues: ItemFormValues
  onSubmit: (values: ItemFormValues) => void | Promise<void>
  onCancel: () => void
  submitting: boolean
  categories: CategoryTreeNode[]
  locations: LocationRead[]
  tagSuggestions: string[]
}

function flattenCategories(nodes: CategoryTreeNode[], depth = 0): Array<{ id: number; label: string }> {
  const out: Array<{ id: number; label: string }> = []
  for (const n of nodes) {
    out.push({ id: n.id, label: `${"— ".repeat(depth)}${n.name}` })
    if (n.children && n.children.length > 0) out.push(...flattenCategories(n.children, depth + 1))
  }
  return out
}

export function ItemForm({
  defaultValues, onSubmit, onCancel, submitting,
  categories, locations, tagSuggestions,
}: Props) {
  const t = useTranslations()
  const form = useForm<ItemFormValues>({
    resolver: zodResolver(itemFormSchema),
    defaultValues,
  })
  const flatCats = flattenCategories(categories)

  return (
    <form
      onSubmit={form.handleSubmit(onSubmit)}
      className="space-y-4 max-w-xl"
      aria-label="item-form"
    >
      <div>
        <Label htmlFor="name">{t("items.form.name")}</Label>
        <Input id="name" {...form.register("name")} />
        {form.formState.errors.name && (
          <p role="alert" className="mt-1 text-sm text-destructive">
            {t("items.form.validation.nameRequired")}
          </p>
        )}
      </div>

      <div>
        <Label htmlFor="description">{t("items.form.description")}</Label>
        <Textarea id="description" rows={3} {...form.register("description")} />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label>{t("items.form.category")}</Label>
          <Select
            value={form.watch("category_id")?.toString() ?? "none"}
            onValueChange={(v) => form.setValue("category_id", v === "none" ? null : Number(v))}
          >
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="none">{t("items.form.noneOption")}</SelectItem>
              {flatCats.map((c) => (
                <SelectItem key={c.id} value={String(c.id)}>{c.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label>{t("items.form.location")}</Label>
          <Select
            value={form.watch("location_id")?.toString() ?? "none"}
            onValueChange={(v) => form.setValue("location_id", v === "none" ? null : Number(v))}
          >
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="none">{t("items.form.noneOption")}</SelectItem>
              {locations.map((l) => (
                <SelectItem key={l.id} value={String(l.id)}>
                  {[l.floor, l.room, l.zone].filter(Boolean).join(" / ")}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div>
        <Label htmlFor="quantity">{t("items.form.quantity")}</Label>
        <Input
          id="quantity"
          type="number"
          min={0}
          {...form.register("quantity", { valueAsNumber: true })}
        />
        {form.formState.errors.quantity && (
          <p role="alert" className="mt-1 text-sm text-destructive">
            {t("items.form.validation.quantityMin")}
          </p>
        )}
      </div>

      <div>
        <Label>{t("items.form.tags")}</Label>
        <TagMultiSelect
          value={form.watch("tag_names")}
          onChange={(next) => form.setValue("tag_names", next)}
          suggestions={tagSuggestions}
        />
      </div>

      <div>
        <Label htmlFor="notes">{t("items.form.notes")}</Label>
        <Textarea id="notes" rows={2} {...form.register("notes")} />
      </div>

      <div className="flex gap-2">
        <Button type="submit" disabled={submitting}>
          {submitting ? t("items.form.saving") : t("items.form.save")}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel}>
          {t("items.form.cancel")}
        </Button>
      </div>
    </form>
  )
}
```

- [ ] **Step 3: Write unit test for form schema**

```tsx
// apps/web/components/items/item-form.test.tsx
import { describe, it, expect } from "vitest"
import { itemFormSchema } from "./item-form"

describe("itemFormSchema", () => {
  const ok = {
    name: "thing", description: "", category_id: null, location_id: null,
    quantity: 1, notes: "", tag_names: [],
  }

  it("accepts a valid minimal record", () => {
    expect(itemFormSchema.safeParse(ok).success).toBe(true)
  })

  it("rejects empty name", () => {
    const r = itemFormSchema.safeParse({ ...ok, name: "" })
    expect(r.success).toBe(false)
  })

  it("rejects negative quantity", () => {
    const r = itemFormSchema.safeParse({ ...ok, quantity: -1 })
    expect(r.success).toBe(false)
  })

  it("rejects non-integer quantity", () => {
    const r = itemFormSchema.safeParse({ ...ok, quantity: 1.5 })
    expect(r.success).toBe(false)
  })
})
```

- [ ] **Step 4: Run unit tests**

```bash
cd apps/web
pnpm test
```
Expected: new tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/web/components/items/
git commit -m "feat(web): add shared ItemForm + tag multi-select"
```

---

## Task 14: Items list page + filter panel

**Files:**
- Create: `apps/web/components/items/items-table.tsx`
- Create: `apps/web/components/items/items-filter-panel.tsx`
- Create: `apps/web/app/(app)/items/items-list-client.tsx`
- Modify: `apps/web/app/(app)/items/page.tsx`

- [ ] **Step 1: Write `items-table.tsx`**

```tsx
// apps/web/components/items/items-table.tsx
"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"

import { Badge } from "@/components/ui/badge"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import type { ItemRead } from "@/lib/api/items"

export function ItemsTable({ items }: { items: ItemRead[] }) {
  const t = useTranslations()
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t("items.list.columnName")}</TableHead>
          <TableHead>{t("items.list.columnCategory")}</TableHead>
          <TableHead>{t("items.list.columnLocation")}</TableHead>
          <TableHead className="text-right">{t("items.list.columnQuantity")}</TableHead>
          <TableHead>{t("items.list.columnTags")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((i) => (
          <TableRow key={i.id}>
            <TableCell>
              <Link className="font-medium underline-offset-2 hover:underline" href={`/items/${i.id}`}>
                {i.name}
              </Link>
            </TableCell>
            <TableCell>{i.category?.name ?? "—"}</TableCell>
            <TableCell>
              {i.location ? [i.location.floor, i.location.room, i.location.zone].filter(Boolean).join(" / ") : "—"}
            </TableCell>
            <TableCell className="text-right tabular-nums">{i.quantity}</TableCell>
            <TableCell className="space-x-1">
              {i.tags.map((t) => <Badge key={t.id} variant="secondary">{t.name}</Badge>)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
```

- [ ] **Step 2: Write `items-filter-panel.tsx`**

```tsx
// apps/web/components/items/items-filter-panel.tsx
"use client"

import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { ItemFilters } from "@/lib/api/items"
import { useCategories } from "@/lib/hooks/use-categories"
import { useLocations } from "@/lib/hooks/use-locations"
import { useTags } from "@/lib/hooks/use-tags"

interface Props {
  filters: ItemFilters
  onChange: (next: ItemFilters) => void
}

export function ItemsFilterPanel({ filters, onChange }: Props) {
  const t = useTranslations()
  const cats = useCategories()
  const locs = useLocations()
  const tags = useTags()

  const anyActive =
    filters.categoryId != null || filters.locationId != null ||
    (filters.tagIds && filters.tagIds.length > 0)

  const flatCats: Array<{ id: number; label: string }> = []
  const walk = (nodes: typeof cats.data, depth = 0) => {
    if (!nodes) return
    for (const n of nodes) {
      flatCats.push({ id: n.id, label: `${"— ".repeat(depth)}${n.name}` })
      walk(n.children ?? [], depth + 1)
    }
  }
  walk(cats.data)

  return (
    <div className="space-y-3 border rounded-md p-3 text-sm">
      <div>
        <Label>{t("items.form.category")}</Label>
        <Select
          value={filters.categoryId?.toString() ?? "all"}
          onValueChange={(v) =>
            onChange({ ...filters, categoryId: v === "all" ? undefined : Number(v), page: 1 })
          }
        >
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("items.form.noneOption")}</SelectItem>
            {flatCats.map((c) => (
              <SelectItem key={c.id} value={String(c.id)}>{c.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label>{t("items.form.location")}</Label>
        <Select
          value={filters.locationId?.toString() ?? "all"}
          onValueChange={(v) =>
            onChange({ ...filters, locationId: v === "all" ? undefined : Number(v), page: 1 })
          }
        >
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("items.form.noneOption")}</SelectItem>
            {(locs.data ?? []).map((l) => (
              <SelectItem key={l.id} value={String(l.id)}>
                {[l.floor, l.room, l.zone].filter(Boolean).join(" / ")}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div>
        <Label>{t("items.form.tags")}</Label>
        <div className="flex flex-wrap gap-1">
          {(tags.data ?? []).map((tag) => {
            const on = filters.tagIds?.includes(tag.id) ?? false
            return (
              <button
                key={tag.id}
                type="button"
                onClick={() => {
                  const next = on
                    ? (filters.tagIds ?? []).filter((id) => id !== tag.id)
                    : [...(filters.tagIds ?? []), tag.id]
                  onChange({ ...filters, tagIds: next.length ? next : undefined, page: 1 })
                }}
                className={`rounded px-2 py-0.5 text-xs ${on ? "bg-primary text-primary-foreground" : "bg-muted"}`}
              >
                {tag.name}
              </button>
            )
          })}
        </div>
      </div>

      {anyActive && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => onChange({ q: filters.q, page: 1 })}
        >
          {t("items.list.clearFilters")}
        </Button>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Write `items-list-client.tsx`**

```tsx
// apps/web/app/(app)/items/items-list-client.tsx
"use client"

import Link from "next/link"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { useTranslations } from "next-intl"
import { useCallback, useEffect, useMemo, useState } from "react"

import { ItemsFilterPanel } from "@/components/items/items-filter-panel"
import { ItemsTable } from "@/components/items/items-table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import type { ItemFilters } from "@/lib/api/items"
import { useItems } from "@/lib/hooks/use-items"
import { filtersFromSearchParams, filtersToSearchParams } from "@/lib/items/filters"

export function ItemsListClient() {
  const t = useTranslations()
  const router = useRouter()
  const pathname = usePathname()
  const params = useSearchParams()
  const filters = useMemo<ItemFilters>(
    () => filtersFromSearchParams(new URLSearchParams(params.toString())),
    [params],
  )

  const [searchInput, setSearchInput] = useState(filters.q ?? "")
  useEffect(() => setSearchInput(filters.q ?? ""), [filters.q])

  const writeFilters = useCallback(
    (next: ItemFilters) => {
      const qs = filtersToSearchParams(next).toString()
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false })
    },
    [router, pathname],
  )

  useEffect(() => {
    const h = setTimeout(() => {
      if (searchInput !== (filters.q ?? "")) {
        writeFilters({ ...filters, q: searchInput || undefined, page: 1 })
      }
    }, 300)
    return () => clearTimeout(h)
  }, [searchInput, filters, writeFilters])

  const { data, isLoading } = useItems(filters)

  return (
    <div className="grid gap-4 md:grid-cols-[16rem_1fr]">
      <aside className="space-y-3">
        <ItemsFilterPanel filters={filters} onChange={writeFilters} />
      </aside>

      <section className="space-y-3">
        <div className="flex gap-2">
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={t("items.list.searchPlaceholder")}
            aria-label={t("items.list.searchPlaceholder")}
          />
          <Button asChild>
            <Link href="/items/new">{t("items.list.new")}</Link>
          </Button>
        </div>

        {isLoading ? (
          <Skeleton className="h-40 w-full" />
        ) : !data || data.items.length === 0 ? (
          <div className="rounded border p-6 text-center text-muted-foreground">
            {data && data.total === 0 && !filters.q && !filters.categoryId && !filters.locationId && !filters.tagIds ? (
              <>
                <p>{t("items.list.empty")}</p>
                <Button asChild variant="link">
                  <Link href="/items/new">{t("items.list.emptyCta")}</Link>
                </Button>
              </>
            ) : (
              <p>{t("items.list.noResults")}</p>
            )}
          </div>
        ) : (
          <>
            <ItemsTable items={data.items} />
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>{t("items.list.page", {
                page: data.page,
                total: Math.max(1, Math.ceil(data.total / data.per_page)),
              })}</span>
              <div className="flex gap-2">
                <Button
                  variant="outline" size="sm"
                  disabled={data.page <= 1}
                  onClick={() => writeFilters({ ...filters, page: Math.max(1, (filters.page ?? 1) - 1) })}
                >
                  ←
                </Button>
                <Button
                  variant="outline" size="sm"
                  disabled={data.page * data.per_page >= data.total}
                  onClick={() => writeFilters({ ...filters, page: (filters.page ?? 1) + 1 })}
                >
                  →
                </Button>
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  )
}
```

- [ ] **Step 4: Replace `app/(app)/items/page.tsx`**

```tsx
// apps/web/app/(app)/items/page.tsx
import { useTranslations } from "next-intl"

import {
  Breadcrumb, BreadcrumbItem, BreadcrumbList, BreadcrumbPage,
} from "@/components/ui/breadcrumb"
import { ItemsListClient } from "./items-list-client"

export default function ItemsPage() {
  const t = useTranslations()
  return (
    <section className="space-y-4 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>{t("nav.items")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <h1 className="text-2xl font-semibold">{t("nav.items")}</h1>
      <ItemsListClient />
    </section>
  )
}
```

- [ ] **Step 5: Typecheck + lint**

```bash
cd apps/web
pnpm typecheck && pnpm lint
```
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add apps/web/components/items/items-table.tsx \
        apps/web/components/items/items-filter-panel.tsx \
        apps/web/app/\(app\)/items/items-list-client.tsx \
        apps/web/app/\(app\)/items/page.tsx
git commit -m "feat(web): items list page with search, filters, pagination"
```

---

## Task 15: Items create + edit pages

**Files:**
- Create: `apps/web/app/(app)/items/new/page.tsx`
- Create: `apps/web/app/(app)/items/[id]/edit/page.tsx`

- [ ] **Step 1: Write `new/page.tsx`**

```tsx
// apps/web/app/(app)/items/new/page.tsx
"use client"

import { useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { ItemForm, type ItemFormValues } from "@/components/items/item-form"
import {
  Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { useCategories } from "@/lib/hooks/use-categories"
import { useCreateItem } from "@/lib/hooks/use-items"
import { useLocations } from "@/lib/hooks/use-locations"
import { useTags } from "@/lib/hooks/use-tags"

const empty: ItemFormValues = {
  name: "", description: "", category_id: null, location_id: null,
  quantity: 1, notes: "", tag_names: [],
}

export default function NewItemPage() {
  const t = useTranslations()
  const router = useRouter()
  const create = useCreateItem()
  const cats = useCategories()
  const locs = useLocations()
  const tags = useTags()

  async function handleSubmit(values: ItemFormValues) {
    const created = await create.mutateAsync({
      name: values.name,
      description: values.description || undefined,
      category_id: values.category_id ?? undefined,
      location_id: values.location_id ?? undefined,
      quantity: values.quantity,
      notes: values.notes || undefined,
      tag_names: values.tag_names,
    })
    toast.success(t("items.toast.created"))
    router.push(`/items/${created.id}`)
  }

  return (
    <section className="space-y-4 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem><BreadcrumbLink href="/items">{t("nav.items")}</BreadcrumbLink></BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem><BreadcrumbPage>{t("items.list.new")}</BreadcrumbPage></BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <h1 className="text-2xl font-semibold">{t("items.list.new")}</h1>
      <ItemForm
        defaultValues={empty}
        onSubmit={handleSubmit}
        onCancel={() => router.push("/items")}
        submitting={create.isPending}
        categories={cats.data ?? []}
        locations={locs.data ?? []}
        tagSuggestions={(tags.data ?? []).map((t) => t.name)}
      />
    </section>
  )
}
```

- [ ] **Step 2: Write `[id]/edit/page.tsx`**

```tsx
// apps/web/app/(app)/items/[id]/edit/page.tsx
"use client"

import { useParams, useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { ItemForm, type ItemFormValues } from "@/components/items/item-form"
import {
  Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Skeleton } from "@/components/ui/skeleton"
import { useCategories } from "@/lib/hooks/use-categories"
import { useItem, useUpdateItem } from "@/lib/hooks/use-items"
import { useLocations } from "@/lib/hooks/use-locations"
import { useTags } from "@/lib/hooks/use-tags"

export default function EditItemPage() {
  const t = useTranslations()
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const id = params?.id ?? ""
  const item = useItem(id)
  const update = useUpdateItem(id)
  const cats = useCategories()
  const locs = useLocations()
  const tags = useTags()

  if (item.isLoading || !item.data) {
    return (
      <section className="space-y-4 p-6">
        <Skeleton className="h-64 w-full max-w-xl" />
      </section>
    )
  }

  const defaults: ItemFormValues = {
    name: item.data.name,
    description: item.data.description ?? "",
    category_id: item.data.category?.id ?? null,
    location_id: item.data.location?.id ?? null,
    quantity: item.data.quantity,
    notes: item.data.notes ?? "",
    tag_names: item.data.tags.map((t) => t.name),
  }

  async function handleSubmit(values: ItemFormValues) {
    await update.mutateAsync({
      name: values.name,
      description: values.description || null,
      category_id: values.category_id,
      location_id: values.location_id,
      quantity: values.quantity,
      notes: values.notes || null,
      tag_names: values.tag_names,
    })
    toast.success(t("items.toast.updated"))
    router.push(`/items/${id}`)
  }

  return (
    <section className="space-y-4 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem><BreadcrumbLink href="/items">{t("nav.items")}</BreadcrumbLink></BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem><BreadcrumbLink href={`/items/${id}`}>{item.data.name}</BreadcrumbLink></BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem><BreadcrumbPage>{t("items.detail.edit")}</BreadcrumbPage></BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <h1 className="text-2xl font-semibold">{t("items.detail.edit")}</h1>
      <ItemForm
        defaultValues={defaults}
        onSubmit={handleSubmit}
        onCancel={() => router.push(`/items/${id}`)}
        submitting={update.isPending}
        categories={cats.data ?? []}
        locations={locs.data ?? []}
        tagSuggestions={(tags.data ?? []).map((t) => t.name)}
      />
    </section>
  )
}
```

- [ ] **Step 3: Typecheck**

```bash
cd apps/web
pnpm typecheck
```
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add apps/web/app/\(app\)/items/new/page.tsx apps/web/app/\(app\)/items/\[id\]/edit/page.tsx
git commit -m "feat(web): items new + edit pages"
```

---

## Task 16: Items detail page + delete dialog

**Files:**
- Create: `apps/web/components/items/delete-item-dialog.tsx`
- Create: `apps/web/app/(app)/items/[id]/page.tsx`

- [ ] **Step 1: Delete dialog**

```tsx
// apps/web/components/items/delete-item-dialog.tsx
"use client"

import { useTranslations } from "next-intl"

import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"

interface Props {
  onConfirm: () => void | Promise<void>
  pending: boolean
}

export function DeleteItemDialog({ onConfirm, pending }: Props) {
  const t = useTranslations()
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="destructive">{t("items.detail.delete")}</Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t("items.detail.confirmDelete")}</AlertDialogTitle>
          <AlertDialogDescription>{t("items.detail.confirmDeleteBody")}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{t("items.form.cancel")}</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm} disabled={pending}>
            {t("items.detail.delete")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
```

- [ ] **Step 2: Detail page**

```tsx
// apps/web/app/(app)/items/[id]/page.tsx
"use client"

import Link from "next/link"
import { useParams, useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { toast } from "sonner"

import { DeleteItemDialog } from "@/components/items/delete-item-dialog"
import { Badge } from "@/components/ui/badge"
import {
  Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useDeleteItem, useItem } from "@/lib/hooks/use-items"

export default function ItemDetailPage() {
  const t = useTranslations()
  const router = useRouter()
  const params = useParams<{ id: string }>()
  const id = params?.id ?? ""
  const item = useItem(id)
  const del = useDeleteItem()

  async function handleDelete() {
    await del.mutateAsync(id)
    toast.success(t("items.toast.deleted"))
    router.push("/items")
  }

  if (item.isLoading) {
    return (
      <section className="space-y-4 p-6">
        <Skeleton className="h-64 w-full max-w-2xl" />
      </section>
    )
  }
  if (item.isError || !item.data) {
    return (
      <section className="space-y-4 p-6">
        <p className="text-muted-foreground">{t("items.detail.notFound")}</p>
      </section>
    )
  }

  const i = item.data
  return (
    <section className="space-y-4 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem><BreadcrumbLink href="/items">{t("nav.items")}</BreadcrumbLink></BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem><BreadcrumbPage>{i.name}</BreadcrumbPage></BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold">{i.name}</h1>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link href={`/items/${i.id}/edit`}>{t("items.detail.edit")}</Link>
          </Button>
          <DeleteItemDialog onConfirm={handleDelete} pending={del.isPending} />
        </div>
      </div>

      <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2 max-w-2xl">
        <div>
          <dt className="text-sm text-muted-foreground">{t("items.form.description")}</dt>
          <dd>{i.description || "—"}</dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">{t("items.form.quantity")}</dt>
          <dd className="tabular-nums">{i.quantity}</dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">{t("items.form.category")}</dt>
          <dd>{i.category?.name ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-sm text-muted-foreground">{t("items.form.location")}</dt>
          <dd>{i.location ? [i.location.floor, i.location.room, i.location.zone].filter(Boolean).join(" / ") : "—"}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-sm text-muted-foreground">{t("items.form.tags")}</dt>
          <dd className="space-x-1">
            {i.tags.length === 0 ? "—" : i.tags.map((t) => <Badge key={t.id} variant="secondary">{t.name}</Badge>)}
          </dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-sm text-muted-foreground">{t("items.form.notes")}</dt>
          <dd className="whitespace-pre-wrap">{i.notes || "—"}</dd>
        </div>
      </dl>
    </section>
  )
}
```

- [ ] **Step 3: Typecheck**

```bash
cd apps/web
pnpm typecheck
```
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add apps/web/components/items/delete-item-dialog.tsx apps/web/app/\(app\)/items/\[id\]/page.tsx
git commit -m "feat(web): items detail page with delete dialog"
```

---

## Task 17: Settings / taxonomy page

**Files:**
- Create: `apps/web/components/taxonomy/categories-panel.tsx`
- Create: `apps/web/components/taxonomy/locations-panel.tsx`
- Create: `apps/web/app/(app)/settings/taxonomy/page.tsx`

- [ ] **Step 1: `categories-panel.tsx`**

```tsx
// apps/web/components/taxonomy/categories-panel.tsx
"use client"

import { Trash2 } from "lucide-react"
import { useTranslations } from "next-intl"
import { useState } from "react"

import type { CategoryTreeNode } from "@/lib/api/categories"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  useCategories, useCreateCategory, useDeleteCategory,
} from "@/lib/hooks/use-categories"

function flatten(nodes: CategoryTreeNode[], depth = 0): Array<{ id: number; label: string; node: CategoryTreeNode }> {
  const out: Array<{ id: number; label: string; node: CategoryTreeNode }> = []
  for (const n of nodes) {
    out.push({ id: n.id, label: `${"— ".repeat(depth)}${n.name}`, node: n })
    out.push(...flatten(n.children ?? [], depth + 1))
  }
  return out
}

export function CategoriesPanel() {
  const t = useTranslations()
  const cats = useCategories()
  const create = useCreateCategory()
  const del = useDeleteCategory()
  const [name, setName] = useState("")
  const [parent, setParent] = useState<string>("none")

  const flat = flatten(cats.data ?? [])

  async function handleAdd() {
    if (!name.trim()) return
    await create.mutateAsync({
      name: name.trim(),
      parent_id: parent === "none" ? null : Number(parent),
    })
    setName("")
    setParent("none")
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t("taxonomy.categories.name")}
          aria-label={t("taxonomy.categories.name")}
        />
        <Select value={parent} onValueChange={setParent}>
          <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="none">{t("taxonomy.categories.noParent")}</SelectItem>
            {flat.map((c) => (
              <SelectItem key={c.id} value={String(c.id)}>{c.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button onClick={handleAdd} disabled={create.isPending || !name.trim()}>
          {t("taxonomy.categories.add")}
        </Button>
      </div>

      {flat.length === 0 ? (
        <p className="text-muted-foreground">{t("taxonomy.categories.empty")}</p>
      ) : (
        <ul className="space-y-1">
          {flat.map((c) => (
            <li key={c.id} className="flex items-center justify-between border rounded px-3 py-2">
              <span>{c.label}</span>
              <Button
                variant="ghost" size="sm"
                onClick={() => {
                  if (confirm(t("taxonomy.categories.confirmDelete"))) {
                    del.mutate(c.id)
                  }
                }}
              >
                <Trash2 className="h-4 w-4" />
                <span className="sr-only">{t("taxonomy.categories.delete")}</span>
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
```

- [ ] **Step 2: `locations-panel.tsx`**

```tsx
// apps/web/components/taxonomy/locations-panel.tsx
"use client"

import { Trash2 } from "lucide-react"
import { useTranslations } from "next-intl"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  useCreateLocation, useDeleteLocation, useLocations,
} from "@/lib/hooks/use-locations"

export function LocationsPanel() {
  const t = useTranslations()
  const locs = useLocations()
  const create = useCreateLocation()
  const del = useDeleteLocation()
  const [floor, setFloor] = useState("")
  const [room, setRoom] = useState("")
  const [zone, setZone] = useState("")

  async function handleAdd() {
    if (!floor.trim()) return
    await create.mutateAsync({
      floor: floor.trim(),
      room: room.trim() || null,
      zone: zone.trim() || null,
    })
    setFloor(""); setRoom(""); setZone("")
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
        <Input value={floor} onChange={(e) => setFloor(e.target.value)}
               placeholder={t("taxonomy.locations.floor")} aria-label={t("taxonomy.locations.floor")} />
        <Input value={room} onChange={(e) => setRoom(e.target.value)}
               placeholder={t("taxonomy.locations.room")} aria-label={t("taxonomy.locations.room")} />
        <Input value={zone} onChange={(e) => setZone(e.target.value)}
               placeholder={t("taxonomy.locations.zone")} aria-label={t("taxonomy.locations.zone")} />
        <Button onClick={handleAdd} disabled={create.isPending || !floor.trim()}>
          {t("taxonomy.locations.add")}
        </Button>
      </div>

      {(locs.data ?? []).length === 0 ? (
        <p className="text-muted-foreground">{t("taxonomy.locations.empty")}</p>
      ) : (
        <ul className="space-y-1">
          {(locs.data ?? []).map((l) => (
            <li key={l.id} className="flex items-center justify-between border rounded px-3 py-2">
              <span>{[l.floor, l.room, l.zone].filter(Boolean).join(" / ")}</span>
              <Button
                variant="ghost" size="sm"
                onClick={() => {
                  if (confirm(t("taxonomy.locations.confirmDelete"))) {
                    del.mutate(l.id)
                  }
                }}
              >
                <Trash2 className="h-4 w-4" />
                <span className="sr-only">{t("taxonomy.locations.delete")}</span>
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Taxonomy page**

```tsx
// apps/web/app/(app)/settings/taxonomy/page.tsx
"use client"

import { useTranslations } from "next-intl"

import { CategoriesPanel } from "@/components/taxonomy/categories-panel"
import { LocationsPanel } from "@/components/taxonomy/locations-panel"
import {
  Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export default function TaxonomyPage() {
  const t = useTranslations()
  return (
    <section className="space-y-4 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem><BreadcrumbLink href="/settings">{t("nav.settings")}</BreadcrumbLink></BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem><BreadcrumbPage>{t("nav.taxonomy")}</BreadcrumbPage></BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <h1 className="text-2xl font-semibold">{t("taxonomy.title")}</h1>

      <Tabs defaultValue="categories">
        <TabsList>
          <TabsTrigger value="categories">{t("taxonomy.tabs.categories")}</TabsTrigger>
          <TabsTrigger value="locations">{t("taxonomy.tabs.locations")}</TabsTrigger>
        </TabsList>
        <TabsContent value="categories"><CategoriesPanel /></TabsContent>
        <TabsContent value="locations"><LocationsPanel /></TabsContent>
      </Tabs>
    </section>
  )
}
```

- [ ] **Step 4: Typecheck + lint**

```bash
cd apps/web
pnpm typecheck && pnpm lint
```
Expected: clean.

- [ ] **Step 5: Commit**

```bash
git add apps/web/components/taxonomy/ apps/web/app/\(app\)/settings/taxonomy/page.tsx
git commit -m "feat(web): taxonomy (categories + locations) settings page"
```

---

## Task 18: Playwright E2E — full items lifecycle

**Files:**
- Create: `apps/web/tests/items-crud.spec.ts`

- [ ] **Step 1: Write the E2E spec**

```ts
// apps/web/tests/items-crud.spec.ts
import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()

async function register(request: import("@playwright/test").APIRequestContext, username: string) {
  const email = `${username}@t.io`
  const password = "secret1234"
  const reg = await request.post("/api/auth/register", { data: { email, username, password } })
  expect(reg.status()).toBe(201)
  return { username, password }
}

async function loginUi(page: import("@playwright/test").Page, username: string, password: string) {
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill(password)
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
}

test("items full CRUD lifecycle", async ({ page, request }) => {
  const u = `crud_${unique()}`
  const { username, password } = await register(request, u)
  await loginUi(page, username, password)

  await page.goto("/items")
  await expect(page.getByText("還沒有任何物品")).toBeVisible()

  await page.getByRole("link", { name: "新增物品" }).first().click()
  await page.waitForURL("**/items/new")
  await page.getByLabel("名稱").fill("燈泡")
  await page.getByLabel("描述").fill("臥室用")
  await page.getByLabel("數量").fill("3")

  const tagInput = page.getByPlaceholder("輸入後按 Enter 新增")
  await tagInput.fill("家電")
  await tagInput.press("Enter")
  await tagInput.fill("備品")
  await tagInput.press("Enter")

  await page.getByRole("button", { name: /^儲存$/ }).click()
  await expect(page.getByRole("heading", { name: "燈泡" })).toBeVisible()

  await page.goto("/items")
  await expect(page.getByRole("link", { name: "燈泡" })).toBeVisible()

  await page.getByPlaceholder("搜尋物品名稱或描述…").fill("燈")
  await expect(page.getByRole("link", { name: "燈泡" })).toBeVisible()

  await page.getByRole("link", { name: "燈泡" }).click()
  await page.getByRole("link", { name: "編輯" }).click()
  await page.getByLabel("名稱").fill("LED 燈泡")
  await page.getByRole("button", { name: /^儲存$/ }).click()
  await expect(page.getByRole("heading", { name: "LED 燈泡" })).toBeVisible()

  await page.getByRole("button", { name: "刪除" }).first().click()
  await page.getByRole("button", { name: "刪除" }).nth(1).click()
  await page.waitForURL("**/items")
  await expect(page.getByText("還沒有任何物品")).toBeVisible()
})

test("filtering by tag narrows results", async ({ page, request }) => {
  const u = `filter_${unique()}`
  const { username, password } = await register(request, u)
  await loginUi(page, username, password)

  for (const [name, tag] of [["筆記本", "文具"], ["筆", "文具"], ["杯子", "廚具"]] as const) {
    await page.goto("/items/new")
    await page.getByLabel("名稱").fill(name)
    const tagInput = page.getByPlaceholder("輸入後按 Enter 新增")
    await tagInput.fill(tag)
    await tagInput.press("Enter")
    await page.getByRole("button", { name: /^儲存$/ }).click()
    await page.waitForURL("**/items/**")
  }

  await page.goto("/items")
  await page.getByRole("button", { name: "廚具" }).click()
  await expect(page.getByRole("link", { name: "杯子" })).toBeVisible()
  await expect(page.getByRole("link", { name: "筆" })).toHaveCount(0)
})

test("cannot view another user's item", async ({ page, request }) => {
  const a = `a_${unique()}`
  const b = `b_${unique()}`
  const creds_a = await register(request, a)
  const creds_b = await register(request, b)

  const loginRes = await request.post("/api/auth/login", {
    data: { username: creds_a.username, password: creds_a.password },
  })
  const token = (await loginRes.json()).access_token
  const created = await request.post("/api/items", {
    headers: { Authorization: `Bearer ${token}` },
    data: { name: "secret" },
  })
  expect(created.status()).toBe(201)
  const itemId = (await created.json()).id

  await loginUi(page, creds_b.username, creds_b.password)
  await page.goto(`/items/${itemId}`)
  await expect(page.getByText("找不到此物品")).toBeVisible()
})
```

- [ ] **Step 2: Run Playwright locally (needs both dev servers)**

Instructions to run:
```bash
# terminal 1
cd apps/api
uv run uvicorn app.main:app --port 8000 --reload

# terminal 2
cd apps/web
pnpm dev

# terminal 3
cd apps/web
pnpm test:e2e tests/items-crud.spec.ts
```
Expected: all 3 tests pass.

If the existing playwright.config.ts webServer handles spin-up, the single command `pnpm test:e2e tests/items-crud.spec.ts` from `apps/web` is enough — check the file and adapt accordingly.

- [ ] **Step 3: Commit**

```bash
git add apps/web/tests/items-crud.spec.ts
git commit -m "test(e2e): add items CRUD + filter + authorization flows"
```

---

## Task 19: Documentation — roadmap + worktree-local README

**Files:**
- Modify: `docs/v2-roadmap.md`

- [ ] **Step 1: Mark subproject #3 complete**

Open `docs/v2-roadmap.md`. Find the #3 row and mark it the same way #2 was marked (look for `✅ 完成` on #2 and mirror the format). The exact lines to change depend on current file shape — the implementer should read the file and mirror the pattern; no other content edits.

- [ ] **Step 2: Commit**

```bash
git add docs/v2-roadmap.md
git commit -m "docs: mark #3 items CRUD + search subproject complete"
```

---

## Task 20: Final verification

- [ ] **Step 1: Full API suite**

```bash
cd apps/api
uv run pytest -q
```
Expected: all green.

- [ ] **Step 2: Full web unit tests**

```bash
cd apps/web
pnpm typecheck && pnpm lint && pnpm test
```
Expected: all green.

- [ ] **Step 3: Build check**

```bash
cd apps/web
pnpm build
```
Expected: compiles without errors.

- [ ] **Step 4: No commit; this task is verification only**

If everything passes, the plan is complete. The controller (subagent-driven-development) runs its final code-reviewer pass after this and then invokes `superpowers:finishing-a-development-branch` to merge the worktree back to `main`.

---
