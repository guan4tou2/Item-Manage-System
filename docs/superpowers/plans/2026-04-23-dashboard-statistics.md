# #4 Dashboard + Statistics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver `/dashboard` (overview + recent items) and `/statistics` (distribution charts) pages backed by five new read-only `/api/stats/*` endpoints.

**Architecture:** Reuse existing layering from #3 — FastAPI route → service → repository → SQLAlchemy async; Next.js App Router pages with React Query hooks and Recharts components. All stats are owner-scoped and exclude soft-deleted items. No migrations.

**Tech Stack:** FastAPI 0.115, SQLAlchemy 2.0 async, Pydantic v2, pytest-asyncio · Next.js 15, React 19, TanStack Query v5, next-intl, Recharts, shadcn UI, Vitest, Playwright.

---

## File Structure

**Backend (new):**
- `apps/api/app/repositories/stats_repository.py` — SQL aggregation queries
- `apps/api/app/schemas/stats.py` — Pydantic response schemas
- `apps/api/app/services/stats_service.py` — thin orchestrator (owner scoping delegated to repo)
- `apps/api/app/routes/stats.py` — five GET endpoints
- `apps/api/tests/test_stats_routes.py` — route + auth integration tests
- `apps/api/tests/test_stats_repository.py` — repo unit tests

**Backend (modify):**
- `apps/api/app/main.py` — register `stats.router`

**Frontend (new):**
- `apps/web/lib/api/stats.ts` — typed API client
- `apps/web/lib/hooks/use-stats.ts` — React Query hooks
- `apps/web/components/dashboard/stat-card.tsx`
- `apps/web/components/dashboard/recent-items-card.tsx`
- `apps/web/components/dashboard/quick-links.tsx`
- `apps/web/components/stats/category-chart.tsx`
- `apps/web/components/stats/location-chart.tsx`
- `apps/web/components/stats/tag-chart.tsx`
- `apps/web/components/stats/empty-chart.tsx`
- `apps/web/app/(app)/statistics/page.tsx`
- `apps/web/components/dashboard/stat-card.test.tsx`
- `apps/web/components/dashboard/recent-items-card.test.tsx`
- `apps/web/tests/dashboard.spec.ts`
- `apps/web/tests/statistics.spec.ts`

**Frontend (modify):**
- `apps/web/app/(app)/dashboard/page.tsx` — replace placeholder
- `apps/web/components/shell/nav-items.ts` — add `statistics` entry and broaden `NavItem["key"]` union
- `apps/web/messages/en.json` + `apps/web/messages/zh-TW.json` — `dashboard.*`, `stats.*`, `nav.statistics`
- `packages/api-types/openapi.json` + `packages/api-types/src/index.ts` — regenerated

---

## Task 1: Stats Pydantic schemas

**Files:**
- Create: `apps/api/app/schemas/stats.py`
- Test: `apps/api/tests/test_stats_schemas.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_stats_schemas.py
from app.schemas.stats import (
    OverviewStats,
    CategoryBucket,
    LocationBucket,
    TagBucket,
)


def test_overview_stats_serializes_all_fields():
    s = OverviewStats(
        total_items=5,
        total_quantity=10,
        total_categories=2,
        total_locations=1,
        total_tags=3,
    )
    assert s.model_dump() == {
        "total_items": 5,
        "total_quantity": 10,
        "total_categories": 2,
        "total_locations": 1,
        "total_tags": 3,
    }


def test_category_bucket_allows_null_id_and_name():
    b = CategoryBucket(category_id=None, name=None, count=7)
    assert b.model_dump() == {"category_id": None, "name": None, "count": 7}


def test_location_bucket_allows_null_id_and_label():
    b = LocationBucket(location_id=None, label=None, count=4)
    assert b.model_dump() == {"location_id": None, "label": None, "count": 4}


def test_tag_bucket_requires_id_and_name():
    b = TagBucket(tag_id=1, name="red", count=2)
    assert b.model_dump() == {"tag_id": 1, "name": "red", "count": 2}
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `apps/api`):
```bash
.venv/bin/python -m pytest tests/test_stats_schemas.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.schemas.stats'`.

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/app/schemas/stats.py
from __future__ import annotations

from pydantic import BaseModel


class OverviewStats(BaseModel):
    total_items: int
    total_quantity: int
    total_categories: int
    total_locations: int
    total_tags: int


class CategoryBucket(BaseModel):
    category_id: int | None
    name: str | None
    count: int


class LocationBucket(BaseModel):
    location_id: int | None
    label: str | None
    count: int


class TagBucket(BaseModel):
    tag_id: int
    name: str
    count: int
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_stats_schemas.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/schemas/stats.py apps/api/tests/test_stats_schemas.py
git commit -m "feat(api): add stats Pydantic schemas"
```

---

## Task 2: Stats repository — overview query

**Files:**
- Create: `apps/api/app/repositories/stats_repository.py`
- Test: `apps/api/tests/test_stats_repository.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_stats_repository.py
import uuid

import pytest

from app.models.category import Category
from app.models.item import Item
from app.models.location import Location
from app.models.tag import Tag
from app.models.user import User
from app.repositories import stats_repository


@pytest.fixture
async def two_users(db_session):
    a = User(email="a@t.io", username="alice", hashed_password="x")
    b = User(email="b@t.io", username="bob", hashed_password="x")
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
        Item(owner_id=bob.id, name="z", quantity=100),  # not Alice's
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_stats_repository.py -v`
Expected: `ModuleNotFoundError: No module named 'app.repositories.stats_repository'`.

- [ ] **Step 3: Write minimal implementation**

```python
# apps/api/app/repositories/stats_repository.py
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.item import Item
from app.models.location import Location
from app.models.tag import Tag


