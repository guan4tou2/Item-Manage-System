from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.list import (
    ListCreate,
    ListDetail,
    ListEntryCreate,
    ListEntryUpdate,
    ListSummary,
    ListUpdate,
    ReorderRequest,
)


def test_list_create_accepts_valid_kind():
    body = ListCreate(kind="travel", title="旅行")
    assert body.kind == "travel"


def test_list_create_rejects_invalid_kind():
    with pytest.raises(ValidationError):
        ListCreate(kind="weird", title="X")


def test_list_create_rejects_empty_title():
    with pytest.raises(ValidationError):
        ListCreate(kind="generic", title="")


def test_list_create_rejects_negative_budget():
    with pytest.raises(ValidationError):
        ListCreate(kind="shopping", title="買東西", budget=Decimal("-5"))


def test_list_update_rejects_unknown_field():
    with pytest.raises(ValidationError):
        ListUpdate.model_validate({"weird": 1})


def test_list_entry_create_requires_positive_quantity():
    with pytest.raises(ValidationError):
        ListEntryCreate(name="x", quantity=0)


def test_list_entry_update_forbids_extra():
    with pytest.raises(ValidationError):
        ListEntryUpdate.model_validate({"foo": "bar"})


def test_reorder_request_accepts_empty_list():
    r = ReorderRequest(entry_ids=[])
    assert r.entry_ids == []


def test_list_summary_can_be_built():
    now = datetime.now(timezone.utc)
    s = ListSummary(
        id=uuid.uuid4(),
        kind="travel",
        title="T",
        description=None,
        start_date=date.today(),
        end_date=None,
        budget=None,
        entry_count=3,
        done_count=1,
        created_at=now,
        updated_at=now,
    )
    assert s.entry_count == 3


def test_list_detail_wraps_entries():
    now = datetime.now(timezone.utc)
    detail = ListDetail(
        id=uuid.uuid4(),
        kind="shopping",
        title="shop",
        description=None,
        start_date=None,
        end_date=None,
        budget=Decimal("100.00"),
        entry_count=0,
        done_count=0,
        created_at=now,
        updated_at=now,
        entries=[],
    )
    assert detail.entries == []
