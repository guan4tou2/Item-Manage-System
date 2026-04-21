from typing import Literal

from pydantic import BaseModel, ConfigDict

Theme = Literal["system", "light", "dark"]


class PreferencesRead(BaseModel):
    theme: Theme = "system"

    model_config = ConfigDict(extra="allow")


class PreferencesUpdate(BaseModel):
    theme: Theme | None = None

    model_config = ConfigDict(extra="allow")