async def overview(session: AsyncSession, owner_id: UUID) -> dict[str, int]:
    item_stmt = select(
        func.count(Item.id),
        func.coalesce(func.sum(Item.quantity), 0),
    ).where(Item.owner_id == owner_id, Item.is_deleted.is_(False))
    total_items, total_quantity = (await session.execute(item_stmt)).one()

    total_categories = (await session.execute(
        select(func.count(Category.id)).where(Category.owner_id == owner_id)
    )).scalar_one()
    total_locations = (await session.execute(
        select(func.count(Location.id)).where(Location.owner_id == owner_id)
    )).scalar_one()
    total_tags = (await session.execute(
        select(func.count(Tag.id)).where(Tag.owner_id == owner_id)
    )).scalar_one()

    return {
        "total_items": int(total_items),
        "total_quantity": int(total_quantity),
        "total_categories": int(total_categories),
        "total_locations": int(total_locations),
        "total_tags": int(total_tags),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_stats_repository.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/repositories/stats_repository.py apps/api/tests/test_stats_repository.py
git commit -m "feat(api): add stats.overview repository"
```

---

## Task 3: Stats repository — by_category

**Files:**
- Modify: `apps/api/app/repositories/stats_repository.py`
- Modify: `apps/api/tests/test_stats_repository.py`

- [ ] **Step 1: Write the failing test (append)**

Append to `test_stats_repository.py`:

```python
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
        Item(owner_id=alice.id, name="i4", quantity=1),  # no category
        Item(owner_id=alice.id, name="i5", quantity=1, is_deleted=True),  # excluded
    ])
    await db_session.commit()

    rows = await stats_repository.by_category(db_session, alice.id)
    # Sorted by count DESC. A=2, B=1, null=1 — null bucket last among ties by SQL order, so just check contents.
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_stats_repository.py -v`
Expected: `AttributeError: module has no attribute 'by_category'`.

- [ ] **Step 3: Extend repository**

Append to `stats_repository.py`:

```python
from sqlalchemy.orm import aliased


