from __future__ import annotations
import uuid
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
