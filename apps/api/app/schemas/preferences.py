from typing import Literal

from pydantic import BaseModel, ConfigDict

Theme = Literal["system", "light", "dark"]
Language = Literal["zh-TW", "en"]


class PreferencesRead(BaseModel):
    theme: Theme = "system"
    language: Language = "zh-TW"

    model_config = ConfigDict(extra="allow")


class PreferencesUpdate(BaseModel):
    theme: Theme | None = None
    language: Language | None = None

    model_config = ConfigDict(extra="allow")
