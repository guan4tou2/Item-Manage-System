# Notification Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship an in-app notification inbox with a generic `emit()` service and two producers (low-stock, welcome), plus header bell + dedicated page.

**Architecture:** Standard FastAPI layering — new `Notification` model → repository → service (with `emit()`) → `/api/notifications` router. Item model gains a nullable `min_quantity` column; `items_service` calls `emit()` when quantity transitions across that threshold. Auth register route calls `emit()` for welcome. Frontend adds an API client, React Query hooks, a bell badge in the header, and a `/notifications` page.

**Tech Stack:** FastAPI 0.115 · SQLAlchemy 2.0 async · Pydantic v2 · Alembic · Next.js 15 App Router · React 19 · TanStack Query v5 · next-intl 3.21 · shadcn UI · Vitest · Playwright.

**Worktree:** `.claude/worktrees/notification-center` · **Branch:** `claude/notification-center` · **Baseline:** API 126/126, web 40/40 vitest, typecheck clean.

**Spec:** `docs/superpowers/specs/2026-04-23-notification-center-design.md`

---

## Conventions (all tasks)

- Run API commands from `.claude/worktrees/notification-center/apps/api` with `.venv/bin/python -m pytest …`
- Run web commands from `.claude/worktrees/notification-center/apps/web`
- Commit after each task; use `cd` chains since shell state does not persist between Bash calls
- TDD: failing test → run to fail → implement → run to pass → commit

---

## Task 1: Notification model

**Files:**
- Create: `apps/api/app/models/notification.py`
- Modify: `apps/api/app/models/__init__.py`
- Create: `apps/api/tests/test_notification_model_smoke.py`

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/test_notification_model_smoke.py`:
```python
from __future__ import annotations

import pytest

from app.models.notification import Notification


async def test_notification_row_roundtrip(db_session):
    from app.models.user import User
    from app.auth.password import hash_password

    user = User(email="n@t.io", username="n_user", password_hash=hash_password("secret1234"))
    db_session.add(user)
    await db_session.flush()

    n = Notification(
        user_id=user.id,
        type="system.welcome",
        title="歡迎",
        body="從儀表板開始。",
        link="/dashboard",
    )
    db_session.add(n)
    await db_session.commit()
    await db_session.refresh(n)

    assert n.id is not None
    assert n.user_id == user.id
    assert n.type == "system.welcome"
    assert n.read_at is None
    assert n.created_at is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && .venv/bin/python -m pytest tests/test_notification_model_smoke.py -v`
Expected: `ModuleNotFoundError: No module named 'app.models.notification'`

- [ ] **Step 3: Create the model**

Create `apps/api/app/models/notification.py`:
```python
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, _utcnow
from app.models.user import GUID


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )
```

- [ ] **Step 4: Export from models package**

Modify `apps/api/app/models/__init__.py` so it reads:
```python
from app.models.category import Category
from app.models.item import Item
from app.models.location import Location
from app.models.notification import Notification
from app.models.tag import Tag, item_tags
from app.models.user import User

