"""
config.py
---------
Central configuration for the Multi-Step Research Assistant.
Only GROQ_API_KEY is a required secret; DuckDuckGo search needs no key.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
OUTPUTS_DIR = Path(os.getenv("OUTPUTS_DIR", BASE_DIR / "outputs"))
LOG_DIR = Path(os.getenv("LOG_DIR", BASE_DIR / "logs"))
LOG_FILE = LOG_DIR / "research_assistant.log"

for _dir in (OUTPUTS_DIR, LOG_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# LLM (Groq)
# --------------------------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.1))

# --------------------------------------------------------------------------
# Web search (DuckDuckGo -- free, no API key)
# --------------------------------------------------------------------------
SEARCH_RESULTS_PER_TASK = int(os.getenv("SEARCH_RESULTS_PER_TASK", 5))

# --------------------------------------------------------------------------
# Research workflow
# --------------------------------------------------------------------------
MAX_TASKS = int(os.getenv("MAX_TASKS", 5))           # cap on planner-generated tasks
MAX_RETRIES_PER_TASK = int(os.getenv("MAX_RETRIES_PER_TASK", 2))
MIN_RESULTS_FOR_SUFFICIENCY = int(os.getenv("MIN_RESULTS_FOR_SUFFICIENCY", 2))

# --------------------------------------------------------------------------
# FastAPI / Streamlit
# --------------------------------------------------------------------------
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", 8000))
