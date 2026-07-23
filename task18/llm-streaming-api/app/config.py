"""
Centralized configuration, loaded from environment variables / .env.

Using pydantic-settings gives us validation for free -- e.g. if someone
sets HEARTBEAT_INTERVAL_SECONDS=abc in .env, the app fails fast at startup
with a clear error instead of crashing later mid-stream.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    heartbeat_interval_seconds: float = 10.0
    request_timeout_seconds: float = 60.0
    max_concurrent_streams: int = 20


settings = Settings()
