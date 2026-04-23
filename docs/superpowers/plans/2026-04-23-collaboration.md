# Collaboration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship three collaboration features — shared groups, item loans, and ownership transfers — atop a new visibility service that lets group members view each other's items read-only.

**Architecture:** New tables `groups`, `group_members`, `item_loans`, `item_transfers`. A `visibility_service` computes the set of owner ids visible to a user (self + fellow group members) and is used by items read paths; mutations stay strictly owner-checked. Transfer acceptance flips `items.owner_id`. Notifications via existing `#5` emit service.

**Tech Stack:** Same v2 stack. No new packages.

**Worktree:** `.claude/worktrees/collaboration` · **Branch:** `claude/collaboration` · **Baseline:** API 223/223, web typecheck clean, vitest 57/57. Already includes the @dnd-kit dep fix for lists.

**Spec:** `docs/superpowers/specs/2026-04-23-collaboration-design.md`

---

## Conventions

- API commands from `.claude/worktrees/collaboration/apps/api` with `.venv/bin/python -m …`
- Web commands from `.claude/worktrees/collaboration/apps/web`
- Commit per task; prefix commands with `cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration && …`

---

## Task 1: Group + GroupMember models

**Files:** `apps/api/app/models/group.py`, `apps/api/app/models/__init__.py`, `apps/api/tests/test_group_model_smoke.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_group_model_smoke.py
from __future__ import annotations
from app.auth.password import hash_password
from app.models.group import Group, GroupMember
from app.models.user import User


async def test_group_with_member_roundtrip(db_session):
    owner = User(email="o@t.io", username="o_user", password_hash=hash_password("secret1234"))
    m = User(email="m@t.io", username="m_user", password_hash=hash_password("secret1234"))
    db_session.add_all([owner, m])
    await db_session.flush()
    g = Group(owner_id=owner.id, name="家人")
    g.members = [GroupMember(user_id=owner.id), GroupMember(user_id=m.id)]
    db_session.add(g)
    await db_session.commit()
    assert g.id is not None
    assert len(g.members) == 2
```

- [ ] **Step 2: Run — expect `ModuleNotFoundError`**

`cd apps/api && .venv/bin/python -m pytest tests/test_group_model_smoke.py -v`

- [ ] **Step 3: Implement**

Create `apps/api/app/models/group.py`:
```python
from __future__ import annotations
import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, _utcnow
from app.models.user import GUID


class Group(Base):
    __tablename__ = "groups"
    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_groups_owner_name"),)

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    members: Mapped[list["GroupMember"]] = relationship(
        "GroupMember", back_populates="group", cascade="all, delete-orphan"
    )


class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_members_group_user"),)

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    group: Mapped[Group] = relationship("Group", back_populates="members")
```

Update `apps/api/app/models/__init__.py` to add `Group` + `GroupMember` imports and `__all__` entries.

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/api/app/models/group.py apps/api/app/models/__init__.py apps/api/tests/test_group_model_smoke.py
git commit -m "feat(api): add Group + GroupMember ORM models"
```

---

## Task 2: ItemLoan model

**Files:** `apps/api/app/models/loan.py`, `apps/api/app/models/__init__.py`, `apps/api/tests/test_loan_model_smoke.py`

- [ ] **Step 1: Test**

```python
# tests/test_loan_model_smoke.py
from __future__ import annotations
from datetime import date
from app.auth.password import hash_password
from app.models.item import Item
from app.models.loan import ItemLoan
from app.models.user import User


async def test_loan_with_label(db_session):
    u = User(email="l@t.io", username="l_user", password_hash=hash_password("secret1234"))
    db_session.add(u); await db_session.flush()
    item = Item(owner_id=u.id, name="傘")
    db_session.add(item); await db_session.flush()
    loan = ItemLoan(item_id=item.id, borrower_label="陌生人", expected_return=date(2026, 6, 1))
    db_session.add(loan); await db_session.commit()
    assert loan.id is not None
    assert loan.returned_at is None
```

- [ ] **Step 2: Run — expect `ModuleNotFoundError`**

- [ ] **Step 3: Implement**

Create `apps/api/app/models/loan.py`:
```python
from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, _utcnow
from app.models.user import GUID


