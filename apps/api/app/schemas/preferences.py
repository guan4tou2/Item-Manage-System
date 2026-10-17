from typing import Literal

from pydantic import BaseModel, ConfigDict

Theme = Literal["system", "light", "dark"]
Language = Literal["zh-TW", "en"]
Currency = Literal["TWD", "USD", "EUR", "JPY", "CNY", "HKD"]


class PreferencesRead(BaseModel):
    theme: Theme = "system"
    language: Language = "zh-TW"
    currency: Currency = "TWD"

    model_config = ConfigDict(extra="allow")


class PreferencesUpdate(BaseModel):
    theme: Theme | None = None
    language: Language | None = None
    currency: Currency | None = None

    model_config = ConfigDict(extra="allow")
