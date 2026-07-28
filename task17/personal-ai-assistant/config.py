"""
config.py
---------
Central configuration for the Personal AI Assistant.

Every tunable value lives here, read from environment variables (via a
.env file) with sensible free/local defaults so the project runs with
only ONE required secret: GROQ_API_KEY.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
VECTOR_DB_DIR = Path(os.getenv("VECTOR_DB_DIR", BASE_DIR / "vector_store"))
DB_PATH = Path(os.getenv("DB_PATH", BASE_DIR / "db" / "assistant.db"))
LOG_DIR = Path(os.getenv("LOG_DIR", BASE_DIR / "logs"))
LOG_FILE = LOG_DIR / "assistant.log"

for _dir in (DATA_DIR, VECTOR_DB_DIR, DB_PATH.parent, LOG_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# LLM (Groq) — the only required secret in this project
# --------------------------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.0))

# --------------------------------------------------------------------------
# Web search (DuckDuckGo — free, no API key)
# --------------------------------------------------------------------------
SEARCH_MAX_RESULTS = int(os.getenv("SEARCH_MAX_RESULTS", 5))

# --------------------------------------------------------------------------
# Weather (Open-Meteo — free, no API key)
# --------------------------------------------------------------------------
OPEN_METEO_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# --------------------------------------------------------------------------
# Document RAG (file reading / summarizing)
# --------------------------------------------------------------------------
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", 4))
SUPPORTED_FILE_EXTENSIONS = {".pdf", ".docx", ".txt"}

# --------------------------------------------------------------------------
# Conversation memory
# --------------------------------------------------------------------------
# How many past turns to keep in the live in-memory buffer per session.
MAX_MEMORY_TURNS = int(os.getenv("MAX_MEMORY_TURNS", 20))

# --------------------------------------------------------------------------
# Voice (SpeechRecognition + pyttsx3 — both free / offline where possible)
# --------------------------------------------------------------------------
TTS_RATE = int(os.getenv("TTS_RATE", 175))
TTS_VOLUME = float(os.getenv("TTS_VOLUME", 1.0))