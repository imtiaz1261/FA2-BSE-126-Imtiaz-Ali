"""
config.py
---------
Central configuration for Jarvis-Lite. Only GROQ_API_KEY is required;
weather (Open-Meteo) and stock data (yfinance) need no API key.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = Path(os.getenv("LOG_DIR", BASE_DIR / "logs"))
LOG_FILE = LOG_DIR / "jarvis.log"
LOG_DIR.mkdir(parents=True, exist_ok=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.2))

MAX_TOOL_CALL_ROUNDS = int(os.getenv("MAX_TOOL_CALL_ROUNDS", 4))  # safety cap against runaway loops
