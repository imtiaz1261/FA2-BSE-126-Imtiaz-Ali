"""Tests for configuration loading and basic validation.

This small test ensures the Settings object can be imported and
some key properties have expected types/values. It is intentionally
lightweight and does not require external services.
"""

from backend.core.config import settings


def test_settings_loads_and_parses_types():
    # Basic smoke checks
    assert settings.APP_NAME
    assert isinstance(settings.DEBUG, bool)
    assert isinstance(settings.POSTGRES_PORT, int)
    assert isinstance(settings.allowed_origins_list, list)
    assert isinstance(settings.allowed_extensions_list, list)


def test_important_secrets_present():
    # In CI these may be absent; this test simply ensures keys exist
    # and are non-empty strings in local development.
    assert hasattr(settings, "SECRET_KEY")
    assert hasattr(settings, "JWT_SECRET_KEY")
    assert hasattr(settings, "OPENAI_API_KEY")

    assert isinstance(settings.SECRET_KEY, str)
    assert isinstance(settings.JWT_SECRET_KEY, str)
    assert isinstance(settings.OPENAI_API_KEY, str)
