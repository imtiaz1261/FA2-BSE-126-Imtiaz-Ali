"""
config.py
---------
Central configuration. Only GROQ_API_KEY is required.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PLUGINS_DIR = Path(os.getenv("PLUGINS_DIR", BASE_DIR / "plugins"))
PLUGIN_STATE_FILE = Path(os.getenv("PLUGIN_STATE_FILE", BASE_DIR / "plugins_state.json"))
LOG_DIR = Path(os.getenv("LOG_DIR", BASE_DIR / "logs"))
LOG_FILE = LOG_DIR / "plugin_system.log"
LOG_DIR.mkdir(parents=True, exist_ok=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.2))
MAX_TOOL_CALL_ROUNDS = int(os.getenv("MAX_TOOL_CALL_ROUNDS", 4))
