from __future__ import annotations

import uuid
from datetime import date, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.batch import BatchConsume, BatchCreate, BatchRead, BatchUpdate


def _batch(**overrides) -> SimpleNamespace:
    base = dict(
        id=uuid.uuid4(),
        item_id=uuid.uuid4(),
        quantity=3,
        expiry_date=None,
        received_at=None,
        note=None,
        unit_cost=None,
        is_depleted=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_batch_read_derives_days_left_and_status():
    today = date(2026, 10, 15)

    expiring = BatchRead.from_batch(_batch(expiry_date=date(2026, 10, 22)), today=today)
    assert expiring.unit_cost is None
    assert expiring.days_left == 7
    assert expiring.status == "expiring"

    expired = BatchRead.from_batch(_batch(expiry_date=date(2026, 10, 14)), today=today)
    assert expired.days_left == -1
    assert expired.status == "expired"

    none = BatchRead.from_batch(_batch(expiry_date=None), today=today)
    assert none.days_left is None
    assert none.status == "ok"

    far = BatchRead.from_batch(_batch(expiry_date=date(2026, 11, 30)), today=today)
    assert far.status == "ok"


def test_batch_create_quantity_optional_but_positive_when_given():
    assert BatchCreate().quantity is None
    assert BatchCreate(quantity=1).quantity == 1
    with pytest.raises(ValidationError):
        BatchCreate(quantity=0)


def test_batch_update_exclude_unset_semantics():
    body = BatchUpdate(expiry_date=date(2026, 12, 31))
    assert body.model_dump(exclude_unset=True) == {"expiry_date": date(2026, 12, 31)}

    cleared = BatchUpdate(expiry_date=None, note=None)
    assert cleared.model_dump(exclude_unset=True) == {"expiry_date": None, "note": None}

    with pytest.raises(ValidationError):
        BatchUpdate(quantity=0)


def test_batch_consume_requires_positive_quantity():
    assert BatchConsume(quantity=2).quantity == 2
    with pytest.raises(ValidationError):
        BatchConsume(quantity=0)
