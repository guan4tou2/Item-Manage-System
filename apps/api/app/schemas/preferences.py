from typing import Literal

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

Theme = Literal["system", "light", "dark"]
Language = Literal["zh-TW", "en"]
Currency = Literal["TWD", "USD", "EUR", "JPY", "CNY", "HKD"]

_CURRENCY_ADAPTER = TypeAdapter(Currency)


def currency_from_raw(raw: dict) -> Currency:
    """Read a currency from a raw preferences dict; never raises.

    Missing or invalid values (e.g. legacy/foreign writes) fall back to TWD.
    """
    try:
        return _CURRENCY_ADAPTER.validate_python(raw.get("currency", "TWD"))
    except ValidationError:
        return "TWD"


class PreferencesRead(BaseModel):
    theme: Theme = "system"
    language: Language = "zh-TW"
    currency: Currency = "TWD"
    #: Phase 30：viewer 一次性說明 banner 是否已關閉（不重複顯示）
    viewer_notice_dismissed: bool = False
    #: Phase 31：月報總開關（關閉後不生成、不通知、不寄信）
    report_monthly_enabled: bool = True
    #: Phase 34：允許把物品摘要送往 Gemini（AI 搜尋／問答）；預設關閉
    ai_data_sharing_enabled: bool = False

    model_config = ConfigDict(extra="allow")


class PreferencesUpdate(BaseModel):
    theme: Theme | None = None
    language: Language | None = None
    currency: Currency | None = None
    viewer_notice_dismissed: bool | None = None
    report_monthly_enabled: bool | None = None
    ai_data_sharing_enabled: bool | None = None

    model_config = ConfigDict(extra="allow")
