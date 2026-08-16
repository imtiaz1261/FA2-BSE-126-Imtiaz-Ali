from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    db_path: str = os.getenv("AB_DB_PATH", "data/ab_testing.db")
    variant_a_weight: float = float(os.getenv("VARIANT_A_WEIGHT", "0.5"))

settings = Settings()
if not 0 < settings.variant_a_weight < 1:
    raise ValueError("VARIANT_A_WEIGHT must be between 0 and 1.")