__all__ = ["User", "Item", "Category", "Location", "Tag", "item_tags", "Notification"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd apps/api && .venv/bin/python -m pytest tests/test_notification_model_smoke.py -v`
Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
git add apps/api/app/models/notification.py apps/api/app/models/__init__.py apps/api/tests/test_notification_model_smoke.py
git commit -m "feat(api): add Notification ORM model"
```

---

## Task 2: Item.min_quantity field

**Files:**
- Modify: `apps/api/app/models/item.py`
- Create: `apps/api/tests/test_item_min_quantity_smoke.py`

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/test_item_min_quantity_smoke.py`:
```python
from __future__ import annotations

import pytest

from app.auth.password import hash_password
from app.models.item import Item
from app.models.user import User


async def test_item_stores_min_quantity(db_session):
    user = User(email="m@t.io", username="m_user", password_hash=hash_password("secret1234"))
    db_session.add(user)
    await db_session.flush()

    item = Item(owner_id=user.id, name="便當盒", quantity=5, min_quantity=2)
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    assert item.min_quantity == 2


async def test_item_min_quantity_defaults_to_none(db_session):
    user = User(email="m2@t.io", username="m2_user", password_hash=hash_password("secret1234"))
    db_session.add(user)
    await db_session.flush()

    item = Item(owner_id=user.id, name="筷子", quantity=1)
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    assert item.min_quantity is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && .venv/bin/python -m pytest tests/test_item_min_quantity_smoke.py -v`
Expected: `TypeError: 'min_quantity' is an invalid keyword argument for Item`

- [ ] **Step 3: Add the column**

Modify `apps/api/app/models/item.py`. Change `__table_args__` and add the column:
```python
class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_items_quantity_nonneg"),
        CheckConstraint(
            "min_quantity IS NULL OR min_quantity >= 0",
            name="ck_items_min_quantity_nonneg",
        ),
    )

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"), default=1)
    min_quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="items")  # noqa: F821
    location: Mapped[Optional["Location"]] = relationship("Location", back_populates="items")  # noqa: F821
    tags: Mapped[list["Tag"]] = relationship("Tag", secondary="item_tags", back_populates="items")  # noqa: F821
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/api && .venv/bin/python -m pytest tests/test_item_min_quantity_smoke.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
git add apps/api/app/models/item.py apps/api/tests/test_item_min_quantity_smoke.py
git commit -m "feat(api): add Item.min_quantity column"
```

---

## Task 3: Alembic migration 0004

**Files:**
- Create: `apps/api/alembic/versions/0004_notifications_and_min_quantity.py`

- [ ] **Step 1: Verify current head**

Run: `cd apps/api && .venv/bin/python -m alembic heads`
Expected: `0003 (head)`

- [ ] **Step 2: Write the migration**

Create `apps/api/alembic/versions/0004_notifications_and_min_quantity.py`:
```python
"""notifications table + items.min_quantity

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-23 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("link", sa.String(length=500), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index(
        "ix_notifications_created_at", "notifications", ["created_at"]
    )

    op.add_column(
        "items",
        sa.Column("min_quantity", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_items_min_quantity_nonneg",
        "items",
        "min_quantity IS NULL OR min_quantity >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_items_min_quantity_nonneg", "items", type_="check")
    op.drop_column("items", "min_quantity")
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
```

- [ ] **Step 3: Verify heads and offline SQL render**

Run: `cd apps/api && .venv/bin/python -m alembic heads`
Expected: `0004 (head)`

Run: `cd apps/api && .venv/bin/python -m alembic upgrade 0004 --sql 2>&1 | head -40`
Expected: Valid DDL output includes `CREATE TABLE notifications` and `ALTER TABLE items ADD COLUMN min_quantity`.

- [ ] **Step 4: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
git add apps/api/alembic/versions/0004_notifications_and_min_quantity.py
git commit -m "feat(api): migration 0004 — notifications table + items.min_quantity"
```

---

## Task 4: Notification schemas

**Files:**
- Create: `apps/api/app/schemas/notification.py`
- Create: `apps/api/tests/test_notification_schemas.py`

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/test_notification_schemas.py`:
```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.schemas.notification import (
    NotificationListResponse,
    NotificationRead,
    UnreadCountResponse,
)


def test_notification_read_serialises_minimal():
    n = NotificationRead(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        type="system.welcome",
        title="歡迎",
        body=None,
        link="/dashboard",
        read_at=None,
        created_at=datetime.now(timezone.utc),
    )
    dumped = n.model_dump()
    assert dumped["type"] == "system.welcome"
    assert dumped["body"] is None


def test_notification_list_response_shape():
    resp = NotificationListResponse(items=[], total=0, unread_count=0)
    assert resp.items == []
    assert resp.total == 0
    assert resp.unread_count == 0


def test_unread_count_response_shape():
    resp = UnreadCountResponse(count=3)
    assert resp.count == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && .venv/bin/python -m pytest tests/test_notification_schemas.py -v`
Expected: `ModuleNotFoundError: No module named 'app.schemas.notification'`

- [ ] **Step 3: Create the schemas**

Create `apps/api/app/schemas/notification.py`:
```python
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    id: UUID
    user_id: UUID
    type: str
    title: str
    body: Optional[str]
    link: Optional[str]
    read_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: list[NotificationRead]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    count: int


class MarkAllReadResponse(BaseModel):
    marked: int
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/api && .venv/bin/python -m pytest tests/test_notification_schemas.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
git add apps/api/app/schemas/notification.py apps/api/tests/test_notification_schemas.py
git commit -m "feat(api): add Notification Pydantic schemas"
```

---

## Task 5: Notifications repository

**Files:**
- Create: `apps/api/app/repositories/notifications_repository.py`
- Create: `apps/api/tests/test_notifications_repository.py`

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/test_notifications_repository.py`:
```python
from __future__ import annotations

import pytest

from app.auth.password import hash_password
from app.models.notification import Notification
from app.models.user import User
from app.repositories import notifications_repository as repo


@pytest.fixture
async def two_users(db_session):
    a = User(email="a@t.io", username="a_user", password_hash=hash_password("secret1234"))
    b = User(email="b@t.io", username="b_user", password_hash=hash_password("secret1234"))
    db_session.add_all([a, b])
    await db_session.flush()
    return a, b


async def test_create_persists_row(db_session, two_users):
    a, _ = two_users
    n = await repo.create(
        db_session,
        user_id=a.id,
        type="system.welcome",
        title="歡迎",
        body=None,
        link="/dashboard",
    )
    assert n.id is not None
    assert n.read_at is None


async def test_list_paginated_owner_scoped_desc(db_session, two_users):
    a, b = two_users
    n1 = await repo.create(db_session, user_id=a.id, type="t", title="A1")
    n2 = await repo.create(db_session, user_id=a.id, type="t", title="A2")
    await repo.create(db_session, user_id=b.id, type="t", title="B1")

    rows, total, unread_count = await repo.list_paginated(
        db_session, a.id, unread_only=False, limit=10, offset=0
    )
    assert [r.title for r in rows] == ["A2", "A1"]
    assert total == 2
    assert unread_count == 2


async def test_list_unread_only_filters(db_session, two_users):
    a, _ = two_users
    read_row = await repo.create(db_session, user_id=a.id, type="t", title="read")
    await repo.mark_read(db_session, a.id, read_row.id)
    await repo.create(db_session, user_id=a.id, type="t", title="unread")

    rows, total, unread = await repo.list_paginated(
        db_session, a.id, unread_only=True, limit=10, offset=0
    )
    assert [r.title for r in rows] == ["unread"]
    assert total == 1
    assert unread == 1


async def test_list_pagination(db_session, two_users):
    a, _ = two_users
    for i in range(5):
        await repo.create(db_session, user_id=a.id, type="t", title=f"n{i}")
    page1, total, _ = await repo.list_paginated(db_session, a.id, unread_only=False, limit=2, offset=0)
    page2, _, _ = await repo.list_paginated(db_session, a.id, unread_only=False, limit=2, offset=2)
    assert total == 5
    assert len(page1) == 2
    assert len(page2) == 2
    # newest first
    assert page1[0].title == "n4"
    assert page2[0].title == "n2"


async def test_unread_count(db_session, two_users):
    a, _ = two_users
    r1 = await repo.create(db_session, user_id=a.id, type="t", title="x")
    await repo.create(db_session, user_id=a.id, type="t", title="y")
    await repo.mark_read(db_session, a.id, r1.id)
    assert await repo.unread_count(db_session, a.id) == 1


async def test_mark_read_is_idempotent(db_session, two_users):
    a, _ = two_users
    n = await repo.create(db_session, user_id=a.id, type="t", title="x")
    first = await repo.mark_read(db_session, a.id, n.id)
    original = first.read_at
    second = await repo.mark_read(db_session, a.id, n.id)
    assert second.read_at == original


async def test_mark_read_other_owner_returns_none(db_session, two_users):
    a, b = two_users
    n = await repo.create(db_session, user_id=b.id, type="t", title="x")
    assert await repo.mark_read(db_session, a.id, n.id) is None


async def test_mark_all_read_counts_only_unread(db_session, two_users):
    a, _ = two_users
    r1 = await repo.create(db_session, user_id=a.id, type="t", title="x")
    await repo.mark_read(db_session, a.id, r1.id)
    await repo.create(db_session, user_id=a.id, type="t", title="y")
    await repo.create(db_session, user_id=a.id, type="t", title="z")
    marked = await repo.mark_all_read(db_session, a.id)
    assert marked == 2
    assert await repo.unread_count(db_session, a.id) == 0


async def test_delete_owner_scoped(db_session, two_users):
    a, b = two_users
    n_a = await repo.create(db_session, user_id=a.id, type="t", title="x")
    n_b = await repo.create(db_session, user_id=b.id, type="t", title="y")
    assert await repo.delete(db_session, a.id, n_a.id) is True
    assert await repo.delete(db_session, a.id, n_b.id) is False
    # Confirm B still has its row
    rows, total, _ = await repo.list_paginated(db_session, b.id, unread_only=False, limit=10, offset=0)
    assert total == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && .venv/bin/python -m pytest tests/test_notifications_repository.py -v`
Expected: `ModuleNotFoundError: No module named 'app.repositories.notifications_repository'`

- [ ] **Step 3: Create the repository**

Create `apps/api/app/repositories/notifications_repository.py`:
```python
from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import _utcnow
from app.models.notification import Notification


async def create(
    session: AsyncSession,
    *,
    user_id: UUID,
    type: str,
    title: str,
    body: str | None = None,
    link: str | None = None,
) -> Notification:
    n = Notification(
        user_id=user_id, type=type, title=title, body=body, link=link
    )
    session.add(n)
    await session.commit()
    await session.refresh(n)
    return n


async def list_paginated(
    session: AsyncSession,
    user_id: UUID,
    *,
    unread_only: bool,
    limit: int,
    offset: int,
) -> tuple[list[Notification], int, int]:
    base = select(Notification).where(Notification.user_id == user_id)
    count_base = select(func.count(Notification.id)).where(Notification.user_id == user_id)
    if unread_only:
        base = base.where(Notification.read_at.is_(None))
        count_base = count_base.where(Notification.read_at.is_(None))

    total = (await session.execute(count_base)).scalar_one()
    unread = (await session.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id, Notification.read_at.is_(None)
        )
    )).scalar_one()

    stmt = base.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows), int(total), int(unread)


async def unread_count(session: AsyncSession, user_id: UUID) -> int:
    stmt = select(func.count(Notification.id)).where(
        Notification.user_id == user_id, Notification.read_at.is_(None)
    )
    return int((await session.execute(stmt)).scalar_one())


async def mark_read(
    session: AsyncSession, user_id: UUID, notification_id: UUID
) -> Notification | None:
    stmt = select(Notification).where(
        Notification.id == notification_id, Notification.user_id == user_id
    )
    n = (await session.execute(stmt)).scalar_one_or_none()
    if n is None:
        return None
    if n.read_at is None:
        n.read_at = _utcnow()
        await session.commit()
        await session.refresh(n)
    return n


async def mark_all_read(session: AsyncSession, user_id: UUID) -> int:
    stmt = (
        update(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        .values(read_at=_utcnow())
    )
    result = await session.execute(stmt)
    await session.commit()
    return int(result.rowcount or 0)


async def delete(
    session: AsyncSession, user_id: UUID, notification_id: UUID
) -> bool:
    stmt = sa_delete(Notification).where(
        Notification.id == notification_id, Notification.user_id == user_id
    )
    result = await session.execute(stmt)
    await session.commit()
    return (result.rowcount or 0) > 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/api && .venv/bin/python -m pytest tests/test_notifications_repository.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
git add apps/api/app/repositories/notifications_repository.py apps/api/tests/test_notifications_repository.py
git commit -m "feat(api): add notifications repository with pagination + owner isolation"
```

---

## Task 6: Notifications service with emit()

**Files:**
- Create: `apps/api/app/services/notifications_service.py`
- Create: `apps/api/tests/test_notifications_service.py`

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/test_notifications_service.py`:
```python
from __future__ import annotations

import pytest

from app.auth.password import hash_password
from app.models.user import User
from app.services import notifications_service as svc


@pytest.fixture
async def user(db_session):
    u = User(email="s@t.io", username="s_user", password_hash=hash_password("secret1234"))
    db_session.add(u)
    await db_session.flush()
    return u


async def test_emit_creates_notification(db_session, user):
    n = await svc.emit(
        db_session,
        user_id=user.id,
        type="system.welcome",
        title="歡迎",
        body="開始吧",
        link="/dashboard",
    )
    assert n is not None
    assert n.type == "system.welcome"


async def test_emit_returns_none_on_failure(db_session, user, monkeypatch):
    from app.repositories import notifications_repository as repo

    async def boom(*_args, **_kwargs):
        raise RuntimeError("db blew up")

    monkeypatch.setattr(repo, "create", boom)
    # Must NOT raise
    n = await svc.emit(
        db_session,
        user_id=user.id,
        type="low_stock",
        title="x",
    )
    assert n is None


async def test_list_service_delegates(db_session, user):
    await svc.emit(db_session, user_id=user.id, type="t", title="a")
    await svc.emit(db_session, user_id=user.id, type="t", title="b")
    resp = await svc.list_notifications(db_session, user.id, unread_only=False, limit=10, offset=0)
    assert resp.total == 2
    assert resp.unread_count == 2
    assert [n.title for n in resp.items] == ["b", "a"]


async def test_get_unread_count(db_session, user):
    await svc.emit(db_session, user_id=user.id, type="t", title="a")
    await svc.emit(db_session, user_id=user.id, type="t", title="b")
    resp = await svc.get_unread_count(db_session, user.id)
    assert resp.count == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && .venv/bin/python -m pytest tests/test_notifications_service.py -v`
Expected: `ModuleNotFoundError: No module named 'app.services.notifications_service'`

- [ ] **Step 3: Create the service**

Create `apps/api/app/services/notifications_service.py`:
```python
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.repositories import notifications_repository as repo
from app.schemas.notification import (
    MarkAllReadResponse,
    NotificationListResponse,
    NotificationRead,
    UnreadCountResponse,
)

logger = logging.getLogger(__name__)


async def emit(
    session: AsyncSession,
    *,
    user_id: UUID,
    type: str,
    title: str,
    body: str | None = None,
    link: str | None = None,
) -> Notification | None:
    """Create a notification. Swallows errors and returns None to avoid
    breaking the triggering transaction."""
    try:
        return await repo.create(
            session,
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            link=link,
        )
    except Exception:
        logger.warning("notification emit failed", exc_info=True, extra={"type": type, "user_id": str(user_id)})
        return None


async def list_notifications(
    session: AsyncSession,
    user_id: UUID,
    *,
    unread_only: bool,
    limit: int,
    offset: int,
) -> NotificationListResponse:
    rows, total, unread = await repo.list_paginated(
        session, user_id, unread_only=unread_only, limit=limit, offset=offset
    )
    return NotificationListResponse(
        items=[NotificationRead.model_validate(r) for r in rows],
        total=total,
        unread_count=unread,
    )


async def get_unread_count(session: AsyncSession, user_id: UUID) -> UnreadCountResponse:
    return UnreadCountResponse(count=await repo.unread_count(session, user_id))


async def mark_read(
    session: AsyncSession, user_id: UUID, notification_id: UUID
) -> NotificationRead | None:
    n = await repo.mark_read(session, user_id, notification_id)
    return NotificationRead.model_validate(n) if n is not None else None


async def mark_all_read(
    session: AsyncSession, user_id: UUID
) -> MarkAllReadResponse:
    return MarkAllReadResponse(marked=await repo.mark_all_read(session, user_id))


async def delete(
    session: AsyncSession, user_id: UUID, notification_id: UUID
) -> bool:
    return await repo.delete(session, user_id, notification_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/api && .venv/bin/python -m pytest tests/test_notifications_service.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
git add apps/api/app/services/notifications_service.py apps/api/tests/test_notifications_service.py
git commit -m "feat(api): add notifications service with fail-soft emit()"
```

---

## Task 7: Notifications routes

**Files:**
- Create: `apps/api/app/routes/notifications.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/api/tests/test_notifications_routes.py`

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/test_notifications_routes.py`:
```python
from __future__ import annotations

import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={
        "email": "n@t.io", "username": "n_user", "password": "secret1234",
    })
    r = await client.post("/api/auth/login", json={
        "username": "n_user", "password": "secret1234",
    })
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def other_auth(client):
    await client.post("/api/auth/register", json={
        "email": "o@t.io", "username": "o_user", "password": "secret1234",
    })
    r = await client.post("/api/auth/login", json={
        "username": "o_user", "password": "secret1234",
    })
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


class TestAuth:
    async def test_list_requires_auth(self, client):
        r = await client.get("/api/notifications")
        assert r.status_code == 401

    async def test_unread_count_requires_auth(self, client):
        r = await client.get("/api/notifications/unread-count")
        assert r.status_code == 401


class TestList:
    async def test_empty(self, client, auth):
        r = await client.get("/api/notifications", headers=auth)
        assert r.status_code == 200
        assert r.json() == {"items": [], "total": 0, "unread_count": 0}

    async def test_after_welcome_on_register(self, client, auth):
        # register already emitted welcome in Task 8
        r = await client.get("/api/notifications", headers=auth)
        body = r.json()
        assert body["total"] >= 1

    async def test_limit_validation_zero_rejected(self, client, auth):
        r = await client.get("/api/notifications?limit=0", headers=auth)
        assert r.status_code == 422

    async def test_limit_validation_too_large_rejected(self, client, auth):
        r = await client.get("/api/notifications?limit=200", headers=auth)
        assert r.status_code == 422


class TestUnreadCount:
    async def test_returns_int(self, client, auth):
        r = await client.get("/api/notifications/unread-count", headers=auth)
        assert r.status_code == 200
        assert isinstance(r.json()["count"], int)


class TestMarkRead:
    async def test_marks_own_notification(self, client, auth):
        lst = (await client.get("/api/notifications", headers=auth)).json()
        if not lst["items"]:
            pytest.skip("welcome not yet wired")
        nid = lst["items"][0]["id"]
        r = await client.patch(f"/api/notifications/{nid}/read", headers=auth)
        assert r.status_code == 200
        assert r.json()["read_at"] is not None

    async def test_other_owner_returns_404(self, client, auth, other_auth):
        other_list = (await client.get("/api/notifications", headers=other_auth)).json()
        if not other_list["items"]:
            pytest.skip("welcome not yet wired")
        nid = other_list["items"][0]["id"]
        r = await client.patch(f"/api/notifications/{nid}/read", headers=auth)
        assert r.status_code == 404


class TestMarkAllRead:
    async def test_returns_marked_count(self, client, auth):
        r = await client.post("/api/notifications/mark-all-read", headers=auth)
        assert r.status_code == 200
        assert "marked" in r.json()


class TestDelete:
    async def test_delete_own_204(self, client, auth):
        lst = (await client.get("/api/notifications", headers=auth)).json()
        if not lst["items"]:
            pytest.skip("welcome not yet wired")
        nid = lst["items"][0]["id"]
        r = await client.delete(f"/api/notifications/{nid}", headers=auth)
        assert r.status_code == 204

    async def test_delete_other_owner_404(self, client, auth, other_auth):
        other_list = (await client.get("/api/notifications", headers=other_auth)).json()
        if not other_list["items"]:
            pytest.skip("welcome not yet wired")
        nid = other_list["items"][0]["id"]
        r = await client.delete(f"/api/notifications/{nid}", headers=auth)
        assert r.status_code == 404
```

Note: tests referencing "welcome" will still pass after Task 8 wires register→emit. Before Task 8, they `skip`. After Task 8, they assert real behavior.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && .venv/bin/python -m pytest tests/test_notifications_routes.py -v`
Expected: all fail at `404 Not Found` (routes not mounted) or similar.

- [ ] **Step 3: Create the routes**

Create `apps/api/app/routes/notifications.py`:
```python
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import (
    MarkAllReadResponse,
    NotificationListResponse,
    NotificationRead,
    UnreadCountResponse,
)
from app.services import notifications_service as svc

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = False,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> NotificationListResponse:
    return await svc.list_notifications(
        session, user.id, unread_only=unread_only, limit=limit, offset=offset
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UnreadCountResponse:
    return await svc.get_unread_count(session, user.id)


@router.patch("/{notification_id}/read", response_model=NotificationRead)
async def mark_read(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> NotificationRead:
    n = await svc.mark_read(session, user.id, notification_id)
    if n is None:
        raise HTTPException(status_code=404, detail="notification not found")
    return n


@router.post("/mark-all-read", response_model=MarkAllReadResponse)
async def mark_all_read(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MarkAllReadResponse:
    return await svc.mark_all_read(session, user.id)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    if not await svc.delete(session, user.id, notification_id):
        raise HTTPException(status_code=404, detail="notification not found")
```

- [ ] **Step 4: Mount router in main**

Modify `apps/api/app/main.py`. In the imports block change:
```python
from app.routes import auth, categories, health, items, locations, stats, tags, users
```
to:
```python
from app.routes import auth, categories, health, items, locations, notifications, stats, tags, users
```

Add `app.include_router(notifications.router)` immediately after `app.include_router(stats.router)` so the `create_app` block reads:
```python
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(categories.router)
    app.include_router(locations.router)
    app.include_router(tags.router)
    app.include_router(items.router)
    app.include_router(stats.router)
    app.include_router(notifications.router)
    return app
```

- [ ] **Step 5: Run test to verify routes pass (welcome-dependent cases skip for now)**

Run: `cd apps/api && .venv/bin/python -m pytest tests/test_notifications_routes.py -v`
Expected: `TestAuth`, `TestList::test_empty`, `TestList::test_limit_validation_*`, `TestUnreadCount::test_returns_int`, `TestMarkAllRead::test_returns_marked_count` all pass. Welcome-dependent tests skip. Overall: no failures.

- [ ] **Step 6: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
git add apps/api/app/routes/notifications.py apps/api/app/main.py apps/api/tests/test_notifications_routes.py
git commit -m "feat(api): add /api/notifications router"
```

---

## Task 8: Welcome notification on register

**Files:**
- Modify: `apps/api/app/routes/auth.py`
- Create: `apps/api/tests/test_notifications_welcome.py`

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/test_notifications_welcome.py`:
```python
from __future__ import annotations


async def test_register_creates_welcome_notification(client):
    await client.post("/api/auth/register", json={
        "email": "w@t.io", "username": "w_user", "password": "secret1234",
    })
    r = await client.post("/api/auth/login", json={
        "username": "w_user", "password": "secret1234",
    })
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    lst = (await client.get("/api/notifications", headers=headers)).json()
    assert lst["total"] == 1
    assert lst["unread_count"] == 1
    item = lst["items"][0]
    assert item["type"] == "system.welcome"
    assert item["title"] == "歡迎使用 IMS"
    assert item["link"] == "/dashboard"
    assert item["read_at"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && .venv/bin/python -m pytest tests/test_notifications_welcome.py -v`
Expected: `assert 0 == 1`

- [ ] **Step 3: Call emit from register route**

Modify `apps/api/app/routes/auth.py`. Add import near the other imports:
```python
from app.services import notifications_service
```

Replace the body of the `register` endpoint so it reads:
```python
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest, response: Response, session: AsyncSession = Depends(get_db)
) -> TokenResponse:
    service = AuthService(session)
    try:
        user = await service.register(
            email=payload.email, username=payload.username, password=payload.password
        )
    except EmailAlreadyExists:
        raise HTTPException(status_code=409, detail="email already registered")
    except UsernameAlreadyExists:
        raise HTTPException(status_code=409, detail="username already taken")
    await notifications_service.emit(
        session,
        user_id=user.id,
        type="system.welcome",
        title="歡迎使用 IMS",
        body="從儀表板開始管理你的物品吧。",
        link="/dashboard",
    )
    access = service.issue_access_token(user)
    refresh = service.issue_refresh_token(user)
    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access, user=UserPublic.model_validate(user))
```

- [ ] **Step 4: Run both welcome test and full routes test**

Run: `cd apps/api && .venv/bin/python -m pytest tests/test_notifications_welcome.py tests/test_notifications_routes.py -v`
Expected: All pass. Previously-skipped route cases (mark-read, delete, cross-owner 404) now execute and pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
git add apps/api/app/routes/auth.py apps/api/tests/test_notifications_welcome.py
git commit -m "feat(api): emit welcome notification on register"
```

---

## Task 9: Low-stock notification on item update

**Files:**
- Modify: `apps/api/app/services/items_service.py`
- Modify: `apps/api/app/schemas/item.py`
- Create: `apps/api/tests/test_notifications_low_stock.py`

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/test_notifications_low_stock.py`:
```python
from __future__ import annotations

import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={
        "email": "ls@t.io", "username": "ls_user", "password": "secret1234",
    })
    r = await client.post("/api/auth/login", json={
        "username": "ls_user", "password": "secret1234",
    })
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _count_low_stock(client, auth) -> int:
    lst = (await client.get("/api/notifications", headers=auth)).json()
    return sum(1 for i in lst["items"] if i["type"] == "low_stock")


async def test_low_stock_fires_on_threshold_crossing(client, auth):
    create = await client.post(
        "/api/items", headers=auth, json={"name": "便當盒", "quantity": 5, "min_quantity": 2},
    )
    item_id = create.json()["id"]
    # Update quantity 5 -> 1 (crosses 2)
    r = await client.patch(f"/api/items/{item_id}", headers=auth, json={"quantity": 1})
    assert r.status_code == 200
    assert await _count_low_stock(client, auth) == 1


async def test_low_stock_does_not_refire_while_below(client, auth):
    create = await client.post(
        "/api/items", headers=auth, json={"name": "牙刷", "quantity": 3, "min_quantity": 2},
    )
    item_id = create.json()["id"]
    await client.patch(f"/api/items/{item_id}", headers=auth, json={"quantity": 1})
    await client.patch(f"/api/items/{item_id}", headers=auth, json={"quantity": 0})
    assert await _count_low_stock(client, auth) == 1


async def test_low_stock_refires_after_refill(client, auth):
    create = await client.post(
        "/api/items", headers=auth, json={"name": "杯子", "quantity": 5, "min_quantity": 2},
    )
    item_id = create.json()["id"]
    await client.patch(f"/api/items/{item_id}", headers=auth, json={"quantity": 1})   # fire 1
    await client.patch(f"/api/items/{item_id}", headers=auth, json={"quantity": 5})   # above again
    await client.patch(f"/api/items/{item_id}", headers=auth, json={"quantity": 2})   # fire 2
    assert await _count_low_stock(client, auth) == 2


async def test_create_below_threshold_fires(client, auth):
    await client.post(
        "/api/items", headers=auth, json={"name": "襪子", "quantity": 1, "min_quantity": 2},
    )
    assert await _count_low_stock(client, auth) == 1


async def test_no_min_quantity_no_notification(client, auth):
    create = await client.post("/api/items", headers=auth, json={"name": "筷子", "quantity": 5})
    item_id = create.json()["id"]
    await client.patch(f"/api/items/{item_id}", headers=auth, json={"quantity": 0})
    assert await _count_low_stock(client, auth) == 0


async def test_changing_min_quantity_alone_does_not_fire(client, auth):
    create = await client.post(
        "/api/items", headers=auth, json={"name": "湯匙", "quantity": 3, "min_quantity": 1},
    )
    item_id = create.json()["id"]
    await client.patch(f"/api/items/{item_id}", headers=auth, json={"min_quantity": 5})
    assert await _count_low_stock(client, auth) == 0


async def test_low_stock_notification_has_link_to_item(client, auth):
    create = await client.post(
        "/api/items", headers=auth, json={"name": "牙膏", "quantity": 1, "min_quantity": 2},
    )
    item_id = create.json()["id"]
    lst = (await client.get("/api/notifications", headers=auth)).json()
    n = next(i for i in lst["items"] if i["type"] == "low_stock")
    assert n["link"] == f"/items/{item_id}"
    assert "牙膏" in n["title"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && .venv/bin/python -m pytest tests/test_notifications_low_stock.py -v`
Expected: `test_create_below_threshold_fires` fails with `422` (schema rejects `min_quantity`), other tests show 0 low_stock events.

- [ ] **Step 3: Extend item schemas**

Modify `apps/api/app/schemas/item.py`. Replace the three schema classes so they read:
```python
class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    quantity: int = Field(default=1, ge=0)
    min_quantity: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None
    tag_names: list[str] = Field(default_factory=list)


class ItemUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    category_id: Optional[int] = None
    location_id: Optional[int] = None
    quantity: Optional[int] = Field(default=None, ge=0)
    min_quantity: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None
    tag_names: Optional[list[str]] = None

    model_config = ConfigDict(extra="forbid")


class ItemRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    quantity: int
    min_quantity: Optional[int]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    category: Optional[CategoryRead]
    location: Optional[LocationRead]
    tags: list[TagRead]

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 4: Wire emit() into items_service**

Modify `apps/api/app/services/items_service.py`.

Add import at the top (after the existing `from app.schemas.item import …` line):
```python
from app.services import notifications_service
```

Replace the bodies of `create_item` and `update_item` so they read:
```python
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
        min_quantity=body.min_quantity,
        notes=body.notes,
        tags=tags,
    )
    created = await items_repository.create(session, item)
    if (
        created.min_quantity is not None
        and created.min_quantity > 0
        and created.quantity <= created.min_quantity
    ):
        await notifications_service.emit(
            session,
            user_id=owner_id,
            type="low_stock",
            title=f"「{created.name}」庫存不足",
            body=f"目前數量：{created.quantity}，提醒閾值：{created.min_quantity}",
            link=f"/items/{created.id}",
        )
    return ItemRead.model_validate(created)


async def update_item(
    session: AsyncSession, owner_id: UUID, item_id: UUID, body: ItemUpdate
) -> ItemRead:
    item = await items_repository.get_owned(session, owner_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    old_quantity = item.quantity
    fields = body.model_dump(exclude_unset=True)
    quantity_changing = "quantity" in fields
    if "category_id" in fields or "location_id" in fields:
        await _validate_refs(
            session,
            owner_id,
            fields.get("category_id", item.category_id),
            fields.get("location_id", item.location_id),
        )
    if "tag_names" in fields:
        new_names = fields.pop("tag_names")
        item.tags = await tags_repository.get_or_create_many(session, owner_id, new_names or [])
    for k, v in fields.items():
        setattr(item, k, v)
    saved = await items_repository.save(session, item)
    if (
        quantity_changing
        and saved.min_quantity is not None
        and saved.min_quantity > 0
        and old_quantity > saved.min_quantity
        and saved.quantity <= saved.min_quantity
    ):
        await notifications_service.emit(
            session,
            user_id=owner_id,
            type="low_stock",
            title=f"「{saved.name}」庫存不足",
            body=f"目前數量：{saved.quantity}，提醒閾值：{saved.min_quantity}",
            link=f"/items/{saved.id}",
        )
    return ItemRead.model_validate(saved)
```

- [ ] **Step 5: Run low-stock tests**

Run: `cd apps/api && .venv/bin/python -m pytest tests/test_notifications_low_stock.py -v`
Expected: 7 passed.

- [ ] **Step 6: Run full test suite to confirm no regressions**

Run: `cd apps/api && .venv/bin/python -m pytest -q`
Expected: All tests pass (prior 126 + new notification tests).

- [ ] **Step 7: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
git add apps/api/app/services/items_service.py apps/api/app/schemas/item.py apps/api/tests/test_notifications_low_stock.py
git commit -m "feat(api): emit low_stock notification on threshold crossing"
```

---

## Task 10: Regenerate api-types

**Files:**
- Modify: `packages/api-types/openapi.json`
- Modify: `packages/api-types/src/index.ts`

- [ ] **Step 1: Run the codegen**

Run: `cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center && pnpm --filter @ims/api gen:types && pnpm --filter @ims/api-types gen:types`
Expected: Both commands succeed, files updated.

- [ ] **Step 2: Verify notifications paths appear**

Run: `grep -c '/api/notifications' packages/api-types/src/index.ts`
Expected: ≥ 5 (five endpoints referenced).

- [ ] **Step 3: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
git add packages/api-types/openapi.json packages/api-types/src/index.ts
git commit -m "chore(api-types): regenerate for notification endpoints"
```

---

## Task 11: Web API client for notifications

**Files:**
- Create: `apps/web/lib/api/notifications.ts`

- [ ] **Step 1: Create the client**

Create `apps/web/lib/api/notifications.ts`:
```typescript
import type { paths } from "@ims/api-types"

import { apiFetch } from "./client"

export type NotificationRead =
  paths["/api/notifications"]["get"]["responses"]["200"]["content"]["application/json"]["items"][number]

export type NotificationListResponse =
  paths["/api/notifications"]["get"]["responses"]["200"]["content"]["application/json"]

export type UnreadCountResponse =
  paths["/api/notifications/unread-count"]["get"]["responses"]["200"]["content"]["application/json"]

export async function listNotifications(
  params: { unreadOnly?: boolean; limit?: number; offset?: number },
  accessToken: string | null,
): Promise<NotificationListResponse> {
  const q = new URLSearchParams()
  if (params.unreadOnly) q.set("unread_only", "true")
  if (params.limit !== undefined) q.set("limit", String(params.limit))
  if (params.offset !== undefined) q.set("offset", String(params.offset))
  const res = await apiFetch(`/notifications${q.size ? `?${q}` : ""}`, { accessToken })
  return (await res.json()) as NotificationListResponse
}

export async function getUnreadCount(accessToken: string | null): Promise<UnreadCountResponse> {
  const res = await apiFetch("/notifications/unread-count", { accessToken })
  return (await res.json()) as UnreadCountResponse
}

export async function markNotificationRead(
  id: string,
  accessToken: string | null,
): Promise<NotificationRead> {
  const res = await apiFetch(`/notifications/${id}/read`, { method: "PATCH", accessToken })
  return (await res.json()) as NotificationRead
}

export async function markAllNotificationsRead(
  accessToken: string | null,
): Promise<{ marked: number }> {
  const res = await apiFetch("/notifications/mark-all-read", { method: "POST", accessToken })
  return (await res.json()) as { marked: number }
}

export async function deleteNotification(
  id: string,
  accessToken: string | null,
): Promise<void> {
  await apiFetch(`/notifications/${id}`, { method: "DELETE", accessToken })
}
```

- [ ] **Step 2: Typecheck**

Run: `cd apps/web && pnpm typecheck`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
git add apps/web/lib/api/notifications.ts
git commit -m "feat(web): add typed notifications API client"
```

---

## Task 12: React Query hooks for notifications

**Files:**
- Create: `apps/web/lib/hooks/use-notifications.ts`

- [ ] **Step 1: Create the hooks**

Create `apps/web/lib/hooks/use-notifications.ts`:
```typescript
"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import * as api from "@/lib/api/notifications"
import { useAccessToken } from "@/lib/auth/use-auth"

const STALE = 30_000

export function useNotifications(params: { unreadOnly?: boolean; limit?: number; offset?: number } = {}) {
  const token = useAccessToken()
  const { unreadOnly = false, limit = 20, offset = 0 } = params
  return useQuery({
    queryKey: ["notifications", "list", { unreadOnly, limit, offset }],
    queryFn: () => api.listNotifications({ unreadOnly, limit, offset }, token),
    enabled: token !== null,
    staleTime: STALE,
  })
}

export function useUnreadCount() {
  const token = useAccessToken()
  return useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: () => api.getUnreadCount(token),
    enabled: token !== null,
    staleTime: STALE,
    refetchInterval: 60_000,
    refetchOnWindowFocus: true,
  })
}

export function useMarkNotificationRead() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.markNotificationRead(id, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] })
    },
  })
}

export function useMarkAllNotificationsRead() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.markAllNotificationsRead(token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] })
    },
  })
}

export function useDeleteNotification() {
  const token = useAccessToken()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.deleteNotification(id, token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] })
    },
  })
}
```

- [ ] **Step 2: Typecheck**

Run: `cd apps/web && pnpm typecheck`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
git add apps/web/lib/hooks/use-notifications.ts
git commit -m "feat(web): add notifications React Query hooks"
```

---

## Task 13: i18n messages for notifications

**Files:**
- Modify: `apps/web/messages/zh-TW.json`
- Modify: `apps/web/messages/en.json`

- [ ] **Step 1: Add zh-TW entries**

Modify `apps/web/messages/zh-TW.json`. In the `nav` block add `"notifications": "通知"` (keep alphabetical — it goes between `locations`/`items` alphabetically but insert after `lists` for readability, i.e. within the existing `nav` object). The critical requirement is the key `nav.notifications` resolves.

Then insert a sibling `notifications` object at the top level (between `stats` and whatever follows, or at the end of the object just before the closing `}`):
```json
"notifications": {
  "title": "通知",
  "filters": {
    "all": "全部",
    "unread": "未讀"
  },
  "actions": {
    "markRead": "標為已讀",
    "markAllRead": "全部標為已讀",
    "delete": "刪除"
  },
  "empty": {
    "title": "尚無通知",
    "cta": "前往儀表板"
  },
  "loadMore": "載入更多",
  "bell": {
    "label": "通知"
  }
}
```

- [ ] **Step 2: Add en entries**

Modify `apps/web/messages/en.json`. In the `nav` block add `"notifications": "Notifications"`.

Add a sibling top-level `notifications` object:
```json
"notifications": {
  "title": "Notifications",
  "filters": {
    "all": "All",
    "unread": "Unread"
  },
  "actions": {
    "markRead": "Mark read",
    "markAllRead": "Mark all read",
    "delete": "Delete"
  },
  "empty": {
    "title": "No notifications yet",
    "cta": "Go to dashboard"
  },
  "loadMore": "Load more",
  "bell": {
    "label": "Notifications"
  }
}
```

- [ ] **Step 3: Typecheck (next-intl typed keys)**

Run: `cd apps/web && pnpm typecheck`
Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
git add apps/web/messages/zh-TW.json apps/web/messages/en.json
git commit -m "feat(web): add i18n strings for notifications"
```

---

## Task 14: NotificationBell component

**Files:**
- Create: `apps/web/components/shell/notification-bell.tsx`
- Create: `apps/web/components/shell/notification-bell.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `apps/web/components/shell/notification-bell.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"
import { NotificationBell } from "./notification-bell"

vi.mock("@/lib/hooks/use-notifications", () => ({
  useUnreadCount: () => mockState.value,
}))

const mockState: { value: { data?: { count: number }; isLoading: boolean } } = {
  value: { data: { count: 0 }, isLoading: false },
}

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

describe("NotificationBell", () => {
  it("hides badge when count is 0", () => {
    mockState.value = { data: { count: 0 }, isLoading: false }
    render(<NotificationBell />, { wrapper: Provider })
    expect(screen.queryByTestId("notification-badge")).not.toBeInTheDocument()
  })

  it("shows count when 1..99", () => {
    mockState.value = { data: { count: 7 }, isLoading: false }
    render(<NotificationBell />, { wrapper: Provider })
    expect(screen.getByTestId("notification-badge")).toHaveTextContent("7")
  })

  it("shows 99+ when count exceeds 99", () => {
    mockState.value = { data: { count: 150 }, isLoading: false }
    render(<NotificationBell />, { wrapper: Provider })
    expect(screen.getByTestId("notification-badge")).toHaveTextContent("99+")
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/web && pnpm test -- notification-bell`
Expected: `Failed to resolve import "./notification-bell"`.

- [ ] **Step 3: Create the component**

Create `apps/web/components/shell/notification-bell.tsx`:
```tsx
"use client"

import Link from "next/link"
import { Bell } from "lucide-react"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { useUnreadCount } from "@/lib/hooks/use-notifications"

export function NotificationBell() {
  const t = useTranslations()
  const { data } = useUnreadCount()
  const count = data?.count ?? 0
  const label = count > 99 ? "99+" : String(count)

  return (
    <Button
      asChild
      variant="ghost"
      size="icon"
      aria-label={t("notifications.bell.label")}
      className="relative"
    >
      <Link href="/notifications">
        <Bell className="h-5 w-5" />
        {count > 0 ? (
          <span
            data-testid="notification-badge"
            aria-live="polite"
            className="absolute -right-1 -top-1 min-w-[1.25rem] rounded-full bg-destructive px-1 text-[0.625rem] font-semibold leading-4 text-destructive-foreground"
          >
            {label}
          </span>
        ) : null}
      </Link>
    </Button>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/web && pnpm test -- notification-bell`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
git add apps/web/components/shell/notification-bell.tsx apps/web/components/shell/notification-bell.test.tsx
git commit -m "feat(web): add NotificationBell header component"
```

---

## Task 15: Mount bell in AppHeader + add nav item

**Files:**
- Modify: `apps/web/components/shell/app-header.tsx`
- Modify: `apps/web/components/shell/nav-items.ts`

- [ ] **Step 1: Extend NavItem and insert notifications entry**

Replace `apps/web/components/shell/nav-items.ts` with:
```typescript
import type { Route } from "next"

export interface NavItem {
  key: "dashboard" | "items" | "statistics" | "notifications" | "lists" | "settings"
  href: Route
  /** i18n key for label */
  labelKey: string
}

export const NAV_ITEMS: readonly NavItem[] = [
  { key: "dashboard", href: "/dashboard", labelKey: "nav.dashboard" },
  { key: "items", href: "/items", labelKey: "nav.items" },
  { key: "statistics", href: "/statistics", labelKey: "nav.statistics" },
  { key: "notifications", href: "/notifications", labelKey: "nav.notifications" },
  { key: "lists", href: "/lists", labelKey: "nav.lists" },
  { key: "settings", href: "/settings", labelKey: "nav.settings" },
]
```

- [ ] **Step 2: Mount bell in header**

Modify `apps/web/components/shell/app-header.tsx`. Add import:
```tsx
import { NotificationBell } from "./notification-bell"
```

Replace the `<div className="ml-auto …">` block so it reads:
```tsx
      <div className="ml-auto flex items-center gap-2">
        <NotificationBell />
        <UserMenu />
      </div>
```

- [ ] **Step 3: Typecheck**

Run: `cd apps/web && pnpm typecheck`
Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
git add apps/web/components/shell/app-header.tsx apps/web/components/shell/nav-items.ts
git commit -m "feat(web): mount NotificationBell + add notifications nav item"
```

---

## Task 16: NotificationItem row component

**Files:**
- Create: `apps/web/components/notifications/notification-item.tsx`
- Create: `apps/web/components/notifications/notification-item.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `apps/web/components/notifications/notification-item.test.tsx`:
```tsx
import { fireEvent, render, screen } from "@testing-library/react"
import { NextIntlClientProvider } from "next-intl"
import { describe, expect, it, vi } from "vitest"

import enMessages from "@/messages/en.json"
import { NotificationItem } from "./notification-item"
import type { NotificationRead } from "@/lib/api/notifications"

const Provider = ({ children }: { children: React.ReactNode }) => (
  <NextIntlClientProvider locale="en" messages={enMessages}>
    {children}
  </NextIntlClientProvider>
)

const baseRow: NotificationRead = {
  id: "id-1",
  user_id: "u1",
  type: "system.welcome",
  title: "Welcome",
  body: "Start from the dashboard.",
  link: "/dashboard",
  read_at: null,
  created_at: new Date().toISOString(),
}

describe("NotificationItem", () => {
  it("renders title and body", () => {
    render(<NotificationItem row={baseRow} onOpen={vi.fn()} onDelete={vi.fn()} />, { wrapper: Provider })
    expect(screen.getByText("Welcome")).toBeInTheDocument()
    expect(screen.getByText("Start from the dashboard.")).toBeInTheDocument()
  })

  it("shows unread dot when read_at is null", () => {
    render(<NotificationItem row={baseRow} onOpen={vi.fn()} onDelete={vi.fn()} />, { wrapper: Provider })
    expect(screen.getByTestId("unread-dot")).toBeInTheDocument()
  })

  it("hides unread dot when row is read", () => {
    render(
      <NotificationItem
        row={{ ...baseRow, read_at: new Date().toISOString() }}
        onOpen={vi.fn()}
        onDelete={vi.fn()}
      />,
      { wrapper: Provider },
    )
    expect(screen.queryByTestId("unread-dot")).not.toBeInTheDocument()
  })

  it("fires onOpen when row is clicked", () => {
    const onOpen = vi.fn()
    render(<NotificationItem row={baseRow} onOpen={onOpen} onDelete={vi.fn()} />, { wrapper: Provider })
    fireEvent.click(screen.getByRole("button", { name: /open notification/i }))
    expect(onOpen).toHaveBeenCalledWith(baseRow)
  })

  it("fires onDelete when delete button clicked", () => {
    const onDelete = vi.fn()
    render(<NotificationItem row={baseRow} onOpen={vi.fn()} onDelete={onDelete} />, { wrapper: Provider })
    fireEvent.click(screen.getByRole("button", { name: /delete/i }))
    expect(onDelete).toHaveBeenCalledWith(baseRow.id)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/web && pnpm test -- notification-item`
Expected: `Failed to resolve import "./notification-item"`.

- [ ] **Step 3: Create the component**

Create `apps/web/components/notifications/notification-item.tsx`:
```tsx
"use client"

import { X } from "lucide-react"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { NotificationRead } from "@/lib/api/notifications"

interface Props {
  row: NotificationRead
  onOpen: (row: NotificationRead) => void
  onDelete: (id: string) => void
}

function formatRelative(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const sec = Math.max(0, Math.round(diffMs / 1000))
  if (sec < 60) return `${sec}s`
  const min = Math.round(sec / 60)
  if (min < 60) return `${min}m`
  const hr = Math.round(min / 60)
  if (hr < 24) return `${hr}h`
  const day = Math.round(hr / 24)
  return `${day}d`
}

export function NotificationItem({ row, onOpen, onDelete }: Props) {
  const t = useTranslations()
  const unread = row.read_at === null
  return (
    <li className={cn("group flex items-start gap-3 border-b p-4", !unread && "opacity-70")}>
      <button
        type="button"
        aria-label="Open notification"
        onClick={() => onOpen(row)}
        className="flex flex-1 flex-col items-start gap-1 text-left"
      >
        <div className="flex items-center gap-2">
          {unread ? (
            <span
              data-testid="unread-dot"
              aria-hidden
              className="h-2 w-2 rounded-full bg-primary"
            />
          ) : null}
          <span className="font-medium">{row.title}</span>
          <span className="text-xs text-muted-foreground">{formatRelative(row.created_at)}</span>
        </div>
        {row.body ? (
          <p className="text-sm text-muted-foreground">{row.body}</p>
        ) : null}
      </button>
      <Button
        variant="ghost"
        size="icon"
        aria-label={t("notifications.actions.delete")}
        onClick={() => onDelete(row.id)}
      >
        <X className="h-4 w-4" />
      </Button>
    </li>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/web && pnpm test -- notification-item`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
git add apps/web/components/notifications/notification-item.tsx apps/web/components/notifications/notification-item.test.tsx
git commit -m "feat(web): add NotificationItem row component"
```

---

## Task 17: Notifications empty state component

**Files:**
- Create: `apps/web/components/notifications/empty.tsx`

- [ ] **Step 1: Write the component**

Create `apps/web/components/notifications/empty.tsx`:
```tsx
"use client"

import Link from "next/link"
import { useTranslations } from "next-intl"

import { Button } from "@/components/ui/button"

export function NotificationsEmpty() {
  const t = useTranslations()
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded border border-dashed p-12 text-center">
      <p className="text-sm font-medium">{t("notifications.empty.title")}</p>
      <Button asChild variant="outline" size="sm">
        <Link href="/dashboard">{t("notifications.empty.cta")}</Link>
      </Button>
    </div>
  )
}
```

- [ ] **Step 2: Typecheck**

Run: `cd apps/web && pnpm typecheck`
Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
git add apps/web/components/notifications/empty.tsx
git commit -m "feat(web): add NotificationsEmpty state component"
```

---

## Task 18: Notifications page

**Files:**
- Create: `apps/web/app/(app)/notifications/page.tsx`

- [ ] **Step 1: Write the page**

Create `apps/web/app/(app)/notifications/page.tsx`:
```tsx
"use client"

import { useRouter } from "next/navigation"
import { useState } from "react"
import { useTranslations } from "next-intl"

import { NotificationsEmpty } from "@/components/notifications/empty"
import { NotificationItem } from "@/components/notifications/notification-item"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  useDeleteNotification,
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
} from "@/lib/hooks/use-notifications"
import type { NotificationRead } from "@/lib/api/notifications"

export default function NotificationsPage() {
  const t = useTranslations()
  const router = useRouter()
  const [tab, setTab] = useState<"all" | "unread">("all")
  const query = useNotifications({ unreadOnly: tab === "unread", limit: 50, offset: 0 })
  const markRead = useMarkNotificationRead()
  const markAllRead = useMarkAllNotificationsRead()
  const del = useDeleteNotification()

  const handleOpen = (row: NotificationRead) => {
    if (row.read_at === null) markRead.mutate(row.id)
    if (row.link) router.push(row.link as never)
  }

  return (
    <section className="space-y-6 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink href="/dashboard">{t("nav.dashboard")}</BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>{t("notifications.title")}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t("notifications.title")}</h1>
        <Button
          variant="outline"
          size="sm"
          onClick={() => markAllRead.mutate()}
          disabled={markAllRead.isPending}
        >
          {t("notifications.actions.markAllRead")}
        </Button>
      </div>

      <Tabs value={tab} onValueChange={(v) => setTab(v as "all" | "unread")}>
        <TabsList>
          <TabsTrigger value="all">{t("notifications.filters.all")}</TabsTrigger>
          <TabsTrigger value="unread">{t("notifications.filters.unread")}</TabsTrigger>
        </TabsList>
      </Tabs>

      <div className="rounded-lg border">
        {query.isLoading ? (
          <div className="space-y-2 p-4">
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-14 w-full" />
          </div>
        ) : query.data && query.data.items.length > 0 ? (
          <ul>
            {query.data.items.map((row) => (
              <NotificationItem
                key={row.id}
                row={row}
                onOpen={handleOpen}
                onDelete={(id) => del.mutate(id)}
              />
            ))}
          </ul>
        ) : (
          <NotificationsEmpty />
        )}
      </div>
    </section>
  )
}
```

- [ ] **Step 2: Verify Tabs + Skeleton components exist**

Run: `ls apps/web/components/ui/tabs.tsx apps/web/components/ui/skeleton.tsx`
Expected: Both files exist. If `tabs.tsx` is missing, install shadcn tabs:
```bash
cd apps/web && pnpm dlx shadcn@latest add tabs --yes
```
Otherwise proceed.

- [ ] **Step 3: Typecheck**

Run: `cd apps/web && pnpm typecheck`
Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
git add "apps/web/app/(app)/notifications/page.tsx"
# If you ran shadcn add, also stage:
git add apps/web/components/ui/tabs.tsx apps/web/package.json pnpm-lock.yaml 2>/dev/null || true
git commit -m "feat(web): add notifications inbox page"
```

---

## Task 19: E2E tests

**Files:**
- Create: `apps/web/tests/notifications.spec.ts`

- [ ] **Step 1: Write the spec**

Create `apps/web/tests/notifications.spec.ts`:
```typescript
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

test("new user sees welcome notification and unread badge", async ({ page, request }) => {
  const u = `notif_${unique()}`
  await register(request, u)
  await loginUi(page, u)
  await expect(page.getByTestId("notification-badge")).toHaveText("1")

  await page.getByRole("link", { name: "通知" }).first().click()
  await page.waitForURL("**/notifications")
  await expect(page.getByText("歡迎使用 IMS")).toBeVisible()
})

test("clicking a notification marks it read and navigates", async ({ page, request }) => {
  const u = `notif2_${unique()}`
  await register(request, u)
  await loginUi(page, u)
  await page.goto("/notifications")
  await page.getByRole("button", { name: /open notification/i }).first().click()
  await page.waitForURL("**/dashboard")
  await page.goto("/notifications")
  await expect(page.getByTestId("notification-badge")).toHaveCount(0)
})

test("mark all read empties unread tab", async ({ page, request }) => {
  const u = `notif3_${unique()}`
  await register(request, u)
  await loginUi(page, u)
  await page.goto("/notifications")
  await page.getByRole("button", { name: "全部標為已讀" }).click()
  await page.getByRole("tab", { name: "未讀" }).click()
  await expect(page.getByText("尚無通知")).toBeVisible()
})

test("low-stock notification appears after API update", async ({ page, request }) => {
  const u = `notif4_${unique()}`
  await register(request, u)
  const login = await request.post("/api/auth/login", {
    data: { username: u, password: "secret1234" },
  })
  const token = (await login.json()).access_token
  const item = await request.post("/api/items", {
    headers: { Authorization: `Bearer ${token}` },
    data: { name: "便當盒", quantity: 5, min_quantity: 2 },
  })
  const itemId = (await item.json()).id
  await request.patch(`/api/items/${itemId}`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { quantity: 1 },
  })

  await loginUi(page, u)
  await page.goto("/notifications")
  await expect(page.getByText(/庫存不足/)).toBeVisible()
})
```

- [ ] **Step 2: Commit (tests not executed now — run with E2E suite separately)**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
git add apps/web/tests/notifications.spec.ts
git commit -m "test(e2e): add notifications welcome + mark-read + low-stock flows"
```

---

## Task 20: Mark roadmap done

**Files:**
- Modify: `docs/v2-roadmap.md`

- [ ] **Step 1: Flip #5 row**

Change the line
```markdown
| 5 | 通知中心 | ⏳ 未開始 |
```
to
```markdown
| 5 | 通知中心 | ✅ 完成 |
```

- [ ] **Step 2: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
git add docs/v2-roadmap.md
git commit -m "docs: mark #5 notification center subproject complete"
```

---

## Final Verification

After Task 20, run full gates:

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/notification-center
cd apps/api && .venv/bin/python -m pytest -q && cd ../..
cd apps/web && pnpm typecheck && pnpm test && pnpm build && cd ../..
```

Expected:
- API pytest: all passing (prior 126 + new notification tests ≈ 30 additions)
- Web typecheck: 0 errors
- Web vitest: all passing (prior 40 + 8 new notification tests)
- Web build: successful; route list includes `/notifications`

E2E (manual, requires API + web dev servers running):
```bash
pnpm --filter @ims/web e2e
```
