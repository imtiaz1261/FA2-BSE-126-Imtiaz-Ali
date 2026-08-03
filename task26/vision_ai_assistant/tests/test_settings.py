"""Basic tests for application settings."""

from config.settings import get_settings


def test_settings_load_default_app_name() -> None:
    """Ensure default app name is available when environment is not configured."""
    settings = get_settings()
    assert settings.app_name == "Secure AI Assistant"


def test_guardrails_enabled_by_default() -> None:
    """Ensure both guardrails are enabled in default configuration."""
    settings = get_settings()
    assert settings.input_guardrail_enabled is True
    assert settings.output_guardrail_enabled is True