async def by_category(session: AsyncSession, owner_id: UUID) -> list[dict]:
    cat = aliased(Category)
    stmt = (
        select(
            Item.category_id,
            cat.name,
            func.count(Item.id).label("count"),
        )
        .select_from(Item)
        .outerjoin(cat, cat.id == Item.category_id)
        .where(Item.owner_id == owner_id, Item.is_deleted.is_(False))
        .group_by(Item.category_id, cat.name)
        .order_by(func.count(Item.id).desc())
    )
    rows = (await session.execute(stmt)).all()
    return [
        {"category_id": r.category_id, "name": r.name, "count": int(r.count)}
        for r in rows
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_stats_repository.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/repositories/stats_repository.py apps/api/tests/test_stats_repository.py
git commit -m "feat(api): add stats.by_category repository with null bucket"
```

---

## Task 4: Stats repository — by_location

**Files:**
- Modify: `apps/api/app/repositories/stats_repository.py`
- Modify: `apps/api/tests/test_stats_repository.py`

- [ ] **Step 1: Write the failing test (append)**

```python
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
        Item(owner_id=alice.id, name="i4", quantity=1),  # no location
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_stats_repository.py -v`
Expected: `AttributeError: module has no attribute 'by_location'`.

- [ ] **Step 3: Extend repository**

Append to `stats_repository.py`:

```python
async def by_location(session: AsyncSession, owner_id: UUID) -> list[dict]:
    loc = aliased(Location)
    stmt = (
        select(
            Item.location_id,
            loc.floor,
            loc.room,
            loc.zone,
            func.count(Item.id).label("count"),
        )
        .select_from(Item)
        .outerjoin(loc, loc.id == Item.location_id)
        .where(Item.owner_id == owner_id, Item.is_deleted.is_(False))
        .group_by(Item.location_id, loc.floor, loc.room, loc.zone)
        .order_by(func.count(Item.id).desc())
    )
    rows = (await session.execute(stmt)).all()
    out = []
    for r in rows:
        if r.location_id is None:
            label = None
        else:
            parts = [p for p in (r.floor, r.room, r.zone) if p]
            label = " / ".join(parts) if parts else None
        out.append({
            "location_id": r.location_id,
            "label": label,
            "count": int(r.count),
        })
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_stats_repository.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/repositories/stats_repository.py apps/api/tests/test_stats_repository.py
git commit -m "feat(api): add stats.by_location repository with composed label"
```

---

## Task 5: Stats repository — by_tag + recent_items

**Files:**
- Modify: `apps/api/app/repositories/stats_repository.py`
- Modify: `apps/api/tests/test_stats_repository.py`

- [ ] **Step 1: Write the failing test (append)**

```python
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
    # red used on 3 items, blue on 1, unused excluded
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_stats_repository.py -v`
Expected: AttributeError about `by_tag` / `recent_items`.

- [ ] **Step 3: Extend repository**

Append to `stats_repository.py`:

```python
from sqlalchemy.orm import selectinload

from app.models.tag import item_tags


async def by_tag(session: AsyncSession, owner_id: UUID, *, limit: int) -> list[dict]:
    stmt = (
        select(Tag.id, Tag.name, func.count(item_tags.c.item_id).label("count"))
        .select_from(Tag)
        .join(item_tags, item_tags.c.tag_id == Tag.id)
        .join(Item, Item.id == item_tags.c.item_id)
        .where(
            Tag.owner_id == owner_id,
            Item.owner_id == owner_id,
            Item.is_deleted.is_(False),
        )
        .group_by(Tag.id, Tag.name)
        .order_by(func.count(item_tags.c.item_id).desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [
        {"tag_id": r.id, "name": r.name, "count": int(r.count)}
        for r in rows
    ]


async def recent_items(session: AsyncSession, owner_id: UUID, *, limit: int) -> list[Item]:
    stmt = (
        select(Item)
        .where(Item.owner_id == owner_id, Item.is_deleted.is_(False))
        .order_by(Item.created_at.desc())
        .limit(limit)
        .options(
            selectinload(Item.tags),
            selectinload(Item.category),
            selectinload(Item.location),
        )
    )
    return list((await session.execute(stmt)).scalars().all())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_stats_repository.py -v`
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/repositories/stats_repository.py apps/api/tests/test_stats_repository.py
git commit -m "feat(api): add stats.by_tag + recent_items repositories"
```

---

## Task 6: Stats service

**Files:**
- Create: `apps/api/app/services/stats_service.py`

- [ ] **Step 1: Write the service**

No dedicated service test — service is a thin wrapper, verified via route tests in Task 7.

```python
# apps/api/app/services/stats_service.py
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import stats_repository
from app.schemas.item import ItemRead
from app.schemas.stats import (
    CategoryBucket,
    LocationBucket,
    OverviewStats,
    TagBucket,
)


async def get_overview(session: AsyncSession, owner_id: UUID) -> OverviewStats:
    data = await stats_repository.overview(session, owner_id)
    return OverviewStats(**data)


async def get_by_category(session: AsyncSession, owner_id: UUID) -> list[CategoryBucket]:
    rows = await stats_repository.by_category(session, owner_id)
    return [CategoryBucket(**r) for r in rows]


async def get_by_location(session: AsyncSession, owner_id: UUID) -> list[LocationBucket]:
    rows = await stats_repository.by_location(session, owner_id)
    return [LocationBucket(**r) for r in rows]


async def get_by_tag(session: AsyncSession, owner_id: UUID, *, limit: int) -> list[TagBucket]:
    rows = await stats_repository.by_tag(session, owner_id, limit=limit)
    return [TagBucket(**r) for r in rows]


async def get_recent(session: AsyncSession, owner_id: UUID, *, limit: int) -> list[ItemRead]:
    items = await stats_repository.recent_items(session, owner_id, limit=limit)
    return [ItemRead.model_validate(i) for i in items]
```

- [ ] **Step 2: Commit**

```bash
git add apps/api/app/services/stats_service.py
git commit -m "feat(api): add stats service wiring schemas to repository"
```

---

## Task 7: Stats routes + wire into main

**Files:**
- Create: `apps/api/app/routes/stats.py`
- Modify: `apps/api/app/main.py` — add `stats` to router imports + `include_router`
- Test: `apps/api/tests/test_stats_routes.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_stats_routes.py
import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={
        "email": "s@t.io", "username": "stats_user", "password": "secret1234",
    })
    r = await client.post("/api/auth/login", json={
        "username": "stats_user", "password": "secret1234",
    })
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


class TestStatsAuth:
    async def test_overview_requires_auth(self, client):
        r = await client.get("/api/stats/overview")
        assert r.status_code == 401


class TestOverview:
    async def test_empty(self, client, auth):
        r = await client.get("/api/stats/overview", headers=auth)
        assert r.status_code == 200
        assert r.json() == {
            "total_items": 0, "total_quantity": 0,
            "total_categories": 0, "total_locations": 0, "total_tags": 0,
        }

    async def test_counts(self, client, auth):
        await client.post("/api/items", headers=auth, json={"name": "a", "quantity": 3})
        await client.post("/api/items", headers=auth, json={"name": "b", "quantity": 2, "tag_names": ["x"]})
        r = await client.get("/api/stats/overview", headers=auth)
        body = r.json()
        assert body["total_items"] == 2
        assert body["total_quantity"] == 5
        assert body["total_tags"] == 1


class TestByCategory:
    async def test_includes_uncategorized_bucket(self, client, auth):
        cat = await client.post("/api/categories", headers=auth, json={"name": "gadgets"})
        cat_id = cat.json()["id"]
        await client.post("/api/items", headers=auth, json={"name": "p", "category_id": cat_id})
        await client.post("/api/items", headers=auth, json={"name": "q"})
        r = await client.get("/api/stats/by-category", headers=auth)
        assert r.status_code == 200
        rows = r.json()
        ids = {row["category_id"] for row in rows}
        assert cat_id in ids
        assert None in ids


class TestByLocation:
    async def test_label_format(self, client, auth):
        loc = await client.post(
            "/api/locations", headers=auth,
            json={"floor": "1F", "room": "客廳", "zone": None},
        )
        lid = loc.json()["id"]
        await client.post("/api/items", headers=auth, json={"name": "p", "location_id": lid})
        r = await client.get("/api/stats/by-location", headers=auth)
        assert r.status_code == 200
        row = next(x for x in r.json() if x["location_id"] == lid)
        assert row["label"] == "1F / 客廳"


class TestByTag:
    async def test_default_limit_and_order(self, client, auth):
        await client.post("/api/items", headers=auth, json={"name": "a", "tag_names": ["red", "blue"]})
        await client.post("/api/items", headers=auth, json={"name": "b", "tag_names": ["red"]})
        r = await client.get("/api/stats/by-tag", headers=auth)
        assert r.status_code == 200
        rows = r.json()
        assert rows[0]["name"] == "red"
        assert rows[0]["count"] == 2

    async def test_limit_query_validation(self, client, auth):
        r = await client.get("/api/stats/by-tag?limit=51", headers=auth)
        assert r.status_code == 422
        r = await client.get("/api/stats/by-tag?limit=0", headers=auth)
        assert r.status_code == 422


class TestRecent:
    async def test_order_and_default_limit(self, client, auth):
        for i in range(7):
            await client.post("/api/items", headers=auth, json={"name": f"item{i}"})
        r = await client.get("/api/stats/recent", headers=auth)
        assert r.status_code == 200
        names = [i["name"] for i in r.json()]
        assert names[0] == "item6"
        assert len(names) == 5  # default limit

    async def test_custom_limit(self, client, auth):
        for i in range(3):
            await client.post("/api/items", headers=auth, json={"name": f"x{i}"})
        r = await client.get("/api/stats/recent?limit=2", headers=auth)
        assert len(r.json()) == 2

    async def test_limit_validation(self, client, auth):
        r = await client.get("/api/stats/recent?limit=21", headers=auth)
        assert r.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_stats_routes.py -v`
Expected: 404s / import error — routes not wired yet.

- [ ] **Step 3: Write the route module**

```python
# apps/api/app/routes/stats.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.item import ItemRead
from app.schemas.stats import (
    CategoryBucket,
    LocationBucket,
    OverviewStats,
    TagBucket,
)
from app.services import stats_service

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/overview", response_model=OverviewStats)
async def overview(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> OverviewStats:
    return await stats_service.get_overview(session, user.id)


@router.get("/by-category", response_model=list[CategoryBucket])
async def by_category(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[CategoryBucket]:
    return await stats_service.get_by_category(session, user.id)


@router.get("/by-location", response_model=list[LocationBucket])
async def by_location(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[LocationBucket]:
    return await stats_service.get_by_location(session, user.id)


@router.get("/by-tag", response_model=list[TagBucket])
async def by_tag(
    limit: int = Query(default=10, ge=1, le=50),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[TagBucket]:
    return await stats_service.get_by_tag(session, user.id, limit=limit)


@router.get("/recent", response_model=list[ItemRead])
async def recent(
    limit: int = Query(default=5, ge=1, le=20),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[ItemRead]:
    return await stats_service.get_recent(session, user.id, limit=limit)
```

- [ ] **Step 4: Wire router in `main.py`**

Edit `apps/api/app/main.py`:
```python
from app.routes import auth, categories, health, items, locations, stats, tags, users
# ...
app.include_router(items.router)
app.include_router(stats.router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_stats_routes.py -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/routes/stats.py apps/api/app/main.py apps/api/tests/test_stats_routes.py
git commit -m "feat(api): add /api/stats/* read-only endpoints"
```

---

## Task 8: Regenerate api-types

**Files:**
- Modify: `packages/api-types/openapi.json`
- Modify: `packages/api-types/src/index.ts`

- [ ] **Step 1: Run OpenAPI export + codegen**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/dashboard-stats
pnpm --filter @ims/api gen:types
pnpm --filter @ims/api-types gen:types
```

- [ ] **Step 2: Verify stats endpoints in generated types**

Run:
```bash
grep -E "/api/stats/(overview|by-category|by-location|by-tag|recent)" packages/api-types/openapi.json
```
Expected: 5 matches.

- [ ] **Step 3: Commit**

```bash
git add packages/api-types/
git commit -m "chore(api-types): regenerate for stats endpoints"
```

---

## Task 9: Web API client for stats

**Files:**
- Create: `apps/web/lib/api/stats.ts`

- [ ] **Step 1: Write the module**

```typescript
// apps/web/lib/api/stats.ts
import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

export type OverviewStats = paths["/api/stats/overview"]["get"]["responses"]["200"]["content"]["application/json"]
export type CategoryBucket = paths["/api/stats/by-category"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type LocationBucket = paths["/api/stats/by-location"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type TagBucket = paths["/api/stats/by-tag"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type RecentItem = paths["/api/stats/recent"]["get"]["responses"]["200"]["content"]["application/json"][number]

export async function getOverview(accessToken: string | null): Promise<OverviewStats> {
  const res = await apiFetch("/stats/overview", { accessToken })
  return (await res.json()) as OverviewStats
}

export async function getByCategory(accessToken: string | null): Promise<CategoryBucket[]> {
  const res = await apiFetch("/stats/by-category", { accessToken })
  return (await res.json()) as CategoryBucket[]
}

export async function getByLocation(accessToken: string | null): Promise<LocationBucket[]> {
  const res = await apiFetch("/stats/by-location", { accessToken })
  return (await res.json()) as LocationBucket[]
}

export async function getByTag(limit: number, accessToken: string | null): Promise<TagBucket[]> {
  const res = await apiFetch(`/stats/by-tag?limit=${limit}`, { accessToken })
  return (await res.json()) as TagBucket[]
}

export async function getRecent(limit: number, accessToken: string | null): Promise<RecentItem[]> {
  const res = await apiFetch(`/stats/recent?limit=${limit}`, { accessToken })
  return (await res.json()) as RecentItem[]
}
```

- [ ] **Step 2: Typecheck**

Run: `cd apps/web && pnpm typecheck`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add apps/web/lib/api/stats.ts
git commit -m "feat(web): add typed stats API client"
```

---

## Task 10: React Query hooks for stats

**Files:**
- Create: `apps/web/lib/hooks/use-stats.ts`

- [ ] **Step 1: Write the hooks**

```typescript
// apps/web/lib/hooks/use-stats.ts
"use client"

import { useQuery } from "@tanstack/react-query"

import * as api from "@/lib/api/stats"
import { useAccessToken } from "@/lib/auth/use-auth"

const STALE = 30_000

export function useOverview() {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["stats", "overview"],
    queryFn: () => api.getOverview(token),
    enabled: token !== null,
    staleTime: STALE,
  })
}

export function useByCategory() {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["stats", "by-category"],
    queryFn: () => api.getByCategory(token),
    enabled: token !== null,
    staleTime: STALE,
  })
}

export function useByLocation() {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["stats", "by-location"],
    queryFn: () => api.getByLocation(token),
    enabled: token !== null,
    staleTime: STALE,
  })
}

export function useByTag(limit = 10) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["stats", "by-tag", limit],
    queryFn: () => api.getByTag(limit, token),
    enabled: token !== null,
    staleTime: STALE,
  })
}

export function useRecent(limit = 5) {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["stats", "recent", limit],
    queryFn: () => api.getRecent(limit, token),
    enabled: token !== null,
    staleTime: STALE,
  })
}
```

- [ ] **Step 2: Typecheck**

Run: `cd apps/web && pnpm typecheck`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add apps/web/lib/hooks/use-stats.ts
git commit -m "feat(web): add React Query hooks for stats"
```

---

## Task 11: i18n messages for dashboard + stats + nav

**Files:**
- Modify: `apps/web/messages/en.json`
- Modify: `apps/web/messages/zh-TW.json`

- [ ] **Step 1: Update `en.json`**

Add inside existing `"nav"` object:
```json
"statistics": "Statistics"
```

Add new top-level `"dashboard"` and `"stats"` objects (next to existing `"items"`):
```json
"dashboard": {
  "title": "Dashboard",
  "overview": {
    "items": "Items",
    "quantity": "Total quantity",
    "categories": "Categories",
    "locations": "Locations"
  },
  "recent": {
    "title": "Recent items",
    "viewAll": "View all",
    "empty": "No items yet"
  },
  "quickLinks": {
    "items": "Manage items",
    "stats": "View statistics",
    "taxonomy": "Configure categories & locations"
  }
},
"stats": {
  "title": "Statistics",
  "byCategory": {
    "title": "By category",
    "uncategorized": "Uncategorized"
  },
  "byLocation": {
    "title": "By location",
    "unplaced": "Unplaced"
  },
  "byTag": {
    "title": "Top tags"
  },
  "empty": {
    "title": "No data yet",
    "cta": "Create some items first"
  }
}
```

- [ ] **Step 2: Update `zh-TW.json`**

Add inside existing `"nav"` object:
```json
"statistics": "統計"
```

Add:
```json
"dashboard": {
  "title": "儀表板",
  "overview": {
    "items": "物品",
    "quantity": "總數量",
    "categories": "分類",
    "locations": "位置"
  },
  "recent": {
    "title": "最近物品",
    "viewAll": "查看全部",
    "empty": "尚無物品"
  },
  "quickLinks": {
    "items": "管理物品",
    "stats": "查看統計",
    "taxonomy": "設定分類與位置"
  }
},
"stats": {
  "title": "統計",
  "byCategory": {
    "title": "依分類",
    "uncategorized": "未分類"
  },
  "byLocation": {
    "title": "依位置",
    "unplaced": "未定位"
  },
  "byTag": {
    "title": "熱門標籤"
  },
  "empty": {
    "title": "尚無資料",
    "cta": "先新增一些物品"
  }
}
```

- [ ] **Step 3: Verify both files parse**

Run: `cd apps/web && node -e "JSON.parse(require('fs').readFileSync('messages/en.json'))" && node -e "JSON.parse(require('fs').readFileSync('messages/zh-TW.json'))"`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add apps/web/messages/
git commit -m "feat(web): add i18n strings for dashboard + stats"
```

---

## Task 12: StatCard component

**Files:**
- Create: `apps/web/components/dashboard/stat-card.tsx`
- Test: `apps/web/components/dashboard/stat-card.test.tsx`

- [ ] **Step 1: Write the failing test**

```typescript
// apps/web/components/dashboard/stat-card.test.tsx
import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { StatCard } from "./stat-card"

describe("StatCard", () => {
  it("renders label and numeric value", () => {
    render(<StatCard label="Items" value={42} />)
    expect(screen.getByText("Items")).toBeInTheDocument()
    expect(screen.getByText("42")).toBeInTheDocument()
  })

  it("shows skeleton when loading", () => {
    const { container } = render(<StatCard label="Items" loading />)
    expect(container.querySelector('[data-slot="skeleton"]')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/web && pnpm vitest run components/dashboard/stat-card.test.tsx`
Expected: module not found.

- [ ] **Step 3: Write the component**

```tsx
// apps/web/components/dashboard/stat-card.tsx
import type { ReactNode } from "react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

interface Props {
  label: string
  value?: number
  icon?: ReactNode
  loading?: boolean
}

export function StatCard({ label, value, icon, loading }: Props) {
  return (
    <Card role="group" aria-label={label}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
        {icon ? <span className="text-muted-foreground">{icon}</span> : null}
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-16" />
        ) : (
          <div className="text-3xl font-semibold tabular-nums">{value ?? 0}</div>
        )}
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/web && pnpm vitest run components/dashboard/stat-card.test.tsx`
Expected: 2 passing.

- [ ] **Step 5: Commit**

```bash
git add apps/web/components/dashboard/stat-card.tsx apps/web/components/dashboard/stat-card.test.tsx
git commit -m "feat(web): add StatCard component"
```

---

## Task 13: RecentItemsCard component

**Files:**
- Create: `apps/web/components/dashboard/recent-items-card.tsx`
- Test: `apps/web/components/dashboard/recent-items-card.test.tsx`

- [ ] **Step 1: Write the failing test**

```typescript
// apps/web/components/dashboard/recent-items-card.test.tsx
import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it } from "vitest"

import enMessages from "@/messages/en.json"
import { RecentItemsCard } from "./recent-items-card"

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

describe("RecentItemsCard", () => {
  it("renders empty state when items is empty", () => {
    render(<RecentItemsCard items={[]} />, { wrapper: Provider })
    expect(screen.getByText("No items yet")).toBeInTheDocument()
  })

  it("lists item names when items provided", () => {
    render(
      <RecentItemsCard
        items={[
          { id: "a", name: "Apple" } as any,
          { id: "b", name: "Banana" } as any,
        ]}
      />,
      { wrapper: Provider },
    )
    expect(screen.getByText("Apple")).toBeInTheDocument()
    expect(screen.getByText("Banana")).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/web && pnpm vitest run components/dashboard/recent-items-card.test.tsx`
Expected: module not found.

- [ ] **Step 3: Write the component**

```tsx
// apps/web/components/dashboard/recent-items-card.tsx
import Link from "next/link"
import { useTranslations } from "next-intl"

import type { RecentItem } from "@/lib/api/stats"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface Props {
  items: RecentItem[]
}

export function RecentItemsCard({ items }: Props) {
  const t = useTranslations()
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>{t("dashboard.recent.title")}</CardTitle>
        <Button asChild variant="link" size="sm">
          <Link href="/items">{t("dashboard.recent.viewAll")}</Link>
        </Button>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("dashboard.recent.empty")}</p>
        ) : (
          <ul className="divide-y">
            {items.map((item) => (
              <li key={item.id} className="py-2">
                <Link
                  href={`/items/${item.id}` as never}
                  className="block hover:underline"
                >
                  {item.name}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/web && pnpm vitest run components/dashboard/recent-items-card.test.tsx`
Expected: 2 passing.

- [ ] **Step 5: Commit**

```bash
git add apps/web/components/dashboard/recent-items-card.tsx apps/web/components/dashboard/recent-items-card.test.tsx
git commit -m "feat(web): add RecentItemsCard component"
```

---

## Task 14: QuickLinks component

**Files:**
- Create: `apps/web/components/dashboard/quick-links.tsx`

- [ ] **Step 1: Write the component**

```tsx
// apps/web/components/dashboard/quick-links.tsx
import Link from "next/link"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"

const LINKS = [
  { href: "/items", key: "items" as const },
  { href: "/statistics", key: "stats" as const },
  { href: "/settings/taxonomy", key: "taxonomy" as const },
]

export function QuickLinks() {
  const t = useTranslations()
  return (
    <div className="flex flex-wrap gap-2">
      {LINKS.map(({ href, key }) => (
        <Button key={key} asChild variant="outline">
          <Link href={href as never}>{t(`dashboard.quickLinks.${key}`)}</Link>
        </Button>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/components/dashboard/quick-links.tsx
git commit -m "feat(web): add QuickLinks dashboard component"
```

---

## Task 15: Dashboard page

**Files:**
- Modify: `apps/web/app/(app)/dashboard/page.tsx` (replace entirely)

- [ ] **Step 1: Replace the page**

```tsx
// apps/web/app/(app)/dashboard/page.tsx
"use client"

import { useTranslations } from "next-intl"

import { QuickLinks } from "@/components/dashboard/quick-links"
import { RecentItemsCard } from "@/components/dashboard/recent-items-card"
import { StatCard } from "@/components/dashboard/stat-card"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb"
import { useOverview, useRecent } from "@/lib/hooks/use-stats"

export default function DashboardPage() {
  const t = useTranslations()
  const overview = useOverview()
  const recent = useRecent(5)

  return (
    <section className="space-y-6 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>{t("nav.dashboard")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div>
        <h1 className="text-2xl font-semibold">{t("dashboard.title")}</h1>
      </div>

      <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
        <StatCard
          label={t("dashboard.overview.items")}
          value={overview.data?.total_items}
          loading={overview.isLoading}
        />
        <StatCard
          label={t("dashboard.overview.quantity")}
          value={overview.data?.total_quantity}
          loading={overview.isLoading}
        />
        <StatCard
          label={t("dashboard.overview.categories")}
          value={overview.data?.total_categories}
          loading={overview.isLoading}
        />
        <StatCard
          label={t("dashboard.overview.locations")}
          value={overview.data?.total_locations}
          loading={overview.isLoading}
        />
      </div>

      <RecentItemsCard items={recent.data ?? []} />

      <QuickLinks />
    </section>
  )
}
```

- [ ] **Step 2: Typecheck**

Run: `cd apps/web && pnpm typecheck`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add apps/web/app/\(app\)/dashboard/page.tsx
git commit -m "feat(web): implement dashboard page with overview + recent items"
```

---

## Task 16: EmptyChart shared component

**Files:**
- Create: `apps/web/components/stats/empty-chart.tsx`

- [ ] **Step 1: Write the component**

```tsx
// apps/web/components/stats/empty-chart.tsx
import { useTranslations } from "next-intl"

export function EmptyChart() {
  const t = useTranslations()
  return (
    <div className="flex h-48 flex-col items-center justify-center rounded border border-dashed text-center">
      <p className="text-sm font-medium">{t("stats.empty.title")}</p>
      <p className="mt-1 text-xs text-muted-foreground">{t("stats.empty.cta")}</p>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/components/stats/empty-chart.tsx
git commit -m "feat(web): add shared EmptyChart component"
```

---

## Task 17: Add recharts dependency

**Files:**
- Modify: `apps/web/package.json`

- [ ] **Step 1: Install recharts**

Run:
```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/dashboard-stats
pnpm add --filter @ims/web recharts@^2.12.7
```

- [ ] **Step 2: Verify package.json updated**

Run: `grep recharts apps/web/package.json`
Expected: `"recharts": "^2.12.7"`.

- [ ] **Step 3: Commit**

```bash
git add apps/web/package.json pnpm-lock.yaml
git commit -m "chore(web): add recharts dependency"
```

---

## Task 18: CategoryChart (doughnut)

**Files:**
- Create: `apps/web/components/stats/category-chart.tsx`

- [ ] **Step 1: Write the component**

```tsx
// apps/web/components/stats/category-chart.tsx
"use client"

import { useTranslations } from "next-intl"
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { EmptyChart } from "@/components/stats/empty-chart"
import type { CategoryBucket } from "@/lib/api/stats"

const PALETTE = [
  "#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed",
  "#0891b2", "#db2777", "#65a30d", "#ea580c", "#475569",
]

interface Props {
  buckets: CategoryBucket[]
  loading?: boolean
}

export function CategoryChart({ buckets, loading }: Props) {
  const t = useTranslations()
  const data = buckets.map((b) => ({
    name: b.name ?? t("stats.byCategory.uncategorized"),
    value: b.count,
  }))
  const empty = !loading && data.length === 0

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("stats.byCategory.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        {empty ? (
          <EmptyChart />
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={data} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80}>
                {data.map((_, i) => (
                  <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/components/stats/category-chart.tsx
git commit -m "feat(web): add CategoryChart (doughnut) component"
```

---

## Task 19: LocationChart (vertical bar)

**Files:**
- Create: `apps/web/components/stats/location-chart.tsx`

- [ ] **Step 1: Write the component**

```tsx
// apps/web/components/stats/location-chart.tsx
"use client"

import { useTranslations } from "next-intl"
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { EmptyChart } from "@/components/stats/empty-chart"
import type { LocationBucket } from "@/lib/api/stats"

interface Props {
  buckets: LocationBucket[]
  loading?: boolean
}

export function LocationChart({ buckets, loading }: Props) {
  const t = useTranslations()
  const data = buckets.map((b) => ({
    name: b.label ?? t("stats.byLocation.unplaced"),
    count: b.count,
  }))
  const empty = !loading && data.length === 0

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("stats.byLocation.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        {empty ? (
          <EmptyChart />
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" interval={0} tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#2563eb" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/components/stats/location-chart.tsx
git commit -m "feat(web): add LocationChart (bar) component"
```

---

## Task 20: TagChart (horizontal bar)

**Files:**
- Create: `apps/web/components/stats/tag-chart.tsx`

- [ ] **Step 1: Write the component**

```tsx
// apps/web/components/stats/tag-chart.tsx
"use client"

import { useTranslations } from "next-intl"
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { EmptyChart } from "@/components/stats/empty-chart"
import type { TagBucket } from "@/lib/api/stats"

interface Props {
  buckets: TagBucket[]
  loading?: boolean
}

export function TagChart({ buckets, loading }: Props) {
  const t = useTranslations()
  const data = buckets.map((b) => ({ name: b.name, count: b.count }))
  const empty = !loading && data.length === 0

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("stats.byTag.title")}</CardTitle>
      </CardHeader>
      <CardContent>
        {empty ? (
          <EmptyChart />
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(240, data.length * 28)}>
            <BarChart data={data} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" allowDecimals={false} />
              <YAxis dataKey="name" type="category" width={80} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#16a34a" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/components/stats/tag-chart.tsx
git commit -m "feat(web): add TagChart (horizontal bar) component"
```

---

## Task 21: Statistics page

**Files:**
- Create: `apps/web/app/(app)/statistics/page.tsx`

- [ ] **Step 1: Write the page**

```tsx
// apps/web/app/(app)/statistics/page.tsx
"use client"

import { useTranslations } from "next-intl"

import { CategoryChart } from "@/components/stats/category-chart"
import { LocationChart } from "@/components/stats/location-chart"
import { TagChart } from "@/components/stats/tag-chart"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { useByCategory, useByLocation, useByTag } from "@/lib/hooks/use-stats"

export default function StatisticsPage() {
  const t = useTranslations()
  const cats = useByCategory()
  const locs = useByLocation()
  const tags = useByTag(10)

  return (
    <section className="space-y-6 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink href="/dashboard">{t("nav.dashboard")}</BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>{t("stats.title")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <h1 className="text-2xl font-semibold">{t("stats.title")}</h1>

      <div className="grid gap-4 md:grid-cols-2">
        <CategoryChart buckets={cats.data ?? []} loading={cats.isLoading} />
        <LocationChart buckets={locs.data ?? []} loading={locs.isLoading} />
      </div>

      <TagChart buckets={tags.data ?? []} loading={tags.isLoading} />
    </section>
  )
}
```

- [ ] **Step 2: Typecheck + build**

Run:
```bash
cd apps/web && pnpm typecheck && pnpm build
```
Expected: success; output lists `/statistics` and `/dashboard` routes.

- [ ] **Step 3: Commit**

```bash
git add apps/web/app/\(app\)/statistics/page.tsx
git commit -m "feat(web): add statistics page with three charts"
```

---

## Task 22: Add Statistics to nav

**Files:**
- Modify: `apps/web/components/shell/nav-items.ts`

- [ ] **Step 1: Extend NAV_ITEMS and broaden key union**

Replace content:
```typescript
import type { Route } from "next"

export interface NavItem {
  key: "dashboard" | "items" | "statistics" | "lists" | "settings"
  href: Route
  /** i18n key for label */
  labelKey: string
}

export const NAV_ITEMS: readonly NavItem[] = [
  { key: "dashboard", href: "/dashboard", labelKey: "nav.dashboard" },
  { key: "items", href: "/items", labelKey: "nav.items" },
  { key: "statistics", href: "/statistics", labelKey: "nav.statistics" },
  { key: "lists", href: "/lists", labelKey: "nav.lists" },
  { key: "settings", href: "/settings", labelKey: "nav.settings" },
]
```

- [ ] **Step 2: Typecheck**

Run: `cd apps/web && pnpm typecheck`
Expected: no errors (existing usages of `NavItem` in header/drawer are key-agnostic).

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/shell/nav-items.ts
git commit -m "feat(web): add statistics to primary navigation"
```

---

## Task 23: Dashboard E2E

**Files:**
- Create: `apps/web/tests/dashboard.spec.ts`

- [ ] **Step 1: Write the spec**

```typescript
// apps/web/tests/dashboard.spec.ts
import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()

async function register(request: import("@playwright/test").APIRequestContext, username: string) {
  await request.post("/api/auth/register", {
    data: { email: `${username}@t.io`, username, password: "secret1234" },
  })
}

async function loginUi(page: import("@playwright/test").Page, username: string) {
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill("secret1234")
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
}

test("landing redirects to dashboard when logged in", async ({ page, request }) => {
  const u = `dash_${unique()}`
  await register(request, u)
  await loginUi(page, u)
  await page.goto("/")
  await page.waitForURL("**/dashboard")
  await expect(page.getByRole("heading", { name: "儀表板" })).toBeVisible()
})

test("dashboard shows stat cards and recent items", async ({ page, request }) => {
  const u = `dash2_${unique()}`
  await register(request, u)
  await loginUi(page, u)

  // Empty state
  await expect(page.getByRole("group", { name: "物品" })).toBeVisible()
  await expect(page.getByText("尚無物品")).toBeVisible()

  // Create an item via API, then reload dashboard
  const login = await request.post("/api/auth/login", {
    data: { username: u, password: "secret1234" },
  })
  const token = login.json ? (await login.json()).access_token : ""
  await request.post("/api/items", {
    headers: { Authorization: `Bearer ${token}` },
    data: { name: "測試物品", quantity: 3 },
  })

  await page.reload()
  await expect(page.getByText("測試物品")).toBeVisible()
})

test("view all on recent card navigates to items", async ({ page, request }) => {
  const u = `dash3_${unique()}`
  await register(request, u)
  await loginUi(page, u)
  await page.getByRole("link", { name: "查看全部" }).click()
  await page.waitForURL("**/items")
})
```

- [ ] **Step 2: Commit (tests not executed now — run separately)**

```bash
git add apps/web/tests/dashboard.spec.ts
git commit -m "test(e2e): add dashboard redirect + stat card + recent items flows"
```

---

## Task 24: Statistics E2E

**Files:**
- Create: `apps/web/tests/statistics.spec.ts`

- [ ] **Step 1: Write the spec**

```typescript
// apps/web/tests/statistics.spec.ts
import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()

async function register(request: import("@playwright/test").APIRequestContext, username: string) {
  await request.post("/api/auth/register", {
    data: { email: `${username}@t.io`, username, password: "secret1234" },
  })
}

async function loginUi(page: import("@playwright/test").Page, username: string) {
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill("secret1234")
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
}

test("statistics page shows three chart cards", async ({ page, request }) => {
  const u = `stat_${unique()}`
  await register(request, u)
  await loginUi(page, u)
  await page.goto("/statistics")
  await expect(page.getByRole("heading", { name: "依分類" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "依位置" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "熱門標籤" })).toBeVisible()
})

test("empty DB shows empty state in each chart", async ({ page, request }) => {
  const u = `stat2_${unique()}`
  await register(request, u)
  await loginUi(page, u)
  await page.goto("/statistics")
  // 3 empty states, one per chart
  await expect(page.getByText("尚無資料")).toHaveCount(3)
})
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/tests/statistics.spec.ts
git commit -m "test(e2e): add statistics page chart + empty state flows"
```

---

## Task 25: Mark roadmap done

**Files:**
- Modify: `docs/v2-roadmap.md`

- [ ] **Step 1: Flip #4 row**

Change line 13 from:
```markdown
| 4 | 儀表板與統計 | ⏳ 未開始 |
```
to:
```markdown
| 4 | 儀表板與統計 | ✅ 完成 |
```

- [ ] **Step 2: Commit**

```bash
git add docs/v2-roadmap.md
git commit -m "docs: mark #4 dashboard + statistics subproject complete"
```

---

## Final Verification

After Task 25, run full gates:

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/dashboard-stats
cd apps/api && .venv/bin/python -m pytest -q && cd ../..
cd apps/web && pnpm typecheck && pnpm test && pnpm build && cd ../..
```

Expected:
- API pytest: all passing (prior 101 + new stats tests)
- Web typecheck: 0 errors
- Web vitest: all passing (prior 36 + 4 new dashboard tests)
- Web build: successful (output includes `/dashboard` and `/statistics` routes)

E2E (manual, requires API + web dev servers running):
```bash
pnpm --filter @ims/web e2e
```
