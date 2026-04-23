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
