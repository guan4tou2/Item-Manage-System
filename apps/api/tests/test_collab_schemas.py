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


def test_group_member_read_role_accepts_four_values():
    from datetime import datetime, timezone
    from app.schemas.group import GroupMemberRead

    for role in ("owner", "admin", "editor", "viewer"):
        row = GroupMemberRead(
            user_id=uuid.uuid4(), username="u", joined_at=datetime.now(tz=timezone.utc), role=role
        )
        assert row.role == role


def test_group_member_read_role_rejects_unknown():
    from datetime import datetime, timezone
    from app.schemas.group import GroupMemberRead

    with pytest.raises(ValidationError):
        GroupMemberRead(
            user_id=uuid.uuid4(), username="u", joined_at=datetime.now(tz=timezone.utc), role="boss"
        )


def test_add_member_role_defaults_to_editor():
    assert GroupAddMember(username="u").role == "editor"


def test_add_member_role_rejects_owner_and_unknown():
    with pytest.raises(ValidationError):
        GroupAddMember(username="u", role="owner")
    with pytest.raises(ValidationError):
        GroupAddMember(username="u", role="boss")


def test_group_summary_my_role_literal():
    from datetime import datetime, timezone
    from app.schemas.group import GroupSummary

    base = dict(
        id=uuid.uuid4(),
        name="g",
        owner_id=uuid.uuid4(),
        owner_username="o",
        is_owner=False,
        member_count=1,
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
    )
    for role in ("owner", "admin", "editor", "viewer"):
        assert GroupSummary(**base, my_role=role).my_role == role
    with pytest.raises(ValidationError):
        GroupSummary(**base, my_role="boss")
