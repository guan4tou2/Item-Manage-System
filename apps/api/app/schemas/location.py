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
