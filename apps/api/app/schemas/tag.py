from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TagRead(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)