class ItemLoan(Base):
    __tablename__ = "item_loans"
    __table_args__ = (
        CheckConstraint(
            "borrower_user_id IS NOT NULL OR borrower_label IS NOT NULL",
            name="ck_loans_borrower_presence",
        ),
        Index(
            "uq_item_loans_one_active",
            "item_id",
            unique=True,
            sqlite_where=text("returned_at IS NULL"),
            postgresql_where=text("returned_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    item_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    borrower_user_id: Mapped[Optional[UUID]] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    borrower_label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    lent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    expected_return: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    returned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
```

Update `apps/api/app/models/__init__.py` to export `ItemLoan`.

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/api/app/models/loan.py apps/api/app/models/__init__.py apps/api/tests/test_loan_model_smoke.py
git commit -m "feat(api): add ItemLoan ORM model"
```

---

## Task 3: ItemTransfer model

**Files:** `apps/api/app/models/transfer.py`, `apps/api/app/models/__init__.py`, `apps/api/tests/test_transfer_model_smoke.py`

- [ ] **Step 1: Test**

```python
# tests/test_transfer_model_smoke.py
from __future__ import annotations
from app.auth.password import hash_password
from app.models.item import Item
from app.models.transfer import ItemTransfer
from app.models.user import User


async def test_transfer_pending(db_session):
    a = User(email="a@t.io", username="a_user", password_hash=hash_password("secret1234"))
    b = User(email="b@t.io", username="b_user", password_hash=hash_password("secret1234"))
    db_session.add_all([a, b]); await db_session.flush()
    item = Item(owner_id=a.id, name="筆")
    db_session.add(item); await db_session.flush()
    t = ItemTransfer(item_id=item.id, from_user_id=a.id, to_user_id=b.id, status="pending")
    db_session.add(t); await db_session.commit()
    assert t.id is not None
    assert t.status == "pending"
```

- [ ] **Step 2: Run — expect `ModuleNotFoundError`**

- [ ] **Step 3: Implement**

Create `apps/api/app/models/transfer.py`:
```python
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, _utcnow
from app.models.user import GUID


class ItemTransfer(Base):
    __tablename__ = "item_transfers"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','accepted','rejected','cancelled')",
            name="ck_transfers_status_valid",
        ),
        Index(
            "uq_item_transfers_one_pending",
            "item_id",
            unique=True,
            sqlite_where=text("status = 'pending'"),
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    item_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    from_user_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    to_user_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default=text("'pending'"))
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
```

Update `apps/api/app/models/__init__.py` to export `ItemTransfer`.

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/api/app/models/transfer.py apps/api/app/models/__init__.py apps/api/tests/test_transfer_model_smoke.py
git commit -m "feat(api): add ItemTransfer ORM model"
```

---

## Task 4: Item.owner relationship

**Files:** `apps/api/app/models/item.py`, `apps/api/tests/test_item_owner_smoke.py`

- [ ] **Step 1: Test**

```python
# tests/test_item_owner_smoke.py
from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.auth.password import hash_password
from app.models.item import Item
from app.models.user import User


async def test_item_owner_relationship(db_session):
    u = User(email="own@t.io", username="own_user", password_hash=hash_password("secret1234"))
    db_session.add(u); await db_session.flush()
    db_session.add(Item(owner_id=u.id, name="x"))
    await db_session.commit()
    stmt = select(Item).options(selectinload(Item.owner)).where(Item.owner_id == u.id)
    row = (await db_session.execute(stmt)).scalar_one()
    assert row.owner.username == "own_user"
```

- [ ] **Step 2: Run — expect `AttributeError` on `Item.owner`**

- [ ] **Step 3: Implement — add `owner` relationship to Item**

Modify `apps/api/app/models/item.py`: add `from typing import TYPE_CHECKING` and inside the class after `tags:` add:
```python
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id])  # noqa: F821
```

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/api/app/models/item.py apps/api/tests/test_item_owner_smoke.py
git commit -m "feat(api): add Item.owner relationship"
```

---

## Task 5: Alembic migration 0006

**Files:** `apps/api/alembic/versions/0006_collaboration.py`

- [ ] **Step 1: Verify head**

`cd apps/api && .venv/bin/python -m alembic heads` → `0005 (head)`

- [ ] **Step 2: Write migration**

Create `apps/api/alembic/versions/0006_collaboration.py`:
```python
"""groups + group_members + item_loans + item_transfers

Revision ID: 0006
Revises: 0005
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("owner_id", "name", name="uq_groups_owner_name"),
    )
    op.create_index("ix_groups_owner_id", "groups", ["owner_id"])

    op.create_table(
        "group_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_members_group_user"),
    )
    op.create_index("ix_group_members_group_id", "group_members", ["group_id"])
    op.create_index("ix_group_members_user_id", "group_members", ["user_id"])

    op.create_table(
        "item_loans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("borrower_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("borrower_label", sa.String(200), nullable=True),
        sa.Column("lent_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expected_return", sa.Date(), nullable=True),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "borrower_user_id IS NOT NULL OR borrower_label IS NOT NULL",
            name="ck_loans_borrower_presence",
        ),
    )
    op.create_index("ix_item_loans_item_id", "item_loans", ["item_id"])
    op.create_index("ix_item_loans_borrower_user_id", "item_loans", ["borrower_user_id"])
    op.create_index("ix_item_loans_returned_at", "item_loans", ["returned_at"])
    op.create_index(
        "uq_item_loans_one_active", "item_loans", ["item_id"],
        unique=True, postgresql_where=sa.text("returned_at IS NULL"),
        sqlite_where=sa.text("returned_at IS NULL"),
    )

    op.create_table(
        "item_transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','accepted','rejected','cancelled')",
            name="ck_transfers_status_valid",
        ),
    )
    op.create_index("ix_item_transfers_item_id", "item_transfers", ["item_id"])
    op.create_index("ix_item_transfers_from_user_id", "item_transfers", ["from_user_id"])
    op.create_index("ix_item_transfers_to_user_id", "item_transfers", ["to_user_id"])
    op.create_index(
        "uq_item_transfers_one_pending", "item_transfers", ["item_id"],
        unique=True, postgresql_where=sa.text("status = 'pending'"),
        sqlite_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index("uq_item_transfers_one_pending", table_name="item_transfers")
    op.drop_index("ix_item_transfers_to_user_id", table_name="item_transfers")
    op.drop_index("ix_item_transfers_from_user_id", table_name="item_transfers")
    op.drop_index("ix_item_transfers_item_id", table_name="item_transfers")
    op.drop_table("item_transfers")
    op.drop_index("uq_item_loans_one_active", table_name="item_loans")
    op.drop_index("ix_item_loans_returned_at", table_name="item_loans")
    op.drop_index("ix_item_loans_borrower_user_id", table_name="item_loans")
    op.drop_index("ix_item_loans_item_id", table_name="item_loans")
    op.drop_table("item_loans")
    op.drop_index("ix_group_members_user_id", table_name="group_members")
    op.drop_index("ix_group_members_group_id", table_name="group_members")
    op.drop_table("group_members")
    op.drop_index("ix_groups_owner_id", table_name="groups")
    op.drop_table("groups")
```

- [ ] **Step 3: Verify**

`cd apps/api && .venv/bin/python -m alembic heads` → `0006 (head)`
`.venv/bin/python -m alembic upgrade 0006 --sql 2>&1 | grep "CREATE TABLE"` → shows all 4 tables.

- [ ] **Step 4: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/api/alembic/versions/0006_collaboration.py
git commit -m "feat(api): migration 0006 — collaboration tables"
```

---

## Task 6: Pydantic schemas (groups + loans + transfers + ItemRead)

**Files:** `apps/api/app/schemas/group.py`, `apps/api/app/schemas/loan.py`, `apps/api/app/schemas/transfer.py`, `apps/api/app/schemas/item.py` (modify), `apps/api/tests/test_collab_schemas.py`

- [ ] **Step 1: Test**

```python
# tests/test_collab_schemas.py
from __future__ import annotations
import uuid
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from app.schemas.group import GroupCreate, GroupUpdate, GroupAddMember
from app.schemas.loan import LoanCreate
from app.schemas.transfer import TransferCreate


def test_group_create_rejects_empty_name():
    with pytest.raises(ValidationError):
        GroupCreate(name="")


def test_group_update_forbids_extra():
    with pytest.raises(ValidationError):
        GroupUpdate.model_validate({"weird": 1})


def test_add_member_requires_username():
    with pytest.raises(ValidationError):
        GroupAddMember(username="")


def test_loan_create_allows_either_borrower():
    LoanCreate(borrower_label="張三")
    LoanCreate(borrower_username="a_user")


def test_loan_create_rejects_both_null():
    with pytest.raises(ValidationError):
        LoanCreate()


def test_loan_create_rejects_both_set():
    with pytest.raises(ValidationError):
        LoanCreate(borrower_label="x", borrower_username="a_user")


def test_transfer_create_requires_item_and_user():
    with pytest.raises(ValidationError):
        TransferCreate(item_id=uuid.uuid4())
```

- [ ] **Step 2: Run — fail with `ModuleNotFoundError`**

- [ ] **Step 3: Create `apps/api/app/schemas/group.py`**

```python
from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    model_config = ConfigDict(extra="forbid")


class GroupMemberRead(BaseModel):
    user_id: UUID
    username: str
    joined_at: datetime


class GroupSummary(BaseModel):
    id: UUID
    name: str
    owner_id: UUID
    owner_username: str
    is_owner: bool
    member_count: int
    created_at: datetime
    updated_at: datetime


class GroupDetail(GroupSummary):
    members: list[GroupMemberRead]


class GroupAddMember(BaseModel):
    username: str = Field(min_length=1, max_length=50)
```

- [ ] **Step 4: Create `apps/api/app/schemas/loan.py`**

```python
from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LoanCreate(BaseModel):
    borrower_username: Optional[str] = Field(default=None, min_length=1, max_length=50)
    borrower_label: Optional[str] = Field(default=None, min_length=1, max_length=200)
    expected_return: Optional[date] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _exactly_one_borrower(self) -> "LoanCreate":
        has_user = self.borrower_username is not None
        has_label = self.borrower_label is not None
        if has_user == has_label:
            raise ValueError("supply exactly one of borrower_username or borrower_label")
        return self


class LoanRead(BaseModel):
    id: UUID
    item_id: UUID
    borrower_user_id: Optional[UUID]
    borrower_username: Optional[str]
    borrower_label: Optional[str]
    lent_at: datetime
    expected_return: Optional[date]
    returned_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 5: Create `apps/api/app/schemas/transfer.py`**

```python
from __future__ import annotations
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


TransferStatus = Literal["pending", "accepted", "rejected", "cancelled"]


class TransferCreate(BaseModel):
    item_id: UUID
    to_username: str = Field(min_length=1, max_length=50)
    message: Optional[str] = None


class TransferRead(BaseModel):
    id: UUID
    item_id: UUID
    item_name: str
    from_user_id: UUID
    from_username: str
    to_user_id: UUID
    to_username: str
    status: TransferStatus
    message: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]
```

- [ ] **Step 6: Modify `apps/api/app/schemas/item.py`**

Replace `ItemRead` so it reads:
```python
class ItemRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    quantity: int
    min_quantity: Optional[int]
    notes: Optional[str]
    owner_id: UUID
    owner_username: str
    created_at: datetime
    updated_at: datetime
    category: Optional[CategoryRead]
    location: Optional[LocationRead]
    tags: list[TagRead]

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 7: Run schemas test — expect PASS**

- [ ] **Step 8: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/api/app/schemas/group.py apps/api/app/schemas/loan.py apps/api/app/schemas/transfer.py apps/api/app/schemas/item.py apps/api/tests/test_collab_schemas.py
git commit -m "feat(api): add collaboration Pydantic schemas + ItemRead.owner"
```

---

## Task 7: Groups repository

**Files:** `apps/api/app/repositories/groups_repository.py`, `apps/api/tests/test_groups_repository.py`

- [ ] **Step 1: Test**

```python
# tests/test_groups_repository.py
from __future__ import annotations
from uuid import uuid4
import pytest
from app.auth.password import hash_password
from app.models.user import User
from app.repositories import groups_repository as repo


@pytest.fixture
async def users(db_session):
    a = User(email="a@t.io", username="a_user", password_hash=hash_password("secret1234"))
    b = User(email="b@t.io", username="b_user", password_hash=hash_password("secret1234"))
    db_session.add_all([a, b]); await db_session.flush()
    return a, b


async def test_create_adds_owner_as_member(db_session, users):
    a, _ = users
    g = await repo.create(db_session, owner_id=a.id, name="家人")
    members = await repo.list_members(db_session, g.id)
    assert len(members) == 1
    assert members[0].user_id == a.id


async def test_list_for_user_includes_both_owned_and_joined(db_session, users):
    a, b = users
    g1 = await repo.create(db_session, owner_id=a.id, name="a-group")
    g2 = await repo.create(db_session, owner_id=b.id, name="b-group")
    await repo.add_member(db_session, g2.id, a.id)
    rows = await repo.list_for_user(db_session, a.id)
    ids = {r.id for r in rows}
    assert {g1.id, g2.id} == ids


async def test_update_name(db_session, users):
    a, _ = users
    g = await repo.create(db_session, owner_id=a.id, name="old")
    updated = await repo.update(db_session, g, {"name": "new"})
    assert updated.name == "new"


async def test_delete_cascades_members(db_session, users):
    a, _ = users
    g = await repo.create(db_session, owner_id=a.id, name="x")
    ok = await repo.delete(db_session, a.id, g.id)
    assert ok is True


async def test_add_member_unique(db_session, users):
    a, b = users
    g = await repo.create(db_session, owner_id=a.id, name="g")
    await repo.add_member(db_session, g.id, b.id)
    with pytest.raises(Exception):
        await repo.add_member(db_session, g.id, b.id)


async def test_remove_member(db_session, users):
    a, b = users
    g = await repo.create(db_session, owner_id=a.id, name="g")
    await repo.add_member(db_session, g.id, b.id)
    ok = await repo.remove_member(db_session, g.id, b.id)
    assert ok is True
    members = await repo.list_members(db_session, g.id)
    assert {m.user_id for m in members} == {a.id}
```

- [ ] **Step 2: Run — fail with `ModuleNotFoundError`**

- [ ] **Step 3: Implement**

Create `apps/api/app/repositories/groups_repository.py`:
```python
from __future__ import annotations
from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import Group, GroupMember


async def create(session: AsyncSession, *, owner_id: UUID, name: str) -> Group:
    g = Group(owner_id=owner_id, name=name)
    session.add(g)
    await session.flush()
    session.add(GroupMember(group_id=g.id, user_id=owner_id))
    await session.commit()
    await session.refresh(g)
    return g


async def get_owned(session: AsyncSession, owner_id: UUID, group_id: UUID) -> Group | None:
    stmt = select(Group).where(Group.id == group_id, Group.owner_id == owner_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_for_member(
    session: AsyncSession, user_id: UUID, group_id: UUID
) -> Group | None:
    stmt = (
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(Group.id == group_id, GroupMember.user_id == user_id)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_for_user(session: AsyncSession, user_id: UUID) -> list[Group]:
    stmt = (
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == user_id)
        .order_by(Group.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def member_count(session: AsyncSession, group_id: UUID) -> int:
    return int((await session.execute(
        select(func.count(GroupMember.id)).where(GroupMember.group_id == group_id)
    )).scalar_one())


async def update(session: AsyncSession, group: Group, fields: dict) -> Group:
    for k, v in fields.items():
        setattr(group, k, v)
    await session.commit()
    await session.refresh(group)
    return group


async def delete(session: AsyncSession, owner_id: UUID, group_id: UUID) -> bool:
    stmt = sa_delete(Group).where(Group.id == group_id, Group.owner_id == owner_id)
    result = await session.execute(stmt)
    await session.commit()
    return (result.rowcount or 0) > 0


async def list_members(session: AsyncSession, group_id: UUID) -> list[GroupMember]:
    stmt = (
        select(GroupMember)
        .where(GroupMember.group_id == group_id)
        .order_by(GroupMember.joined_at)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_member(
    session: AsyncSession, group_id: UUID, user_id: UUID
) -> GroupMember | None:
    stmt = select(GroupMember).where(
        GroupMember.group_id == group_id, GroupMember.user_id == user_id
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def add_member(
    session: AsyncSession, group_id: UUID, user_id: UUID
) -> GroupMember:
    gm = GroupMember(group_id=group_id, user_id=user_id)
    session.add(gm)
    await session.commit()
    await session.refresh(gm)
    return gm


async def remove_member(
    session: AsyncSession, group_id: UUID, user_id: UUID
) -> bool:
    stmt = sa_delete(GroupMember).where(
        GroupMember.group_id == group_id, GroupMember.user_id == user_id
    )
    result = await session.execute(stmt)
    await session.commit()
    return (result.rowcount or 0) > 0
```

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/api/app/repositories/groups_repository.py apps/api/tests/test_groups_repository.py
git commit -m "feat(api): add groups repository"
```

---

## Task 8: Loans repository

**Files:** `apps/api/app/repositories/loans_repository.py`, `apps/api/tests/test_loans_repository.py`

- [ ] **Step 1: Test**

```python
# tests/test_loans_repository.py
from __future__ import annotations
from uuid import uuid4
import pytest
from app.auth.password import hash_password
from app.models.item import Item
from app.models.user import User
from app.repositories import loans_repository as repo


@pytest.fixture
async def owner_and_item(db_session):
    u = User(email="o@t.io", username="o_user", password_hash=hash_password("secret1234"))
    db_session.add(u); await db_session.flush()
    item = Item(owner_id=u.id, name="傘")
    db_session.add(item); await db_session.commit()
    return u, item


async def test_create_loan_with_label(db_session, owner_and_item):
    _, item = owner_and_item
    loan = await repo.create(db_session, item_id=item.id, borrower_label="張三")
    assert loan.returned_at is None
    assert loan.borrower_label == "張三"


async def test_active_loan_uniqueness(db_session, owner_and_item):
    _, item = owner_and_item
    await repo.create(db_session, item_id=item.id, borrower_label="a")
    with pytest.raises(Exception):
        await repo.create(db_session, item_id=item.id, borrower_label="b")


async def test_list_by_item(db_session, owner_and_item):
    _, item = owner_and_item
    a = await repo.create(db_session, item_id=item.id, borrower_label="a")
    await repo.mark_returned(db_session, a)
    await repo.create(db_session, item_id=item.id, borrower_label="b")
    rows = await repo.list_by_item(db_session, item.id)
    assert len(rows) == 2


async def test_get_active(db_session, owner_and_item):
    _, item = owner_and_item
    assert await repo.get_active(db_session, item.id) is None
    loan = await repo.create(db_session, item_id=item.id, borrower_label="a")
    active = await repo.get_active(db_session, item.id)
    assert active is not None
    assert active.id == loan.id


async def test_mark_returned(db_session, owner_and_item):
    _, item = owner_and_item
    loan = await repo.create(db_session, item_id=item.id, borrower_label="a")
    returned = await repo.mark_returned(db_session, loan)
    assert returned.returned_at is not None


async def test_delete(db_session, owner_and_item):
    _, item = owner_and_item
    loan = await repo.create(db_session, item_id=item.id, borrower_label="a")
    ok = await repo.delete(db_session, item.id, loan.id)
    assert ok is True
```

- [ ] **Step 2: Run — fail with `ModuleNotFoundError`**

- [ ] **Step 3: Implement**

Create `apps/api/app/repositories/loans_repository.py`:
```python
from __future__ import annotations
from datetime import date
from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import _utcnow
from app.models.loan import ItemLoan


async def create(
    session: AsyncSession, *, item_id: UUID,
    borrower_user_id: UUID | None = None,
    borrower_label: str | None = None,
    expected_return: date | None = None,
    notes: str | None = None,
) -> ItemLoan:
    loan = ItemLoan(
        item_id=item_id,
        borrower_user_id=borrower_user_id,
        borrower_label=borrower_label,
        expected_return=expected_return,
        notes=notes,
    )
    session.add(loan)
    await session.commit()
    await session.refresh(loan)
    return loan


async def get(
    session: AsyncSession, item_id: UUID, loan_id: UUID
) -> ItemLoan | None:
    stmt = select(ItemLoan).where(ItemLoan.id == loan_id, ItemLoan.item_id == item_id)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_active(session: AsyncSession, item_id: UUID) -> ItemLoan | None:
    stmt = select(ItemLoan).where(
        ItemLoan.item_id == item_id, ItemLoan.returned_at.is_(None)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_by_item(session: AsyncSession, item_id: UUID) -> list[ItemLoan]:
    stmt = (
        select(ItemLoan)
        .where(ItemLoan.item_id == item_id)
        .order_by(ItemLoan.created_at.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def mark_returned(session: AsyncSession, loan: ItemLoan) -> ItemLoan:
    loan.returned_at = _utcnow()
    await session.commit()
    await session.refresh(loan)
    return loan


async def delete(
    session: AsyncSession, item_id: UUID, loan_id: UUID
) -> bool:
    stmt = sa_delete(ItemLoan).where(
        ItemLoan.id == loan_id, ItemLoan.item_id == item_id
    )
    result = await session.execute(stmt)
    await session.commit()
    return (result.rowcount or 0) > 0
```

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/api/app/repositories/loans_repository.py apps/api/tests/test_loans_repository.py
git commit -m "feat(api): add loans repository with active-uniqueness"
```

---

## Task 9: Transfers repository

**Files:** `apps/api/app/repositories/transfers_repository.py`, `apps/api/tests/test_transfers_repository.py`

- [ ] **Step 1: Test**

```python
# tests/test_transfers_repository.py
from __future__ import annotations
from uuid import uuid4
import pytest
from app.auth.password import hash_password
from app.models.item import Item
from app.models.user import User
from app.repositories import transfers_repository as repo


@pytest.fixture
async def two_users_and_item(db_session):
    a = User(email="a@t.io", username="a_user", password_hash=hash_password("secret1234"))
    b = User(email="b@t.io", username="b_user", password_hash=hash_password("secret1234"))
    db_session.add_all([a, b]); await db_session.flush()
    item = Item(owner_id=a.id, name="傘")
    db_session.add(item); await db_session.commit()
    return a, b, item


async def test_create_pending(db_session, two_users_and_item):
    a, b, item = two_users_and_item
    t = await repo.create(db_session, item_id=item.id, from_user_id=a.id, to_user_id=b.id)
    assert t.status == "pending"


async def test_one_pending_per_item(db_session, two_users_and_item):
    a, b, item = two_users_and_item
    await repo.create(db_session, item_id=item.id, from_user_id=a.id, to_user_id=b.id)
    with pytest.raises(Exception):
        await repo.create(db_session, item_id=item.id, from_user_id=a.id, to_user_id=b.id)


async def test_list_for_user(db_session, two_users_and_item):
    a, b, item = two_users_and_item
    await repo.create(db_session, item_id=item.id, from_user_id=a.id, to_user_id=b.id)
    incoming = await repo.list_for_user(db_session, b.id, direction="incoming")
    outgoing = await repo.list_for_user(db_session, a.id, direction="outgoing")
    assert len(incoming) == 1
    assert len(outgoing) == 1


async def test_resolve_accept(db_session, two_users_and_item):
    a, b, item = two_users_and_item
    t = await repo.create(db_session, item_id=item.id, from_user_id=a.id, to_user_id=b.id)
    resolved = await repo.resolve(db_session, t, status="accepted")
    assert resolved.status == "accepted"
    assert resolved.resolved_at is not None


async def test_get_pending_for_item(db_session, two_users_and_item):
    a, b, item = two_users_and_item
    assert await repo.get_pending_for_item(db_session, item.id) is None
    t = await repo.create(db_session, item_id=item.id, from_user_id=a.id, to_user_id=b.id)
    pending = await repo.get_pending_for_item(db_session, item.id)
    assert pending is not None
    assert pending.id == t.id


async def test_get_pending_gone_after_resolve(db_session, two_users_and_item):
    a, b, item = two_users_and_item
    t = await repo.create(db_session, item_id=item.id, from_user_id=a.id, to_user_id=b.id)
    await repo.resolve(db_session, t, status="rejected")
    assert await repo.get_pending_for_item(db_session, item.id) is None
```

- [ ] **Step 2: Run — expect `ModuleNotFoundError`**

- [ ] **Step 3: Implement**

Create `apps/api/app/repositories/transfers_repository.py`:
```python
from __future__ import annotations
from typing import Literal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import _utcnow
from app.models.transfer import ItemTransfer


async def create(
    session: AsyncSession, *,
    item_id: UUID, from_user_id: UUID, to_user_id: UUID,
    message: str | None = None,
) -> ItemTransfer:
    t = ItemTransfer(
        item_id=item_id,
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        message=message,
        status="pending",
    )
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return t


async def get(session: AsyncSession, transfer_id: UUID) -> ItemTransfer | None:
    return (await session.execute(
        select(ItemTransfer).where(ItemTransfer.id == transfer_id)
    )).scalar_one_or_none()


async def get_pending_for_item(
    session: AsyncSession, item_id: UUID
) -> ItemTransfer | None:
    stmt = select(ItemTransfer).where(
        ItemTransfer.item_id == item_id, ItemTransfer.status == "pending"
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_for_user(
    session: AsyncSession, user_id: UUID,
    *,
    direction: Literal["incoming", "outgoing", "both"] = "both",
    status: Literal["pending", "resolved", "all"] = "all",
) -> list[ItemTransfer]:
    stmt = select(ItemTransfer)
    if direction == "incoming":
        stmt = stmt.where(ItemTransfer.to_user_id == user_id)
    elif direction == "outgoing":
        stmt = stmt.where(ItemTransfer.from_user_id == user_id)
    else:
        stmt = stmt.where(
            or_(
                ItemTransfer.from_user_id == user_id,
                ItemTransfer.to_user_id == user_id,
            )
        )
    if status == "pending":
        stmt = stmt.where(ItemTransfer.status == "pending")
    elif status == "resolved":
        stmt = stmt.where(ItemTransfer.status != "pending")
    stmt = stmt.order_by(ItemTransfer.created_at.desc())
    return list((await session.execute(stmt)).scalars().all())


async def resolve(
    session: AsyncSession, t: ItemTransfer,
    *, status: Literal["accepted", "rejected", "cancelled"],
) -> ItemTransfer:
    t.status = status
    t.resolved_at = _utcnow()
    await session.commit()
    await session.refresh(t)
    return t
```

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/api/app/repositories/transfers_repository.py apps/api/tests/test_transfers_repository.py
git commit -m "feat(api): add transfers repository with unique-pending"
```

---

## Task 10: Visibility service + items integration

**Files:** `apps/api/app/services/visibility_service.py`, `apps/api/app/repositories/items_repository.py` (modify), `apps/api/app/services/items_service.py` (modify), `apps/api/tests/test_visibility_service.py`

- [ ] **Step 1: Test**

```python
# tests/test_visibility_service.py
from __future__ import annotations
import pytest
from app.auth.password import hash_password
from app.models.user import User
from app.repositories import groups_repository
from app.services.visibility_service import visible_item_owner_ids


@pytest.fixture
async def three_users(db_session):
    a = User(email="a@t.io", username="a_user", password_hash=hash_password("secret1234"))
    b = User(email="b@t.io", username="b_user", password_hash=hash_password("secret1234"))
    c = User(email="c@t.io", username="c_user", password_hash=hash_password("secret1234"))
    db_session.add_all([a, b, c]); await db_session.flush()
    return a, b, c


async def test_alone_returns_self(db_session, three_users):
    a, _, _ = three_users
    assert await visible_item_owner_ids(db_session, a.id) == {a.id}


async def test_group_member_sees_everyone_in_group(db_session, three_users):
    a, b, c = three_users
    g = await groups_repository.create(db_session, owner_id=a.id, name="g")
    await groups_repository.add_member(db_session, g.id, b.id)
    await groups_repository.add_member(db_session, g.id, c.id)
    assert await visible_item_owner_ids(db_session, a.id) == {a.id, b.id, c.id}
    assert await visible_item_owner_ids(db_session, b.id) == {a.id, b.id, c.id}


async def test_non_member_not_visible(db_session, three_users):
    a, b, c = three_users
    g = await groups_repository.create(db_session, owner_id=a.id, name="g")
    await groups_repository.add_member(db_session, g.id, b.id)
    assert c.id not in await visible_item_owner_ids(db_session, a.id)


async def test_union_across_groups(db_session, three_users):
    a, b, c = three_users
    g1 = await groups_repository.create(db_session, owner_id=a.id, name="g1")
    await groups_repository.add_member(db_session, g1.id, b.id)
    g2 = await groups_repository.create(db_session, owner_id=a.id, name="g2")
    await groups_repository.add_member(db_session, g2.id, c.id)
    assert await visible_item_owner_ids(db_session, a.id) == {a.id, b.id, c.id}
```

- [ ] **Step 2: Run — expect `ModuleNotFoundError`**

- [ ] **Step 3: Implement visibility service**

Create `apps/api/app/services/visibility_service.py`:
```python
from __future__ import annotations
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import GroupMember


async def visible_item_owner_ids(
    session: AsyncSession, user_id: UUID
) -> set[UUID]:
    """Owner ids whose items the given user may read.

    = {user's own id} ∪ {user_ids of all fellow group members}
    """
    ids: set[UUID] = {user_id}
    own_groups = (await session.execute(
        select(GroupMember.group_id).where(GroupMember.user_id == user_id)
    )).scalars().all()
    if not own_groups:
        return ids
    stmt = select(GroupMember.user_id).where(
        GroupMember.group_id.in_(own_groups)
    )
    for uid in (await session.execute(stmt)).scalars():
        ids.add(uid)
    return ids
```

- [ ] **Step 4: Modify items_repository to accept visible owner ids**

Replace `_base_query` in `apps/api/app/repositories/items_repository.py`:
```python
def _base_query(owner_ids):
    """owner_ids may be a single UUID or an iterable/set of UUIDs."""
    if isinstance(owner_ids, (set, list, tuple)):
        if not owner_ids:
            return select(Item).where(Item.id.is_(None))  # no matches
        return select(Item).where(
            Item.owner_id.in_(owner_ids), Item.is_deleted.is_(False)
        )
    return select(Item).where(
        Item.owner_id == owner_ids, Item.is_deleted.is_(False)
    )
```

Modify `get_owned` so it stays strict (single owner); add a new `get_visible`:
```python
async def get_visible(
    session: AsyncSession, owner_ids: set[UUID], item_id: UUID
) -> Item | None:
    stmt = (
        _base_query(owner_ids)
        .where(Item.id == item_id)
        .options(
            selectinload(Item.tags),
            selectinload(Item.category),
            selectinload(Item.location),
            selectinload(Item.owner),
        )
    )
    return (await session.execute(stmt)).scalar_one_or_none()
```

Update `list_paginated`'s signature to accept `owner_ids: set[UUID]` (or single UUID for backward compat) and use `_base_query(owner_ids)`. Also add `selectinload(Item.owner)` to option chain so `ItemRead.owner_username` works.

- [ ] **Step 5: Modify items_service reads to use visibility**

In `apps/api/app/services/items_service.py`:
- Add `from app.services.visibility_service import visible_item_owner_ids`
- `list_items`: compute `visible = await visible_item_owner_ids(session, owner_id)`; pass to `items_repository.list_paginated(session, visible, ...)`
- `get_item`: same, use `items_repository.get_visible(session, visible, item_id)`
- `update_item` / `delete_item` / loan emit logic stay using `get_owned(session, owner_id, item_id)` (owner-only writes)

Update `ItemRead.model_validate` calls to pass `from_attributes=True` — add a helper to augment owner_username. Actually simpler: `ItemRead` has `owner_username` field with `from_attributes=True`, and `Item.owner` is loaded via `selectinload`. Create an explicit shaping helper:

```python
def _to_read(item: Item) -> ItemRead:
    return ItemRead.model_validate({
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "quantity": item.quantity,
        "min_quantity": item.min_quantity,
        "notes": item.notes,
        "owner_id": item.owner_id,
        "owner_username": item.owner.username,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "category": item.category,
        "location": item.location,
        "tags": item.tags,
    })
```

Replace all `ItemRead.model_validate(item)` in `items_service.py` with `_to_read(item)`.

Make sure `items_repository.create` and `save` also return items with `owner` loaded — after each call, `await session.refresh(item, ["owner"])` or similar. Simpler: after `await items_repository.save(session, item)`, reload via `get_owned` + `selectinload` pattern.

Concrete change: in `items_repository.create` and `save`, add after `await session.commit()`:
```python
await session.refresh(item, ["tags", "category", "location", "owner"])
```

- [ ] **Step 6: Run all items + visibility tests**

Run: `cd apps/api && .venv/bin/python -m pytest tests/test_visibility_service.py tests/test_items_service.py tests/test_items_routes.py tests/test_items_repository.py -v 2>&1 | tail -30`
Expected: visibility 4 pass, items test suites all pass (existing tests must still pass with new owner_username field).

Adjust any items tests that assert `ItemRead` shape — they must now include `owner_id` + `owner_username`.

- [ ] **Step 7: Full suite sanity**

`cd apps/api && .venv/bin/python -m pytest -q`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/api/app/services/visibility_service.py apps/api/app/services/items_service.py apps/api/app/repositories/items_repository.py apps/api/tests/test_visibility_service.py apps/api/tests/test_items_*.py
git commit -m "feat(api): add visibility service + extend item reads to group members"
```

---

## Task 11: Groups service

**Files:** `apps/api/app/services/groups_service.py`, `apps/api/tests/test_groups_service.py`

- [ ] **Step 1: Test**

```python
# tests/test_groups_service.py
from __future__ import annotations
from uuid import uuid4
import pytest
from fastapi import HTTPException
from app.auth.password import hash_password
from app.models.user import User
from app.schemas.group import GroupAddMember, GroupCreate, GroupUpdate
from app.services import groups_service as svc


@pytest.fixture
async def users(db_session):
    a = User(email="a@t.io", username="a_user", password_hash=hash_password("secret1234"))
    b = User(email="b@t.io", username="b_user", password_hash=hash_password("secret1234"))
    db_session.add_all([a, b]); await db_session.flush()
    return a, b


async def test_create_group_owner_is_member(db_session, users):
    a, _ = users
    summary = await svc.create_group(db_session, a.id, GroupCreate(name="g"))
    detail = await svc.get_group_detail(db_session, a.id, summary.id)
    assert detail.is_owner is True
    assert len(detail.members) == 1


async def test_non_owner_cannot_rename(db_session, users):
    a, b = users
    g = await svc.create_group(db_session, a.id, GroupCreate(name="g"))
    await svc.add_member_by_username(db_session, a.id, g.id, GroupAddMember(username="b_user"))
    with pytest.raises(HTTPException) as ex:
        await svc.update_group(db_session, b.id, g.id, GroupUpdate(name="new"))
    assert ex.value.status_code == 404


async def test_non_owner_cannot_add_member(db_session, users):
    a, b = users
    g = await svc.create_group(db_session, a.id, GroupCreate(name="g"))
    await svc.add_member_by_username(db_session, a.id, g.id, GroupAddMember(username="b_user"))
    with pytest.raises(HTTPException) as ex:
        await svc.add_member_by_username(db_session, b.id, g.id, GroupAddMember(username="a_user"))
    assert ex.value.status_code == 404


async def test_add_member_unknown_username(db_session, users):
    a, _ = users
    g = await svc.create_group(db_session, a.id, GroupCreate(name="g"))
    with pytest.raises(HTTPException) as ex:
        await svc.add_member_by_username(db_session, a.id, g.id, GroupAddMember(username="ghost"))
    assert ex.value.status_code == 404


async def test_add_member_duplicate(db_session, users):
    a, _ = users
    g = await svc.create_group(db_session, a.id, GroupCreate(name="g"))
    with pytest.raises(HTTPException) as ex:
        await svc.add_member_by_username(db_session, a.id, g.id, GroupAddMember(username="a_user"))
    assert ex.value.status_code == 409


async def test_member_can_leave(db_session, users):
    a, b = users
    g = await svc.create_group(db_session, a.id, GroupCreate(name="g"))
    await svc.add_member_by_username(db_session, a.id, g.id, GroupAddMember(username="b_user"))
    await svc.remove_member(db_session, b.id, g.id, b.id)
    detail = await svc.get_group_detail(db_session, a.id, g.id)
    assert len(detail.members) == 1


async def test_cannot_remove_owner(db_session, users):
    a, _ = users
    g = await svc.create_group(db_session, a.id, GroupCreate(name="g"))
    with pytest.raises(HTTPException) as ex:
        await svc.remove_member(db_session, a.id, g.id, a.id)
    assert ex.value.status_code == 409
```

- [ ] **Step 2: Run — expect `ModuleNotFoundError`**

- [ ] **Step 3: Implement**

Create `apps/api/app/services/groups_service.py`:
```python
from __future__ import annotations
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import GroupMember
from app.models.user import User
from app.repositories import groups_repository, user_repo as _unused  # placeholder
from app.schemas.group import (
    GroupAddMember,
    GroupCreate,
    GroupDetail,
    GroupMemberRead,
    GroupSummary,
    GroupUpdate,
)


async def _user_by_username(session: AsyncSession, username: str) -> User | None:
    return (await session.execute(
        select(User).where(User.username == username)
    )).scalar_one_or_none()


async def _summary(session: AsyncSession, g, current_user_id: UUID) -> GroupSummary:
    owner = (await session.execute(
        select(User).where(User.id == g.owner_id)
    )).scalar_one()
    count = await groups_repository.member_count(session, g.id)
    return GroupSummary(
        id=g.id, name=g.name, owner_id=g.owner_id, owner_username=owner.username,
        is_owner=(g.owner_id == current_user_id), member_count=count,
        created_at=g.created_at, updated_at=g.updated_at,
    )


async def list_groups(session: AsyncSession, user_id: UUID) -> list[GroupSummary]:
    groups = await groups_repository.list_for_user(session, user_id)
    return [await _summary(session, g, user_id) for g in groups]


async def create_group(
    session: AsyncSession, owner_id: UUID, body: GroupCreate
) -> GroupSummary:
    g = await groups_repository.create(session, owner_id=owner_id, name=body.name)
    return await _summary(session, g, owner_id)


async def _ensure_visible(session, user_id, group_id):
    g = await groups_repository.get_for_member(session, user_id, group_id)
    if g is None:
        raise HTTPException(status_code=404, detail="group not found")
    return g


async def _ensure_owned(session, user_id, group_id):
    g = await groups_repository.get_owned(session, user_id, group_id)
    if g is None:
        raise HTTPException(status_code=404, detail="group not found")
    return g


async def get_group_detail(
    session: AsyncSession, user_id: UUID, group_id: UUID
) -> GroupDetail:
    g = await _ensure_visible(session, user_id, group_id)
    summary = await _summary(session, g, user_id)
    gms = await groups_repository.list_members(session, group_id)
    user_ids = [gm.user_id for gm in gms]
    users_map = {
        u.id: u for u in (await session.execute(
            select(User).where(User.id.in_(user_ids))
        )).scalars()
    }
    members = [
        GroupMemberRead(
            user_id=gm.user_id,
            username=users_map[gm.user_id].username,
            joined_at=gm.joined_at,
        ) for gm in gms
    ]
    return GroupDetail(**summary.model_dump(), members=members)


async def update_group(
    session: AsyncSession, user_id: UUID, group_id: UUID, body: GroupUpdate
) -> GroupSummary:
    g = await _ensure_owned(session, user_id, group_id)
    fields = body.model_dump(exclude_unset=True)
    updated = await groups_repository.update(session, g, fields)
    return await _summary(session, updated, user_id)


async def delete_group(
    session: AsyncSession, user_id: UUID, group_id: UUID
) -> None:
    if not await groups_repository.delete(session, user_id, group_id):
        raise HTTPException(status_code=404, detail="group not found")


async def add_member_by_username(
    session: AsyncSession, user_id: UUID, group_id: UUID, body: GroupAddMember
) -> GroupMemberRead:
    g = await _ensure_owned(session, user_id, group_id)
    user = await _user_by_username(session, body.username)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    existing = await groups_repository.get_member(session, group_id, user.id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="already a member")
    gm = await groups_repository.add_member(session, group_id, user.id)
    return GroupMemberRead(user_id=user.id, username=user.username, joined_at=gm.joined_at)


async def remove_member(
    session: AsyncSession, user_id: UUID, group_id: UUID, target_user_id: UUID
) -> None:
    g = await _ensure_visible(session, user_id, group_id)
    if target_user_id == g.owner_id:
        raise HTTPException(status_code=409, detail="cannot remove group owner")
    # owner can remove anyone; non-owner can only remove self
    if user_id != g.owner_id and user_id != target_user_id:
        raise HTTPException(status_code=403, detail="forbidden")
    if not await groups_repository.remove_member(session, group_id, target_user_id):
        raise HTTPException(status_code=404, detail="member not found")
```

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/api/app/services/groups_service.py apps/api/tests/test_groups_service.py
git commit -m "feat(api): add groups service with owner rules"
```

---

## Task 12: Loans service

**Files:** `apps/api/app/services/loans_service.py`, `apps/api/tests/test_loans_service.py`

- [ ] **Step 1: Test**

```python
# tests/test_loans_service.py
from __future__ import annotations
from uuid import uuid4
import pytest
from fastapi import HTTPException
from app.auth.password import hash_password
from app.models.item import Item
from app.models.user import User
from app.schemas.loan import LoanCreate
from app.services import loans_service as svc


@pytest.fixture
async def owner_and_item(db_session):
    u = User(email="l@t.io", username="l_user", password_hash=hash_password("secret1234"))
    db_session.add(u); await db_session.flush()
    item = Item(owner_id=u.id, name="傘")
    db_session.add(item); await db_session.commit()
    return u, item


async def test_create_with_label(db_session, owner_and_item):
    u, item = owner_and_item
    loan = await svc.create_loan(db_session, u.id, item.id, LoanCreate(borrower_label="張三"))
    assert loan.borrower_label == "張三"


async def test_create_with_username_resolves_user(db_session, owner_and_item):
    u, item = owner_and_item
    friend = User(email="f@t.io", username="friend_user", password_hash=hash_password("secret1234"))
    db_session.add(friend); await db_session.commit()
    loan = await svc.create_loan(db_session, u.id, item.id, LoanCreate(borrower_username="friend_user"))
    assert loan.borrower_user_id == friend.id


async def test_create_unknown_username_422(db_session, owner_and_item):
    u, item = owner_and_item
    with pytest.raises(HTTPException) as ex:
        await svc.create_loan(db_session, u.id, item.id, LoanCreate(borrower_username="ghost"))
    assert ex.value.status_code == 422


async def test_existing_active_rejects(db_session, owner_and_item):
    u, item = owner_and_item
    await svc.create_loan(db_session, u.id, item.id, LoanCreate(borrower_label="a"))
    with pytest.raises(HTTPException) as ex:
        await svc.create_loan(db_session, u.id, item.id, LoanCreate(borrower_label="b"))
    assert ex.value.status_code == 409


async def test_non_owner_cannot_create(db_session, owner_and_item):
    u, item = owner_and_item
    other = User(email="x@t.io", username="x_user", password_hash=hash_password("secret1234"))
    db_session.add(other); await db_session.commit()
    with pytest.raises(HTTPException) as ex:
        await svc.create_loan(db_session, other.id, item.id, LoanCreate(borrower_label="a"))
    assert ex.value.status_code == 404


async def test_return_loan(db_session, owner_and_item):
    u, item = owner_and_item
    loan = await svc.create_loan(db_session, u.id, item.id, LoanCreate(borrower_label="a"))
    returned = await svc.mark_returned(db_session, u.id, item.id, loan.id)
    assert returned.returned_at is not None


async def test_return_already_returned_409(db_session, owner_and_item):
    u, item = owner_and_item
    loan = await svc.create_loan(db_session, u.id, item.id, LoanCreate(borrower_label="a"))
    await svc.mark_returned(db_session, u.id, item.id, loan.id)
    with pytest.raises(HTTPException) as ex:
        await svc.mark_returned(db_session, u.id, item.id, loan.id)
    assert ex.value.status_code == 409
```

- [ ] **Step 2: Run — expect `ModuleNotFoundError`**

- [ ] **Step 3: Implement**

Create `apps/api/app/services/loans_service.py`:
```python
from __future__ import annotations
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories import items_repository, loans_repository
from app.schemas.loan import LoanCreate, LoanRead


def _to_read(loan, borrower: User | None) -> LoanRead:
    return LoanRead(
        id=loan.id,
        item_id=loan.item_id,
        borrower_user_id=loan.borrower_user_id,
        borrower_username=borrower.username if borrower else None,
        borrower_label=loan.borrower_label,
        lent_at=loan.lent_at,
        expected_return=loan.expected_return,
        returned_at=loan.returned_at,
        notes=loan.notes,
        created_at=loan.created_at,
        updated_at=loan.updated_at,
    )


async def _ensure_owner(session, user_id, item_id):
    item = await items_repository.get_owned(session, user_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    return item


async def list_loans(session, user_id, item_id) -> list[LoanRead]:
    await _ensure_owner(session, user_id, item_id)
    rows = await loans_repository.list_by_item(session, item_id)
    user_ids = [r.borrower_user_id for r in rows if r.borrower_user_id is not None]
    users = {u.id: u for u in (await session.execute(
        select(User).where(User.id.in_(user_ids))
    )).scalars()} if user_ids else {}
    return [_to_read(r, users.get(r.borrower_user_id) if r.borrower_user_id else None) for r in rows]


async def create_loan(
    session: AsyncSession, user_id: UUID, item_id: UUID, body: LoanCreate
) -> LoanRead:
    await _ensure_owner(session, user_id, item_id)
    active = await loans_repository.get_active(session, item_id)
    if active is not None:
        raise HTTPException(status_code=409, detail="item already has an active loan")
    borrower: User | None = None
    borrower_user_id = None
    if body.borrower_username is not None:
        borrower = (await session.execute(
            select(User).where(User.username == body.borrower_username)
        )).scalar_one_or_none()
        if borrower is None:
            raise HTTPException(status_code=422, detail="borrower_username not found")
        borrower_user_id = borrower.id
    loan = await loans_repository.create(
        session,
        item_id=item_id,
        borrower_user_id=borrower_user_id,
        borrower_label=body.borrower_label,
        expected_return=body.expected_return,
        notes=body.notes,
    )
    return _to_read(loan, borrower)


async def mark_returned(
    session: AsyncSession, user_id: UUID, item_id: UUID, loan_id: UUID
) -> LoanRead:
    await _ensure_owner(session, user_id, item_id)
    loan = await loans_repository.get(session, item_id, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="loan not found")
    if loan.returned_at is not None:
        raise HTTPException(status_code=409, detail="already returned")
    returned = await loans_repository.mark_returned(session, loan)
    borrower = None
    if returned.borrower_user_id:
        borrower = (await session.execute(
            select(User).where(User.id == returned.borrower_user_id)
        )).scalar_one_or_none()
    return _to_read(returned, borrower)


async def delete_loan(
    session: AsyncSession, user_id: UUID, item_id: UUID, loan_id: UUID
) -> None:
    await _ensure_owner(session, user_id, item_id)
    if not await loans_repository.delete(session, item_id, loan_id):
        raise HTTPException(status_code=404, detail="loan not found")
```

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/api/app/services/loans_service.py apps/api/tests/test_loans_service.py
git commit -m "feat(api): add loans service with active-guard"
```

---

## Task 13: Transfers service

**Files:** `apps/api/app/services/transfers_service.py`, `apps/api/tests/test_transfers_service.py`

- [ ] **Step 1: Test**

```python
# tests/test_transfers_service.py
from __future__ import annotations
from uuid import uuid4
import pytest
from fastapi import HTTPException
from app.auth.password import hash_password
from app.models.item import Item
from app.models.user import User
from app.schemas.transfer import TransferCreate
from app.services import transfers_service as svc


@pytest.fixture
async def two_users_and_item(db_session):
    a = User(email="a@t.io", username="a_user", password_hash=hash_password("secret1234"))
    b = User(email="b@t.io", username="b_user", password_hash=hash_password("secret1234"))
    db_session.add_all([a, b]); await db_session.flush()
    item = Item(owner_id=a.id, name="筆")
    db_session.add(item); await db_session.commit()
    return a, b, item


async def test_create_transfer(db_session, two_users_and_item):
    a, b, item = two_users_and_item
    t = await svc.create_transfer(db_session, a.id, TransferCreate(item_id=item.id, to_username="b_user"))
    assert t.status == "pending"
    assert t.to_user_id == b.id


async def test_self_transfer_422(db_session, two_users_and_item):
    a, _, item = two_users_and_item
    with pytest.raises(HTTPException) as ex:
        await svc.create_transfer(db_session, a.id, TransferCreate(item_id=item.id, to_username="a_user"))
    assert ex.value.status_code == 422


async def test_non_owner_404(db_session, two_users_and_item):
    _, b, item = two_users_and_item
    with pytest.raises(HTTPException) as ex:
        await svc.create_transfer(db_session, b.id, TransferCreate(item_id=item.id, to_username="b_user"))
    assert ex.value.status_code == 404


async def test_double_pending_409(db_session, two_users_and_item):
    a, _, item = two_users_and_item
    await svc.create_transfer(db_session, a.id, TransferCreate(item_id=item.id, to_username="b_user"))
    with pytest.raises(HTTPException) as ex:
        await svc.create_transfer(db_session, a.id, TransferCreate(item_id=item.id, to_username="b_user"))
    assert ex.value.status_code == 409


async def test_accept_flips_owner(db_session, two_users_and_item):
    a, b, item = two_users_and_item
    t = await svc.create_transfer(db_session, a.id, TransferCreate(item_id=item.id, to_username="b_user"))
    resolved = await svc.accept_transfer(db_session, b.id, t.id)
    assert resolved.status == "accepted"
    await db_session.refresh(item)
    assert item.owner_id == b.id


async def test_accept_non_recipient_404(db_session, two_users_and_item):
    a, b, item = two_users_and_item
    t = await svc.create_transfer(db_session, a.id, TransferCreate(item_id=item.id, to_username="b_user"))
    with pytest.raises(HTTPException) as ex:
        await svc.accept_transfer(db_session, a.id, t.id)
    assert ex.value.status_code == 404


async def test_cancel_by_sender(db_session, two_users_and_item):
    a, _, item = two_users_and_item
    t = await svc.create_transfer(db_session, a.id, TransferCreate(item_id=item.id, to_username="b_user"))
    resolved = await svc.cancel_transfer(db_session, a.id, t.id)
    assert resolved.status == "cancelled"


async def test_reject_by_recipient(db_session, two_users_and_item):
    a, b, item = two_users_and_item
    t = await svc.create_transfer(db_session, a.id, TransferCreate(item_id=item.id, to_username="b_user"))
    resolved = await svc.reject_transfer(db_session, b.id, t.id)
    assert resolved.status == "rejected"
```

- [ ] **Step 2: Run — expect `ModuleNotFoundError`**

- [ ] **Step 3: Implement**

Create `apps/api/app/services/transfers_service.py`:
```python
from __future__ import annotations
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item
from app.models.user import User
from app.repositories import (
    items_repository,
    loans_repository,
    transfers_repository,
)
from app.schemas.transfer import TransferCreate, TransferRead
from app.services import notifications_service


async def _to_read(session, t) -> TransferRead:
    rows = {u.id: u for u in (await session.execute(
        select(User).where(User.id.in_([t.from_user_id, t.to_user_id]))
    )).scalars()}
    item = (await session.execute(
        select(Item).where(Item.id == t.item_id)
    )).scalar_one_or_none()
    return TransferRead(
        id=t.id,
        item_id=t.item_id,
        item_name=item.name if item else "(deleted)",
        from_user_id=t.from_user_id,
        from_username=rows[t.from_user_id].username,
        to_user_id=t.to_user_id,
        to_username=rows[t.to_user_id].username,
        status=t.status,
        message=t.message,
        created_at=t.created_at,
        resolved_at=t.resolved_at,
    )


async def list_transfers(
    session, user_id, *, direction, status_filter,
) -> list[TransferRead]:
    rows = await transfers_repository.list_for_user(
        session, user_id, direction=direction, status=status_filter
    )
    return [await _to_read(session, r) for r in rows]


async def create_transfer(
    session: AsyncSession, user_id: UUID, body: TransferCreate
) -> TransferRead:
    item = await items_repository.get_owned(session, user_id, body.item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="item not found")
    recipient = (await session.execute(
        select(User).where(User.username == body.to_username)
    )).scalar_one_or_none()
    if recipient is None:
        raise HTTPException(status_code=404, detail="recipient not found")
    if recipient.id == user_id:
        raise HTTPException(status_code=422, detail="cannot transfer to self")
    existing = await transfers_repository.get_pending_for_item(session, body.item_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="item already has a pending transfer")
    active_loan = await loans_repository.get_active(session, body.item_id)
    if active_loan is not None:
        raise HTTPException(status_code=409, detail="item is currently on loan")

    t = await transfers_repository.create(
        session, item_id=body.item_id, from_user_id=user_id, to_user_id=recipient.id,
        message=body.message,
    )
    sender = (await session.execute(
        select(User).where(User.id == user_id)
    )).scalar_one()
    await notifications_service.emit(
        session,
        user_id=recipient.id,
        type="transfer.request",
        title=f"{sender.username} 想轉移「{item.name}」給你",
        body=body.message,
        link="/collaboration?tab=transfers",
    )
    return await _to_read(session, t)


async def _get_transfer_for_user(
    session, user_id: UUID, transfer_id: UUID, *, as_role: Literal["recipient", "sender"]
):
    t = await transfers_repository.get(session, transfer_id)
    if t is None:
        raise HTTPException(status_code=404, detail="transfer not found")
    if as_role == "recipient" and t.to_user_id != user_id:
        raise HTTPException(status_code=404, detail="transfer not found")
    if as_role == "sender" and t.from_user_id != user_id:
        raise HTTPException(status_code=404, detail="transfer not found")
    return t


async def accept_transfer(
    session: AsyncSession, user_id: UUID, transfer_id: UUID
) -> TransferRead:
    t = await _get_transfer_for_user(session, user_id, transfer_id, as_role="recipient")
    if t.status != "pending":
        raise HTTPException(status_code=409, detail="transfer already resolved")
    item = (await session.execute(
        select(Item).where(Item.id == t.item_id)
    )).scalar_one_or_none()
    if item is None or item.owner_id != t.from_user_id:
        raise HTTPException(status_code=409, detail="item no longer owned by sender")
    active_loan = await loans_repository.get_active(session, t.item_id)
    if active_loan is not None:
        raise HTTPException(status_code=409, detail="item is currently on loan")
    item.owner_id = t.to_user_id
    resolved = await transfers_repository.resolve(session, t, status="accepted")
    recipient = (await session.execute(
        select(User).where(User.id == t.to_user_id)
    )).scalar_one()
    await notifications_service.emit(
        session, user_id=t.from_user_id, type="transfer.accepted",
        title=f"{recipient.username} 已接受「{item.name}」的轉移",
        link="/collaboration?tab=transfers",
    )
    return await _to_read(session, resolved)


async def reject_transfer(
    session: AsyncSession, user_id: UUID, transfer_id: UUID
) -> TransferRead:
    t = await _get_transfer_for_user(session, user_id, transfer_id, as_role="recipient")
    if t.status != "pending":
        raise HTTPException(status_code=409, detail="transfer already resolved")
    resolved = await transfers_repository.resolve(session, t, status="rejected")
    return await _to_read(session, resolved)


async def cancel_transfer(
    session: AsyncSession, user_id: UUID, transfer_id: UUID
) -> TransferRead:
    t = await _get_transfer_for_user(session, user_id, transfer_id, as_role="sender")
    if t.status != "pending":
        raise HTTPException(status_code=409, detail="transfer already resolved")
    resolved = await transfers_repository.resolve(session, t, status="cancelled")
    return await _to_read(session, resolved)
```

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/api/app/services/transfers_service.py apps/api/tests/test_transfers_service.py
git commit -m "feat(api): add transfers service with ownership swap on accept"
```

---

## Task 14: Groups routes + wire main

**Files:** `apps/api/app/routes/groups.py`, `apps/api/app/main.py` (modify), `apps/api/tests/test_groups_routes.py`

- [ ] **Step 1: Test**

```python
# tests/test_groups_routes.py
from __future__ import annotations
import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={"email": "g@t.io", "username": "g_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "g_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def friend_auth(client):
    await client.post("/api/auth/register", json={"email": "fr@t.io", "username": "fr_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "fr_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_requires_auth(client):
    assert (await client.get("/api/groups")).status_code == 401


async def test_crud_roundtrip(client, auth):
    r = await client.post("/api/groups", headers=auth, json={"name": "g"})
    assert r.status_code == 201
    gid = r.json()["id"]
    assert (await client.get(f"/api/groups/{gid}", headers=auth)).status_code == 200
    assert (await client.patch(f"/api/groups/{gid}", headers=auth, json={"name": "new"})).json()["name"] == "new"
    assert (await client.delete(f"/api/groups/{gid}", headers=auth)).status_code == 204


async def test_add_and_remove_member(client, auth, friend_auth):
    gid = (await client.post("/api/groups", headers=auth, json={"name": "fam"})).json()["id"]
    r = await client.post(f"/api/groups/{gid}/members", headers=auth, json={"username": "fr_user"})
    assert r.status_code == 201
    member_user_id = r.json()["user_id"]
    assert (await client.delete(f"/api/groups/{gid}/members/{member_user_id}", headers=auth)).status_code == 204


async def test_add_member_unknown_404(client, auth):
    gid = (await client.post("/api/groups", headers=auth, json={"name": "g"})).json()["id"]
    r = await client.post(f"/api/groups/{gid}/members", headers=auth, json={"username": "ghost"})
    assert r.status_code == 404


async def test_add_duplicate_member_409(client, auth):
    gid = (await client.post("/api/groups", headers=auth, json={"name": "g"})).json()["id"]
    r = await client.post(f"/api/groups/{gid}/members", headers=auth, json={"username": "g_user"})
    assert r.status_code == 409


async def test_cross_owner_404(client, auth, friend_auth):
    gid = (await client.post("/api/groups", headers=auth, json={"name": "g"})).json()["id"]
    assert (await client.get(f"/api/groups/{gid}", headers=friend_auth)).status_code == 404
```

- [ ] **Step 2: Run — failing because routes not mounted**

- [ ] **Step 3: Implement**

Create `apps/api/app/routes/groups.py`:
```python
from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.group import (
    GroupAddMember,
    GroupCreate,
    GroupDetail,
    GroupMemberRead,
    GroupSummary,
    GroupUpdate,
)
from app.services import groups_service as svc

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("", response_model=list[GroupSummary])
async def list_groups(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.list_groups(session, user.id)


@router.post("", response_model=GroupSummary, status_code=status.HTTP_201_CREATED)
async def create_group(
    body: GroupCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.create_group(session, user.id, body)


@router.get("/{group_id}", response_model=GroupDetail)
async def get_group(
    group_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.get_group_detail(session, user.id, group_id)


@router.patch("/{group_id}", response_model=GroupSummary)
async def update_group(
    group_id: UUID,
    body: GroupUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.update_group(session, user.id, group_id, body)


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_group(
    group_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await svc.delete_group(session, user.id, group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{group_id}/members", response_model=GroupMemberRead, status_code=status.HTTP_201_CREATED
)
async def add_member(
    group_id: UUID,
    body: GroupAddMember,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.add_member_by_username(session, user.id, group_id, body)


@router.delete(
    "/{group_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def remove_member(
    group_id: UUID,
    user_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await svc.remove_member(session, user.id, group_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 4: Mount in main**

Modify `apps/api/app/main.py`:
- Change import line to:
  `from app.routes import auth, categories, groups, health, items, lists, locations, notifications, stats, tags, users`
- Add `app.include_router(groups.router)` after `app.include_router(lists.router)`.

- [ ] **Step 5: Run — expect PASS**

- [ ] **Step 6: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/api/app/routes/groups.py apps/api/app/main.py apps/api/tests/test_groups_routes.py
git commit -m "feat(api): add /api/groups router"
```

---

## Task 15: Loans routes

**Files:** `apps/api/app/routes/loans.py`, `apps/api/app/main.py` (modify), `apps/api/tests/test_loans_routes.py`

- [ ] **Step 1: Test**

```python
# tests/test_loans_routes.py
from __future__ import annotations
import pytest


@pytest.fixture
async def auth(client):
    await client.post("/api/auth/register", json={"email": "ln@t.io", "username": "ln_user", "password": "secret1234"})
    r = await client.post("/api/auth/login", json={"username": "ln_user", "password": "secret1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
async def item_id(client, auth):
    r = await client.post("/api/items", headers=auth, json={"name": "傘"})
    return r.json()["id"]


async def test_empty_history(client, auth, item_id):
    r = await client.get(f"/api/items/{item_id}/loans", headers=auth)
    assert r.status_code == 200
    assert r.json() == []


async def test_create_with_label(client, auth, item_id):
    r = await client.post(
        f"/api/items/{item_id}/loans", headers=auth, json={"borrower_label": "張三"},
    )
    assert r.status_code == 201
    assert r.json()["borrower_label"] == "張三"


async def test_active_uniqueness(client, auth, item_id):
    await client.post(f"/api/items/{item_id}/loans", headers=auth, json={"borrower_label": "a"})
    r = await client.post(f"/api/items/{item_id}/loans", headers=auth, json={"borrower_label": "b"})
    assert r.status_code == 409


async def test_return(client, auth, item_id):
    loan = (await client.post(f"/api/items/{item_id}/loans", headers=auth, json={"borrower_label": "a"})).json()
    r = await client.post(f"/api/items/{item_id}/loans/{loan['id']}/return", headers=auth)
    assert r.status_code == 200
    assert r.json()["returned_at"] is not None


async def test_delete(client, auth, item_id):
    loan = (await client.post(f"/api/items/{item_id}/loans", headers=auth, json={"borrower_label": "a"})).json()
    r = await client.delete(f"/api/items/{item_id}/loans/{loan['id']}", headers=auth)
    assert r.status_code == 204
```

- [ ] **Step 2: Run — fail with 404**

- [ ] **Step 3: Implement**

Create `apps/api/app/routes/loans.py`:
```python
from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.loan import LoanCreate, LoanRead
from app.services import loans_service as svc

router = APIRouter(prefix="/api/items/{item_id}/loans", tags=["loans"])


@router.get("", response_model=list[LoanRead])
async def list_loans(
    item_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.list_loans(session, user.id, item_id)


@router.post("", response_model=LoanRead, status_code=status.HTTP_201_CREATED)
async def create_loan(
    item_id: UUID,
    body: LoanCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.create_loan(session, user.id, item_id, body)


@router.post("/{loan_id}/return", response_model=LoanRead)
async def mark_returned(
    item_id: UUID,
    loan_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.mark_returned(session, user.id, item_id, loan_id)


@router.delete(
    "/{loan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_loan(
    item_id: UUID,
    loan_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await svc.delete_loan(session, user.id, item_id, loan_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 4: Mount in main**

Modify `apps/api/app/main.py`: change import line to include `loans` and add `app.include_router(loans.router)` after groups.

- [ ] **Step 5: Run — expect PASS**

- [ ] **Step 6: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/api/app/routes/loans.py apps/api/app/main.py apps/api/tests/test_loans_routes.py
git commit -m "feat(api): add /api/items/{id}/loans router"
```

---

## Task 16: Transfers routes

**Files:** `apps/api/app/routes/transfers.py`, `apps/api/app/main.py` (modify), `apps/api/tests/test_transfers_routes.py`

- [ ] **Step 1: Test**

```python
# tests/test_transfers_routes.py
from __future__ import annotations
import pytest


@pytest.fixture
async def two_auths(client):
    await client.post("/api/auth/register", json={"email": "a@t.io", "username": "a_user", "password": "secret1234"})
    await client.post("/api/auth/register", json={"email": "b@t.io", "username": "b_user", "password": "secret1234"})
    ra = await client.post("/api/auth/login", json={"username": "a_user", "password": "secret1234"})
    rb = await client.post("/api/auth/login", json={"username": "b_user", "password": "secret1234"})
    return (
        {"Authorization": f"Bearer {ra.json()['access_token']}"},
        {"Authorization": f"Bearer {rb.json()['access_token']}"},
    )


async def test_requires_auth(client):
    assert (await client.get("/api/transfers")).status_code == 401


async def test_create_and_accept(client, two_auths):
    a, b = two_auths
    item_id = (await client.post("/api/items", headers=a, json={"name": "X"})).json()["id"]
    t = (await client.post("/api/transfers", headers=a, json={"item_id": item_id, "to_username": "b_user"})).json()
    # b's notifications got one
    assert t["status"] == "pending"
    r = await client.post(f"/api/transfers/{t['id']}/accept", headers=b)
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"
    # now b owns the item
    got = (await client.get(f"/api/items/{item_id}", headers=b)).json()
    assert got["owner_username"] == "b_user"


async def test_self_transfer_422(client, two_auths):
    a, _ = two_auths
    item_id = (await client.post("/api/items", headers=a, json={"name": "X"})).json()["id"]
    r = await client.post("/api/transfers", headers=a, json={"item_id": item_id, "to_username": "a_user"})
    assert r.status_code == 422


async def test_non_owner_cannot_create(client, two_auths):
    a, b = two_auths
    item_id = (await client.post("/api/items", headers=a, json={"name": "X"})).json()["id"]
    r = await client.post("/api/transfers", headers=b, json={"item_id": item_id, "to_username": "a_user"})
    assert r.status_code == 404


async def test_reject(client, two_auths):
    a, b = two_auths
    item_id = (await client.post("/api/items", headers=a, json={"name": "X"})).json()["id"]
    t = (await client.post("/api/transfers", headers=a, json={"item_id": item_id, "to_username": "b_user"})).json()
    r = await client.post(f"/api/transfers/{t['id']}/reject", headers=b)
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


async def test_cancel(client, two_auths):
    a, b = two_auths
    item_id = (await client.post("/api/items", headers=a, json={"name": "X"})).json()["id"]
    t = (await client.post("/api/transfers", headers=a, json={"item_id": item_id, "to_username": "b_user"})).json()
    r = await client.post(f"/api/transfers/{t['id']}/cancel", headers=a)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


async def test_notification_emitted_to_recipient(client, two_auths):
    a, b = two_auths
    item_id = (await client.post("/api/items", headers=a, json={"name": "X"})).json()["id"]
    await client.post("/api/transfers", headers=a, json={"item_id": item_id, "to_username": "b_user"})
    notifs = (await client.get("/api/notifications", headers=b)).json()
    types = [n["type"] for n in notifs["items"]]
    assert "transfer.request" in types
```

- [ ] **Step 2: Run — fail with 404**

- [ ] **Step 3: Implement**

Create `apps/api/app/routes/transfers.py`:
```python
from __future__ import annotations
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.transfer import TransferCreate, TransferRead
from app.services import transfers_service as svc

router = APIRouter(prefix="/api/transfers", tags=["transfers"])


@router.get("", response_model=list[TransferRead])
async def list_transfers(
    direction: Literal["incoming", "outgoing", "both"] = "both",
    status_filter: Literal["pending", "resolved", "all"] = "all",
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.list_transfers(
        session, user.id, direction=direction, status_filter=status_filter
    )


@router.post("", response_model=TransferRead, status_code=201)
async def create_transfer(
    body: TransferCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.create_transfer(session, user.id, body)


@router.post("/{transfer_id}/accept", response_model=TransferRead)
async def accept(
    transfer_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.accept_transfer(session, user.id, transfer_id)


@router.post("/{transfer_id}/reject", response_model=TransferRead)
async def reject(
    transfer_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.reject_transfer(session, user.id, transfer_id)


@router.post("/{transfer_id}/cancel", response_model=TransferRead)
async def cancel(
    transfer_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await svc.cancel_transfer(session, user.id, transfer_id)
```

- [ ] **Step 4: Mount in main**

Update import line in `apps/api/app/main.py` to include `transfers`, add `app.include_router(transfers.router)` after loans.

- [ ] **Step 5: Run full API suite**

`cd apps/api && .venv/bin/python -m pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/api/app/routes/transfers.py apps/api/app/main.py apps/api/tests/test_transfers_routes.py
git commit -m "feat(api): add /api/transfers router"
```

---

## Task 17: Regenerate api-types

- [ ] **Step 1: Run**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration/apps/api && \
  .venv/bin/python scripts/export_openapi.py > ../../packages/api-types/openapi.json && \
  cd ../../packages/api-types && node generate.mjs
```
Expected: `wrote .../packages/api-types/src/index.ts`.

- [ ] **Step 2: Verify**

`grep -c "/api/groups\|/api/transfers\|/api/items/{item_id}/loans" packages/api-types/src/index.ts` → ≥ 10

- [ ] **Step 3: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add packages/api-types/openapi.json
git add -f packages/api-types/src/index.ts
git commit -m "chore(api-types): regenerate for collaboration endpoints"
```

---

## Task 18: Web API clients (groups + loans + transfers)

**Files:** `apps/web/lib/api/groups.ts`, `apps/web/lib/api/loans.ts`, `apps/web/lib/api/transfers.ts`

- [ ] **Step 1: Create groups client**

```typescript
// apps/web/lib/api/groups.ts
import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

export type GroupSummary = paths["/api/groups"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type GroupDetail = paths["/api/groups/{group_id}"]["get"]["responses"]["200"]["content"]["application/json"]
export type GroupMember = GroupDetail["members"][number]
export type GroupCreateBody = paths["/api/groups"]["post"]["requestBody"]["content"]["application/json"]
export type GroupUpdateBody = paths["/api/groups/{group_id}"]["patch"]["requestBody"]["content"]["application/json"]

export async function listGroups(token: string | null): Promise<GroupSummary[]> {
  return (await apiFetch("/groups", { accessToken: token })).json()
}
export async function createGroup(body: GroupCreateBody, token: string | null): Promise<GroupSummary> {
  return (await apiFetch("/groups", { method: "POST", accessToken: token, body: JSON.stringify(body) })).json()
}
export async function getGroup(id: string, token: string | null): Promise<GroupDetail> {
  return (await apiFetch(`/groups/${id}`, { accessToken: token })).json()
}
export async function updateGroup(id: string, body: GroupUpdateBody, token: string | null): Promise<GroupSummary> {
  return (await apiFetch(`/groups/${id}`, { method: "PATCH", accessToken: token, body: JSON.stringify(body) })).json()
}
export async function deleteGroup(id: string, token: string | null): Promise<void> {
  await apiFetch(`/groups/${id}`, { method: "DELETE", accessToken: token })
}
export async function addGroupMember(groupId: string, username: string, token: string | null): Promise<GroupMember> {
  return (await apiFetch(`/groups/${groupId}/members`, { method: "POST", accessToken: token, body: JSON.stringify({ username }) })).json()
}
export async function removeGroupMember(groupId: string, userId: string, token: string | null): Promise<void> {
  await apiFetch(`/groups/${groupId}/members/${userId}`, { method: "DELETE", accessToken: token })
}
```

- [ ] **Step 2: Create loans client**

```typescript
// apps/web/lib/api/loans.ts
import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

export type Loan = paths["/api/items/{item_id}/loans"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type LoanCreateBody = paths["/api/items/{item_id}/loans"]["post"]["requestBody"]["content"]["application/json"]

export async function listLoans(itemId: string, token: string | null): Promise<Loan[]> {
  return (await apiFetch(`/items/${itemId}/loans`, { accessToken: token })).json()
}
export async function createLoan(itemId: string, body: LoanCreateBody, token: string | null): Promise<Loan> {
  return (await apiFetch(`/items/${itemId}/loans`, { method: "POST", accessToken: token, body: JSON.stringify(body) })).json()
}
export async function returnLoan(itemId: string, loanId: string, token: string | null): Promise<Loan> {
  return (await apiFetch(`/items/${itemId}/loans/${loanId}/return`, { method: "POST", accessToken: token })).json()
}
export async function deleteLoan(itemId: string, loanId: string, token: string | null): Promise<void> {
  await apiFetch(`/items/${itemId}/loans/${loanId}`, { method: "DELETE", accessToken: token })
}
```

- [ ] **Step 3: Create transfers client**

```typescript
// apps/web/lib/api/transfers.ts
import type { paths } from "@ims/api-types"
import { apiFetch } from "./client"

export type Transfer = paths["/api/transfers"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type TransferCreateBody = paths["/api/transfers"]["post"]["requestBody"]["content"]["application/json"]

export async function listTransfers(
  params: { direction?: "incoming" | "outgoing" | "both"; status_filter?: "pending" | "resolved" | "all" },
  token: string | null,
): Promise<Transfer[]> {
  const q = new URLSearchParams()
  if (params.direction) q.set("direction", params.direction)
  if (params.status_filter) q.set("status_filter", params.status_filter)
  return (await apiFetch(`/transfers${q.size ? `?${q}` : ""}`, { accessToken: token })).json()
}
export async function createTransfer(body: TransferCreateBody, token: string | null): Promise<Transfer> {
  return (await apiFetch("/transfers", { method: "POST", accessToken: token, body: JSON.stringify(body) })).json()
}
export async function acceptTransfer(id: string, token: string | null): Promise<Transfer> {
  return (await apiFetch(`/transfers/${id}/accept`, { method: "POST", accessToken: token })).json()
}
export async function rejectTransfer(id: string, token: string | null): Promise<Transfer> {
  return (await apiFetch(`/transfers/${id}/reject`, { method: "POST", accessToken: token })).json()
}
export async function cancelTransfer(id: string, token: string | null): Promise<Transfer> {
  return (await apiFetch(`/transfers/${id}/cancel`, { method: "POST", accessToken: token })).json()
}
```

- [ ] **Step 4: Typecheck**

`cd apps/web && pnpm typecheck` → 0 errors.

- [ ] **Step 5: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/web/lib/api/groups.ts apps/web/lib/api/loans.ts apps/web/lib/api/transfers.ts
git commit -m "feat(web): add typed clients for groups/loans/transfers"
```

---

## Task 19: React Query hooks

**Files:** `apps/web/lib/hooks/use-groups.ts`, `apps/web/lib/hooks/use-loans.ts`, `apps/web/lib/hooks/use-transfers.ts`

- [ ] **Step 1: groups hook**

```typescript
// apps/web/lib/hooks/use-groups.ts
"use client"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import * as api from "@/lib/api/groups"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useGroups() {
  const token = useAccessToken()
  return useQuery({ queryKey: ["groups", "index"], queryFn: () => api.listGroups(token), enabled: token !== null, staleTime: 30_000 })
}
export function useGroup(id: string | null) {
  const token = useAccessToken()
  return useQuery({ queryKey: ["groups", "detail", id], queryFn: () => api.getGroup(id as string, token), enabled: token !== null && id !== null, staleTime: 30_000 })
}
export function useCreateGroup() {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (body: api.GroupCreateBody) => api.createGroup(body, token), onSuccess: () => qc.invalidateQueries({ queryKey: ["groups"] }) })
}
export function useUpdateGroup(id: string) {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (body: api.GroupUpdateBody) => api.updateGroup(id, body, token), onSuccess: () => qc.invalidateQueries({ queryKey: ["groups"] }) })
}
export function useDeleteGroup() {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (id: string) => api.deleteGroup(id, token), onSuccess: () => qc.invalidateQueries({ queryKey: ["groups"] }) })
}
export function useAddGroupMember(groupId: string) {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (username: string) => api.addGroupMember(groupId, username, token), onSuccess: () => qc.invalidateQueries({ queryKey: ["groups"] }) })
}
export function useRemoveGroupMember(groupId: string) {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (userId: string) => api.removeGroupMember(groupId, userId, token), onSuccess: () => qc.invalidateQueries({ queryKey: ["groups"] }) })
}
```

- [ ] **Step 2: loans hook**

```typescript
// apps/web/lib/hooks/use-loans.ts
"use client"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import * as api from "@/lib/api/loans"
import { useAccessToken } from "@/lib/auth/use-auth"

export function useLoans(itemId: string) {
  const token = useAccessToken()
  return useQuery({ queryKey: ["loans", itemId], queryFn: () => api.listLoans(itemId, token), enabled: token !== null, staleTime: 30_000 })
}
export function useCreateLoan(itemId: string) {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (body: api.LoanCreateBody) => api.createLoan(itemId, body, token), onSuccess: () => qc.invalidateQueries({ queryKey: ["loans", itemId] }) })
}
export function useReturnLoan(itemId: string) {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (loanId: string) => api.returnLoan(itemId, loanId, token), onSuccess: () => qc.invalidateQueries({ queryKey: ["loans", itemId] }) })
}
export function useDeleteLoan(itemId: string) {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (loanId: string) => api.deleteLoan(itemId, loanId, token), onSuccess: () => qc.invalidateQueries({ queryKey: ["loans", itemId] }) })
}
```

- [ ] **Step 3: transfers hook**

```typescript
// apps/web/lib/hooks/use-transfers.ts
"use client"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import * as api from "@/lib/api/transfers"
import { useAccessToken } from "@/lib/auth/use-auth"

type ListParams = { direction?: "incoming" | "outgoing" | "both"; status_filter?: "pending" | "resolved" | "all" }

export function useTransfers(params: ListParams = {}) {
  const token = useAccessToken()
  return useQuery({ queryKey: ["transfers", "index", params], queryFn: () => api.listTransfers(params, token), enabled: token !== null, staleTime: 30_000 })
}
function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["transfers"] })
  qc.invalidateQueries({ queryKey: ["items"] })
  qc.invalidateQueries({ queryKey: ["notifications"] })
}
export function useCreateTransfer() {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (body: api.TransferCreateBody) => api.createTransfer(body, token), onSuccess: () => invalidateAll(qc) })
}
export function useAcceptTransfer() {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (id: string) => api.acceptTransfer(id, token), onSuccess: () => invalidateAll(qc) })
}
export function useRejectTransfer() {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (id: string) => api.rejectTransfer(id, token), onSuccess: () => invalidateAll(qc) })
}
export function useCancelTransfer() {
  const token = useAccessToken(); const qc = useQueryClient()
  return useMutation({ mutationFn: (id: string) => api.cancelTransfer(id, token), onSuccess: () => invalidateAll(qc) })
}
```

- [ ] **Step 4: Typecheck**

- [ ] **Step 5: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/web/lib/hooks/use-groups.ts apps/web/lib/hooks/use-loans.ts apps/web/lib/hooks/use-transfers.ts
git commit -m "feat(web): add hooks for groups/loans/transfers"
```

---

## Task 20: i18n messages

**Files:** `apps/web/messages/zh-TW.json`, `apps/web/messages/en.json`

- [ ] **Step 1: Add `nav.collab` and full `collab` block to zh-TW.json**

Before final `}`, add sibling `collab` object:
```json
  "collab": {
    "title": "協作",
    "tabs": {
      "groups": "群組",
      "transfers": "轉移"
    },
    "groups": {
      "new": "新增群組",
      "empty": "尚無群組",
      "memberCount": "{count} 人",
      "youAreOwner": "擁有者",
      "detail": {
        "addMember": "加入成員",
        "addMemberUsernamePlaceholder": "對方使用者名稱",
        "removeMember": "移除",
        "confirmRemove": "確定移除此成員？",
        "delete": "刪除群組",
        "confirmDelete": "確定刪除此群組？所有成員將失去彼此物品的可見性。",
        "leave": "離開群組"
      }
    },
    "transfers": {
      "tabs": {
        "incoming": "收到",
        "outgoing": "發出",
        "pending": "等待中",
        "history": "歷史"
      },
      "actions": {
        "accept": "接受",
        "reject": "拒絕",
        "cancel": "取消"
      },
      "status": {
        "pending": "等待中",
        "accepted": "已接受",
        "rejected": "已拒絕",
        "cancelled": "已取消"
      },
      "empty": "尚無轉移請求"
    },
    "loan": {
      "card": {
        "title": "借出紀錄",
        "active": "借出中",
        "history": "歷史紀錄",
        "expectedReturn": "預計歸還：{date}",
        "borrowerUser": "{username}（站內使用者）"
      },
      "actions": {
        "new": "新增借用",
        "return": "歸還",
        "delete": "刪除紀錄"
      },
      "new": {
        "title": "新增借用",
        "modeUser": "站內使用者",
        "modeLabel": "自訂名稱",
        "borrowerUser": "使用者名稱",
        "borrowerLabel": "借用者（自訂）",
        "expectedReturn": "預計歸還日",
        "notes": "備註",
        "create": "建立"
      }
    },
    "transfer": {
      "actions": {
        "new": "轉移所有權"
      },
      "new": {
        "title": "轉移所有權",
        "toUsername": "接收者使用者名稱",
        "message": "附註訊息（選填）",
        "create": "送出請求",
        "awaiting": "等待 {username} 接受"
      }
    },
    "readonly": {
      "sharedBy": "由 {username} 分享（唯讀）"
    }
  }
```

Also add `"nav.collab": "協作"` inside the `nav` object.

- [ ] **Step 2: Add parallel block to en.json** (translate all keys above). Keep keys identical; translate values to English.

- [ ] **Step 3: Typecheck**

`cd apps/web && pnpm typecheck` → 0 errors.

- [ ] **Step 4: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/web/messages/zh-TW.json apps/web/messages/en.json
git commit -m "feat(web): add i18n strings for collaboration"
```

---

## Task 21: Nav + collaboration hub page

**Files:** `apps/web/components/shell/nav-items.ts` (modify), `apps/web/app/(app)/collaboration/page.tsx`, `apps/web/components/collaboration/group-card.tsx`, `apps/web/components/collaboration/new-group-dialog.tsx`, `apps/web/components/collaboration/transfer-card.tsx`

- [ ] **Step 1: Nav**

Replace `apps/web/components/shell/nav-items.ts`:
```typescript
import type { Route } from "next"

export interface NavItem {
  key: "dashboard" | "items" | "statistics" | "notifications" | "lists" | "collab" | "settings"
  href: Route
  labelKey: string
}

export const NAV_ITEMS: readonly NavItem[] = [
  { key: "dashboard", href: "/dashboard", labelKey: "nav.dashboard" },
  { key: "items", href: "/items", labelKey: "nav.items" },
  { key: "statistics", href: "/statistics", labelKey: "nav.statistics" },
  { key: "notifications", href: "/notifications", labelKey: "nav.notifications" },
  { key: "lists", href: "/lists", labelKey: "nav.lists" },
  { key: "collab", href: "/collaboration", labelKey: "nav.collab" },
  { key: "settings", href: "/settings", labelKey: "nav.settings" },
]
```

- [ ] **Step 2: GroupCard component**

Create `apps/web/components/collaboration/group-card.tsx`:
```tsx
"use client"
import Link from "next/link"
import { useTranslations } from "next-intl"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { GroupSummary } from "@/lib/api/groups"

export function GroupCard({ row }: { row: GroupSummary }) {
  const t = useTranslations()
  return (
    <Link href={`/collaboration/groups/${row.id}` as never} className="block no-underline">
      <Card className="transition-shadow hover:shadow-md">
        <CardHeader className="flex flex-row items-start justify-between gap-2 pb-2">
          <CardTitle className="text-base">{row.name}</CardTitle>
          {row.is_owner ? <Badge variant="secondary">{t("collab.groups.youAreOwner")}</Badge> : null}
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {t("collab.groups.memberCount", { count: row.member_count })} · {row.owner_username}
        </CardContent>
      </Card>
    </Link>
  )
}
```

- [ ] **Step 3: NewGroupDialog component**

Create `apps/web/components/collaboration/new-group-dialog.tsx`:
```tsx
"use client"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { useTranslations } from "next-intl"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useCreateGroup } from "@/lib/hooks/use-groups"

export function NewGroupDialog() {
  const t = useTranslations()
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const create = useCreateGroup()
  const submit = async () => {
    if (!name.trim()) return
    const g = await create.mutateAsync({ name: name.trim() })
    setOpen(false); setName("")
    router.push(`/collaboration/groups/${g.id}` as never)
  }
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button size="sm">{t("collab.groups.new")}</Button></DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>{t("collab.groups.new")}</DialogTitle></DialogHeader>
        <div className="space-y-2">
          <Label>{t("collab.groups.new")}</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>{t("lists.new.cancel")}</Button>
          <Button onClick={submit} disabled={!name.trim() || create.isPending}>{t("lists.new.create")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

- [ ] **Step 4: TransferCard component**

Create `apps/web/components/collaboration/transfer-card.tsx`:
```tsx
"use client"
import { useTranslations } from "next-intl"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useAcceptTransfer, useCancelTransfer, useRejectTransfer } from "@/lib/hooks/use-transfers"
import type { Transfer } from "@/lib/api/transfers"

export function TransferCard({ row, currentUserId }: { row: Transfer; currentUserId: string }) {
  const t = useTranslations()
  const accept = useAcceptTransfer()
  const reject = useRejectTransfer()
  const cancel = useCancelTransfer()
  const isIncoming = row.to_user_id === currentUserId
  const peer = isIncoming ? row.from_username : row.to_username
  const isPending = row.status === "pending"

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between pb-2">
        <CardTitle className="text-base">{row.item_name}</CardTitle>
        <Badge variant={isPending ? "default" : "secondary"}>{t(`collab.transfers.status.${row.status}`)}</Badge>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">
        <p>{isIncoming ? `${peer} → 你` : `你 → ${peer}`}</p>
        {row.message ? <p className="mt-1">{row.message}</p> : null}
      </CardContent>
      {isPending ? (
        <CardFooter className="gap-2">
          {isIncoming ? (
            <>
              <Button size="sm" onClick={() => accept.mutate(row.id)} disabled={accept.isPending}>
                {t("collab.transfers.actions.accept")}
              </Button>
              <Button size="sm" variant="outline" onClick={() => reject.mutate(row.id)} disabled={reject.isPending}>
                {t("collab.transfers.actions.reject")}
              </Button>
            </>
          ) : (
            <Button size="sm" variant="outline" onClick={() => cancel.mutate(row.id)} disabled={cancel.isPending}>
              {t("collab.transfers.actions.cancel")}
            </Button>
          )}
        </CardFooter>
      ) : null}
    </Card>
  )
}
```

- [ ] **Step 5: Collaboration page**

Create `apps/web/app/(app)/collaboration/page.tsx`:
```tsx
"use client"
import { useSearchParams } from "next/navigation"
import { useState, useEffect } from "react"
import { useTranslations } from "next-intl"
import { GroupCard } from "@/components/collaboration/group-card"
import { NewGroupDialog } from "@/components/collaboration/new-group-dialog"
import { TransferCard } from "@/components/collaboration/transfer-card"
import { Breadcrumb, BreadcrumbItem, BreadcrumbList, BreadcrumbPage } from "@/components/ui/breadcrumb"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useGroups } from "@/lib/hooks/use-groups"
import { useTransfers } from "@/lib/hooks/use-transfers"
import { useAuthStore } from "@/lib/auth/auth-store"

export default function CollaborationPage() {
  const t = useTranslations()
  const sp = useSearchParams()
  const [tab, setTab] = useState<"groups" | "transfers">(() => (sp.get("tab") === "transfers" ? "transfers" : "groups"))
  useEffect(() => {
    const q = sp.get("tab")
    if (q === "transfers" || q === "groups") setTab(q)
  }, [sp])
  const groups = useGroups()
  const transfers = useTransfers()
  const userId = useAuthStore((s) => s.user?.id ?? "")

  return (
    <section className="space-y-6 p-6">
      <Breadcrumb><BreadcrumbList><BreadcrumbItem><BreadcrumbPage>{t("collab.title")}</BreadcrumbPage></BreadcrumbItem></BreadcrumbList></Breadcrumb>
      <h1 className="text-2xl font-semibold">{t("collab.title")}</h1>
      <Tabs value={tab} onValueChange={(v) => setTab(v as "groups" | "transfers")}>
        <TabsList>
          <TabsTrigger value="groups">{t("collab.tabs.groups")}</TabsTrigger>
          <TabsTrigger value="transfers">{t("collab.tabs.transfers")}</TabsTrigger>
        </TabsList>
        <TabsContent value="groups" className="space-y-4">
          <div className="flex justify-end"><NewGroupDialog /></div>
          {(groups.data?.length ?? 0) === 0 ? (
            <p className="text-sm text-muted-foreground">{t("collab.groups.empty")}</p>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {groups.data?.map((g) => <GroupCard key={g.id} row={g} />)}
            </div>
          )}
        </TabsContent>
        <TabsContent value="transfers" className="space-y-4">
          {(transfers.data?.length ?? 0) === 0 ? (
            <p className="text-sm text-muted-foreground">{t("collab.transfers.empty")}</p>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {transfers.data?.map((r) => <TransferCard key={r.id} row={r} currentUserId={userId} />)}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </section>
  )
}
```

- [ ] **Step 6: Typecheck**

`cd apps/web && pnpm typecheck` → 0 errors.

- [ ] **Step 7: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/web/components/shell/nav-items.ts apps/web/components/collaboration/group-card.tsx apps/web/components/collaboration/new-group-dialog.tsx apps/web/components/collaboration/transfer-card.tsx "apps/web/app/(app)/collaboration/page.tsx"
git commit -m "feat(web): add collaboration hub page + group & transfer cards"
```

---

## Task 22: Group detail page

**Files:** `apps/web/app/(app)/collaboration/groups/[id]/page.tsx`, `apps/web/components/collaboration/add-member-dialog.tsx`

- [ ] **Step 1: AddMemberDialog**

Create `apps/web/components/collaboration/add-member-dialog.tsx`:
```tsx
"use client"
import { useState } from "react"
import { useTranslations } from "next-intl"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useAddGroupMember } from "@/lib/hooks/use-groups"

export function AddMemberDialog({ groupId }: { groupId: string }) {
  const t = useTranslations()
  const [open, setOpen] = useState(false)
  const [username, setUsername] = useState("")
  const [error, setError] = useState<string | null>(null)
  const add = useAddGroupMember(groupId)
  const submit = async () => {
    setError(null)
    try {
      await add.mutateAsync(username.trim())
      setOpen(false); setUsername("")
    } catch (e) {
      setError(t("collab.groups.detail.addMember"))
    }
  }
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button size="sm">{t("collab.groups.detail.addMember")}</Button></DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>{t("collab.groups.detail.addMember")}</DialogTitle></DialogHeader>
        <div className="space-y-2">
          <Label>{t("collab.groups.detail.addMemberUsernamePlaceholder")}</Label>
          <Input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>{t("lists.new.cancel")}</Button>
          <Button onClick={submit} disabled={!username.trim() || add.isPending}>{t("lists.new.create")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

- [ ] **Step 2: Detail page**

Create `apps/web/app/(app)/collaboration/groups/[id]/page.tsx`:
```tsx
"use client"
import { useParams, useRouter } from "next/navigation"
import { useTranslations } from "next-intl"
import { AddMemberDialog } from "@/components/collaboration/add-member-dialog"
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog"
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useDeleteGroup, useGroup, useRemoveGroupMember } from "@/lib/hooks/use-groups"
import { useAuthStore } from "@/lib/auth/auth-store"

export default function GroupDetailPage() {
  const t = useTranslations()
  const params = useParams()
  const router = useRouter()
  const id = String(params.id)
  const query = useGroup(id)
  const remove = useRemoveGroupMember(id)
  const del = useDeleteGroup()
  const currentUserId = useAuthStore((s) => s.user?.id ?? "")

  if (query.isLoading) return <section className="p-6"><Skeleton className="h-8 w-60" /></section>
  if (!query.data) return <section className="p-6">Not found.</section>
  const g = query.data

  return (
    <section className="space-y-6 p-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem><BreadcrumbLink href="/collaboration">{t("collab.title")}</BreadcrumbLink></BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem><BreadcrumbPage>{g.name}</BreadcrumbPage></BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
      <div className="flex items-start justify-between">
        <h1 className="text-2xl font-semibold">{g.name}</h1>
        {g.is_owner ? (
          <AlertDialog>
            <AlertDialogTrigger asChild><Button variant="outline" size="sm">{t("collab.groups.detail.delete")}</Button></AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>{t("collab.groups.detail.delete")}</AlertDialogTitle>
                <AlertDialogDescription>{t("collab.groups.detail.confirmDelete")}</AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>{t("lists.new.cancel")}</AlertDialogCancel>
                <AlertDialogAction onClick={async () => { await del.mutateAsync(id); router.push("/collaboration") }}>{t("collab.groups.detail.delete")}</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        ) : (
          <Button variant="outline" size="sm" onClick={async () => { await remove.mutateAsync(currentUserId); router.push("/collaboration") }}>
            {t("collab.groups.detail.leave")}
          </Button>
        )}
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">{t("collab.groups.memberCount", { count: g.member_count })}</h2>
          {g.is_owner ? <AddMemberDialog groupId={id} /> : null}
        </div>
        <ul className="divide-y rounded border">
          {g.members.map((m) => (
            <li key={m.user_id} className="flex items-center justify-between p-3">
              <div>
                <span className="font-medium">{m.username}</span>
                {m.user_id === g.owner_id ? <span className="ml-2 text-xs text-muted-foreground">({t("collab.groups.youAreOwner")})</span> : null}
              </div>
              {g.is_owner && m.user_id !== g.owner_id ? (
                <Button variant="ghost" size="sm" onClick={() => remove.mutate(m.user_id)}>{t("collab.groups.detail.removeMember")}</Button>
              ) : null}
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
```

- [ ] **Step 3: Typecheck + commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
cd apps/web && pnpm typecheck && cd ../..
git add apps/web/components/collaboration/add-member-dialog.tsx "apps/web/app/(app)/collaboration/groups/[id]/page.tsx"
git commit -m "feat(web): add group detail page"
```

---

## Task 23: Loan + Transfer integration in item detail page

**Files:** `apps/web/components/collaboration/loan-card.tsx`, `apps/web/components/collaboration/new-loan-dialog.tsx`, `apps/web/components/collaboration/new-transfer-dialog.tsx`, `apps/web/components/collaboration/readonly-badge.tsx`, `apps/web/app/(app)/items/[id]/page.tsx` (modify)

- [ ] **Step 1: ReadonlyBadge**

```tsx
// apps/web/components/collaboration/readonly-badge.tsx
"use client"
import { Lock } from "lucide-react"
import { useTranslations } from "next-intl"

export function ReadonlyBadge({ ownerUsername }: { ownerUsername: string }) {
  const t = useTranslations()
  return (
    <div className="flex items-center gap-2 rounded border bg-muted px-3 py-1.5 text-sm text-muted-foreground">
      <Lock className="h-3.5 w-3.5" />
      {t("collab.readonly.sharedBy", { username: ownerUsername })}
    </div>
  )
}
```

- [ ] **Step 2: LoanCard**

```tsx
// apps/web/components/collaboration/loan-card.tsx
"use client"
import { useTranslations } from "next-intl"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { NewLoanDialog } from "@/components/collaboration/new-loan-dialog"
import { useDeleteLoan, useLoans, useReturnLoan } from "@/lib/hooks/use-loans"

export function LoanCard({ itemId }: { itemId: string }) {
  const t = useTranslations()
  const { data } = useLoans(itemId)
  const ret = useReturnLoan(itemId)
  const del = useDeleteLoan(itemId)
  const all = data ?? []
  const active = all.find((l) => l.returned_at === null) ?? null
  const history = all.filter((l) => l.returned_at !== null)

  return (
    <Card>
      <CardHeader><CardTitle className="text-base">{t("collab.loan.card.title")}</CardTitle></CardHeader>
      <CardContent className="space-y-2 text-sm">
        {active ? (
          <div>
            <p className="font-medium">
              {active.borrower_username ? t("collab.loan.card.borrowerUser", { username: active.borrower_username }) : active.borrower_label}
            </p>
            {active.expected_return ? <p className="text-muted-foreground">{t("collab.loan.card.expectedReturn", { date: active.expected_return })}</p> : null}
            {active.notes ? <p className="text-muted-foreground">{active.notes}</p> : null}
          </div>
        ) : (
          <p className="text-muted-foreground">—</p>
        )}
        {history.length > 0 ? (
          <details>
            <summary className="cursor-pointer text-muted-foreground">{t("collab.loan.card.history")} ({history.length})</summary>
            <ul className="mt-2 space-y-1">
              {history.map((l) => (
                <li key={l.id} className="flex items-center justify-between">
                  <span>{l.borrower_username ?? l.borrower_label}</span>
                  <Button size="sm" variant="ghost" onClick={() => del.mutate(l.id)}>{t("collab.loan.actions.delete")}</Button>
                </li>
              ))}
            </ul>
          </details>
        ) : null}
      </CardContent>
      <CardFooter className="gap-2">
        {active ? (
          <Button size="sm" onClick={() => ret.mutate(active.id)} disabled={ret.isPending}>
            {t("collab.loan.actions.return")}
          </Button>
        ) : (
          <NewLoanDialog itemId={itemId} />
        )}
      </CardFooter>
    </Card>
  )
}
```

- [ ] **Step 3: NewLoanDialog**

```tsx
// apps/web/components/collaboration/new-loan-dialog.tsx
"use client"
import { useState } from "react"
import { useTranslations } from "next-intl"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useCreateLoan } from "@/lib/hooks/use-loans"

export function NewLoanDialog({ itemId }: { itemId: string }) {
  const t = useTranslations()
  const [open, setOpen] = useState(false)
  const [mode, setMode] = useState<"user" | "label">("label")
  const [user, setUser] = useState("")
  const [label, setLabel] = useState("")
  const [date, setDate] = useState("")
  const [notes, setNotes] = useState("")
  const create = useCreateLoan(itemId)

  const submit = async () => {
    const body: Parameters<typeof create.mutateAsync>[0] = {
      expected_return: date || undefined,
      notes: notes || undefined,
    } as never
    if (mode === "user" && user.trim()) (body as { borrower_username?: string }).borrower_username = user.trim()
    if (mode === "label" && label.trim()) (body as { borrower_label?: string }).borrower_label = label.trim()
    await create.mutateAsync(body)
    setOpen(false); setUser(""); setLabel(""); setDate(""); setNotes("")
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button size="sm">{t("collab.loan.actions.new")}</Button></DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>{t("collab.loan.new.title")}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="flex gap-2">
            <Button size="sm" variant={mode === "user" ? "default" : "outline"} onClick={() => setMode("user")}>
              {t("collab.loan.new.modeUser")}
            </Button>
            <Button size="sm" variant={mode === "label" ? "default" : "outline"} onClick={() => setMode("label")}>
              {t("collab.loan.new.modeLabel")}
            </Button>
          </div>
          {mode === "user" ? (
            <div className="space-y-1">
              <Label>{t("collab.loan.new.borrowerUser")}</Label>
              <Input value={user} onChange={(e) => setUser(e.target.value)} />
            </div>
          ) : (
            <div className="space-y-1">
              <Label>{t("collab.loan.new.borrowerLabel")}</Label>
              <Input value={label} onChange={(e) => setLabel(e.target.value)} />
            </div>
          )}
          <div className="space-y-1">
            <Label>{t("collab.loan.new.expectedReturn")}</Label>
            <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <div className="space-y-1">
            <Label>{t("collab.loan.new.notes")}</Label>
            <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>{t("lists.new.cancel")}</Button>
          <Button onClick={submit} disabled={create.isPending || (mode === "user" ? !user.trim() : !label.trim())}>
            {t("collab.loan.new.create")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

- [ ] **Step 4: NewTransferDialog**

```tsx
// apps/web/components/collaboration/new-transfer-dialog.tsx
"use client"
import { useState } from "react"
import { useTranslations } from "next-intl"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useCreateTransfer } from "@/lib/hooks/use-transfers"

export function NewTransferDialog({ itemId }: { itemId: string }) {
  const t = useTranslations()
  const [open, setOpen] = useState(false)
  const [to, setTo] = useState("")
  const [msg, setMsg] = useState("")
  const create = useCreateTransfer()
  const submit = async () => {
    await create.mutateAsync({ item_id: itemId, to_username: to.trim(), message: msg.trim() || undefined })
    setOpen(false); setTo(""); setMsg("")
  }
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button size="sm" variant="outline">{t("collab.transfer.actions.new")}</Button></DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle>{t("collab.transfer.new.title")}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label>{t("collab.transfer.new.toUsername")}</Label>
            <Input value={to} onChange={(e) => setTo(e.target.value)} autoFocus />
          </div>
          <div className="space-y-1">
            <Label>{t("collab.transfer.new.message")}</Label>
            <Textarea value={msg} onChange={(e) => setMsg(e.target.value)} rows={2} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>{t("lists.new.cancel")}</Button>
          <Button onClick={submit} disabled={!to.trim() || create.isPending}>{t("collab.transfer.new.create")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

- [ ] **Step 5: Integrate into item detail page**

Modify `apps/web/app/(app)/items/[id]/page.tsx` to:
- Read current user id from `useAuthStore((s) => s.user?.id ?? "")`
- Compute `isOwner = item.owner_id === currentUserId`
- Render `<ReadonlyBadge ownerUsername={item.owner_username} />` when `!isOwner`
- Hide edit/delete buttons when `!isOwner`
- Render `<LoanCard itemId={item.id} />` and `<NewTransferDialog itemId={item.id} />` only when `isOwner`

The exact patch depends on the existing page; add imports at top:
```tsx
import { LoanCard } from "@/components/collaboration/loan-card"
import { NewTransferDialog } from "@/components/collaboration/new-transfer-dialog"
import { ReadonlyBadge } from "@/components/collaboration/readonly-badge"
import { useAuthStore } from "@/lib/auth/auth-store"
```

Inside the component:
```tsx
const currentUserId = useAuthStore((s) => s.user?.id ?? "")
const isOwner = item.owner_id === currentUserId
```

Replace the action-bar JSX: when `!isOwner`, render only `<ReadonlyBadge>`. When `isOwner`, keep existing Edit/Delete plus `<NewTransferDialog itemId={item.id} />` next to them. Below the item body, when `isOwner`, add `<LoanCard itemId={item.id} />`.

- [ ] **Step 6: Typecheck**

`cd apps/web && pnpm typecheck` → 0 errors.

- [ ] **Step 7: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/web/components/collaboration/readonly-badge.tsx apps/web/components/collaboration/loan-card.tsx apps/web/components/collaboration/new-loan-dialog.tsx apps/web/components/collaboration/new-transfer-dialog.tsx "apps/web/app/(app)/items/[id]/page.tsx"
git commit -m "feat(web): integrate loan + transfer + readonly UI into item detail"
```

---

## Task 24: E2E tests

**Files:** `apps/web/tests/collaboration.spec.ts`

- [ ] **Step 1: Write the spec**

```typescript
// apps/web/tests/collaboration.spec.ts
import { expect, test } from "@playwright/test"

const unique = () => Date.now().toString()

async function register(request: import("@playwright/test").APIRequestContext, username: string) {
  await request.post("/api/auth/register", { data: { email: `${username}@t.io`, username, password: "secret1234" } })
}

async function loginUi(page: import("@playwright/test").Page, username: string) {
  await page.goto("/login")
  await page.getByLabel("使用者名稱").fill(username)
  await page.getByLabel("密碼").fill("secret1234")
  await page.getByRole("button", { name: /登入/ }).click()
  await page.waitForURL("**/dashboard")
}

test("group + loan + transfer end-to-end", async ({ browser, request }) => {
  const alice = `alice_${unique()}`
  const bob = `bob_${unique()}`
  await register(request, alice)
  await register(request, bob)

  // Alice: create item + group + add bob
  const alicePage = await (await browser.newContext()).newPage()
  await loginUi(alicePage, alice)
  const loginA = await request.post("/api/auth/login", { data: { username: alice, password: "secret1234" } })
  const tokenA = (await loginA.json()).access_token
  const itemA = await request.post("/api/items", { headers: { Authorization: `Bearer ${tokenA}` }, data: { name: "Alice 的傘" } })
  const itemId = (await itemA.json()).id

  await alicePage.goto("/collaboration")
  await alicePage.getByRole("button", { name: "新增群組" }).click()
  await alicePage.getByRole("textbox").first().fill("家人")
  await alicePage.getByRole("button", { name: "建立" }).click()
  await alicePage.waitForURL(/\/collaboration\/groups\//)
  await alicePage.getByRole("button", { name: "加入成員" }).click()
  await alicePage.getByRole("textbox").fill(bob)
  await alicePage.getByRole("button", { name: "建立" }).click()

  // Bob: logs in, sees Alice's item read-only
  const bobPage = await (await browser.newContext()).newPage()
  await loginUi(bobPage, bob)
  await bobPage.goto("/items")
  await expect(bobPage.getByText("Alice 的傘")).toBeVisible()
  await bobPage.getByText("Alice 的傘").click()
  await expect(bobPage.getByText(/由 .+ 分享/)).toBeVisible()

  // Alice: create transfer to Bob
  await alicePage.goto(`/items/${itemId}`)
  await alicePage.getByRole("button", { name: "轉移所有權" }).click()
  await alicePage.getByLabel("接收者使用者名稱").fill(bob)
  await alicePage.getByRole("button", { name: "送出請求" }).click()

  // Bob: accept transfer
  await bobPage.goto("/collaboration?tab=transfers")
  await bobPage.getByRole("button", { name: "接受" }).click()
  await expect(bobPage.getByText(/已接受/)).toBeVisible()

  // Bob: now owner
  await bobPage.goto(`/items/${itemId}`)
  await expect(bobPage.getByText(/由 .+ 分享/)).toHaveCount(0)
})
```

- [ ] **Step 2: Commit (run E2E separately)**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add apps/web/tests/collaboration.spec.ts
git commit -m "test(e2e): add collaboration end-to-end flow"
```

---

## Task 25: Mark roadmap done

**Files:** `docs/v2-roadmap.md`

- [ ] **Step 1: Flip #7 row**

Change
```markdown
| 7 | 協作（群組、借用、轉移） | ⏳ 未開始 |
```
to
```markdown
| 7 | 協作（群組、借用、轉移） | ✅ 完成 |
```

- [ ] **Step 2: Commit**

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
git add docs/v2-roadmap.md
git commit -m "docs: mark #7 collaboration subproject complete"
```

---

## Final Verification

```bash
cd /Users/guantou/Desktop/Item-Manage-System/.claude/worktrees/collaboration
cd apps/api && .venv/bin/python -m pytest -q && cd ../..
cd apps/web && pnpm typecheck && pnpm test && pnpm build && cd ../..
```

Expected: API 223 + ~60 new ≈ 283 all pass; web typecheck clean; vitest 57 unchanged (no new vitest suites — components tested only via E2E); build includes `/collaboration`, `/collaboration/groups/[id]`.

E2E (manual): `pnpm --filter @ims/web e2e`.
