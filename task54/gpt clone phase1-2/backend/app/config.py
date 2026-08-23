"""
Centralized application settings, loaded from environment variables / .env.
Import `settings` anywhere it's needed rather than reading os.environ directly.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "Chatline"
    environment: str = "development"
    frontend_url: str = "http://localhost:5173"

    # Database
    database_url: str
    database_url_sync: str

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Cookies
    cookie_secure: bool = False
    cookie_domain: str = "localhost"

    # Rate limiting
    login_rate_limit: str = "5/minute"

    # Logging
    log_level: str = "INFO"

    # Sentry Error Tracking
    sentry_dsn: str = ""
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 0.1
    sentry_profiles_sample_rate: float = 0.1

    # Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "no-reply@chatline.app"

    # OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_tenant: str = "common"  # "common" allows personal + work/school accounts

    # Vision & S3
    s3_endpoint: str = ""  # e.g., "https://s3.amazonaws.com" or minio endpoint
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "chatline-images"
    s3_region: str = "us-east-1"
    vision_api_key: str = ""  # Claude/GPT-4V API key
    vision_model: str = "gpt-4-vision-preview"  # or "claude-3-vision-sonnet"
    max_image_size_mb: int = 10
    image_upload_expiry_hours: int = 24

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
