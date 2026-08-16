"""
Configuration settings for the recommendation system.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/recommendation_db"
    sqlalchemy_echo: bool = False

    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    embedding_model: str = "text-embedding-3-small"

    # Groq
    groq_api_key: Optional[str] = None
    groq_model: str = "mixtral-8x7b-32768"

    # FastAPI
    fastapi_host: str = "0.0.0.0"
    fastapi_port: int = 8000
    debug: bool = True

    # Streamlit
    streamlit_port: int = 8501
    streamlit_theme: str = "light"

    # Recommendation Settings
    top_n_recommendations: int = 5
    similarity_threshold: float = 0.3
    max_conversation_history: int = 20
    embedding_dimension: int = 1536  # OpenAI embedding dimension

    class Config:
        env_file = ".env"
        case_sensitive = False

    def validate_api_keys(self) -> bool:
        """Validate that at least one LLM API key is provided."""
        if not self.openai_api_key and not self.groq_api_key:
            raise ValueError(
                "At least one LLM API key must be provided "
                "(OPENAI_API_KEY or GROQ_API_KEY)"
            )
        return True


# Global settings instance
settings = Settings()

# Validate on startup
try:
    settings.validate_api_keys()
except ValueError as e:
    print(f"Warning: {e}")
