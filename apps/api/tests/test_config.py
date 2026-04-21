import pytest
from pydantic import ValidationError

from app.config import Settings, _DEFAULT_JWT_SECRET


def test_default_secret_rejected_outside_dev():
    with pytest.raises(ValidationError):
        Settings(environment="prod", jwt_secret=_DEFAULT_JWT_SECRET)


def test_default_secret_allowed_in_dev():
    settings = Settings(environment="dev", jwt_secret=_DEFAULT_JWT_SECRET)
    assert settings.jwt_secret == _DEFAULT_JWT_SECRET
    assert settings.environment == "dev"
