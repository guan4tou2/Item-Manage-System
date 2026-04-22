import pytest
from pydantic import ValidationError

from app.schemas.preferences import PreferencesRead, PreferencesUpdate


class TestPreferencesRead:
    def test_default_theme_is_system(self):
        prefs = PreferencesRead()
        assert prefs.theme == "system"

    def test_default_language_is_zh_tw(self):
        prefs = PreferencesRead()
        assert prefs.language == "zh-TW"

    def test_accepts_valid_theme(self):
        prefs = PreferencesRead(theme="dark")
        assert prefs.theme == "dark"

    def test_accepts_valid_language(self):
        prefs = PreferencesRead(language="en")
        assert prefs.language == "en"

    def test_rejects_invalid_theme(self):
        with pytest.raises(ValidationError):
            PreferencesRead(theme="neon")

    def test_rejects_invalid_language(self):
        with pytest.raises(ValidationError):
            PreferencesRead(language="ja")

    def test_allows_extra_keys(self):
        prefs = PreferencesRead(theme="light", notifications_enabled=True)
        assert prefs.model_dump()["notifications_enabled"] is True


class TestPreferencesUpdate:
    def test_all_fields_optional(self):
        PreferencesUpdate()  # should not raise

    def test_theme_only(self):
        update = PreferencesUpdate(theme="dark")
        assert update.model_dump(exclude_none=True) == {"theme": "dark"}

    def test_language_only(self):
        update = PreferencesUpdate(language="en")
        assert update.model_dump(exclude_none=True) == {"language": "en"}

    def test_theme_and_language(self):
        update = PreferencesUpdate(theme="dark", language="en")
        assert update.model_dump(exclude_none=True) == {"theme": "dark", "language": "en"}

    def test_allows_extra_keys(self):
        update = PreferencesUpdate(notifications_enabled=True)
        assert update.model_dump(exclude_none=True)["notifications_enabled"] is True

    def test_rejects_invalid_theme(self):
        with pytest.raises(ValidationError):
            PreferencesUpdate(theme="aqua")

    def test_rejects_invalid_language(self):
        with pytest.raises(ValidationError):
            PreferencesUpdate(language="de")
