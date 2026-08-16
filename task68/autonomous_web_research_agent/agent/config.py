from dataclasses import dataclass
import os
from dotenv import load_dotenv
load_dotenv()

@dataclass(frozen=True)
class Settings:
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    max_pages: int = int(os.getenv("MAX_PAGES", "8"))
    max_search_rounds: int = int(os.getenv("MAX_SEARCH_ROUNDS", "4"))
    max_seconds: int = int(os.getenv("MAX_SECONDS", "180"))

settings = Settings()
